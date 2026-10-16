"""Read the saved Main montage afresh, then run its real WeakAttack02 PIE path."""
from pathlib import Path
import hashlib
import json
import os
import unreal as u

root = Path(u.Paths.project_dir()).resolve()
out = Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
target = root / 'Content/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAttackCombo.uasset'
apply_report = json.loads((root / 'Metadata/CombatVFXSequencer_20261013/MainApply01/MainApplyReport.json').read_text(encoding='utf-8'))
assert apply_report['status'] == 'passed'
sha = hashlib.sha256(target.read_bytes()).hexdigest()
assert sha == apply_report['after_sha256'], 'Main montage changed since the saved apply.'
montage = u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/WeakAttack/AM_DAS_WeakAttackCombo')
effect_id = apply_report['effect_id']
managed = []
for event in u.AnimationLibrary.get_animation_notify_events(montage):
    parent = event.get_editor_property('Notify')
    if not isinstance(parent, u.KZAnimNotify_CombatEffect):
        continue
    for data in [parent] + list(parent.get_editor_property('BatchedEffects')):
        if str(data.get_editor_property('EventId')) == effect_id:
            managed.append(data)
assert len(managed) == 2, 'Expected one saved begin/end pair.'
assert sorted(bool(d.get_editor_property('bEndEvent')) for d in managed) == [False, True]
assert all(d.get_editor_property('bUseSequencerTransform') for d in managed)
assert all(d.get_editor_property('NiagaraTemplate').get_path_name() == '/Game/VFX/01_ARPGEssentials/KZ_Slash.KZ_Slash' for d in managed)
(out / 'FreshSavedReadback.json').write_text(json.dumps({
    'montage_sha256': sha, 'effect_id': effect_id, 'begin_end': 2,
    'sequencer_enabled': True, 'start': managed[0].get_editor_property('WindowStartTime'),
    'end': managed[0].get_editor_property('WindowEndTime')}, indent=2), encoding='utf-8')

source = (root / 'Scripts/Engineering/weak_attack02_slash_driver_20261013.py').read_text(encoding='utf-8')
exec(compile(source, __file__, 'exec'), globals())
