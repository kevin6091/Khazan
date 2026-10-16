"""Read-only Main snapshot and guarded private work intake for shoulder tuning."""
import datetime, hashlib, json, shutil
from pathlib import Path
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
work=Path('C:/Users/user/Desktop/GitProject/Khazan_PlayerPartsWork_20261007/Khazan')
report=Path(__file__).resolve().parent
target='Content/_Art/Player/Character/Meshs/Torso/Player_Original_Torso_RigidBody_PhysicsAsset.uasset'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()
assert sha(main/target)=='7560A4A740D8AD99370F7D210CC7A444A828EC0F14C4939141A8CD50A23CFCDE'
assert not (report/'BeforeManifest.json').exists()
before=[dict(path=target,beforeSha256=sha(main/target))]
(report/'BeforeManifest.json').write_text(json.dumps(before,indent=2),encoding='utf-8')
backup=report/'Before'/target; backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(main/target,backup)
protected=set()
for folder in ('Source','Config','Content/_Art/Player/Character'):
    protected.update(p.relative_to(main).as_posix() for p in (main/folder).rglob('*') if p.is_file())
protected.difference_update([target])
protected.update(['Khazan.uproject','Content/Maps/DevMap.umap','Binaries/Win64/UnrealEditor.modules'])
modules=json.loads((main/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
protected.add('Binaries/Win64/'+modules['Modules']['Khazan'])
(report/'ProtectedBefore.json').write_text(json.dumps([dict(path=p,sha256=sha(main/p)) for p in sorted(protected)],indent=2),encoding='utf-8')
changed=[]
paths=[p for folder in ('Source','Config','Content/_Art/Player/Character') for p in (main/folder).rglob('*') if p.is_file()]
for source in paths:
    relative=source.relative_to(main).as_posix()
    if relative=='Source/Khazan/Khazan.Build.cs' or relative.startswith('Source/Khazan/Tests/'): continue
    destination=work/relative
    if not destination.exists() or sha(source)!=sha(destination):
        if destination.exists():
            old=report/'WorkIntakeBefore'/relative; old.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(destination,old)
        destination.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,destination)
        assert sha(destination)==sha(source)
        changed.append(dict(path=relative,mainSha256=sha(source)))
(report/'WorkIntake.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),changed=changed,mainMutations=0,protected=len(protected)),indent=2),encoding='utf-8')
print('Protected Main files:',len(protected),'Private intake changed:',len(changed))
