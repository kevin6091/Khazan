"""Existing native attack/lifetime tests; only QA fixture/inspection selection changes."""
from pathlib import Path
import os,unreal as u
main=Path(os.environ['KZ_LOOKSPIN_MAIN']);project=Path(u.Paths.project_dir()).resolve()
out=Path(os.environ['KZ_LOOKSPIN_OUT'])
HEIN_QA=os.environ.get('KZ_LOOKSPIN_LEVEL')=='HeinMach'
os.environ.update(KZ_MONSTER_PHYSICS_OUT=str(out),KZ_MONSTER_REPAIR_OUT=str(out),
 KZ_MONSTER_PHYSICS_TESTS=os.environ.get('KZ_LOOKSPIN_TESTS','Khazan.CombatEffect.PIE,Khazan.Combat.PlayerAttackCollision.PIE'),
 KZ_SLASH_INSPECT='1',KZ_SLASH_INSPECT_NODE=os.environ.get('KZ_LOOKSPIN_NODE','SpinningAttack01'),
 KZ_SLASH_COMPOSED_ONLY='1',KZ_ATTACK_VFX_TRANSFORM_JSONL=str(out/'NativeTransforms.jsonl'))
def isolate_ai():
    # Only transient QA instances. Preserve target classes and all saved AI settings.
    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        if isinstance(actor,u.KZMonster):
            actor.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
            actor.set_editor_property('ai_controller_class',None)
    if HEIN_QA:
        world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
        actors=u.get_editor_subsystem(u.EditorActorSubsystem)
        start=next(a for a in actors.get_all_level_actors() if isinstance(a,u.PlayerStart))
        p=u.Vector(10094.534774,-6517.085901,-5174.297077)
        hit=None
        for p in [p,start.get_actor_location()]:
            hit=u.SystemLibrary.line_trace_single_by_profile(world,p+u.Vector(0,0,500),p-u.Vector(0,0,1500),
                'Pawn',True,[],u.DrawDebugTrace.NONE,True)
            if hit and hit.to_dict()['blocking_hit']:break
        assert hit and hit.to_dict()['blocking_hit'],'Transient HeinMach review needs a real floor'
        point=u.get_default_object(u.GameplayStatics).call_method('BreakHitResult',args=(hit,))[4]
        # QA-only spawn clearance; native wait requires the pawn to land first.
        start.set_actor_location(point+u.Vector(0,0,200),False,False)
        start.set_actor_rotation(u.Rotator(pitch=0,yaw=177.083725,roll=0),False)
        for i,name in enumerate(('Swordsman','SwordShield','HeavySwordsman','HalberdElite')):
            cls=u.load_class(None,'/Game/Bluprints/Monsters/BP_Monster_'+name+'.BP_Monster_'+name+'_C');assert cls
            actor=actors.spawn_actor_from_class(cls,point+u.Vector(20000+400*i,0,300))
            actor.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED)
            actor.set_editor_property('ai_controller_class',None)
            actor.get_component_by_class(u.CharacterMovementComponent).set_movement_mode(u.MovementMode.MOVE_NONE)
    hidden=set(os.environ.get('KZ_LOOKSPIN_HIDE_LAYERS','').split(','))-{''}
    if hidden:
        asset=u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/SpinningAttack/AM_DAS_Player_SpinningAttack')
        changed=[]
        for event in u.AnimationLibrary.get_animation_notify_events(asset):
            parent=event.get_editor_property('Notify')
            if not isinstance(parent,u.KZAnimNotify_CombatEffect):continue
            for fx in [parent]+list(parent.get_editor_property('BatchedEffects')):
                ident=str(fx.get_editor_property('EventId'))
                particle=fx.get_editor_property('ParticleTemplate')
                suppress=any('KZSpin'+role+'_' in ident for role in hidden)
                suppress=suppress or ('Original' in hidden and particle and particle.get_name()=='FP_Kazan_SpinningBeast_Axe_Slash_01')
                if suppress:
                    fx.set_editor_property('ParticleTemplate',None);changed.append(ident)
        import json
        (out/'TransientLayerIsolation.json').write_text(json.dumps(dict(hidden=sorted(hidden),changed=changed,asset_saves=0),indent=2),encoding='utf-8')
