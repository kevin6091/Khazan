"""Prepare a narrow hair-only change in the existing isolated editor project."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parents[1] / 'Khazan_PlayerPartsWork_20261007/Khazan'
REPORT = MAIN / 'Metadata/PlayerParts_20261007/HairRefinement'
TARGET = Path('Content/_Art/Player/Character/Meshs/Hair/Player_Original_Hair_RigidBody_PhysicsAsset.uasset')
if (REPORT / 'BeforeManifest.json').exists():
    raise RuntimeError('Existing baseline must be retained; resume without preparation')
REPORT.mkdir(parents=True, exist_ok=True)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def copy(src, dst):
    assert dst.resolve().is_relative_to(WORK.resolve())
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and os.stat(dst).st_nlink > 1:
        dst.unlink()
    shutil.copy2(src, dst)

backup = REPORT / 'Before' / TARGET
backup.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(MAIN / TARGET, backup)
(REPORT / 'BeforeManifest.json').write_text(json.dumps([dict(path=TARGET.as_posix(), beforeSha256=digest(MAIN / TARGET))], indent=2), encoding='utf-8')
# Preserve all current source and character content, including changes from other tasks.
for folder in ('Source', 'Config', 'Content/_Art/Player/Character'):
    for src in (MAIN / folder).rglob('*'):
        if src.is_file():
            copy(src, WORK / src.relative_to(MAIN))
copy(MAIN / 'Khazan.uproject', WORK / 'Khazan.uproject')
rules = WORK / 'Source/Khazan/Khazan.Build.cs'
text = rules.read_text(encoding='utf-8-sig')
anchor = '\t\t// Uncomment if you are using Slate UI'
assert anchor in text
text = text.replace(anchor, '        if (Target.bBuildEditor) { PrivateDependencyModuleNames.AddRange(new[] { "UnrealEd", "AnimGraph", "AnimGraphRuntime", "BlueprintGraph", "KismetCompiler" }); }\n\n' + anchor, 1)
rules.write_text(text, encoding='utf-8')
for name in ('PlayerPartsAuthorEditor.cpp', 'PlayerPartsPIEEditor.cpp'):
    copy(MAIN / 'Scripts/Engineering' / name, WORK / 'Source/Khazan/Tests' / name)
copy(MAIN / 'Scripts/Engineering/player_parts_isolated_editor.py', WORK / 'Saved/player_parts_isolated_editor.py')
for src in (WORK / 'Source').rglob('*'):
    if src.is_file():
        os.utime(src, None)
protected = []
for folder in ('Source', 'Config', 'Content/_Art/Player/Character'):
    for src in (MAIN / folder).rglob('*'):
        if src.is_file() and src.relative_to(MAIN) != TARGET:
            protected.append(dict(path=src.relative_to(MAIN).as_posix(), sha256=digest(src)))
for relative in ('Khazan.uproject', 'Content/Maps/DevMap.umap', 'Binaries/Win64/UnrealEditor.modules', 'Binaries/Win64/UnrealEditor-Khazan.dll'):
    protected.append(dict(path=relative, sha256=digest(MAIN / relative)))
(REPORT / 'ProtectedBefore.json').write_text(json.dumps(protected, indent=2), encoding='utf-8')
(REPORT / 'Preparation.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), main=str(MAIN), work=str(WORK), protected=len(protected), targets=1, new_runtime_files=0), indent=2), encoding='utf-8')
print('Prepared hair-only baseline and refreshed isolated source; protected', len(protected), 'files.')
