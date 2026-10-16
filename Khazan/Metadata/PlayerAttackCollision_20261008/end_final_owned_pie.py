import os,json,datetime
from pathlib import Path
assert os.getpid()==26104
unreal.unregister_slate_post_tick_callback(ACTUAL_QA['handle'])
state={k:v for k,v in ACTUAL_QA['s'].items() if k not in ('world','player','target','input','action','anim','attrs')}
state.update(done=True,error='Optional Python visual probe used unavailable unreal.AbilitySystemBlueprintLibrary; not a runtime product result',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),counted_as_verification=False)
Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/PlayerAttackCollision_20261008/ActualWeakNormalTarget.json').write_text(json.dumps(state,indent=2,default=str),encoding='utf-8')
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
print('SUPPLEMENTAL_HELPER_STOPPED; OWNED_PIE_END_REQUESTED')
