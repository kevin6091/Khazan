"""Publish verified snow files only, preserving the live user's loaded module."""
from pathlib import Path
import datetime
import hashlib
import json
import re
import shutil
ROOT=Path(__file__).resolve().parents[2]
STAGE=Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
OUT=ROOT/'Saved/ImportReports/HeinMachSnow_20261006'
BACKUP=OUT/'DeliveryBackup20261007';BACKUP.mkdir(exist_ok=True)
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()
assert json.loads((OUT/'Resume20261007/SceneFinalAudit.json').read_text())['success']
assert json.loads((OUT/'Resume20261007/NavigationFinal.json').read_text())['passed']
log=(OUT/'verify.log').read_text(encoding='utf-8',errors='replace')
completed=re.findall(r'Test Completed\. Result=\{(\w+)\} Name=\{PIE\} Path=\{Khazan.Snow.PIE\}',log)
assert completed and completed[-1]=='Success','Latest real-RHI native snow test must pass'
map_rel=Path('Content/Maps/L_HeinMach_Environment.umap')
assert sha(ROOT/map_rel)=='f236d88889a65c00675ed4e24f1c53a3d17677efd3048ebcaa096443e7685442','Main map changed; rebase required'
intake=json.loads((OUT/'CompletedWorkIntake.json').read_text())
# The independent Monster task is still editing its development-only test.
# Preserve its newest source. Gameplay/animation/other source must match the build.
DEVELOPMENT_TEST='Source/Khazan/Tests/KZMonsterAIPIETest.cpp'
test_snapshot=[dict(path=r['path'],compiled_sha256=r['sha256'],current_sha256=sha(ROOT/r['path']))
               for r in intake['main_source'] if r['path']==DEVELOPMENT_TEST]
for row in intake['main_source']:
    if row['path']!=DEVELOPMENT_TEST:assert sha(ROOT/row['path'])==row['sha256'],row['path']
for p in (ROOT/'Source').rglob('*'):
    if p.is_file() and p.name!='Khazan.Build.cs' and p.relative_to(ROOT).as_posix()!=DEVELOPMENT_TEST:
        assert sha(p)==sha(STAGE/p.relative_to(ROOT)),str(p)
own=[Path('Source/Khazan/Environment/KZSnowDeformation.h'),Path('Source/Khazan/Environment/KZSnowDeformation.cpp'),
     Path('Source/Khazan/Tests/KZSnowDeformationPIETest.cpp')]
bindings=json.loads((OUT/'Authoring.json').read_text())
assert len(bindings['terrain_components'])==46
assets=[Path('Content')/(p.split('/Game/',1)[1].split('.',1)[0]+'.uasset')
        for p in bindings['materials']+[r['new_mesh'] for r in bindings['terrain_components']]]
assert len(set(assets))==48
manifest_rel=Path('Binaries/Win64/UnrealEditor.modules')
original_manifest=json.loads((ROOT/manifest_rel).read_text())
stage_manifest=json.loads((STAGE/manifest_rel).read_text())
assert original_manifest['BuildId']==stage_manifest['BuildId']
old_dll=ROOT/'Binaries/Win64'/original_manifest['Modules']['Khazan'];old_dll_sha=sha(old_dll)
report=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=[],
    unchanged_loaded_module=dict(path=str(old_dll),sha256=old_dll_sha),build_id=original_manifest['BuildId'])
def backup(rel):
    target=ROOT/rel;assert target.resolve().is_relative_to(ROOT.resolve())
    if target.exists():
        dest=BACKUP/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        assert not dest.exists(),'Keep the first delivery backup: '+str(dest)
        shutil.copy2(target,dest)
def copy(rel):
    backup(rel);target=ROOT/rel;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(STAGE/rel,target);assert sha(target)==sha(STAGE/rel)
    report['files'].append(dict(path=rel.as_posix(),sha256=sha(target)))
for rel in own+assets+[map_rel]:copy(rel)
build_rel=Path('Source/Khazan/Khazan.Build.cs');backup(build_rel)
text=(ROOT/build_rel).read_text(encoding='utf-8-sig')
assert '"RHI"' not in text
text=re.sub(r'(PrivateDependencyModuleNames.AddRange\(new string\[\] \{\s*)(\}\);)',r'\1"RHI" \2',text,count=1)
assert '"RHI"' in text;(ROOT/build_rel).write_text(text,encoding='utf-8')
config_rel=Path('Config/DefaultEngine.ini');backup(config_rel)
text=(ROOT/config_rel).read_text(encoding='utf-8-sig')
assert 'r.Nanite.AllowTessellation' not in text and 'r.Nanite.Tessellation' not in text
text+='\n[SystemSettings]\nr.Nanite.AllowTessellation=1\nr.Nanite.Tessellation=1\n'
(ROOT/config_rel).write_text(text,encoding='utf-8')
# UE HotReload watches newly added DLLs beginning "UnrealEditor-Khazan-".
# This manifest-selected filename does not match that watched suffix pattern.
alias='UnrealEditor-KhazanSnow20261007.dll'
binary_target=ROOT/'Binaries/Win64'/alias;assert not binary_target.exists()
shutil.copy2(STAGE/'Binaries/Win64'/stage_manifest['Modules']['Khazan'],binary_target)
assert sha(binary_target)==sha(STAGE/'Binaries/Win64'/stage_manifest['Modules']['Khazan'])
pdb=STAGE/'Binaries/Win64/UnrealEditor-Khazan.pdb'
if pdb.exists():shutil.copy2(pdb,binary_target.with_suffix('.pdb'))
backup(manifest_rel)
updated=dict(original_manifest);updated['Modules']=dict(original_manifest['Modules'],Khazan=alias)
temp=ROOT/'Binaries/Win64/UnrealEditor.modules.snowtmp'
temp.write_text(json.dumps(updated,indent=2),encoding='utf-8');temp.replace(ROOT/manifest_rel)
assert sha(old_dll)==old_dll_sha
report.update(success=True,native_assets=48,source_files=3,map_sha256=sha(ROOT/map_rel),
    published_module=dict(path=str(binary_target),sha256=sha(binary_target)),
    restart_required=True,source_proof=intake['main_source'],
    unrelated_development_test_snapshot=test_snapshot,
    scope='Only own Snow source/assets, HeinMach map, private RHI and Nanite startup settings. Existing user module retained; no live HotReload.')
(OUT/'Delivery20261007.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SNOW_MAIN_DELIVERY_VERIFIED',report['native_assets'],report['map_sha256'],alias)
