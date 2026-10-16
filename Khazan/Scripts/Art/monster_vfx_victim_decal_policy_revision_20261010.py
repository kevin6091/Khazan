"""Root-launched exact 43-Effect private policy revision; never edit original reports.

Default probe saves nothing. Root opts into apply with
KZ_MONSTER_VFX_VICTIM_DECAL_MODE=apply and exact loaded native DLL SHA in
KZ_MONSTER_VFX_VICTIM_DECAL_DLL_SHA256. Source victim animation owns these
Decal windows. Original absent CDO condition remains unknown, not hit proof.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import ast
import copy
import ctypes
import difflib
import hashlib
import json
import os
import re
import shutil
import struct
import traceback
import zipfile
import unreal

MAIN = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path(unreal.Paths.project_dir()).resolve()
assert WORK == Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan'), 'Main/shared revision blocked'
TASK = MAIN / 'Saved/ImportReports/MonsterVFX_20261008'
OUT = TASK / 'Authoring/VictimDecalPolicyRevision'
FINAL = TASK / 'Authoring/VictimDecalPolicyRevision.json'
AUTHOR = TASK / 'Authoring/PrivateAuthoring.json'
PLAN = TASK / 'PreparedPlaybackPlan.json'
MODE = globals().get('KZ_MONSTER_VFX_VICTIM_DECAL_MODE', os.environ.get('KZ_MONSTER_VFX_VICTIM_DECAL_MODE', 'probe'))
assert MODE in ('probe', 'apply')
EXPECTED_COUNT = 43
EXPECTED_SEQUENCE_COUNT = 26
EXPECTED_IDS_SHA256 = 'c0e8384053dc16c8752b6aaac6c2073d579aaa6e74baa7caa1760673b7ae4068'
EXPECTED_PLAN_SHA256 = 'aee394cf819993a74d7113b7b778638f69e5365faa46b585999dc36a15861bca'
EXPECTED_AUTHOR_SHA256 = 'fe268dad08bd3e34b33671be6307e641a7b95bf1c318e08ad6a4ef0c928e80c0'
POLICY = 'Explicit revised project presentation adapter: source victim Damage/Death animation owns Decal timing. Remove only the former Blood-name-inferred guard. No fake confirmed hit, outgoing-hit gate, new incoming state, timer or getter. Original absent CDO success condition remains unknown.'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.victim-decal.tmp')
    assert not temp.exists(), str(temp)
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temp, path)


def package_file(asset, mutation=False):
    assert asset.startswith('/Game/') and '.' not in asset and '..' not in Path(asset).parts
    path = WORK / ('Content/' + asset.removeprefix('/Game/') + '.uasset')
    if mutation:
        assert path.resolve() == path and path.resolve().is_relative_to(WORK), 'Shared/junction mutation blocked: ' + asset
    return path


def immutable_backup(source, target, expected):
    assert sha(source) == expected, 'Backup source CAS changed: ' + str(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        assert sha(target) == expected, 'Retained backup differs: ' + str(target)
    else:
        shutil.copy2(source, target)
    assert sha(target) == expected


def loaded_module():
    manifest = WORK / 'Binaries/Win64/UnrealEditor.modules'
    manifest_data = read(manifest)
    alias = manifest_data['Modules']['Khazan']
    expected = globals().get('KZ_MONSTER_VFX_VICTIM_DECAL_DLL_SHA256', os.environ.get('KZ_MONSTER_VFX_VICTIM_DECAL_DLL_SHA256'))
    if MODE == 'apply' or expected is not None:
        assert isinstance(expected, str) and re.fullmatch('[0-9a-fA-F]{64}', expected), 'Exact loaded native DLL SHA required'
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [ctypes.c_wchar_p]
    kernel.GetModuleHandleW.restype = ctypes.c_void_p
    kernel.GetModuleFileNameW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint32]
    kernel.GetModuleFileNameW.restype = ctypes.c_uint32
    handle = kernel.GetModuleHandleW(alias)
    assert handle, 'Selected native module not loaded'
    buffer = ctypes.create_unicode_buffer(32768)
    count = kernel.GetModuleFileNameW(handle, buffer, len(buffer))
    assert 0 < count < len(buffer)
    path = Path(buffer.value).resolve()
    assert path == (WORK / 'Binaries/Win64' / alias).resolve()
    actual_sha = sha(path)
    if expected is not None:
        assert actual_sha == expected.lower(), 'Loaded module SHA differs'
    return {'path': str(path), 'sha256': actual_sha, 'name': alias,
        'manifest_sha256': sha(manifest), 'build_id': manifest_data['BuildId']}


def readonly_helpers():
    # Only established getter/export functions, not author top-level execution.
    h = {'Path': Path, 'unreal': unreal, 'json': json, 're': re,
        'hashlib': hashlib, 'Counter': Counter, 'struct': struct,
        'WORK': WORK, 'OUT': OUT / 'RawModelExports'}
    h['OUT'].mkdir(parents=True, exist_ok=True)
    sources = [
        (MAIN / 'Scripts/Art/player_attack_vfx_author.py', {'guid', 'f32', 'export'}),
        (MAIN / 'Scripts/Art/monster_vfx_author_20261008.py',
            {'encode', 'data_fields', 'track_names', 'state_events', 'actual_event',
             'exported_struct_fields', 'raw_snapshot', 'preserved_snapshot', 'verify_preserved', 'sha'})]
    for source, names in sources:
        tree = ast.parse(source.read_text(encoding='utf-8-sig'))
        nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
        assert {node.name for node in nodes} == names
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'), h)
    return h


def source_evidence(event):
    s = event['source']
    if 'source_file' in s:
        source = MAIN / s['source_file']
        payload = source.read_bytes()
        location = {'source_file': str(source)}
    else:
        source = MAIN / s['source_zip']
        with zipfile.ZipFile(source) as archive:
            payload = archive.read(s['source_zip_entry'])
        location = {'source_zip': str(source), 'source_zip_sha256': sha(source), 'source_zip_entry': s['source_zip_entry']}
    assert hashlib.sha256(payload).hexdigest() == s['source_sha256'], 'Exact original JSON bytes differ'
    raw = json.loads(payload)
    exports = raw if isinstance(raw, list) else raw['Exports']
    reference = s['raw_notify']['NotifyStateClass']
    index = int(reference['ObjectPath'].rsplit('.', 1)[1])
    entry = exports[index]
    assert entry['Type'] == event['notify_type'] == 'xxAnimNotifyState_Decal'
    assert entry['Properties'] == s['properties']
    assert 'bOnAttackSuccessed' not in entry['Properties']
    assert reference['ObjectName'].endswith(':' + entry['Name'] + "'")
    return {'event_id': event['event_id'], 'asset': event['asset'], 'family': event['family'], 'category': event['category'],
        'source_package': s['source_package'], 'source_sha256': s['source_sha256'],
        'source_export_index': index, 'source_export_name': entry['Name'], 'source_notify_field': s['field'],
        'raw_property_keys': sorted(entry['Properties']), 'serialized_bOnAttackSuccessed_present': False,
        'original_cdo_condition': 'Unknown: omitted instance field does not establish original CDO default.', **location}


def export_text(h, asset, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    h['export'](asset, target)
    return target.read_text(encoding='utf-8-sig')


def exact_bool_only_export_diff(before, after, count):
    deleted, inserted = [], []
    for tag, i, j, k, l in difflib.SequenceMatcher(None, before.splitlines(), after.splitlines(), autojunk=False).get_opcodes():
        if tag != 'equal':
            deleted.extend(before.splitlines()[i:j])
            inserted.extend(after.splitlines()[k:l])
    assert len(deleted) == count and all(line.strip() == 'bOnAttackSuccessed=True' for line in deleted), 'Other serialized sequence/subobject properties changed: ' + repr(deleted[:8])
    assert len(inserted) <= count and all(line.strip() == 'bOnAttackSuccessed=False' for line in inserted), 'Other serialized sequence/subobject properties inserted: ' + repr(inserted[:8])
    return {'removed_true_lines': len(deleted), 'inserted_false_lines': len(inserted),
        'only_exact_guard_property_changed': True, 'default_false_may_be_omitted_by_exporter': True}


def main():
    report = {'schema': 'Khazan.MonsterVFX.VictimDecalPolicyRevision.v1', 'status': 'running',
        'mode': MODE, 'pid': os.getpid(), 'utc': datetime.now(timezone.utc).isoformat(), 'project': str(WORK),
        'policy': POLICY, 'package_saves': 0, 'asset_saves': 0, 'asset_mutations': 0, 'main_mutations': 0,
        'events': [], 'sequences': [], 'source_absent_field_evidence43': []}
    before_hashes = {}
    try:
        assert not FINAL.exists(), 'Revision already committed; use fresh saved audit, never repeat'
        assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None, 'Own PIE must stop first'
        assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
        assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
        assert sha(PLAN) == EXPECTED_PLAN_SHA256 and sha(AUTHOR) == EXPECTED_AUTHOR_SHA256
        plan, author = read(PLAN), read(AUTHOR)
        assert author['status'] == 'passed' and author['plan_sha256'] == sha(PLAN)
        assert len(author['sequences']) == 487 and len(author['events']) == 3342 and len(author['mutation_journal']) == 499
        targets = [e for e in plan['events'] if e.get('effect_fields', {}).get('bOnAttackSuccessed') is True]
        ids = sorted(e['event_id'] for e in targets)
        assert len(ids) == len(set(ids)) == EXPECTED_COUNT
        assert hashlib.sha256(json.dumps(ids, separators=(',', ':')).encode()).hexdigest() == EXPECTED_IDS_SHA256
        assert all(e['category'] in ('Damage', 'Death') and e['notify_type'] == 'xxAnimNotifyState_Decal' for e in targets)
        paths = {e['asset'] for e in targets}
        assert len(paths) == EXPECTED_SEQUENCE_COUNT
        immutable_paths = [PLAN, AUTHOR, TASK / 'Authoring/ApesCurrentMaterialBindingRevision/Applied.json',
            TASK / 'Authoring/ContentRebaseRevision.json', TASK / 'Authoring/ContentRebaseRevision/IntakePlan.json',
            TASK / 'Authoring/ContentRebaseRevision/IntakeApplied.json',
            WORK / 'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json',
            WORK / 'Saved/ImportReports/MonsterVFX_20261008/Authoring/PrivateAuthoring.json',
            WORK / 'Saved/ImportReports/MonsterVFX_20261008/Authoring/ApesCurrentMaterialBindingRevision.json']
        assert all(p.is_file() for p in immutable_paths)
        immutable_hashes = {str(p): sha(p) for p in immutable_paths}
        assert immutable_hashes[str(immutable_paths[6])] == sha(PLAN) and immutable_hashes[str(immutable_paths[7])] == sha(AUTHOR)
        for p, expected in plan['source_inputs'].items():
            assert sha(p) == expected, 'Original prepared source input differs: ' + p
            immutable_hashes[p] = expected
        helper_inputs = {str(MAIN / ('Scripts/Art/' + name)): sha(MAIN / ('Scripts/Art/' + name)) for name in
            ('player_attack_vfx_author.py', 'monster_vfx_author_20261008.py', 'prepare_monster_vfx_plan_20261008.py')}
        immutable_hashes.update(helper_inputs)
        report.update(original_author_sha256=sha(AUTHOR), original_plan_sha256=sha(PLAN),
            immutable_report_sha256=immutable_hashes, script_sha256=sha(__file__),
            target_event_ids_sha256=EXPECTED_IDS_SHA256, expected43=EXPECTED_COUNT,
            expected_sequence_count=EXPECTED_SEQUENCE_COUNT, loaded_native_module=loaded_module())
        expected = {j['path']: j['saved_sha256'] for j in author['mutation_journal']}
        rebase = read(TASK / 'Authoring/ContentRebaseRevision.json')
        assert rebase['status'] == 'passed' and rebase['mode'] == 'apply' and rebase['author_before_sha256'] == sha(AUTHOR)
        assert rebase['original_author_journal_preserved'] and rebase['untouched493_sha_preserved']
        for row in rebase['rows']:
            expected[row['definition']] = row['merged_after_sha256']
        assert len(expected) == 499
        before_hashes = {p: sha(package_file(p)) for p in expected}
        assert before_hashes == expected, 'Selected499 current bytes differ from immutable author + explicit Definition rebase'
        report['selected499_before_sha256'] = before_hashes
        report['source_absent_field_evidence43'] = [source_evidence(e) for e in targets]
        h = readonly_helpers()
        state_class = unreal.load_class(None, '/Script/Khazan.KZAnimNotifyState_MonsterVisual')
        effect_class = unreal.load_class(None, '/Script/Khazan.KZAnimNotify_CombatEffect')
        assert state_class and effect_class
        sequence_records = {r['path']: r for r in author['sequences']}
        records = {r['event_id']: r for r in author['events']}
        groups = defaultdict(list)
        for e in targets:
            groups[e['asset']].append(e)
        loaded, prepared, before_exports = {}, [], {}
        for path in sorted(paths):
            asset = unreal.load_asset(path)
            assert isinstance(asset, unreal.AnimSequence)
            record = sequence_records[path]
            assert before_hashes[path] == record['after_sha256']
            assert h['verify_preserved'](asset, record['before']) == record['after']
            loaded[path] = asset
            before_exports[path] = export_text(h, asset, OUT / 'BeforeExports' / (record['relative'] + '.t3d'))
            all_events = {h['guid'](v.export_text()): v for v in h['state_events'](asset)}
            for e in groups[path]:
                r = records[e['event_id']]
                assert r['asset'] == path and r['effect_fields'] == e['effect_fields'] and r['state_fields'] == e['state_fields']
                actual = all_events[r['guid']]
                state = actual.get_editor_property('notify_state_class')
                assert state and state.get_class() == state_class
                effect = state.get_editor_property('Effect')
                assert effect and effect.get_class() == effect_class and effect.get_outer() == state
                assert h['data_fields'](state, r['state_fields']) == r['state_readback']
                assert h['data_fields'](effect, r['effect_fields']) == r['effect_readback']
                assert effect.get_editor_property('bOnAttackSuccessed') is True
                prepared.append((e, r, actual, state, effect))
        assert len(prepared) == EXPECTED_COUNT and len({effect.get_path_name() for _, _, _, _, effect in prepared}) == EXPECTED_COUNT
        # The loaded objects stay untouched in probe; test the exact reflected bool on a transient object.
        transient = unreal.new_object(effect_class)
        transient.set_editor_property('bOnAttackSuccessed', True, unreal.PropertyAccessChangeNotifyMode.NEVER)
        transient.set_editor_property('bOnAttackSuccessed', False, unreal.PropertyAccessChangeNotifyMode.NEVER)
        assert transient.get_editor_property('bOnAttackSuccessed') is False
        assert {p: sha(package_file(p)) for p in expected} == before_hashes
        assert all(sha(p) == value for p, value in immutable_hashes.items())
        if MODE == 'probe':
            report.update(status='passed', transient_only_probe=True, target_events=EXPECTED_COUNT,
                target_sequences=sorted(paths), original_reports_unchanged=True, all499_bytes_unchanged=True)
            write(OUT / 'Probe.json', report)
        else:
            probe_path = OUT / 'Probe.json'
            probe = read(probe_path)
            assert probe['status'] == 'passed' and probe['mode'] == 'probe' and probe['transient_only_probe']
            assert probe['script_sha256'] == sha(__file__) and probe['selected499_before_sha256'] == before_hashes
            assert probe['immutable_report_sha256'] == immutable_hashes
            assert probe['loaded_native_module']['sha256'] == report['loaded_native_module']['sha256']
            report['probe_sha256'] = sha(probe_path)
            for path in sorted(paths):
                immutable_backup(package_file(path, True), OUT / 'BeforeAssets' / sequence_records[path]['relative'], before_hashes[path])
            write(OUT / 'ApplyProgress.json', report)
            for e, r, actual, state, effect in prepared:
                before_fields = copy.deepcopy(r['effect_fields'])
                after_fields = dict(before_fields, bOnAttackSuccessed=False)
                before_readback = h['data_fields'](effect, before_fields)
                timing = h['actual_event'](actual)
                state_readback = h['data_fields'](state, r['state_fields'])
                loaded[e['asset']].modify()
                effect.modify()
                effect.set_editor_property('bOnAttackSuccessed', False, unreal.PropertyAccessChangeNotifyMode.NEVER)
                after_readback = h['data_fields'](effect, after_fields)
                assert after_readback == dict(before_readback, bOnAttackSuccessed=False)
                assert h['actual_event'](actual) == timing and h['data_fields'](state, r['state_fields']) == state_readback
                report['events'].append({'event_id': e['event_id'], 'guid': r['guid'], 'asset': e['asset'],
                    'effect_path': effect.get_path_name(), 'before_effect_fields': before_fields, 'after_effect_fields': after_fields,
                    'before_effect_readback': before_readback, 'after_effect_readback': after_readback,
                    'state_fields': copy.deepcopy(r['state_fields']), 'before_state_readback': state_readback,
                    'after_state_readback': h['data_fields'](state, r['state_fields']),
                    'before_notify_event_readback': timing, 'after_notify_event_readback': h['actual_event'](actual),
                    'before_effect_field': {'bOnAttackSuccessed': True}, 'after_effect_field': {'bOnAttackSuccessed': False},
                    'all_other_effect_fields_unchanged': True, 'state_fields_timing_guid_unchanged': True})
                report['asset_mutations'] += 1
            for path in sorted(paths):
                asset = loaded[path]
                record = sequence_records[path]
                assert h['verify_preserved'](asset, record['before']) == record['after']
                after_text = export_text(h, asset, OUT / 'AfterExports' / (record['relative'] + '.t3d'))
                comparison = exact_bool_only_export_diff(before_exports[path], after_text, len(groups[path]))
                # Guard every selected package and immutable input before each save.
                changed = {s['asset']: s['after_sha256'] for s in report['sequences']}
                assert all(sha(package_file(p)) == changed.get(p, prior) for p, prior in before_hashes.items())
                assert all(sha(p) == value for p, value in immutable_hashes.items())
                assert unreal.EditorAssetLibrary.save_loaded_asset(asset, False)
                report['package_saves'] += 1
                report['asset_saves'] += 1
                post_text = export_text(h, asset, OUT / 'AfterSavedExports' / (record['relative'] + '.t3d'))
                assert post_text == after_text, 'Save changed serialized properties beyond exact guard policy'
                assert h['verify_preserved'](asset, record['before']) == record['after']
                report['sequences'].append({'asset': path, 'path': path, 'relative': record['relative'],
                    'prior_private_sha256': before_hashes[path], 'after_sha256': sha(package_file(path)),
                    'backup_path': str(OUT / 'BeforeAssets' / record['relative']), 'backup_sha256': before_hashes[path],
                    'before_export_path': str(OUT / 'BeforeExports' / (record['relative'] + '.t3d')),
                    'after_export_path': str(OUT / 'AfterExports' / (record['relative'] + '.t3d')),
                    'after_saved_export_path': str(OUT / 'AfterSavedExports' / (record['relative'] + '.t3d')),
                    'before_export_sha256': sha(OUT / 'BeforeExports' / (record['relative'] + '.t3d')),
                    'after_export_sha256': sha(OUT / 'AfterExports' / (record['relative'] + '.t3d')),
                    'after_saved_export_sha256': sha(OUT / 'AfterSavedExports' / (record['relative'] + '.t3d')),
                    'raw_pose_curves_settings_notifies_unchanged': True, 'other_state_fields_preserved': True,
                    'exact_guard_only_serialized_diff': comparison, 'revised_effect_count': len(groups[path])})
                write(OUT / 'ApplyProgress.json', report)
            after_hashes = {p: sha(package_file(p)) for p in expected}
            assert all(after_hashes[p] == value for p, value in before_hashes.items() if p not in paths)
            assert all(after_hashes[s['asset']] == s['after_sha256'] for s in report['sequences'])
            assert all(sha(p) == value for p, value in immutable_hashes.items())
            assert len(report['events']) == report['asset_mutations'] == EXPECTED_COUNT
            assert len(report['sequences']) == report['package_saves'] == EXPECTED_SEQUENCE_COUNT
            report.update(status='passed', selected499_after_sha256=after_hashes,
                other_author_assets_unchanged=True, unchanged_author_asset_count=499 - EXPECTED_SEQUENCE_COUNT,
                original_reports_unchanged=True, original_author_journal_preserved=True,
                only43_subobject_bool_changes=True, fresh_saved_audit_required=True)
            write(OUT / 'Applied.json', report)
            write(FINAL, report)
            write(WORK / 'Saved/ImportReports/MonsterVFX_20261008/Authoring/VictimDecalPolicyRevision.json', report)
        print('KZ_MONSTER_VFX_VICTIM_DECAL_' + report['status'].upper(), flush=True)
    except Exception:
        report['status'] = 'failed'
        report['error'] = traceback.format_exc()
        report['current_selected_sha256'] = {p: sha(package_file(p)) for p in before_hashes}
        report['retry_contract'] = 'No automatic retry/rollback. Close only owned process unsaved. Root must compare current exact26 package SHA against Failed/ApplyProgress and verified BeforeAssets, then CAS-restore only confirmed changed targets if necessary. Never rewrite Plan/PrivateAuthoring/ApesApplied/ContentRebase or original Main-before journal.'
        write(OUT / ('Failed_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json'), report)
        unreal.log_error(report['error'])
        print('KZ_MONSTER_VFX_VICTIM_DECAL_FAILED', flush=True)
        raise


if __name__ == '__main__':
    main()
