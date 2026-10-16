"""Create a private current-Main snapshot; detach only the two definition assets."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import subprocess

main = Path(__file__).resolve().parents[2]
work = main.parent.parent / "Khazan_GiantReactionWork_20261014" / "Khazan"
out = main / "Metadata" / "GiantReaction_20261014"
assert main.exists() and not work.exists() and work.parent.parent == main.parent.parent
out.mkdir(parents=True, exist_ok=True)
work.mkdir(parents=True)
for folder in ("Source", "Config", "Scripts"):
    shutil.copytree(main / folder, work / folder)
shutil.copy2(main / "Khazan.uproject", work / "Khazan.uproject")
env = dict(os.environ, KZ_JUNCTION_PATH=str(work / "Plugins"), KZ_JUNCTION_TARGET=str(main / "Plugins"))
result = subprocess.run(["powershell.exe", "-NoProfile", "-Command",
                         "New-Item -ItemType Junction -Path $env:KZ_JUNCTION_PATH -Target $env:KZ_JUNCTION_TARGET | Out-Null"],
                        env=env, capture_output=True, text=True)
assert result.returncode == 0, result.stderr
count = 0
for root, dirs, files in os.walk(main / "Content"):
    destination = work / Path(root).relative_to(main)
    destination.mkdir(parents=True, exist_ok=True)
    for name in files:
        os.link(Path(root) / name, destination / name)
        count += 1
targets = [f"Content/Monsters/{family}/Data/DA_Character_{family}.uasset"
           for family in ("ApesStoneHandElite", "Yetuga")]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
baseline = {}
for relative in targets:
    source, destination = main / relative, work / relative
    baseline[relative] = sha(source)
    destination.unlink()
    shutil.copy2(source, destination)
    assert not os.path.samefile(source, destination) and sha(destination) == baseline[relative]
manifest = json.loads((main / "Binaries/Win64/UnrealEditor.modules").read_text(encoding="utf-8-sig"))
module = main / "Binaries/Win64" / manifest["Modules"]["Khazan"]
binary = work / "Binaries/Win64"
binary.mkdir(parents=True)
alias = "UnrealEditor-KhazanGiantReactionBaseline20261014.dll"
shutil.copy2(module, binary / alias)
manifest["Modules"]["Khazan"] = alias
(binary / "UnrealEditor.modules").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
receipt = {"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "main": str(main),
           "work": str(work), "content_hardlinks": count, "detached_targets": baseline,
           "baseline_module": str(module), "baseline_module_sha256": sha(module)}
(out / "WorkPreparation.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
print("PRIVATE_WORK_READY", count, "hardlinks,", len(targets), "detached targets")
