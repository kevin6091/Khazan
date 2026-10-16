"""Lightweight owned Entry PIE: visible flash and active-particle readback."""
from pathlib import Path
import json,os,time,traceback,unreal as u
OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT']);ROOT=Path(u.Paths.project_dir()).resolve()
R={'status':'running','samples':[],'asset_saves':0};start=time.monotonic();phase=0;busy=False
u.load_object(None,'/Script/UnrealEd.Default__EditorPerformanceSettings').set_editor_property('bThrottleCPUWhenNotForeground',False)
def finish(error=None):
 global phase
 if phase==99:return
 phase=99;u.unregister_slate_post_tick_callback(handle)
 R['status']='failed' if error else 'passed'
 if error:R['error']=error
 (OUT/'ParticleRuntime.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
 u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play();u.SystemLibrary.quit_editor()
def tick(delta):
 global phase,busy,component,world,camera,rt,born,frame
 if busy or phase==99:return
 busy=True
 try:
  if time.monotonic()-start>180:finish('Owned particle probe timeout');return
  if phase==0:
   if time.monotonic()-start<3:return
   u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(u.SceneCapture2D,u.Vector(-250,0,100),u.Rotator())
   u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_begin_play();phase=1;return
  if phase==1:
   world=u.EditorLevelLibrary.get_game_world()
   if not world:return
   player=u.GameplayStatics.get_player_character(world,0)
   if player:player.set_actor_hidden_in_game(True)
   cameras=u.GameplayStatics.get_all_actors_of_class(world,u.SceneCapture2D)
   if not cameras:return
   camera=cameras[0]
   capture=camera.get_component_by_class(u.SceneCaptureComponent2D)
   rt=u.RenderingLibrary.create_render_target2d(world,512,512,u.TextureRenderTargetFormat.RTF_RGBA8)
   capture.set_editor_property('texture_target',rt);capture.set_editor_property('capture_source',u.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
   capture.set_editor_property('capture_every_frame',False)
   capture.set_editor_property('fov_angle',60)
   component=u.GameplayStatics.spawn_emitter_at_location(world,u.load_asset('/Game/_Art/Effects/Combat/AttackContact/PP_Monster_HitFlameFlash'),u.Vector(0,0,100),u.Rotator(),u.Vector(1,1,1),True)
   born=time.monotonic();frame=0;phase=2;return
  if phase==2:
   particles=component.get_num_active_particles();R['samples'].append({'frame':frame,'particles':particles})
   if frame in [2,5,9,14]:
    camera.get_component_by_class(u.SceneCaptureComponent2D).capture_scene()
    u.RenderingLibrary.export_render_target(world,rt,str(OUT),'Flash_%02d.png'%frame)
   frame+=1
   if frame>=20:finish()
 except Exception:finish(traceback.format_exc())
 finally:busy=False
handle=u.register_slate_post_tick_callback(tick)
