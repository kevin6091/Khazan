"""Visual isolation only; in-memory ability defaults, no asset save or pass claim."""
from pathlib import Path
import json
import os
import time
import unreal

OUT = Path(os.environ["KZ_PARRY_OUT"])
MODE = os.environ["KZ_PARRY_LAYER"]
OUT.mkdir(parents=True, exist_ok=True)
guard_class = unreal.load_class(None, "/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard.GA_Player_Guard_C")
guard = unreal.get_default_object(guard_class)
effects = list(guard.get_editor_property("ParryBrutalEffects"))
if MODE == "RequestedNiagara":
    guard.set_editor_property("ParryBrutalEffects", [])
elif MODE == "BrutalContacts":
    guard.set_editor_property("ParryBillboardDistortion", None)
    guard.set_editor_property("ParryBrutalEffects", [effect for effect in effects
        if effect.get_editor_property("ParticleTemplate").get_name() in ("PP_AtkEx_Grapple_01", "PP_AtkEx_Grapple_02", "PP_Dmg_Blood_Trail_Sub")])
else:
    guard.set_editor_property("ParryBillboardDistortion", None)
    guard.set_editor_property("ParryBrutalEffects", [effect for effect in effects
        if effect.get_editor_property("ParticleTemplate").get_name() == MODE])
unreal.load_object(None,"/Script/UnrealEd.Default__EditorPerformanceSettings").set_editor_property("bThrottleCPUWhenNotForeground",False)
assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level("/Game/Maps/DevMap")
unreal.SystemLibrary.execute_console_command(None, "t.MaxFPS 60")
unreal.SystemLibrary.execute_console_command(None, "Automation RunTests Khazan.Parry.PIE")
START = time.monotonic()

def tick(delta):
    if (OUT / "03_ActualParryEffectTail.png").exists() or time.monotonic() - START > 100:
        unreal.unregister_slate_post_tick_callback(CALLBACK)
        (OUT / "Diagnostic.json").write_text(json.dumps({"mode": MODE, "asset_saves": 0,
            "status": "captured" if (OUT / "03_ActualParryEffectTail.png").exists() else "timeout",
            "functional_test_completed": False}, indent=2), encoding="utf-8")
        if unreal.EditorLevelLibrary.get_pie_worlds(False):
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        unreal.SystemLibrary.quit_editor()

CALLBACK = unreal.register_slate_post_tick_callback(tick)
