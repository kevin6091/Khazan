"""Read-only inventory of actual giant animation consumers, then root audit."""
from pathlib import Path
import hashlib
import json
import os
import runpy
import traceback
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = Path(os.environ['KZ_GIANT_ROOT_OUT'])
OUT.mkdir(parents=True, exist_ok=True)
report = {'status': 'running', 'project': str(ROOT), 'saved_packages': 0, 'families': [], 'definitions': [], 'montages': [], 'sequences': []}
clips, montages, definitions = {}, {}, {}
registry = unreal.AssetRegistryHelpers.get_asset_registry()

def prop(obj, key, default=None):
    if obj is None:
        return default
    try:
        return obj.get_editor_property(key)
    except Exception:
        try:
            return obj.get_editor_property(key[2:]) if key.startswith('b_') else default
        except Exception:
            return default

def path(obj):
    return obj.get_path_name() if obj else None

def animation(obj, family, role):
    if not obj:
        return
    use = (family, role)
    if isinstance(obj, unreal.AnimSequence):
        clips.setdefault(path(obj), {'object': obj, 'uses': set()})['uses'].add(use)
    elif isinstance(obj, (unreal.AnimMontage, unreal.AnimComposite)):
        key = path(obj)
        if key in montages:
            montages[key]['uses'].add(use)
            for segment in montages[key]['segments']:
                animation(unreal.load_asset(segment['clip']), family, role)
            return
        row = {'asset': key, 'uses': {use}, 'segments': []}
        montages[key] = row
        tracks = [prop(t, 'anim_track') for t in prop(obj, 'slot_anim_tracks', [])] if isinstance(obj, unreal.AnimMontage) else [prop(obj, 'anim_track')]
        for track in tracks:
            for segment in prop(track, 'anim_segments', []):
                clip = prop(segment, 'anim_reference')
                row['segments'].append({'clip': path(clip), 'start': prop(segment, 'start_pos'),
                                        'clip_start': prop(segment, 'anim_start_time'), 'clip_end': prop(segment, 'anim_end_time'),
                                        'rate': prop(segment, 'anim_play_rate'), 'loops': prop(segment, 'looping_count')})
                animation(clip, family, role)

def ability(cls, family, role):
    if not cls:
        return
    cdo = unreal.get_default_object(cls)
    definition = prop(cdo, 'combo_definition')
    if not definition:
        return
    key = path(definition)
    if (key, family) in definitions:
        return
    row = {'asset': key, 'family': family, 'ability': path(cls), 'role': role, 'nodes': []}
    definitions[(key, family)] = row
    for node in prop(definition, 'nodes', []):
        montage = prop(node, 'montage')
        node_id = str(prop(node, 'node_id'))
        animation(montage, family, 'ability:' + node_id)
        row['nodes'].append({'node': node_id, 'skill': str(prop(node, 'pattern_skill')),
                             'montage': path(montage), 'section': str(prop(node, 'section_name')),
                             'pattern_moves': [move.export_text() for move in prop(node, 'pattern_moves', [])]})

def graph(cls, family):
    pending = [path(cls).split('.')[0]] if cls else []
    seen = set()
    options = unreal.AssetRegistryDependencyOptions(include_hard_package_references=True, include_soft_package_references=True,
        include_searchable_names=False, include_hard_management_references=False, include_soft_management_references=False)
    while pending:
        package = pending.pop()
        if package in seen:
            continue
        seen.add(package)
        for ref in registry.get_dependencies(package, options) or []:
            for data in registry.get_assets_by_package_name(ref) or []:
                kind = str(data.asset_class_path.asset_name)
                if kind in ('AnimSequence', 'AnimMontage', 'AnimComposite'):
                    animation(data.get_asset(), family, 'anim_graph:' + package)
                elif kind in ('AnimBlueprint', 'BlendSpace', 'BlendSpace1D', 'AimOffsetBlendSpace', 'AimOffsetBlendSpace1D'):
                    pending.append(str(ref))
    return sorted(seen)

