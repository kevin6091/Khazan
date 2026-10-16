"""Reuse opaque-background native VFX colour comparison; bind loaded module."""
from pathlib import Path
import ctypes,hashlib,json,os
import unreal as u
main=Path(os.environ['KZ_LOOKSPIN_MAIN']);project=Path(u.Paths.project_dir()).resolve()
exec(compile((main/'Scripts/Art/probe_heinmach_vfx_colours_20261015.py').read_text(encoding='utf-8'),__file__,'exec'),globals())
extra='/Game/_Art/Effects/Combat/Spinning/PP_Spinning_OverFury_Accent'
selected=os.environ.get('KZ_HM_COLOUR_PROBE_ASSETS','')
if u.EditorAssetLibrary.does_asset_exist(extra) and (not selected or extra in selected.split(',')):
    assert not any(x['asset']==extra for x in systems)
    systems.append({'asset':extra,'class':'ParticleSystem'})
report['catalogue_scope']='Prior current321 references plus the one Spin-only OverFury copy; original systems remain byte-identical.'
manifest=json.loads((project/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.GetModuleHandleW.argtypes=[ctypes.c_wchar_p];kernel.GetModuleHandleW.restype=ctypes.c_void_p
kernel.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint];kernel.GetModuleFileNameW.restype=ctypes.c_uint
name=manifest['Modules']['Khazan'];handle_module=kernel.GetModuleHandleW(name)
buffer=ctypes.create_unicode_buffer(32768)
assert handle_module and kernel.GetModuleFileNameW(handle_module,buffer,len(buffer))
module=Path(buffer.value).resolve();assert module.is_relative_to(project/'Binaries')
report['actual_module']=str(module);report['module_sha256']=hashlib.sha256(module.read_bytes()).hexdigest()
report['background_contract']='Opaque neutral unlit inverse-exposure panel: matched pre-refraction scene colour; unsaved QA only.'
u.SystemLibrary.execute_console_command(world,'DisableAllScreenMessages')
report['screen_messages_disabled_QA']=True
if os.environ.get('KZ_LOOKSPIN_DELAY_READBACK')=='1':
    BASE_IMAGE_READY=image_ready
    READBACK_ISSUED=False;PENDING_RENDER_FRAME=0
    def shot(name):
        global pending_image,pending_since,READBACK_ISSUED,PENDING_RENDER_FRAME
        u.GameplayStatics.set_game_paused(game,True)
        pending_image=out/name;pending_since=time.monotonic();READBACK_ISSUED=False
        PENDING_RENDER_FRAME=u.SystemLibrary.get_frame_count()
        u.GameplayStatics.get_player_controller(game,0).set_view_target_with_blend(camera,0)
    def image_ready():
        global READBACK_ISSUED
        if not READBACK_ISSUED:
            frames=int(os.environ.get('KZ_LOOKSPIN_RENDER_FRAME_WAIT','0'))
            ready=u.SystemLibrary.get_frame_count()>=PENDING_RENDER_FRAME+frames if frames else time.monotonic()-pending_since>=.12
            if ready:
                u.SystemLibrary.execute_console_command(game,'KZ.QA.ColourShot "'+str(pending_image)+'"')
                READBACK_ISSUED=True
            return False
        return BASE_IMAGE_READY()
    report['method']='Native ReadPixels after paused render settling; fixed .2s simulation; zero debug overlay'
    report['paused_settling_QA']={'engine_frames':int(os.environ.get('KZ_LOOKSPIN_RENDER_FRAME_WAIT','0')),
                                 'minimum_seconds_if_frame_mode_zero':.12}
if os.environ.get('KZ_LOOKSPIN_DIAGNOSTIC_NO_FOG')=='1':
    for cvar in ['r.Fog','r.VolumetricFog','r.SkyAtmosphere']:
        u.SystemLibrary.execute_console_command(world,cvar+' 0')
    report['diagnostic_only']='Global native fog/atmosphere disabled only in this unsaved QA process to isolate opaque-particle colour.'
