"""Read only: one affected leaf, texture alpha and actual connected shader channels."""
from pathlib import Path
import json,os,traceback,unreal
OUT=Path(os.environ['KZ_LOOK_OUT']);lib=unreal.MaterialEditingLibrary
report={'success':False,'connections':[],'textures':[],'asset_saves':0}
try:
    m=unreal.load_asset('/Game/_Art/Player/Environment/HeinMach/Reconstructed/OverrideMaterials/Inherited/Materials/MI_WM_COM_SmallTree_Base_003_02')
    assert m
    for name in ['BaseColorTexture','OpacityTexture','EmissiveColorTexture']:
        t=lib.get_material_instance_texture_parameter_value(m,name);assert t
        task=unreal.AssetExportTask();task.set_editor_property('object',t);task.set_editor_property('filename',str(OUT/(name+'.png')))
        task.set_editor_property('automated',True);task.set_editor_property('prompt',False);task.set_editor_property('replace_identical',True)
        assert unreal.Exporter.run_asset_export_task(task)
        report['textures'].append({'parameter':name,'texture':t.get_path_name(),'file':str(OUT/(name+'.png')),
            'compression_no_alpha':t.get_editor_property('compression_no_alpha'),'compression':str(t.get_editor_property('compression_settings')),
            'srgb':t.get_editor_property('srgb'),'alpha_min_max':str(t.get_editor_property('adjust_min_alpha'))+','+str(t.get_editor_property('adjust_max_alpha'))})
    root=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/SceneLook/M_HM_PBR_Masked');assert root
    nodes={n.get_name():n for n in lib.get_material_expressions(root)}
    seen=set()
    def visit(node):
        if not node or node.get_name() in seen:return
        seen.add(node.get_name())
        inputs=lib.get_inputs_for_material_expression(root,node)
        names=lib.get_material_expression_input_names(node)
        row={'node':node.get_name(),'class':node.get_class().get_name(),'inputs':[]}
        for key in ['parameter_name','default_value']:
            try:
                v=node.get_editor_property(key);row[key]=v if isinstance(v,(float,int,str)) else str(v)
            except Exception:pass
        for index,parent in enumerate(inputs):
            if parent:row['inputs'].append({'pin':str(names[index]),'node':parent.get_name(),'output':lib.get_input_node_output_name_for_material_expression(node,parent)})
        report['connections'].append(row)
        for parent in inputs:visit(parent)
    visit(lib.get_material_property_input_node(root,unreal.MaterialProperty.MP_OPACITY_MASK))
    report['success']=True
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
(OUT/'OpacityProbe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['success'],report.get('error')
