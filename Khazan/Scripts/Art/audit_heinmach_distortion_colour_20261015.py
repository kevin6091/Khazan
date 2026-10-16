"""Read only the two colour-signature outlier systems and their material graphs."""
from pathlib import Path
import json,os
import unreal as u
out=Path(os.environ['KZ_HM_COLOUR_OUT']);lib=u.MaterialEditingLibrary;rows=[]
for path in ('/Game/VFX/03_SlashHit/Materials/M_SW_distort_Sprite','/Game/VFX/03_SlashHit/Materials/M_shokW_basic',
             '/Game/_Art/Effects/Combat/PlayerSlamDistort/M_FloorSoft_M_SW_distort_Sprite',
             '/Game/VFX/03_SlashHit/KZ_Parring_Distort','/Game/_Art/Effects/Combat/PlayerSlamDistort/NS_Player_Plunge_ParringDistort'):
    obj=u.load_asset(path);assert obj
    task=u.AssetExportTask();task.object=obj;task.filename=str(out/(obj.get_name()+'.t3d'))
    task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False
    assert u.Exporter.run_asset_export_task(task)
    if isinstance(obj,u.Material):
        rows.append({'asset':path,'nodes':[node.get_class().get_name() for node in lib.get_material_expressions(obj)]})
(out/'Audit.json').write_text(json.dumps({'asset_saves':0,'rows':rows},indent=2),encoding='utf-8')
