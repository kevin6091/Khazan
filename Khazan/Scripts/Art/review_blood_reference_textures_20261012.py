from pathlib import Path
from PIL import Image, ImageDraw
import json
root=Path(__file__).resolve().parents[2]/'Metadata/MonsterBloodReference_20261012/TextureProbe01'
files=sorted(root.glob('*.tga'));stats=[]
for batch in range(2):
    subset=files[batch*6:(batch+1)*6];sheet=Image.new('RGB',(1040,225*len(subset)),(38,38,38));draw=ImageDraw.Draw(sheet)
    for row,path in enumerate(subset):
        im=Image.open(path).convert('RGBA');stats.append({'name':path.stem,'size':im.size,'extrema':im.getextrema()})
        channels=[im.convert('RGB')]+[im.getchannel(c).convert('RGB') for c in 'RGB']
        for col,pic in enumerate(channels):
            pic.thumbnail((250,195));sheet.paste(pic,(260*col,row*225+28));draw.text((260*col+4,row*225+4),path.stem+' '+['RGB','R','G','B'][col],fill='white')
    sheet.save(root/('Channels%02d.png'%batch))
(root/'ChannelStats.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
