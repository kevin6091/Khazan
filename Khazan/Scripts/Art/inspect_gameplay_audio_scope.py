"""Read existing timing/source manifests before targeted audio extraction."""
from pathlib import Path
from collections import Counter
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Saved/ImportReports/GameplayAudio_20261011'

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def shape(value):
    if isinstance(value, dict):
        return {k: (f'list:{len(v)}' if isinstance(v, list) else
                    f'dict:{len(v)}' if isinstance(v, dict) else v)
                for k, v in list(value.items())[:30]}
    return {'count': len(value), 'sample': value[:1]}

def main():
    files = [
        'Saved/ImportReports/PlayerAttackVFX_20261008/MetadataAudit/CurrentSegmentTimingPlan.json',
        'Saved/ImportReports/PlayerAttackVFX_20261008/MetadataAudit/OriginalSourceTimingContracts.json',
        'Metadata/MonsterVFX_20261008/HumanOriginal/CurrentHumanClipMap.json',
        'Metadata/MonsterVFX_20261008/HumanOriginal/OriginalHumanVFXManifest.json',
        'Metadata/MonsterVFX_20261008/ApesYetugaOriginal/Manifest.json',
        'Metadata/CombatReaction_20261008/AnimationClassification.json',
        'Saved/ImportReports/HeinMachCleanPresentation_20261011/MonsterAnimationAudit02/UsedAnimations.json',
    ]
    summary = {}
    for rel in files:
        p = ROOT / rel
        summary[rel] = shape(read(p)) if p.exists() else 'missing'
    level = Path.home() / 'Desktop' / '\uce74\uc794' / 'Exports/BBQ/Content/_Kazan_/Level/HeinMach'
    audio = []
    types = Counter()
    for p in level.glob('*.json'):
        if p.stem.endswith('BuiltData'):
            continue
        data = read(p)
        for i, obj in enumerate(data):
            typ = obj.get('Type', '')
            types[typ] += 1
            text = json.dumps(obj, ensure_ascii=False)
            if any(x in typ.lower() for x in ('sound', 'audio', 'akambient', 'reverb')) or 'AkAudioEvent' in text:
                audio.append({'file': str(p), 'index': i, 'export': obj})
    (OUT / 'HeinMachAudioSourceActors.json').write_text(json.dumps(audio, ensure_ascii=False, indent=2), encoding='utf-8')
    summary['heinmach'] = {'source_folder': str(level), 'files': len(list(level.glob('*.json'))),
                           'audio_rows': len(audio), 'audio_types': dict(Counter(r['export'].get('Type') for r in audio))}
    (OUT / 'ScopeInspection.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    for k, v in summary.items():
        print(k, json.dumps(v, ensure_ascii=False)[:4200])
    contracts = read(ROOT / files[1])
    key, sample = next(iter(contracts.items()))
    print('PLAYER CONTRACT', key, json.dumps(sample)[:3300])
    human = read(ROOT / files[3])['clips']
    print('HUMAN SOURCE TIMING', json.dumps(human[0])[:2700])
    apes = read(ROOT / files[4])
    print('APES CLIP', json.dumps(apes['clips'][0])[:2000])
    print('APES INPUTS', json.dumps(apes['inputs'])[:1900])
    print('REACTION PLAYER', json.dumps(read(ROOT / files[5])['player'])[:2400])
    for typ in ('AkAmbientSound', 'AkComponent', 'xxLevelVolumeComponent_SoundEvent',
                'AkLateReverbComponent', 'HeinMach_Sound_C', 'BP_InnerSound_C'):
        sample = next((r for r in audio if r['export'].get('Type') == typ), None)
        print('ENV SAMPLE', typ, json.dumps(sample, ensure_ascii=False)[:2800])

if __name__ == '__main__':
    main()
