import os,time,json
from pathlib import Path
assert os.getpid()==2252
out=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/PlayerAttackCollision_20261008')
log=out/'OwnedPIEEditor.log'
tests=['Khazan.Guard.PIE','Khazan.Heal.PIE']
state={'index':0,'phase':'stop','results':[],'done':False}
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
def checkpoint():
    (out/'GuardHealRegression.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
def regression_tick(delta):
    if state['done']:return
    if state['phase']=='stop':
        level.editor_request_end_play();state['phase']='wait_stop';checkpoint()
    elif state['phase']=='wait_stop' and not editor.get_game_world():
        state['offset']=log.stat().st_size;state['deadline']=time.monotonic()+180
        console('Automation RunTests '+tests[state['index']]);state['phase']='wait_test';checkpoint()
    elif state['phase'] in ('wait_test','observe'):
        with log.open('r',encoding='utf-8',errors='replace') as f:
            f.seek(state['offset']);new=f.read()
        test=tests[state['index']]
        lines=[line for line in new.splitlines() if 'Path={'+test+'}' in line]
        if state['phase']=='wait_test' and any('Test Started.' in line for line in lines):
            level.editor_request_begin_play();state['phase']='observe';checkpoint()
        completed=[line for line in lines if 'Test Completed.' in line]
        if completed:
            state['results'].append({'test':test,'success':'Result={Success}' in completed[-1],'line':completed[-1]})
            state['index']+=1
            if state['index']==len(tests):
                state['done']=True;unreal.unregister_slate_post_tick_callback(handle)
            else:state['phase']='stop'
            checkpoint()
        elif time.monotonic()>state['deadline']:
            state.update(done=True,error='Timed out: '+test);unreal.unregister_slate_post_tick_callback(handle);checkpoint()
handle=unreal.register_slate_post_tick_callback(regression_tick)
checkpoint()
print('GUARD_HEAL_REGRESSION_REGISTERED')
