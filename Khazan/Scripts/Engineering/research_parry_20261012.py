"""Target stored original JustGuard contracts; no game-wide extraction."""
from pathlib import Path
import hashlib, json
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Metadata/Parry_20261012'
OUT.mkdir(exist_ok=True)
G = ROOT / 'Saved/Extracted/InGame_Playback_20261002/Metadata/BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/Guard'
R = {'animation': [], 'routing': [], 'effect_assets': []}
for name in ['AC_Kazan_DualAxeSword_Com_Guard_Start', 'AC_Kazan_DualAxeSword_Com_Guard_Normal_Start',
             'AC_Kazan_DualAxeSword_Com_Guard_Suc_Just_L', 'AC_Kazan_DualAxeSword_Com_Guard_Suc_Just_R']:
    p = G / (name + '.json'); data = json.loads(p.read_text(encoding='utf-8-sig'))
    props = data[0]['Properties']; row = {'file': p.relative_to(ROOT).as_posix(), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
         'track': props.get('AnimationTrack'), 'curves': props.get('RawCurveData'), 'notifies': []}
    for i, n in enumerate(props.get('Notifies', [])):
        ref = n.get('NotifyStateClass') or n.get('Notify') or {}
        obj = next((e for e in data if e['Name'] == ref.get('ObjectName', '').split(':')[-1].rstrip("'")), {})
        op = obj.get('Properties', {})
        if n['NotifyName'] in ['xxSkillAction','xxEnableCancelSK','xxAkEvent','xxCanMove','xxParticle']:
            row['notifies'].append({'index': i, 'name': n['NotifyName'], 'start': n['LinkValue'], 'duration': n.get('Duration', 0),
                                   'properties': {k:v for k,v in op.items() if k != 'BakedSpawnTransforms'}})
    R['animation'].append(row)
M = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
rows = json.loads((M / 'AssetManifest.json').read_text())
effect = next(r for r in rows if r['name'] == 'PP_AtkEx_JustGuard')
p = ROOT / effect['source_json']; data = json.loads(p.read_text(encoding='utf-8-sig'))
R['effect_assets'] = [effect]
R['effect_structure'] = [{'name': x['Name'], 'type':x['Type'], 'properties': x.get('Properties',{})} for x in data
                         if x['Type'] in ['ParticleSystem','ParticleModuleRequired','ParticleModuleMeshMaterial','ParticleModuleTypeDataMesh']]
routes = json.loads((M / 'EffectRoutingContracts.json').read_text())
R['routing'] = [r for r in routes if 'PP_Damage_Spray' in str(r.get('source_package','')) and 'NewJustGuard' in json.dumps(r)]
R['guard_skill'] = json.loads((ROOT/'Metadata/GuardImplementation_20261002/OriginalTimingEvidence.json').read_text())['guard_skill_info']
(OUT/'OriginalEvidence.json').write_text(json.dumps(R,ensure_ascii=False,indent=2),encoding='utf-8')
for r in R['animation']:
    print(Path(r['file']).stem, json.dumps(r['track']), 'curves', json.dumps(r['curves']))
    for n in r['notifies']:
        if n['name'] != 'xxParticle': print(n['index'], n['name'], n['start'], n['duration'], n['properties'])
print('Effect structure:', json.dumps(R['effect_structure'],ensure_ascii=False))
print('Routes:', json.dumps(R['routing'],ensure_ascii=False))
