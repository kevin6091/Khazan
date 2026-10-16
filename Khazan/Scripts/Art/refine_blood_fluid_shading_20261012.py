from pathlib import Path
import unreal,os,json,traceback
ROOT=Path(unreal.Paths.project_dir()).resolve();assert 'Khazan_GiantFallWork_20261011' in str(ROOT)
OUT=Path(os.environ['KZ_BLOOD_REFERENCE_OUT']);lib=unreal.MaterialEditingLibrary;d={'status':'running','saved':[]}
try:
    for name in ['FT_Monster_HitBloodGroundMask','FT_Monster_HitBloodFluid']:
        t=unreal.load_asset('/Game/_Art/Effects/Combat/Blood/'+name);assert t
        t.set_editor_property('never_stream',True);t.set_editor_property('lod_bias',0);t.set_editor_property('max_texture_size',0)
        assert unreal.EditorAssetLibrary.save_loaded_asset(t,only_if_is_dirty=False);d['saved'].append(t.get_path_name())
    m=unreal.load_asset('/Game/_Art/Effects/Combat/Blood/M_Monster_HitBloodFluid');assert m
    m.set_editor_property('translucency_lighting_mode',unreal.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    nodes=lib.get_material_expressions(m)
    tex=next(n for n in nodes if isinstance(n,unreal.MaterialExpressionTextureSampleParameter2D))
    base=next(n for n in nodes if isinstance(n,unreal.MaterialExpressionVectorParameter))
    inputs=[]
    for name in ['T','Color']:
        i=unreal.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
    tint=lib.create_material_expression(m,unreal.MaterialExpressionCustom)
    tint.set_editor_property('inputs',inputs);tint.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    tint.set_editor_property('code','return Color*lerp(.3,1.8,saturate(T.b*.75+T.r*.25));')
    assert lib.connect_material_expressions(tex,'RGB',tint,'T');assert lib.connect_material_expressions(base,'RGB',tint,'Color')
    assert lib.connect_material_property(tint,'',unreal.MaterialProperty.MP_BASE_COLOR)
    lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False);d['saved'].append(m.get_path_name())
    d.update(status='passed',temporary_tint='Color * lerp(.3,1.8,saturate(B*.75+R*.25))',engine_lighting='SurfacePerPixelLighting',mask_texture_mips='never-stream/lod-bias0/max-size0: preserve full source silhouette')
except Exception:d.update(status='failed',error=traceback.format_exc());unreal.log_error(d['error'])
(OUT/'ShadingRevision.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
