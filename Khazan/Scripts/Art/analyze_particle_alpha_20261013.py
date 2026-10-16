"""Offline material ownership/opacity graph triage from the saved usage audit."""
from pathlib import Path
import collections, json, re
MAIN = Path(__file__).resolve().parents[2]
ROOT = MAIN / 'Metadata/ParticleAlpha_20261013'
AUDIT = ROOT / 'Audit02'
d = json.loads((AUDIT / 'Audit.json').read_text(encoding='utf-8'))
materials = {r['path']: r for r in d['materials']}
systems = {r['path']: r for r in d['systems']}
uses = collections.defaultdict(set)

def package(p): return p.split('.', 1)[0]
def exported(path):
    b = path.read_bytes()
    return b.decode('utf-16' if b.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig')

for path, row in systems.items():
    text = exported(AUDIT / row['export'])
    # Actual ParticleModuleRequired/mesh override Material pointers, not mesh defaults.
    for p in re.findall(r'\bMaterial(?:s\(\d+\)|s\[\d+\])?=(?:"[^\']*|[^\']*)\'(/Game/[^\'"\r\n]+)', text):
        uses[package(p)].add(path)

rows = []
for path, row in materials.items():
    if not uses[path]: continue
    chain = []; current = row; seen = set(); override = None
    while current and current['path'] not in seen:
        seen.add(current['path']); chain.append(current['path'])
        text = current.get('base_property_overrides') or ''
        if override is None and 'bOverride_BlendMode=True' in text:
            m = re.search(r'\bBlendMode=([^,)]+)', text)
            if m: override = m.group(1)
        parent = current.get('parent')
        if not parent: break
        current = materials.get(package(parent))
    if not current or current['class'] != 'Material': continue
    mode = override or current['settings'].get('blend_mode')
    nodes = {n['name']: n for n in current['nodes']}
    reachable = set(); queue = [v for k, v in current['outputs'].items() if 'OPACITY' in k and v]
    while queue:
        n = queue.pop()
        if n in reachable or n not in nodes: continue
        reachable.add(n); queue.extend(v for v in nodes[n]['inputs'] if v)
    alpha_nodes = [nodes[n] for n in sorted(reachable)]
    item = {'path': path, 'master': current['path'], 'effective_blend': mode, 'systems': sorted(uses[path]),
            'alpha_connected': bool(reachable), 'outputs': current['outputs'], 'alpha_nodes': alpha_nodes,
            'has_explicit_edge_feather': any('feather' in str(n).lower() or 'smooth particle boundary' in str(n).lower() for n in alpha_nodes),
            'textures': sorted(set(re.findall(r"Texture2D'(/Game/[^'\r\n]+)'", exported(AUDIT / row['export']))))}
    rows.append(item)
report = {'status': 'triaged', 'direct_material_count': len(rows), 'masters': len(set(r['master'] for r in rows)),
          'rows': rows, 'translucent_missing_alpha': [r for r in rows if any(t in str(r['effective_blend']).lower() for t in ('translucent','masked','alpha_composite')) and not r['alpha_connected']],
          'note': 'Lack of explicit feather is not proof of a defect. Resolve texture/channel and inspect actual RHI before editing.'}
(ROOT / 'MaterialTriage.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps({'direct_material_count': len(rows), 'master_count': report['masters'],
                  'missing_alpha': [{'path': r['path'], 'blend': r['effective_blend'], 'systems': r['systems']} for r in report['translucent_missing_alpha']],
                  'unfeathered_masters': sorted(set(r['master'] for r in rows if not r['has_explicit_edge_feather']))}, indent=2))
