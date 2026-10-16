import unreal as u
from pathlib import Path
import json,os
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);folder='/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/OriginalObjects/'
rows=[]
for name in ['FS_Ice_Spear_002','FS_Ice_Floor_003']:
    m=u.load_asset(folder+'Meshes/'+name);b=m.get_bounds();rows.append({'mesh':m.get_path_name(),'bounds':str(b)})
for name in ['FP_Boss_Yetuga_IceBreath_explosion_01','FP_Boss_Yetuga_IceBreath_Smash_04']:
    p=u.load_asset(folder+name);r={'system':p.get_path_name(),'lod_distances':str(p.get_editor_property('LODDistances')),'lod_method':str(p.get_editor_property('LODMethod')),'emitters':[]}
    for e in u.FXConverterUtilitiesLibrary.get_cascade_system_emitters(p):
        lod=u.FXConverterUtilitiesLibrary.get_cascade_emitter_lod_level(e,0);req=u.FXConverterUtilitiesLibrary.get_lod_level_required_module(lod)
        if u.FXConverterUtilitiesLibrary.get_lod_level_is_enabled(lod):
            typ=u.FXConverterUtilitiesLibrary.get_lod_level_type_data_module(lod)
            r['emitters'].append({'emitter':e.get_name(),'typedata':str(typ),'mesh':str(typ.get_editor_property('Mesh')) if isinstance(typ,u.ParticleModuleTypeDataMesh) else None,'req':{key:str(req.get_editor_property(key)) for key in ['Material','EmitterDuration','EmitterLoops','bUseLocalSpace','bKillOnDeactivate','bKillOnCompleted']}})
    rows.append(r)
(out/'FieldBounds.json').write_text(json.dumps(rows,indent=2),encoding='utf-8');print(json.dumps(rows,indent=2))
