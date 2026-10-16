from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/ImportReports/HeinMachGhosting_20261008'
state=json.loads((OUT/'CaptureState.json').read_text(encoding='utf-8'))
assert state['pid']==28236 and state['done'] and state['success']
capture=json.loads((Path(state['run'])/'CaptureMetadata.json').read_text(encoding='utf-8'))
assert len(capture['variants'])==1
variant=capture['variants'][0]
assert variant['movement_observed'] and variant['attack_montage_observed']
assert variant['requested']['name']=='Delivered_100_AA2_Count2_SavedParts254'
assert variant['requested']['all_parts_stencil'] is False,'Saved flags must be exercised, not patched by QA'
assert len(capture['parts_before'])==8 and all(p['render_custom_depth'] and p['stencil']==254 for p in capture['parts_before'])
assert len(variant['images'])==13 and all(Path(row['path']).is_file() for row in variant['images'])
assert not state.get('cleanup_error')
probe=json.loads((OUT/'RuntimeProbe.json').read_text(encoding='utf-8'))
assert len(probe['meshes'])==8 and all(row['render_custom_depth']=='True' and row['custom_depth_stencil_value']=='254' for row in probe['meshes'])
assert all(row['per_bone_motion_blur']=='True' and row['enable_update_rate_optimizations']=='False' for row in probe['meshes'])
report=dict(success=True,pid=state['pid'],world=probe['pawn'].split(':')[0],actual_input_move=True,actual_attack_montage=True,
  saved_parts_mask_verified=True,all_parts_velocity_and_animation_policy_preserved=True,capture=str(Path(state['run'])/'CaptureMetadata.json'),images=13,frames=len(variant['frames']),cvars=variant['cvars'])
(OUT/'FreshRuntimeVerification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
