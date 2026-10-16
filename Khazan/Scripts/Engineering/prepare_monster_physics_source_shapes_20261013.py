"""Extract only stored original anatomy shape fields; preserve exact raw values/provenance."""
from pathlib import Path
import hashlib,json
MAIN=Path(__file__).resolve().parents[2]
OUT=MAIN/'Metadata/MonsterSecondaryPhysics_20261013'
WORK=MAIN.parent.parent/'Khazan_PlayerPartsWork_20261007/Khazan'
base='Content/_Art/Enemies/HeinMach/Metadata/'
sources={
 'Adult':base+'Source/BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster_Human/Adult/Adult_M/Model/C_M_Human_Adult_M_PhysicsAsset.json',
 'Elite':base+'Expansion_20260909/Source/BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster_Human/Elite/Elite_M/Model/C_M_Human_Elite_M_PhysicsAsset.json',
 'Halberd':base+'Source/BBQ/Content/_Kazan_/Art/Character/CHA_Model/Monster_Human/Named/Halberd/Model/C_M_Halberd_Skeleton_PhysicsAsset.json'}
data={}
for category,rel in sources.items():
    file=MAIN/rel;exports=json.loads(file.read_text(encoding='utf-8-sig'))
    bodies=[]
    for exp in exports:
        if exp['Type']=='SkeletalBodySetup':
            p=exp['Properties']
            bodies.append(dict(bone=p['BoneName'],geometry=p.get('AggGeom',{}),
                field=f"{exp['Name']}.Properties.AggGeom",source_type=p.get('PhysicsType','unspecified')))
    data[category]=dict(source=rel,package=exports[0]['Package'],sha256=hashlib.sha256(file.read_bytes()).hexdigest(),bodies=bodies)
text=json.dumps(data,indent=2)
(OUT/'OriginalAnatomyShapes.json').write_text(text,encoding='utf-8')
(WORK/'Saved/MonsterSecondaryPhysicsOriginalShapes.json').write_text(text,encoding='utf-8')
print('ORIGINAL ANATOMY SHAPES', {k:len(v['bodies']) for k,v in data.items()})
