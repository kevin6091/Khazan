"""Selective hash-guarded fire delivery; preserves other maps and existing assets."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2]
STAGE=ROOT/'Saved/ArtStaging/HeinMachTutorialFires_20261006'
OUT=ROOT/'Saved/ImportReports/HeinMachTutorialFires_20261006'
BRANCH=Path('Content/_Art/Player/Environment/HeinMach/Reconstructed/TutorialFires')
META=Path('Content/_Art/Player/Environment/HeinMach/Metadata/TutorialFires_20261006')
MAP=Path('Content/Maps/L_HeinMach_Environment.umap')
BACKUP=ROOT/'Saved/ArtBackups/HeinMachTutorialFires_20261006'

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def write(name,value):
    for base in (OUT,ROOT/META):
        base.mkdir(parents=True,exist_ok=True);(base/(name+'.json')).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def prepare():
    setup=read(OUT/'StageSetup.json')
    assert sha(ROOT/MAP)==setup['baseline_map_sha256'],'Main map changed: rebase instead of overwrite'
    assert not (ROOT/BRANCH).exists(),'New asset destination already exists: do not overwrite'
    for name in ('audit','compile','capture'):
        assert read(OUT/(name+'_Process.json'))['passed'],name
    assert read(OUT/'StageSavedSceneAudit.json')['passed']
    files=[{'path':str(p.relative_to(STAGE)).replace('\\','/'),'sha256':sha(p)} for p in sorted((STAGE/BRANCH).rglob('*.uasset'))]
    assert len(files)==72,len(files)
    files.append({'path':str(MAP).replace('\\','/'),'sha256':sha(STAGE/MAP)})
    BACKUP.mkdir(parents=True,exist_ok=True)
    backup=BACKUP/MAP;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(ROOT/MAP,backup)
    assert sha(backup)==setup['baseline_map_sha256']
    originals=[]
    for r in read(ROOT/'Saved/Extracted/HeinMachTutorialFires_20261006/AssetManifest.json'):
        p=ROOT/r['source_json'];assert sha(p)==r['source_sha256']
        original=dict(r)
        if r['source_type'] in ('MaterialFunction','TextureRenderTarget2D','CurveLinearColorAtlas','CurveLinearColor'):
            original['native_status']='source_only';original['destination']=None
        elif r['reuse_existing']:
            assert r['destination'].startswith('/Game/'),r
            assert (ROOT/'Content'/(r['destination'][len('/Game/'):] + '.uasset')).is_file(),r
            original['native_status']='reused_exact_source'
        elif r['source_package'].startswith('Engine/Content/'):
            original['destination']='/Engine/'+r['source_package'][len('Engine/Content/'):]
            original['native_status']='engine_asset'
        elif (STAGE/'Content'/(r['destination'][len('/Game/'):] + '.uasset')).is_file():original['native_status']='task_native'
        else:original['native_status']='source_only';original['destination']=None
        originals.append(original)
    write('NativeAssetManifest',originals)
    write('SourceOnlyAssets',[r for r in originals if r['native_status']=='source_only'])
    source_native={('Content/'+r['destination'][len('/Game/'):] + '.uasset') for r in originals if r['native_status']=='task_native'}
    adapters=[r['path'] for r in files[:-1] if r['path'] not in source_native]
    assert len(source_native)+len(adapters)==len(files)-1
    manifest={'main_baseline_sha256':setup['baseline_map_sha256'],'map_backup':str(backup.relative_to(ROOT)).replace('\\','/'),
              'files':files,'source_visual_packages':len(originals),'new_native_packages':72,'existing_actors_preserved':9610,'new_map_actors':258,
              'source_status_counts':dict(Counter(r['native_status'] for r in originals)), 'native_adapter_packages':adapters,
              'other_maps_baseline':[r for r in setup['baseline_packages'] if r['path'].replace('\\','/')!=str(MAP).replace('\\','/')]}
    write('InstallManifest',manifest);print('PREPARED',len(files),'packages; backup hash verified')

def install():
    manifest=read(OUT/'InstallManifest.json')
    assert sha(ROOT/MAP)==manifest['main_baseline_sha256'],'Main map changed: rebase'
    assert sha(ROOT/manifest['map_backup'])==manifest['main_baseline_sha256']
    assert not (ROOT/BRANCH).exists(),'Destination already exists; stop to preserve changes'
    for row in manifest['files']:
        rel=Path(row['path']);assert sha(STAGE/rel)==row['sha256'],rel
    # Install the new support packages first, then the verified map.
    for row in manifest['files']:
        rel=Path(row['path']);dest=ROOT/rel
        dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(STAGE/rel,dest)
        assert sha(dest)==row['sha256'],rel
    for path in (STAGE/META).rglob('*.json'):
        rel=path.relative_to(STAGE/META)
        dest=ROOT/META/rel;dest.parent.mkdir(parents=True,exist_ok=True)
        # Existing preparation metadata identifies the same extracted snapshot.
        shutil.copy2(path,dest)
    write('InstallResult',{'passed':True,'packages':len(manifest['files']),'new_native_packages':72,'main_map_sha256':sha(ROOT/MAP),'user_editor_reloaded':False})
    print('INSTALLED',len(manifest['files']),'packages; every SHA verified')

def verify():
    manifest=read(OUT/'InstallManifest.json')
    errors=[r['path'] for r in manifest['files'] if not (ROOT/r['path']).is_file() or sha(ROOT/r['path'])!=r['sha256']]
    assert sha(ROOT/manifest['map_backup'])==manifest['main_baseline_sha256']
    # Other maps may be edited independently by the user; report their hashes,
    # and never copy stage snapshots over those edits.
    others=[{'path':r['path'],'baseline_sha256':r['sha256'],'current_sha256':sha(ROOT/r['path'])} for r in manifest['other_maps_baseline']]
    report={'passed':not errors,'errors':errors,'packages':len(manifest['files']),'backup_verified':True,'other_maps':others,
            'fresh_main_audit':read(OUT/'MainSavedSceneAudit.json'),'actual_main_game_capture':read(OUT/'main_capture_Process.json')}
    assert report['fresh_main_audit']['passed'] and report['actual_main_game_capture']['passed']
    write('DeliveryVerification',report);assert not errors,errors
    print('VERIFIED',report['packages'],'packages and fresh main rendering')

if __name__=='__main__':{'prepare':prepare,'install':install,'verify':verify}[sys.argv[1]]()
