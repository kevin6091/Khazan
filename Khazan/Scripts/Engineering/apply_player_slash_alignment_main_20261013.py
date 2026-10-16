"""CAS-deliver only reviewed files, leaving foreign edits/workspaces untouched."""
from pathlib import Path
import hashlib,json,os,shutil,datetime
MAIN=Path(__file__).resolve().parents[2];WORK=MAIN.parent.parent/'Khazan_PlayerSlashWork_20261013/Khazan';OUT=MAIN/'Metadata/PlayerSlashAlignment_20261013'
base=json.loads((OUT/'Baseline.json').read_text())
expected={k.replace('\\','/'):v for k,v in base['sha256'].items()}
sources=['Source/Khazan/Ability/KZActionAbility.cpp','Source/Khazan/Ability/KZActionAbility.h','Source/Khazan/Animation/Notifies/KZAnimNotify_CombatEffect.cpp','Source/Khazan/Tests/KZCombatEffectPIETest.cpp']
assets=[k for k in expected if k.startswith('Content/')]
files=sources+assets
# Apply only after full private actual-GPU and screenshot inspection is passed.
assert json.loads((OUT/'FinalRHI02/Driver.json').read_text())['status']=='passed'
assert json.loads((OUT/'SavedWork04/SavedVerification.json').read_text())['status']=='passed'
for rel in files:
 assert hashlib.sha256((MAIN/rel).read_bytes()).hexdigest()==expected[rel],('Main changed; rebase required',rel)
 assert (WORK/rel).is_file()
run=OUT/'MainApply01';run.mkdir(exist_ok=False)
protected={}
for rel in ['Content/VFX/01_ARPGEssentials/KZ_Slash.uasset','Content/VFX/01_ARPGEssentials/Meshes/SM_VFX_SlashRing_01.uasset','Content/Data/Character/DA_CharacterDefinition_Player.uasset']:
 p=MAIN/rel
 if p.is_file():protected[rel]=hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for rel in files:
 src=WORK/rel;dst=MAIN/rel;backup=run/'Before'/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dst,backup)
 data=src.read_bytes();temp=dst.with_name(dst.name+'.KZSlashApply_20261013.tmp');assert not temp.exists();temp.write_bytes(data)
 assert hashlib.sha256(dst.read_bytes()).hexdigest()==expected[rel]
 # Atomic replacement breaks any old content hardlinks instead of rewriting their inode.
 os.replace(temp,dst)
 rows.append({'file':rel,'before':expected[rel],'after':hashlib.sha256(data).hexdigest()})
(run/'Applied.json').write_text(json.dumps({'status':'applied_pending_Main_build_RHI','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':rows,'protected_asset_sha256':protected,'method':'All-target CAS; byte backups; atomic file replacement; no private DLL copy'},indent=2),encoding='utf-8')
print('MAIN_SCOPED_APPLY',len(rows))