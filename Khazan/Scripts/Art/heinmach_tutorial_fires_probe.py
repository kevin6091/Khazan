"""Read-only isolated current-map preflight and exact actor preservation baseline."""
from pathlib import Path
import json
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
OUT=Path(__file__).resolve().parents[2] if False else Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Saved/ImportReports/HeinMachTutorialFires_20261006')
sub=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
actors=sub.get_all_level_actors()

def pose(a):
    v=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
    return [v.x,v.y,v.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]

report={'world':unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name(),
        'actor_count':len(actors),'poses':{a.get_actor_label():pose(a) for a in actors},'fixtures':[],'lights':[]}
for a in actors:
    label=a.get_actor_label()
    if any(s in label.lower() for s in ('bonfire','brazier','torch','lamp','candle')):
        c=a.get_component_by_class(unreal.StaticMeshComponent)
        report['fixtures'].append({'label':label,'pose':pose(a),'mesh':c.static_mesh.get_path_name() if c and c.static_mesh else None})
    c=a.get_component_by_class(unreal.PointLightComponent)
    if c and label.startswith('HM_SourceLight'):
        report['lights'].append({'label':label,'pose':pose(a),'intensity':c.get_editor_property('intensity'),
                                 'units':str(c.get_editor_property('intensity_units')),'radius':c.get_editor_property('attenuation_radius'),
                                 'inverse_squared':c.get_editor_property('use_inverse_squared_falloff'),'ies':c.get_editor_property('ies_texture').get_path_name() if c.get_editor_property('ies_texture') else None})
(OUT/'BaselineScene.json').write_text(json.dumps(report,indent=2)+'\n')
print('KZ_HM_FIRES_PROBE_PASSED',len(actors),'fixtures',len(report['fixtures']),'sourceLights',len(report['lights']))
