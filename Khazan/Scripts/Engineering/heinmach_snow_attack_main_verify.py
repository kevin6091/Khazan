"""Canonical saved-map audit and actual native PIE in a uniquely owned hidden editor.

Outside UE: Engine Python heinmach_snow_attack_main_verify.py launch
Inside UE: the same file is the startup entry; no packages or materials are saved.
"""
from array import array
import ctypes
from ctypes import wintypes
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
import uuid

ROOT=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=ROOT/'Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008'
MAP='/Game/Maps/L_HeinMach_Environment'
ALIAS='UnrealEditor-KhazanSnowWeaponContact20261008.dll'
TOKEN='KZ_SNOW_ATTACK_MAIN_VERIFY_TOKEN'
LOG=OUT/'MainVerify.log'
SOURCES=('Source/Khazan/Environment/KZSnowDeformation.h',
         'Source/Khazan/Environment/KZSnowDeformation.cpp',
         'Source/Khazan/Tests/KZSnowDeformationPIETest.cpp')

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def write(name,value):
    path=OUT/name;temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,indent=2),encoding='utf-8');temporary.replace(path)

def delivery_guard():
    receipt=read(OUT/'Delivery.json')
    assert receipt['success'],'Publish must succeed before this verifier can launch'
    assert receipt.get('map_asset',MAP)==MAP,'Only the delivered canonical map is accepted'
    module=Path(receipt['module']).resolve()
    assert module==(ROOT/'Binaries/Win64'/ALIAS).resolve(),module
    assert sha(module)==receipt['module_sha256'],'Delivered native module changed'
    manifest=read(ROOT/'Binaries/Win64/UnrealEditor.modules')
    assert manifest['Modules']['Khazan']==ALIAS,'Different module selected'
    hashes=receipt['hashes'];assert isinstance(hashes,dict)
    required=set(SOURCES)|{'Content/Maps/L_HeinMach_Environment.umap','Binaries/Win64/UnrealEditor.modules'}
    normalized={Path(name).as_posix():value for name,value in hashes.items()}
    assert required<=normalized.keys(),required-normalized.keys()
    for relative,expected in normalized.items():
        path=(ROOT/relative).resolve();assert path.is_relative_to(ROOT.resolve()),relative
        assert isinstance(expected,str) and sha(path)==expected,(relative,'Delivered file changed')
    if 'surface_profiles_sha256' in receipt:
        assert sha(OUT/'SurfaceProfiles.json')==receipt['surface_profiles_sha256']
    return receipt

