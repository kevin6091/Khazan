"""Controlled animation and translation A/B in a real temporal game viewport.

Only transient runtime state changes. No gameplay implementation or assets saved.
Translation/phase numbers below are QA sampling positions, not gameplay tuning.
"""
from pathlib import Path
import json
import math
import runpy
import time
import traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
OUT=ROOT/'Saved/ImportReports/HeinMachReference_20261006/motion'
OUT.mkdir(parents=True,exist_ok=True)
CONF=runpy.run_path(str(ROOT/'Scripts/Art/heinmach_weather_look.py'))
ASSETS='/Game/_Art/Player/Environment/Rendering/HeinMachWeather'
LIB=unreal.MaterialEditingLibrary
START=time.monotonic()
WORLD=PAWN=MESH=CAMERA=SNOW=HANDLE=ORIGIN=SEQUENCE=None
FRAME=INDEX=0
MIDS=[]
VARIANTS=[('LegacyPP_TSR_NoSnow',True,4,False),('FixedPP_TSR_NoSnow',False,4,False),
          ('FixedPP_TSR_Snow',False,4,True),('FixedPP_FXAA_NoSnow',False,1,False)]
if '-HMReferenceTAA' in unreal.SystemLibrary.get_command_line():
    VARIANTS=[('FixedPP_TAA_NoSnow',False,2,False)]
REPORT={'real_game_viewport':True,'highres_screenshot':False,'assets_saved':False,
        'AA_delivered':'TSR','spatial_reference':'FXAA comparison only',
        'motion':'Transient single-node source animation and deterministic actor translation, not input-driven PIE.',
        'variants':[]}


def configure():
    name,legacy,aa,snow=VARIANTS[INDEX]
    unreal.SystemLibrary.execute_console_command(WORLD,'r.AntiAliasingMethod '+str(aa))
    SNOW.set_visibility(snow,True)
    MIDS.clear()
    for volume in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.PostProcessVolume):
        settings=volume.get_editor_property('settings')
        label=volume.get_actor_label()
        profile={209:'Blizzard1',210:'Blizzard2',211:'Boss',212:'Cave1',213:'Cave1',214:'Escape',215:'OP'}[int(label.rsplit('_',1)[-1])] if label.startswith('HM_Environment_PP_') else 'OP'
        fixed=unreal.load_asset(ASSETS+'/MI_HM_RegionalLook_'+profile)
        parent=unreal.load_asset('/Game/__HeinMachQA/MI_Legacy_'+profile) if legacy else fixed
        mid=unreal.MaterialLibrary.create_dynamic_material_instance(WORLD,parent)
        assert mid
        # Identical parameters for the causal A/B: only the pass location differs.
        for parameter in LIB.get_scalar_parameter_names(fixed):
            mid.set_scalar_parameter_value(parameter,LIB.get_material_instance_scalar_parameter_value(fixed,parameter))
        for parameter in LIB.get_vector_parameter_names(fixed):
            mid.set_vector_parameter_value(parameter,LIB.get_material_instance_vector_parameter_value(fixed,parameter))
        for parameter in LIB.get_texture_parameter_names(fixed):
            value=LIB.get_material_instance_texture_parameter_value(fixed,parameter)
            if value:mid.set_texture_parameter_value(parameter,value)
        weighted=settings.get_editor_property('weighted_blendables')
        entries=list(weighted.get_editor_property('array'))
        assert len(entries)==1
        entries[0].set_editor_property('object',mid)
        weighted.set_editor_property('array',entries)
        settings.set_editor_property('weighted_blendables',weighted)
        volume.set_editor_property('settings',settings)
        MIDS.append(mid)
    path=OUT/name
    path.mkdir(parents=True,exist_ok=True)
    REPORT['variants'].append({'name':name,'AA_method':aa,'snow_visible':snow,
                               'same_shading_parameters':True,'frames':[]})


def finish(error=None):
    if error:REPORT['error']=error;unreal.log_error(error)
    (OUT/'MotionVerification.json').write_text(json.dumps(REPORT,indent=2)+'\n',encoding='utf-8')
    unreal.unregister_slate_post_tick_callback(HANDLE)
    if not error:print('KZ_HEINMACH_REFERENCE_MOTION_PASSED')
    unreal.SystemLibrary.execute_console_command(WORLD,'QUIT')


