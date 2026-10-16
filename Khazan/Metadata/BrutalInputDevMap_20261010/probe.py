from pathlib import Path
import json, os, unreal

ROOT=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
OUT=ROOT/'Metadata/BrutalInputDevMap_20261010'
assert Path(unreal.Paths.project_dir()).resolve()==ROOT
report=dict(pid=os.getpid(), success=False)
def path(value): return value.get_path_name() if value else None
def vec(value): return [float(value.x),float(value.y),float(value.z)]
try:
    subsystem=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world=subsystem.get_editor_world()
    assert world.get_path_name().split('.')[0]=='/Game/Maps/DevMap'
    data=unreal.load_asset('/Game/Data/DA_InputData')
    definition=unreal.load_asset('/Game/Data/Character/DA_CharacterDefinition_Player')
    mapping=data.get_editor_property('InputMappingContext')
    report['input_data']=dict(asset=path(data), mapping=path(mapping),
       input_actions=[dict(tag=str(row.get_editor_property('InputTag')),action=path(row.get_editor_property('InputAction'))) for row in data.get_editor_property('InputActions')],
       mappings=[dict(action=path(row.get_editor_property('action')),key=str(row.get_editor_property('key').get_editor_property('key_name'))) for row in mapping.get_editor_property('mappings')])
    report['grants']=[dict(ability=path(row.get_editor_property('AbilityClass')),tag=str(row.get_editor_property('InputTag'))) for row in definition.get_editor_property('InitialAbilityGrants')]
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    report['actors']=[]
    for actor in actors:
        origin,extent=actor.get_actor_bounds(False)
        row=dict(name=actor.get_name(),label=actor.get_actor_label(),class_path=path(actor.get_class()),
                 location=vec(actor.get_actor_location()),scale=vec(actor.get_actor_scale3d()),
                 bounds=dict(origin=vec(origin),extent=vec(extent)))
        if isinstance(actor,unreal.StaticMeshActor):
            component=actor.static_mesh_component
            row.update(mesh=path(component.static_mesh),collision=str(component.get_collision_enabled()))
        if isinstance(actor,unreal.NavMeshBoundsVolume):
            row['boxes']=[dict(name=component.get_name(),extent=vec(component.get_unscaled_box_extent())) for component in actor.get_components_by_class(unreal.BoxComponent)]
        report['actors'].append(row)
    report['monsters']=[]
    for family in ('Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga'):
        cls=unreal.load_class(None,f'/Game/Bluprints/Monsters/BP_Monster_{family}.BP_Monster_{family}_C')
        assert cls, family
        cdo=unreal.get_default_object(cls)
        capsule=cdo.get_component_by_class(unreal.CapsuleComponent)
        mesh=cdo.get_component_by_class(unreal.SkeletalMeshComponent)
        report['monsters'].append(dict(family=family,class_path=path(cls),
             capsule_radius=capsule.get_scaled_capsule_radius(),capsule_half_height=capsule.get_scaled_capsule_half_height(),
             mesh=path(mesh.skeletal_mesh),anim_class=path(mesh.anim_class),mesh_location=vec(mesh.relative_location),
             definition_tag=str(cdo.get_editor_property('CharacterDefinitionAssetName'))))
    report['dirty_content']=[path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    report['dirty_maps']=[path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    report['success']=True
except Exception as error:
    import traceback
    report.update(error=str(error),traceback=traceback.format_exc())
finally:
    (OUT/'Probe02.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    unreal.SystemLibrary.execute_console_command(subsystem.get_editor_world(),'QUIT_EDITOR')
