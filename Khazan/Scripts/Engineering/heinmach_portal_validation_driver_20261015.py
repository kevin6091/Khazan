"""Run the saved HeinMach portal through actual capsule overlap, not a direct method call."""
from pathlib import Path
import os, unreal
driver = Path(unreal.Paths.project_dir()).resolve() / 'Scripts/Engineering/monster_physics_validation_driver_20261013.py'
# The same established scene QA texture budget, isolated to this owned process.
for command in ['sg.TextureQuality 2', 'sg.EffectsQuality 2', 'r.Streaming.PoolSize 800']:
    unreal.SystemLibrary.execute_console_command(None, command)
os.environ['KZ_MONSTER_PHYSICS_OUT'] = os.environ['KZ_PORTAL_OUT']
os.environ['KZ_MONSTER_PHYSICS_TESTS'] = 'Khazan.Portal.PIE'
source = driver.read_text(encoding='utf-8').replace("load_level('/Game/Maps/DevMap')", "load_level('/Game/Maps/L_HeinMach_Environment')")
__file__ = str(driver)
exec(compile(source, str(driver), 'exec'), globals())
report['qa_only_texture_quality'] = 2
report['qa_only_streaming_pool_mb'] = 800
