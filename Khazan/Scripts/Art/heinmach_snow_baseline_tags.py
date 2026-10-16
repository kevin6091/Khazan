"""Read a disposable copy of the unchanged main map to distinguish existing tags."""
from pathlib import Path
import hashlib
import json
import shutil
import unreal
ROOT=Path(unreal.Paths.project_dir()).resolve()
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
U=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem);assert not U.get_game_world()
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
source=MAIN/'Content/Maps/L_HeinMach_Environment.umap'
assert hashlib.sha256(source.read_bytes()).hexdigest()=='f236d88889a65c00675ed4e24f1c53a3d17677efd3048ebcaa096443e7685442'
destination=ROOT/'Content/Maps/__SnowReadOnlyBaseline.umap'
shutil.copy2(source,destination)
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
out_dir=MAIN/'Saved/ImportReports/HeinMachSnow_20261006/Resume20261007'
verified={r['label'] for r in json.loads((out_dir/'MicroDressing.json').read_text())['changed']}
extras={a.get_actor_label() for a in E.get_all_level_actors() for c in a.get_components_by_class(unreal.StaticMeshComponent)
        if c.component_has_tag('HeinMachMicroDressing') and a.get_actor_label() not in verified}
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/__SnowReadOnlyBaseline')
parts=[c for a in E.get_all_level_actors() for c in a.get_components_by_class(unreal.StaticMeshComponent)
       if c.component_has_tag('HeinMachMicroDressing')]
report=dict(main_map_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),existing_micro_dressing=len(parts),
    parts=[dict(label=c.get_owner().get_actor_label(),pawn=str(c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN)),
        nav=c.get_editor_property('bCanEverAffectNavigation'),visibility=str(c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY))) for c in parts])
restore={}
for a in E.get_all_level_actors():
    if a.get_actor_label() not in extras:continue
    c=a.get_component_by_class(unreal.StaticMeshComponent)
    restore[a.get_actor_label()]=dict(pawn=c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN),
        nav=c.get_editor_property('bCanEverAffectNavigation'),tags=list(c.component_tags))
assert set(restore)==extras
unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
for a in E.get_all_level_actors():
    if a.get_actor_label() not in restore:continue
    c=a.get_component_by_class(unreal.StaticMeshComponent);r=restore[a.get_actor_label()]
    c.modify();c.set_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN,r['pawn'])
    c.set_editor_property('bCanEverAffectNavigation',r['nav']);c.set_editor_property('component_tags',r['tags'])
report['private_legacy_extras_restored_to_exact_main_collision_and_tags']=[dict(label=k,pawn=str(v['pawn']),nav=v['nav'],tags=[str(t) for t in v['tags']]) for k,v in restore.items()]
assert unreal.EditorLoadingAndSavingUtils.save_map(U.get_editor_world(),'/Game/Maps/L_HeinMach_Environment')
out=MAIN/'Saved/ImportReports/HeinMachSnow_20261006/Resume20261007/MainBaselineMicroDressing.json'
out.write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SNOW_MAIN_BASELINE_TAGS',len(parts),'PRIVATE_EXTRAS_RESTORED',len(restore))
