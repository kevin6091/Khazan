"""Select original Korean/SFX banks and media, retaining package/archive proof."""
from collections import Counter
from pathlib import Path
import hashlib
import json
from prepare_gameplay_audio_scope import ROOT, OUT, EXTRACT, read

def main():
    index = read(EXTRACT/'Index03/AudioPackageIndex.json')
    by_path = {r['path']: r for r in index}
    by_suffix = {}
    for path in by_path:
        if '/WwiseAudio/' in path:
            by_suffix.setdefault(path.split('/WwiseAudio/',1)[1], []).append(path)
    requests = {'BBQ/Content/WwiseAudio/Init.bnk'}
    events = []
    gamesyncs = []
    aux = []
    names = set()
    metadata_reports = read(EXTRACT/'Events02/MetadataExtractionReport.json')
    metadata_reports += read(EXTRACT/'Supplement01/MetadataExtractionReport.json')
    metadata_reports += read(EXTRACT/'Events03/MetadataExtractionReport.json')
    metadata_reports += read(EXTRACT/'Events04/MetadataExtractionReport.json')
    if (EXTRACT/'Events05/MetadataExtractionReport.json').exists():
        metadata_reports += read(EXTRACT/'Events05/MetadataExtractionReport.json')
    if (EXTRACT/'Events06/MetadataExtractionReport.json').exists():
        metadata_reports += read(EXTRACT/'Events06/MetadataExtractionReport.json')
    seen_sources=set()
    for report in metadata_reports:
        if report['status'] != 'ok' or report['source'] in seen_sources:
            continue
        seen_sources.add(report['source'])
        exports = read(report['target'])
        for obj in exports:
            typ = obj.get('Type','')
            names.add(obj.get('Name',''))
            if typ in ('AkSwitchValue','AkStateValue','AkRtpc'):
                gamesyncs.append({'source_package': report['source'], 'export': obj})
                if typ in ('AkSwitchValue','AkStateValue'):
                    names.add(report['source'].rsplit('/',2)[-2])
                    names.add(obj.get('GroupValueCookedData',{}).get('DebugName',''))
            if typ == 'AkAuxBus':
                aux.append({'source_package': report['source'], 'export': obj})
            if typ != 'AkAudioEvent':
                continue
            cooked = obj.get('EventCookedData', {})
            language_rows = cooked.get('EventLanguageMap', [])
            chosen = [r for r in language_rows if r['Key']['LanguageName'] in ('Korean(KR)','SFX')]
            if not chosen:
                print('NO SELECTED LANGUAGE', obj['Name'], [r['Key'] for r in language_rows])
            for lang in chosen:
                names.add(lang['Key']['LanguageName'])
                value = lang['Value']
                row = {'source_package': report['source'], 'name': obj['Name'], 'language': lang['Key'],
                       'cooked': value, 'metadata_file': report['target'],
                       'metadata_sha256': hashlib.sha256(Path(report['target']).read_bytes()).hexdigest(),
                       'duration_properties': {k:v for k,v in obj.items() if any(s in k.lower() for s in ('duration','infinite','attenuation'))}}
                events.append(row)
                for field, pathkey in (('SoundBanks','SoundBankPathName'),('Media','MediaPathName')):
                    for v in value.get(field, []):
                        matches = by_suffix.get(v[pathkey], [])
                        assert len(matches)==1,(v[pathkey],matches)
                        requests.add(matches[0])
                        names.add(v.get('DebugName',''))
    plan = {'events': events, 'gamesyncs': gamesyncs, 'aux_buses': aux,
            'raw_requests': sorted(requests), 'voice_language': 'Korean(KR)',
            'numeric_policy': 'Source bank levels/delays/pitches first; native spatial/reverb adaptation separately labeled.'}
    (OUT/'ResourcePlan.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    (EXTRACT/'RawRequests.json').write_text(json.dumps(sorted(requests), indent=2), encoding='utf-8')
    (OUT/'Tools/wwnames.txt').write_text('\n'.join(sorted(n for n in names if n))+'\n', encoding='utf-8')
    print('EVENTS', len(events), 'RAW FILES', len(requests), Counter(Path(p).suffix for p in requests),
          'RAW BY ARCHIVE', Counter(by_path[p]['archive'] for p in requests))
    print('GAME SYNCS',len(gamesyncs),'AUX',len(aux))
    for r in gamesyncs:
        text=json.dumps(r['export'])
        if any(v in text for v in ('vo_kz_switch-kz"','physical_material-pm_snow"','physical_material-pm_deepsnow"')):
            print('SWITCH',text[:1500])
    print('EVENT SAMPLE', json.dumps(events[0],ensure_ascii=False)[:2200] if events else None)

if __name__ == '__main__':
    main()
