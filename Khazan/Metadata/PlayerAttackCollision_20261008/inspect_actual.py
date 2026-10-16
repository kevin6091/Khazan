import json
print('ACTUAL_STATE',json.dumps({k:v for k,v in s.items() if k not in ('world','player','target','input','action','anim','attrs')},default=str))
print('GAME_WORLD',unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world())
print('GE_CLASS',unreal.load_class(None,'/Game/Bluprints/AbilitySystem/Effects/Attack/GE_ComboAttack_Damage.GE_ComboAttack_Damage_C'))
