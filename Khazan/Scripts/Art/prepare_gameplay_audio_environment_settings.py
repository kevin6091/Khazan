"""Resolved zone extents and original source reverb provenance; native DSP adapter."""
from pathlib import Path
from collections import Counter
import json
from prepare_gameplay_audio_scope import OUT,read,refs,package
source=read(OUT/'HeinMachEnvironmentPlan01.json');cues={r['event_package']:r for r in read(OUT/'NativeCuePlan01.json')['cues']}
rows=[];missing=[]
for r in source:
    p=(r['root'] or {}).get('Properties',{});rotation=p.get('RelativeRotation',{'Pitch':0,'Yaw':0,'Roll':0})
    scale=p.get('RelativeScale3D',{'X':1.,'Y':1.,'Z':1.})
    outer=(r.get('brush') or {}).get('Bounds',{}).get('BoxExtent')
    inner=(r.get('inner_box') or {}).get('Properties',{}).get('BoxExtent')
    reverb=[e for e in r['components'] if e['Type']=='AkLateReverbComponent']
    aux=next((package(e.get('Properties',{}).get('AuxBus')) for e in reverb if e.get('Properties',{}).get('AuxBus')),'')
    for pkg in r['events']:
        if pkg not in cues:missing.append({'actor':r['source_actor'],'event':pkg});continue
        cue=cues[pkg];props=cue['source']['duration_properties'];rad=props.get('MaxAttenuationRadius',0)
        # Source point-event repetition isn't serialized for plain AkAmbientSound.
        # The original continuous containers remain intact; finite environmental
        # details get a named native delay profile, instead of a per-frame timer.
        repeat=not cue['loop'] and '/vo/' not in pkg.lower()
        rows.append({'source_actor':r['source_actor'],'source_type':r['type'],'source_file':r['source_file'],
            'source_sha256':r['source_sha256'],'event':pkg,'cue':cue['asset'],'location':r['location'],'rotation':rotation,'scale':scale,
            'outer_extent':outer,'inner_extent':inner,'source_aux_bus':aux,'source_reverb_components':reverb,
            'source_max_attenuation_cm':rad,'source_infinite':props.get('IsInfinite'),'repeat_adapter':repeat,
            'repeat_delay_seconds':[12.,28.] if repeat else None,
            'repeat_source':'Temporary sparse environmental repetition; original native actor repost policy not serialized.' if repeat else 'Original bank continuous/loop structure',
            'box_falloff_cm':max((outer[a]-inner[a])*scale[a] for a in ('X','Y','Z')) if outer and inner else None})
plan={'actors':rows,'missing':missing,'policy':{'coordinates':'Original UE level world cm, source root transform, no axis/scale conversion',
    'reverb':'Original room/outside aux names and volume extents; native UE DSP settings are temporary adapters',
    'repetition':'Source bank continuous loops; sparse12–28s only where native AkAmbientSound repost policy is absent',
    'fire':'Current placed torch/brazier actors, exact original Play_Chaos_LOBJ_Fire_Loop bank; no visual changes'}}
(OUT/'EnvironmentAuthoringPlan01.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print('ENV READY',len(rows),'missing',missing,'zones',sum(bool(r['outer_extent']) for r in rows),'finite repeats',sum(r['repeat_adapter'] for r in rows))
