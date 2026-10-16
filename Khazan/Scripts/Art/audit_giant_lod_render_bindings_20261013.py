import unreal as u
from pathlib import Path
import json,os
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish';fx=u.FXConverterUtilitiesLibrary;rows=[]
for asset in u.EditorAssetLibrary.list_assets(root+'/Particles',recursive=True):
    ps=u.load_asset(asset)
    if not isinstance(ps,u.ParticleSystem):continue
    for emitter in fx.get_cascade_system_emitters(ps):
        for i in range(len(ps.get_editor_property('LODDistances'))):
            lod=fx.get_cascade_emitter_lod_level(emitter,i)
            if not lod or not fx.get_lod_level_is_enabled(lod):continue
            req=fx.get_lod_level_required_module(lod);mat=req.get_editor_property('Material')
            rows.append({'system':ps.get_name(),'emitter':emitter.get_name(),'lod':i,'material':mat.get_path_name() if mat else None,'named_overrides':str(req.get_editor_property('NamedMaterialOverrides'))})
(out/'LODRenderers.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
for r in rows:
    if 'Slashdust_HalfCircle_Left' in r['system']:print(json.dumps(r))
