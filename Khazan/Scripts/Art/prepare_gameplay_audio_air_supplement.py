from prepare_gameplay_audio_scope import OUT,EXTRACT,read
import json
res=read(OUT/'ResourcePlan.json');have={r['source_package'] for r in res['events']}
missing=sorted({e['event_package'] for e in read(OUT/'PlaybackPlan.json')['events'] if e['event_package'] not in have})
(EXTRACT/'Events04Requests.json').write_text(json.dumps(missing,indent=2),encoding='utf-8')
print('MISSING PLAYBACK EVENTS',missing)
