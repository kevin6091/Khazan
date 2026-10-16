"""Apply the saved, unadjusted WeakAttack02 sequence to the current Main montage."""
from pathlib import Path
import hashlib
import json
import os
import time
import traceback
import unreal as u
import kz_combat_vfx_sequencer as tool

ROOT = Path(u.Paths.project_dir()).resolve()
OUT = Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
MONTAGE_FILE = ROOT / 'Content/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAttackCombo.uasset'
BACKUP = ROOT / 'Metadata/CombatVFXSequencer_20261013/MainApplyBackup/AM_DAS_WeakAttackCombo.Before.uasset'
REFERENCE = ROOT / 'Metadata/CombatVFXSequencer_20261013/EditorVisualFinal01/Edits.json'
report = {'status': 'running', 'target': str(MONTAGE_FILE), 'reference': str(REFERENCE)}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_montage(montage, name):
    task = u.AssetExportTask()
    task.object = montage
    task.filename = str(OUT / name)
    task.exporter = u.ObjectExporterT3D()
    task.automated = True
    task.prompt = False
    assert u.Exporter.run_asset_export_task(task), name


def same_default(actual, expected):
    assert actual['managed_ids'] == expected['managed_ids']
    assert len(actual['effects']) == len(expected['effects']) == 1
    for effect, baseline in zip(actual['effects'], expected['effects']):
        assert effect['id'] == baseline['id'] and effect['system'] == baseline['system']
        assert effect['drain'] == baseline['drain']
        assert abs(effect['start'] - baseline['start']) < .001
        assert abs(effect['end'] - baseline['end']) < .001
        assert len(effect['keys']) == len(baseline['keys']) == 115
        for key, prior in zip(effect['keys'], baseline['keys']):
            assert abs(key['time'] - prior['time']) < .001
            for field, limit in [('location', .02), ('rotation', .03), ('scale', .001)]:
                assert all(abs(a - b) < limit for a, b in zip(key[field], prior[field])), field


def apply():
    assert MONTAGE_FILE.exists() and BACKUP.exists() and REFERENCE.exists()
    report['before_sha256'] = digest(MONTAGE_FILE)
    assert report['before_sha256'] == digest(BACKUP), 'Main montage changed after backup; abort without saving.'
    sequence = tool.open_weak02()
    manifest, current = tool.collect_edits(sequence)
    same_default(current, json.loads(REFERENCE.read_text(encoding='utf-8')))
    report['default_verified'] = True
    montage = u.load_asset(manifest['montage'])
    export_montage(montage, 'MontageBefore.t3d')
    applied = tool.apply_current()
    same_default(applied, current)
    export_montage(montage, 'MontageAfter.t3d')
    report['after_sha256'] = digest(MONTAGE_FILE)
    assert report['after_sha256'] != report['before_sha256'], 'Apply did not save the montage.'
    report['effect_id'] = applied['effects'][0]['id']
    report['baked_keys'] = len(applied['effects'][0]['keys'])
    report['status'] = 'passed'


started = time.monotonic()
ran = False
busy = False


def tick(delta):
    global ran, started, busy
    if busy or time.monotonic() - started < 8:
        return
    if not ran:
        ran = True
        busy = True
        try:
            apply()
        except Exception:
            report['status'] = 'failed'
            report['error'] = traceback.format_exc()
            u.log_error(report['error'])
        finally:
            (OUT / 'MainApplyReport.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
            busy = False
            started = time.monotonic()
        return
    u.unregister_slate_post_tick_callback(handle)
    u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
    u.SystemLibrary.quit_editor()


handle = u.register_slate_post_tick_callback(tick)