def launch():
    assert Path(__file__).resolve().is_relative_to(ROOT.resolve())
    receipt=delivery_guard();token=uuid.uuid4().hex
    args=['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe',
          str(ROOT/'Khazan.uproject'),'/Engine/Maps/Entry','-unattended','-nosplash','-nosound',
          '-RenderOffscreen','-NoSourceControl','-NoLiveCoding','-windowed','-ResX=1280','-ResY=720',
          '-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
          '-EnablePlugins=GameFeatures,PythonScriptPlugin','-abslog='+str(LOG),
          '-ExecCmds=py '+str(Path(__file__).resolve())]
    protected=read(OUT/'MainReadOnly.json')['pid'] if (OUT/'MainReadOnly.json').exists() else None
    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
    process=subprocess.Popen(args,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW,
        env=dict(os.environ,**{TOKEN:token,'UE_SKIP_UBT_SDK_SETUP':'1','PYTHONUTF8':'1'}))
    assert process.pid!=protected
    write('MainVerificationLaunch.json',dict(pid=process.pid,token=token,command=args,
        protected_editor_pid=protected,module=receipt['module'],delivery_sha256=sha(OUT/'Delivery.json'),
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    print('SNOW_ATTACK_OWN_MAIN_BACKGROUND',process.pid,flush=True)
    code=process.wait()
    result=read(OUT/'MainVerification.json') if (OUT/'MainVerification.json').exists() else None
    write('MainVerificationExit.json',dict(pid=process.pid,exit_code=code,
        success=code==0 and bool(result and result.get('success')),
        utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    assert code==0 and result and result['pid']==process.pid and result['success'],result
    print('SNOW_ATTACK_OWN_MAIN_VERIFICATION_SUCCESS',process.pid,flush=True)

def verify():
    project=Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())).resolve()
    assert project==ROOT.resolve(),project
    owned=read(OUT/'MainVerificationLaunch.json')
    assert os.getpid()==owned['pid'] and os.environ.get(TOKEN)==owned['token'],'Unowned editor'
    assert os.getpid()!=owned.get('protected_editor_pid'),'User editor is protected'
    report=dict(success=False,pid=os.getpid(),project=str(ROOT),map_asset=MAP,
                native_pie_passed=False,saved_scene_passed=False,material_recompile=False,package_save=False)
    perf=settings=None;saved_throttle=None;saved_qa={};callback=None
    def console(command):
        editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        unreal.SystemLibrary.execute_console_command(editor.get_game_world() or editor.get_editor_world(),command)
    def restore():
        if perf is not None and saved_throttle is not None:
            perf.set_editor_property('bThrottleCPUWhenNotForeground',saved_throttle,
                notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
        if settings is not None:
            for key,value in saved_qa.items():settings.set_editor_property(key,value)
    def startup_failure():
        restore();report.update(error=traceback.format_exc(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        write('MainVerification.json',report);traceback.print_exc();unreal.SystemLibrary.quit_editor()
    try:
        receipt=delivery_guard()
        assert sha(OUT/'Delivery.json')==owned['delivery_sha256'],'Delivery receipt changed since launch'
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetModuleHandleW.argtypes=[wintypes.LPCWSTR];kernel.GetModuleHandleW.restype=wintypes.HMODULE
        kernel.GetModuleFileNameW.argtypes=[wintypes.HMODULE,wintypes.LPWSTR,wintypes.DWORD]
        kernel.GetModuleFileNameW.restype=wintypes.DWORD
        handle=kernel.GetModuleHandleW(ALIAS);assert handle,'Expected module not loaded'
        buffer=ctypes.create_unicode_buffer(32768);assert kernel.GetModuleFileNameW(handle,buffer,len(buffer))
        assert Path(buffer.value).resolve()==Path(receipt['module']).resolve(),buffer.value
        report.update(module_path=buffer.value,module_sha256=sha(Path(buffer.value)),delivery_sha256=owned['delivery_sha256'])
        editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        assert not editor.get_game_world(),'Startup must not already be PIE'
        world=unreal.EditorLoadingAndSavingUtils.load_map(MAP);assert world
        actors={a.get_actor_label():a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()}
        before=read(ROOT/'Saved/ImportReports/HeinMachSnow_20261006/Resume20261007/SceneBefore.json')
        assert len(actors)==9869,len(actors)
        for name,expected in before['poses'].items():
            actor=actors[name];p=actor.get_actor_location();r=actor.get_actor_rotation();s=actor.get_actor_scale3d()
            actual=[p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]
            assert all(abs(a-b)<1e-6 for a,b in zip(actual,expected)),name
        owners=[a for a in actors.values() if isinstance(a,unreal.KZSnowDeformation)];assert len(owners)==1
        owner=owners[0];assert len(owner.get_editor_property('merged_weapon_contacts'))==4
        parts=[c for a in actors.values() for c in a.get_components_by_class(unreal.StaticMeshComponent)]
        assert sum(c.component_has_tag('HeinMachSnowSurface') for c in parts)==46
        assert sum(c.component_has_tag('HeinMachMicroDressing') for c in parts)==65
        assert sum('KZHeinMachTutorialFire' in [str(t) for t in a.tags] for a in actors.values())==258
        expected=dict(receipt.get('settings',{}))
        expected.update(foot_radius_cm=[8/1.4,5/1.4],foot_contact_height_cm=8.,foot_compression=35/55,
            weapon_compression=50/55,weapon_radius_cm=100.,weapon_contact_height_cm=79.,weapon_surface_contact_tolerance_cm=6.)
        actual_settings={}
        for key,value in expected.items():
            actual=owner.get_editor_property(key)
            if isinstance(value,list):
                actual=[float(actual.x),float(actual.y)]
                assert len(actual)==len(value) and all(abs(a-b)<1e-6 for a,b in zip(actual,value)),(key,actual,value)
            else:
                actual=float(actual);assert abs(actual-value)<1e-6,(key,actual,value)
            actual_settings[key]=actual
        baked=read(OUT/'SurfaceProfiles.json');assert baked['success'] and len(baked['profiles'])==2
        loaded=owner.get_editor_property('surface_contact_samples');assert len(loaded)==2
        by_material={row.get_editor_property('material').get_path_name().split('.')[0]:row for row in loaded}
        profiles=[];materials=[]
        for entry in baked['profiles']:
            actual=by_material[entry['material']];resolution=actual.get_editor_property('resolution')
            assert [resolution.x,resolution.y]==entry['resolution']
            count=resolution.x*resolution.y*3;assert count==entry['samples_count']
            binary=Path(entry['samples_file']);assert binary.stat().st_size==count*4==entry['bytes']
            assert sha(binary)==entry['samples_sha256']
            samples=array('f');samples.frombytes(binary.read_bytes())
            if sys.byteorder!='little':samples.byteswap()
            serialized=list(actual.get_editor_property('samples'))
            assert len(serialized)==count and serialized==list(samples),'Serialized profile samples differ from baked bytes'
            for key in ('uv_origin_cm','uv_scale_cm'):
                vector=actual.get_editor_property(key)
                assert all(abs(a-b)<1e-6 for a,b in zip((vector.x,vector.y),entry[key])),key
            for key in ('depth_reference_cm','rim_height_cm'):
                assert abs(actual.get_editor_property(key)-entry[key])<1e-6,key
            assert abs(entry['depth_reference_cm']-55.)<1e-6 and abs(entry['rim_height_cm']-12.)<1e-6
            material=unreal.load_asset(entry['material']);assert material
            params={str(node.get_editor_property('parameter_name')):float(node.get_editor_property('default_value'))
                for node in unreal.MaterialEditingLibrary.get_material_expressions(material)
                if isinstance(node,unreal.MaterialExpressionScalarParameter)}
            for key,value in [('SnowHeightCm_DeepSnow',55.),('HM_DepthReferenceCm_User',55.),('SnowRimHeightCm_Temporary',12.)]:
                assert abs(params[key]-value)<1e-6,(entry['material'],key,params[key])
            assert abs(material.get_editor_property('displacement_scaling').magnitude-.75)<1e-6
            profiles.append(dict(material=entry['material'],resolution=entry['resolution'],samples_count=count,
                samples_sha256=entry['samples_sha256'],uv_origin_cm=entry['uv_origin_cm'],uv_scale_cm=entry['uv_scale_cm']))
            materials.append(dict(asset=entry['material'],height_cm=55.,depth_reference_cm=55.,rim_height_cm=12.,displacement_magnitude=.75))
        report.update(saved_scene_passed=True,actors=len(actors),source_poses_preserved=len(before['poses']),
            snow_surfaces=46,micro_dressing=65,fire_actors=258,native_weapon_profiles=4,
            snow_contact_settings=actual_settings,surface_profiles=profiles,snow_material_depth=materials)
        perf=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
        saved_throttle=perf.get_editor_property('bThrottleCPUWhenNotForeground')
        perf.set_editor_property('bThrottleCPUWhenNotForeground',False,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
        settings=unreal.get_default_object(unreal.load_class(None,'/Script/Engine.AutomationTestSettings'))
        for key in ('DefaultInteractiveFramerate','DefaultInteractiveFramerateDuration'):
            saved_qa[key]=settings.get_editor_property(key);settings.set_editor_property(key,1.)
        state=dict(offset=LOG.stat().st_size,started=False,requested=False,native_log='',deadline=time.monotonic()+420.)
        def finish(success,error=None):
            nonlocal callback
            try:
                delivery_guard()
                assert sha(OUT/'Delivery.json')==owned['delivery_sha256'],'Receipt changed during verification'
                if success:
                    for fixture in ('PlayerWeakBegin','PlayerGroundContact','PlayerNearSurfaceAir','PlayerAirAttack'):
                        assert 'SnowActualAttack fixture='+fixture in state['native_log'],fixture
                    for fixture in ('MonsterAttackBegin','MonsterGroundContact','MonsterAirAttack'):
                        assert state['native_log'].count('SnowActualAttack fixture='+fixture)>=4,fixture
            except Exception:
                success=False;error=traceback.format_exc()
            console('csvprofile stop');unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play();restore()
            report.update(success=success,native_pie_passed=success,error=error,utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
            write('MainVerification.json',report);unreal.unregister_slate_post_tick_callback(callback)
            print('SNOW_ATTACK_MAIN_NATIVE_VERIFICATION',success,json.dumps(report))
            quit_at=time.monotonic()+3.
            def quit_tick(delta):
                if time.monotonic()<quit_at:return
                unreal.unregister_slate_post_tick_callback(quit_handle);unreal.SystemLibrary.quit_editor()
            quit_handle=unreal.register_slate_post_tick_callback(quit_tick)
        def tick(delta):
            try:
                if time.monotonic()>state['deadline']:return finish(False,'Owned canonical native PIE deadline')
                with LOG.open(encoding='utf-8',errors='replace') as stream:
                    stream.seek(state['offset']);chunk=stream.read();state['offset']=stream.tell()
                state['native_log']+=chunk
                if 'Test Started. Name={PIE} Path={Khazan.Snow.PIE}' in state['native_log']:state['started']=True
                if state['started'] and not state['requested'] and not editor.get_game_world():
                    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play();state['requested']=True
                if 'Test Completed. Result={Success} Name={PIE} Path={Khazan.Snow.PIE}' in state['native_log']:return finish(True)
                if 'Test Completed. Result={Fail} Name={PIE} Path={Khazan.Snow.PIE}' in state['native_log']:return finish(False,'See native assertions in MainVerify.log')
            except Exception:return finish(False,traceback.format_exc())
        callback=unreal.register_slate_post_tick_callback(tick)
        console('csvprofile start');console('CsvCategory HeinMachSnow enable');console('Automation RunTests Khazan.Snow.PIE')
        print('SNOW_ATTACK_MAIN_CANONICAL_SCENE_AUDITED',json.dumps(report))
    except Exception:startup_failure()

try:
    import unreal
except ImportError:
    if __name__=='__main__':
        assert len(sys.argv)==2 and sys.argv[1]=='launch','Use: Engine Python this_script.py launch'
        launch()
else:
    verify()
