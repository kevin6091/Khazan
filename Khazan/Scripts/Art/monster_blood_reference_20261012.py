"""Targeted original texture/material inspection; screenshot matching authoring is separate."""
from pathlib import Path
import unreal, os, json, traceback
OUT=Path(os.environ['KZ_BLOOD_REFERENCE_OUT'])
d={'status':'running','textures':[],'materials':[],'asset_saves':0}
try:
    base='/Game/_Art/Effects/Shared/Textures/BBQ_Texture/Decal/'
    names=['FT_Decal_Blood_000','FT_Decal_Blood_001','FT_Decal_Blood_002','FT_Decal_Blood_003','FT_Decal_Blood_004','FT_Decal_Blood_A_000','FT_Decal_Blood_A_001','FT_Decal_Blood_A_002','FT_Decal_Blood_A_003','FT_Decal_Blood_Linear_000','FT_Decal_Blood_Curve_A_000']
    for name in names:
        a=unreal.load_asset(base+name);assert a,name
        task=unreal.AssetExportTask();task.object=a;task.filename=str(OUT/(name+'.tga'));task.automated=True;task.prompt=False;task.replace_identical=True
        task.exporter=unreal.TextureExporterTGA();assert unreal.Exporter.run_asset_export_task(task),name
        d['textures'].append({'asset':a.get_path_name(),'size':[a.blueprint_get_size_x(),a.blueprint_get_size_y()],'srgb':a.get_editor_property('srgb'),'compression':str(a.get_editor_property('compression_settings'))})
    for name in ['PD_Blood_Base','PD_Blood_Super','PD_Blood_SuperRound','PD_Blood_Gsword_Super']:
        a=unreal.load_asset('/Game/_Art/Effects/Shared/Materials/BBQ_Material/PhysicsDecal/'+name);assert a,name
        parent=a.get_editor_property('parent');master=parent
        while isinstance(master,unreal.MaterialInstance):master=master.get_editor_property('parent')
        d['materials'].append({'asset':a.get_path_name(),'parent':parent.get_path_name(),'master':master.get_path_name(),'domain':str(master.get_editor_property('material_domain')),'scalars':str(a.get_editor_property('scalar_parameter_values')),'texture_parameters':str(a.get_editor_property('texture_parameter_values'))})
    d['status']='passed'
except Exception:d['status']='failed';d['error']=traceback.format_exc();unreal.log_error(d['error'])
(OUT/'Probe.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
