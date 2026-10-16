"""Extract only the two original field particle packages and their needed references."""
from pathlib import Path
import zipfile,json,hashlib

main=Path(__file__).resolve().parents[2];out=main/'Metadata/GiantVFX_20261013/ObjectOriginal'
out.mkdir(exist_ok=True)
archives=[main/'Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911/SourceMetadata.zip',
          main/'Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/SourceMetadata.zip']
index={}
for archive in archives:
    if not archive.exists():continue
    with zipfile.ZipFile(archive) as z:
        for name in z.namelist():
            normalized=name.replace('\\','/')
            if '/BBQ/' in normalized:normalized='BBQ/'+normalized.split('/BBQ/',1)[1]
            if normalized.startswith('BBQ/') and normalized.endswith('.json'):index.setdefault(normalized[:-5],(archive,name))
targets=['BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Monster/Boss_Yetuga/FP_Boss_Yetuga_IceBreath_explosion_01',
         'BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Monster/Boss_Yetuga/FP_Boss_Yetuga_IceBreath_Smash_04']
rows=[]
for key in targets:
    assert key in index,key
    archive,name=index[key]
    with zipfile.ZipFile(archive) as z:data=z.read(name)
    dest=out/(key.rsplit('/',1)[-1]+'.json');dest.write_bytes(data)
    objects=json.loads(data.decode('utf-8-sig'))
    root=next(o for o in objects if o['Type']=='ParticleSystem' and not o.get('Outer'))
    row={'source_package':key,'source_type':'ParticleSystem','name':root['Name'],'source_json':str(dest),
         'source_sha256':hashlib.sha256(data).hexdigest(),'source_cache_zip':str(archive),'source_cache_zip_entry':name,
         'destination':'/Game/_Art/Effects/Monsters/ApesYetuga/GiantPolish/OriginalObjects/'+root['Name']}
    rows.append(row)
    refs=set()
    def collect(value):
        if isinstance(value,dict):
            p=value.get('ObjectPath','')
            if p.startswith('BBQ/') and p.rsplit('.',1)[0]!=key:refs.add(p.rsplit('.',1)[0])
            for v in value.values():collect(v)
        elif isinstance(value,list):
            for v in value:collect(v)
    collect(objects);row['references']=sorted(refs)
(out/'OriginalParticleRows.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('Two exact source particle packages:',[(r['name'],len(r['references'])) for r in rows])
