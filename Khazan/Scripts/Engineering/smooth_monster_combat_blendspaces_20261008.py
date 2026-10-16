"""Apply only four combat BlendSpace weight speeds; audit the existing ABP nodes.

Run inside Unreal Python, not as a standalone Python process. For example:
    import runpy, sys
    script = '<project>/Scripts/Engineering/smooth_monster_combat_blendspaces_20261008.py'
    old_argv = sys.argv
    try:
        sys.argv = [script, 'audit']
        runpy.run_path(script, run_name='__main__')
    finally:
        sys.argv = old_argv

Modes: audit (default), mainapply, workapply. workapply requires sys.argv[2]
to contain the exact copied project root. mainapply accepts only MAIN_PROJECT.
No ABP, sequence, montage, source, map, or non-combat BlendSpace is saved.
"""
import datetime
import hashlib
import json
import os
import pathlib
import sys

import unreal


MAIN_PROJECT = pathlib.Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
ORIGINAL_BASE = pathlib.Path(
    'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/Source/BBQ/Content/'
    '_Kazan_/Design/Monster/Human/Empire')
SOURCE_FIELD = 'Properties.TargetWeightInterpolationSpeedPerSec'
TARGETS = (
    ('Swordsman', 'EmpireSword', 'BS_EmpireSword_LockOnMove', 6.0),
    ('SwordShield', 'Empire_SwordShield', 'BS_Empire_SwordShield_LockOnMove', 10.0),
    ('HeavySwordsman', 'Empire_SwordHArmor', 'BS_Empire_SwordHArmor_LockOnMove', 10.0),
    ('HalberdElite', 'EmpireHalberd_E', 'BS_EmpireHalberd_E_LockOnMove', 5.0),
)


def plain(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, unreal.Object):
        return value.get_path_name()
    if isinstance(value, (list, tuple, unreal.Array)):
        return [plain(item) for item in value]
    return str(value)


def property_read(owner, name):
    try:
        return {'ok': True, 'value': plain(owner.get_editor_property(name))}
    except Exception as error:
        return {'ok': False, 'error': str(error)}


def abp_readback(asset):
    """Read author graph node structs without modifying or compiling the ABP."""
    result = {'asset': asset.get_path_name(), 'status': property_read(asset, 'status'),
              'graphs': [], 'errors': []}
    try:
        graphs = asset.get_editor_property('function_graphs')
    except Exception as error:
        result['errors'].append({'property': 'function_graphs', 'error': str(error)})
        result['readback_complete'] = False
        return result
    for graph in graphs:
        if graph.get_name() != 'AnimGraph':
            continue
        graph_result = {'name': graph.get_name(), 'path': graph.get_path_name(), 'nodes': []}
        result['graphs'].append(graph_result)
        try:
            nodes = graph.get_editor_property('nodes')
        except Exception as error:
            result['errors'].append({'graph': graph.get_path_name(), 'property': 'nodes',
                                     'error': str(error)})
            continue
        for node in nodes:
            kind = node.get_class().get_name()
            if kind not in ('AnimGraphNode_Slot', 'AnimGraphNode_BlendListByBool',
                            'AnimGraphNode_BlendListByEnum', 'AnimGraphNode_Inertialization'):
                continue
            row = {'node': node.get_name(), 'class': kind, 'properties': {}}
            graph_result['nodes'].append(row)
            if kind == 'AnimGraphNode_BlendListByEnum':
                row['bound_enum'] = property_read(node, 'BoundEnum')
                row['visible_enum_entries'] = property_read(node, 'VisibleEnumEntries')
                for field, read in (('BoundEnum', row['bound_enum']),
                                    ('VisibleEnumEntries', row['visible_enum_entries'])):
                    if not read['ok']:
                        result['errors'].append({'node': node.get_path_name(), 'property': field,
                                                 'error': read['error']})
            if kind == 'AnimGraphNode_Inertialization':
                continue
            try:
                data = node.get_editor_property('node')
            except Exception as error:
                result['errors'].append({'node': node.get_path_name(), 'property': 'node',
                                         'error': str(error)})
                continue
            fields = ('SlotName', 'bAlwaysUpdateSourcePose') if kind == 'AnimGraphNode_Slot' else (
                'BlendTime', 'TransitionType', 'BlendType', 'ChildUpateMode', 'BlendProfile')
            for field in fields:
                read = property_read(data, field)
                row['properties'][field] = read
                if not read['ok']:
                    result['errors'].append({'node': node.get_path_name(), 'property': field,
                                             'error': read['error']})
    counts = {}
    for graph in result['graphs']:
        for node in graph['nodes']:
            counts[node['class']] = counts.get(node['class'], 0) + 1
    result['node_class_counts'] = counts
    result['expected_node_counts_match'] = counts == {
        'AnimGraphNode_Slot': 1, 'AnimGraphNode_BlendListByBool': 1,
        'AnimGraphNode_BlendListByEnum': 3, 'AnimGraphNode_Inertialization': 1}
    result['readback_complete'] = (bool(result['graphs']) and not result['errors']
                                   and result['expected_node_counts_match'])
    return result


