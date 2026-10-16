"""Scope UV-edge/refraction fading to the floor-only variant; keep Fab originals."""
from pathlib import Path
import json,os,traceback,unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();MAIN=Path(os.environ['KZ_PARRY_MAIN']);OUT=Path(os.environ['KZ_PARRY_OUT'])
assert ROOT==MAIN.parent.parent/'Khazan_SlamDistortWork_20261012/Khazan'
lib=u.MaterialEditingLibrary;DIR='/Game/_Art/Effects/Combat/PlayerSlamDistort';report={'success':False,'saved':[],'materials':[]}
try:
    system=u.load_asset(DIR+'/NS_Player_Plunge_ParringDistort');assert system
    cache={};bases={}
    for emitter in ['M_SW_distort_Sprite_0','M_SW_distort_Sprite001_1','Hit003_6']:
        renderer=u.load_object(None,system.get_path_name()+':'+emitter+'.NiagaraSpriteRendererProperties_0')
        source=renderer.get_editor_property('material');assert source
        if source.get_path_name() in cache:
            renderer.set_editor_property('material',cache[source.get_path_name()]);continue
        chain=[];base=source
        while isinstance(base,u.MaterialInstanceConstant):chain.append(base);base=base.get_editor_property('parent')
        assert isinstance(base,u.Material)
        if base.get_path_name() not in bases:
            material=u.EditorAssetLibrary.duplicate_asset(base.get_path_name(),DIR+'/M_FloorSoft_'+base.get_name());assert material
            uv=lib.create_material_expression(material,u.MaterialExpressionTextureCoordinate,-900,500)
            mask=lib.create_material_expression(material,u.MaterialExpressionCustom,-650,500)
            mask.set_editor_property('description','TEMP floor burst radial edge fade; geometry UV constants, fade starts at normalized radius .8')
            mask.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
            mask.set_editor_property('code','return 1.0-smoothstep(0.8,1.0,length(UV*2.0-1.0));')
            item=u.CustomInput();item.set_editor_property('input_name','UV');mask.set_editor_property('inputs',[item])
            assert lib.connect_material_expressions(uv,'',mask,'UV')
            opacity=lib.get_material_property_input_node(material,u.MaterialProperty.MP_OPACITY)
            if opacity:
                output=lib.get_material_property_input_node_output_name(material,u.MaterialProperty.MP_OPACITY)
                multiply=lib.create_material_expression(material,u.MaterialExpressionMultiply,-300,500)
                assert lib.connect_material_expressions(opacity,output,multiply,'A')
                assert lib.connect_material_expressions(mask,'',multiply,'B')
                assert lib.connect_material_property(multiply,'',u.MaterialProperty.MP_OPACITY)
            else:assert lib.connect_material_property(mask,'',u.MaterialProperty.MP_OPACITY)
            refraction=lib.get_material_property_input_node(material,u.MaterialProperty.MP_REFRACTION)
            if refraction:
                output=lib.get_material_property_input_node_output_name(material,u.MaterialProperty.MP_REFRACTION)
                lerp=lib.create_material_expression(material,u.MaterialExpressionLinearInterpolate,-300,750)
                lerp.set_editor_property('const_a',1.) # neutral index of refraction at transparent edges
                assert lib.connect_material_expressions(refraction,output,lerp,'B')
                assert lib.connect_material_expressions(mask,'',lerp,'Alpha')
                assert lib.connect_material_property(lerp,'',u.MaterialProperty.MP_REFRACTION)
            errors=lib.recompile_material(material);assert not errors,errors
            assert u.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False)
            report['saved'].append(material.get_path_name());bases[base.get_path_name()]=material
        parent=bases[base.get_path_name()]
        for mi in reversed(chain):
            copy=u.EditorAssetLibrary.duplicate_asset(mi.get_path_name(),DIR+'/MI_FloorSoft_'+mi.get_name());assert copy
            lib.set_material_instance_parent(copy,parent);lib.update_material_instance(copy)
            assert u.EditorAssetLibrary.save_loaded_asset(copy,only_if_is_dirty=False)
            report['saved'].append(copy.get_path_name());parent=copy
        renderer.set_editor_property('material',parent);cache[source.get_path_name()]=parent
        report['materials'].append({'original':source.get_path_name(),'floor':parent.get_path_name()})
    assert u.EditorAssetLibrary.save_loaded_asset(system,only_if_is_dirty=False);report['saved'].append(system.get_path_name())
    report['success']=True
except Exception:report['error']=traceback.format_exc()
finally:
    (OUT/'AlphaRefinement.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('SLAM_DISTORT_ALPHA',report['success'],report.get('error',''))
if not report['success']:raise RuntimeError(report.get('error','Alpha refinement failed'))
