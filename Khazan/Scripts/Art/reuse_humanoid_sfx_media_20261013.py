"""Match verified source bytes/trim commands to existing decoded assets."""
from pathlib import Path
import hashlib
import json
from prepare_gameplay_audio_scope import ROOT,read

OUT=ROOT/'Metadata/HumanoidSFX_20261013';PRIOR=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
plan=read(OUT/'NativeCuePlan01.json');old=read(PRIOR/'NativeDecodedManifest01.json')
# Reuse this task's already imported bytes as well as the previous audit's
# bytes. A source hash, trim command and loop capability must all match.
if (OUT/'NativeDecodedImport01.json').exists():
    old += read(OUT/'NativeDecodedImport01.json')
by={}
for r in old:by.setdefault((Path(r['media']).stem,r['commands']),[]).append(r)
reused=[];new=[];keys={}
for r in plan['waves']:
    digest=hashlib.sha256(Path(r['media']).read_bytes()).hexdigest()
    matches=[x for x in by.get((Path(r['media']).stem,r['commands']),[]) if x['source_sha256']==digest and (not r['needed_loop'] or x['needed_loop'])]
    if matches:
        original=matches[0];keys[r['key']]=original['key'];reused.append(dict(original,reused_existing=True))
    else:
        keys[r['key']]=r['key'];new.append(r)
def replace(n):
    if n['kind']=='wave':n['wave_key']=keys[n['wave_key']]
    for c in n.get('children',[]):replace(c)
    if n['kind']=='surface_switch':
        for c in list(n['branches'].values())+[n['default']]:replace(c)
for r in plan['cues']:replace(r['graph'])
plan['waves']=new
(OUT/'NativeCueImportPlan01.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
(OUT/'ReusedDecoded01.json').write_text(json.dumps({r['key']:r for r in reused},indent=2),encoding='utf-8')
print('NEW WAVES',len(new),'REUSED WAVES',len(reused),'CUES',len(plan['cues']))
