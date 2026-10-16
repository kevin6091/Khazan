"""Run the bundled root-motion skill audit on exact original-mapped giant clips."""
from pathlib import Path
import runpy
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
report = root / "Metadata/GiantGrabs_20261013/RootMotionAudit.json"
assets = [
    "/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Attack/Attack_CloseGrab_Start_Stone",
    "/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Attack/Attack_CloseGrab_Success_01_Turn_Stone",
    "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_CloseGrab_Start",
    "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_CloseGrab_Success_01",
    "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_CloseGrab_Success_02",
    "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_RushGrab",
    "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_RushGrab_Success",
    "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_Armageddon_Jump_Start",
    "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_Armageddon_Jump_End",
    "/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Attack/Attack_Armageddon_Jump_End_Close",
]
runpy.run_path(
    r"C:\Users\user\.codex\skills\unreal-root-motion-repair\scripts\audit_root_motion.py",
    init_globals={
        "ROOT_MOTION_AUDIT_ASSETS": [
            {"asset": path, "expects_root_motion": True, "motion_bones": ["Root"]}
            for path in assets
        ],
        "ROOT_MOTION_AUDIT_REPORT": str(report),
    },
    run_name="__main__",
)
unreal.SystemLibrary.quit_editor()
