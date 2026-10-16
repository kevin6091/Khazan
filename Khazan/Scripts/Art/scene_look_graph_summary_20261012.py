from pathlib import Path
import json
from PIL import Image
ROOT=Path(__file__).resolve().parents[2]
d=json.loads((ROOT/'Metadata/SceneLook_20261012/MaterialAudit01/Materials.json').read_text())
root=next(v for k,v in d['materials'].items() if k.endswith('M_AKCartoonCharacter.M_AKCartoonCharacter'))
nodes={n['name']:n for n in root['nodes']}
def tree(name,depth,seen):
    if not name or name in seen or depth>7:return
    seen.add(name);n=nodes[name]
    selected={k:v for k,v in n.items() if k not in ['input_nodes','desc']}
    print(' '*depth+str(selected))
    for child in n['input_nodes']:tree(child,depth+1,seen)
for out in ['BASE_COLOR','METALLIC','ROUGHNESS','SPECULAR']:
    print(out);tree(root['outputs'][out]['node'],0,set())
for k,v in d['materials'].items():
    if k.endswith(('CM_P_Kazan_Nude_UpperV2.CM_P_Kazan_Nude_UpperV2','CM_P_Kazan_FaceV2.CM_P_Kazan_FaceV2')):
        print(k,{p:v['scalar_parameters'].get(p) for p in ['MetallicStrength','UseSpecularAsMetallic','RoughnessScale','RoughnessBias','DarkAOLevel','SpecularStrength']},v['texture_parameters'].get('Tex_S'))
for p in [ROOT/'Metadata/SceneLook_20261012/OpacityProbe01/OpacityTexture.png',
    Path.home()/'Desktop/\uce74\uc794/BBQ/Content/Art/World/World_Material/Prop/Texture/WT_COM_ThinTree_Base_001_02_D.png',
    Path.home()/'Desktop/\uce74\uc794/BBQ/Content/Art/World/World_Material/Prop/Texture/WT_COM_ThinTree_Base_001_03_D.png']:
    im=Image.open(p);print('TEXTURE',p.name,im.mode,im.size,im.getextrema())
src=Path.home()/'Desktop/\uce74\uc794/Exports/BBQ/Content/Art/World/World_Material/Prop/Material/WM_COM_SmallTree_Base_003_02.json'
for e in json.loads(src.read_text(encoding='utf-8-sig')):
    if e.get('Type')=='MaterialInstanceConstant':
        print('SOURCE',src,{k:v for k,v in e.get('Properties',{}).items() if k in ['Parent','TextureParameterValues','ScalarParameterValues','BasePropertyOverrides']})