try:
    for family in ('ApesStoneHandElite', 'Yetuga'):
        cls = unreal.load_class(None, f'/Game/Bluprints/Monsters/BP_Monster_{family}.BP_Monster_{family}_C')
        assert cls, family
        cdo = unreal.get_default_object(cls)
        mesh = prop(cdo, 'mesh')
        definition = prop(cdo, 'character_definition') or unreal.load_asset(f'/Game/Monsters/{family}/Data/DA_Character_{family}')
        assert mesh and definition, family
        anim_cls = prop(mesh, 'anim_class')
        body = prop(mesh, 'skeletal_mesh')
        body_skeleton = prop(body, 'skeleton')
        report['families'].append({'family': family, 'definition': path(definition), 'mesh': path(body),
            'body_skeleton': path(body_skeleton), 'mesh_transform': mesh.get_relative_transform().export_text(),
            'anim_class': path(anim_cls), 'root_motion_mode': str(prop(unreal.get_default_object(anim_cls), 'root_motion_mode')),
            'anim_graph_packages': graph(anim_cls, family), 'ai_settings': prop(cdo, 'ai_settings').export_text()})
        for grant in prop(definition, 'initial_ability_grants', []):
            ability(prop(grant, 'ability_class'), family, 'initial_grant')
        for routine in prop(definition, 'unaware_routines', []):
            ability(prop(routine, 'ability_class'), family, 'unaware')
        for choice in prop(cdo, 'combat_patterns', []):
            ability(prop(choice, 'ability'), family, 'combat_choice:' + str(prop(choice, 'skill')))
        reactions = prop(definition, 'hit_reactions')
        for key in ('short_hits', 'knockbacks', 'launches', 'shield_blocks', 'additive_hits'):
            for montage in prop(reactions, key, []):
                animation(montage, family, 'reaction:' + key)
        animation(prop(reactions, 'victim_front'), family, 'reaction:victim_front')
        stamina = prop(definition, 'monster_stamina')
        for key in ('exhaustion_montage', 'part_group1_groggy_montage', 'death_presentation_montage', 'brutal_front_victim_montage', 'brutal_back_victim_montage'):
            animation(prop(stamina, key), family, 'stamina:' + key)
    report['definitions'] = list(definitions.values())
    report['montages'] = [dict(row, uses=sorted(row['uses'])) for row in montages.values()]
    skeletons = {row['family']: row['body_skeleton'] for row in report['families']}
    for key, entry in sorted(clips.items()):
        clip = entry['object']
        package = clip.get_path_name().split('.')[0]
        file = ROOT / 'Content' / (package.removeprefix('/Game/') + '.uasset')
        skeleton = path(prop(clip, 'skeleton'))
        report['sequences'].append({'asset': key, 'uses': sorted(entry['uses']), 'skeleton': skeleton,
            'body_consumer': any(skeletons[f] == skeleton for f, role in entry['uses']),
            'file': str(file), 'sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
            'enable_root_motion': prop(clip, 'enable_root_motion'), 'force_root_lock': prop(clip, 'force_root_lock'),
            'root_lock': str(prop(clip, 'root_motion_root_lock')), 'additive': str(prop(clip, 'additive_anim_type')),
            'length': clip.get_play_length(), 'rate_scale': prop(clip, 'rate_scale')})
    report['dirty_content'] = [str(p.get_name()) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    report['summary'] = {'sequences': len(clips), 'montages': len(montages), 'definitions': len(definitions),
        'root_motion_disabled': [r['asset'] for r in report['sequences'] if r['body_consumer'] and not r['enable_root_motion']],
        'force_root_lock_disabled': [r['asset'] for r in report['sequences'] if r['body_consumer'] and not r['force_root_lock']]}
    runpy.run_path(r'C:/Users/user/.codex/skills/unreal-root-motion-repair/scripts/audit_root_motion.py',
        init_globals={'ROOT_MOTION_AUDIT_ASSETS': [{'asset': row['asset'], 'expects_root_motion': False, 'motion_bones': ['Root', 'Bip001']} for row in report['sequences'] if row['body_consumer']],
                      'ROOT_MOTION_AUDIT_REPORT': str(OUT / 'RootAudit.json')}, run_name='__main__')
    report['status'] = 'passed'
except Exception:
    report.update(status='failed', error=traceback.format_exc())
    unreal.log_error(report['error'])
finally:
    (OUT / 'Usage.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    unreal.log('GIANT_USED_ROOT ' + json.dumps({'status': report['status'], 'summary': report.get('summary'), 'error': report.get('error')}))
    unreal.SystemLibrary.quit_editor()
