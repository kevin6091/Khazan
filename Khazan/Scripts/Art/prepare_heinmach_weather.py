"""Targeted cached-source discovery; never prints FModel settings or keys."""
from pathlib import Path
import json
import hashlib

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path.home() / 'Desktop' / '\uce74\uc794' / 'Exports'
OUT = ROOT / 'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006'
EXTRACT = ROOT / 'Saved/Extracted/HeinMachWeather_20261006'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def walk(value, field=''):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk(item, field + '.' + key)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from walk(item, field + '[' + str(i) + ']')
    elif isinstance(value, str):
        yield field, value


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = read(ROOT / 'Content/_Art/Player/Environment/Rendering/Metadata/LookRestoration_20261002/SourceManifest.json')
    summary = {}
    for key, profile in manifest['HeinMach'].items():
        d = profile['default_properties']
        pp = d.get('Settings', {})
        summary[key] = {'package': profile['source_package'],
                        'weather_references': {k:v for k,v in d.items() if any(s in k.lower() for s in ('sky','cloud','snow','particle','weather'))},
                        'active_PP': {k:v for k,v in pp.items() if pp.get('bOverride_' + k) is True},
                        'inactive_PP_serialized': {k:v for k,v in pp.items() if pp.get('bOverride_' + k) is False}}
    scene = {}
    hits = []
    for path in (SOURCE / 'BBQ/Content/_Kazan_/Level/HeinMach').glob('*.json'):
        if path.stem.endswith('BuiltData') or 'Cine' in path.stem:
            continue
        data = read(path)
        for i, obj in enumerate(data):
            if any(s in obj.get('Type', '').lower() for s in ('environmentsky', 'envsky', 'environmentproxy', 'envcloud')):
                scene[path.name + ':' + str(i)] = obj
            for field, text in walk(obj):
                low = text.lower()
                if ('snow' in low or 'blizzard' in low) and ('ObjectPath' in field or field == '.Name' or field == '.Type') and ('vfx' in low or any(s in obj.get('Type','').lower() for s in ('particle', 'envsnow', 'weather', 'snow'))):
                    hits.append({'file': str(path), 'export_index':i, 'object': obj.get('Name'), 'type':obj.get('Type'), 'field':field, 'value':text})
    index_path = EXTRACT / 'Index/TargetedPackageIndex.json'
    candidates = [p for p in read(index_path) if any(s in p.lower() for s in ('vfx','art/ artrendering','ar_weather','ar_data/snow','skybox','was_sky'))]
    result = {'profiles':summary, 'source_environment_scene':scene, 'level_weather_references':hits, 'targeted_provider_candidates':candidates}
    (OUT / 'SourceDiscovery.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'source_env':[{ 'key':k,'type':v['Type'],'name':v['Name']} for k,v in scene.items()],
                      'weather_level_refs': sorted(set(x['value'] for x in hits if 'ObjectPath' in x['field'])),
                      'provider_weather_candidates':[p for p in candidates if '/Environment/' in p or '/AR_' in p or '/UI/' in p or '/World/FP_' in p]}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