def tick(delta):
    global WORLD,PAWN,MESH,CAMERA,SNOW,ORIGIN,SEQUENCE,FRAME,INDEX
    try:
        if time.monotonic()-START>600:finish('Motion capture timeout');return
        if WORLD is None:
            WORLD=unreal.load_object(None,'/Game/Maps/L_HeinMach_Environment.L_HeinMach_Environment')
            PAWN=unreal.GameplayStatics.get_player_pawn(WORLD,0)
            assert PAWN
            pc=unreal.GameplayStatics.get_player_controller(WORLD,0)
            pc.set_ignore_move_input(True);pc.set_ignore_look_input(True)
            pc.disable_input(pc);PAWN.disable_input(pc)
            PAWN.get_component_by_class(unreal.CharacterMovementComponent).disable_movement()
            ORIGIN=PAWN.get_actor_location()
            MESH=PAWN.get_component_by_class(unreal.SkeletalMeshComponent)
            SEQUENCE=unreal.load_asset('/Game/_Art/Player/Animation/InGame/DAS/Locomotion/Run/CA_P_Kazan_DualAxeSword_Run_F')
            assert SEQUENCE
            MESH.play_animation(SEQUENCE,True);MESH.set_play_rate(0)
            REPORT['animation']=SEQUENCE.get_path_name()
            REPORT['animation_length_seconds']=SEQUENCE.get_play_length()
            REPORT['skeletal_materials']=[]
            for component in PAWN.get_components_by_class(unreal.SkeletalMeshComponent):
                for index in range(component.get_num_materials()):
                    material=component.get_material(index)
                    root=material
                    overrides=[]
                    while isinstance(root,unreal.MaterialInstance):
                        try:overrides.append(str(root.get_editor_property('base_property_overrides')))
                        except Exception:pass
                        root=root.get_editor_property('parent')
                    REPORT['skeletal_materials'].append({'component':component.get_name(),'slot':index,
                        'material':material.get_path_name(),'parent':str(root),'instance_overrides':overrides,
                        'base_blend_mode':str(root.get_editor_property('blend_mode')) if root else None})
            CAMERA=next(c for c in PAWN.get_components_by_class(unreal.CameraComponent) if c.is_active())
            CAMERA.detach_from_component(unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD,unreal.DetachmentRule.KEEP_WORLD)
            CAMERA.set_editor_property('use_pawn_control_rotation',False)
            SNOW=next(a for a in unreal.GameplayStatics.get_all_actors_of_class(WORLD,unreal.NiagaraActor)
                      if a.get_actor_label()=='HM_Environment_SourceSnow').get_component_by_class(unreal.NiagaraComponent)
            for name,value in CONF['QUALITY_PREVIEW'].items():
                unreal.SystemLibrary.execute_console_command(WORLD,name+' '+str(value))
            unreal.SystemLibrary.execute_console_command(WORLD,'t.MaxFPS 30')
            configure()
        if time.monotonic()-START<10:return
        FRAME+=1
        sample=max(0,min(FRAME-100,60))
        offset=120*math.sin(sample*math.pi/60)
        position=unreal.Vector(ORIGIN.x,ORIGIN.y+offset,ORIGIN.z)
        PAWN.set_actor_location(position,False,False)
        # Stop both pose and translation after sample 60 to inspect history decay.
        phase=(sample/30)%SEQUENCE.get_play_length()
        MESH.set_position(phase,False)
        if 101<=FRAME<=160 or FRAME in (162,164,168,176,184):
            target=OUT/VARIANTS[INDEX][0]/('%03d.png'%sample if FRAME<=160 else 'stop_%03d.png'%(FRAME-160))
            unreal.SystemLibrary.execute_console_command(WORLD,'Shot filename="'+str(target)+'" -nosuffix')
            REPORT['variants'][-1]['frames'].append({'frame':FRAME,'phase_seconds':phase,
                                                    'actor_location':[position.x,position.y,position.z],'image':str(target)})
        if FRAME>=190:
            INDEX+=1;FRAME=0
            if INDEX==len(VARIANTS):finish()
            else:configure()
    except Exception:finish(traceback.format_exc())


HANDLE=unreal.register_slate_post_tick_callback(tick)
