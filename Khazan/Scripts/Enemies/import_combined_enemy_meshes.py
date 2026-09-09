"""Import the generated complete outfits; preserve source parts separately."""
import unreal,pathlib,json,runpy,traceback
PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve()
META=PROJECT/'Content/_Art/Enemies/HeinMach/Metadata'
MANIFEST=json.loads((META/'EnemyImportManifest.json').read_text(encoding='utf-8'))
ROWS=json.loads((META/'CombinedMeshManifest.json').read_text(encoding='utf-8'))
LIB=runpy.run_path(str(PROJECT/'Scripts/Enemies/import_enemy_library.py'))
EAL=unreal.EditorAssetLibrary;ROOT=MANIFEST['destination_root']
REPORT=PROJECT/'Saved/ImportReports/HeinMachEnemy_CombinedBodies.json'
def main():
    result={'status':'running','meshes':[]}
    try:
        skeleton=unreal.load_asset(ROOT+'/Empire/Skeletons/SKEL_EN_EmpireHuman')
        materials={r['source_package']:unreal.load_asset(r['destination']) for r in MANIFEST['materials']}
        factory=unreal.load_class(None,'/Script/UnrealPSKPSA.PSKFactory')
        sk=unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
        for r in ROWS:
            mesh,created=LIB['import_one'](r['source_file'],r['asset'],unreal.new_object(factory))
            mesh.skeleton=skeleton
            slots=list(mesh.get_editor_property('materials'))
            if len(slots)!=len(r['materials']):raise RuntimeError('Combined slots '+r['asset'])
            for slot,source,name in zip(slots,r['materials'],r['slot_names']):
                slot.set_editor_property('material_interface',materials[source]);slot.set_editor_property('material_slot_name',name)
            mesh.set_editor_property('materials',slots)
            EAL.set_metadata_tag(mesh,'EnemyArtRole','CombinedSourceOutfit')
            EAL.set_metadata_tag(mesh,'OriginalPartAssembly',json.dumps(r,ensure_ascii=False))
            LIB['save'](mesh)
            result['meshes'].append({'asset':r['asset'],'vertices':sk.get_num_verts(mesh,0),'material_slots':len(slots),'source_points':r['counts']['PNTS0000'],'source_triangles':r['counts']['FACE3200']})
            print('ENEMY_COMBINED_MESH',mesh.get_name())
        result['status']='passed'
    except Exception:
        result['status']='failed';result['error']=traceback.format_exc();raise
    finally:REPORT.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
if __name__=='__main__':main()
