"""Create source-timed idle sequences and reusable visual enemy Blueprints.

Blueprints are art assemblies with source equipment and no gameplay/AI logic.
The catalogue enumerates source-allowed part combinations. It does not claim
to reproduce the original runtime's random roll for an individual spawn.
"""
import unreal, pathlib, json, struct, itertools, fractions, traceback, runpy, math

PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve()
ROOT=PROJECT/'Saved/Extracted/HeinMachEnemies'
META=PROJECT/'Content/_Art/Enemies/HeinMach/Metadata'
MANIFEST=json.loads((META/'EnemyImportManifest.json').read_text(encoding='utf-8'))
DEST=MANIFEST['destination_root'];EAL=unreal.EditorAssetLibrary
TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
SUB=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
SUBLIB=unreal.SubobjectDataBlueprintFunctionLibrary
REPORT=PROJECT/'Saved/ImportReports/HeinMachEnemy_AssemblyBuild.json'
MESHES={r['source_package']:r for r in MANIFEST['meshes']}
SCS_NODES={}

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(a):
    if not EAL.save_loaded_asset(a,only_if_is_dirty=False):raise RuntimeError('Save '+a.get_path_name())
def load(p):
    x=unreal.load_asset(p)
    if not x:raise RuntimeError('Load '+p)
    return x
def tag(a,k,v):EAL.set_metadata_tag(a,k,str(v))
def pkg(v):
    if not v:return None
    return v.get('ObjectPath',v.get('AssetPathName','')).split('.')[0].replace('/Game/','BBQ/Content/')
def source_by_name(n):return read(next((ROOT/'Metadata').rglob(n+'.json')))
def mesh_named(name):return load(next(r['destination'] for r in MANIFEST['meshes'] if r['source_package'].endswith('/'+name)))

def psa_data(path):
    data=path.read_bytes();offset=0;chunks={}
    while offset<len(data):
        tag,flags,size,count=struct.unpack_from('<20siii',data,offset);offset+=32
        chunks[tag.split(b'\0')[0].decode()]=(size,count,data[offset:offset+size*count]);offset+=size*count
    size,count,b=chunks['BONENAMES']
    bones=[b[i*size:i*size+64].split(b'\0')[0].decode() for i in range(count)]
    info=struct.unpack('<64s64s4i3f3i',chunks['ANIMINFO'][2][:168])
    frames=info[-1];keys=list(struct.iter_unpack('<8f',chunks['ANIMKEYS'][2]))
    scale_chunk=chunks.get('SCALEKEYS')
    scales=list(struct.iter_unpack('<4f',scale_chunk[2])) if scale_chunk else None
    return bones,frames,keys,scales,info

