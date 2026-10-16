"""Hardlink immutable current project files; detach only this task's asset targets."""
from pathlib import Path
import hashlib
import json
import os
import shutil

MAIN = Path(r"C:\Users\user\Desktop\GitProject\Khazan\Khazan").resolve()
WORK = Path(r"C:\Users\user\Desktop\GitProject\Khazan_GiantGrabsWork_20261013\Khazan").resolve()
assert MAIN.exists() and not WORK.exists() and WORK.parent.parent == MAIN.parent.parent
WORK.mkdir(parents=True)

TARGETS = [
    "Content/Monsters/ApesStoneHandElite/Data/DA_OriginalPatterns_ApesStoneHandElite.uasset",
    "Content/Monsters/Yetuga/Data/DA_OriginalPatterns_Yetuga.uasset",
    "Content/Bluprints/Monsters/BP_Monster_ApesStoneHandElite.uasset",
    "Content/Bluprints/Monsters/BP_Monster_Yetuga.uasset",
    "Content/Monsters/ApesStoneHandElite/Abilities/GA_Original_Dodge_A.uasset",
    "Content/Monsters/ApesStoneHandElite/Abilities/GA_Original_Level_DashAtk_New.uasset",
    "Content/Monsters/Yetuga/Abilities/GA_Original_CloseGrab.uasset",
    "Content/Monsters/Yetuga/Abilities/GA_Original_RushGrab.uasset",
]


def digest(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


for folder in ("Content", "Plugins", "Binaries"):
    source = MAIN / folder
    for base, dirs, files in os.walk(source):
        rel = Path(base).relative_to(MAIN)
        target_dir = WORK / rel
        target_dir.mkdir(parents=True, exist_ok=True)
        for name in files:
            src, dst = Path(base) / name, target_dir / name
            os.link(src, dst)

for folder in ("Config", "Source", "Scripts"):
    shutil.copytree(MAIN / folder, WORK / folder)
shutil.copy2(MAIN / "Khazan.uproject", WORK / "Khazan.uproject")
(WORK / "Metadata/GiantGrabs_20261013").mkdir(parents=True)

report = {"main": str(MAIN), "work": str(WORK), "targets": {}}
for rel in TARGETS:
    source, target = MAIN / rel, WORK / rel
    before = digest(source)
    target.unlink()
    shutil.copy2(source, target)
    assert digest(target) == before
    assert not os.path.samefile(source, target)
    report["targets"][rel] = before

out = MAIN / "Metadata/GiantGrabs_20261013/WorkPreparation.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"work": str(WORK), "targets": len(TARGETS)}, indent=2))
