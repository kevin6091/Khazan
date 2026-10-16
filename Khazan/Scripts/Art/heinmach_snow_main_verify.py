"""Read-only saved-main audit plus transient native PIE, only in the owned background process."""
from pathlib import Path
import ctypes
from ctypes import wintypes
import datetime
import json
import os
import time
import unreal
ROOT=Path(unreal.Paths.project_dir()).resolve()
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=ROOT/'Saved/ImportReports/HeinMachSnow_20261006'
launch=json.loads((OUT/'MainVerificationLaunch.json').read_text())
assert os.environ.get('KZ_SNOW_MAIN_VERIFY_TOKEN')==launch['token'] and os.getpid()==launch['pid']
assert os.getpid()!=7220
LOG=OUT/'main_verify.log'
PERF=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
THROTTLE=PERF.get_editor_property('bThrottleCPUWhenNotForeground')
PERF.set_editor_property('bThrottleCPUWhenNotForeground',False,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
settings=unreal.get_default_object(unreal.load_class(None,'/Script/Engine.AutomationTestSettings'))
settings.set_editor_property('DefaultInteractiveFramerate',1.0)
settings.set_editor_property('DefaultInteractiveFramerateDuration',1.0)
contact_path=OUT/'Contact55_20261007/Delivery.json'
contact_receipt=json.loads(contact_path.read_text(encoding='utf-8')) if contact_path.exists() else None
map_asset=contact_receipt.get('map_asset',contact_receipt.get('preview_map_asset','/Game/Maps/L_HeinMach_Environment')) if contact_receipt else '/Game/Maps/L_HeinMach_Environment'
assert map_asset in ('/Game/Maps/L_HeinMach_Environment','/Game/Maps/L_HeinMach_Environment_Contact55_20261007')
world=unreal.EditorLoadingAndSavingUtils.load_map(map_asset)
actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
before=json.loads((OUT/'Resume20261007/SceneBefore.json').read_text())
assert len(actors)==9869
for name,p in before['poses'].items():
    a=actors[name];v=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
    assert max(abs(x-y) for x,y in zip(p,[v.x,v.y,v.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]))<1e-6,name
snow=[a for a in actors.values() if isinstance(a,unreal.KZSnowDeformation)];assert len(snow)==1
assert len(snow[0].get_editor_property('merged_weapon_contacts'))==4
parts=[c for a in actors.values() for c in a.get_components_by_class(unreal.StaticMeshComponent)]
assert sum(c.component_has_tag('HeinMachSnowSurface') for c in parts)==46
assert sum(c.component_has_tag('HeinMachMicroDressing') for c in parts)==65
assert len([a for a in actors.values() if 'KZHeinMachTutorialFire' in [str(t) for t in a.tags]])==258
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.GetModuleHandleW.argtypes=[wintypes.LPCWSTR];kernel.GetModuleHandleW.restype=wintypes.HMODULE
kernel.GetModuleFileNameW.argtypes=[wintypes.HMODULE,wintypes.LPWSTR,wintypes.DWORD];kernel.GetModuleFileNameW.restype=wintypes.DWORD
module_name=json.loads((ROOT/'Binaries/Win64/UnrealEditor.modules').read_text())['Modules']['Khazan']
module=kernel.GetModuleHandleW(module_name);assert module
buffer=ctypes.create_unicode_buffer(32768);assert kernel.GetModuleFileNameW(module,buffer,len(buffer))
report=dict(project=str(ROOT),pid=os.getpid(),module_path=buffer.value,map_asset=map_asset,actors=len(actors),
    source_poses_preserved=len(before['poses']),snow_surfaces=46,micro_dressing=65,fire_actors=258,
    native_weapon_profiles=4,saved_scene_passed=True,native_pie_passed=False)
broad_delivery=OUT/'BroadBrush20261007/Delivery.json'
contact_delivery=OUT/'Contact55_20261007/Delivery.json'
deep_delivery=contact_delivery if contact_delivery.exists() else OUT/'DeepSnow20261007/Delivery.json'
depth_receipt=json.loads(deep_delivery.read_text(encoding='utf-8')) if deep_delivery.exists() else None
def read_snow_settings(expected):
    actual={}
    for key,value in expected.items():
        p=snow[0].get_editor_property(key)
        actual[key]=[float(p.x),float(p.y)] if isinstance(value,list) else float(p)
        if isinstance(value,list):
            assert len(actual[key])==len(value) and all(abs(a-b)<1e-6 for a,b in zip(actual[key],value)),(key,actual[key],value)
        else:
            assert abs(actual[key]-value)<1e-6,(key,actual[key],value)
    return actual
if broad_delivery.exists():
    expected=json.loads(broad_delivery.read_text(encoding='utf-8'))['settings']
    if depth_receipt:
        expected.update({key:value for key,value in depth_receipt['settings'].items() if key in expected})
    report['snow_contact_settings']=read_snow_settings(expected)
if depth_receipt:
    report['snow_depth_settings']=read_snow_settings(depth_receipt['settings'])
    materials=[]
    material_assets=depth_receipt['material_assets']
    for asset in material_assets:
        mat=unreal.load_asset(asset)
        params={str(n.get_editor_property('parameter_name')):n.get_editor_property('default_value')
            for n in unreal.MaterialEditingLibrary.get_material_expressions(mat) if isinstance(n,unreal.MaterialExpressionScalarParameter)}
        expected_height=55. if deep_delivery==contact_delivery else 60.
        assert abs(params['SnowHeightCm_DeepSnow']-expected_height)<1e-6 and abs(params['SnowRimHeightCm_Temporary']-12.)<1e-6
        if deep_delivery==contact_delivery:
            assert abs(params['HM_DepthReferenceCm_User']-55.)<1e-6
        assert abs(mat.get_editor_property('displacement_scaling').magnitude-0.75)<1e-6
        errors=list(unreal.MaterialEditingLibrary.recompile_material(mat));assert not errors,errors
        materials.append(dict(asset=mat.get_path_name(),parameters={k:v for k,v in params.items() if k.startswith('SnowHeightCm_') or k in ('SnowRimHeightCm_Temporary','HM_DepthReferenceCm_User')},compile_errors=errors))
    report['snow_material_depth']=materials
state=dict(offset=LOG.stat().st_size,started=False,requested=False,result=None,deadline=time.monotonic()+420)
def console(command):unreal.SystemLibrary.execute_console_command(world,command)
console('csvprofile start');console('CsvCategory HeinMachSnow enable')
console('Automation RunTests Khazan.Snow.PIE')
def finish(success,error=None):
    console('csvprofile stop')
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
    PERF.set_editor_property('bThrottleCPUWhenNotForeground',THROTTLE,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    report.update(success=success,native_pie_passed=success,error=error,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    (OUT/'MainVerification20261007.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    print('SNOW_MAIN_NATIVE_VERIFICATION',success,json.dumps(report))
    # Allow the asynchronous CSV writer to finish before exiting our own editor.
    state['quit_at']=time.monotonic()+3
    def quit_tick(delta):
        if time.monotonic()<state['quit_at']:return
        unreal.unregister_slate_post_tick_callback(QUIT_HANDLE);console('QUIT_EDITOR')
    QUIT_HANDLE=unreal.register_slate_post_tick_callback(quit_tick)
def verify_tick(delta):
    if time.monotonic()>state['deadline']:return finish(False,'Owned main PIE deadline')
    with LOG.open(encoding='utf-8',errors='replace') as stream:
        stream.seek(state['offset']);chunk=stream.read();state['offset']=stream.tell()
    if 'Test Started. Name={PIE} Path={Khazan.Snow.PIE}' in chunk:state['started']=True
    if state['started'] and not state['requested'] and not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world():
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play();state['requested']=True
    if 'Test Completed. Result={Success} Name={PIE} Path={Khazan.Snow.PIE}' in chunk:return finish(True)
    if 'Test Completed. Result={Fail} Name={PIE} Path={Khazan.Snow.PIE}' in chunk:return finish(False,'See native assertion in main_verify.log')
HANDLE=unreal.register_slate_post_tick_callback(verify_tick)
print('SNOW_MAIN_SAVED_SCENE_AUDITED',json.dumps(report))
