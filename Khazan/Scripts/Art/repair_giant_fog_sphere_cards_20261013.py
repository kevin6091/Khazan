"""Bound the recovered procedural breath-fog card with an organic source mask."""
from pathlib import Path
import unreal as u
import json,os
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');out=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
assert Path(u.Paths.project_dir()).resolve()==main.parent.parent/'Khazan_GiantVFXWork_20261013/Khazan'
root='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish';fx=u.FXConverterUtilitiesLibrary;mat=u.load_asset(root+'/Materials/M_KZGiant_SoftPowder');assert mat;report=[]
for path in u.EditorAssetLibrary.list_assets(root+'/Particles',recursive=True):
    p=u.load_asset(path)
    if not isinstance(p,u.ParticleSystem):continue
    changed=False
    for e in fx.get_cascade_system_emitters(p):
        for li in range(len(p.get_editor_property('lod_distances'))):
            lod=fx.get_cascade_emitter_lod_level(e,li);req=fx.get_lod_level_required_module(lod);old=req.get_editor_property('material')
            if old and old.get_name().startswith('KZ_Base_S_Spheremask_01_'):
                req.set_editor_property('material',mat);changed=True;report.append({'system':path,'required':req.get_path_name(),'before':old.get_path_name(),'after':mat.get_path_name(),'reason':'RHI procedural fog has straight quad boundaries; TEMP source organic smoke mask + card support + depth fade, timings/distributions preserved'})
    if changed:assert u.EditorAssetLibrary.save_loaded_asset(p,only_if_is_dirty=False)
(out/'FogSphereCardRepair.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
