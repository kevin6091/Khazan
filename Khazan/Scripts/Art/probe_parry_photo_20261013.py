from pathlib import Path
import json, os, unreal as u
OUT=Path(os.environ['KZ_PARRY_PHOTO_OUT'])

def export(asset,name):
    t=u.AssetExportTask();t.object=asset;t.filename=str(OUT/name)
    t.exporter=u.ObjectExporterT3D();t.automated=True;t.prompt=False;t.replace_identical=True
    assert u.Exporter.run_asset_export_task(t)

ps=u.load_asset('/Game/_Art/Effects/Combat/GuardParry/PP_AtkEx_Parry');assert ps
export(ps,'OriginalParry.t3d')
root='/Game/_Art/Effects/Shared/Materials/'
paths=[root+'Fluid/MI/'+n for n in ['FMI_fluid_A_162','FMI_fluid_A_15','FMI_fluid_A_12','FMI_fluid_A_11','FMI_fluid_A_13']]
paths += [root+'SubUV/MI/FMI_SubUV_color_A_16',root+'SubUV/MI/FMI_Subuv_Atlas_B_01',root+'BBQ_Material/MI/FM_Subuv_Lightning_Spark_002']
report={'assets':[],'missing':[],'classes':[]}
for p in paths:
    a=u.load_asset(p)
    if not a:report['missing'].append(p);continue
    export(a,a.get_name()+'.t3d');parent=a.get_editor_property('parent')
    if parent:export(parent,parent.get_name()+'.t3d')
    report['assets'].append({'path':p,'parent':parent.get_path_name() if parent else None})
for name in ['LegacyCameraShake','BlueprintFactory']:
    report['classes'].append({'name':name,'available':hasattr(u,name)})
(OUT/'Probe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