def main():
    root = pathlib.Path(unreal.Paths.project_dir()).resolve()
    mode = sys.argv[1] if len(sys.argv) > 1 else 'audit'
    if mode not in ('audit', 'mainapply', 'workapply'):
        raise RuntimeError('Use sys.argv = [script, audit|mainapply|workapply, optional_work_root]')
    if mode == 'mainapply' and root != MAIN_PROJECT:
        raise RuntimeError('mainapply project identity mismatch: ' + str(root))
    if mode == 'workapply':
        if len(sys.argv) != 3:
            raise RuntimeError('workapply needs the exact work project root in sys.argv[2]')
        expected = pathlib.Path(sys.argv[2]).resolve()
        if root != expected or root == MAIN_PROJECT:
            raise RuntimeError('workapply must match the explicitly supplied non-main project root')
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    if editor.get_game_world():
        raise RuntimeError('Stop PIE before this saved-asset operation')
    dirty_before = [p.get_path_name() for p in
                    unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    report = {'mode': mode, 'project': str(root), 'pid': os.getpid(),
              'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'dirty_content_before': dirty_before, 'families': [],
              'policy': 'Original sample-weight speed values copied without changing BS topology.',
              'limits': ['Original normalized X/Y topology differs from current Direction/Speed topology.',
                         'Original omitted InterpolationTime/ease fields are not asserted as zero/false.',
                         'ABP readback errors are reported, not counted as verified settings.',
                         'No runtime motion or exact original-engine interpolation equivalence tested.']}
    loaded = []
    # Validate every original record and all four target assets before any mutation.
    for family, original_family, original_name, expected_value in TARGETS:
        original_file = root / ORIGINAL_BASE / original_family / 'Moving/Move' / (original_name + '.json')
        raw = original_file.read_bytes()
        exports = json.loads(raw.decode('utf-8-sig'))
        matches = [entry for entry in exports if entry.get('Name') == original_name
                   and entry.get('Type') == 'BlendSpace']
        if len(matches) != 1:
            raise RuntimeError('Original BlendSpace export identity mismatch: ' + str(original_file))
        original = matches[0]
        value = original['Properties']['TargetWeightInterpolationSpeedPerSec']
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value != expected_value:
            raise RuntimeError('Original direct weight-speed value mismatch: ' + str(original_file))
        base = '/Game/Monsters/' + family + '/Animations/'
        target_path = base + 'BS_Combat_' + family
        abp_path = base + 'ABP_' + family
        space = unreal.load_asset(target_path)
        abp = unreal.load_asset(abp_path)
        if not isinstance(space, unreal.BlendSpace) or not isinstance(abp, unreal.AnimBlueprint):
            raise RuntimeError('Required saved combat BlendSpace/ABP missing: ' + family)
        if mode != 'audit' and target_path in dirty_before:
            raise RuntimeError('Target already has unsaved edits; refusing to save it: ' + target_path)
        row = {'family': family, 'asset': space.get_path_name(), 'package': target_path,
               'original_file': str(original_file), 'original_package': original.get('Package'),
               'original_export_name': original_name, 'original_field': SOURCE_FIELD,
               'original_raw_value': value, 'original_sha256': hashlib.sha256(raw).hexdigest(),
               'unit': 'sample weight per second (not degrees/second or a blend duration)',
               'before': space.get_editor_property('target_weight_interpolation_speed_per_sec'),
               'requested': value, 'changed': False, 'saved': False,
               'abp_package_was_dirty': abp_path in dirty_before}
        loaded.append((space, abp, row))
        report['families'].append(row)
    for space, abp, row in loaded:
        if mode != 'audit' and row['before'] != row['requested']:
            space.set_editor_property('target_weight_interpolation_speed_per_sec', row['requested'])
            row['changed'] = True
            row['saved'] = unreal.EditorAssetLibrary.save_loaded_asset(space, only_if_is_dirty=False)
            if not row['saved']:
                raise RuntimeError('Combat BlendSpace save failed: ' + row['asset'])
        row['after'] = space.get_editor_property('target_weight_interpolation_speed_per_sec')
        row['target_value_matches'] = row['after'] == row['requested']
        row['abp_readback'] = abp_readback(abp)
    report['dirty_content_after'] = [p.get_path_name() for p in
                                   unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    report['all_target_values_match'] = all(row['target_value_matches'] for row in report['families'])
    report['all_abp_readbacks_complete'] = all(row['abp_readback']['readback_complete']
                                             for row in report['families'])
    output = root / 'Saved/MonsterMotionSmoothing_20261008' / ('CombatBlendSpace_' + mode + '.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print('Combat BlendSpace report:', output)


if __name__ == '__main__':
    main()
