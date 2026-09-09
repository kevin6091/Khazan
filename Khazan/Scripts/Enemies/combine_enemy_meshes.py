"""Assemble source-allowed outfits into one skinned body per combination.

Vertex positions, normals, UV0, triangles and weights are preserved. Indices are
rebased and bone indices are mapped by original names to the full source tree.
Missing optional vertex colours are neutral white; missing extra UV channels
use that part's UV0. Original per-part morph and LOD exports remain archived.
"""
import pathlib,json,struct,collections,math,itertools
PROJECT=pathlib.Path(__file__).resolve().parents[2]
ROOT=PROJECT/'Saved/Extracted/HeinMachEnemies'
META=PROJECT/'Content/_Art/Enemies/HeinMach/Metadata'
H=struct.Struct('<20siii');B=struct.Struct('<64s3i11f')
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def chunks(p):
    d=p.read_bytes();off=0;out={}
    while off<len(d):
        t,f,s,n=H.unpack_from(d,off);off+=32
        out[t.split(b'\0')[0].decode()]=(s,n,d[off:off+s*n]);off+=s*n
    assert off==len(d)
    return out
def bone_name(b):return b[0].split(b'\0')[0].decode()
def main():
    manifest=read(META/'EnemyImportManifest.json');catalog=[]
    for family,recipe in manifest['recipes'].items():
        roles=[(k.replace('PartsList',''),v) for k,v in recipe['properties'].items() if k.endswith('PartsList')]
        for combination in itertools.product(*(list(enumerate(v)) for _,v in roles)):
            parts={role:entry['Mesh'].get('ObjectPath',entry['Mesh'].get('AssetPathName','')).split('.')[0].replace('/Game/','BBQ/Content/') for (role,_),(idx,entry) in zip(roles,combination)}
            suffix='_'.join(role[0]+str(idx+1).zfill(2) for (role,_),(idx,entry) in zip(roles,combination))
            catalog.append({'asset':manifest['destination_root']+'/Empire/Assemblies/'+family+'/BP_EN_Empire_'+family+'_'+suffix,'family':family,'parts':parts})
    meshes={r['source_package']:r for r in manifest['meshes']}
    carrier=next(r for r in manifest['meshes'] if r['carrier'])
    skeleton=chunks(pathlib.Path(carrier['source_file']))['REFSKELT']
    ref=list(B.iter_unpack(skeleton[2]));names={bone_name(b):i for i,b in enumerate(ref)}
    output=[]
    for rec in catalog:
        if rec['family']=='HalberdElite':continue
        merged=collections.defaultdict(bytearray);counts=collections.Counter();materials=[];slots=[];sources=[];max_bind_position_error=0.0
        parts=[(role,meshes[p],chunks(pathlib.Path(meshes[p]['source_file']))) for role,p in rec['parts'].items()]
        uv_count=max(sum(k.startswith('EXTRAUVS') for k in c) for _,_,c in parts)
        for role,r,c in parts:
            points,wedge_start,mat_start=counts['PNTS0000'],counts['VTXW0000'],len(materials)
            bone_rows=list(B.iter_unpack(c['REFSKELT'][2]));remap={i:names[bone_name(b)] for i,b in enumerate(bone_rows)}
            # Compare positions for every shared bone; do not silently substitute a
            # differently proportioned source skeleton.
            for b in bone_rows:
                other=ref[names[bone_name(b)]]
                delta=max(abs(x-y) for x,y in zip(b[8:11],other[8:11]));max_bind_position_error=max(max_bind_position_error,delta)
                assert delta<0.01,(r['source_package'],bone_name(b),delta)
            for name in ['PNTS0000','VTXNORMS']:
                merged[name].extend(c[name][2]);counts[name]+=c[name][1]
            wedge_rows=list(struct.iter_unpack('<IffBBH',c['VTXW0000'][2]))
            for point,u,v,mat,res,pad in wedge_rows:merged['VTXW0000'].extend(struct.pack('<IffBBH',point+points,u,v,mat+mat_start,res,pad))
            counts['VTXW0000']+=len(wedge_rows)
            face_tag='FACE0000' if 'FACE0000' in c else 'FACE3200'
            fmt='<3HBBI' if face_tag=='FACE0000' else '<3IBBI'
            for a,b,d,mat,aux,smooth in struct.iter_unpack(fmt,c[face_tag][2]):merged['FACE3200'].extend(struct.pack('<3IBBI',a+wedge_start,b+wedge_start,d+wedge_start,mat+mat_start,aux,smooth))
            counts['FACE3200']+=c[face_tag][1]
            for weight,point,bone in struct.iter_unpack('<fii',c['RAWWEIGHTS'][2]):merged['RAWWEIGHTS'].extend(struct.pack('<fii',weight,point+points,remap[bone]))
            counts['RAWWEIGHTS']+=c['RAWWEIGHTS'][1]
            merged['MATT0000'].extend(c['MATT0000'][2]);counts['MATT0000']+=c['MATT0000'][1]
            materials.extend(r['materials']);slots.extend(role+'_'+s for s in r['source_slot_names'])
            merged['VERTEXCOLOR'].extend(c['VERTEXCOLOR'][2] if 'VERTEXCOLOR' in c else b'\xff'*4*len(wedge_rows));counts['VERTEXCOLOR']+=len(wedge_rows)
            for channel in range(uv_count):
                key='EXTRAUVS'+str(channel)
                merged[key].extend(c[key][2] if key in c else b''.join(struct.pack('<ff',w[1],w[2]) for w in wedge_rows));counts[key]+=len(wedge_rows)
            sources.append({'role':role,'package':r['source_package'],'points':c['PNTS0000'][1],'wedges':c['VTXW0000'][1],'triangles':c[face_tag][1],'material_offset':mat_start,'point_offset':points,'wedge_offset':wedge_start})
        sizes={'PNTS0000':12,'VTXNORMS':12,'VTXW0000':16,'FACE3200':18,'RAWWEIGHTS':12,'MATT0000':88,'VERTEXCOLOR':4,**{'EXTRAUVS'+str(i):8 for i in range(uv_count)}}
        name=rec['asset'].rsplit('/',1)[1].replace('BP_EN_','SK_EN_')
        file=ROOT/'Derived/CombinedBodies'/(name+'.psk');file.parent.mkdir(parents=True,exist_ok=True)
        data=bytearray(H.pack(b'ACTRHEAD',0,0,0))
        for key,block in merged.items():
            assert len(block)==sizes[key]*counts[key],key
            data.extend(H.pack(key.encode(),0,sizes[key],counts[key]));data.extend(block)
        data.extend(H.pack(b'REFSKELT',0,*skeleton[:2]));data.extend(skeleton[2]);file.write_bytes(data)
        row={'asset':manifest['destination_root']+'/Empire/CombinedMeshes/'+rec['family']+'/'+name,'assembly':rec['asset'],'family':rec['family'],'source_file':str(file),'parts':sources,'materials':materials,'slot_names':slots,'counts':dict(counts),'bones':len(ref),'max_bind_position_error_cm':max_bind_position_error,'optional_attribute_fill':'Absent colour=white; absent higher UV=UV0; original absence retained in per-part archive'}
        output.append(row)
    (META/'CombinedMeshManifest.json').write_text(json.dumps(output,indent=2,ensure_ascii=False),encoding='utf-8')
    print('COMBINED_BODY_SOURCE',len(output),'max_bind_error_cm',max(x['max_bind_position_error_cm'] for x in output))
if __name__=='__main__':main()
