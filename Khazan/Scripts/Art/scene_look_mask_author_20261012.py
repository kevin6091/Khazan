"""Repair missing USD opacity-mask input, preserving source parameters and overrides."""
from pathlib import Path
import json,os,traceback,unreal
ROOT=Path(unreal.Paths.project_dir()).resolve();MAIN=Path(os.environ['KZ_LOOK_MAIN']);OUT=Path(os.environ['KZ_LOOK_OUT'])
assert ROOT!=MAIN
targets=json.loads((MAIN/'Metadata/SceneLook_20261012/MaskBaseline.json').read_text())['targets']
lib=unreal.MaterialEditingLibrary;assets=unreal.EditorAssetLibrary
base='/Game/_Art/Player/Environment/Rendering/SceneLook'
report={'success':False,'saved':[],'changes':[],'shader_errors':[],'compatibility_parents':[]}

try:
    root=unreal.load_asset(base+'/M_HM_PBR_Masked')
    if not root:
        original_root=unreal.load_asset('/USDCore/Materials/UsdPreviewSurface.UsdPreviewSurface');assert original_root
        root=unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset('M_HM_PBR_Masked',base,original_root)
    assert root and isinstance(root,unreal.Material)
    node=lib.get_material_property_input_node(root,unreal.MaterialProperty.MP_OPACITY)
    output=lib.get_material_property_input_node_output_name(root,unreal.MaterialProperty.MP_OPACITY)
    assert node,'USD source has no opacity input'
    assert lib.connect_material_property(node,output,unreal.MaterialProperty.MP_OPACITY_MASK)
    root.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
    assert lib.get_material_property_input_node(root,unreal.MaterialProperty.MP_OPACITY_MASK)==node
    report['mask_input']={'node':node.get_name(),'output':output,'policy':'Reuse existing authored texture component/UV/opacity; no new alpha cutoff or source parameter value'}
    errors=lib.recompile_material(root)
    if errors:report['shader_errors']+=list(map(str,errors))
    assert not report['shader_errors'],report['shader_errors']
    assert assets.save_loaded_asset(root,False);report['saved'].append(root.get_path_name().split('.')[0])
    clones={'/USDCore/Materials/UsdPreviewSurface.UsdPreviewSurface':root}
    def clone_parent(source):
        path=source.get_path_name()
        if path in clones:return clones[path]
        assert isinstance(source,unreal.MaterialInstanceConstant),path
        parent=clone_parent(source.get_editor_property('parent'))
        dst=base+'/MI_HM_'+source.get_name()+'_Compatibility'
        obj=unreal.load_asset(dst) or unreal.AssetToolsHelpers.get_asset_tools().duplicate_asset(dst.rsplit('/',1)[1],base,source);assert obj
        obj.set_editor_property('parent',parent);assert assets.save_loaded_asset(obj,False)
        clones[path]=obj;report['saved'].append(dst)
        report['compatibility_parents'].append({'original':path,'clone':obj.get_path_name(),'base_overrides_preserved':obj.get_editor_property('base_property_overrides').export_text()})
        return obj
    for row in targets:
        m=unreal.load_asset(row['material']);assert m
        original=m.get_editor_property('parent');assert original.get_path_name()==row['parent']
        override_before=m.get_editor_property('base_property_overrides').export_text()
        scalar_before={str(k):lib.get_material_instance_scalar_parameter_value(m,k) for k in lib.get_scalar_parameter_names(m)}
        tex_before={str(k):str(lib.get_material_instance_texture_parameter_value(m,k)) for k in lib.get_texture_parameter_names(m)}
        new=clone_parent(original);m.set_editor_property('parent',new)
        assert m.get_editor_property('base_property_overrides').export_text()==override_before
        assert scalar_before=={str(k):lib.get_material_instance_scalar_parameter_value(m,k) for k in lib.get_scalar_parameter_names(m)}
        assert tex_before=={str(k):str(lib.get_material_instance_texture_parameter_value(m,k)) for k in lib.get_texture_parameter_names(m)}
        assert assets.save_loaded_asset(m,False)
        report['saved'].append(m.get_path_name().split('.')[0])
        report['changes'].append({'material':m.get_path_name(),'old_parent':original.get_path_name(),'new_parent':new.get_path_name(),
            'original_base_overrides':override_before,'scalar_texture_parameters_identical':True,
            'opacity_texture_component':lib.get_material_instance_vector_parameter_value(m,'OpacityTextureComponent').export_text()})
    report['success']=True
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
(OUT/'MaskAuthoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['success'],report.get('error')
