"""Lossless half-float texture recovery from original inline UE4 texture bulk.

Radiance HDR export loses alpha and quantizes float data. Store RGBA half bits
unchanged in uncompressed OpenEXR scanlines. File layout: openexr.com docs.
"""
from pathlib import Path
from array import array
import hashlib
import json
import struct

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Saved/Extracted/CombatEffects_20261006'
META = ROOT / 'Content/_Art/Effects/Metadata/Extraction_20261006'
rows = json.loads((META / 'AssetManifest.json').read_text(encoding='utf-8'))
report = []


def attribute(name, typ, data):
    return name.encode() + b'\0' + typ.encode() + b'\0' + struct.pack('<i', len(data)) + data


for row in rows:
    if row['source_type'] != 'Texture2D':
        continue
    original = next(o for o in json.loads((ROOT / row['source_json']).read_text(encoding='utf-8-sig')) if o['Type'] == 'Texture2D')
    if original['PixelFormat'] != 'PF_FloatRGBA':
        continue
    mip = original['Mips'][0]
    width, height = mip['SizeX'], mip['SizeY']
    count = width * height * 8
    assert mip['BulkData']['ElementCount'] == count
    path = BASE / 'OriginalRaw' / row['source_package']
    raw = path.with_suffix('.uexp').read_bytes()
    signature = struct.pack('<III', 0x48, count, count)
    hits, start = [], 0
    while True:
        pos = raw.find(signature, start)
        if pos < 0:
            break
        offset = pos + 20
        if raw[offset + count:offset + count + 12] == struct.pack('<III', width, height, 1):
            hits.append(offset)
        start = pos + 1
    assert len(hits) == 1, (row['name'], hits)
    pixels = raw[hits[0]:hits[0] + count]
    channels = b''.join(c.encode() + b'\0' + struct.pack('<iB3xii', 1, 0, 1, 1) for c in 'ABGR') + b'\0'
    window = struct.pack('<iiii', 0, 0, width - 1, height - 1)
    header = struct.pack('<II', 20000630, 2)
    for name, typ, value in [('channels', 'chlist', channels), ('compression', 'compression', b'\0'),
        ('dataWindow', 'box2i', window), ('displayWindow', 'box2i', window), ('lineOrder', 'lineOrder', b'\0'),
        ('pixelAspectRatio', 'float', struct.pack('<f', 1)), ('screenWindowCenter', 'v2f', struct.pack('<ff', 0, 0)),
        ('screenWindowWidth', 'float', struct.pack('<f', 1))]:
        header += attribute(name, typ, value)
    header += b'\0'
    offset = len(header) + height * 8
    offsets = b''.join(struct.pack('<Q', offset + y * (width * 8 + 8)) for y in range(height))
    output = BASE / 'Precision' / (row['name'] + '.exr')
    output.parent.mkdir(exist_ok=True)
    restored = bytearray()
    with output.open('wb') as out:
        out.write(header + offsets)
        for y in range(height):
            line = array('H')
            line.frombytes(pixels[y * width * 8:(y + 1) * width * 8])
            planes = [line[c::4] for c in (3, 2, 1, 0)]
            data = b''.join(p.tobytes() for p in planes)
            out.write(struct.pack('<ii', y, len(data)) + data)
            check = array('H', [0]) * (width * 4)
            for c, plane in zip((3, 2, 1, 0), planes):
                check[c::4] = plane
            restored.extend(check.tobytes())
    assert hashlib.sha256(restored).digest() == hashlib.sha256(pixels).digest()
    report.append({'source_package': row['source_package'], 'path': str(output.relative_to(ROOT)).replace('\\', '/'),
        'dimensions': [width, height], 'bulk_offset_in_uexp': hits[0], 'rgba_half_sha256': hashlib.sha256(pixels).hexdigest(),
        'exr_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'conversion': 'RGBA16F bits to ABGR half scanline EXR; alpha, sign, magnitude preserved; reconstructed interleaved SHA256 matches.'})
(META / 'PrecisionTextureExtraction.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('Exact RGBA16F textures:', len(report), flush=True)
