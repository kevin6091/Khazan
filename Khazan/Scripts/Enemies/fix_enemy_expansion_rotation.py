"""Correct generated V2 assembly rotations using explicit UE Python axis names."""
import unreal, pathlib, json, runpy
PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve()
ROOT=PROJECT/'Saved/Extracted/HeinMachEnemiesV2'
CAT=json.loads((ROOT/'AssemblyCatalog.json').read_text(encoding='utf-8'))
M=json.loads((ROOT/'ImportManifest.json').read_text(encoding='utf-8'))
MESH={r['source_package']:r['destination'] for r in M['meshes']}
SUB=unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
LIB=unreal.SubobjectDataBlueprintFunctionLibrary
EAL=unreal.EditorAssetLibrary
REPORT=PROJECT/'Saved/ImportReports/HeinMachEnemyV2_OrientationAudit.json'

def main():
    report={'status':'running','reason':'UE 5.8 Python Rotator positional fields are roll, pitch, yaw; use explicit axis keywords.','assemblies':[]}
    for rec in CAT:
        bp=unreal.load_asset(rec['asset']);assert bp
        comps={}
        for h in SUB.k2_gather_subobject_data_for_blueprint(bp):
            c=LIB.get_object_for_blueprint(LIB.get_data(h),bp)
            if isinstance(c,unreal.SkeletalMeshComponent):comps[c.get_name()]=c
        comps['EnemyBody_GEN_VARIABLE'].set_editor_property('relative_rotation',unreal.Rotator(pitch=0,yaw=-90,roll=0))
        for e in rec['equipment']:
            r=e.get('properties',{}).get('RelativeRotation')
            if not r:continue
            cs=[c for c in comps.values() if c.get_skinned_asset().get_path_name().split('.')[0]==MESH[e['package']]]
            assert len(cs)==1,(rec['asset'],e['package'])
            cs[0].set_editor_property('relative_rotation',unreal.Rotator(pitch=r['Pitch'],yaw=r['Yaw'],roll=r['Roll']))
        EAL.set_metadata_tag(bp,'EnemyRotationContract','Named pitch=0, yaw=-90, roll=0; source equipment rotations use named axes.')
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        assert EAL.save_loaded_asset(bp,only_if_is_dirty=False)
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()
    runpy.run_path(str(PROJECT/'Scripts/Enemies/audit_enemy_expansion_catalogue.py'),run_name='__main__')
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if not a.get_actor_label().startswith('EN_Variant_'):continue
        body=next(c for c in a.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name()=='EnemyBody')
        r=body.get_world_rotation()
        assert abs(r.pitch)<1e-5 and abs(r.roll)<1e-5,(a.get_actor_label(),r)
        bones={str(body.get_bone_name(i)) for i in range(body.get_num_bones())}
        row={'actor':a.get_actor_label(),'world_rotation':{'pitch':r.pitch,'yaw':r.yaw,'roll':r.roll}}
        if 'Bip001-Head' in bones:
            head=body.get_socket_location('Bip001-Head');pelvis=body.get_socket_location('Bip001-Pelvis')
            assert head.z>pelvis.z>a.get_actor_location().z,(a.get_actor_label(),head,pelvis)
            row['head_height_cm']=head.z-a.get_actor_location().z
            row['pelvis_height_cm']=pelvis.z-a.get_actor_location().z
        report['assemblies'].append(row)
    report['status']='passed'
    REPORT.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).set_level_viewport_camera_info(unreal.Vector(1800,1110,1080),unreal.Rotator(pitch=-23,yaw=180,roll=0))
    unreal.get_editor_subsystem(unreal.EditorActorSubsystem).select_nothing()
    print('ENEMY_ORIENTATION_AUDIT_PASSED',len(report['assemblies']))

if __name__=='__main__':main()
