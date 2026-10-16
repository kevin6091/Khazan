"""Read only actual Original components, final cloth poses and verified files."""
import hashlib, json, math
from pathlib import Path
import unreal
root = Path(unreal.Paths.project_dir()).resolve()
main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
exec(compile((main / 'Scripts/Engineering/player_parts_runtime_readback.py').read_text(encoding='utf-8-sig'), 'parts_readback', 'exec'))
data = json.loads((root / 'Saved/PlayerPartsRuntimeReadback.json').read_text(encoding='utf-8-sig'))
finite = {}
for component in components:
    if component.get_name() not in ('Torso', 'Leg', 'Hair'): continue
    count = 0
    for bone in component.get_all_socket_names():
        if not str(bone).startswith(('B_Cape_', 'B_Cloth_', 'B_Leather_', 'B_Iron_', 'Hair_')): continue
        transform = component.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_WORLD)
        values = [transform.translation.x, transform.translation.y, transform.translation.z,
                  transform.rotation.x, transform.rotation.y, transform.rotation.z, transform.rotation.w,
                  transform.scale3d.x, transform.scale3d.y, transform.scale3d.z]
        assert all(math.isfinite(v) for v in values), (component.get_name(), str(bone))
        assert max(abs(v - 1) for v in values[-3:]) < .001, (component.get_name(), str(bone))
        count += 1
    finite[component.get_name()] = count
assert finite == {'Torso': 12, 'Leg': 59, 'Hair': 72}, finite
report = Path(globals().get('cloth_report_directory',
                          main / 'Metadata/PlayerParts_20261007/ClothRefinement')).resolve()
assert report.is_relative_to(main / 'Metadata') and report != main / 'Metadata'
manifest = json.loads((report / 'CandidateManifest.json').read_text(encoding='utf-8-sig'))
for entry in manifest['packages']:
    assert hashlib.sha256((root / entry['path']).read_bytes()).hexdigest().upper() == entry['preparedSha256']
hair_path = 'Content/_Art/Player/Character/Meshs/Hair/Player_Original_Hair_RigidBody_PhysicsAsset.uasset'
protected = json.loads((report / 'ProtectedBefore.json').read_text(encoding='utf-8-sig'))
expected_hair = next(e['sha256'] for e in protected if e['path'] == hair_path)
assert hashlib.sha256((root / hair_path).read_bytes()).hexdigest().upper() == expected_hair
data.update(success=True, finite_secondary_bones=finite, hair_pa_unchanged=True,
            tested_saved_package_count=len(manifest['packages']))
(root / 'Saved/PlayerClothStockReadback.json').write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('Stock Original parts and final cloth poses verified; Hair PA preserved.')
