"""Existing six-family native blood/ash viewport QA in this process only."""
from pathlib import Path
import os,runpy,shutil
import unreal as u
ROOT=Path(u.Paths.project_dir()).resolve()
OUT=Path(os.environ['KZ_MONSTER_REPAIR_OUT'])
source=ROOT/'Metadata/MonsterRootCollisionRepair_20261012/AttackCases.tsv'
assert source.is_file()
shutil.copy2(source,OUT/'AttackCases.tsv')
os.environ['KZ_MONSTER_REPAIR_QUICK_VISUAL']='1'
runpy.run_path(str(ROOT/'Scripts/Engineering/monster_presentation_repair_editor_driver_20261011.py'),run_name='__main__')

# Existing review camera faces the side opposite the original QA attacker.
# Move only this process's hidden QA player to the camera side BEFORE the
# native PlayHitBlood call, so the contact-surface flash is not behind the body.
def hit_side_preview(delta):
    world=u.EditorLevelLibrary.get_game_world()
    if not world:return
    player=u.GameplayStatics.get_player_character(world,0)
    pc=u.GameplayStatics.get_player_controller(world,0)
    if not player or not pc:return
    camera=pc.get_view_target()
    if isinstance(camera,u.CameraActor):
        player.set_actor_hidden_in_game(True)
        player.set_actor_location(camera.get_actor_location(),False,True)
preview_handle=u.register_slate_post_tick_callback(hit_side_preview)
