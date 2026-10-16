"""Record observed tests, current protected files, and final numerical provenance."""
from pathlib import Path
import datetime
import hashlib
import json
import re

MAIN = Path(__file__).resolve().parents[2]
REPORT = MAIN / 'Metadata/PlayerParts_20261007/BodyCollisionTuning'
def read(name):
    return json.loads((REPORT / name).read_text(encoding='utf-8-sig'))
def write(name, data):
    (REPORT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()
observed = []
for filename, test in [('CollisionAuthor_SingleThin_Success.log', 'CollisionAuthor'),
                       ('PIE_SingleThinBodyContact.log', 'PIE'),
                       ('Guard_SingleThin_Success.log', 'PIE'),
                       ('Heal_SingleThin_Success.log', 'PIE')]:
    text = (REPORT / filename).read_text(encoding='utf-8-sig', errors='replace')
    assert 'Test Completed. Result={Success} Name={' + test + '}' in text, filename
    observed.append({'file': filename, 'completed_successfully': True})
stock = read('Stock_RuntimeReadback.json')
assert stock['tested_saved_package_count'] == 7
assert set(stock['secondary_pose_summary']) == {'Torso', 'Leg', 'Hair'}
mass_lines = [line for line in (REPORT / 'CollisionAuthor_SingleThin_Success.log').read_text(encoding='utf-8-sig').splitlines() if 'CalculatedMass part=' in line]
assert len(mass_lines) == 52
write('CalculatedMassInertia.json', {'source_kind': 'Current imported asset + engine calculation, not original-game metadata',
    'source_package_template': '/Game/_Art/Player/Character/Meshs/{Part}/Player_Original_{Part}_PhysicsAsset',
    'input_fields': ['SkeletalBodySetups[bone].AggGeom', 'DefaultInstance', 'PhysicalMaterial density/raise-to-power'],
    'calculation': 'Engine MakeDynamicActorSetup(unit transform); preserve mass and CoM. Invert ScaleInertia(true) using body-axis second moments: q_i=(trace(I_old)/2-I_old,i)/(trace(I_thin)/2-I_thin,i); detS=(qX*qY*qZ)^(1/5); S_i=sqrt(q_i/detS).',
    'units': {'mass': 'kg', 'inertia': 'kg cm^2', 'center_of_mass': 'cm', 'inertia_tensor_scale': 'dimensionless spatial scale'},
    'verified_bodies': 52, 'mass_relative_tolerance': .0001, 'inertia_diagonal_relative_tolerance': .001,
    'center_of_mass_tolerance_cm': .001, 'full_off_diagonal_tensor_preservation_verified': False,
    'observed_values': mass_lines})
provenance = read('TuningProvenance.json')
provenance['reason'] = 'Slight extra velocity damping. One thin physical capsule per simulated body, avoiding thick fitted garment collision. Calculated mass/CoM/body-axis inertia diagonals retained.'
provenance['rejected_design'] = 'Original mass-only/NoCollision shapes were still re-enabled by ImmediatePhysicsActorHandle CreateParticleHandle; logs and screenshots retained.'
provenance['engine_sources'].append('Engine/Source/Runtime/Engine/Private/PhysicsEngine/ImmediatePhysics/ImmediatePhysicsChaos/ImmediatePhysicsActorHandle_Chaos.cpp: CreateParticleHandle')
provenance['verified'] = ['18 current-pose anatomical colliders per part', 'Actual contact manifolds and impulses in all three simulations', '52 single thin shapes and calculated mass/CoM/inertia-diagonal checks', 'Rendered idle/movement/back view', 'Guard/Heal regression', 'Current-main stock DLL saved/runtime reload']
provenance['verification_pending'] = ['Main integration and fresh load', 'Original-game physics parity', 'All skinned vertices/every combat pose/long-duration hardware QA']
write('TuningProvenance.json', provenance)
native = (REPORT / 'PIE_SingleThinBodyContact.log').read_text(encoding='utf-8-sig')
contacts = re.findall(r'ActualBodyContacts part=(\w+) manifoldPoints=(\d+) accumulatedImpulse=([\d.]+)', native)
assert len(contacts) == 3 and all(int(points) > 0 and float(impulse) > 0 for _, points, impulse in contacts)
write('Verification.json', {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'isolated_native_pie_passed': True, 'stock_saved_reload_passed': True, 'guard_passed': True, 'heal_passed': True,
    'observed_logs': observed, 'actual_contacts': contacts, 'stock_binary': read('StockBinary.json'),
    'stock_runtime': 'Stock_RuntimeReadback.json', 'screenshots': ['Thin_Idle.png', 'Thin_Moving.png', 'Stock_Back.png'],
    'runtime_cpp_changes': 0, 'main_integration_complete': False})
paths = [p for folder in ('Source', 'Config') for p in (MAIN / folder).rglob('*') if p.is_file()]
module = json.loads((MAIN / 'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))['Modules']['Khazan']
paths += [MAIN / 'Khazan.uproject', MAIN / 'Content/Maps/DevMap.umap',
          MAIN / 'Content/_Art/Player/Character/Bluprints/ABP_Player.uasset',
          MAIN / 'Content/_Art/Player/Character/Meshs/Player_PhysicsAsset.uasset',
          MAIN / 'Binaries/Win64/UnrealEditor.modules', MAIN / 'Binaries/Win64' / module]
assert digest(MAIN / 'Binaries/Win64' / module) == read('StockBinary.json')['mainSha']
targets = {entry['path'] for entry in read('CandidateManifest.json')['packages']}
paths += [p for p in (MAIN / 'Content/_Art/Player/Character').rglob('*') if p.is_file() and p.relative_to(MAIN).as_posix() not in targets]
unique = {p.relative_to(MAIN).as_posix(): p for p in paths}
write('IntegrationProtectedBefore.json', [{'path': rel, 'sha256': digest(p)} for rel, p in sorted(unique.items())])
print('Recorded native/stock success, 52 mass calculations, and', len(unique), 'protected current-main files. Main assets unchanged.')
