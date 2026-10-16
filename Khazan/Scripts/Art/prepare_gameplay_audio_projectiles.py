"""Targeted current skill-object sound metadata, from saved source COI exports."""
import json
from prepare_gameplay_audio_scope import ROOT,OUT,EXTRACT,SourceCache,read,refs,package
cache=SourceCache();rows=[];events=set()
for family in read(ROOT/'Metadata/GiantCombatFall_20261011/AuthoringPlan.json')['families']:
    for obj in family['objects']:
        exports,proof=cache.get(obj['source'])
        for i,e in enumerate(exports):
            sound=e.get('Properties',{}).get('SoundData')
            if not sound:continue
            event=package(sound.get('ProjectileAudioEvent'));events.add(event)
            rows.append({'family':family['family'],'object_id':obj['id'],'source_package':obj['source'],
                'source_field':f'[{i}].Properties.SoundData','sound_data':sound,'event':event,'proof':proof,
                'playback_adapter':'Existing skill-object launch -> original projectile event; impact/EndPlay stops flight audio. Native original launch callback is not serialized.'})
(OUT/'ProjectileAudioPlan01.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
events.add('BBQ/Content/_Kazan_/Sound/Monster/yetuga_renewal/efx/efx_yetuga_fastball_obj_move_stop')
(EXTRACT/'Events05Requests.json').write_text(json.dumps(sorted(events),indent=2),encoding='utf-8')
print('PROJECTILE_EVENTS',len(events),'OBJECTS',len(rows))
