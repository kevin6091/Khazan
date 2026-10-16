"""Source notify/event closure. Cached source first; no asset/runtime writes."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/ImportReports/GameplayAudio_20261011'
EXTRACT = ROOT / 'Saved/Extracted/GameplayAudio_20261011'
CACHE = Path.home() / 'Desktop' / '\uce74\uc794' / 'Exports'

def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))

def package(ref):
    value = (ref or {}).get('ObjectPath', (ref or {}).get('AssetPathName', ''))
    if value.startswith('/Game/'):
        value = 'BBQ/Content/' + value[6:]
    return re.sub(r'\.[^/]+$', '', value)

def refs(value, field=''):
    if isinstance(value, dict):
        if 'AkAudioEvent' in value.get('ObjectName', '') or ('AssetPathName' in value and
                any(x in value['AssetPathName'] for x in ('/Sound/', '/WwiseAudio/'))):
            yield field, package(value)
        for k, v in value.items():
            yield from refs(v, field + '.' + k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            yield from refs(v, field + f'[{i}]')

class SourceCache:
    def __init__(self):
        self.roots = [EXTRACT/'Sources03',EXTRACT/'Sources02',EXTRACT/'Sources01',EXTRACT/'Supplement01',
            ROOT/'Metadata/MonsterVFX_20261008/HumanOriginal/Source',
            ROOT/'Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/Source',
            ROOT/'Content/_Art/Effects/Metadata/Extraction_20261006/Bindings/Source',
            ROOT/'Saved/Extracted/CombatEffects_20261006/BindingSource',
            ROOT/'Saved/Extracted/CombatEffects_20261006/Source',
            CACHE]
        apes = read(ROOT/'Metadata/MonsterVFX_20261008/ApesYetugaOriginal/Manifest.json')
        self.zips = [(p, zipfile.ZipFile(ROOT/p)) for p in apes['inputs']['source_zips']]
        self.explicit = {}
        self.memory = {}
        self.missing = set()
        for rel in ('Saved/ImportReports/PlayerAttackVFX_20261008/MetadataAudit/OriginalSourceTimingContracts.json',
                    'Metadata/MonsterVFX_20261008/HumanOriginal/OriginalSourceTimingContracts.json'):
            for p, row in read(ROOT/rel).items():
                if row.get('source_file'):
                    self.explicit[p] = ROOT/row['source_file']

    def get(self, p):
        if p in self.memory:
            return self.memory[p]
        candidates = ([self.explicit[p]] if p in self.explicit else []) + [r/(p+'.json') for r in self.roots]
        for f in candidates:
            if f.exists():
                raw = f.read_bytes()
                result = (json.loads(raw.decode('utf-8-sig')), {'file': str(f), 'sha256': hashlib.sha256(raw).hexdigest()})
                self.memory[p] = result
                return result
        for rel, z in self.zips:
            names = [p+'.json', 'Source/'+p+'.json']
            for name in names:
                if name in z.namelist():
                    raw = z.read(name)
                    result = (json.loads(raw.decode('utf-8-sig')), {'zip': rel, 'entry': name,
                              'sha256': hashlib.sha256(raw).hexdigest()})
                    self.memory[p] = result
                    return result
        self.missing.add(p)
        return None

def main():
    cache = SourceCache()
    human = read(ROOT/'Metadata/MonsterVFX_20261008/HumanOriginal/OriginalHumanVFXManifest.json')['clips']
    apes = read(ROOT/'Metadata/MonsterVFX_20261008/ApesYetugaOriginal/Manifest.json')
    player_segments = read(ROOT/'Saved/ImportReports/PlayerAttackVFX_20261008/MetadataAudit/CurrentSegmentTimingPlan.json')
    sources = {c['OriginalPackage'] for c in human}
    sources |= {c.get('OriginalPackage', c.get('original_package')) for c in apes['clips']}
    sources |= {c['OriginalPackage'] for c in player_segments if c.get('OriginalPackage')}
    # Current player import metadata is the authoritative source mapping, including
    # fall/heal/dodge/reaction/locomotion changes made after the attack audit.
    currentfile = OUT/'CurrentAssets02/CurrentAssets.json'
    if currentfile.exists() and read(currentfile).get('success'):
        current = read(currentfile)['assets']
        for c in current:
            for key, value in c.get('metadata', {}).items():
                try:
                    obj = json.loads(value)
                except (ValueError, TypeError):
                    obj = None
                if isinstance(obj, dict) and isinstance(obj.get('source'), str) and obj['source'].startswith('BBQ/'):
                    sources.add(obj['source'])
                if isinstance(value, str) and value.startswith('BBQ/'):
                    sources.add(value)
    sources.discard(None)
    found = []
    types = Counter()
    events = set()
    seen = set()

    def visit(p):
        if p in seen:
            return
        seen.add(p)
        result = cache.get(p)
        if not result:
            return
        exports, proof = result
        for i, obj in enumerate(exports):
            typ = obj.get('Type', '')
            prop = obj.get('Properties', {})
            if 'Notify' in typ and any(w in typ.lower() for w in ('sound', 'audio', 'ak', 'footstep')):
                types[typ] += 1
                found.append({'package': p, 'index': i, 'export': obj, 'proof': proof})
                events.update(v for _, v in refs(obj))
            for segment in prop.get('AnimationTrack', {}).get('AnimSegments', []):
                child = package(segment.get('AnimReference'))
                if child:
                    visit(child)
    for p in sorted(sources):
        visit(p)
    env = read(OUT/'HeinMachAudioSourceActors.json')
    env_events = {p for r in env for _, p in refs(r['export'])}
    events |= env_events
    index = read(EXTRACT/'Index03/AudioPackageIndex.json')
    # Inspect both chunk1 audio exports even when not part of current characters.
    chunk1 = {r['path'][:-7] for r in index if r['path'].endswith('.uasset') and 'chunk1-' in r['archive']}
    requests = events | chunk1
    requests.add('BBQ/Content/Art/Character/CHA_Data/FootPrint/FootPrintHuman')
    # Names and exact IDs restore original surface/character switch selection.
    gamesync = {r['path'][:-7] for r in index if r['path'].endswith('.uasset') and
                ('/GameSync/' in r['path'] or '/Master-Mixer_Hierarchy/' in r['path'])}
    requests |= gamesync
    (OUT/'OriginalAudioNotifyExports.json').write_text(json.dumps(found, ensure_ascii=False, indent=2), encoding='utf-8')
    (EXTRACT/'EventMetadataRequests.json').write_text(json.dumps(sorted(requests), indent=2), encoding='utf-8')
    (EXTRACT/'SourceMetadataRequests.json').write_text(json.dumps(sorted(cache.missing), indent=2), encoding='utf-8')
    result = {'source_packages': len(sources), 'visited_packages': len(seen), 'source_missing': sorted(cache.missing),
              'notify_exports': len(found), 'types': dict(types), 'event_packages': len(events),
              'heinmach_event_packages': sorted(env_events), 'chunk1_checked_packages': sorted(chunk1)}
    (OUT/'SourceScope.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Source scope', {k:v for k,v in result.items() if isinstance(v, (int, dict))})
    print('Missing source examples', sorted(cache.missing)[:8])
    for typ in types:
        example = next(r for r in found if r['export']['Type']==typ)
        print('NOTIFY', typ, json.dumps(example['export'], ensure_ascii=False)[:1800])
    print('HeinMach events', [p.rsplit('/',1)[-1] for p in sorted(env_events)])

if __name__ == '__main__':
    main()
