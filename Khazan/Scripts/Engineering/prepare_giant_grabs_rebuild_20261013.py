"""Refresh task-owned Work source and detach linker outputs from Main hardlinks."""
from pathlib import Path
import hashlib
import json
import os
import shutil

MAIN = Path(r"C:\Users\user\Desktop\GitProject\Khazan\Khazan").resolve()
WORK = Path(r"C:\Users\user\Desktop\GitProject\Khazan_GiantGrabsWork_20261013\Khazan").resolve()
assert MAIN != WORK and WORK.is_dir() and WORK.parent.parent == MAIN.parent.parent

SOURCE = [
    "Source/Khazan/Ability/Combo/KZComboDefinitionData.h",
    "Source/Khazan/Ability/KZAbilitySystemComponent.h",
    "Source/Khazan/Ability/KZAbilitySystemComponent.cpp",
    "Source/Khazan/Ability/PlayerAbility/KZGuardAbility.h",
    "Source/Khazan/Ability/PlayerAbility/KZGuardAbility.cpp",
    "Source/Khazan/Ability/Combo/KZComboActionAbility.cpp",
    "Source/Khazan/Ability/MonsterAbility/KZMonsterPatternAbility.h",
    "Source/Khazan/Ability/MonsterAbility/KZMonsterPatternAbility.cpp",
    "Source/Khazan/Character/KZMonster.h",
    "Source/Khazan/AI/KZMonsterAIController.cpp",
    "Source/Khazan/AI/KZMonsterStateTreeNodes.cpp",
    "Source/Khazan/Tests/KZGiantFallPIETest.cpp",
    "Scripts/Engineering/finalize_giant_grab_guard_20261013.py",
    "Scripts/Engineering/verify_giant_grabs_20261013.py",
    "Scripts/Engineering/giant_grab_pie_driver_20261013.py",
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


report = {"work": str(WORK), "source": {}, "detached": []}
for rel in SOURCE:
    src, dst = MAIN / rel, WORK / rel
    assert src.is_file() and (dst.is_file() or rel.startswith("Scripts/")), rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    assert sha(src) == sha(dst)
    report["source"][rel] = sha(src)

for root in (WORK / "Binaries", WORK / "Plugins"):
    for base, _, names in os.walk(root):
        for name in names:
            path = Path(base) / name
            if not (name.endswith((".modules", ".target")) or
                    path.parent == WORK / "Binaries/Win64" and name in
                    ("UnrealEditor-Khazan.dll", "UnrealEditor-Khazan.pdb", "UnrealEditor-Khazan.lib")):
                continue
            if path.stat().st_nlink <= 1:
                continue
            tmp = path.with_name(path.name + ".GiantGrabDetach")
            assert not tmp.exists() and path.resolve().is_relative_to(WORK)
            shutil.copy2(path, tmp)
            assert sha(path) == sha(tmp)
            os.replace(tmp, path)
            assert path.stat().st_nlink == 1
            report["detached"].append(str(path.relative_to(WORK)))

out = MAIN / "Metadata/GiantGrabs_20261013/WorkRebuildPreparation.json"
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"source": len(SOURCE), "detached": len(report["detached"])}, indent=2))
