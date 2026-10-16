import os
from pathlib import Path
import json
import unreal as u
out=Path(os.environ['KZ_AUDIO_OUTPUT']);report={}
for cls in ('AnimationLibrary','SoundNodeWavePlayer','SoundNodeMixer','SoundNodeRandom','SoundNodeConcatenator','SoundNodeSwitch','SoundNodeParamCrossFade','SoundNodeModulator','SoundWave','SoundAttenuationSettings','SoundConcurrencySettings','SoundClassProperties','ReverbSettings','InteriorSettings','EditorActorSubsystem','AudioComponent','AudioMixerBlueprintLibrary'):
    c=getattr(u,cls,None);report[cls]={'available':bool(c),'methods':[n for n in dir(c or object) if not n.startswith('_')]}
for name in ('SoundCueFactoryNew','SoundAttenuationFactory','SoundConcurrencyFactory','SoundClassFactory','ReverbEffectFactory','AudioVolumeFactory','ActorFactoryBoxVolume'):
    report[name]={'available':bool(getattr(u,name,None))}
report['notify_add_docs']={n:getattr(u.AnimationLibrary,n).__doc__ for n in dir(u.AnimationLibrary) if 'notify' in n and ('add_' in n or 'remove' in n)}
(out/'AuthorAPI.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('KZAudio author API probe complete')
