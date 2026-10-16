"""Explicit mask-channel sampling and native stock foliage shading for source leaf MIs."""
from pathlib import Path
import hashlib,json,os,traceback,unreal
ROOT=Path(unreal.Paths.project_dir()).resolve();MAIN=Path(os.environ['KZ_LOOK_MAIN']);OUT=Path(os.environ['KZ_LOOK_OUT'])
assert ROOT!=MAIN
lib=unreal.MaterialEditingLibrary;assets=unreal.EditorAssetLibrary
report={'success':False,'saved':[],'leaf_changes':[],'shader_errors':[]}
try:
    root=unreal.load_asset('/Game/_Art/Player/Environment/Rendering/SceneLook/M_HM_PBR_Masked');assert root
    nodes=lib.get_material_expressions(root)
    params={str(n.get_editor_property('parameter_name')):n for n in nodes if isinstance(n,(unreal.MaterialExpressionVectorParameter,unreal.MaterialExpressionTextureSampleParameter2D))}
    mask=lib.get_material_property_input_node(root,unreal.MaterialProperty.MP_OPACITY_MASK)
    channel=next((n for n in nodes if isinstance(n,unreal.MaterialExpressionCustom) and n.get_editor_property('desc').startswith('Native explicit RGBA opacity selection')),None)
    if not channel:channel=lib.create_material_expression(root,unreal.MaterialExpressionCustom,1600,1250)
    inputs=[]
    for name in ['Value','ChannelRGB','ChannelA']:
        inp=unreal.CustomInput();inp.set_editor_property('input_name',name);inputs.append(inp)
    channel.set_editor_property('inputs',inputs);channel.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    channel.set_editor_property('code','return dot(Value, float4(ChannelRGB.rgb, ChannelA));')
    channel.set_editor_property('desc','Native explicit RGBA opacity selection; source texture/UV/component/use/cutoff retained')
    assert lib.connect_material_expressions(params['OpacityTexture'],'RGBA',channel,'Value')
    assert lib.connect_material_expressions(params['OpacityTextureComponent'],'RGB',channel,'ChannelRGB')
    assert lib.connect_material_expressions(params['OpacityTextureComponent'],'A',channel,'ChannelA')
    assert lib.connect_material_expressions(channel,'',mask,'B')
    # Source-supported stock TwoSidedFoliage uses diffuse as its transmission color.
    color=lib.get_material_property_input_node(root,unreal.MaterialProperty.MP_BASE_COLOR)
    assert lib.connect_material_property(color,'',unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
    report['shader_errors']=list(map(str,lib.recompile_material(root)))
    assert not report['shader_errors'];assert assets.save_loaded_asset(root,False)
    report['saved'].append(root.get_path_name().split('.')[0])
    baseline=json.loads((MAIN/'Metadata/SceneLook_20261012/MaskBaseline.json').read_text())
    source_dir=Path.home()/'Desktop/\uce74\uc794/Exports/BBQ/Content/Art/World/World_Material/Prop/Material'
    for row in baseline['targets']:
        name=row['material'].split('/')[-1].split('.')[0].removeprefix('MI_')
        if not name.startswith('WM_COM_SmallTree_Base_') or not name.endswith('_02'):continue
        source=source_dir/(name+'.json')
        if not source.exists():continue
        entries=json.loads(source.read_text(encoding='utf-8-sig'))
        entry=next(e for e in entries if e.get('Type')=='MaterialInstanceConstant')
        props=entry.get('Properties',{});orig=props.get('BasePropertyOverrides',{})
        if orig.get('ShadingModel')!='MSM_TwoSidedFoliage':continue
        m=unreal.load_asset(row['material']);assert m
        overrides=m.get_editor_property('base_property_overrides')
        overrides.set_editor_property('override_shading_model',True)
        overrides.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_TWO_SIDED_FOLIAGE)
        m.set_editor_property('base_property_overrides',overrides)
        emission_before=lib.get_material_instance_scalar_parameter_value(m,'UseEmissiveColorTexture')
        # TEMP native PBR: source Tex_E is a saturated RGB mask, not a verified radiance image.
        # Retain the source texture binding while removing the adapter's raw RGB glow.
        lib.set_material_instance_scalar_parameter_value(m,'UseEmissiveColorTexture',0.0)
        assert lib.get_material_instance_scalar_parameter_value(m,'UseEmissiveColorTexture')==0.0
        lib.update_material_instance(m)
        assert assets.save_loaded_asset(m,False)
        report['saved'].append(m.get_path_name().split('.')[0])
        report['leaf_changes'].append({'material':m.get_path_name(),'source_file':str(source),
            'source_sha':hashlib.sha256(source.read_bytes()).hexdigest(),'source_field':'BasePropertyOverrides.ShadingModel',
            'source_value':orig['ShadingModel'],'native_value':'MSM_TWOSIDED_FOLIAGE',
            'TEMP_raw_emission_before':emission_before,'TEMP_raw_emission_after':0.0,
            'source_texture_and_clip_retained':True})
    report['success']=True
except Exception:report['error']=traceback.format_exc();unreal.log_error(report['error'])
(OUT/'FoliageFinish.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['success'],report.get('error')