def make_animation(source_name,mesh,path,preset=None):
    existing=load(path) if EAL.does_asset_exist(path) else None
    if existing and EAL.get_metadata_tag(existing,'EnemyAnimationImportVersion')=='2_NormalizedQuaternions':return existing,{'asset':path,'reused':True}
    psa=next((ROOT/'Animation').rglob(source_name+'.psa'))
    source=next(x for x in source_by_name(source_name) if x['Type']=='AnimSequence')
    bones,frames,keys,scales,info=psa_data(psa)
    seconds=float(source['Properties']['SequenceLength'])
    rate=fractions.Fraction((frames-1)/seconds).limit_denominator(100000)
    skel=mesh.get_editor_property('skeleton')
    factory=unreal.AnimSequenceFactory();factory.set_editor_property('target_skeleton',skel)
    factory.set_editor_property('preview_skeletal_mesh',mesh)
    folder,name=path.rsplit('/',1);seq=existing or TOOLS.create_asset(name,folder,unreal.AnimSequence,factory)
    if not seq:raise RuntimeError('Animation create '+path)
    controller=seq.controller
    controller.open_bracket('Import source Enemy ActorX idle',False)
    controller.set_frame_rate(unreal.FrameRate(rate.numerator,rate.denominator),False)
    controller.set_number_of_frames(unreal.FrameNumber(frames-1),False)
    pose=unreal.new_object(unreal.SkeletalMeshComponent);pose.set_skeletal_mesh(mesh)
    valid={str(pose.get_bone_name(i)) for i in range(pose.get_num_bones())}
    modifications={v['BoneName']:v.get('BoneScale',{}) for v in (preset or {}).get('BoneTransform',[])}
    applied=[]
    for i,bone in enumerate(bones):
        if bone not in valid:continue
        positions=[];rotations=[];scale_keys=[];mod=modifications.get(bone,{})
        for frame in range(frames):
            index=frame*len(bones)+i;k=keys[index]
            positions.append(unreal.Vector(k[0],-k[1],k[2]))
            # CUE4Parse's resampling can emit non-unit quaternions. Normalize
            # before UE's Sequencer controller converts them to Euler channels.
            # This preserves orientation and avoids a gimbal-pole conversion error.
            q=[k[3],-k[4],k[5],-k[6] if i==0 else k[6]]
            norm=math.sqrt(sum(v*v for v in q))
            if norm==0:raise RuntimeError('Zero source quaternion '+bone)
            rotations.append(unreal.Quat(*(v/norm for v in q)))
            s=scales[index] if scales else (1,1,1)
            scale_keys.append(unreal.Vector(s[0]*mod.get('X',1),s[1]*mod.get('Y',1),s[2]*mod.get('Z',1)))
        if not existing:controller.add_bone_curve(bone,False)
        if not controller.set_bone_track_keys(bone,positions,rotations,scale_keys,False):raise RuntimeError('Track '+bone)
        applied.append(bone)
    controller.close_bracket(False)
    tag(seq,'OriginalPackage',source['Package']);tag(seq,'SourceTiming','(PSA NumRawFrames-1)/original SequenceLength; source samples retained')
    tag(seq,'EnemyAnimationImportVersion','2_NormalizedQuaternions')
    if preset:tag(seq,'BoneModPreview',json.dumps(preset,ensure_ascii=False))
    save(seq)
    return seq,{'asset':path,'source':source['Package'],'frames':frames,'source_seconds':seconds,'fps':[rate.numerator,rate.denominator],'source_psa_rate':info[8],'tracks':len(applied),'preset':preset is not None}

def component(bp,parent,name,mesh):
    node_class=unreal.load_class(None,'/Script/Engine.SCS_Node')
    before={o.get_path_name() for o in unreal.ObjectIterator(node_class)}
    params=unreal.AddNewSubobjectParams(parent_handle=parent,new_class=unreal.SkeletalMeshComponent,blueprint_context=bp,conform_transform_to_parent=True)
    handle,reason=SUB.add_new_subobject(params)
    data=SUBLIB.get_data(handle);obj=SUBLIB.get_object_for_blueprint(data,bp)
    if not obj:raise RuntimeError('Add component '+str(reason))
    SUB.rename_subobject(handle,unreal.Text(name))
    created=[o for o in unreal.ObjectIterator(node_class) if o.get_path_name() not in before]
    if len(created)!=1:raise RuntimeError('Expected one new SCS node: '+str([o.get_path_name() for o in created]))
    SCS_NODES[obj.get_path_name()]=created[0]
    obj.set_skeletal_mesh(mesh)
    obj.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    obj.set_editor_property('mobility',unreal.ComponentMobility.MOVABLE)
    return handle,obj

def set_socket(bp,comp,name):
    # SCS owns Blueprint attachment; modifying only a transient component's
    # AttachSocketName would be overwritten on actor construction.
    node=SCS_NODES[comp.get_path_name()]
    unreal.get_default_object(unreal.SystemLibrary).call_method('SetNamePropertyByName',(node,unreal.Name('AttachToName'),unreal.Name(name)))

