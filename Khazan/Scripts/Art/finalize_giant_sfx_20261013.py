"""Bind the current Main giant SFX repair to saved assets and actual audio RHI."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Metadata/GiantSFX_20261013'
read = lambda path: json.loads((OUT / path).read_text(encoding='utf-8-sig'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()

repair = read('MainGiantAudioRepair01/GiantAudioBindingRepair.json')
audit = read('MainGiantSavedAuditFinal/GiantSFXAudit.json')
runtime = read('FinalMainAudioRHI01/Driver.json')
ballista = read('BallistaInteractionRHI01/Driver.json')
manifest = json.loads((ROOT / 'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
module = ROOT / 'Binaries/Win64' / manifest['Modules']['Khazan']
runtime_log = (OUT / 'FinalMainAudioRHI01/Editor.log').read_text(encoding='utf-8', errors='replace')
loaded_module_line = next((line for line in runtime_log.splitlines()
                           if "InternalLoadLibrary: 'Khazan'" in line and module.as_posix() in line), None)
assert loaded_module_line, 'Final audio PIE did not load the current Main Khazan DLL'
assert repair['success'] and audit['success'] and not audit['errors']
assert runtime['status'] == 'passed' and ballista['status'] == 'passed'
assert len(runtime['family_captures']) == 26 and len(runtime['projectile_captures']) == 2
assert not runtime['audio_errors'] and not ballista['audio_errors']
assert all(row['peak'] > 0 and row['clipped_samples'] == 0
           for row in runtime['family_captures'] + runtime['projectile_captures'] + ballista['family_captures'])
assert runtime['output']['clipped_samples'] == ballista['output']['clipped_samples'] == 0
assert sum(row['source_events'] for row in audit['families'].values()) == 701
assert sum(row['matched_events'] for row in audit['families'].values()) == 701
assert all(row['missing_events'] == row['wrong_cues'] == row['extra_events'] ==
           row['null_sounds'] == row['time_shifts'] == 0 for row in audit['families'].values())
assert all(row['guards'] == row['windows'] and row['object_guards'] == row['objects']
           and row['projectile_sounds'] == 1 and not row['issues'] for row in audit['combos'])
assert all(row['issue'] is None for row in audit['definitions'])
for row in repair['packages']:
    asset_file = ROOT / 'Content' / (row['asset'].removeprefix('/Game/') + '.uasset')
    assert asset_file.is_file() and sha(asset_file) == row['after_sha256']
    assert row['non_audio_struct_fields_equal'] and Path(row['backup']).is_file()

report = {
    'status': 'current_main_binding_repaired_and_targeted_runtime_passed',
    'date_kst': '2026-10-13',
    'scope': {'giant_families': ['ApesStoneHandElite', 'Yetuga'],
              'source_events': 701, 'source_sequences': 212,
              'attack_windows_with_guard_sound': 294,
              'pattern_objects_with_guard_sound': 4,
              'fastball_flight_sounds': 2,
              'recipient_impact_definitions': 2},
    'changes': {
        'main_packages': [{k: row[k] for k in ('asset', 'before_sha256', 'after_sha256',
                                               'backup', 'windows_changed', 'objects_changed',
                                               'projectiles_changed', 'non_audio_struct_fields_equal')}
                          for row in repair['packages']],
        'runtime_gameplay_code_changed': False,
        'qa_change': 'Existing Khazan.Audio.PIE sample plan may select a saved montage and section.',
        'numeric_provenance': 'Source cue bindings; no new gameplay timing/gain values. Existing source retime under one 60 Hz frame preserved.'},
    'verification': {
        'saved_audit': 'MainGiantSavedAuditFinal/GiantSFXAudit.json',
        'saved_packages_written_by_audit': audit['saved_packages'],
        'families': audit['families'],
        'combos': audit['combos'],
        'recipient_impact': audit['definitions'],
        'runtime': 'FinalMainAudioRHI01/Driver.json',
        'runtime_samples': len(runtime['family_captures']),
        'runtime_giant_samples': 22,
        'runtime_player_samples': 4,
        'runtime_cancel_samples': 2,
        'runtime_projectile_samples': len(runtime['projectile_captures']),
        'runtime_mixed_peak': runtime['output']['peak'],
        'runtime_mixed_clipped_samples': runtime['output']['clipped_samples'],
        'ballista_animation_audio': 'BallistaInteractionRHI01/Driver.json',
        'ballista_clip_peak': ballista['family_captures'][0]['peak'],
        'main_module': str(module), 'main_module_sha256': sha(module),
        'loaded_module_log': loaded_module_line,
        'native_completion': runtime['native_completion']},
    'source_content_exception': {
        'asset': '/Game/Monsters/ApesStoneHandElite/Animations/InGame/Idle/Locomotion_Stand_F_Original_Variant02',
        'finding': 'Apes idle uses the original shared Yetuga Stand_F sequence and its Yetuga foley/voice events.',
        'source_proof': 'Saved/ImportReports/GameplayAudio_20261011/AudioAuthoringPlan01.json; source_package BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster/Yetuga/Ani/CA_M_Yetuga_Stand_F',
        'changed': False},
    'limits': [
        'Readback covers all 701 planned giant events, but RHI directly samples 22 giant cases rather than every action and transition.',
        'A synthetic dynamic-montage fixture can skip audio inside its first update; current saved giant pattern montages passed the same early dodge, turn and guard-reaction cues. Do not generalize dynamic-montage failures to the saved pattern path.',
        'The Ballista animation cue is authored and was manually played in PIE; no world Ballista interaction owner/call path was found in current Source, so actual object use is not verified.',
        'Original Wwise DSP, global RTPC, simultaneous voice budget and all frame-by-frame perceptual parity are not established.'
    ],
    'previous_humanoid_player_scope': 'Metadata/HumanoidSFX_20261013/FinalVerification.json'
}
(OUT / 'FinalVerification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'status': report['status'], 'runtime': runtime['status'], 'ballista': ballista['status']}))
