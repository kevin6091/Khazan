"""One-time migration of this task's unreferenced first assembly prototypes.

Keep deletion and re-creation in separate editor processes: a loaded generated
class can survive asset deletion until its owning Python references are released.
"""
import unreal,pathlib,json
P=pathlib.Path(unreal.Paths.project_dir()).resolve()
rows=json.loads((P/'Content/_Art/Enemies/HeinMach/Metadata/EnemyAssemblyCatalog.json').read_text(encoding='utf-8'))
E=unreal.EditorAssetLibrary;pending=[]
for r in rows:
    p=r['asset']
    if not E.does_asset_exist(p):continue
    a=unreal.load_asset(p)
    if E.get_metadata_tag(a,'EnemyAssemblyVersion')=='2_CombinedBody':continue
    if E.get_metadata_tag(a,'EnemyArtRole')!='VisualAssembly_NoGameplayAI':raise RuntimeError('Unrecognized asset '+p)
    refs=E.find_package_referencers_for_asset(p,load_assets_to_confirm=True)
    if refs:raise RuntimeError('Prototype is already in use '+p+' '+str(refs))
    pending.append(p)
for p in pending:
    if not p.startswith('/Game/_Art/Enemies/HeinMach/'):raise RuntimeError('Delete boundary')
    if not E.delete_asset(p):raise RuntimeError('Delete generated prototype '+p)
(P/'Saved/ImportReports/HeinMachEnemy_PrototypeMigration.json').write_text(json.dumps({'status':'passed','deleted_initial_prototypes':pending},indent=2),encoding='utf-8')
