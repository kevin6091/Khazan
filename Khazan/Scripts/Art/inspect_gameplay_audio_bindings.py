from pathlib import Path
from collections import Counter
import json
import xml.etree.ElementTree as ET
from prepare_gameplay_audio_scope import ROOT, OUT, EXTRACT, read

current = read(OUT/'CurrentAssets02/CurrentAssets.json')
print('CURRENT', current['success'], current['count'], Counter(r['type'] for r in current['assets']))
print('METADATA', [(r['asset'], list(r['metadata'])) for r in current['assets'] if r['metadata']][:4])
for rel in ('Saved/Extracted/DualAxeSword_20260916/AnimationImportManifest.json',
            'Metadata/GiantCombatFall_20261011/AuthoringPlan.json',
            'Metadata/CombatReaction_20261008/ReactionAuthoringPlan.json',
            'Metadata/MonsterVFX_20261008/ApesYetugaOriginal/Manifest.json'):
    if not (ROOT/rel).exists():
        print('MISSING MAP', rel)
        continue
    value = read(ROOT/rel)
    print('MAP', rel, json.dumps(value[:1] if isinstance(value,list) else
          {k: (v[:1] if isinstance(v,list) else v) for k,v in value.items()}, ensure_ascii=False)[:3600])
for name in ('Events01','Sources01'):
    values = read(EXTRACT/name/'MetadataExtractionReport.json')
    print('EXTRACTION', name, len(values), Counter(r.get('Status',r.get('status')) for r in values),
          [r for r in values if r.get('Status',r.get('status')) not in ('metadata','exported','success','ok')][:2])
events = list((EXTRACT/'Events01').rglob('*.json'))
sample = read(EXTRACT/'Events01/BBQ/Content/Art/Character/CHA_Data/FootPrint/FootPrintHuman.json')
print('FOOTPRINT', json.dumps(sample,ensure_ascii=False)[:3000])
data = read(OUT/'HeinMachAudioSourceActors.json')
for typ in ('xxAkSpatialAudioVolume','xxLevelVolumeComponent_SoundEvent'):
    for r in [r for r in data if r['export']['Type']==typ and r['export'].get('Properties')][:2]:
        print('ENV VOLUME', json.dumps(r['export'],ensure_ascii=False)[:2500])
tree = ET.ElementTree(ET.fromstring('<banks>'+ (OUT/'BankProbe01/Banks.xml').read_text(encoding='utf-8') + '</banks>'))
print('BANK XML', tree.getroot().tag, tree.getroot().attrib,
      [(e.tag,e.attrib) for e in list(tree.getroot())[:2]])
