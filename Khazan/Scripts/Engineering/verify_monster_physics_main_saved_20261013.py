"""Fresh Main loader: verify all authorized mesh/PA links and BP settings, save nothing."""
from pathlib import Path
import json,os,unreal
MAIN=Path(__file__).resolve().parents[2]
assert Path(unreal.Paths.project_dir()).resolve()==MAIN
OUT=Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
plan=json.loads((MAIN/'Metadata/MonsterSecondaryPhysics_20261013/Preparation.json').read_text(encoding='utf-8'))
verified_meshes=[]
for name in plan['meshes']:
    mesh=unreal.load_asset(name);assert mesh
    pa=mesh.get_editor_property('physics_asset');assert pa
    expected=name.rsplit('/',1)[0]+'/Physics/PA_'+name.rsplit('/',1)[1]
    assert pa.get_path_name()==expected+'.'+expected.rsplit('/',1)[1]
    assert unreal.EditorAssetLibrary.get_metadata_tag(pa,'KZSecondaryPhysicsTuning')
    verified_meshes.append(dict(mesh=mesh.get_path_name(),physics=pa.get_path_name(),
        source=unreal.EditorAssetLibrary.get_metadata_tag(pa,'KZAnatomySource')))
exec(compile((MAIN/'Scripts/Engineering/audit_monster_secondary_physics_20261013.py').read_text(encoding='utf-8'),__file__,'exec'))
inventory=json.loads((OUT/'Inventory.json').read_text(encoding='utf-8'))
for bp in inventory['blueprints']:
    if '/Monsters/' not in bp['blueprint']:continue
    for c in bp['components']:
        if c['mesh']:assert c['physics'],(bp['blueprint'],c['name'])
(OUT/'MainSavedVerification.json').write_text(json.dumps(dict(passed=True,meshes=verified_meshes,save_count=0,
    blueprints=[b['blueprint'] for b in inventory['blueprints']],scope='All imported 35 meshes and current saved gameplay components'),indent=2),encoding='utf-8')
print('MAIN SAVED VERIFICATION PASSED',len(verified_meshes))
