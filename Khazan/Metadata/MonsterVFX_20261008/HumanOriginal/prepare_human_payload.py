"""Create import-ready delta manifest; extract only missing native visual payloads."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import os
import struct
import subprocess

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
PROVIDER=ROOT/'Scripts/Enemies/EnemyExtractor/bin/Release/net10.0/EnemyExtractor.exe'
MANIFEST=ROOT/'Content/_Art/Effects/Metadata/Extraction_20261006/AssetManifest.json'


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def write(name,value):
    path=OUT/name;temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(temporary,path)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def relative(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()


def extract(mode,packages,label):
    if not packages:
        return
    write(label+'_Requests.json',sorted(packages))
    directory=OUT/('OriginalRaw' if mode=='raw' else 'Payload')
    directory.mkdir(exist_ok=True)
    with (OUT/(label+'.log')).open('w',encoding='utf-8') as log:
        result=subprocess.run([str(PROVIDER),mode,str(directory),str(OUT/(label+'_Requests.json'))],stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode==0,(label,result.returncode)
    receipt=directory/'ExportReport.json'
    if receipt.exists():
        write(label+'_Receipt.json',read(receipt))


def main():
    original=read(MANIFEST);reserved={r['destination'].lower():r['source_package'] for r in original if r.get('destination')}
    closure=read(OUT/'ResourceClosure.json')
    rows=[]
    for r in closure['resources']:
        assert r['source_file'],r['source_package']
        file=ROOT/r['source_file'];data=read(file);name=r['source_package'].rsplit('/',1)[-1]
        obj=next((o for o in data if o.get('Name')==name and not o.get('Outer')),None)
        if obj is None:
            obj=next((o for o in data if not o.get('Outer')),data[-1])
        typ=obj['Type'];dest=r['native_destination']
        if not dest:
            folder={'Texture2D':'Shared/Textures/MonsterHuman','TextureCube':'Shared/Textures/MonsterHuman','VolumeTexture':'Shared/Textures/MonsterHuman',
                    'StaticMesh':'Shared/Meshes/MonsterHuman','SkeletalMesh':'Shared/Meshes/MonsterHuman',
                    'Material':'Shared/Materials/MonsterHuman','MaterialInstanceConstant':'Shared/Materials/MonsterHuman',
                    'VectorFieldStatic':'Shared/VectorFields/MonsterHuman',
                    'ParticleSystem':'Monsters/Human','NiagaraSystem':'Monsters/Human'}.get(typ,'Shared/Data/MonsterHuman')
            dest='/Game/_Art/Effects/'+folder+'/'+name
            if dest.lower() in reserved and reserved[dest.lower()]!=r['source_package']:
                dest+='_'+hashlib.sha256(r['source_package'].encode()).hexdigest()[:8]
            assert dest.lower() not in reserved or reserved[dest.lower()]==r['source_package']
            reserved[dest.lower()]=r['source_package']
        rows.append({'source_package':r['source_package'],'source_type':typ,'name':name,
                     'source_json':r['source_file'],'source_sha256':sha(file),'destination':dest,
                     'source_root_export_index':data.index(obj),'source_root_export_name':obj['Name'],
                     'is_requested_root':r['requested_directly_by_notify'],'reused_native':r['native_file_exists'],
                     'existing_native_sha256':r['native_sha256'],'existing_native_file':r['native_file'],
                     'source_only_reason':'Cooked Niagara/editor function graph unavailable; native author must explicitly assess support.' if typ in ('NiagaraSystem','MaterialFunction') else None})
    delta=[r for r in rows if not r['reused_native']]
    payload=[r['source_package'] for r in delta if r['source_type'] in ('Texture2D','TextureCube','VolumeTexture','StaticMesh','SkeletalMesh')]
    vectors=[r for r in delta if r['source_type']=='VectorFieldStatic']
    raw=[r['source_package'] for r in delta]
    # Original raw is source preservation/import dependency evidence; it is never copied into product Content.
    extract('raw',raw,'OriginalRawDelta')
    extract('export',payload,'VisualPayloadDelta')
    vector_evidence=[]
    for r in vectors:
        data=read(ROOT/r['source_json']);props=data[r['source_root_export_index']]['Properties']
        sizes=[props[k] for k in ('SizeX','SizeY','SizeZ')];expected=math.prod(sizes)*8
        package=OUT/'OriginalRaw'/r['source_package'];uasset=Path(str(package)+'.uasset');uexp=Path(str(package)+'.uexp')
        b=uexp.read_bytes();assert b[-4:]==struct.pack('<I',0x9e2a83c1)
        offset=len(b)-4-expected;flags,count,disk,absolute=struct.unpack_from('<IIIq',b,offset-20)
        assert count==disk==expected and flags==0x48 and absolute==uasset.stat().st_size+offset
        samples=list(struct.iter_unpack('<eeee',b[offset:offset+expected]));assert len(samples)==math.prod(sizes)
        assert all(math.isfinite(v) for s in samples for v in s) and all(s[3]==0 for s in samples)
        bounds=props['Bounds'];lines=[','.join(map(str,sizes)),','.join(str(bounds['Min'][c]) for c in 'XYZ'),','.join(str(bounds['Max'][c]) for c in 'XYZ')]
        lines.extend(','.join(format(v,'.9g') for v in s[:3]) for s in samples)
        target=OUT/'VectorFields'/(r['name']+'.fga');target.parent.mkdir(exist_ok=True);target.write_text(',\n'.join(lines)+',\n',encoding='ascii')
        vector_evidence.append({'source_package':r['source_package'],'source_metadata':r['source_json'],'source_sha256':r['source_sha256'],
                                'source_raw_uasset_sha256':sha(uasset),'source_raw_uexp_sha256':sha(uexp),'dimensions':sizes,'bounds_cm':bounds,
                                'samples':len(samples),'bulk_flags':flags,'payload_offset_in_uexp':offset,'fga':relative(target),'fga_sha256':sha(target),
                                'conversion':'Exact-order FFloat16Color RGB to FGA XYZ; alpha verifiedzero; no sign/scale/strength changes.'})
    for r in rows:
        prefix=OUT/'Payload'/r['source_package']
        own=[]
        if prefix.parent.exists():
            own=[{'file':relative(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in prefix.parent.glob(prefix.name+'.*') if p.is_file()]
        r['payload_files']=own
        r['raw_source_files']=[{'file':relative(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in (OUT/'OriginalRaw'/r['source_package']).parent.glob(r['name']+'.*') if p.is_file()]
        v=next((v for v in vector_evidence if v['source_package']==r['source_package']),None)
        if v:
            r['vector_field_conversion']=v
        if r['source_package'] in payload:
            assert own,'Missing requested visual payload: '+r['source_package']
    write('ImportReadyAssetManifest.json',rows)
    write('ImportDeltaAssetManifest.json',[r for r in rows if not r['reused_native']])
    write('VectorFieldExtraction.json',vector_evidence)
    result={'schema':1,'status':'READ_ONLY_EXTRACTION_IMPORT_READY_NO_PRODUCT_ASSET_MUTATIONS','asset_rows':len(rows),
            'reused_native_assets':sum(r['reused_native'] for r in rows),'delta_rows':len(delta),
            'delta_types':dict(Counter(r['source_type'] for r in delta)),
            'visual_payload_packages':len(payload),'exact_vector_fields':len(vectors),'raw_delta_packages':len(raw),
            'global_asset_manifest_unchanged_sha256':sha(MANIFEST),'limitations':['Source-only Niagara/MaterialFunction are not author-complete assets.',
            'Routing rawconditions, curve/source defaults, notify correction transforms are preserved; runtime behavior/equivalent rendering not verified.']}
    write('ImportPreparationSummary.json',result);print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':
    main()
