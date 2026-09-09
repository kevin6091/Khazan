"""Fresh-process source/asset audit and construction of a separate art catalogue.

Run with UnrealEditor-Cmd -run=pythonscript. The audit touches no existing maps.
Catalogue spacing and lighting are presentation settings, not original gameplay.
"""
import unreal, pathlib, json, runpy, math, traceback

PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve()
META=PROJECT/'Content/_Art/Enemies/HeinMach/Metadata'
MANIFEST=json.loads((META/'EnemyImportManifest.json').read_text(encoding='utf-8'))
CATALOG=json.loads((META/'EnemyAssemblyCatalog.json').read_text(encoding='utf-8'))
DEST=MANIFEST['destination_root'];EAL=unreal.EditorAssetLibrary
SK=unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
LEVEL=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LIB=runpy.run_path(str(PROJECT/'Scripts/Enemies/build_enemy_assemblies.py'))
REPORT=PROJECT/'Saved/ImportReports/HeinMachEnemy_FreshAudit.json'
MAP=DEST+'/Preview/L_HeinMach_EnemyCatalogue'

def check(value,message):
    if not value:raise RuntimeError(message)
def load(path):
    asset=unreal.load_asset(path);check(asset,'Missing '+path);return asset
def path(obj):return obj.get_path_name().split('.')[0] if obj else None
def xyz(v):return [v.x,v.y,v.z]

def inspect_assets(report):
    texs={r['source_package']:r['destination'] for r in MANIFEST['textures']}
    mats={r['source_package']:r['destination'] for r in MANIFEST['materials']}
    for r in MANIFEST['textures']:
        t=load(r['destination']);check(isinstance(t,unreal.Texture2D),'Texture type')
        check(t.get_editor_property('srgb')==r['properties'].get('SRGB',True),'sRGB '+t.get_name())
    report['textures_verified']=len(texs)
    for r in MANIFEST['materials']:
        mat=load(r['destination']);p=r['source_object'].get('Properties',{})
        if r['source_type']=='MaterialInstanceConstant':
            expected=mats[LIB['pkg'](p['Parent'])]
            check(path(mat.get_editor_property('parent'))==expected,'Material parent '+mat.get_name())
            for v in p.get('TextureParameterValues',[]):
                key=LIB['pkg'](v.get('ParameterValue'))
                if key in texs:
                    actual=unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mat,v['ParameterInfo']['Name'])
                    check(path(actual)==texs[key],'Texture binding '+mat.get_name()+' '+v['ParameterInfo']['Name'])
        check(EAL.get_metadata_tag(mat,'OriginalPropertiesJSON'),'Missing source properties '+mat.get_name())
    report['materials_verified']=len(mats)
    for r in MANIFEST['meshes']:
        mesh=load(r['destination']);skel=mesh.get_editor_property('skeleton')
        check(skel,'Missing skeleton '+mesh.get_name())
        slots=mesh.get_editor_property('materials')
        check(len(slots)==len(r['materials']),'Slot count '+mesh.get_name())
        for i,(slot,p) in enumerate(zip(slots,r['materials'])):
            expected=mats[p] if p else DEST+'/Shared/Materials/M_EN_InvisiblePoseCarrier'
            check(path(slot.material_interface)==expected,'Material slot '+mesh.get_name())
            expected_slot='MaterialSlot' if r['carrier'] and r['source_slot_names'][i]=='None' else r['source_slot_names'][i]
            check(str(slot.material_slot_name).lower()==expected_slot.lower(),'Slot name '+mesh.get_name()+': '+str(slot.material_slot_name)+' versus '+expected_slot)
        comp=unreal.new_object(unreal.SkeletalMeshComponent);comp.set_skinned_asset_and_update(mesh)
        names=[str(comp.get_bone_name(i)) for i in range(comp.get_num_bones())]
        verts=SK.get_num_verts(mesh,0);check(verts>0,'Empty geometry '+mesh.get_name())
        if r['carrier']:check(len(names)==185 and 'Weapon_R' in names and 'Weapon_L' in names,'Carrier skeleton')
        if '/Empire/Parts/' in r['destination']:check(path(skel)==DEST+'/Empire/Skeletons/SKEL_EN_EmpireHuman','Shared skeleton')
        report['meshes'].append({'asset':r['destination'],'skeleton':path(skel),'bones':len(names),'vertices_lod0':verts,'material_slots':len(slots),'ue_lods':SK.get_lod_count(mesh)})

