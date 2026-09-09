"""Fresh process, real-RHI material and saved catalogue verification."""
import unreal,pathlib,json,traceback
PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve();ROOT=PROJECT/'Saved/Extracted/HeinMachEnemiesV2'
M=json.loads((ROOT/'ImportManifest.json').read_text(encoding='utf-8'));CAT=json.loads((ROOT/'AssemblyCatalog.json').read_text(encoding='utf-8'))
def main():
    report={'status':'running','materials':[],'textures':[],'assemblies':[]}
    try:
        for r in M['materials']:
            mat=unreal.load_asset(r['destination']);assert mat
            s=unreal.MaterialEditingLibrary.get_statistics(mat)
            values={k:s.get_editor_property(k) for k in ['num_vertex_shader_instructions','num_pixel_shader_instructions','num_samplers','num_pixel_texture_samples']}
            assert values['num_vertex_shader_instructions']>0 and values['num_pixel_shader_instructions']>0,(r['destination'],values)
            report['materials'].append({'asset':r['destination'],**values})
        for r in M['textures']:
            tex=unreal.load_asset(r['destination']);assert tex
            assert tex.get_editor_property('srgb')==r['properties'].get('SRGB',True),r['destination']
            report['textures'].append(r['destination'])
        assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level('/Game/_Art/Enemies/HeinMach/Preview/L_HeinMach_EnemyCatalogue')
        actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors();catalogue={a.get_actor_label():a for a in actors if a.get_actor_label().startswith('EN_Variant_')}
        assert len(catalogue)==16
        for rec in CAT:
            actor=catalogue['EN_Variant_'+rec['asset'].rsplit('/',1)[1]]
            comps={c.get_name():c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent)};body=comps['EnemyBody']
            rotation=body.get_editor_property('relative_rotation')
            assert abs(rotation.pitch)<1e-6 and abs(rotation.roll)<1e-6 and abs(rotation.yaw+90)<1e-6,(rec['asset'],'body rotation',rotation)
            assert body.get_editor_property('animation_data').anim_to_play
            for name,comp in comps.items():
                mesh=comp.get_skinned_asset();assert mesh and mesh.get_editor_property('skeleton')
                if name!='EnemyBody':assert comp.get_attach_parent()==body
                if name.startswith(('EnemyWeapon','EnemyShield','EnemyQuiver')):assert body.does_socket_exist(comp.get_attach_socket_name())
                assert all(comp.get_material(i) is not None for i in range(comp.get_num_materials()))
            report['assemblies'].append({'asset':rec['asset'],'components':len(comps),'saved_blueprint_construction':True,'weapon_attachments':True})
        report['status']='passed'
    except Exception:
        report['status']='failed';report['error']=traceback.format_exc();raise
    finally:(PROJECT/'Saved/ImportReports/HeinMachEnemyV2_RenderAudit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    print('ENEMY_V2_RENDER_AUDIT_PASSED')
if __name__=='__main__':main()
