"""Fresh saved Main readback after promoting the reviewed audio-only combo edit."""

from pathlib import Path
import json
import os
import re
import traceback
import unreal as u


root = Path(os.environ["KZ_AUDIO_MAIN"])
out = Path(os.environ["KZ_AUDIO_OUTPUT"])
baseline = root / "Metadata/PlayerImpactSFX_20261013/MainApply_20261014/Before/Content"
report = {"success": False, "errors": [], "package_saves": 0}


def without_impact(text):
    return re.sub(r",?ImpactSound=[^,)]*", "", text)


def inspect(obj):
    nodes = obj.get_editor_property("nodes")
    windows = [w for node in nodes for w in node.get_editor_property("attack_windows")]
    return nodes, [w.get_editor_property("impact_sound") for w in windows]


try:
    u.SystemLibrary.execute_console_command(None, 'KZ.Audio.MountBindingCopies "' + str(baseline) + '"')
    main = u.load_object(None, "/Game/Data/ComboCommand/DA_Player_Combo_Definition.DA_Player_Combo_Definition")
    before = u.load_object(None, "/KZAudioBindingStage/Data/ComboCommand/DA_Player_Combo_Definition.DA_Player_Combo_Definition")
    assert main and before
    main_nodes, main_sounds = inspect(main)
    before_nodes, before_sounds = inspect(before)
    assert len(main_nodes) == len(before_nodes) == 26
    assert len(main_sounds) == len(before_sounds) == 60
    assert all(sound is None for sound in main_sounds)
    assert all(sound and sound.get_name() == "SC_efx_pc_dualaxesword_com_impact" for sound in before_sounds)
    assert [without_impact(node.export_text()) for node in main_nodes] == [
        without_impact(node.export_text()) for node in before_nodes
    ]
    report.update({"success": True, "main_common_count": 0, "before_common_count": 60,
                   "non_audio_nodes_equal": True, "node_count": 26, "window_count": 60})
except Exception:
    report["errors"].append(traceback.format_exc())
    u.log_error(report["errors"][-1])

out.mkdir(parents=True, exist_ok=True)
(out / "MainReadback.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
assert report["success"], report["errors"]
