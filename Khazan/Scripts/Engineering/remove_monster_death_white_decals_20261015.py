"""Remove only the eight visually isolated erroneous death decal bindings."""
import hashlib
import json
import re
import shutil
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT = ROOT / 'Metadata/MonsterDeathWhiteDisc_20261015'
AUDIT = json.loads((OUT / 'SavedAudit.json').read_text())
ISOLATION = json.loads((OUT / 'IsolationRHI01/RuntimeReport.json').read_text())
assert AUDIT['status'] == ISOLATION['status'] == 'passed'
assert len(ISOLATION['isolations']) == 9
BAD = {
    '/Game/_Art/Effects/Shared/Materials/MonsterHuman/FMI_Decal_Deferred_D_02.FMI_Decal_Deferred_D_02',
    '/Game/_Art/Effects/Shared/Materials/MonsterHuman/MI_Decal_Deferred_D_00.MI_Decal_Deferred_D_00',
}
TARGETS = {clip['asset']: [event for event in clip['events'] if event['decal'] in BAD]
           for clip in AUDIT['clips']}
TARGETS = {asset: events for asset, events in TARGETS.items() if events}
assert len(TARGETS) == 8 and all(len(events) == 1 for events in TARGETS.values())
assert len([item for item in ISOLATION['isolations'] if item['decal']['material'] in BAD]) == 8


def filename(asset):
    return ROOT / 'Content' / (asset.removeprefix('/Game/') + '.uasset')


def sha(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def export(asset, directory):
    file = OUT / directory / (asset.get_path_name().split('.')[0].removeprefix('/Game/') + '.t3d')
    file.parent.mkdir(parents=True, exist_ok=True)
    task = u.AssetExportTask()
    task.object = asset
    task.filename = str(file)
    task.exporter = u.ObjectExporterT3D()
    task.automated = True
    task.prompt = False
    assert u.Exporter.run_asset_export_task(task)
    return file.read_text(encoding='utf-8-sig')


def normalize(text):
    # The only allowed serialized object difference is this material pointer.
    result = []
    for line in text.splitlines():
        if re.match(r'^\s*DecalMaterial=', line) and (line.strip() == 'DecalMaterial=None' or any(material in line for material in BAD)):
            continue
        result.append(line)
    return '\n'.join(result)


def snapshot(asset):
    return {'seconds': asset.get_play_length(),
            'notify_events': [event.export_text() for event in u.AnimationLibrary.get_animation_notify_events(asset)]}


report = {'status': 'running', 'project': str(ROOT), 'source_changes': 0,
          'changed_field': 'UKZAnimNotify_CombatEffect.DecalMaterial', 'saved': [], 'unchanged': []}
try:
    # Preflight every frozen source hash before modifying or saving any asset.
    for clip in AUDIT['clips']:
        assert sha(filename(clip['asset'])) == clip['sha256'], 'Concurrent package edit: ' + clip['asset']
    loaded = []
    for asset_path, expected in TARGETS.items():
        asset = u.load_asset(asset_path)
        assert isinstance(asset, u.AnimSequence)
        match = []
        for event in u.AnimationLibrary.get_animation_notify_events(asset):
            state = event.get_editor_property('notify_state_class')
            if not isinstance(state, u.KZAnimNotifyState_MonsterVisual):
                continue
            effect = state.get_editor_property('Effect')
            if effect and str(effect.get_editor_property('EventId')) == expected[0]['event_id']:
                match.append(effect)
        assert len(match) == 1, asset_path
        effect = match[0]
        assert effect.get_editor_property('DecalMaterial').get_path_name() == expected[0]['decal']
        # No fallback particle, Niagara, trail, route or nested event may be exposed by clearing this binding.
        for field in ('ParticleTemplate', 'NiagaraTemplate', 'TrailMesh', 'TrailMaterial'):
            assert effect.get_editor_property(field) is None, (asset_path, field)
        for field in ('SurfaceRoutes', 'BatchedEffects'):
            assert not effect.get_editor_property(field), (asset_path, field)
        source = filename(asset_path)
        backup = OUT / 'Backup' / source.relative_to(ROOT)
        backup.parent.mkdir(parents=True, exist_ok=True)
        assert not backup.exists(), 'Backup already exists; use saved report for a verified resume'
        shutil.copy2(source, backup)
        assert sha(backup) == sha(source)
        loaded.append((asset_path, asset, effect, expected[0], snapshot(asset), export(asset, 'Before')))
    for asset_path, asset, effect, original, before, before_text in loaded:
        effect.set_editor_property('DecalMaterial', None)
        assert snapshot(asset) == before, 'Notify timing/GUID/object layout changed'
        edited_text = export(asset, 'Edited')
        assert normalize(edited_text) == normalize(before_text), 'Unexpected serialized property change before save: ' + asset_path
        assert u.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False), asset_path
        assert snapshot(asset) == before
        saved_text = export(asset, 'After')
        assert normalize(saved_text) == normalize(before_text), 'Unexpected serialized property change after save: ' + asset_path
        report['saved'].append({'asset': asset_path, 'event_id': original['event_id'],
                                'removed_material': original['decal'], 'source_package': original['source_package'],
                                'original_time': original['time'], 'original_duration': original['duration'],
                                'sha256_before': sha(OUT / 'Backup' / filename(asset_path).relative_to(ROOT)),
                                'sha256_after': sha(filename(asset_path)), 'snapshot': before,
                                'only_decal_material_changed': True})
        (OUT / 'Authoring.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    for clip in AUDIT['clips']:
        if clip['asset'] in TARGETS:
            continue
        assert sha(filename(clip['asset'])) == clip['sha256'], clip['asset']
        report['unchanged'].append(clip['asset'])
    report['status'] = 'passed'
except Exception:
    report['status'] = 'failed'
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
(OUT / 'Authoring.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
if report['status'] != 'passed':
    raise RuntimeError(report['error'])
print('KZ_DEATH_WHITE_DECALS_REMOVED', len(report['saved']), flush=True)
