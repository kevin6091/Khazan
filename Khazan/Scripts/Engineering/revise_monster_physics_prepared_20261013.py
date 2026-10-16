"""Update a not-yet-delivered prepared asset, preserving the rejected candidate."""
from pathlib import Path
import hashlib,json,shutil
MAIN=Path(__file__).resolve().parents[2]
WORK=MAIN.parent.parent/'Khazan_PlayerPartsWork_20261007/Khazan'
OUT=MAIN/'Metadata/MonsterSecondaryPhysics_20261013'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OUT/'DeliveryManifest.json').read_text(encoding='utf-8'))
assert not manifest['complete'] and not (OUT/'PreparedVerification.json').exists()
changed=[r for r in manifest['files'] if sha(WORK/r['path'])!=r['prepared']]
assert len(changed)==1 and changed[0]['path'].endswith('/PA_SK_EN_Yetuga.uasset')
shutil.copy2(OUT/'DeliveryManifest.json',OUT/'DeliveryManifestBeforeClothRevision.json')
for row in changed:
    target=MAIN/row['path'];assert not target.exists()
    before=OUT/'RejectedPrepared'/row['path'];before.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(OUT/'Prepared'/row['path'],before)
    shutil.copy2(WORK/row['path'],OUT/'Prepared'/row['path']);row['prepared']=sha(WORK/row['path'])
(OUT/'DeliveryManifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('PREPARED YETUGA CLOTH REVISION; MAIN UNCHANGED')
