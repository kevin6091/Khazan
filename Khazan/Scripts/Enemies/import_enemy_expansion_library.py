"""Import new art in the live Editor, reusing existing source assets untouched."""
import unreal,pathlib,json,sys,traceback
PROJECT=pathlib.Path(unreal.Paths.project_dir()).resolve();ROOT=PROJECT/'Saved/Extracted/HeinMachEnemiesV2'
sys.path.insert(0,str(PROJECT/'Scripts/Enemies'))
import import_enemy_library as L
M=json.loads((ROOT/'ImportManifest.json').read_text(encoding='utf-8'));EAL=unreal.EditorAssetLibrary
L.MANIFEST=M;L.DEST=M['destination_root'];L.REPORT=PROJECT/'Saved/ImportReports/HeinMachEnemyV2_Library.json'
def write(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def bind(mesh,materials,names,mapping):
    slots=list(mesh.get_editor_property('materials'));assert len(slots)==len(materials)
    for slot,p,name in zip(slots,materials,names):
        slot.set_editor_property('material_interface',mapping[p]);slot.set_editor_property('material_slot_name',name)
    mesh.set_editor_property('materials',slots)
def import_mesh(r,matmap,skels,combined=False):
    dest=r['asset'] if combined else r['destination'];source=r['source_file'];key=r['source_skeleton']
    if not combined and r['reused']:
        mesh=L.load(dest);skels[key]=mesh.get_editor_property('skeleton');return mesh,False
    mesh,new=L.import_one(source,dest,unreal.new_object(unreal.load_class(None,'/Script/UnrealPSKPSA.PSKFactory')))
    original=mesh.get_editor_property('skeleton')
    if key not in skels:
        target=M['skeletons'][key]['destination'];L.save(original);L.save(mesh)
        if EAL.does_asset_exist(target):skels[key]=L.load(target)
        else:
            assert EAL.rename_asset(original.get_path_name().split('.')[0],target);skels[key]=L.load(target)
    mesh.skeleton=skels[key]
    bind(mesh,r['materials'],r['slot_names'] if combined else r['source_slot_names'],matmap)
    L.tag(mesh,json.dumps(r['parts']) if combined else r['source_package'],'CombinedSourceOutfit' if combined else 'SourceSkeletalMesh')
    if not combined:EAL.set_metadata_tag(mesh,'SourceLODArchive',json.dumps(r['lod_files']))
    EAL.set_metadata_tag(mesh,'EnemyExpansionVersion','20260909');L.save(mesh)
    return mesh,new
def main():
    report={'status':'running','textures':[],'materials':[],'meshes':[],'combined':[]}
    try:
        original=M['textures'];M['textures']=[r for r in original if not r['reused']]
        tm={r['source_package']:L.load(r['destination']) for r in original if r['reused']};tm.update(L.textures(report));M['textures']=original
        mm=L.materials(tm,report);skels={}
        # Establish exact existing shared skeleton references before new imports.
        for r in M['meshes']:
            if r['reused']:skels[r['source_skeleton']]=L.load(r['destination']).get_editor_property('skeleton')
        for r in sorted(M['meshes'],key=lambda r:not r['carrier']):
            mesh,new=import_mesh(r,mm,skels);report['meshes'].append({'asset':mesh.get_path_name(),'created':new})
        for key,skel in skels.items():M['skeletons'][key]['destination']=skel.get_path_name().split('.')[0]
        for r in json.loads((ROOT/'CombinedMeshManifest.json').read_text(encoding='utf-8')):
            mesh,new=import_mesh(r,mm,skels,True);report['combined'].append({'asset':mesh.get_path_name(),'created':new})
        # Heavy armor has different source bind poses for its three parts.
        # Each skin keeps its own bind transforms and uses the shared animation.
        report['status']='passed';write(ROOT/'ImportManifest.json',M)
    except Exception:
        report['status']='failed';report['error']=traceback.format_exc();raise
    finally:write(L.REPORT,report)
    print('ENEMY_V2_LIBRARY',len(report['textures']),len(report['materials']),len(report['meshes']),len(report['combined']))
if __name__=='__main__':main()
