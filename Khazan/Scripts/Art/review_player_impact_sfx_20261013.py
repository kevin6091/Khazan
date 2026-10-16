"""Remove the duplicated common weapon impact from normal Player combo hits.

The accepted hit still plays the target's material-specific body cue. Brutal
uses its own authored animation audio and separate paired damage producer.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import traceback
import unreal as u

root = Path(os.environ['KZ_AUDIO_MAIN'])
out = Path(os.environ['KZ_AUDIO_OUTPUT'])
asset_path = '/Game/Data/ComboCommand/DA_Player_Combo_Definition'
asset_file = root / 'Content/Data/ComboCommand/DA_Player_Combo_Definition.uasset'
common_path = '/Game/Audio/Original/Events/SC_efx_pc_dualaxesword_com_impact.SC_efx_pc_dualaxesword_com_impact'
author = os.environ.get('KZ_PLAYER_IMPACT_MODE') == 'author'
report = {'success': False, 'mode': 'author' if author else 'verify', 'asset': asset_path,
          'expected_previous_common': common_path, 'errors': []}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def without_impact(text):
    return re.sub(r',?ImpactSound=[^,)]*', '', text)

try:
    lib = u.EditorAssetLibrary
    obj = lib.load_asset(asset_path)
    assert obj and asset_file.exists()
    report['before_sha256'] = sha(asset_file)
    nodes = obj.get_editor_property('nodes')
    report['node_count'] = len(nodes)
    before = [without_impact(n.export_text()) for n in nodes]
    sounds = []
    for node in nodes:
        for window in node.get_editor_property('attack_windows'):
            sound = window.get_editor_property('impact_sound')
            sounds.append(sound.get_path_name() if sound else None)
    report['window_count'] = len(sounds)
    if author:
        assert len(sounds) == 60, 'Unexpected Player attack-window count'
        assert all(path == common_path for path in sounds), 'Concurrent/different Player impact binding'
        backup = out / 'Before/Content/Data/ComboCommand/DA_Player_Combo_Definition.uasset'
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset_file, backup)
        report['backup'] = str(backup)
        for ni, node in enumerate(nodes):
            windows = node.get_editor_property('attack_windows')
            for wi, window in enumerate(windows):
                window.set_editor_property('impact_sound', None)
                windows[wi] = window
            node.set_editor_property('attack_windows', windows)
            nodes[ni] = node
        assert before == [without_impact(n.export_text()) for n in nodes], 'Non-audio combo fields changed'
        obj.set_editor_property('nodes', nodes)
        lib.set_metadata_tag(obj, 'OriginalAudioHitPolicy',
            'Normal Player combo: target material body hit only on accepted HP damage; '
            'common weapon impact removed after listening review. Brutal retains authored grapple cues.')
        prepared_root = root / 'Saved/ImportReports/GameplayAudio_20261011/PlayerImpactReview_20261013/Prepared/Content'
        prepared = prepared_root / 'Data/ComboCommand/DA_Player_Combo_Definition.uasset'
        u.SystemLibrary.execute_console_command(None,
            'KZ.Audio.SaveBindingCopy "' + asset_path + '" "' + str(prepared_root) + '"')
        assert prepared.exists(), 'Prepared Player combo package was not saved'
        report['prepared'] = str(prepared)
        report['prepared_sha256'] = sha(prepared)
        assert sha(asset_file) == report['before_sha256'], 'Concurrent Main asset change'
        replacement = out / 'Replace/DA_Player_Combo_Definition.uasset'
        replacement.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prepared, replacement)
        try:
            os.replace(replacement, asset_file)
            report['main_applied'] = True
        except PermissionError:
            report['main_applied'] = False
            report['pending_locked_main'] = True
    else:
        assert len(sounds) == 60, 'Unexpected Player attack-window count'
        assert all(path is None for path in sounds), 'Normal Player hit still has common impact'
    report['after_sha256'] = sha(asset_file)
    report['remaining_common_bindings'] = 0 if author and report['main_applied'] else sum(path == common_path for path in sounds)
    report['material_body_hit_owners'] = 'unchanged CharacterDefinition.HitReactions.ImpactSound'
    report['success'] = True
except Exception:
    report['errors'].append(traceback.format_exc())
    u.log_error(report['errors'][-1])

(out / 'PlayerImpactReview.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
assert report['success'], report['errors']
