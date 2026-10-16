"""Immutable-file and fresh-runtime receipt for the eight giant-grab assets."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

MAIN = Path(r"C:\Users\user\Desktop\GitProject\Khazan\Khazan").resolve()
WORK = Path(r"C:\Users\user\Desktop\GitProject\Khazan_GiantGrabsWork_20261013\Khazan").resolve()
OUT = MAIN / "Metadata/GiantGrabs_20261013"


def read(root: Path, relative: str):
    return json.loads((root / relative).read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


delivery = read(MAIN, "Metadata/GiantGrabs_20261013/DeliveryResult.json")
work_readback = read(WORK, "Metadata/GiantGrabs_20261013/FreshReadback.json")
main_readback = read(MAIN, "Metadata/GiantGrabs_20261013/FreshReadback.json")
work_pie = read(WORK, "Metadata/GiantGrabs_20261013/ExpandedPIEDriver.json")
main_pie = read(MAIN, "Metadata/GiantGrabs_20261013/MainPIEDriver.json")
pie_result = read(MAIN, "Metadata/GiantCombatFall_20261011/PIEResult.json")
root_motion = read(WORK, "Metadata/GiantGrabs_20261013/RootMotionAudit.json")
pose = read(WORK, "Metadata/GiantGrabs_20261013/PlayerHoldPoseAudit.json")
assert delivery["status"] == "delivered" and len(delivery["assets"]) == 8
assert work_readback["status"] == main_readback["status"] == "passed"
assert len(work_readback["checks"]) == len(main_readback["checks"]) == 38
assert work_pie["status"] == main_pie["status"] == "passed"
assert pie_result["passed"] and pie_result["pattern_cases"] == 13
assert len(root_motion["assets"]) == 10 and all(a["status"] == "audited" for a in root_motion["assets"])
assert pose[0]["moving_after_frame_10"] == 65
assets = []
for item in delivery["assets"]:
    relative = item["path"]
    main_path = (MAIN / relative).resolve()
    work_path = (WORK / relative).resolve()
    assert MAIN in main_path.parents and WORK in work_path.parents
    assert item["delivered"] and sha(main_path) == sha(work_path) == item["after"]
    assets.append({"path": relative, "sha256": item["after"]})
source_paths = [
    "Source/Khazan/Ability/Combo/KZComboActionAbility.cpp",
    "Source/Khazan/Ability/Combo/KZComboActionAbility.h",
    "Source/Khazan/Ability/Combo/KZComboDefinitionData.h",
    "Source/Khazan/Ability/KZAbilitySystemComponent.cpp",
    "Source/Khazan/Ability/KZAbilitySystemComponent.h",
    "Source/Khazan/Ability/MonsterAbility/KZMonsterPatternAbility.cpp",
    "Source/Khazan/Ability/MonsterAbility/KZMonsterPatternAbility.h",
    "Source/Khazan/Ability/PlayerAbility/KZGuardAbility.cpp",
    "Source/Khazan/Ability/PlayerAbility/KZGuardAbility.h",
    "Source/Khazan/AI/KZMonsterAIController.cpp",
    "Source/Khazan/AI/KZMonsterStateTreeNodes.cpp",
    "Source/Khazan/Character/KZMonster.h",
    "Source/Khazan/Tests/KZGiantFallPIETest.cpp",
]
sources = []
for relative in source_paths:
    digest = sha(MAIN / relative)
    assert digest == sha(WORK / relative), relative
    sources.append({"path": relative, "sha256": digest})
module = (MAIN / "Binaries/Win64/UnrealEditor.modules")
module_name = json.loads(module.read_text(encoding="utf-8-sig"))["Modules"]["Khazan"]
assert (MAIN / "Binaries/Win64" / module_name).is_file()
assert Path(main_pie["module"]).resolve() == (MAIN / "Binaries/Win64" / module_name).resolve()
report = {
    "status": "main_build_and_saved_pie_verified",
    "assets": assets,
    "sources": sources,
    "work_saved_checks": len(work_readback["checks"]),
    "main_saved_checks": len(main_readback["checks"]),
    "pattern_cases": pie_result["pattern_cases"],
    "root_motion_sequences_audited": len(root_motion["assets"]),
    "source_player_hold_bones_moving_after_frame_10": pose[0]["moving_after_frame_10"],
    "main_module": str((MAIN / "Binaries/Win64" / module_name).resolve()),
    "main_pie_completion": main_pie["completion"],
}
(OUT / "FinalVerification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps({"status": report["status"], "assets": len(assets),
                  "sources": len(sources), "pattern_cases": report["pattern_cases"]}))