def inspect_animation(report):
    for family,source_name in [('Sword','CA_M_EmpSwd_Stand_F'),('SwordShield','CA_M_EmpireSwordShield_Stand_F'),('HalberdElite','CA_M_Halberd_Stand_F')]:
        folder='HalberdElite' if family=='HalberdElite' else 'Empire'
        seq=load(DEST+'/'+folder+'/Animation/A_EN_'+family+'_Idle')
        mesh=LIB['mesh_named']('C_M_HalberdV2' if family=='HalberdElite' else 'C_M_Human_Adult_M_EmptyMesh')
        source=next(x for x in LIB['source_by_name'](source_name) if x['Type']=='AnimSequence')
        psa=next((PROJECT/'Saved/Extracted/HeinMachEnemies/Animation').rglob(source_name+'.psa'))
        bones,frames,keys,scales,info=LIB['psa_data'](psa)
        check(abs(seq.get_play_length()-source['Properties']['SequenceLength'])<0.00001,'Duration '+source_name)
        kinds={}
        for kind in [unreal.AnimDataEvalType.RAW,unreal.AnimDataEvalType.COMPRESSED]:
            opts=unreal.AnimPoseEvaluationOptions(evaluation_type=kind,should_retarget=False,extract_root_motion=False,incorporate_root_motion_into_pose=True,optional_skeletal_mesh=mesh)
            maximum=[0.,0.,0.];worst_rotation=None
            for frame in range(frames):
                pose=unreal.AnimPoseExtensions.get_anim_pose_at_frame(seq,frame,opts)
                check(pose.is_valid(),'Invalid pose '+seq.get_name())
                for i,b in enumerate(bones):
                    k=keys[frame*len(bones)+i];t=pose.get_bone_pose(b,unreal.AnimPoseSpaces.LOCAL)
                    expected_p=[k[0],-k[1],k[2]];expected_q=[k[3],-k[4],k[5],-k[6] if i==0 else k[6]]
                    norm=math.sqrt(sum(v*v for v in expected_q));expected_q=[v/norm for v in expected_q]
                    actual_q=[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w]
                    pe=max(abs(a-e) for a,e in zip(xyz(t.translation),expected_p))
                    qe=min(max(abs(a-e) for a,e in zip(actual_q,expected_q)),max(abs(a+e) for a,e in zip(actual_q,expected_q)))
                    s=scales[frame*len(bones)+i][:3] if scales else [1,1,1]
                    se=max(abs(a-e) for a,e in zip(xyz(t.scale3d),s))
                    if qe>maximum[1]:worst_rotation={'bone':b,'frame':frame,'expected':expected_q,'actual':actual_q}
                    maximum=[max(a,b) for a,b in zip(maximum,[pe,qe,se])]
            # Numerical validation tolerances, not gameplay settings.
            check(maximum[0]<0.05 and maximum[1]<0.002 and maximum[2]<0.001,'Pose mismatch '+source_name+' '+str(kind)+' '+str(maximum)+' '+str(worst_rotation))
            kinds[str(kind)]=maximum
        report['animations'].append({'asset':path(seq),'frames':frames,'bones':len(bones),'duration':seq.get_play_length(),'max_errors_position_cm_quaternion_component_scale':kinds})

