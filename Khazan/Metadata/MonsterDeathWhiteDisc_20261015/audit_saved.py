"""Targeted read-only audit of stored death clips and their remaining floor effects."""
import hashlib
import json
import traceback
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT = ROOT / 'Metadata/MonsterDeathWhiteDisc_20261015'
OUT.mkdir(parents=True, exist_ok=True)
PLAN = json.loads((ROOT / 'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json').read_text(encoding='utf-8-sig'))


def path(value):
    return value.get_path_name() if value else None


def sha(asset):
    file = ROOT / 'Content' / (asset.split('.')[0].removeprefix('/Game/') + '.uasset')
    return hashlib.sha256(file.read_bytes()).hexdigest()


def export(asset, filename):
    task = u.AssetExportTask()
    task.object = asset
    task.filename = str(OUT / filename)
    task.exporter = u.ObjectExporterT3D()
    task.automated = True
    task.prompt = False
    assert u.Exporter.run_asset_export_task(task)
    return filename


report = {'status': 'running', 'project': str(ROOT), 'saved_packages': 0, 'families': [], 'clips': [], 'materials': []}
try:
    refs = set()
    for recipe in PLAN['death_presentations']:
        cls = u.EditorAssetLibrary.load_blueprint_class('/Game/Bluprints/Monsters/BP_Monster_' + recipe['family'])
        assert cls
        default = u.get_default_object(cls)
        report['families'].append({'family': recipe['family'], 'montage': recipe['montage'],
                                   'source_sequence': recipe['source_sequence'],
                                   'blood': path(default.get_editor_property('HitBloodEffect')),
                                   'blood_decal': path(default.get_editor_property('HitBloodDecalMaterial')),
                                   'ash': path(default.get_editor_property('DeathAshEffect'))})
    groups = {}
    for row in PLAN['events']:
        if row['category'] == 'Death':
            groups[row['asset']] = row['family']
    for asset_path, family in sorted(groups.items()):
        asset = u.load_asset(asset_path)
        assert isinstance(asset, u.AnimSequence)
        record = {'asset': asset_path, 'family': family, 'sha256': sha(asset_path), 'seconds': asset.get_play_length(), 'events': []}
        for event in u.AnimationLibrary.get_animation_notify_events(asset):
            state = event.get_editor_property('notify_state_class')
            if not isinstance(state, u.KZAnimNotifyState_MonsterVisual):
                continue
            effect = state.get_editor_property('Effect')
            if not effect:
                continue
            decal = effect.get_editor_property('DecalMaterial')
            value = {'state': path(state), 'effect': path(effect), 'event_id': str(effect.get_editor_property('EventId')),
                     'source_package': effect.get_editor_property('SourcePackage'),
                     'time': u.AnimationLibrary.get_anim_notify_event_trigger_time(event),
                     'duration': u.AnimationLibrary.get_anim_notify_event_duration(event),
                     'particle': path(effect.get_editor_property('ParticleTemplate')), 'decal': path(decal),
                     'decal_size': str(effect.get_editor_property('DecalSize')),
                     'decal_life': effect.get_editor_property('DecalLifeSpan'),
                     'attached': effect.get_editor_property('bAttached'),
                     'floor': effect.get_editor_property('bSpawnOnFloor'), 'surface_routes': []}
            if decal:
                refs.add(decal.get_path_name())
            for route in effect.get_editor_property('SurfaceRoutes'):
                material = route.get_editor_property('DecalMaterial')
                if material:
                    refs.add(material.get_path_name())
                value['surface_routes'].append({'surface_raw': route.export_text(),
                                                'particle': path(route.get_editor_property('ParticleTemplate')),
                                                'decal': path(material),
                                                'suppress_decal': route.get_editor_property('bSuppressDecal')})
            record['events'].append(value)
        report['clips'].append(record)
    for index, reference in enumerate(sorted(refs)):
        material = u.load_asset(reference)
        chain = []
        while isinstance(material, u.MaterialInstanceConstant):
            chain.append(path(material))
            export(material, 'Material_%02d_%s.t3d' % (index, material.get_name()))
            material = material.get_editor_property('parent')
        assert isinstance(material, u.Material)
        chain.append(path(material))
        report['materials'].append({'reference': reference, 'chain': chain,
                                    'base_graph': export(material, 'Base_%02d_%s.t3d' % (index, material.get_name())),
                                    'domain': str(material.get_editor_property('material_domain')),
                                    'blend': str(material.get_editor_property('blend_mode'))})
    for clip in report['clips']:
        assert sha(clip['asset']) == clip['sha256'], clip['asset']
    report['status'] = 'passed'
except Exception:
    report['status'] = 'failed'
    report['error'] = traceback.format_exc()
    u.log_error(report['error'])
(OUT / 'SavedAudit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
if report['status'] != 'passed':
    raise RuntimeError(report['error'])
print('KZ_DEATH_FLOOR_SAVED_AUDIT_PASSED', len(report['clips']), len(report['materials']), flush=True)
