"""Inspect actual hair poses and the tested package in the isolated stock editor."""
from pathlib import Path
import hashlib
import json
import math
import unreal

main = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
source = main / 'Scripts/Engineering/player_parts_runtime_readback.py'
exec(compile(source.read_text(encoding='utf-8-sig'), str(source), 'exec'))
body = next(c for c in components if c.get_name() == 'CharacterMesh0')
hair = next(c for c in components if c.get_name() == 'Hair')
finite = 0
for bone in hair.get_all_socket_names():
    if not str(bone).startswith('Hair_'):
        continue
    pose = hair.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_WORLD)
    assert all(math.isfinite(v) for v in (pose.translation.x, pose.translation.y, pose.translation.z,
                                         pose.rotation.x, pose.rotation.y, pose.rotation.z, pose.rotation.w)), str(bone)
    finite += 1
assert finite == 72, finite
face_locks = []
for bone in ('Hair_LL4_001', 'Hair_LL4_002', 'Hair_RR4_001', 'Hair_RR4_002'):
    actual = hair.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_WORLD)
    parent = body.get_socket_transform(bone, unreal.RelativeTransformSpace.RTS_WORLD)
    distance = math.sqrt(sum((a - b) ** 2 for a, b in zip((actual.translation.x, actual.translation.y, actual.translation.z),
                                                        (parent.translation.x, parent.translation.y, parent.translation.z))))
    qa, qb = actual.rotation, parent.rotation
    dot = abs(qa.x * qb.x + qa.y * qb.y + qa.z * qb.z + qa.w * qb.w)
    angle = math.degrees(2 * math.acos(min(1, dot)))
    assert distance < .1 and angle < .1, (bone, distance, angle)
    face_locks.append(dict(bone=bone, position_error_cm=distance, rotation_error_degrees=angle))
manifest = json.loads((main / 'Metadata/PlayerParts_20261007/HairRefinement/CandidateManifest.json').read_text(encoding='utf-8-sig'))
for entry in manifest['packages']:
    assert hashlib.sha256((root / entry['path']).read_bytes()).hexdigest().upper() == entry['preparedSha256']
data['hair_finite_secondary_bones'] = finite
data['face_locks_follow_current_parent_pose'] = face_locks
data['tested_saved_package_count'] = len(manifest['packages'])
out = root / 'Saved/PlayerHairStockReadback.json'
out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
print('Stock saved hair verified: 72 finite bones, four face locks copied, exact candidate SHA.')
