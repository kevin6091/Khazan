"""Inspect native Niagara script inputs without saving any gameplay assets."""
from pathlib import Path
import json
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / 'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006'
fx = unreal.FXConverterUtilitiesLibrary
rows = {}
for package in ['/Niagara/DynamicInputs/Vectors/ReturnCameraProperty',
                '/Niagara/VectorFields/SampleVectorField',
                '/Niagara/VectorFields/ApplyVectorField',
                '/Niagara/DynamicInputs/Vectors/ReturnCameraVector',
                '/Niagara/Modules/Spawn/Initialization/InitializeParticle',
                '/Niagara/Modules/Collision/Collision',
                '/Niagara/Modules/Update/Utility/CurlNoise']:
    ctx = fx.create_script_context(unreal.CreateScriptContextArgs(fx.create_asset_data(package)))
    script = unreal.load_asset(package)
    entry = {'script':script.get_path_name(),'properties':{}}
    for field in ['source','script_source','latest_script_data','version_data','script_data','usage']:
        try:
            value = script.get_editor_property(field)
            entry['properties'][field] = str(value)
            if isinstance(value,unreal.NiagaraScriptSource):
                graph = value.get_editor_property('node_graph')
                nodes = graph.get_editor_property('nodes')
                entry['nodes'] = [{'name':n.get_name(),'class':n.get_class().get_name(),
                                   'text':str(n.get_editor_property('input')) if isinstance(n,unreal.NiagaraNodeInput) else ''} for n in nodes]
        except Exception as e:
            entry['properties'][field] = 'Unavailable: '+str(e)
    rows[package] = entry
for path in ['/Niagara/Enums/ENiagara_CameraProperties','/Niagara/Enums/ENiagara_GPUCollisionType',
             '/Niagara/Enums/ENiagara_CameraVectors']:
    obj = unreal.load_asset(path)
    try:
        display=str(obj.get_editor_property('display_name_map'))
    except Exception as e:
        display=str(e)
    rows[path] = {'entries':display, 'object':str(obj)}
world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
rows['PP_bounds']=[{'label':a.get_actor_label(),'bounds':str(a.get_actor_bounds(False))} for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors() if isinstance(a,unreal.PostProcessVolume)]
vf=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/VF_HM_Perlin_Source16')
rows['imported_vector_field']={}
for f in ['SizeX','SizeY','SizeZ','bounds','bAllowCPUAccess']:
    try:rows['imported_vector_field'][f]=str(vf.get_editor_property(f))
    except Exception as e:rows['imported_vector_field'][f]=str(e)
system=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/NS_HM_SourceSnow_TwoLayers')
rows['system']={}
for f in ['EmitterHandles','SystemSpawnScript','SystemUpdateScript']:
    try:rows['system'][f]=str(system.get_editor_property(f))
    except Exception as e:rows['system'][f]=str(e)
rows['API']={n:getattr(unreal,n).__doc__ for n in ['NiagaraSystem','NiagaraPythonScriptModuleInput','NiagaraSimCacheFunctionLibrary'] if hasattr(unreal,n)}
try:
    task=unreal.AssetExportTask()
    task.set_editor_property('object',system)
    task.set_editor_property('filename',str(ROOT/'Saved/Extracted/HeinMachWeather_20261006/NativeSnowTwoLayers.t3d'))
    task.set_editor_property('exporter',unreal.ObjectExporterT3D())
    task.set_editor_property('automated',True)
    task.set_editor_property('prompt',False)
    task.set_editor_property('selected',False)
    rows['system_exported']=unreal.Exporter.run_asset_export_task(task)
except Exception as e:rows['system_export_error']=str(e)
(OUT/'NiagaraSupplement.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
print('KZ_NIAGARA_INPUTS_PROBED')