def build_blueprint(record,anims):
    path=record['asset']
    if EAL.does_asset_exist(path):
        existing=load(path)
        if EAL.get_metadata_tag(existing,'EnemyAssemblyVersion')=='2_CombinedBody':return existing
        raise RuntimeError('Legacy generated assembly requires separate reset_generated_enemy_assemblies.py process: '+path)
    factory=unreal.BlueprintFactory();factory.set_editor_property('parent_class',unreal.Actor)
    folder,name=path.rsplit('/',1);bp=TOOLS.create_asset(name,folder,unreal.Blueprint,factory)
    handles=SUB.k2_gather_subobject_data_for_blueprint(bp)
    parent=handles[-1] # New Actor BP's DefaultSceneRoot.
    family=record['family'];halberd=family=='HalberdElite'
    body_path=DEST+'/Empire/CombinedMeshes/'+family+'/'+path.rsplit('/',1)[1].replace('BP_EN_','SK_EN_')
    carrier=mesh_named('C_M_HalberdV2') if halberd else load(body_path)
    main_handle,main=component(bp,parent,'EnemyBody',carrier)
    main.set_editor_property('relative_rotation',unreal.Rotator(0,-90,0))
    main.set_editor_property('relative_scale3d',unreal.Vector(record['scale'],record['scale'],record['scale']))
    main.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    play=main.get_editor_property('animation_data');play.set_editor_property('anim_to_play',anims[family]);play.set_editor_property('saved_looping',True);play.set_editor_property('saved_playing',True)
    main.set_editor_property('animation_data',play)
    sword_name='C_I_Halberd_WeaponV2' if halberd else 'C_I_Empire_Q1Sword002'
    h,weapon=component(bp,main_handle,'EnemyWeapon_R',mesh_named(sword_name));set_socket(bp,weapon,'Weapon_R')
    if family=='SwordShield':
        weapon.set_editor_property('relative_location',unreal.Vector(-2.2943702,2.0527954,7.965602e-06))
        weapon.set_editor_property('relative_scale3d',unreal.Vector(1,1,0.8))
        h,shield=component(bp,main_handle,'EnemyShield_L',mesh_named('C_I_SwordShield_Default001V2_L1'));set_socket(bp,shield,'Weapon_L')
    tag(bp,'EnemyArtRole','VisualAssembly_NoGameplayAI');tag(bp,'SourceRecipe',record.get('recipe','CB_EmpireHalberd_E_Early'))
    tag(bp,'EnemyAssemblyVersion','2_CombinedBody')
    tag(bp,'AssemblySelection',json.dumps(record,ensure_ascii=False))
    unreal.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    return bp

def main():
    report={'status':'running','animations':[],'assemblies':[]}
    try:
        anims={}
        carrier=mesh_named('C_M_Human_Adult_M_EmptyMesh')
        for family,name in [('Sword','CA_M_EmpSwd_Stand_F'),('SwordShield','CA_M_EmpireSwordShield_Stand_F'),('HalberdElite','CA_M_Halberd_Stand_F')]:
            seq,info=make_animation(name,mesh_named('C_M_HalberdV2') if family=='HalberdElite' else carrier,DEST+'/'+('HalberdElite' if family=='HalberdElite' else 'Empire')+'/Animation/A_EN_'+family+'_Idle')
            anims[family]=seq;report['animations'].append(info)
        records=[]
        for family,recipe in MANIFEST['recipes'].items():
            p=recipe['properties'];roles=[(k.replace('PartsList',''),v) for k,v in p.items() if k.endswith('PartsList')]
            for combination in itertools.product(*(list(enumerate(v)) for k,v in roles)):
                selections={role:pkg(entry['Mesh']) for (role,_),(idx,entry) in zip(roles,combination)}
                suffix='_'.join(role[0]+str(idx+1).zfill(2) for (role,_),(idx,entry) in zip(roles,combination))
                records.append({'asset':DEST+'/Empire/Assemblies/'+family+'/BP_EN_Empire_'+family+'_'+suffix,'family':family,'recipe':recipe['source'],'parts':selections,'scale':1.2,'selection_policy':'enumerated allowed geometry; original spawn RNG result is not known'})
        records.append({'asset':DEST+'/HalberdElite/Assemblies/BP_EN_Empire_HalberdElite','family':'HalberdElite','parts':{},'scale':1.0,'selection_policy':'HeinMach progression elite, not the two tutorial targets'})
        for r in records:
            bp=build_blueprint(r,anims);report['assemblies'].append(r)
            print('ENEMY_ASSEMBLY',bp.get_name())
        (META/'EnemyAssemblyCatalog.json').write_text(json.dumps(records,indent=2,ensure_ascii=False),encoding='utf-8')
        report['status']='passed'
    except Exception:
        report['status']='failed';report['error']=traceback.format_exc();raise
    finally:REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')

if __name__=='__main__':main()
