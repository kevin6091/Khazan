"""Change editor controls in memory, then exercise the real attack and cancellation."""
from pathlib import Path
import os, json, hashlib
import unreal as u
import kz_combat_vfx_sequencer as tool

root = Path(u.Paths.project_dir()).resolve()
out = Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
sequence = tool.open_weak02()
manifest, before = tool.collect_edits(sequence)
binding = next(b for b in sequence.get_bindings() if tool._guid(b) in manifest['bindings'])
track = next(t for t in binding.get_tracks() if isinstance(t, u.MovieScene3DTransformTrack))
section = next(s for s in track.get_sections() if s.get_row_index() == 1)
channels = section.get_all_channels()[:9]
# Test-only visible editor changes, never saved to the production sequence.
changes = {0: 20.0, 4: 7.0, 6: .1, 7: .1, 8: .1}
for axis, value in changes.items():
    for key in list(channels[axis].get_keys()): channels[axis].remove_key(key)
    channels[axis].set_default(value)
    channels[axis].add_key(u.FrameNumber(0), value, interpolation=u.MovieSceneKeyInterpolation.LINEAR)
child = next(b for b in sequence.get_bindings() if tool._guid(b.get_parent()) == tool._guid(binding))
life = next(t for t in child.get_tracks() if isinstance(t, u.MovieSceneNiagaraSystemTrack)).get_sections()[0]
rate = sequence.get_display_rate(); step = rate.denominator / rate.numerator
life.set_range_seconds(life.get_start_frame_seconds() + step, life.get_end_frame_seconds() - step)
life.set_section_end_behavior(u.NiagaraSystemSpawnSectionEndBehavior.DEACTIVATE)
_, edits = tool.collect_edits(sequence)
assert len(edits['effects']) == len(before['effects']) == 1
first, original = edits['effects'][0], before['effects'][0]
assert abs(first['keys'][0]['location'][0] - original['keys'][0]['location'][0] - changes[0]) < .01
assert abs(first['keys'][0]['scale'][0] - original['keys'][0]['scale'][0] - changes[6]) < .01
montage = u.load_asset(manifest['montage'])
task = u.AssetExportTask(); task.object = montage; task.filename = str(out / 'MontageBefore.t3d'); task.exporter = u.ObjectExporterT3D(); task.automated = True; task.prompt = False
assert u.Exporter.run_asset_export_task(task)
invalid = json.loads(json.dumps(edits)); invalid['effects'][0]['end'] = invalid['effects'][0]['start']
assert u.KZAnimNotify_CombatEffect.apply_sequencer_edits(montage, json.dumps(invalid)), 'Invalid interval accepted'
error = u.KZAnimNotify_CombatEffect.apply_sequencer_edits(montage, json.dumps(edits))
assert not error, error
(out / 'ExpectedEdits.json').write_text(json.dumps(edits, indent=2), encoding='utf-8')
(out / 'EditorEditProof.json').write_text(json.dumps({'position_cm': changes[0], 'pitch_degrees': changes[4], 'scale_delta': changes[6], 'clock_shift_seconds': step, 'values_source': 'temporary QA fixture; no production tuning', 'editor_numeric_matches': True, 'invalid_interval_rejected': True, 'production_sequence_saved': False, 'production_montage_saved': False}, indent=2), encoding='utf-8')
task.filename = str(out / 'MontageEdited.t3d'); assert u.Exporter.run_asset_export_task(task)
u.LevelSequenceEditorBlueprintLibrary.close_level_sequence()
source = (root / 'Scripts/Engineering/weak_attack02_slash_driver_20261013.py').read_text(encoding='utf-8')
exec(compile(source, __file__, 'exec'), globals())
