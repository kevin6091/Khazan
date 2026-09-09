"""Six source humanoid families, curated clothing and source-attached equipment."""
import unreal,pathlib,json,sys,traceback
PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve();ROOT=PROJECT/'Saved/Extracted/HeinMachEnemiesV2'
sys.path.insert(0,str(PROJECT/'Scripts/Enemies'))
import build_enemy_assemblies as B
M=json.loads((ROOT/'ImportManifest.json').read_text(encoding='utf-8'));EAL=unreal.EditorAssetLibrary
ANIMS={r['source_package']:r['destination'] for r in json.loads((ROOT/'AnimationImportManifest.json').read_text(encoding='utf-8'))}
MESHES={r['source_package']:r for r in M['meshes']};MATS={r['source_package']:r['destination'] for r in M['materials']}
def source(p):return json.loads((ROOT/'Metadata'/(p+'.json')).read_text(encoding='utf-8'))
def single(p):return next(o['Properties'] for o in source(p) if o.get('Properties'))
def matching(n):
    found=[p for p in MESHES if p.endswith('/'+n)];assert len(found)==1,(n,found);return found[0]
def play(comp,p):
    assert p in ANIMS,p
    comp.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
    data=comp.get_editor_property('animation_data');data.set_editor_property('anim_to_play',B.load(ANIMS[p]));data.set_editor_property('saved_looping',True);data.set_editor_property('saved_playing',True);data.set_editor_property('saved_play_rate',1.0)
    comp.set_editor_property('animation_data',data)
def part(bp,parent,name,p,socket=None,animation=None,properties=None):
    handle,comp=B.component(bp,parent,name,B.load(MESHES[p]['destination']))
    for i,mat in enumerate(MESHES[p]['materials']):
        if mat:comp.set_material(i,B.load(MATS[mat]))
    if socket:B.set_socket(bp,comp,socket)
    pr=properties or {}
    for field,target in [('RelativeLocation','relative_location'),('RelativeScale3D','relative_scale3d')]:
        if field in pr:
            v=pr[field];comp.set_editor_property(target,unreal.Vector(v['X'],v['Y'],v['Z']))
    if 'RelativeRotation' in pr:
        v=pr['RelativeRotation'];comp.set_editor_property('relative_rotation',unreal.Rotator(pitch=v['Pitch'],yaw=v['Yaw'],roll=v['Roll']))
    for i,mat in enumerate(pr.get('OverrideMaterials',[])):
        key=B.pkg(mat)
        if key:comp.set_material(i,B.load(MATS[key]))
    if animation:play(comp,animation)
    return handle,comp
