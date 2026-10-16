import json
from pathlib import Path
from prepare_gameplay_audio_scope import OUT,EXTRACT,read
resource=read(OUT/'ResourcePlan.json');have=set()
for folder in ('Raw03','Raw04'):
    have.update(r['source'] for r in read(EXTRACT/folder/'AudioFileExtractionReport.json'))
missing=sorted(set(resource['raw_requests'])-have)
(EXTRACT/'AirRawRequests.json').write_text(json.dumps(missing,indent=2),encoding='utf-8')
print('AIR RAW',len(missing),missing)