def build_catalogue(report):
    if EAL.does_asset_exist(MAP):check(LEVEL.load_level(MAP),'Load catalogue')
    else:check(LEVEL.new_level(MAP),'Create catalogue')
    existing={a.get_actor_label():a for a in ACTORS.get_all_level_actors()}
    for index,r in enumerate(CATALOG):
        label=r['asset'].rsplit('/',1)[1]
        bp=load(r['asset'])
        # 450 cm is catalogue-only spacing: larger than this library's source bounds.
        loc=unreal.Vector((index//8)*450,(index%8)*450,0)
        actor=existing.get(label) or ACTORS.spawn_actor_from_class(EAL.load_blueprint_class(r['asset']),loc)
        check(actor,'Spawn '+label);actor.set_actor_label(label)
        actor.set_folder_path('EnemyCatalogue/'+r['family'])
        comps={c.get_name():c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent)}
        main=comps.get('EnemyBody')
        check(main,'Main component '+label)
        check(len(comps)==(3 if r['family']=='SwordShield' else 2),'Component count '+label)
        check(main.get_editor_property('animation_data').anim_to_play,'Missing idle '+label)
        if r['family']!='HalberdElite':
            mesh=main.get_skinned_asset()
            check(EAL.get_metadata_tag(mesh,'EnemyArtRole')=='CombinedSourceOutfit','Combined body '+label)
            check(main.get_num_bones()==185,'Combined body bones '+label)
        weapon=comps['EnemyWeapon_R']
        check(weapon.get_attach_parent()==main and str(weapon.get_attach_socket_name())=='Weapon_R','Weapon attachment '+label)
        check(main.does_socket_exist('Weapon_R'),'Weapon_R not found '+label)
        if r['family']=='SwordShield':
            shield=comps['EnemyShield_L']
            check(shield.get_attach_parent()==main and str(shield.get_attach_socket_name())=='Weapon_L','Shield attachment '+label)
            check(main.does_socket_exist('Weapon_L'),'Weapon_L not found '+label)
        report['assemblies'].append({'asset':r['asset'],'components':len(comps),'single_body_pose':True,'weapon_socket_verified':True})
    # An empty, independently saved presentation level; no game map is opened.
    if 'EnemyCatalogue_KeyLight' not in existing:
        light=ACTORS.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,500),unreal.Rotator(-45,-35,0))
        light.set_actor_label('EnemyCatalogue_KeyLight')
        light.set_folder_path('PreviewOnly')
        light.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(3.0)
        fill=ACTORS.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,500),unreal.Rotator(-35,145,0))
        fill.set_actor_label('EnemyCatalogue_FillLight');fill.set_folder_path('PreviewOnly')
        fill.get_component_by_class(unreal.DirectionalLightComponent).set_intensity(1.0)
        floor=ACTORS.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(1125,1575,-10))
        floor.set_actor_label('EnemyCatalogue_Floor');floor.set_folder_path('PreviewOnly')
        floor.static_mesh_component.set_static_mesh(load('/Engine/BasicShapes/Cube'))
        floor.set_actor_scale3d(unreal.Vector(32,40,0.2))
        floor.static_mesh_component.set_material(0,load('/Engine/EngineMaterials/DefaultMaterial'))
    check(LEVEL.save_current_level(),'Save catalogue')
    report['catalogue_map']=MAP
    report['preview_settings']={'source_status':'assistant-selected presentation values, not original gameplay','spacing_cm':450,'directional_light_intensities':[3.0,1.0]}

def main():
    report={'status':'running','command_line':unreal.SystemLibrary.get_command_line(),'meshes':[],'animations':[],'assemblies':[]}
    try:
        inspect_assets(report);inspect_animation(report);build_catalogue(report)
        report['status']='passed'
    except Exception:
        report['status']='failed';report['error']=traceback.format_exc();raise
    finally:
        REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print('ENEMY_FRESH_AUDIT_PASSED')

if __name__=='__main__':main()
