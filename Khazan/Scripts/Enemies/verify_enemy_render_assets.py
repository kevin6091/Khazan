"""Compile new Enemy materials with a real RHI and re-open the saved catalogue.

Only unreferenced temporary import companions in this task's staging are removed.
"""
import unreal,pathlib,json,traceback
PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve()
META=PROJECT/'Content/_Art/Enemies/HeinMach/Metadata'
M=json.loads((META/'EnemyImportManifest.json').read_text(encoding='utf-8'))
CAT=json.loads((META/'EnemyAssemblyCatalog.json').read_text(encoding='utf-8'))
ROOT=M['destination_root'];EAL=unreal.EditorAssetLibrary
REPORT=PROJECT/'Saved/ImportReports/HeinMachEnemy_RenderAssetAudit.json'
def check(v,msg):
    if not v:raise RuntimeError(msg)
def main():
    result={'status':'running','command_line':unreal.SystemLibrary.get_command_line(),'materials':[],'deleted_staging':[],'assemblies':[]}
    try:
        for p in [r['destination'] for r in M['materials']]+[ROOT+'/Shared/Materials/M_EN_InvisiblePoseCarrier']:
            mat=unreal.load_asset(p);check(mat,'Missing '+p)
            stats=unreal.MaterialEditingLibrary.get_statistics(mat)
            data={name:stats.get_editor_property(name) for name in ['num_vertex_shader_instructions','num_pixel_shader_instructions','num_samplers','num_pixel_texture_samples']}
            check(data['num_vertex_shader_instructions']>0 and data['num_pixel_shader_instructions']>0,'No compiled shaders '+p+' '+str(data))
            result['materials'].append({'asset':p,**data});print('ENEMY_SHADER_OK',mat.get_name())
        level=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        check(level.load_level(ROOT+'/Preview/L_HeinMach_EnemyCatalogue'),'Catalogue reload')
        actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
        actor_map={a.get_actor_label():a for a in actors}
        for r in CAT:
            label=r['asset'].rsplit('/',1)[1];check(label in actor_map,'Saved catalogue actor '+label)
            a=actor_map[label];comps={c.get_name():c for c in a.get_components_by_class(unreal.SkeletalMeshComponent)}
            main=comps['EnemyBody']
            check(len(comps)==(3 if r['family']=='SwordShield' else 2),'Saved body components '+label)
            check(main.get_editor_property('animation_data').anim_to_play,'Saved idle '+label)
            check(str(comps['EnemyWeapon_R'].get_attach_socket_name())=='Weapon_R','Saved weapon socket '+label)
            if r['family']=='SwordShield':check(str(comps['EnemyShield_L'].get_attach_socket_name())=='Weapon_L','Saved shield socket '+label)
            result['assemblies'].append(label)
        stage=ROOT+'/_ImportStaging'
        pending=EAL.list_assets(stage,recursive=True,include_folder=False)
        for p in pending:
            refs=EAL.find_package_referencers_for_asset(p,load_assets_to_confirm=True)
            outside=[str(x) for x in refs if not str(x).startswith(stage+'/')]
            check(not outside,'Staging is still referenced '+p+' '+str(outside))
        for p in pending:
            check(p.startswith(stage+'/'),'Delete boundary')
            check(EAL.delete_asset(p),'Delete unused companion '+p);result['deleted_staging'].append(p)
        result['status']='passed'
    except Exception:
        result['status']='failed';result['error']=traceback.format_exc();raise
    finally:REPORT.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    print('ENEMY_RENDER_ASSETS_PASSED')
if __name__=='__main__':main()
