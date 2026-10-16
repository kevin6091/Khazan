"""Summarize source snow contracts; preserve raw records and a bounded typed closure."""
from pathlib import Path
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'Saved/Extracted/HeinMachSnow_20261006'
OUT=ROOT/'Saved/ImportReports/HeinMachSnow_20261006'
OUT.mkdir(parents=True,exist_ok=True)
rows=[]; refs=set()
def walk(value):
    if isinstance(value,dict):
        path=value.get('ObjectPath','')
        if isinstance(path,str) and path.startswith('BBQ/'):
            refs.add(path.rsplit('.',1)[0])
        for v in value.values():walk(v)
    elif isinstance(value,list):
        for v in value:walk(v)
for path in sorted((BASE/'Source').rglob('*.json')):
    if 'Report' in path.name:continue
    objects=json.loads(path.read_text(encoding='utf-8-sig'))
    if not isinstance(objects,list):continue
    walk(objects)
    for o in objects:
        p=o.get('Properties',{})
        scalars={r['ParameterInfo']['Name']:r['ParameterValue'] for r in p.get('ScalarParameterValues',[])}
        vectors={r['ParameterInfo']['Name']:r['ParameterValue'] for r in p.get('VectorParameterValues',[])}
        textures={r['ParameterInfo']['Name']:r['ParameterValue']['ObjectPath'] for r in p.get('TextureParameterValues',[]) if isinstance(r.get('ParameterValue'),dict)}
        cached=o.get('CachedExpressionData',p.get('CachedExpressionData',{})).get('Parameters',{})
        for key,values in [('RuntimeEntries','ScalarValues'),('RuntimeEntries[1]','VectorValues')]:
            names=cached.get(key,{}).get('ParameterInfos',[])
            values=cached.get(values,[])
            target=scalars if key=='RuntimeEntries' else vectors
            for n,v in zip(names,values):target.setdefault(n['Name'],v)
        if o['Name'].startswith('WLM_'):
            scalars={k:v for k,v in scalars.items() if re.search('Snow|Height|VT|Cover|Tess',k,re.I)}
            vectors={k:v for k,v in vectors.items() if re.search('Snow|Height|VT|Cover',k,re.I)}
            textures={k:v for k,v in textures.items() if re.search('Snow|Height|VT|Cover',k,re.I)}
        rows.append({'package':o.get('Package'),'name':o['Name'],'type':o['Type'],
          'file':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
          'parent':p.get('Parent'),'scalars':scalars,'vectors':vectors,'textures':textures,
          'snow_fields':{k:v for k,v in p.items() if re.search('Snow|Tessellation|VirtualTexture|Displace|Height',k,re.I)}})
missing=[p for p in sorted(refs) if not (BASE/'Source'/(p+'.json')).exists() and
    (p.startswith('BBQ/Content/BaseMaterials/') or 'Snow' in p or 'WLM_Base' in p or
     '/Constants/' in p or '/MaterialParameter' in p)]
(OUT/'OriginalSnowContracts.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
(BASE/'ClosureRequests.json').write_text(json.dumps(missing,indent=2),encoding='utf-8')
print(json.dumps({'objects':len(rows),'next_source_packages':len(missing)}))
for r in rows:
    if r['name'] in ('WLM_HeinMach','WLM_HeinMach2','FoliageInteractionConstants') or 'Main' in r['name']:
        print(json.dumps(r,ensure_ascii=False))
