"""Select only missing source events/banks/media from the saved two-chunk index."""
from pathlib import Path
import json
import hashlib
import sys
from prepare_gameplay_audio_scope import ROOT,read

OUT=ROOT/'Metadata/HumanoidSFX_20261013';PRIOR=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
EXTRACT=ROOT/'Saved/Extracted/GameplayAudio_20261011'
plan=read(OUT/'PlaybackPlan01.json')
if len(sys.argv)==1:
    requests=set(plan['additional_events'])
    requests.add('BBQ/Content/_Kazan_/Sound/Monster/monster/empireswordshield_s/efx_empireswordshield_s_guard')
    (OUT/'EventRequests01.json').write_text(json.dumps(sorted(requests),indent=2),encoding='utf-8')
    print('SOURCE EVENTS',len(requests))
else:
    index=read(EXTRACT/'Index03/AudioPackageIndex.json');by_suffix={}
    for r in index:
        if '/WwiseAudio/' in r['path']:by_suffix.setdefault(r['path'].split('/WwiseAudio/',1)[1],[]).append(r)
    source=[];requests={'BBQ/Content/WwiseAudio/Init.bnk'};names=set()
    for r in read(OUT/'Events01/MetadataExtractionReport.json'):
        assert r['status']=='ok',r['source']
        for o in read(r['target']):
            if o['Type']!='AkAudioEvent':continue
            for lang in o.get('EventCookedData',{}).get('EventLanguageMap',[]):
                if lang['Key']['LanguageName'] not in ('SFX','Korean(KR)'):continue
                value=lang['Value'];source.append({'source_package':r['source'],'name':o['Name'],'language':lang['Key'],'cooked':value,
                    'metadata_file':r['target'],'metadata_sha256':hashlib.sha256(Path(r['target']).read_bytes()).hexdigest(),
                    'duration_properties':{k:v for k,v in o.items() if any(t in k.lower() for t in ('duration','infinite','attenuation'))}})
                names.add(o['Name'])
                for field,key in (('SoundBanks','SoundBankPathName'),('Media','MediaPathName')):
                    for v in value.get(field,[]):
                        matches=by_suffix.get(v[key],[]);assert len(matches)==1,(v[key],matches)
                        requests.add(matches[0]['path']);names.add(v.get('DebugName',''))
    existing={}
    for directory in ('Raw03','Raw04','Raw05','Raw06','Raw07'):
        for row in read(EXTRACT/directory/'AudioFileExtractionReport.json'):
            if row['status']=='exported':existing[row['source']]=row
    missing=sorted(p for p in requests if p not in existing)
    (OUT/'ResourcePlan01.json').write_text(json.dumps({'events':source,'raw_requests':sorted(requests),'reuse':{p:existing[p] for p in requests if p in existing},'extract':missing},indent=2),encoding='utf-8')
    (OUT/'RawRequests01.json').write_text(json.dumps(missing,indent=2),encoding='utf-8')
    (OUT/'wwnames.txt').write_text((PRIOR/'Tools/wwnames.txt').read_text(encoding='utf-8-sig')+'\n'+'\n'.join(sorted(names)),encoding='utf-8')
    print('EVENT LANGUAGE BRANCHES',len(source),'RAW EXTRACTION',len(missing),'REUSED',len(requests)-len(missing))
