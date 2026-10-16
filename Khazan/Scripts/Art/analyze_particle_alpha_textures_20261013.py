"""PNG channel/border evidence and actual sample-A links, not filename guesses."""
from pathlib import Path
import json, re
from PIL import Image, ImageStat
MAIN = Path(__file__).resolve().parents[2]; ROOT = MAIN / 'Metadata/ParticleAlpha_20261013'
probe = json.loads((ROOT / 'Textures02/Textures.json').read_text())
audit = json.loads((ROOT / 'Audit02/Audit.json').read_text(encoding='utf-8'))
masters = {r['path']: r for r in audit['materials'] if r['class']=='Material'}
triage = {r['path']:r for r in json.loads((ROOT/'MaterialTriage.json').read_text())['rows']}
stats = {}
for path, row in probe['textures'].items():
    if not row.get('file'): continue
    im = Image.open(ROOT / 'Textures02' / row['file']).convert('RGBA'); w,h = im.size
    edges = [im.crop(box) for box in ((0,0,w,1),(0,h-1,w,h),(0,0,1,h),(w-1,0,w,h))]
    means = [ImageStat.Stat(e).mean for e in edges]
    stats[path] = {'size': [w,h], 'extrema': im.getextrema(),
                   'border_mean_rgba': [sum(m[i] for m in means)/4 for i in range(4)],
                   'constant_alpha': im.getextrema()[3][0]==im.getextrema()[3][1]}
candidates = []
for row in probe['rows']:
    master = masters[row['master']]; raw = (ROOT/'Audit02'/master['export']).read_bytes()
    text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig').replace('\r','')
    alpha_names = {n['name'] for n in triage[row['material']]['alpha_nodes']}
    # Exported expression property blocks preserve exact channel OutputIndex.
    blocks = re.findall(r'Begin Object Name="([^"]+)"[^\r\n]*\r?\n(.*?)End Object', text, re.S)
    for texture in row['textures']:
        s = stats.get(texture['texture'])
        if not s or not s['constant_alpha'] or s['extrema'][3][0] != 255: continue
        node = texture['node']; alpha_links = []
        for parent, body in blocks:
            if parent not in alpha_names: continue
            for line in body.splitlines():
                if 'Expression=' in line and re.search(':'+re.escape(node)+r"['\"]",line) and 'OutputIndex=4' in line:
                    alpha_links.append({'parent':parent,'line':line.strip()})
        if alpha_links:
            candidates.append({'material':row['material'],'master':row['master'],'texture':texture['texture'],
                               'parameter':texture['parameter'],'alpha_links':alpha_links,'stats':s,'systems':row['systems']})
R = {'status':'analyzed','texture_stats':stats,'sample_alpha_constant_255_candidates':candidates,
     'note':'A constant alpha is not automatically wrong for meshes or black-RGB Additive. Candidates require current emitter and positive RHI inspection.'}
(ROOT/'TextureChannelAnalysis.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print(json.dumps({'png_textures':len(stats),'constant_255_sampleA_candidates':len(candidates),
                  'candidates':[{'material':r['material'],'master':r['master'],'texture':r['texture'],'systems':r['systems'][:3]} for r in candidates]},indent=2))
