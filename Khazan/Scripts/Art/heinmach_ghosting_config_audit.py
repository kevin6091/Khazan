"""Read startup defaults in a fresh hidden editor; no setters or console commands."""
from pathlib import Path
import hashlib
import json
import os
import traceback
import unreal
STAGE=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
ROOT=STAGE.parents[2]
assert STAGE==ROOT/'Saved/ArtStaging/HeinMachGhostingParts_20261008',STAGE
OUT=ROOT/'Saved/ImportReports/HeinMachGhosting_20261008'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
R={'success':False,'project':str(STAGE),'pid':os.getpid(),'forced_cvars':False,'main_writes':False}
try:
    R['config_hashes']={name:{'main':sha(ROOT/'Config'/name),'private':sha(STAGE/'Config'/name)}
                        for name in ('DefaultEngine.ini','DefaultEditor.ini')}
    assert all(v['main']==v['private'] for v in R['config_hashes'].values())
    names=('r.TSR.Velocity.WeightClampingSampleCount',
           'r.Editor.Viewport.ScreenPercentageMode.RealTime',
           'r.Editor.Viewport.ScreenPercentageMode.NonRealTime',
           'r.Editor.Viewport.ScreenPercentage')
    R['startup_cvars']={name:unreal.SystemLibrary.get_console_variable_float_value(name) for name in names}
    project=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceProjectSettings'))
    user=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
    R['project_settings']={'ManualScreenPercentage':project.get_editor_property('ManualScreenPercentage')}
    R['user_settings']={'bOverrideManualScreenPercentage':user.get_editor_property('bOverrideManualScreenPercentage'),
                        'bOverridePIEScreenPercentage':user.get_editor_property('bOverridePIEScreenPercentage')}
    for label,obj in (('project_settings',project),('user_settings',user)):
        for k in ('RealtimeScreenPercentageMode','NonRealtimeScreenPercentageMode'):
            try:R[label][k]=str(obj.get_editor_property(k))
            except Exception as e:R[label][k]={'not_pythonizable':str(e)}
    assert R['startup_cvars'][names[0]]==2
    assert R['startup_cvars'][names[1]]==0
    assert R['startup_cvars'][names[2]]==0
    assert R['startup_cvars'][names[3]]==100
    assert R['project_settings']['ManualScreenPercentage']==100
    assert not R['user_settings']['bOverrideManualScreenPercentage']
    R['success']=True
    print('KZ_HEINMACH_GHOST_CONFIG_STARTUP_PASSED')
except Exception:
    R['error']=traceback.format_exc()
    raise
finally:
    (OUT/'FreshConfigAudit.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
