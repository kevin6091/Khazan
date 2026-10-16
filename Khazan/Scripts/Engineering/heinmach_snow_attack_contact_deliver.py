"""Guarded delivery of the verified, task-owned weapon contact change."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
STAGE = Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
OUT = ROOT/'Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008'
BASE = OUT.parent
OWN = ('Source/Khazan/Environment/KZSnowDeformation.h',
       'Source/Khazan/Environment/KZSnowDeformation.cpp',
       'Source/Khazan/Tests/KZSnowDeformationPIETest.cpp')
MAP = 'Content/Maps/L_HeinMach_Environment.umap'
MANIFEST = 'Binaries/Win64/UnrealEditor.modules'
ALIAS = 'UnrealEditor-KhazanSnowWeaponContact20261008.dll'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')

def baseline():
    assert not (OUT/'DeliveryBaseline.json').exists(), 'Existing task baseline preserved'
    intake = read(OUT/'SourceIntake.json')
    source = {p['path']: p['sha256'] for p in intake['main_source']}
    assert sha(ROOT/MAP) == intake['main_map_sha256']
    assert {p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'Source').rglob('*') if p.is_file()} == source
    previous = read(BASE/'Contact55_20261007/Delivery.json')
    protect = [p for p in previous['hashes'] if p.startswith('Content/')]
    protect += list(previous['original_materials_preserved'])
    protect += ['Config/DefaultEngine.ini', 'Config/DefaultEditor.ini',
                'Content/_Art/Player/Character/Bluprints/BP_Player.uasset',
                'Binaries/Win64/UnrealEditor-Khazan.dll']
    manifest = read(ROOT/MANIFEST)
    protect += ['Binaries/Win64/'+manifest['Modules']['Khazan']]
    write(OUT/'DeliveryBaseline.json', dict(source=source, map_sha256=sha(ROOT/MAP),
          manifest=manifest, manifest_sha256=sha(ROOT/MANIFEST),
          protected={p:sha(ROOT/p) for p in protect}, utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    print('Task baseline captured; Main unchanged')

def publish():
    assert not (OUT/'Delivery.json').exists(), 'Use receipt for any follow-up; do not repeat delivery'
    b = read(OUT/'DeliveryBaseline.json')
    assert sha(ROOT/MAP) == b['map_sha256'], 'Canonical changed; preserve user changes'
    assert sha(ROOT/MANIFEST) == b['manifest_sha256']
    for p, digest in b['protected'].items():
        assert sha(ROOT/p) == digest, ('Protected file changed', p)
    assert {p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'Source').rglob('*') if p.is_file()} == b['source'], 'Concurrent source changed'
    for p,digest in b['source'].items():
        if p not in OWN: assert sha(STAGE/p) == digest, ('Compiled non-owned source mismatch', p)
    for mode in ('author','audit'):
        r=read(OUT/('SurfaceProfiles_'+mode+'.json'))
        assert r['success'] and r['stage_map_after_sha256'] == sha(STAGE/MAP)
    log=OUT/'StagePIE.log'
    proof=read(OUT/'NativeBuildProof.json')
    assert proof['success'] and log.stat().st_mtime > (OUT/proof['build_log']).stat().st_mtime
    for p,digest in proof['source'].items():assert sha(STAGE/p)==digest, ('QA source changed',p)
    text=log.read_text(encoding='utf-8',errors='replace')
    assert 'Test Completed. Result={Success} Name={PIE} Path={Khazan.Snow.PIE}' in text
    assert 'Test Completed. Result={Fail} Name={PIE} Path={Khazan.Snow.PIE}' not in text
    module=STAGE/'Binaries/Win64/UnrealEditor-Khazan.dll'
    assert sha(module)==proof['module_sha256']
    assert module.stat().st_mtime <= log.stat().st_mtime
    manifest=read(STAGE/MANIFEST)
    assert manifest['BuildId']==b['manifest']['BuildId']
    target=ROOT/'Binaries/Win64'/ALIAS
    assert not target.exists(), 'Do not overwrite loaded or previous module'
    backup=OUT/'Backup'
    for p in (*OWN,MAP,MANIFEST):
        destination=backup/p;destination.parent.mkdir(parents=True,exist_ok=True)
        if destination.exists(): assert sha(destination)==sha(ROOT/p), ('Backup differs',p)
        else: shutil.copy2(ROOT/p,destination)
    # Replace canonical first. A loader lock leaves all source/module targets untouched.
    pending=(ROOT/MAP).with_suffix('.attack_contact_pending')
    shutil.copy2(STAGE/MAP,pending)
    os.replace(pending,ROOT/MAP)
    for p in OWN: shutil.copy2(STAGE/p,ROOT/p)
    shutil.copy2(module,target)
    pdb=module.with_suffix('.pdb')
    if pdb.exists():shutil.copy2(pdb,target.with_suffix('.pdb'))
    manifest['Modules']['Khazan']=ALIAS
    write(ROOT/MANIFEST,manifest)
    files=(*OWN,MAP,MANIFEST,'Binaries/Win64/'+ALIAS)
    hashes={p:sha(ROOT/p) for p in files}
    for p,digest in b['protected'].items():assert sha(ROOT/p)==digest
    profile=read(OUT/'SurfaceProfiles.json')
    receipt=dict(success=True,hashes=hashes,protected=b['protected'],
      module=str(target),module_sha256=sha(target),normal_module_preserved_sha256=sha(ROOT/'Binaries/Win64/UnrealEditor-Khazan.dll'),
      map_asset='/Game/Maps/L_HeinMach_Environment',canonical_map_pending=False,
      surface_profiles_sha256=sha(OUT/'SurfaceProfiles.json'),surface_contact_bytes=sum(p['bytes'] for p in profile['profiles']),
      settings=dict(foot_radius_cm=[8/1.4,5/1.4],foot_contact_height_cm=8.,foot_compression=35/55,
        weapon_compression=50/55,weapon_radius_cm=100.,weapon_contact_height_cm=79.,weapon_surface_contact_tolerance_cm=6.),
      restart_required_for_previously_running_editor=True,native_main_pie_verified=False,
      utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    write(OUT/'Delivery.json',receipt)
    print(json.dumps(receipt,ensure_ascii=False))

if __name__=='__main__':
    {'baseline':baseline,'publish':publish}[sys.argv[1]]()
