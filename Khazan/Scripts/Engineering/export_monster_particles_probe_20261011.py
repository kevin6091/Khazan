"""Read-only text exports of selected particle graphs; no package saves."""
from pathlib import Path
import os,json,unreal,traceback
OUT=Path(os.environ['KZ_MONSTER_REPAIR_OUT'])
report={'status':'running','package_saves':0,'exports':[]}
try:
    for path in ['/Game/_Art/Effects/Combat/Blood/PP_Dmg_Blood_Trail_Sub','/Game/_Art/Effects/Combat/Blood/FP_Monster_HitBlood','/Game/_Art/Effects/Combat/Blood/FP_Monster_DeathAsh']:
        asset=unreal.load_asset(path);assert asset,path
        task=unreal.AssetExportTask();task.set_editor_property('object',asset);task.set_editor_property('filename',str(OUT/(asset.get_name()+'.t3d')));task.set_editor_property('automated',True);task.set_editor_property('prompt',False);task.set_editor_property('exporter',unreal.ParticleSystemExporterT3D())
        assert unreal.Exporter.run_asset_export_task(task),path
        report['exports'].append(path)
    report['status']='passed'
except Exception:report['status']='failed';report['error']=traceback.format_exc();unreal.log_error(report['error'])
(OUT/'ParticleProbe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
