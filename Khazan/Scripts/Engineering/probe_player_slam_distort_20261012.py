"""Inspect only the requested Niagara system and existing plunge landing marker."""
from pathlib import Path
import json, os, traceback, unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_PARRY_OUT'])
report={'success':False,'project':str(ROOT),'asset_saves':0}
try:
    effect=u.load_asset('/Game/VFX/03_SlashHit/KZ_Parring_Distort');assert effect
    report['effect']={'path':effect.get_path_name(),'class':effect.get_class().get_name()}
    for object,name in [(effect,'Niagara'),(u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/FallAttack/AM_DAS_FallAttack'),'Montage')]:
        task=u.AssetExportTask();task.object=object;task.exporter=u.ObjectExporterT3D();task.filename=str(OUT/(name+'.t3d'));task.automated=True;task.prompt=False
        assert u.Exporter.run_asset_export_task(task)
    montage=u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/FallAttack/AM_DAS_FallAttack')
    report['ground_markers']=[];report['notifies']=[]
    for event in u.AnimationLibrary.get_animation_notify_events(montage):
        parent=event.get_editor_property('notify')
        report['notifies'].append(event.export_text())
        if isinstance(parent,u.KZAnimNotify_CombatEffect):
            for child in [parent]+list(parent.get_editor_property('batched_effects')):
                if str(child.get_editor_property('event_id'))=='KZExtra_PlungeGround':
                    report['ground_markers'].append({'event':event.export_text(),'data':{key:str(child.get_editor_property(key)) for key in ['EventId','WindowStartTime','WindowEndTime','bEndEvent','SourceSocket','RelativeLocation','bSpawnOnFloor','bAbsoluteRotation','bDestroyOnNotifyEnd','bDestroyOnAnimEnd']}})
    report['success']=True
except Exception:report['error']=traceback.format_exc()
finally:
    (OUT/'Probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('SLAM_DISTORT_PROBE',report['success'],report.get('error',''))
if not report['success']:raise RuntimeError(report.get('error','Probe failed'))
