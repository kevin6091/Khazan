"""Index named subobjects in cached T3D; never changes a package."""
from pathlib import Path
import json, re

main=Path(__file__).resolve().parents[2];out=main/'Metadata/GiantVFX_20261013'
catalog={}
for file in (out/'ParticleExports01/Exports').glob('*.t3d'):
    b=file.read_bytes();text=b.decode('utf-16' if b.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig')
    objects={};stack=[]
    for line in text.splitlines():
        s=line.strip()
        if s.startswith('Begin Object '):
            name=re.search(r'Name="([^"]+)"',s).group(1)
            cls=re.search(r'Class=([^\s]+)',s)
            ref=re.search(r'ExportPath="([^"]+)"',s)
            key=ref.group(1).split("'",1)[1].rstrip("'") if ref else (stack[-1]+'.'+name if stack else name)
            row=objects.setdefault(key,{'name':name,'class':None,'properties':[]})
            if cls:row['class']=cls.group(1)
            stack.append(key)
        elif s=='End Object':stack.pop()
        elif stack and s:objects[stack[-1]]['properties'].append(s)
    catalog[file.name]=objects
(out/'ParticleObjectCatalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
for selected in ['FP_Boss_Yetuga_Footstep_Normal_01.t3d','FP_Boss_Yetuga_Smash_normal_01.t3d','FP_Boss_Yetuga_IceBreath_Mouth_01.t3d']:
    objects=catalog[selected]
    print(selected)
    for key,row in objects.items():
        if row['class'] and any(c in row['class'] for c in ['ParticleModuleSize','ParticleModuleVelocity','ParticleModuleLifetime']):
            print(row['class'].rsplit('.',1)[-1],row['properties'][:2])
    # Source direct property references above identify the distribution paths below.
    for key,row in objects.items():
        if row['class'] and 'DistributionVector' in row['class']:
            values=[p for p in row['properties'] if p.startswith(('Constant=','Min=','Max='))]
            if values:print(row['name'],values)
