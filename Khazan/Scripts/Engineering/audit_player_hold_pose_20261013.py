"""Read-only check whether the captured-player pose is stationary after root frame 10."""
from pathlib import Path
import json
import math
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
out = root / "Metadata/GiantGrabs_20261013/PlayerHoldPoseAudit.json"
rows = []
for path in (
    "/Game/_Art/Player/Animation/Weapons/DualAxeSword/Recovered/CA_P_Kazan_Hold_Demon",
    "/Game/_Art/Player/Animation/Common/Interaction/Hold/CA_P_Kazan_Hold_Demon",
):
    sequence = unreal.load_asset(path)
    if not sequence:
        rows.append({"path": path, "error": "missing"})
        continue
    frames = unreal.AnimationLibrary.get_num_frames(sequence)
    bones = []
    for bone in unreal.AnimationLibrary.get_animation_track_names(sequence):
        a = unreal.AnimationLibrary.get_bone_pose_for_frame(sequence, bone, 10, False)
        b = unreal.AnimationLibrary.get_bone_pose_for_frame(sequence, bone, min(39, frames - 1), False)
        ta, tb = a.translation, b.translation
        translation = math.dist((ta.x, ta.y, ta.z), (tb.x, tb.y, tb.z))
        qa, qb = a.rotation, b.rotation
        first = math.dist((qa.x, qa.y, qa.z, qa.w), (qb.x, qb.y, qb.z, qb.w))
        second = math.dist((qa.x, qa.y, qa.z, qa.w), (-qb.x, -qb.y, -qb.z, -qb.w))
        bones.append({"bone": str(bone), "translation_delta_cm": translation,
                      "quaternion_delta": min(first, second)})
    moving = [b for b in bones if b["translation_delta_cm"] > 0.05 or b["quaternion_delta"] > 0.0005]
    rows.append({"path": path, "frames": frames,
                 "length_seconds": unreal.AnimationLibrary.get_sequence_length(sequence),
                 "track_count": len(bones), "moving_after_frame_10": len(moving),
                 "root": bones[0] if bones else None,
                 "moving_examples": sorted(moving, key=lambda x: x["translation_delta_cm"] + 100 * x["quaternion_delta"], reverse=True)[:15]})
out.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
unreal.log("PLAYER_HOLD_POSE_AUDIT " + json.dumps(rows, ensure_ascii=False))
unreal.SystemLibrary.quit_editor()
