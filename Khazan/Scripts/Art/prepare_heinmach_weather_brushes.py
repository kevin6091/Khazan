"""Restore source WEP BSP face rings using the previously omitted vertex pool."""
from pathlib import Path
import json
import hashlib

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Saved/Extracted/HeinMachWeather_20261006'
META = ROOT / 'Content/_Art/Player/Environment/Rendering/Metadata/HeinMachWeather_20261006'
source_file = Path.home() / 'Desktop/\uce74\uc794/Exports/BBQ/Content/_Kazan_/Level/HeinMach/HeinMach_Light.json'
objects = json.loads(source_file.read_text(encoding='utf-8-sig'))
geometry_file = BASE/'Brush/HeinMach_Light_BrushGeometry.json'
models = json.loads(geometry_file.read_text())
manifest = json.loads((META.parent/'LookRestoration_20261002/SourceManifest.json').read_text())
report = []
fmt = lambda v: ','.join(format(v[c], '.9g') for c in 'XYZ')
for row in manifest['HeinMach_volumes']:
    a = objects[row['source_actor_index']]
    original = objects[int(a['Properties']['Brush']['ObjectPath'].rsplit('.', 1)[1])]
    candidates = [m['fields'] for m in models if m['fields']['Bounds'] == original['Bounds'] and m['fields']['Points'] == original['Points']]
    assert len(candidates) == 1, (a['Name'], len(candidates))
    model = candidates[0]
    lines = ['Begin Brush Name=HM_SourceWEP', 'Begin PolyList']
    polygons = []
    for node in model['Nodes']:
        if node['NumVertices'] < 3:
            continue
        surf = model['Surfs'][node['iSurf']]
        vertices = [model['Points'][model['Verts'][node['iVertPool']+i]['pVertex']] for i in range(node['NumVertices'])]
        normal = model['Vectors'][surf['vNormal']]
        lines += ['Begin Polygon', 'Origin '+fmt(model['Points'][surf['pBase']]), 'Normal '+fmt(normal),
                  'TextureU '+fmt(model['Vectors'][surf['vTextureU']]), 'TextureV '+fmt(model['Vectors'][surf['vTextureV']])]
        lines += ['Vertex '+fmt(v) for v in vertices]
        lines += ['End Polygon']
        polygons.append({'normal': normal, 'vertices_cm': vertices})
    lines += ['End PolyList', 'End Brush']
    target = BASE/'Brush'/('HM_WEP_'+str(row['source_actor_index'])+'.t3d')
    target.write_text('\n'.join(lines)+'\n', encoding='ascii')
    report.append({'source_actor_index': row['source_actor_index'], 'profile': row['profile'], 'brush': str(target),
                   'polygons': polygons, 'vertices_in_pool': len(model['Verts']), 'transform': row['transform'],
                   't3d_sha256': hashlib.sha256(target.read_bytes()).hexdigest()})
(META/'OriginalBrushTopology.json').write_text(json.dumps({'source_geometry_sha256': hashlib.sha256(geometry_file.read_bytes()).hexdigest(),
    'validation': 'Mounted original Points and Bounds exactly match cached original metadata. Node.iVertPool -> Vert.pVertex -> Point preserves source face rings and BSP splits.',
    'volumes': report}, indent=2)+'\n', encoding='utf-8')
print('Original brush topology:',len(report),'volumes',sum(len(v['polygons']) for v in report),'polygons')
