"""Merge only curated source outfits, with a full skeleton for each body type."""
import pathlib,runpy,struct,collections,json
D=runpy.run_path(str(pathlib.Path(__file__).with_name('discover_enemy_expansion.py')))
P=runpy.run_path(str(pathlib.Path(__file__).with_name('combine_enemy_meshes.py')))
ROOT=D['ROOT'];read=D['read'];write=D['write'];chunks=P['chunks'];H=P['H'];B=P['B'];bone_name=P['bone_name']
def main():
    m=read(ROOT/'ImportManifest.json');meshes={r['source_package']:r for r in m['meshes']};outputs=[]
    for rec in m['catalog']:
        if not rec['parts']:continue
        if rec['family']=='HeavySwordsman':continue # source parts have different bind transforms; preserve modular skins
        carrier=meshes[rec['base_mesh']];skeleton=chunks(pathlib.Path(carrier['source_file']))['REFSKELT']
        ref=list(B.iter_unpack(skeleton[2]));names={bone_name(b):i for i,b in enumerate(ref)}
        merged=collections.defaultdict(bytearray);counts=collections.Counter();materials=[];slots=[];sources=[];max_error=0.0
        parts=[(role,meshes[p],chunks(pathlib.Path(meshes[p]['source_file']))) for role,p in rec['parts'].items()]
        # The empty carrier's unused cloth bones can differ from the outfit.
        # Use the visible part's own bind transforms for those bones; shared
        # visible bones must agree before any merge is allowed.
        visible_binds={};carrier_adjustment=0.0
        for role,r,c in parts:
            for b in B.iter_unpack(c['REFSKELT'][2]):
                name=bone_name(b)
                if name in visible_binds:
                    prev=visible_binds[name]
                    assert max(abs(a-v) for a,v in zip(b[8:11],prev[8:11]))<0.01,(rec['family'],name,'visible-part bind mismatch')
                else:visible_binds[name]=b
        for name,b in visible_binds.items():
            i=names[name];old=ref[i];carrier_adjustment=max(carrier_adjustment,max(abs(a-v) for a,v in zip(b[8:11],old[8:11])))
            value=list(b);value[2]=old[2];value[3]=old[3];ref[i]=tuple(value)
        skeleton=(120,len(ref),b''.join(B.pack(*b) for b in ref))
        uv_count=max(sum(k.startswith('EXTRAUVS') for k in c) for _,_,c in parts)
        for role,r,c in parts:
            point_start,wedge_start,mat_start=counts['PNTS0000'],counts['VTXW0000'],len(materials)
            bones=list(B.iter_unpack(c['REFSKELT'][2]));remap={i:names[bone_name(b)] for i,b in enumerate(bones)}
            for b in bones:
                other=ref[names[bone_name(b)]];error=max(abs(a-v) for a,v in zip(b[8:11],other[8:11]));max_error=max(error,max_error)
                assert error<0.01,(r['source_package'],bone_name(b),error) # bind-position validation tolerance in cm
            for name in ['PNTS0000','VTXNORMS']:
                merged[name].extend(c[name][2]);counts[name]+=c[name][1]
            wedges=list(struct.iter_unpack('<IffBBH',c['VTXW0000'][2]))
            for point,u,v,mat,res,pad in wedges:merged['VTXW0000'].extend(struct.pack('<IffBBH',point+point_start,u,v,mat+mat_start,res,pad))
            counts['VTXW0000']+=len(wedges)
            ft='FACE0000' if 'FACE0000' in c else 'FACE3200';fmt='<3HBBI' if ft=='FACE0000' else '<3IBBI'
            for a,b,z,mat,aux,smooth in struct.iter_unpack(fmt,c[ft][2]):merged['FACE3200'].extend(struct.pack('<3IBBI',a+wedge_start,b+wedge_start,z+wedge_start,mat+mat_start,aux,smooth))
            counts['FACE3200']+=c[ft][1]
            for weight,point,bone in struct.iter_unpack('<fii',c['RAWWEIGHTS'][2]):merged['RAWWEIGHTS'].extend(struct.pack('<fii',weight,point+point_start,remap[bone]))
            counts['RAWWEIGHTS']+=c['RAWWEIGHTS'][1]
            merged['MATT0000'].extend(c['MATT0000'][2]);counts['MATT0000']+=c['MATT0000'][1]
            materials.extend(r['materials']);slots.extend(role+'_'+s for s in r['source_slot_names'])
            merged['VERTEXCOLOR'].extend(c['VERTEXCOLOR'][2] if 'VERTEXCOLOR' in c else b'\xff'*4*len(wedges));counts['VERTEXCOLOR']+=len(wedges)
            for channel in range(uv_count):
                k='EXTRAUVS'+str(channel);merged[k].extend(c[k][2] if k in c else b''.join(struct.pack('<ff',w[1],w[2]) for w in wedges));counts[k]+=len(wedges)
            sources.append({'role':role,'package':r['source_package'],'points':c['PNTS0000'][1],'wedges':c['VTXW0000'][1],'triangles':c[ft][1],'material_offset':mat_start})
        sizes={'PNTS0000':12,'VTXNORMS':12,'VTXW0000':16,'FACE3200':18,'RAWWEIGHTS':12,'MATT0000':88,'VERTEXCOLOR':4,**{'EXTRAUVS'+str(i):8 for i in range(uv_count)}}
        file=ROOT/'Derived/CombinedBodies'/(rec['mesh_asset'].rsplit('/',1)[1]+'.psk');file.parent.mkdir(parents=True,exist_ok=True)
        data=bytearray(H.pack(b'ACTRHEAD',0,0,0))
        for key,block in merged.items():
            assert len(block)==sizes[key]*counts[key];data.extend(H.pack(key.encode(),0,sizes[key],counts[key]));data.extend(block)
        data.extend(H.pack(b'REFSKELT',0,*skeleton[:2]));data.extend(skeleton[2]);file.write_bytes(data)
        outputs.append({'asset':rec['mesh_asset'],'assembly':rec['asset'],'family':rec['family'],'source_skeleton':rec['source_skeleton'],'source_file':str(file),'parts':sources,'materials':materials,'slot_names':slots,'counts':dict(counts),'bones':len(ref),'max_bind_position_error_cm':max_error,'carrier_to_visible_bind_adjustment_cm':carrier_adjustment})
    write(ROOT/'CombinedMeshManifest.json',outputs)
    print('CURATED_BODIES',len(outputs),'bones',sorted(set(x['bones'] for x in outputs)),'max_bind_error_cm',max(x['max_bind_position_error_cm'] for x in outputs))
if __name__=='__main__':main()
