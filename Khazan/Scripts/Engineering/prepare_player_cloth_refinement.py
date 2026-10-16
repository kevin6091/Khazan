"""Refresh the closed private editor; preserve Main and the completed Hair PA."""
from pathlib import Path
import datetime, hashlib, json, os, shutil

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parents[1] / 'Khazan_PlayerPartsWork_20261007/Khazan'
REPORT = MAIN / 'Metadata/PlayerParts_20261007/ClothRefinement'
TARGETS = [Path(f'Content/_Art/Player/Character/Meshs/{p}/Player_Original_{p}_RigidBody_PhysicsAsset.uasset') for p in ('Torso', 'Leg')]
assert not (REPORT / 'BeforeManifest.json').exists(), 'Preserve the existing baseline'
REPORT.mkdir(parents=True, exist_ok=True)

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def copy(src, dst):
    assert dst.resolve().is_relative_to(WORK.resolve())
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and digest(src) == digest(dst): return
    if dst.exists() and os.stat(dst).st_nlink > 1: dst.unlink()
    shutil.copy2(src, dst)
    # UBT caches timestamps. A newly copied change may be older than the private
    # editor's objects, so force only changed source/header files to be rebuilt.
    if dst.is_relative_to(WORK / 'Source'): os.utime(dst, None)

before = []
for rel in TARGETS:
    backup = REPORT / 'Before' / rel
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MAIN / rel, backup)
    before.append(dict(path=rel.as_posix(), beforeSha256=digest(MAIN / rel)))
(REPORT / 'BeforeManifest.json').write_text(json.dumps(before, indent=2), encoding='utf-8')
for folder in ('Source', 'Config', 'Content/_Art/Player/Character'):
    for src in (MAIN / folder).rglob('*'):
        if src.is_file(): copy(src, WORK / src.relative_to(MAIN))
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
protected = []
for folder in ('Source', 'Config', 'Content/_Art/Player/Character'):
    for src in (MAIN / folder).rglob('*'):
        if src.is_file() and src.relative_to(MAIN) not in TARGETS:
            protected.append(dict(path=src.relative_to(MAIN).as_posix(), sha256=digest(src)))
for rel in ('Khazan.uproject', 'Content/Maps/DevMap.umap', 'Binaries/Win64/UnrealEditor.modules', 'Binaries/Win64/UnrealEditor-Khazan.dll'):
    protected.append(dict(path=rel, sha256=digest(MAIN / rel)))
(REPORT / 'ProtectedBefore.json').write_text(json.dumps(protected, indent=2), encoding='utf-8')
(REPORT / 'Preparation.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), main=str(MAIN), work=str(WORK), protected=len(protected), targets=2, new_runtime_files=0), indent=2), encoding='utf-8')
print('Prepared Torso/Leg only; Hair and Main unchanged; protected', len(protected))
