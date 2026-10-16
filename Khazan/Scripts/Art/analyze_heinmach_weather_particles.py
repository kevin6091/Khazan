"""Store source emitter contracts and the exact resource closure for reuse."""
from pathlib import Path
import json
import hashlib

ROOT = Path(__file__).resolve().parents[2]
EXTRACT = ROOT / 'Saved/Extracted/HeinMachWeather_20261006'
SOURCE = EXTRACT / 'Source'
OUT = ROOT / 'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006'


def compact(v):
    if isinstance(v, dict):
        return {k: compact(x) for k,x in v.items()}
    if isinstance(v,list):
        return v if len(v) < 18 else {'count':len(v),'first':v[:12], 'last':v[-3:]}
    return v


def main():
    contracts = {}
    requests = set()
    for package in json.loads((EXTRACT / 'ParticleRequests.json').read_text()):
        path = SOURCE / (package + '.json')
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        def resolve(ref):
            return data[int(ref['ObjectPath'].rsplit('.',1)[1])]
        system = next(x for x in data if x['Type'] == 'ParticleSystem')
        emitters = []
        for ref in system['Properties']['Emitters']:
            emitter = resolve(ref)
            lod = resolve(emitter['Properties']['LODLevels'][0])
            modules = [resolve(lod['Properties'][k]) for k in ('RequiredModule','SpawnModule','TypeDataModule') if lod['Properties'].get(k)]
            modules += [resolve(r) for r in lod['Properties'].get('Modules',[])]
            emitters.append({'name':emitter['Properties'].get('EmitterName',emitter['Name']),
                             'emitter':emitter, 'lod':lod, 'modules':modules})
            for m in modules:
                for k in ('Material','VectorField','Mesh'):
                    r = m.get('Properties',{}).get(k)
                    if isinstance(r,dict) and r.get('ObjectPath') and not r['ObjectPath'].startswith(package+'.'):
                        requests.add(r['ObjectPath'].rsplit('.',1)[0])
        contracts[package] = {'source_json':str(path), 'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                              'system':system, 'emitters':emitters}
    (OUT / 'SourceParticleContracts.json').write_text(json.dumps(contracts,indent=2) + '\n',encoding='utf-8')
    (EXTRACT / 'MaterialRequests.json').write_text(json.dumps(sorted(requests),indent=2) + '\n',encoding='utf-8')
    # Only show the primary falling-snow emitter. The full raw contract is saved.
    ice = next(v for k,v in contracts.items() if k.endswith('/FP_World_IceBlizzard'))
    summary = [{'name':e['name'],'enabled':e['lod']['Properties'].get('bEnabled',True),
                'modules':[{ 'Type':m['Type'], 'Name':m['Name'],'Properties':compact(m.get('Properties',{}))} for m in e['modules']]}
               for e in ice['emitters'] if e['name']=='Flakes_Fast_Large']
    print(json.dumps({'primary_snow':summary,'material_requests':sorted(requests)},indent=2))


if __name__ == '__main__':
    main()
