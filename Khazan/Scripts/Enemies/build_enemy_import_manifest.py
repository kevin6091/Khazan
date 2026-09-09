"""Prepare package-keyed imports and extend the hidden pose carrier's skeleton.

Original ActorX files remain untouched. The pose carrier gets the full original
Skeleton bone tree so cloth bones on follower meshes always have a valid parent
pose. Existing bind transforms and vertex weights are preserved by bone name.
"""
import pathlib, json, struct, hashlib, re, shutil

PROJECT=pathlib.Path(__file__).resolve().parents[2]
ROOT=PROJECT/'Saved/Extracted/HeinMachEnemies'
DEST='/Game/_Art/Enemies/HeinMach'
HEADER=struct.Struct('<20siii')
BONE=struct.Struct('<64s3i11f')

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
def package(ref):
    if not ref:return None
    return ref.get('ObjectPath',ref.get('AssetPathName','')).split('.')[0].replace('/Game/','BBQ/Content/')

def full_carrier(source,skeleton,target=None):
    data=source.read_bytes();offset=0;chunks=[]
    while offset<len(data):
        tag,flag,size,count=HEADER.unpack_from(data,offset);offset+=32
        payload=data[offset:offset+size*count];offset+=size*count
        chunks.append([tag,flag,size,count,payload])
    skel=skeleton['ReferenceSkeleton'];infos=skel['FinalRefBoneInfo'];poses=skel['FinalRefBonePose']
    names={v['Name']:i for i,v in enumerate(infos)}
    old=next(c for c in chunks if c[0].startswith(b'REFSKELT'))
    old_bones=[BONE.unpack_from(old[4],i*120) for i in range(old[3])]
    original={v[0].split(b'\0')[0].decode():v for v in old_bones}
    child_counts=[sum(x['ParentIndex']==i for x in infos) for i in range(len(infos))]
    output=[]
    for i,(info,pose) in enumerate(zip(infos,poses)):
        n=info['Name'];parent=info['ParentIndex']
        if n in original:
            b=list(original[n]);b[2]=child_counts[i];b[3]=parent
        else:
            q=pose['Rotation'];p=pose['Translation']
            assert all(abs(pose['Scale3D'][k]-1)<0.00001 for k in 'XYZ'), n
            b=[n.encode(),0,child_counts[i],parent,q['X'],-q['Y'],q['Z'],-q['W'] if parent==-1 else q['W'],p['X'],-p['Y'],p['Z'],0,0,0,0]
        output.append(BONE.pack(*b))
    remap={i:names[b[0].split(b'\0')[0].decode()] for i,b in enumerate(old_bones)}
    for c in chunks:
        if c[0].startswith(b'REFSKELT'):c[3]=len(output);c[4]=b''.join(output)
        if c[0].startswith(b'RAWWEIGHTS'):
            weights=[struct.unpack_from('<fii',c[4],i*12) for i in range(c[3])]
            c[4]=b''.join(struct.pack('<fii',w,v,remap[b]) for w,v,b in weights)
    target=target or ROOT/'Derived/HeinMach_Empire_FullSkeletonCarrier.psk';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(b''.join(HEADER.pack(*c[:4])+c[4] for c in chunks))
    return target,{'source':str(source),'source_skeleton':skeleton['Package'],'original_bones':len(old_bones),'expanded_bones':len(infos),'geometry_and_existing_bind_transforms':'unchanged','weights':'indices remapped by exact source bone name'}

def main():
    closure=read(ROOT/'SourceClosure.json');objects={}
    for p in closure['packages']:
        f=ROOT/'Metadata'/(p+'.json')
        if f.exists():objects[p]=read(f)
    meshes=[];textures=[];materials=[];used={}
    def unique(name,p):
        if name in used and used[name]!=p:name+='_'+hashlib.sha256(p.encode()).hexdigest()[:8]
        used[name]=p;return name
    for p,objs in sorted(objects.items()):
        for obj in objs:
            typ=obj['Type'];n=obj['Name']
            if typ=='SkeletalMesh':
                source=ROOT/'Assets'/(p+'.psk')
                if not source.exists():continue
                folder='Empire/Parts/'+p.split('/')[-2] if '/Adult_M/Model/' in p else 'Empire/Equipment'
                if '/Named/Halberd/' in p:folder='HalberdElite/Equipment' if n.startswith('C_I_') else 'HalberdElite/Meshes'
                carrier='EmptyMesh' in n
                if carrier:folder='Empire/Parts/PoseCarrier'
                normal_source=source;normalization=None
                if carrier:
                    skel=next(o for o in objects[package(obj['Properties']['Skeleton'])] if o['Type']=='Skeleton')
                    source,normalization=full_carrier(source,skel)
                dest=DEST+'/'+folder+'/'+unique('SK_EN_'+n,p)
                meshes.append({'source_package':p,'source_file':str(source),'original_file':str(normal_source),'destination':dest,'carrier':carrier,'normalization':normalization,'source_skeleton':package(obj['Properties'].get('Skeleton')),'materials':[package(m['Material']) for m in obj['SkeletalMaterials']],'source_slot_names':[m['MaterialSlotName'] for m in obj['SkeletalMaterials']],'bounds':obj['ImportedBounds'],'lod_files':[str(f) for f in normal_source.parent.glob(normal_source.stem+'_LOD*.psk')],'morph_targets':[o['Name'] for o in objs if o['Type']=='MorphTarget']})
            elif typ=='Texture2D':
                source=ROOT/'Assets'/(p+'.png')
                if not source.exists():raise RuntimeError('Missing texture '+p)
                props=obj.get('Properties',{})
                textures.append({'source_package':p,'source_file':str(source),'destination':DEST+'/Shared/Textures/'+unique('T_EN_'+n,p),'properties':props,'source_object':obj})
            elif typ in ('Material','MaterialInstanceConstant'):
                materials.append({'source_package':p,'source_type':typ,'destination':DEST+'/Shared/Materials/'+('Parents/' if '/Base/' in p or typ=='Material' else 'Instances/')+unique(('M_EN_' if typ=='Material' else 'MI_EN_')+n,p),'source_object':obj})
    manifest={'destination_root':DEST,'meshes':meshes,'textures':textures,'materials':materials,'recipes':read(ROOT/'VisualRecipes.json'),'limitations':['Cooked BBQCartoon shader topology is unavailable; named source parameter/parent/texture records are retained with a UE DefaultLit preview adapter.','ActorX source files preserve facial morph data and all source LODs; current project PSK importer does not create UE morph targets or merge source LODs automatically.']}
    out=PROJECT/'Content/_Art/Enemies/HeinMach/Metadata';out.mkdir(parents=True,exist_ok=True)
    write(out/'EnemyImportManifest.json',manifest)
    shutil.copytree(ROOT/'Metadata',out/'Source',dirs_exist_ok=True)
    for n in ['SourceSpawnActors.json','VisualRecipes.json','SourceClosure.json','TargetedPackageIndex.json']:
        shutil.copy2(ROOT/n,out/n)
    write(ROOT/'ImportManifestSummary.json',{'meshes':len(meshes),'textures':len(textures),'materials':len(materials),'manifest':str(out/'EnemyImportManifest.json')})
    print('ENEMY_MANIFEST',len(meshes),len(textures),len(materials))

if __name__=='__main__':main()
