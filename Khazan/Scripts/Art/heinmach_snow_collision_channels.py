"""Preserve the exact main collision channel matrix when creating per-instance Pawn overrides."""
from pathlib import Path
import json
import unreal
ROOT=Path(unreal.Paths.project_dir()).resolve()
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
U=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);assert not U.get_game_world()
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
OUT=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Saved/ImportReports/HeinMachSnow_20261006/Resume20261007')
rows=json.loads((OUT/'MicroDressing.json').read_text())['changed']
baseline=json.loads((OUT/'MainBaselineMicroDressing.json').read_text())
changed={r['label'] for r in rows}
targets=changed|{r['label'] for r in baseline['private_legacy_extras_restored_to_exact_main_collision_and_tags']}
channels={name:getattr(unreal.CollisionChannel,name) for name in dir(unreal.CollisionChannel)
    if name.startswith('ECC_') and name not in ('ECC_MAX','ECC_OVERLAP_ALL_DEPRECATED')}
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/__SnowReadOnlyBaseline')
original={}
for a in E.get_all_level_actors():
    if a.get_actor_label() not in targets:continue
    c=a.get_component_by_class(unreal.StaticMeshComponent)
    original[a.get_actor_label()]={name:c.get_collision_response_to_channel(channel) for name,channel in channels.items()}
assert set(original)==targets
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
def expected(label,name):return unreal.CollisionResponseType.ECR_IGNORE if label in changed and name=='ECC_PAWN' else original[label][name]
for a in E.get_all_level_actors():
    label=a.get_actor_label()
    if label not in targets:continue
    c=a.get_component_by_class(unreal.StaticMeshComponent);c.modify()
    # Seed every response before invalidating the inherited profile. Otherwise
    # custom response serialization can omit inherited values after reload.
    c.set_collision_response_to_all_channels(unreal.CollisionResponseType.ECR_BLOCK)
    for name,channel in channels.items():c.set_collision_response_to_channel(channel,expected(label,name))
assert unreal.EditorLoadingAndSavingUtils.save_map(U.get_editor_world(),'/Game/Maps/L_HeinMach_Environment')
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
for a in E.get_all_level_actors():
    label=a.get_actor_label()
    if label not in targets:continue
    c=a.get_component_by_class(unreal.StaticMeshComponent)
    for name,channel in channels.items():assert c.get_collision_response_to_channel(channel)==expected(label,name),(label,name)
report=dict(success=True,verified_components=len(targets),new_pawn_exclusions=len(changed),
    channels=list(channels),saved_reload=True,original={k:{n:str(v) for n,v in r.items()} for k,r in original.items()},
    scope='Exact main channel responses restored; only the 65 verified micro dressing Pawn responses differ. Existing private 16 extras fully restored.')
(OUT/'CollisionChannelsPreserved.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SNOW_COLLISION_CHANNEL_RELOAD_VERIFIED',len(targets),len(channels))
