"""Preserve tiny RGBA16F cubemaps in a DDS container; no resampling or HDR conversion."""
from pathlib import Path
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Saved/Extracted/CombatEffects_20261006'
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
report = []
for row in json.loads((META / 'AssetManifest.json').read_text(encoding='utf-8')):
    if row['source_type'] != 'TextureCube':
        continue
    source = next(x for x in json.loads((ROOT / row['source_json']).read_text(encoding='utf-8-sig')) if x['Type'] == 'TextureCube')
    if source['PixelFormat'] != 'PF_FloatRGBA':
        continue
    mip = source['Mips'][0]
    w, h = mip['SizeX'], mip['SizeY']
    count = w * h * 8 * 6
    assert count == mip['BulkData']['ElementCount']
    raw = (BASE / 'OriginalRaw' / (row['source_package'] + '.uexp')).read_bytes()
    signature = struct.pack('<III', 0x48, count, count)
    hits = [i + 20 for i in range(len(raw)) if raw.startswith(signature, i)
            and raw[i + 20 + count:i + 20 + count + 12] == struct.pack('<III', w, h, 1)]
    assert len(hits) == 1, hits
    pixels = raw[hits[0]:hits[0] + count]
    # DDS_HEADER / legacy D3DFMT_A16B16G16R16F (FourCC 113) is decoded by
    # UE ImageCore DDSFile.cpp as R16G16B16A16_FLOAT. All six cubemap faces
    # stay in original order. Source original mips also remain in OriginalRaw.
    header = [124, 0x100f, h, w, w * 8, 0, 1] + [0] * 11
    header += [32, 4, 113, 0, 0, 0, 0, 0]
    header += [0x1008, 0xfe00, 0, 0, 0]
    assert len(header) == 31
    path = BASE / 'Precision' / (row['name'] + '.dds')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'DDS ' + struct.pack('<31I', *header) + pixels)
    assert path.read_bytes()[128:] == pixels
    report.append({'source_package': row['source_package'], 'path': str(path.relative_to(ROOT)).replace('\\', '/'),
                   'face_dimensions': [w, h], 'faces': 6, 'bulk_offset_in_uexp': hits[0],
                   'rgba16f_faces_sha256': hashlib.sha256(pixels).hexdigest(),
                   'dds_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                   'conversion': 'Original six-face RGBA16F bits in DDS; no tone mapping, alpha loss or resampling.'})
(META / 'PrecisionCubeExtraction.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('Exact RGBA16F cubes:', len(report))
