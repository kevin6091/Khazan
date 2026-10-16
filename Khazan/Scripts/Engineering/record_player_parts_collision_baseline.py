"""Read-only source/asset baseline for the isolated body collision follow-up."""
from pathlib import Path
import datetime
import hashlib
import json

MAIN = Path(__file__).resolve().parents[2]
WORK = MAIN.parents[1] / 'Khazan_PlayerPartsWork_20261007' / 'Khazan'
REPORT = MAIN / 'Metadata/PlayerParts_20261007/BodyCollisionTuning'
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def write(name, data):
    (REPORT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

raw = json.loads((REPORT / 'BeforeManifest.json').read_text(encoding='utf-8-sig'))
before = []
for entry in raw:
    before.extend(entry['value'] if 'value' in entry else [entry])
assert len(before) == 7 and len({x['path'] for x in before}) == 7
for entry in before:
    assert digest(MAIN / entry['path']) == entry['beforeSha256'], entry['path']
    assert digest(WORK / entry['path']) == entry['beforeSha256'], entry['path']
    assert digest(REPORT / 'Before' / entry['path']) == entry['beforeSha256'], entry['path']
write('BeforeManifest.json', before)

protected = json.loads((REPORT.parent / 'MainIntegrationProtectedBefore.json').read_text(encoding='utf-8-sig'))
current = [{'path': p['Path'].replace('\\', '/'), 'sha256': digest(MAIN / p['Path'])} for p in protected]
write('ProtectedBefore.json', current)
write('TuningProvenance.json', {
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'original_game_physics_values_verified': False,
    'search_scope': [
        'Engineering saved physics diagnostics and Player parts canonical document',
        'Project Metadata/Saved extracted player animation and gameplay metadata',
        'C:/Users/user/Desktop/카잔/BBQ/Content/_Kazan_/Art/Character/CHA_Model/PC/Kazan/Model',
        'C:/Users/user/Desktop/카잔/Exports (player physics exports not found)'],
    'finding': 'Player PSK and animation metadata exist; Player PhysicsAsset/cloth damping metadata not located in inspected saved extracts. Imported Original names do not establish original-game physics settings.',
    'temporary_tuning': {
        'linear_damping': {'before': .01, 'after': .05, 'unit': 's^-1'},
        'angular_damping': {'before': 0, 'after': .35, 'unit': 's^-1'},
        'cloth_contact_radius': {'after': 1., 'unit': 'cm'},
        'hair_contact_radius': {'after': .75, 'unit': 'cm'}},
    'reason': 'Slight velocity decay; thin contact geometry for broad auto-fit garment capsules. Preserve original mass shapes and joint limits/drives.',
    'engine_sources': [
        'Engine/Source/Runtime/AnimGraphRuntime/Private/BoneControllers/AnimNode_RigidBody.cpp: CollectClothColliderObjects, UpdateClothColliderObjects',
        'Engine/Source/Runtime/Engine/Classes/Components/SkeletalMeshComponent.h: AddClothCollisionSource',
        'Engine/Source/Runtime/Experimental/Chaos/Private/Chaos/MassProperties.cpp: CalculateMassPropertiesOfImplicitUnion'],
    'verification_pending': ['Actual contacts/impulses', '18 body collider pose and size', 'Runtime mass comparison', 'Rendered movement', 'Stock saved reload', 'Main integration']})
print('Validated seven before/backup/work hashes; recorded protected files and temporary tuning provenance.')
