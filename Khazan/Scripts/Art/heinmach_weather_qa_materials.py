"""Build two temporary diagnostic graphs using the editor's material factory."""
from pathlib import Path
import time
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
BASE='/Game/_Art/Player/Environment/Rendering/HeinMachWeather/_QA'
START=time.monotonic()
HANDLE=None
LIB=unreal.MaterialEditingLibrary


def tick(delta):
    if time.monotonic()-START<10:return
    unreal.unregister_slate_post_tick_callback(HANDLE)
    unreal.EditorAssetLibrary.make_directory(BASE)
    for name in ('Signal','Albedo'):
        m=unreal.load_asset(BASE+'/M_QA_'+name)
        if not m:m=unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_QA_'+name,BASE,unreal.Material,unreal.MaterialFactoryNew())
        LIB.delete_all_material_expressions(m)
        m.set_editor_property('material_domain',unreal.MaterialDomain.MD_POST_PROCESS)
        m.set_editor_property('blendable_location',unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING if name=='Signal' else unreal.BlendableLocation.BL_SCENE_COLOR_BEFORE_BLOOM)
        if name=='Signal':
            root=LIB.create_material_expression(m,unreal.MaterialExpressionConstant3Vector)
            root.set_editor_property('constant',unreal.LinearColor(0,1,0,1))
        else:
            base=LIB.create_material_expression(m,unreal.MaterialExpressionSceneTexture)
            base.set_editor_property('scene_texture_id',unreal.SceneTextureId.PPI_BASE_COLOR)
            scale=LIB.create_material_expression(m,unreal.MaterialExpressionConstant)
            scale.set_editor_property('r',256.0)
            root=LIB.create_material_expression(m,unreal.MaterialExpressionMultiply)
            assert LIB.connect_material_expressions(base,'Color',root,'A')
            assert LIB.connect_material_expressions(scale,'',root,'B')
        assert LIB.connect_material_property(root,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        errors=LIB.recompile_material(m)
        assert not errors,str(errors)
        assert LIB.get_statistics(m).num_pixel_shader_instructions>0
        assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
    for scale in (2,4,8):
        path=BASE+'/MI_QA_Shadow'+str(scale)
        mi=unreal.load_asset(path) or unreal.EditorAssetLibrary.duplicate_asset('/Game/_Art/Player/Environment/Rendering/HeinMachWeather/MI_HM_RegionalLook_OP',path)
        LIB.set_material_instance_scalar_parameter_value(mi,'HM_NativeShadowFillScale',float(scale))
        LIB.update_material_instance(mi)
        assert unreal.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
    print('KZ_HEINMACH_QA_MATERIALS_READY')
    unreal.SystemLibrary.quit_editor()


HANDLE=unreal.register_slate_post_tick_callback(tick)
