from pathlib import Path
import json
import os
import traceback
import unreal

out=Path(os.environ['KZ_AUDIO_OUTPUT'])
report={}
for name in ('SoundCue','SoundNodeRandom','SoundNodeWavePlayer','SoundNodeLooping','SoundAttenuation',
             'SoundConcurrency','SoundSubmix','ReverbEffect','SoundClass','AudioVolume'):
    cls=getattr(unreal,name,None)
    report[name]={'available':bool(cls),'methods':[n for n in dir(cls or object) if not n.startswith('_') and
                 any(x in n for x in ('sound','node','loop','record','reverb','child','submix','volume'))]}
try:
    cue=unreal.new_object(unreal.SoundCue)
    node=unreal.new_object(unreal.SoundNodeRandom,outer=cue)
    wave=unreal.new_object(unreal.SoundNodeWavePlayer,outer=cue)
    for obj,key,value in ((cue,'first_node',node),(cue,'all_nodes',[node,wave]),
                          (node,'child_nodes',[wave]),(node,'weights',[1.0])):
        try:
            obj.set_editor_property(key,value)
            result={'class':obj.get_class().get_name(),'property':key,'passed':True}
        except Exception as error:
            result={'class':obj.get_class().get_name(),'property':key,'passed':False,'error':str(error)}
        report.setdefault('property_writes',[]).append(result)
except Exception:
    report['error']=traceback.format_exc()
(out/'AudioAPI.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
