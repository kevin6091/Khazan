"""Decode the exact UE4 inline FFloat16Color bulk payload into importable FGA."""
from pathlib import Path
import hashlib
import json
import math
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Saved/Extracted/HeinMachWeather_20261006'
dimension=int(sys.argv[1]) if len(sys.argv)>1 else 16
assert dimension in (8,16)
PACKAGE = 'BBQ/Content/_Kazan_/Art/VFX/VFX_Data/VectorField/FP_Perlin_HighFreq_'+str(dimension)+'x'+str(dimension)+'x'+str(dimension)
raw = BASE / (('DustRaw/' if dimension==8 else 'VectorRaw/') + PACKAGE)
meta_path = BASE / (('DustSource/' if dimension==8 else 'Source/') + PACKAGE + '.json')
meta = json.loads(meta_path.read_text(encoding='utf-8-sig'))[0]['Properties']
size = [meta[n] for n in ['SizeX','SizeY','SizeZ']]
expected = math.prod(size) * 8  # UE SourceData is FFloat16Color (R,G,B,A).
uexp = raw.with_suffix('.uexp').read_bytes()
uasset = raw.with_suffix('.uasset').read_bytes()
assert uexp[-4:] == struct.pack('<I',0x9e2a83c1), 'UE package trailer'
offset = len(uexp)-4-expected
flags,count,on_disk,package_offset = struct.unpack_from('<IIIq',uexp,offset-20)
assert count == on_disk == expected
assert flags == 0x48, 'Expected inline payload + single use bulk flags'
assert package_offset == len(uasset)+offset, 'Serialized combined-package payload offset'
samples = list(struct.iter_unpack('<eeee',uexp[offset:offset+expected]))
assert len(samples)==math.prod(size) and all(math.isfinite(v) for sample in samples for v in sample)
assert all(v[3]==0 for v in samples), 'FGA has three vector components; unexpected alpha payload'
target = BASE / (PACKAGE.rsplit('/',1)[-1]+'.fga')
bounds = meta['Bounds']
rows = [','.join(map(str,size)), ','.join(str(bounds['Min'][c]) for c in 'XYZ'),
        ','.join(str(bounds['Max'][c]) for c in 'XYZ')]
rows.extend(','.join(format(v,'.9g') for v in sample[:3]) for sample in samples)
target.write_text(',\n'.join(rows)+',\n',encoding='ascii')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'source_package':PACKAGE,'source_metadata':str(meta_path),'raw_uasset_sha256':sha(raw.with_suffix('.uasset')),
        'raw_uexp_sha256':sha(raw.with_suffix('.uexp')),'dimensions':size,'source_bounds_cm':bounds,
        'bulk_payload_bytes':expected,'payload_offset_in_uexp':offset,'bulk_flags':flags,
        'samples':len(samples),'fga':str(target),'fga_sha256':sha(target),
        'conversion':'FFloat16Color.RGB -> identical-order FGA XYZ. Alpha verified zero. No sign/coordinate/strength change.',
        'engine_layout_evidence':'UE_5.8/Engine/Source/Runtime/Engine/Private/VectorField.cpp SourceData sizeof(FFloat16Color); original 4.27 byte header independently validated.'}
out=ROOT/('Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006/VectorFieldExtraction'+('8' if dimension==8 else '')+'.json')
out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'exact_vector_samples':len(samples),'output':str(target)}))
