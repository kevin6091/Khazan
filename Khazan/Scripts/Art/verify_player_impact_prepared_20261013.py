"""Fresh readback of the locked Main combo and its prepared audio-only edit."""
from pathlib import Path
import json
import os
import re
import traceback
import unreal as u

root = Path(os.environ['KZ_AUDIO_MAIN'])
out = Path(os.environ['KZ_AUDIO_OUTPUT'])
prepared_root = root / 'Saved/ImportReports/GameplayAudio_20261011/PlayerImpactReview_20261013/Prepared/Content'
report = {'success': False, 'errors': [], 'package_saves': 0}

def without_impact(text):
    return re.sub(r',?ImpactSound=[^,)]*', '', text)

def inspect(obj):
    nodes = obj.get_editor_property('nodes')
    windows = [w for n in nodes for w in n.get_editor_property('attack_windows')]
    return nodes, [w.get_editor_property('impact_sound') for w in windows]

try:
    u.SystemLibrary.execute_console_command(None, 'KZ.Audio.MountBindingCopies "' + str(prepared_root) + '"')
    main = u.load_object(None, '/Game/Data/ComboCommand/DA_Player_Combo_Definition.DA_Player_Combo_Definition')
    prepared = u.load_object(None, '/KZAudioBindingStage/Data/ComboCommand/DA_Player_Combo_Definition.DA_Player_Combo_Definition')
    assert main and prepared
    main_nodes, main_sounds = inspect(main)
    prepared_nodes, prepared_sounds = inspect(prepared)
    assert len(main_sounds) == len(prepared_sounds) == 60
    assert all(s and s.get_name() == 'SC_efx_pc_dualaxesword_com_impact' for s in main_sounds)
    assert all(s is None for s in prepared_sounds)
    assert [without_impact(n.export_text()) for n in main_nodes] == [without_impact(n.export_text()) for n in prepared_nodes]
    report.update({'success': True, 'main_common_count': 60, 'prepared_common_count': 0,
                   'non_audio_nodes_equal': True, 'node_count': len(main_nodes),
                   'prepared': str(prepared_root)})
except Exception:
    report['errors'].append(traceback.format_exc())
    u.log_error(report['errors'][-1])

(out / 'PreparedReadback.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
assert report['success'], report['errors']
