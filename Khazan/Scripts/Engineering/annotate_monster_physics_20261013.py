"""Work-only source labels and readback; save only already-authorized physics packages."""
from pathlib import Path
import json,os,unreal
root=Path(unreal.Paths.project_dir()).resolve()
assert 'Khazan_PlayerPartsWork_20261007' in str(root)
out=Path(os.environ['KZ_MONSTER_PHYSICS_OUT'])
main=root.parent.parent/'Khazan/Khazan'
report=json.loads((main/'Metadata/MonsterSecondaryPhysics_20261013/Author01/MonsterSecondaryPhysicsAuthor.json').read_text(encoding='utf-8'))
rows=[]
for record in report['meshes']:
    mesh=unreal.load_asset(record['mesh'])
    physics=mesh.get_editor_property('physics_asset')
    assert physics and physics.get_path_name()==record['physics']
    unreal.EditorAssetLibrary.set_metadata_tag(physics,'KZAnatomySource',record['anatomy_source'])
    unreal.EditorAssetLibrary.set_metadata_tag(physics,'KZSecondaryPhysicsTuning',
        'User requested current Player hair/cloth values. Source: Player_Original_Hair/Torso_RigidBody_PhysicsAsset; original-game feel parameters unverified. Geometry/mass/inertia from imported LOD0 dominant support; see Metadata/MonsterSecondaryPhysics_20261013.')
    unreal.EditorAssetLibrary.set_metadata_tag(physics,'KZPhysicsOwnership',
        'Animation-driven anatomy; explicit hair/cloth RigidBody post-process; world ragdoll disabled. ComponentSpace for normal enemies; Yetuga WorldSpace with short-fur hard bounds, distal skin-tip contact and calculated pivot inertia x2 temporary stability multiplier. See task reports. PhysicsAsset editor exposes spring/damping/limits/collision.')
    assert unreal.EditorAssetLibrary.save_loaded_asset(physics,only_if_is_dirty=True)
    rows.append(dict(mesh=mesh.get_path_name(),physics=physics.get_path_name(),
        source=unreal.EditorAssetLibrary.get_metadata_tag(physics,'KZAnatomySource')))
(out/'SavedAssetLabels.json').write_text(json.dumps(dict(success=True,meshes=rows),indent=2),encoding='utf-8')
print('MONSTER PHYSICS LABELS/SAVED READBACK',len(rows))
