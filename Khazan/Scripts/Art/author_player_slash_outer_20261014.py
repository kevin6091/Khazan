"""Tune only the 33 existing KZ_Slash start/end pairs in the isolated work copy."""
from pathlib import Path
import difflib
import hashlib
import json
import os
import unreal as u

root = Path(u.Paths.project_dir()).resolve()
main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
assert root == main.parent.parent/'Khazan_PlayerSlashOuterWork_20261014'/'Khazan'
out = Path(os.environ['KZ_SLASH_OUT'])
out.mkdir(parents=True, exist_ok=True)
baseline = json.loads((main/'Metadata/PlayerSlashOuter_20261014/WorkPreparation.json').read_text(encoding='utf-8'))

# TEMP visual tuning in cm/scale, chosen from 2026-10-14 actual pair captures,
# not claimed as original game metadata. Explicit sides prevent first-frame
# auto selection from binding two simultaneous rings to the same weapon.
# The existing Weak02 Sequencer curves already place its ring outside the sword.
plan = {
    '9c0b9461': ('R',25,1.15), 'b7016da5': (None,0,1.0),
    'b135cc89': ('L',40,1.15), '915c6f4d': ('R',35,1.15),
    '6b2e7f2c': ('L',35,1.12), 'dedc9321': ('R',35,1.12),
    '460fe1a9': ('R',45,1.15), '18d5bbdd': ('L',40,1.15),
    'fee2ad76': ('L',40,1.15), 'c971641d': ('R',35,1.15),
    '65db62c9': ('R',40,1.15), 'bb7e8f48': ('L',40,1.15),
    '1d10900d': ('L',30,1.12), '414d0adf': ('R',30,1.12),
    'afd862cd': ('R',60,1.18), '64dc435c': ('R',55,1.18),
    'dd09a312': ('R',60,1.18), '9b5b4c7e': ('L',50,1.18),
    '8ea9a2c2': ('R',50,1.18), '6be2633d': ('L',45,1.15),
    '3e0c947b': ('L',45,1.15), '83a227dc': ('R',50,1.15),
    '56eadfc0': ('L',50,1.15),
    '04e5b308': ('L',40,1.15), '734a3def': ('R',45,1.15),
    'dae9f2f4': ('R',55,1.15), '77f06cdd': ('L',50,1.15),
    'c85f84be': ('L',45,1.15), '9c4fa693': ('L',45,1.15),
    '1e4b39e6': ('L',45,1.15), 'a788e865': ('L',50,1.15),
    'df5d8525': ('L',50,1.15), 'a6066b61': ('L',65,1.15),
}
assert len(plan) == 33

def export(asset, filename):
    task = u.AssetExportTask()
    task.object = asset
    task.filename = str(filename)
    task.exporter = u.ObjectExporterT3D()
    task.automated = True
    task.prompt = False
    assert u.Exporter.run_asset_export_task(task)
    return filename.read_text(encoding='utf-8-sig')

rows = []
seen = set()
for rel, digest in baseline['targets'].items():
    package = '/Game/'+Path(rel).relative_to('Content').with_suffix('').as_posix()
    file = root/rel
    assert hashlib.sha256(file.read_bytes()).hexdigest() == digest, rel
    asset = u.load_asset(package)
    assert asset, package
    name = Path(rel).stem
    before = export(asset, out/f'{name}_Before.t3d')
    clock = [e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(asset)]
    original = set()
    changed = []
    for event in u.AnimationLibrary.get_animation_notify_events(asset):
        parent = event.get_editor_property('Notify')
        if not isinstance(parent,u.KZAnimNotify_CombatEffect):
            continue
        for obj in [parent]+list(parent.get_editor_property('BatchedEffects')):
            event_id = str(obj.get_editor_property('EventId'))
            if not event_id.startswith('KZWeaponSlash_'):
                original.add(obj.get_path_name())
                continue
            suffix = event_id[-8:]
            assert suffix in plan, (package,event_id)
            side,extension,scale = plan[suffix]
            if side is None:
                # This one is authored with a full montage-time Sequencer curve.
                assert obj.get_editor_property('bUseSequencerTransform')
                continue
            near = 'FX_L_Axe_02' if side=='L' else 'FX_R_Sword_02'
            tip = 'FX_L_Axe_01' if side=='L' else 'FX_R_Sword_01'
            obj.set_editor_property('WeaponEdgeNearSocket',near)
            obj.set_editor_property('WeaponEdgeTipSocket',tip)
            obj.set_editor_property('WeaponSlashOutwardOffsetCm',float(extension))
            old_scale = obj.get_editor_property('Scale3D')
            obj.set_editor_property('Scale3D',u.Vector(scale,scale,old_scale.z))
            key = (event_id,bool(obj.get_editor_property('bEndEvent')))
            assert key not in seen,key
            seen.add(key)
            changed.append({'id':event_id,'end':key[1],'side':side,
                            'outward_cm':extension,'xy_scale':scale})
    assert clock == [e.export_text() for e in u.AnimationLibrary.get_animation_notify_events(asset)]
    original_count = len(original)
    for event in u.AnimationLibrary.get_animation_notify_events(asset):
        parent = event.get_editor_property('Notify')
        if isinstance(parent,u.KZAnimNotify_CombatEffect):
            for obj in [parent]+list(parent.get_editor_property('BatchedEffects')):
                path = obj.get_path_name()
                if path in original:
                    original.remove(path)
    assert not original, (package,original)
    after = export(asset, out/f'{name}_After.t3d')
    diff = list(difflib.unified_diff(before.splitlines(),after.splitlines(),lineterm=''))
    allowed = ('WeaponEdgeNearSocket=','WeaponEdgeTipSocket=',
               'WeaponSlashOutwardOffsetCm=','Scale3D=')
    content = [line[1:].strip() for line in diff if line.startswith(('+','-')) and not line.startswith(('+++','---'))]
    assert all(line.startswith(allowed) for line in content),(package,content)
    (out/f'{name}_Changes.patch').write_text('\n'.join(diff),encoding='utf-8')
    assert u.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False)
    rows.append({'asset':package,'file':rel,'changed_objects':len(changed),
                 'changes':changed,'before_sha256':digest,
                 'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                 'original_effect_objects_preserved':original_count,
                 'event_clock_guid_preserved':True,
                 'serialized_changes_limited_to':list(allowed)})

assert len(seen)==64, len(seen)  # 32 tuned pairs; Weak02 remains Sequencer-owned.
report={'status':'isolated_candidate_saved','values_source':'TEMP visual placement from task-owned actual RHI; no original numeric claim',
        'rows':rows,'changed_start_end_objects':len(seen),'untouched_sequencer_pair':'b7016da5',
        'new_runtime_classes':0,'original_effects_preserved':sum(r['original_effect_objects_preserved'] for r in rows)}
(out/'Author.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('SLASH_OUTER_CANDIDATE_AUTHORED',len(seen),len(rows))
