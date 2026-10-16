"""Prepare reviewable field-level changes and guarded selective Main delivery."""
from pathlib import Path
import hashlib,json,os,shutil,sys
MAIN=Path(__file__).resolve().parents[2]
WORK=MAIN.parent.parent/'Khazan_PlayerPartsWork_20261007/Khazan'
OUT=MAIN/'Metadata/MonsterSecondaryPhysics_20261013'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
OLD='\t\t\tPart->SetLeaderPoseComponent(GetMesh(), true, false);'
NEW='''\t\t\t// CopyPose parts evaluate their own cloth/hair post-process physics.
\t\t\tif (Part->GetAnimClass())
\t\t\t{
\t\t\t\tPart->SetLeaderPoseComponent(nullptr);
\t\t\t\tPart->AddTickPrerequisiteComponent(GetMesh());
\t\t\t\t// Modular skeletons omit anatomy bones; use the complete parent's collision.
\t\t\t\tif (UPhysicsAsset* BodyPhysics = GetMesh()->GetPhysicsAsset())
\t\t\t\t\tPart->AddClothCollisionSource(GetMesh(), BodyPhysics);
\t\t\t}
\t\t\telse Part->SetLeaderPoseComponent(GetMesh(), true, false);'''

def prepare():
    assert not (OUT/'DeliveryManifest.json').exists(), 'Preserve an existing prepared delivery'
    plan=json.loads((OUT/'Preparation.json').read_text(encoding='utf-8'))
    author=json.loads((OUT/'Author01/MonsterSecondaryPhysicsAuthor.json').read_text(encoding='utf-8'))
    targets=['Content/'+p.removeprefix('/Game/')+'.uasset' for p in author['saved']]
    rows=[]
    for rel in sorted(set(targets)):
        before=sha(MAIN/rel) if (MAIN/rel).exists() else None
        assert before==plan['baseline'].get(rel), ('Concurrent target change',rel)
        dest=OUT/'Prepared'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(WORK/rel,dest)
        rows.append(dict(path=rel,before=before,prepared=sha(dest)))
    rel='Source/Khazan/Character/KZMonster.cpp'
    text=(MAIN/rel).read_text(encoding='utf-8-sig');assert text.count(OLD)==1
    dest=OUT/'Prepared'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text.replace(OLD,NEW),encoding='utf-8')
    rows.append(dict(path=rel,before=sha(MAIN/rel),prepared=sha(dest)))
    rel='Source/Khazan/Tests/KZMonsterSecondaryPhysicsPIETest.cpp'
    assert not (MAIN/rel).exists()
    dest=OUT/'Prepared'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(MAIN/'Scripts/Engineering/KZMonsterSecondaryPhysicsPIETest.cpp',dest)
    rows.append(dict(path=rel,before=None,prepared=sha(dest)))
    protected={p.relative_to(MAIN).as_posix():sha(p) for folder in ('Source','Config','Content/_Art/Player/Character') for p in (MAIN/folder).rglob('*') if p.is_file() and p.relative_to(MAIN).as_posix() not in {r['path'] for r in rows}}
    (OUT/'ProtectedBeforeDelivery.json').write_text(json.dumps(protected,indent=2),encoding='utf-8')
    (OUT/'DeliveryManifest.json').write_text(json.dumps(dict(complete=False,files=rows),indent=2),encoding='utf-8')
    print('PREPARED SELECTIVE DELIVERY',len(rows))

def deliver():
    manifest=json.loads((OUT/'DeliveryManifest.json').read_text(encoding='utf-8'))
    assert json.loads((OUT/'PreparedVerification.json').read_text(encoding='utf-8'))['passed']
    for row in manifest['files']:
        source=OUT/'Prepared'/row['path'];target=MAIN/row['path']
        assert sha(source)==row['prepared']
        current=sha(target) if target.exists() else None
        assert current in (row['before'],row['prepared']),('Concurrent Main change',row['path'])
    # Check Windows sharing restrictions on every existing target before mutation.
    for row in manifest['files']:
        target=MAIN/row['path']
        if target.exists():
            with target.open('r+b'):pass
    for row in manifest['files']:
        source=OUT/'Prepared'/row['path'];target=MAIN/row['path']
        if target.exists() and sha(target)==row['prepared']:continue
        if target.exists():
            backup=OUT/'MainBeforeDelivery'/row['path'];backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
        target.parent.mkdir(parents=True,exist_ok=True)
        temp=target.with_name(target.name+'.monsterphysics_pending');shutil.copyfile(source,temp);os.replace(temp,target)
        assert sha(target)==row['prepared']
    manifest['complete']=True
    (OUT/'DeliveryManifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('DELIVERED',len(manifest['files']))

if __name__=='__main__':globals()[sys.argv[1]]()
