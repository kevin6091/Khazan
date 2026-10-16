import os,json
from pathlib import Path
assert os.getpid()==2252
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert not editor.get_game_world()
da=unreal.load_asset('/Game/Data/ComboCommand/DA_Player_Combo_Definition')
nodes=da.get_editor_property('nodes')
w=nodes[0].get_editor_property('attack_windows')[0]
start=w.get_editor_property('start_time')
assert abs(start-.30753647142681184)<.00001,('Weak01 current cropped playback mapping',start)
print('TIMING_ANCHOR_OK',start)
console('Automation RunTests Khazan.Combat.PlayerAttackCollision.PIE')
unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
print('HIT_PIE_REQUESTED')
