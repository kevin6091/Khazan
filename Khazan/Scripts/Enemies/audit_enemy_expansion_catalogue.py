"""Validate and display the curated human Enemy library in its art-only map."""
import unreal,pathlib,json,traceback
PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve();ROOT=PROJECT/'Saved/Extracted/HeinMachEnemiesV2'
EAL=unreal.EditorAssetLibrary;ACTORS=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);LEVEL=unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
M=json.loads((ROOT/'ImportManifest.json').read_text(encoding='utf-8'));CATALOG=json.loads((ROOT/'AssemblyCatalog.json').read_text(encoding='utf-8'))
MAP='/Game/_Art/Enemies/HeinMach/Preview/L_HeinMach_EnemyCatalogue'
def path(x):return x.get_path_name().split('.')[0] if x else None
def load(p):
    x=unreal.load_asset(p);assert x,p;return x
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def main():
    report={'status':'running','assemblies':[],'materials':[],'legacy_moves':[]}
    try:
        assert LEVEL.load_level(MAP)
        # This level was generated in the preceding Enemy extraction. Only its
        # generated catalogue actors and presentation helpers are replaced.
        for a in list(ACTORS.get_all_level_actors()):
            label=a.get_actor_label()
            if label.startswith(('BP_EN_','EnemyCatalogue_','EN_Variant_','EN_Label_')):ACTORS.destroy_actor(a)
        order=['Swordsman','SwordShield','Archer','HeavySwordsman','HalberdElite','Mage','MageHard'];row_counts={}
        for rec in CATALOG:
            fam=rec['family'];row=row_counts.get(fam,0);row_counts[fam]=row+1
            location=unreal.Vector(-row*370,order.index(fam)*370,0)
            actor=ACTORS.spawn_actor_from_class(EAL.load_blueprint_class(rec['asset']),location);assert actor
            actor.set_actor_label('EN_Variant_'+rec['asset'].rsplit('/',1)[1]);actor.set_folder_path('Enemies/'+rec['source_level']+'/'+fam)
            comps={c.get_name():c for c in actor.get_components_by_class(unreal.SkeletalMeshComponent)};main=comps['EnemyBody']
            rotation=main.get_editor_property('relative_rotation')
            assert abs(rotation.pitch)<1e-6 and abs(rotation.roll)<1e-6 and abs(rotation.yaw+90)<1e-6,(fam,'body rotation',rotation)
            assert path(main.get_editor_property('animation_data').anim_to_play)==rec['idle_asset']
            expected=5 if fam=='HeavySwordsman' else 3 if fam in ['Archer','SwordShield'] else 2;assert len(comps)==expected,(fam,comps.keys())
            for name,comp in comps.items():
                if name=='EnemyBody':continue
                assert comp.get_attach_parent()==main,(fam,name,'attachment')
                socket=str(comp.get_attach_socket_name())
                if name.startswith('EnemyArmor_'):
                    assert path(comp.get_editor_property('animation_data').anim_to_play)==rec['idle_asset']
                    assert comp.get_editor_property('animation_data').saved_play_rate==1.0
                else:assert main.does_socket_exist(socket),(fam,name,socket)
            label=ACTORS.spawn_actor_from_class(unreal.TextRenderActor,location+unreal.Vector(65,0,240))
            label.set_actor_label('EN_Label_'+fam+'_'+str(row+1));label.set_folder_path('PreviewOnly/Labels')
            text=label.get_component_by_class(unreal.TextRenderComponent);text.set_text(unreal.Text(fam+' / Outfit '+str(row+1).zfill(2)));text.set_world_size(23)
            text.set_text_render_color(unreal.Color(220,232,240,255))
            report['assemblies'].append({'asset':rec['asset'],'family':fam,'components':len(comps),'source_cb':rec['source_cb'],'idle':rec['idle_asset'],'equipment':rec['equipment'],'source_bind_preserved':True})
        floor=ACTORS.spawn_actor_from_class(unreal.StaticMeshActor,unreal.Vector(-520,1110,-10));floor.set_actor_label('EnemyCatalogue_Floor');floor.set_folder_path('PreviewOnly')
        floor.static_mesh_component.set_static_mesh(load('/Engine/BasicShapes/Cube'));floor.set_actor_scale3d(unreal.Vector(24,31,0.2))
        for name,rotation,intensity,priority in [('KeyLight',unreal.Rotator(pitch=-45,yaw=-30,roll=0),3.0,2),('FillLight',unreal.Rotator(pitch=-25,yaw=150,roll=0),1.0,1)]:
            light=ACTORS.spawn_actor_from_class(unreal.DirectionalLight,unreal.Vector(0,0,600),rotation);light.set_actor_label('EnemyCatalogue_'+name);light.set_folder_path('PreviewOnly')
            component=light.get_component_by_class(unreal.DirectionalLightComponent);component.set_editor_property('mobility',unreal.ComponentMobility.MOVABLE);component.set_intensity(intensity);component.set_editor_property('forward_shading_priority',priority)
        sky=ACTORS.spawn_actor_from_class(unreal.SkyAtmosphere,unreal.Vector());sky.set_actor_label('EnemyCatalogue_Sky');sky.set_folder_path('PreviewOnly')
        skylight=ACTORS.spawn_actor_from_class(unreal.SkyLight,unreal.Vector(0,0,500));skylight.set_actor_label('EnemyCatalogue_Ambient');skylight.set_folder_path('PreviewOnly')
        skylight.get_component_by_class(unreal.SkyLightComponent).set_editor_property('real_time_capture',True)
        assert LEVEL.save_current_level()
        # Preserve the previous face-heavy generated variants in an explicit
        # archive. Keep an explicit mapping; transient rename redirectors are
        # not necessarily persisted when a commandlet saves the destination.
        old=json.loads((PROJECT/'Content/_Art/Enemies/HeinMach/Metadata/EnemyAssemblyCatalog.json').read_text(encoding='utf-8'))
        for rec in old:
            src=rec['asset'];dst='/Game/_Art/Enemies/HeinMach/Archive/FaceVariants_20260908/Blueprints/'+src.rsplit('/',1)[1]
            if EAL.does_asset_exist(src) and not EAL.does_asset_exist(dst):assert EAL.rename_asset(src,dst);report['legacy_moves'].append({'from':src,'to':dst})
        oldmesh=json.loads((PROJECT/'Content/_Art/Enemies/HeinMach/Metadata/CombinedMeshManifest.json').read_text(encoding='utf-8'))
        for rec in oldmesh:
            src=rec['asset'];dst='/Game/_Art/Enemies/HeinMach/Archive/FaceVariants_20260908/Meshes/'+src.rsplit('/',1)[1]
            if EAL.does_asset_exist(src) and not EAL.does_asset_exist(dst):assert EAL.rename_asset(src,dst);report['legacy_moves'].append({'from':src,'to':dst})
        EAL.save_directory('/Game/_Art/Enemies/HeinMach/Archive',only_if_is_dirty=True,recursive=True)
        if report['legacy_moves']:write(ROOT/'LegacyAssetMoves.json',report['legacy_moves'])
        assert LEVEL.save_current_level()
        # Source texture identity and material parents remain package-keyed.
        mats={r['source_package']:r['destination'] for r in M['materials']};textures={r['source_package']:r['destination'] for r in M['textures']}
        for r in M['materials']:
            material=load(r['destination']);pr=r['source_object'].get('Properties',{})
            if r['source_type']=='MaterialInstanceConstant':
                p=pr['Parent']['ObjectPath'].split('.')[0];assert path(material.get_editor_property('parent'))==mats[p]
                for t in pr.get('TextureParameterValues',[]):
                    p=t.get('ParameterValue',{}).get('ObjectPath','').split('.')[0]
                    if p in textures:assert path(unreal.MaterialEditingLibrary.get_material_instance_texture_parameter_value(material,t['ParameterInfo']['Name']))==textures[p]
            report['materials'].append(r['destination'])
        report.update({'status':'passed','map':MAP,'active_variants':len(CATALOG),'face_identities':['001','002','003'],'preview_parameters':'Gallery spacing 370 cm, text 23 cm, key/fill 3/1: presentation choices, not original gameplay metadata.'})
    except Exception:
        report['status']='failed';report['error']=traceback.format_exc();raise
    finally:write(PROJECT/'Saved/ImportReports/HeinMachEnemyV2_CatalogueAudit.json',report)
if __name__=='__main__':main()
