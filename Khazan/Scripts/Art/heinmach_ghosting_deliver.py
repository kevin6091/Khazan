"""Selectively deliver the verified character mask; authoring happened in isolation."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import unreal

ROOT=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=ROOT/'Saved/ImportReports/HeinMachGhosting_20261008'
REL='Content/_Art/Player/Character/Bluprints/BP_Player.uasset'
ASSET='/Game/_Art/Player/Character/Bluprints/BP_Player'
SOURCE=ROOT/'Saved/ArtStaging/HeinMachGhostingParts_20261008'/REL
BASELINE='ce037c64d7af2e85d61f8e2d7160f7ad615f3fc5be4c159f0bc1d3b585be70f5'
PREPARED='76a65789f117d72913168e4c5f55da1a258f8ae0e6a3466595f8318467f2cfa4'
assert Path(unreal.Paths.project_dir()).resolve()==ROOT and os.getpid()==3528
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
assert read('Parts/authorReport.json')['success'] and read('Parts/auditReport.json')['success']
assert read('CaptureState.json')['success'] and read('VelocityCapture.json')['done'] and not read('VelocityCapture.json')['error']
assert sha(SOURCE)==PREPARED
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
def clean():
    assert editor.get_game_world() is None,'Preserve active PIE'
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages(),'Preserve dirty content'
    assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'Preserve dirty map'
    world=editor.get_editor_world()
    assert world.get_path_name()=='/Game/Maps/L_HeinMach_Environment.L_HeinMach_Environment'
    return world
world=clean()
protected=['Content/Maps/L_HeinMach_Environment.umap','Content/Maps/L_HeinMach_Environment_Contact55_20261007.umap',
 'Source/Khazan/Environment/KZSnowDeformation.cpp','Source/Khazan/Environment/KZSnowDeformation.h',
 'Binaries/Win64/UnrealEditor.modules']
hashes={p:sha(ROOT/p) for p in protected}
selection={a.get_path_name() for a in actors.get_selected_level_actors()}
actor_paths={a.get_path_name() for a in actors.get_all_level_actors()}
bp=unreal.load_asset(ASSET);assert isinstance(bp,unreal.Blueprint)
package=bp.get_outermost();assert package.get_name()==ASSET
assert sha(ROOT/REL)==BASELINE,'Main player asset changed; preserve user changes'
result=dict(success=False,pid=os.getpid(),world=world.get_path_name(),save_or_pie=False,changed_asset=ASSET,protected=hashes)
try:
    clean()
    unreal.EditorLoadingAndSavingUtils.fully_load_packages([package])
    assert sha(ROOT/REL)==BASELINE
    backup=OUT/'Backup'/REL;backup.parent.mkdir(parents=True,exist_ok=True)
    assert not backup.exists() or sha(backup)==BASELINE
    if not backup.exists():shutil.copy2(ROOT/REL,backup)
    temp=(ROOT/REL).with_suffix('.ghosting-delivery.tmp')
    shutil.copy2(SOURCE,temp);assert sha(temp)==PREPARED
    os.replace(temp,ROOT/REL)
    result['disk_delivered']=True
    outcome=unreal.EditorLoadingAndSavingUtils.reload_packages([package],interaction_mode=unreal.ReloadPackagesInteractionMode.ASSUME_NEGATIVE)
    result['reload_return']=str(outcome)
    assert isinstance(outcome,tuple) and outcome[0] and not str(outcome[1]),outcome
    clean()
    loaded=unreal.load_asset(ASSET)
    rows=[]
    ss=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    for handle in ss.k2_gather_subobject_data_for_blueprint(loaded):
        obj=unreal.SubobjectDataBlueprintFunctionLibrary.get_object(unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle))
        if isinstance(obj,unreal.SkeletalMeshComponent):
            row=dict(name=obj.get_name(),custom_depth=obj.get_editor_property('render_custom_depth'),stencil=obj.get_editor_property('custom_depth_stencil_value'))
            rows.append(row)
            assert row['custom_depth'] and row['stencil']==254,row
    assert len(rows)==8,rows
    assert {a.get_path_name() for a in actors.get_all_level_actors()}==actor_paths
    actors.set_selected_level_actors([a for a in actors.get_all_level_actors() if a.get_path_name() in selection])
    assert all(sha(ROOT/p)==s for p,s in hashes.items())
    # Only the current rendering session changes here; persistent project defaults are Config.
    for command in ['r.ScreenPercentage 100','sg.ResolutionQuality 100','r.TSR.Velocity.WeightClampingSampleCount 2']:
        unreal.SystemLibrary.execute_console_command(world,command)
    result.update(success=True,templates=rows,dirty_content=0,dirty_map=0,map_and_snow_source_preserved=True,
      rendering_readback={key:unreal.SystemLibrary.get_console_variable_float_value(key) for key in ['r.ScreenPercentage','sg.AntiAliasingQuality','r.TSR.History.ScreenPercentage','r.TSR.Velocity.WeightClampingSampleCount']})
except Exception as exc:
    result['error']=repr(exc)
    raise
finally:
    result['main_asset_sha256']=sha(ROOT/REL)
    (OUT/'MainDelivery.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