source=(main/'Scripts/Engineering/monster_physics_validation_driver_20261013.py').read_text(encoding='utf-8')
old="assert PROJECT in (MAIN,MAIN.parent.parent/'Khazan_PlayerPartsWork_20261007/Khazan')"
assert source.count(old)==1;source=source.replace(old,'assert PROJECT == Path('+repr(str(project))+')')
warmup="if time.monotonic()-LAST<5:return"
assert source.count(warmup)==1
source=source.replace(warmup,warmup+'\n            isolate_ai()',1)
if HEIN_QA:source=source.replace("load_level('/Game/Maps/DevMap')","load_level('/Game/Maps/L_HeinMach_Environment')",1)
old="if test.endswith('.PIE') or test.endswith('KnockbackPIE'):"
assert source.count(old)==1
source=source.replace(old,"if (test.endswith('.PIE') or test.endswith('KnockbackPIE')) and test != 'Khazan.CombatEffect.PIE':",1)
source=source.replace("(OUT/'Driver.json').write_text", "report['material_compile_failures']=[line for line in (OUT/'Editor.log').read_text(encoding='utf-8',errors='replace').splitlines() if 'Failed to compile Material' in line or 'Default Material will be used' in line]\n    if report['material_compile_failures']:report['status']='failed'\n    (OUT/'Driver.json').write_text",1)
exec(compile(source,__file__,'exec'),globals())
if os.environ.get('KZ_LOOKSPIN_NATIVE_SHOTS')=='1':
    import json
    SPIN_ASSET=u.load_asset('/Game/_Art/Player/Animation/InGame/DAS/SpinningAttack/AM_DAS_Player_SpinningAttack')
    SHOT_TIMES=[.34,.5,.7,1.03,1.18,1.30,1.43,1.60,1.80,2.0]
    SPIN_SHOTS=[];SHOT_SEEN=set();SPIN_CAMERA_OFFSET=None
    def spin_native_shot(delta):
        global SPIN_CAMERA_OFFSET
        game=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
        if not game:return
        player=u.GameplayStatics.get_player_pawn(game,0)
        if not player:return
        if os.environ.get('KZ_LOOKSPIN_HIDE_CHARACTER')=='1':
            for part in player.get_components_by_class(u.SkeletalMeshComponent):part.set_visibility(False,False)
        mesh=player.get_editor_property('mesh');anim=mesh.get_anim_instance()
        if not anim or not anim.montage_is_playing(SPIN_ASSET):return
        pos=anim.montage_get_position(SPIN_ASSET)
        if os.environ.get('KZ_LOOKSPIN_TRACK_CAMERA')=='1':
            pc=u.GameplayStatics.get_player_controller(game,0);camera=pc.get_view_target()
            if isinstance(camera,u.CameraActor):
                if SPIN_CAMERA_OFFSET is None:
                    rot=player.get_actor_rotation()
                    SPIN_CAMERA_OFFSET=u.MathLibrary.get_forward_vector(rot)*(-480)+u.MathLibrary.get_right_vector(rot)*80+u.Vector(0,0,250)
                chest=mesh.get_socket_location('Bip001-Spine2')
                location=chest+SPIN_CAMERA_OFFSET
                camera.set_actor_location(location,False,False)
                camera.set_actor_rotation(u.MathLibrary.find_look_at_rotation(location,chest),False)
        due=[(i,t) for i,t in enumerate(SHOT_TIMES) if i not in SHOT_SEEN and pos>=t]
        if not due:return
        i,t=due[-1]
        for j,_ in due:SHOT_SEEN.add(j)
        file='SpinNative_%02d.png'%i
        u.SystemLibrary.execute_console_command(game,'KZ.QA.ColourShot "'+str(out/file)+'"')
        SPIN_SHOTS.append(dict(montage_seconds=pos,target_seconds=t,image=file))
    SPIN_SHOT_HANDLE=u.register_slate_post_tick_callback(spin_native_shot)
    BASE_FINISH=finish
    def finish(error=None):
        u.unregister_slate_post_tick_callback(SPIN_SHOT_HANDLE)
        (out/'SpinNativeShots.json').write_text(json.dumps(dict(asset_saves=0,rows=SPIN_SHOTS,
            scope='Actual natural montage; late impact/tail included; native game viewport, no pose seek.'),indent=2),encoding='utf-8')
        BASE_FINISH(error)
