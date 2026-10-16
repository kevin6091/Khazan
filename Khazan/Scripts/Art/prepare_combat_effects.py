"""Targeted FModel/CUE4Parse dependency extraction with package-path provenance."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import os
import re
import shutil
import math
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EXTRACT = ROOT / 'Saved/Extracted/CombatEffects_20261006'
SOURCE = EXTRACT / 'Source'
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
PROVIDER = ROOT / 'Scripts/Enemies/EnemyExtractor/bin/Release/net10.0/EnemyExtractor.exe'


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def references(value, field=''):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from references(item, field + '.' + key)
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from references(item, field + '[' + str(i) + ']')
    elif isinstance(value, str):
        text = value
        if text.startswith('/Game/'):
            text = 'BBQ/Content/' + text[6:]
        if text.startswith(('BBQ/Content/', 'BBQ/Plugins/', 'Engine/Content/')):
            yield field, text.split('.')[0].removesuffix('.uasset')


def typed_visual_references(value):
    if isinstance(value, dict):
        if 'ObjectPath' in value and value.get('ObjectName', '').startswith(('Material', 'Texture', 'StaticMesh', 'VectorField', 'Curve', 'ParticleSystem', 'NiagaraSystem')):
            yield value['ObjectPath'].split('.')[0]
        for item in value.values():
            yield from typed_visual_references(item)
    elif isinstance(value, list):
        for item in value:
            yield from typed_visual_references(item)


def provider(mode, packages, label, output):
    request = EXTRACT / (label + '_Requests.json')
    write(request, sorted(set(packages)))
    with (EXTRACT / (label + '.log')).open('w', encoding='utf-8') as log:
        result = subprocess.run([str(PROVIDER), mode, str(output), str(request)],
                                stdout=log, stderr=subprocess.STDOUT,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(f'{label}: extractor exit {result.returncode}; see {label}.log')
    if mode == 'metadata':
        failures = [r for r in read(output / 'MetadataExtractionReport.json') if r['status'] != 'ok']
        if failures:
            write(META / (label + '_Failures.json'), failures)
            raise RuntimeError(f'{label}: {len(failures)} failed packages')
    print(label, len(packages), flush=True)


def category(package):
    low = package.lower()
    if '/pc/dualaxesword/' in low:
        return 'DualAxeSword/' + ('Flow' if '/flow/' in low else 'Yaksha' if '/yaksha/' in low else 'Core')
    if '/status/enchant/dualaxesword/' in low:
        return 'DualAxeSword/Enchant'
    if '/pp_attack/' in low:
        return 'Combat/' + ('GuardParry' if any(t in low for t in ('guard', 'parry', 'counter')) else 'AttackContact')
    if '/pp_damage/' in low or '/physics/blood/' in low:
        return 'Combat/' + ('Blood' if 'blood' in low else 'HitReaction')
    if '/pp_world/' in low:
        return 'Movement/' + ('DeepSnow' if 'deepsnow' in low else 'IceSnow' if 'icesnow' in low else 'Snow' if 'snow' in low else 'Grass' if 'grass' in low else 'Dust') + '/' + ('Player' if '_pc_' in low else 'Monsters')
    if '/monster/' in low:
        parts = package.split('/Monster/')[1].split('/')
        monster = parts[1] if parts[0] == 'BBQ_Monster' else parts[0]
        return 'Movement/Monsters/' + monster
    return 'Combat/Shared'


def main():
    EXTRACT.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    roots = read(EXTRACT / 'RootRequests.json')
    previous_destinations = {r['source_package']: r['destination'] for r in read(META / 'AssetManifest.json')} if (META / 'AssetManifest.json').exists() else {}
    write(EXTRACT / 'RootRequests.json', roots)
    queue = set(roots)
    visited = set()
    edges = []
    wave = 0
    while queue:
        batch = sorted(queue - visited)
        if not batch:
            break
        missing = [p for p in batch if not (SOURCE / (p + '.json')).is_file()]
        if missing:
            provider('metadata', missing, f'Closure_{wave:02d}', SOURCE)
        next_queue = set()
        for package in batch:
            data = read(SOURCE / (package + '.json'))
            visited.add(package)
            for obj in data:
                typed_dependencies = set(typed_visual_references(obj))
                for field, dependency in references(obj):
                    if dependency != package:
                        edges.append({'source': package, 'object': obj['Name'], 'field': field, 'target': dependency})
                        # Follow visual assets; gameplay, source skeletons and animation
                        # remain metadata references and are not reimported.
                        if dependency in typed_dependencies or '/Art/VFX/' in dependency or '/Art/Character/CHA_Texture/' in dependency or '/Art/Character/CHA_Material/' in dependency or '/CommonTexture/' in dependency or '/Pay_Asset/' in dependency or '/BaseMaterials/' in dependency or dependency.startswith(('Engine/Content/', 'BBQ/Plugins/')):
                            next_queue.add(dependency)
        queue = next_queue - visited
        print('closure', wave, 'visited', len(visited), 'next', len(queue), flush=True)
        wave += 1
    assets = []
    counters = Counter()
    names = Counter()
    for package in sorted(visited):
        file = SOURCE / (package + '.json')
        data = read(file)
        root = next((o for o in data if o.get('Name') == package.split('/')[-1]), data[-1])
        typ = root['Type']
        counters[typ] += 1
        name = package.split('/')[-1]
        if typ in ('ParticleSystem', 'NiagaraSystem'):
            folder = category(package)
        elif typ in ('Texture2D', 'TextureCube', 'VolumeTexture'):
            folder = 'Shared/Textures/' + ('/'.join(package.split('/VFX_Texture/')[1].split('/')[:-1]) if '/VFX_Texture/' in package else 'External')
        elif typ in ('StaticMesh', 'SkeletalMesh'):
            folder = 'Shared/Meshes/' + ('/'.join(package.split('/VFX_Mesh/')[1].split('/')[:-1]) if '/VFX_Mesh/' in package else 'Other')
        elif typ in ('Material', 'MaterialInstanceConstant'):
            folder = 'Shared/Materials/' + ('/'.join(package.split('/VFX_Material/')[1].split('/')[:-1]) if '/VFX_Material/' in package else 'Other')
        elif typ == 'VectorFieldStatic':
            folder = 'Shared/VectorFields'
        else:
            folder = 'Shared/Data'
        target = '/Game/_Art/Effects/' + folder.strip('/') + '/' + name
        names[target.lower()] += 1
        assets.append({'source_package': package, 'source_type': typ, 'name': name,
                       'source_json': str(file.relative_to(ROOT)).replace('\\', '/'),
                       'source_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
                       'destination': target, 'is_requested_root': package in roots})
    for row in assets:
        if row['source_package'] in previous_destinations:
            row['destination'] = previous_destinations[row['source_package']]
        elif names[row['destination'].lower()] > 1:
            row['destination'] += '_' + hashlib.sha256(row['source_package'].encode()).hexdigest()[:8]
    assert len({r['destination'].lower() for r in assets}) == len(assets), 'Destination collision; preserve existing paths before importing'
    write(META / 'AssetManifest.json', assets)
    write(META / 'DependencyEdges.json', edges)
    write(META / 'ExtractionSummary.json', {'root_packages': len(roots), 'closure_packages': len(visited),
          'source_types': dict(counters), 'provider': 'Existing FModel settings + CUE4Parse 1.2.2.202609',
          'original_engine_contract': 'GAME_UE4_27, DesktopMobile', 'game_display_build': 'unverified',
          'scope': 'DAS combat; shared attack/damage/blood; player/monster snow/grass/default contact; Yetuga/Apes contact',
          'excluded': 'cinematics, other PC weapons and unrelated monster abilities'})
    raw = [r['source_package'] for r in assets]
    export = [r['source_package'] for r in assets if r['source_type'] in ('Texture2D', 'TextureCube', 'VolumeTexture', 'StaticMesh', 'SkeletalMesh')]
    if '--payload' in sys.argv:
        provider('raw', raw, 'OriginalRaw', EXTRACT / 'OriginalRaw')
        provider('export', export, 'Payload', EXTRACT / 'Payload')
    if '--vectors' in sys.argv:
        vectors = []
        for row in assets:
            if row['source_type'] != 'VectorFieldStatic':
                continue
            props = next(o for o in read(SOURCE / (row['source_package'] + '.json')) if o['Type'] == 'VectorFieldStatic')['Properties']
            size = [props[n] for n in ('SizeX', 'SizeY', 'SizeZ')]
            raw_path = EXTRACT / 'OriginalRaw' / row['source_package']
            uasset = raw_path.with_suffix('.uasset').read_bytes()
            uexp = raw_path.with_suffix('.uexp').read_bytes()
            expected = math.prod(size) * 8
            assert uexp[-4:] == struct.pack('<I', 0x9e2a83c1)
            offset = len(uexp) - 4 - expected
            flags, count, disk, absolute = struct.unpack_from('<IIIq', uexp, offset - 20)
            assert count == disk == expected and flags == 0x48 and absolute == len(uasset) + offset
            samples = list(struct.iter_unpack('<eeee', uexp[offset:offset + expected]))
            assert all(math.isfinite(v) for s in samples for v in s) and all(s[3] == 0 for s in samples)
            bounds = props['Bounds']
            lines = [','.join(map(str, size)), ','.join(str(bounds['Min'][c]) for c in 'XYZ'), ','.join(str(bounds['Max'][c]) for c in 'XYZ')]
            lines += [','.join(format(v, '.9g') for v in s[:3]) for s in samples]
            target = EXTRACT / 'VectorFields' / (row['name'] + '.fga')
            target.parent.mkdir(exist_ok=True)
            target.write_text(',\n'.join(lines) + ',\n', encoding='ascii')
            vectors.append({'source_package': row['source_package'], 'dimensions': size, 'bounds_cm': bounds,
                            'samples': len(samples), 'uexp_payload_offset': offset, 'bulk_flags': flags,
                            'fga_sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                            'conversion': 'Exact-order FFloat16Color RGB to FGA XYZ; alpha verified zero; no scale or sign change.'})
        write(META / 'VectorFieldExtraction.json', vectors)
        print('Exact vector fields', len(vectors), flush=True)
    shutil.copytree(SOURCE, META / 'Source', dirs_exist_ok=True)
    print(json.dumps({'roots': len(roots), 'packages': len(visited), 'types': dict(counters),
                      'raw_packages': len(raw), 'payload_packages': len(export)}, indent=2), flush=True)


if __name__ == '__main__':
    main()
