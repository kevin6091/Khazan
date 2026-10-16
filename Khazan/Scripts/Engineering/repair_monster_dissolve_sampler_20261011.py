from pathlib import Path
import json,os,unreal
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');ROOT=Path(unreal.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_MONSTER_REPAIR_OUT'])
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
d={'status':'running','saved':[],'reason':'FT_Noise_Dissolve is linear grayscale; preserve its original compression/sRGB and use the correct sampler'}
author=json.loads((MAIN/'Metadata/MonsterPresentationRepair_20261011/MaterialAuthor05/MaterialAuthor.json').read_text(encoding='utf-8-sig'))
for row in author['corpse_masters']:
    m=unreal.load_asset(row['material']);nodes=[n for n in unreal.MaterialEditingLibrary.get_material_expressions(m) if isinstance(n,unreal.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='KZDeathNoise'];assert len(nodes)==1
    nodes[0].set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    unreal.MaterialEditingLibrary.recompile_material(m);assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False);d['saved'].append(m.get_path_name())
d['status']='passed';(OUT/'SamplerRepair.json').write_text(json.dumps(d,indent=2),encoding='utf-8')