def build(rec):
    path=rec['asset']
    if EAL.does_asset_exist(path):
        bp=B.load(path);assert EAL.get_metadata_tag(bp,'EnemyExpansionVersion')=='20260909_Curated16'
        # Preserve resolved AP/weapon provenance when resuming a completed build.
        saved=EAL.get_metadata_tag(bp,'AssemblySelection');assert saved,path
        rec.update(json.loads(saved))
        return bp
    cb=source(rec['source_cb']);cd=next(o['Properties'] for o in cb if o['Name'].startswith('Default__'))
    profiles=cd['AnimationProfiles'];battle=next(x['Value'] for x in profiles if x['Key']=='EAnimationState::Battle');ap=B.pkg(battle);idle=B.pkg(single(ap)['Idle'])
    factory=unreal.BlueprintFactory();factory.set_editor_property('parent_class',unreal.Actor)
    folder,name=path.rsplit('/',1);bp=B.TOOLS.create_asset(name,folder,unreal.Blueprint,factory);parent=B.SUB.k2_gather_subobject_data_for_blueprint(bp)[-1]
    body=B.load(MESHES[rec['base_mesh']]['destination'] if rec['family']=='HeavySwordsman' else rec['mesh_asset'])
    h,main=B.component(bp,parent,'EnemyBody',body)
    # UE 5.8 Python positional Rotator fields are roll/pitch/yaw. Name the axes.
    main.set_editor_property('relative_rotation',unreal.Rotator(pitch=0,yaw=-90,roll=0));main.set_editor_property('relative_scale3d',unreal.Vector(rec['scale'],rec['scale'],rec['scale']));play(main,idle)
    if rec['family']=='HeavySwordsman':
        for role,p in rec['parts'].items():part(bp,h,'EnemyArmor_'+role,p,animation=idle)
    equipment=[];fam=rec['family']
    if fam in ['Swordsman','SwordShield']:
        p=matching('C_I_Empire_Q1Sword002');pr={}
        if fam=='SwordShield':
            pr={'RelativeLocation':{'X':-2.2943702,'Y':2.0527954,'Z':7.965602e-06},'RelativeScale3D':{'X':1,'Y':1,'Z':0.8}}
        part(bp,h,'EnemyWeapon_R',p,'Weapon_R',properties=pr);equipment.append({'package':p,'socket':'Weapon_R','properties':pr})
        if fam=='SwordShield':
            p=matching('C_I_SwordShield_Default001V2_L1');part(bp,h,'EnemyShield_L',p,'Weapon_L');equipment.append({'package':p,'socket':'Weapon_L'})
    elif fam in ['Archer','Mage','MageHard']:
        ws=B.pkg(cd['DefaultDefaultWeaponSlots'][0]);slot=next(o['Properties'] for o in source(ws) if o['Type']=='xxWeaponSlotInfoSkeletalMesh');p=B.pkg(slot['SkeletalMesh']);socket=slot['SocketInfo']['SocketName'];wa=B.pkg(slot.get('DefaultAnimation'))
        part(bp,h,'EnemyWeapon_L',p,socket,wa);equipment.append({'package':p,'socket':socket,'source_weapon_slot':ws,'animation':wa})
        if fam=='Archer':
            obj=next(o for o in cb if o['Type']=='xxWeaponMeshComponent' and 'Quiver' in str(o.get('Properties',{}).get('SkeletalMesh')));pr=obj['Properties'];p=B.pkg(pr['SkeletalMesh'])
            node=next(o['Properties'] for o in cb if o['Type']=='SCS_Node' and obj['Name'] in str(o.get('Properties',{}).get('ComponentTemplate')));socket=node['AttachToName']
            part(bp,h,'EnemyQuiver',p,socket,properties=pr);equipment.append({'package':p,'socket':socket,'source_component':obj['Name'],'properties':pr})
    else:
        obj=next(o for o in cb if o['Type']=='xxWeaponMeshComponent' and o.get('Properties',{}).get('SkeletalMesh'));pr=obj['Properties'];p=B.pkg(pr['SkeletalMesh'])
        node=next(o['Properties'] for o in cb if o['Type']=='SCS_Node' and obj['Name'] in str(o.get('Properties',{}).get('ComponentTemplate')));socket=node['AttachToName']
        part(bp,h,'EnemyWeapon_R',p,socket,properties=pr);equipment.append({'package':p,'socket':socket,'source_component':obj['Name'],'properties':pr})
    rec['equipment']=equipment;rec['idle_source']=idle;rec['idle_asset']=ANIMS[idle]
    B.tag(bp,'EnemyArtRole','VisualAssembly_NoGameplayAI');B.tag(bp,'EnemyExpansionVersion','20260909_Curated16');B.tag(bp,'OriginalPackage',rec['source_cb']);B.tag(bp,'SourceLevel',rec['source_level']);B.tag(bp,'AssemblySelection',json.dumps(rec,ensure_ascii=False))
    if fam=='HeavySwordsman':B.tag(bp,'AnimationContract','EnemyBody and all EnemyArmor components play the same animation at the same phase. Keep their source bind poses; update all components together when switching clips.')
    unreal.BlueprintEditorLibrary.compile_blueprint(bp);B.save(bp);return bp
def main():
    report={'status':'running','assemblies':[]}
    try:
        for r in M['catalog']:
            bp=build(r);report['assemblies'].append(r);print('CURATED_ENEMY',bp.get_name())
        report['status']='passed';(ROOT/'AssemblyCatalog.json').write_text(json.dumps(M['catalog'],indent=2,ensure_ascii=False),encoding='utf-8')
    except Exception:
        report['status']='failed';report['error']=traceback.format_exc();raise
    finally:(PROJECT/'Saved/ImportReports/HeinMachEnemyV2_Assemblies.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
if __name__=='__main__':main()
