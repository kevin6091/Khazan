"""Fresh native readback of the selected saved montage additions, no saves."""
from pathlib import Path
import json,os,hashlib,collections,unreal as u
ROOT=Path(u.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
plan=json.loads((ROOT/'Metadata/CombatFinishFollowup_20261012/Authored.json').read_text(encoding='utf-8'))
report={'status':'running','montages':[],'effects':[],'asset_saves':0}
expected={r['id']:r for r in plan['extra_effects']}
seen=collections.defaultdict(list)
for row in plan['montages']:
    path=row['path'];file=ROOT/('Content/'+path.split('.')[0].removeprefix('/Game/')+'.uasset')
    assert hashlib.sha256(file.read_bytes()).hexdigest()==row['after']
    montage=u.load_asset(path);events=list(u.AnimationLibrary.get_animation_notify_events(montage))
    assert len(events)==row['new_events']
    assert len(set(u.AnimationLibrary.get_anim_notify_event_trigger_time(e) for e in events))==len(events)
    for event in events:
        parent=event.get_editor_property('notify')
        if not isinstance(parent,u.KZAnimNotify_CombatEffect):continue
        for child in [parent]+list(parent.get_editor_property('BatchedEffects')):
            identifier=str(child.get_editor_property('EventId'))
            if identifier not in expected:continue
            original=expected[identifier];ending=child.get_editor_property('bEndEvent')
            seen[identifier].append(ending)
            assert child.get_editor_property('WindowStartTime')==original['start']
            assert child.get_editor_property('WindowEndTime')==original['end']
            scale=child.get_editor_property('Scale3D');assert abs(scale.x-original['scale'])<1e-6
            assert child.get_editor_property('bDestroyOnNotifyEnd') and child.get_editor_property('bDestroyOnNotifyEndDeactived')
            if not ending:report['effects'].append({'id':identifier,'montage':path,'start':original['start'],'end':original['end'],'socket':str(child.get_editor_property('SourceSocket')),'floor':child.get_editor_property('bSpawnOnFloor')})
    report['montages'].append({'path':path,'events':len(events),'sha256':row['after']})
assert set(seen)==set(expected)
assert all(sorted(v)==[False,True] for v in seen.values())
report['effect_windows']=len(seen);report['dirty']=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
assert not report['dirty'];report['status']='passed'
(OUT/'SavedAudit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('FRESH_SAVED_PASSED',len(report['montages']),len(seen))
