"""Read-only census proving concurrent audio Notify data survive our animation save."""
from pathlib import Path
import os,json,re,traceback,unreal
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');OUT=Path(os.environ['KZ_MONSTER_REPAIR_OUT'])
report={'status':'running','project':str(Path(unreal.Paths.project_dir()).resolve()),'package_saves':0,'animations':{}}
def playback(n):
    row={}
    for k in ['Sound','AttachName','bFollow','bGroundMaterialSwitch','FootstepSpeedThreshold','bOnlyForLocalOrLockedTarget','StopSounds','StopFadeSeconds','SourcePackage','SourceField']:
        v=n.get_editor_property(k)
        if isinstance(v,unreal.Object):v=v.get_path_name()
        elif isinstance(v,unreal.Array):v=[x.get_path_name() if x else None for x in v]
        elif not isinstance(v,(bool,int,float,str,type(None))):v=str(v)
        row[k]=v
    return row
try:
    merged=json.loads((MAIN/'Metadata/MonsterPresentationRepair_20261011/ConcurrentAnimationMerge.json').read_text(encoding='utf-8'))
    for r in merged['animations']:
        package='/Game/'+r['path'].removeprefix('Content/').removesuffix('.uasset');seq=unreal.load_asset(package);assert seq,package
        rows=[]
        for e in unreal.AnimationLibrary.get_animation_notify_events(seq):
            n=e.get_editor_property('notify');s=e.get_editor_property('notify_state_class')
            if isinstance(n,unreal.KZAnimNotify_PlayAudio):p=n;row={'type':'Notify'}
            elif isinstance(s,unreal.KZAnimNotifyState_PlayAudio):
                p=s.get_editor_property('Playback');row={'type':'NotifyState','EndSound':s.get_editor_property('EndSound').get_path_name() if s.get_editor_property('EndSound') else None,'bStopAtEnd':s.get_editor_property('bStopAtEnd'),'FadeOutSeconds':s.get_editor_property('FadeOutSeconds')}
            else:continue
            row['event']=e.export_text();row['playback']=playback(p) if p else None;rows.append(row)
        report['animations'][r['path']]=rows
    assert any(report['animations'].values()),'Concurrent audio must exist'
    report['notify_count']=sum(map(len,report['animations'].values()));report['status']='passed'
except Exception:report['status']='failed';report['error']=traceback.format_exc();unreal.log_error(report['error'])
(OUT/'AudioCensus.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
