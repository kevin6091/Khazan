"""Read actual modular poses after a fresh load with the current main DLL."""
from pathlib import Path
import hashlib
import json
import math
import unreal

main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
script = main / 'Scripts/Engineering/player_parts_runtime_readback.py'
exec(compile(script.read_text(encoding='utf-8-sig'), str(script), 'exec'))
summary = {}
for component in components:
    if component.get_name() not in ('Torso', 'Leg', 'Hair'):
        continue
    compared = 0
    for bone in component.get_all_socket_names():
        name = str(bone)
        if not name.startswith(('B_Cape_', 'B_Cloth_', 'B_Leather_', 'B_Iron_', 'Hair_')):
            continue
        child_q = component.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_WORLD).rotation
        assert all(math.isfinite(v) for v in (child_q.x, child_q.y, child_q.z, child_q.w)), name
        compared += 1
    assert compared, component.get_name()
    summary[component.get_name()] = {'secondary_bones_with_finite_actual_pose': compared}
manifest = json.loads((main / 'Metadata/PlayerParts_20261007/BodyCollisionTuning/CandidateManifest.json').read_text(encoding='utf-8-sig'))
for package in manifest['packages']:
    assert hashlib.sha256((root / package['path']).read_bytes()).hexdigest().upper() == package['preparedSha256']
data['secondary_pose_summary'] = summary
data['tested_saved_package_count'] = len(manifest['packages'])
out = root / 'Saved/PlayerPartsCollisionStockReadback.json'
out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('Current-stock saved packages and actual secondary poses verified:', json.dumps(summary))
