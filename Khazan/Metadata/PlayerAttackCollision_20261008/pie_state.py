import unreal
ed=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=ed.get_game_world()
print('WORLD',world)
if world:
    pawn=unreal.GameplayStatics.get_player_pawn(world,0)
    print('PLAYER',pawn)
    if pawn:
        print('CLASS',pawn.get_class().get_path_name(),'LOC',pawn.get_actor_location(),'CONTROLLER',pawn.get_controller())
        move=pawn.get_component_by_class(unreal.CharacterMovementComponent)
        print('MOVE',move,move.get_editor_property('movement_mode'),move.is_moving_on_ground(),move.get_editor_property('velocity'))
    players=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.load_class(None,'/Script/Khazan.KZPlayer'))
    print('PLAYERS',players)
    print('PLAYSETTINGS',unreal.get_default_object(unreal.LevelEditorPlaySettings).export_text() if hasattr(unreal.get_default_object(unreal.LevelEditorPlaySettings),'export_text') else unreal.get_default_object(unreal.LevelEditorPlaySettings).get_editor_property('last_executed_play_mode_type'))
