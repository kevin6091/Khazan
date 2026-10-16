"""Fill only current Apes/Yetuga result-audio fields; preserve latest gameplay data."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import traceback
import unreal as u

ROOT = Path(os.environ['KZ_AUDIO_MAIN'])
OUT = Path(os.environ['KZ_AUDIO_OUTPUT'])
SOURCE = ROOT / 'Saved/ImportReports/GameplayAudio_20261011'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
lib = u.EditorAssetLibrary
target_paths = ('/Game/Monsters/ApesStoneHandElite/Data/DA_OriginalPatterns_ApesStoneHandElite',
                '/Game/Monsters/Yetuga/Data/DA_OriginalPatterns_Yetuga')
plan = {r['object_id']: r for r in read(SOURCE / 'ProjectileAudioPlan01.json')}
cues = {r['event_package']: r['asset'] for r in read(SOURCE / 'NativeCuePlan01.json')['cues']}
report = {'success': False, 'packages': [], 'errors': []}

def without_audio(text):
    return re.sub(r',?(ImpactSound|GuardSound|ProjectileSound|ProjectileStopFadeSeconds)=[^,)]*', '', text)

try:
    guard = lib.load_asset('/Game/Audio/Original/Events/SC_Play_PLYR_DualAxeSword_Guard_Suc')
    assert guard
    for path in target_paths:
        file = ROOT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
        assert file.exists()
        before_hash = sha(file)
        backup = OUT / 'Before' / file.relative_to(ROOT)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, backup)
        obj = lib.load_asset(path)
        assert obj
        nodes = obj.get_editor_property('nodes')
        objects = obj.get_editor_property('pattern_objects')
        before_nodes = [without_audio(n.export_text()) for n in nodes]
        before_objects = [without_audio(o.export_text()) for o in objects]
        windows_changed = objects_changed = projectiles_changed = 0
        for ni, node in enumerate(nodes):
            windows = node.get_editor_property('attack_windows')
            for wi, window in enumerate(windows):
                if not window.get_editor_property('guard_sound'):
                    window.set_editor_property('guard_sound', guard)
                    windows_changed += 1
                windows[wi] = window
            node.set_editor_property('attack_windows', windows)
            nodes[ni] = node
        for oi, data in enumerate(objects):
            if not data.get_editor_property('guard_sound'):
                data.set_editor_property('guard_sound', guard)
                objects_changed += 1
            source = plan.get(str(data.get_editor_property('id')))
            if source:
                cue = lib.load_asset(cues[source['event']])
                assert cue, source['event']
                if data.get_editor_property('projectile_sound') != cue:
                    data.set_editor_property('projectile_sound', cue)
                    projectiles_changed += 1
                # The source move_stop action has no serialized transition time.
                data.set_editor_property('projectile_stop_fade_seconds', 0.)
            objects[oi] = data
        assert before_nodes == [without_audio(n.export_text()) for n in nodes], path + ' nodes'
        assert before_objects == [without_audio(o.export_text()) for o in objects], path + ' objects'
        assert sha(file) == before_hash, path + ' concurrent save'
        obj.set_editor_property('nodes', nodes)
        obj.set_editor_property('pattern_objects', objects)
        assert lib.save_loaded_asset(obj, only_if_is_dirty=False), path
        after_hash = sha(file)
        report['packages'].append({'asset': path, 'before_sha256': before_hash,
                                   'after_sha256': after_hash, 'backup': str(backup),
                                   'windows_changed': windows_changed,
                                   'objects_changed': objects_changed,
                                   'projectiles_changed': projectiles_changed,
                                   'non_audio_struct_fields_equal': True,
                                   'node_count': len(nodes), 'object_count': len(objects)})
    assert sum(p['windows_changed'] for p in report['packages']) == 294
    assert sum(p['objects_changed'] for p in report['packages']) == 4
    assert sum(p['projectiles_changed'] for p in report['packages']) == 2
    report['success'] = True
except Exception:
    report['errors'].append(traceback.format_exc())
    u.log_error(report['errors'][-1])
(OUT / 'GiantAudioBindingRepair.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
assert report['success'], report['errors']
