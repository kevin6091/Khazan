from pathlib import Path
from PIL import Image,ImageDraw
import json
root=Path(__file__).resolve().parents[2]/'Metadata/MonsterBloodReference_20261012/FluidProbe01'
rows=[]
for p in root.glob('*.tga'):
    im=Image.open(p).convert('RGBA');rows.append({'name':p.stem,'size':im.size,'extrema':im.getextrema()})
    rgb=im.convert('RGB');rgb.thumbnail((1024,1024));rgb.save(root/(p.stem+'.png'))
    alpha=im.getchannel('A');alpha.thumbnail((1024,1024));alpha.save(root/(p.stem+'_Alpha.png'))
(root/'ChannelStats.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
