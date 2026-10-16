"""Append the remaining verified action-parent events; frozen earlier files stay."""
from pathlib import Path
import json
import hashlib
import sys
from prepare_gameplay_audio_scope import ROOT,read
OUT=ROOT/'Metadata/HumanoidSFX_20261013';PRIOR=ROOT/'Saved/Extracted/GameplayAudio_20261011'
resource=read(OUT/'ResourcePlan01.json');index=read(PRIOR/'Index03/AudioPackageIndex.json');by_suffix={}
stage=sys.argv[1] if len(sys.argv)>1 else '03'
for r in index:
    if '/WwiseAudio/' in r['path']:by_suffix.setdefault(r['path'].split('/WwiseAudio/',1)[1],[]).append(r)
events=read(OUT/'ResourcePlan.json')['events'];requested=set();names=[]
for r in read(OUT/('Events'+stage)/'MetadataExtractionReport.json'):
    assert r['status']=='ok'
    for o in read(r['target']):
        if o['Type']!='AkAudioEvent':continue
        for lang in o['EventCookedData']['EventLanguageMap']:
            if lang['Key']['LanguageName'] not in ('SFX','Korean(KR)'):continue
            value=lang['Value'];events.append({'source_package':r['source'],'name':o['Name'],'language':lang['Key'],'cooked':value,
                'metadata_file':r['target'],'metadata_sha256':hashlib.sha256(Path(r['target']).read_bytes()).hexdigest(),
                'duration_properties':{k:v for k,v in o.items() if any(t in k.lower() for t in ('duration','infinite','attenuation'))}})
            names.append(o['Name'])
            for field,key in (('SoundBanks','SoundBankPathName'),('Media','MediaPathName')):
                for v in value.get(field,[]):
                    rows=by_suffix.get(v[key],[]);assert len(rows)==1,(v[key],rows);requested.add(rows[0]['path'])
existing={}
for base in (PRIOR/'Raw03',PRIOR/'Raw04',PRIOR/'Raw05',PRIOR/'Raw06',PRIOR/'Raw07',OUT/'Raw01',OUT/'Raw02',OUT/'Raw03'):
    for r in read(base/'AudioFileExtractionReport.json'):
        if r['status']=='exported':existing[r['source']]=r
missing=sorted(requested-set(existing))
(OUT/('ResourcePlan'+stage+'.json')).write_text(json.dumps({'events':events,'reuse':{p:existing[p] for p in requested if p in existing},'extract':missing},indent=2),encoding='utf-8')
(OUT/('RawRequests'+stage+'.json')).write_text(json.dumps(missing,indent=2),encoding='utf-8')
with (OUT/'wwnames.txt').open('a',encoding='utf-8') as f:f.write('\n'+'\n'.join(names))
print('MORE_EVENTS',len(events),'RAW_NEW',len(missing),'RAW_REUSED',len(requested)-len(missing))
