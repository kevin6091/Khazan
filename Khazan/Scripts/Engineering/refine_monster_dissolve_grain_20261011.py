"""Use the existing original dissolve noise at a finer, explicitly provisional UV frequency."""
from pathlib import Path
import os,json,unreal,traceback
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');OUT=Path(os.environ['KZ_MONSTER_REPAIR_OUT']);lib=unreal.MaterialEditingLibrary
r={'status':'running','saved':[],'temporary_noise_tiling':6,'package_saves':0}
try:
    source=json.loads((MAIN/'Metadata/MonsterPresentationRepair_20261011/MaterialAuthor05/MaterialAuthor.json').read_text(encoding='utf-8'))
    for row in source['corpse_masters']:
        m=unreal.load_asset(row['material']);expressions=lib.get_material_expressions(m)
        noise=next(n for n in expressions if isinstance(n,unreal.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='KZDeathNoise')
        existing=[n for n in expressions if isinstance(n,unreal.MaterialExpressionScalarParameter) and str(n.get_editor_property('parameter_name'))=='KZDeathNoiseTiling']
        if not existing:
            uv=lib.create_material_expression(m,unreal.MaterialExpressionTextureCoordinate)
            scale=lib.create_material_expression(m,unreal.MaterialExpressionScalarParameter);scale.set_editor_property('parameter_name','KZDeathNoiseTiling');scale.set_editor_property('default_value',6.)
            multiply=lib.create_material_expression(m,unreal.MaterialExpressionMultiply)
            assert lib.connect_material_expressions(uv,'',multiply,'A') and lib.connect_material_expressions(scale,'',multiply,'B') and lib.connect_material_expressions(multiply,'',noise,'UVs')
        lib.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m,False);r['saved'].append(m.get_path_name())
    r['package_saves']=len(r['saved']);r['status']='passed'
except Exception:r['status']='failed';r['error']=traceback.format_exc();unreal.log_error(r['error'])
(OUT/'DissolveGrain.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
