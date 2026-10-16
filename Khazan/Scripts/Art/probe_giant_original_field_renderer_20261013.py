"""Inspect actual protected Cascade data via the already-installed engine utility."""
import unreal as u
from pathlib import Path
import json,os
out=Path(os.environ['KZ_COMBAT_FINISH_OUT']);FX=u.FXConverterUtilitiesLibrary
report=[]
for name in ['FP_Boss_Yetuga_IceBreath_explosion_01','FP_Boss_Yetuga_IceBreath_Smash_04']:
    p=u.load_asset('/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/OriginalObjects/'+name)
    row={'asset':p.get_path_name(),'emitters':[]}
    for emitter in FX.get_cascade_system_emitters(p):
        lod=FX.get_cascade_emitter_lod_level(emitter,0)
        req=FX.get_lod_level_required_module(lod)
        typ=FX.get_lod_level_type_data_module(lod)
        r={'emitter':emitter.get_path_name(),'enabled':FX.get_lod_level_is_enabled(lod),'material':req.get_editor_property('Material').get_path_name() if req.get_editor_property('Material') else None,
           'type_data':typ.get_class().get_name() if typ else None}
        if isinstance(typ,u.ParticleModuleTypeDataMesh):
            mesh=typ.get_editor_property('Mesh');r['mesh']=mesh.get_path_name() if mesh else None
        row['emitters'].append(r)
    report.append(row)
(out/'FieldRenderer.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
