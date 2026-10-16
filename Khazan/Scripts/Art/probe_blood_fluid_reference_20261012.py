from pathlib import Path
import unreal,os,json,traceback
OUT=Path(os.environ['KZ_BLOOD_REFERENCE_OUT']);d={'status':'running','materials':[],'textures':[]}
try:
    for name in ['FMI_fluid_A_Blood_01','FMI_fluid_A_Blood_02']:
        a=unreal.load_asset('/Game/_Art/Effects/Shared/Materials/Fluid/MI/'+name);assert a
        row={'asset':a.get_path_name(),'scalars':str(a.get_editor_property('scalar_parameter_values')),'vectors':str(a.get_editor_property('vector_parameter_values')),'textures':str(a.get_editor_property('texture_parameter_values'))}
        parent=a.get_editor_property('parent')
        while isinstance(parent,unreal.MaterialInstance):parent=parent.get_editor_property('parent')
        row['parent']=parent.get_path_name();row['graph']=[]
        for n in unreal.MaterialEditingLibrary.get_material_expressions(parent):
            entry={'type':n.get_class().get_name()}
            if isinstance(n,unreal.MaterialExpressionCustom):entry['code']=n.get_editor_property('code')
            if isinstance(n,unreal.MaterialExpressionTextureSample):entry['texture']=n.get_editor_property('texture').get_path_name()
            row['graph'].append(entry)
        d['materials'].append(row)
    for path in ['/Game/_Art/Effects/Shared/Textures/SubUV/FT_Subuv_Fluid_001','/Game/_Art/Effects/Shared/Textures/BBQ_Texture/SubUV/FT_Fluid_random_001']:
        a=unreal.load_asset(path);assert a
        task=unreal.AssetExportTask();task.object=a;task.filename=str(OUT/(a.get_name()+'.tga'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=unreal.TextureExporterTGA()
        assert unreal.Exporter.run_asset_export_task(task);d['textures'].append({'asset':a.get_path_name(),'size':[a.blueprint_get_size_x(),a.blueprint_get_size_y()],'srgb':a.get_editor_property('srgb')})
    d['status']='passed'
except Exception:d.update(status='failed',error=traceback.format_exc());unreal.log_error(d['error'])
(OUT/'FluidProbe.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
