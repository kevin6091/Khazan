from pathlib import Path
import json
import unreal as u

root = Path(u.Paths.project_dir()).resolve()
asset = u.load_asset('/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Attack/Attack_CloseGrab_Start')
events = list(u.AnimationLibrary.get_animation_notify_events(asset))
data = {
    'library_methods': [n for n in dir(u.AnimationLibrary) if 'notify' in n.lower()],
    'event_methods': [n for n in dir(events[0]) if 'notify' in n.lower() or 'track' in n.lower()],
    'relevant_events': [],
}
for e in events:
    obj = e.get_editor_property('notify') or e.get_editor_property('notify_state_class')
    if isinstance(obj, (u.KZAnimNotify_PlayAudio, u.KZAnimNotifyState_PlayAudio, u.KZAnimNotifyState_MonsterVisual)):
        data['relevant_events'].append({
            'name': str(e.get_editor_property('notify_name')),
            'class': obj.get_class().get_name(),
            'source_sound': (obj.get_editor_property('sound').get_path_name()
                             if isinstance(obj, u.KZAnimNotify_PlayAudio) and obj.get_editor_property('sound') else None),
        })
(root / 'Metadata/GiantGrabWarning_20261014/InspectAnimationNotifyAPI.json').write_text(
    json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
