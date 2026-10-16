"""Read only saved shader/particle links in the task-owned copy."""
from pathlib import Path
import json, os, unreal as u
OUT=Path(os.environ['KZ_PARRY_OUT']); BASE='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/'
R={'status':'passed','materials':[]}
def export(a):
    t=u.AssetExportTask();t.object=a;t.filename=str(OUT/(a.get_name()+'.t3d'));t.automated=True;t.prompt=False
    assert u.Exporter.run_asset_export_task(t)
for name in ['FM_fluid_A','FMI_fluid_A_133','FMI_fluid_A_11','FMI_fluid_A_13','FMI_fluid_A_15','FM_Subuv_Atlas_B','DefaultParticle']:
    a=u.load_asset(BASE+'Materials/'+name);export(a)
    row={'path':a.get_path_name()}
    if isinstance(a,u.MaterialInstanceConstant):
        row['parent']=a.get_editor_property('parent').get_path_name()
        row['overrides']=a.get_editor_property('base_property_overrides').export_text()
    else:row['blend_mode']=str(a.get_editor_property('blend_mode'))
    R['materials'].append(row)
export(u.load_asset(BASE+'PP_Player_Parry_Success'))
(OUT/'Probe.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
