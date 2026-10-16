from pathlib import Path
import json,os,unreal as u
OUT=Path(os.environ['KZ_PARRY_PHOTO_OUT'])
m=u.load_asset('/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference/M_Parry_Distortion');assert m
for n in u.MaterialEditingLibrary.get_material_expressions(m):
    if isinstance(n,u.MaterialExpressionTextureSampleParameter2D):
        # The reused source texture is sRGB. Match its actual sampler contract;
        # changing this private shader avoids altering the shared source texture.
        n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
assert not list(u.MaterialEditingLibrary.recompile_material(m))
assert u.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
(OUT/'Sampler.json').write_text(json.dumps({'status':'saved','rhi_compile_still_required':True,'shared_texture_saved':False}),encoding='utf-8')
