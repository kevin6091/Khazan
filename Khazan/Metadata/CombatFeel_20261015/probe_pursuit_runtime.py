from pathlib import Path
import json
import os
import runpy
import time
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
OUT=Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
rows=[]
last=0.

def prop(obj, name):
    try:
        value=obj.get_editor_property(name)
        if isinstance(value,(str,int,float,bool)):return value
        return value.export_text() if hasattr(value,'export_text') else str(value)
    except Exception:return None

def call(obj,name):
    try:return str(getattr(obj,name)())
    except Exception:return None

def probe(delta):
    global last
    if time.monotonic()-last<.2:return
    last=time.monotonic()
    for world in unreal.EditorLevelLibrary.get_pie_worlds(False):
        for actor in unreal.GameplayStatics.get_all_actors_of_class(world,unreal.KZMonster):
            if 'Yetuga' not in actor.get_name() or actor.get_actor_location().z<19000:continue
            cmc=actor.get_component_by_class(unreal.CharacterMovementComponent)
            controller=actor.get_controller()
            target=controller.get_battle_target() if controller else None
            rows.append({'actor':actor.get_name(),'position':str(actor.get_actor_location()),
                'target_position':str(target.get_actor_location()) if target else None,
                'move_ignored':call(actor,'is_move_input_ignored'),
                'pending_input':call(actor,'get_pending_movement_input_vector'),
                'last_input':call(actor,'get_last_movement_input_vector'),
                'immediate_destination':call(controller,'get_immediate_move_destination') if controller else None,
                'cmc':{key:prop(cmc,key) for key in ('MaxWalkSpeed','MaxAcceleration','Acceleration','Velocity','MovementMode','RequestedVelocity','bHasRequestedVelocity','NavMovementProperties','bRequestedMoveUseAcceleration')},
                'tick_enabled':call(cmc,'is_component_tick_enabled')})
    (OUT/'MovementSamples.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')

CALLBACK=unreal.register_slate_post_tick_callback(probe)
runpy.run_path(str(ROOT/'Scripts/Engineering/combat_feel_validation_driver_20261015.py'),run_name='__main__')
