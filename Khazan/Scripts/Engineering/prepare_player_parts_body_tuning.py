"""Refresh the existing isolated author project and back up the three RBAN assets."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parents[1] / 'Khazan_PlayerPartsWork_20261007' / 'Khazan'
REPORT = MAIN / 'Metadata/PlayerParts_20261007/BodyCollisionTuning'
if not WORK.is_dir():
    raise RuntimeError('Existing isolated PlayerParts project required')
if (REPORT / 'BeforeManifest.json').exists():
    raise RuntimeError('Preparation already recorded; resume without replacing the baseline')
REPORT.mkdir(parents=True, exist_ok=True)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def copy_independent(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and os.stat(destination).st_nlink > 1:
        if not destination.resolve().is_relative_to(WORK.resolve()):
            raise RuntimeError('Unexpected hardlink destination')
        destination.unlink()
    shutil.copy2(source, destination)

before = []
for part in ('Torso', 'Leg', 'Hair'):
    relative = Path('Content/_Art/Player/Character/Meshs') / part / ('Player_Original_' + part + '_RigidBody_PhysicsAsset.uasset')
    source = MAIN / relative
    backup = REPORT / 'Before' / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, backup)
    before.append({'path': relative.as_posix(), 'beforeSha256': digest(source)})
    copy_independent(source, WORK / relative)

# Character content is independent in this project. Other Content remains read only.
for source in (MAIN / 'Content/_Art/Player/Character').rglob('*'):
    if source.is_file():
        copy_independent(source, WORK / source.relative_to(MAIN))
source_hashes = []
for folder in ('Source', 'Config'):
    for source in (MAIN / folder).rglob('*'):
        if source.is_file():
            relative = source.relative_to(MAIN)
            copy_independent(source, WORK / relative)
            source_hashes.append({'path': relative.as_posix(), 'sha256': digest(source)})
copy_independent(MAIN / 'Khazan.uproject', WORK / 'Khazan.uproject')
rules = WORK / 'Source/Khazan/Khazan.Build.cs'
text = rules.read_text(encoding='utf-8-sig')
anchor = '\t\t// Uncomment if you are using Slate UI'
if anchor not in text:
    raise RuntimeError('Unexpected module rules; preserve current main dependencies')
text = text.replace(anchor, '        if (Target.bBuildEditor) { PrivateDependencyModuleNames.AddRange(new[] { "UnrealEd", "AnimGraph", "AnimGraphRuntime", "BlueprintGraph", "KismetCompiler" }); }\n\n' + anchor, 1)
rules.write_text(text, encoding='utf-8')
for name in ('PlayerPartsAuthorEditor.cpp', 'PlayerPartsPIEEditor.cpp'):
    copy_independent(MAIN / 'Scripts/Engineering' / name, WORK / 'Source/Khazan/Tests' / name)
# Force UBT to observe the copied source instead of newer stale object files.
for source in (WORK / 'Source').rglob('*'):
    if source.is_file():
        os.utime(source, None)
(REPORT / 'BeforeManifest.json').write_text(json.dumps(before, indent=2), encoding='utf-8')
(REPORT / 'SourceSnapshot.json').write_text(json.dumps({'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'main': str(MAIN), 'work': str(WORK), 'files': source_hashes, 'main_runtime_files_modified': False, 'content_outside_player_character_saved': False}, indent=2), encoding='utf-8')
print('Prepared existing isolated project; backed up three derived PA; retained main runtime files.')
