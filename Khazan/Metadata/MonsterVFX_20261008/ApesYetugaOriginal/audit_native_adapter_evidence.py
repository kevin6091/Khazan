"""Exact raw vector conversion and conservative Niagara constant-store evidence."""
from pathlib import Path
import base64
import hashlib
import json
import math
import struct

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def rel(p):
    return Path(p).resolve().relative_to(ROOT).as_posix()

def write(p,v):
    Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def walk(v,path):
    yield path,v
    if isinstance(v,dict):
        for k,x in v.items():
            yield from walk(x,path+'.'+k)
    elif isinstance(v,list):
        for i,x in enumerate(v):
            yield from walk(x,f'{path}[{i}]')

def scalar_type(v):
    t=v.get('TypeDef',{}).get('ClassStructOrEnum',{}).get('ObjectName','')
    for name,fmt in [('NiagaraFloat','f'),('NiagaraInt32','i'),('NiagaraBool','i'),('Vector2D','ff'),
        ('Vector4','ffff'),('LinearColor','ffff'),('Vector','fff'),('Quat','ffff')]:
        if t=="ScriptStruct'"+name+"'":
            return name,'<'+fmt
    return t,None

def main():
    manifest=read(OUT/'ImportReadyAssetManifest.json');vectors=[];niagara=[]
    for r in manifest:
        if r['source_type']=='VectorFieldStatic' and not r['reused_native'] and not r.get('union_reused_human_manifest'):
            props=read(ROOT/r['source_json'])[r['source_root_export_index']]['Properties']
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
            evidence={'source_package':r['source_package'],'source_metadata':r['source_json'],'source_sha256':r['source_sha256'],
                'source_raw_uasset_sha256':sha(uasset),'source_raw_uexp_sha256':sha(uexp),'dimensions':sizes,'bounds_cm':bounds,
                'samples':len(samples),'bulk_flags':flags,'payload_offset_in_uexp':offset,'fga':rel(target),'fga_sha256':sha(target),
                'conversion':'Exact-order FFloat16Color RGB to FGA XYZ; alpha verified zero; no sign/scale/strength changes.',
                'existing_helper_provenance':'Same validated bulk conversion as HumanOriginal/prepare_human_payload.py.'}
            r['vector_field_conversion']=evidence;vectors.append(evidence)
        if r['source_type']!='NiagaraSystem':
            continue
        data=read(ROOT/r['source_json']);stores=[];variables=[];curves=[];renderers=[];emitters=[]
        for i,o in enumerate(data):
            props=o.get('Properties',{})
            if o['Type']=='NiagaraEmitter':
                emitters.append({'export_index':i,'name':o['Name'],'properties_raw':props})
            if o['Type'].endswith('RendererProperties'):
                renderers.append({'export_index':i,'type':o['Type'],'name':o['Name'],'properties_raw':props})
            if 'Curve' in o['Type'] and o['Type'].startswith('NiagaraDataInterface'):
                curves.append({'export_index':i,'type':o['Type'],'name':o['Name'],'properties_raw':props,
                    'interpretation':'ShaderLUT samples retained in source order; original graph binding/evaluation domain unverified.'})
            for path,v in walk(props,f'Exports[{i}].Properties'):
                if not isinstance(v,dict):
                    continue
                if 'SortedParameterOffsets' in v and 'ParameterData' in v:
                    raw=bytes(v['ParameterData']);decoded=[]
                    for param in v['SortedParameterOffsets']:
                        typ,fmt=scalar_type(param);entry={'raw_parameter':param,'type':typ,'value':None}
                        if fmt and param['Offset']+struct.calcsize(fmt)<=len(raw):
                            vals=struct.unpack_from(fmt,raw,param['Offset']);entry['value']=vals[0] if len(vals)==1 else list(vals)
                            entry['byte_offset']=param['Offset'];entry['raw_bytes_hex']=raw[param['Offset']:param['Offset']+struct.calcsize(fmt)].hex()
                        else:
                            entry['limit']='Interface/object type or unknown struct: not decoded as numeric.'
                        decoded.append(entry)
                    stores.append({'field':path,'parameter_data_bytes':len(raw),'parameters':decoded})
                if 'VarData' in v and 'Name' in v and 'TypeDef' in v:
                    typ,fmt=scalar_type(v);raw=base64.b64decode(v['VarData']);entry={'field':path,'name':v['Name'],'type':typ,'raw_base64':v['VarData'],'value':None}
                    if fmt and len(raw)==struct.calcsize(fmt):
                        vals=struct.unpack(fmt,raw);entry['value']=vals[0] if len(vals)==1 else list(vals)
                    else:
                        entry['limit']='Empty runtime variable or unsupported exact byte/type pairing; no guessed default.'
                    variables.append(entry)
        niagara.append({'source_package':r['source_package'],'source_file':r['source_json'],'source_sha256':r['source_sha256'],
            'destination':r['destination'],'parameter_stores':stores,'dataset_declared_variables':variables,
            'renderers':renderers,'emitters':emitters,'curve_interfaces':curves,
            'limitations':['Cooked parameter defaults/declarations are not proof of actual spawn rate, lifetime or velocity graph execution.',
                'No source/editor graph recovered. Exact renderer/local-space and stored constants can support a disclosed Cascade adapter; unresolved behavior is temporary.']})
    write(OUT/'ImportReadyAssetManifest.json',manifest)
    write(OUT/'ImportDeltaAssetManifest.json',[r for r in manifest if not r['reused_native'] and not r.get('audit_only_actor_context')])
    write(OUT/'VectorFieldExtraction.json',vectors)
    write(OUT/'NiagaraAdapterEvidence.json',{'schema':1,'systems':niagara})
    print(json.dumps({'exact_new_vector_fields':len(vectors),'niagara_systems':len(niagara),
        'numeric_store_values':sum(sum(p['value'] is not None for p in s['parameters']) for n in niagara for s in n['parameter_stores'])}))

if __name__=='__main__':
    main()
