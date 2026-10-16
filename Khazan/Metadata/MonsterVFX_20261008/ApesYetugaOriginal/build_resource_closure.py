"""Targeted, source-identity visual dependency audit. No product asset mutation."""
from collections import defaultdict, deque, Counter
from pathlib import Path
import hashlib
import json
import os
import re
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
FX = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
CACHE_ROOTS = [OUT/'Source', ROOT/'Metadata/MonsterVFX_20261008/HumanOriginal/Source', FX/'Source', FX/'Bindings/Source',
    ROOT/'Saved/Extracted/CombatEffects_20261006/Source', ROOT/'Saved/Extracted/CombatEffects_20261006/Bindings/Source',
    ROOT/'Content/_Art/Enemies/HeinMach/Metadata/Source', ROOT/'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/Source',
    ROOT/'Saved/ImportReports/PlayerAttackVFX_20261008/ResourceAudit/DecalCurveExtraction',
    ROOT/'Saved/ImportReports/PlayerAttackVFX_20261008/ResourceAudit/DecalDependencyExtraction/Source']
FAMILY_ZIPS = [ROOT/'Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911/SourceMetadata.zip',
    ROOT/'Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/SourceMetadata.zip']

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()

def write(name, data):
    p = OUT/name
    t = p.with_suffix(p.suffix+'.tmp')
    t.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(t,p)

def package(path):
    if not path:
        return ''
    if path.startswith('/Game/'):
        path = 'BBQ/Content/'+path[6:]
    return re.sub(r'\.[^/]+$', '', path)

def refs(v, field='Properties'):
    if isinstance(v,dict):
        if 'ObjectPath' in v:
            yield field,package(v['ObjectPath']),v
        elif 'AssetPathName' in v:
            yield field,package(v['AssetPathName']),v
        else:
            for k,x in v.items():
                yield from refs(x,field+'.'+k)
    elif isinstance(v,list):
        for i,x in enumerate(v):
            yield from refs(x,f'{field}[{i}]')

def main():
    native = {r['source_package']:r for r in read(FX/'AssetManifest.json')}
    human = {r['source_package']:r for r in read(ROOT/'Metadata/MonsterVFX_20261008/HumanOriginal/ImportReadyAssetManifest.json')}
    routes = defaultdict(list)
    for r in read(FX/'EffectRoutingContracts.json'):
        routes[r['source_package']].append(r)
    edges = defaultdict(list)
    for r in read(FX/'DependencyEdges.json'):
        edges[r['source']].append(r)
    zips = [zipfile.ZipFile(p) for p in FAMILY_ZIPS]
    zentries = {name:(z,p) for z,p in zip(zips,FAMILY_ZIPS) for name in z.namelist()}

    def load(p):
        a = native.get(p) or human.get(p)
        if a and a.get('source_json') and (ROOT/a['source_json']).exists():
            f = ROOT/a['source_json']
            return read(f),f,None
        f = next((d/(p+'.json') for d in CACHE_ROOTS if (d/(p+'.json')).exists()),None)
        if f:
            return read(f),f,None
        entry = zentries.get(p+'.json')
        if entry:
            z,zpath = entry
            raw = z.read(p+'.json')
            f = OUT/'Source'/(p+'.json')
            f.parent.mkdir(parents=True,exist_ok=True)
            if not f.exists():
                f.write_bytes(raw)
            assert f.read_bytes()==raw
            return json.loads(raw.decode('utf-8-sig')),f,{'source_zip':rel(zpath),'zip_entry':p+'.json','source_zip_sha256':sha(zpath)}
        return None,None,None

    references = read(OUT/'ResourceReferences.json')['records']
    # Reference manifest is restricted to original visual export properties; actor context
    # includes body/light/data dependencies, so the closure preserves that provenance.
    roots = {package(r['package']) for r in references if r.get('package')}
    queue = deque(sorted(roots));seen=set();resources=[];dependency_edges=[]
    while queue:
        p=queue.popleft()
        if p in seen or not p or p.startswith(('/Script/','/Engine/','Engine/','Script/')):
            continue
        seen.add(p)
        data,file,zproof=load(p)
        a=native.get(p);h=human.get(p)
        dest=(a or h or {}).get('destination')
        nativefile=ROOT/'Content'/(dest[6:]+'.uasset') if dest and dest.startswith('/Game/') else None
        row={'source_package':p,'source_file':rel(file) if file else None,'source_sha256':sha(file) if file else None,
            'source_types':sorted({o.get('Type','') for o in data}) if data else [],'family_zip_cache':zproof,
            'native_manifest_entry':a,'human_union_manifest_entry':h,'native_destination':dest,
            'native_file':rel(nativefile) if nativefile else None,'native_file_exists':bool(nativefile and nativefile.exists()),
            'native_sha256':sha(nativefile) if nativefile and nativefile.exists() else None,
            'routing_candidates_raw':routes.get(p,[]),'requested_directly_by_notify':p in roots}
        derived=[]
        if data:
            for i,o in enumerate(data):
                for field,target,reference in refs(o.get('Properties',{}),f'Exports[{i}].Properties'):
                    if target and target!=p:
                        derived.append({'source':p,'field':field,'target':target,'reference':reference})
        for e in edges.get(p,[]):
            derived.append(dict(e))
        for route in routes.get(p,[]):
            for ref in route.get('references',[]):
                target=package((ref.get('source_reference') or {}).get('ObjectPath',''))
                if target and target!=p:
                    derived.append({'source':p,'field':route['field']+ref.get('field',''),'target':target,'routing_condition_raw':route.get('raw_entry')})
        dedup={json.dumps(e,sort_keys=True):e for e in derived}
        row['dependency_count']=len(dedup)
        resources.append(row);dependency_edges.extend(dedup.values())
        queue.extend(e['target'] for e in dedup.values() if e.get('target'))
    for z in zips:
        z.close()
    missing=sorted(r['source_package'] for r in resources if not r['source_file'])
    write('ResourceClosure.json',{'schema':1,'roots':sorted(roots),'resources':resources,'dependency_edges':dependency_edges,
        'missing_source_packages':missing,'limitations':['Package-normalized original references, not proof every conditional branch executes.',
        'Source metadata and native file availability only. No native author, renderer or lifetime equivalence verification.',
        'Actor visual bindings can include mesh/data/light context; do not treat every resource as an auto-active particle.']})
    write('MissingSourceRequests.json',missing)
    summary={'roots':len(roots),'resources':len(resources),'source_missing':len(missing),
        'native_exists':sum(r['native_file_exists'] for r in resources),'already_human_union':sum(bool(r['human_union_manifest_entry']) for r in resources)}
    write('ResourceClosureSummary.json',summary)
    print(json.dumps(summary))

if __name__=='__main__':
    main()
