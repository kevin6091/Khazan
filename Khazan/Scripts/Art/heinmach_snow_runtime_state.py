from pathlib import Path
import json
import unreal
assert Path(unreal.Paths.project_dir()).resolve()==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
W=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
P=unreal.GameplayStatics.get_player_character(W,0) if W else None
print('OWN_SNOW_RUNTIME',json.dumps(dict(time=unreal.GameplayStatics.get_time_seconds(W) if W else None,
    player=str(P.get_actor_location()) if P else None,movement=str(P.get_component_by_class(unreal.CharacterMovementComponent).movement_mode) if P else None,
    monsters=[dict(actor=a.get_name(),location=str(a.get_actor_location())) for a in unreal.GameplayStatics.get_all_actors_of_class(W,unreal.KZMonster)] if W else [])))
