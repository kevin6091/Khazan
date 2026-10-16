"""Read the saved early audio notify fields used by the focused PIE failure."""
import json
import os
from pathlib import Path
import unreal as u

out = Path(os.environ['KZ_AUDIO_OUTPUT']) / 'EarlyNotifyEvents.json'
assets = [
    '/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Damage/Damage_Parry_F',
    '/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Damage/Damage_JustGuardReaction',
    '/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Locomotion/Locomotion_TurnBackRun_Short_01',
]
report = []
for path in assets:
    seq = u.EditorAssetLibrary.load_asset(path)
    assert seq, path
    for event in u.AnimationLibrary.get_animation_notify_events(seq):
        notify = event.get_editor_property('notify')
        if not isinstance(notify, u.KZAnimNotify_PlayAudio):
            continue
        sound = notify.get_editor_property('sound')
        report.append({'asset': path, 'name': notify.get_name(),
                       'sound': sound.get_path_name() if sound else None,
                       'event': event.export_text()})
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
