import json
import os
from pathlib import Path
import traceback
import unreal as u
out=Path(os.environ['KZ_AUDIO_OUTPUT']);report={'success':False}
try:
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    volume=actors.spawn_actor_from_class(u.AudioVolume,u.Vector(0,0,500))
    origin,extent=volume.get_actor_bounds(False)
    report.update(volume=volume.get_path_name(),bounds=[list(origin.to_tuple()),list(extent.to_tuple())],brush=volume.get_editor_property('brush_component').get_path_name() if volume.get_editor_property('brush_component') else None)
    actors.destroy_actor(volume)
    report['submix_factory']=hasattr(u,'SoundSubmixFactory')
    report['recording_methods']=[n for n in dir(u.SoundSubmix) if 'record' in n]
    report['sound_factory']=hasattr(u,'SoundFactory')
    report['enums']=[n for n in dir(u) if any(v in n for v in ('AudioRecording','LoadingBehavior','CompressionType'))]
    report['success']=True
except Exception:report['error']=traceback.format_exc()
(out/'VolumeProbe.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
