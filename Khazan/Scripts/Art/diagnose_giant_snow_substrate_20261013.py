"""Two private shader controls on the runtime-proven black emitter."""
from pathlib import Path
import unreal as u
import json,os
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');out=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
assert Path(u.Paths.project_dir()).resolve()==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish';folder=root+'/Diagnostics';lib=u.MaterialEditingLibrary;at=u.AssetToolsHelpers.get_asset_tools();fx=u.FXConverterUtilitiesLibrary
cases=[]
for kind in ['LegacyControl03','SubstrateControl03']:
    mat=u.EditorAssetLibrary.duplicate_asset(root+'/Materials/M_KZGiant_SoftSnowMist',folder+'/M_'+kind);assert mat
    nodes=list(lib.get_material_expressions(mat));tint=next(n for n in nodes if isinstance(n,u.MaterialExpressionVectorParameter) and str(n.get_editor_property('parameter_name'))=='SnowTint');fade=next(n for n in nodes if isinstance(n,u.MaterialExpressionDepthFade))
    assert lib.connect_material_property(tint,'RGB',u.MaterialProperty.MP_EMISSIVE_COLOR)
    if kind.startswith('SubstrateControl'):
        bsdf=lib.create_material_expression(mat,u.MaterialExpressionSubstrateUnlitBSDF)
        weight=lib.create_material_expression(mat,u.MaterialExpressionSubstrateWeight)
        zero=lib.create_material_expression(mat,u.MaterialExpressionConstant);zero.set_editor_property('r',0)
        names=list(lib.get_material_expression_input_names(bsdf));u.log('SUBSTRATE_CONTROL_INPUTS '+str(names))
        assert lib.connect_material_expressions(tint,'RGB',bsdf,next(n for n in names if 'Emissive' in n))
        assert lib.connect_material_expressions(zero,'',bsdf,next(n for n in names if 'Transmittance' in n))
        assert lib.connect_material_expressions(bsdf,'',weight,'A')
        assert lib.connect_material_expressions(fade,'',weight,'Weight')
        assert lib.connect_material_property(weight,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    errors=list(lib.recompile_material(mat));assert not errors,errors
    assert u.EditorAssetLibrary.save_loaded_asset(mat,only_if_is_dirty=False)
    p=u.EditorAssetLibrary.duplicate_asset(folder+'/DustEmitter1',folder+'/'+kind);assert p
    mi=at.create_asset('MI_'+kind,folder,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());lib.set_material_instance_parent(mi,mat);lib.update_material_instance(mi);assert u.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    for ei,e in enumerate(fx.get_cascade_system_emitters(p)):
        for li in range(len(p.get_editor_property('lod_distances'))):
            lod=fx.get_cascade_emitter_lod_level(e,li)
            req=fx.get_lod_level_required_module(lod);req.set_editor_property('material',mi)
            u.SystemLibrary.execute_console_command(world,'SETNOPEC "'+lod.get_path_name()+'" bEnabled '+('True' if ei==1 else 'False'))
    u.SystemLibrary.execute_console_command(world,'SETNOPEC "'+p.get_path_name()+'" SoloTracking ()')
    assert u.EditorAssetLibrary.save_loaded_asset(p,only_if_is_dirty=False)
    cases.append([kind,'Yetuga','particle',p.get_path_name()])
(out/'SubstrateControl.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
(main/'Metadata/GiantVFX_20261013/RendererIsolationCases.tsv').write_text('\n'.join('\t'.join(c) for c in cases),encoding='utf-8')
