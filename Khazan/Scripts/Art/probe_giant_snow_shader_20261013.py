import unreal as u
from pathlib import Path
import os,json
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);lib=u.MaterialEditingLibrary;root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/Materials/'
rows=[]
for n in ['M_KZGiant_SoftSnowMist','MI_Atlas_MI_KZGiant_Snow_FMI_World_SubUV_color_A_04_1x1','M_KZGiant_SoftPowder']:
    m=u.load_asset(root+n);r={'asset':m.get_path_name()}
    if isinstance(m,u.MaterialInstanceConstant):
        r['parent']=m.get_editor_property('parent').get_path_name();r['overrides']=m.get_editor_property('base_property_overrides').export_text();r['parameters']=[p.export_text() for p in m.get_editor_property('vector_parameter_values')];r['scalars']=[p.export_text() for p in m.get_editor_property('scalar_parameter_values')]
    else:
        r['blend']=str(m.get_editor_property('blend_mode'));r['emissive_node']=str(lib.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR));r['opacity_node']=str(lib.get_material_property_input_node(m,u.MaterialProperty.MP_OPACITY))
        task=u.AssetExportTask();task.object=m;task.filename=str(out/(n+'.t3d'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.ObjectExporterT3D();assert u.Exporter.run_asset_export_task(task)
    rows.append(r)
(out/'SnowShader.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps(rows,indent=2))
