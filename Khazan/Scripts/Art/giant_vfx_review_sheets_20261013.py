"""Build labeled diagnostic contact sheets from actual viewport captures."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import sys
root=Path(__file__).resolve().parents[2]/'Metadata/GiantVFX_20261013'/sys.argv[1]
cases=[x.split('\t') for x in (root/'GiantReviewCases.tsv').read_text(encoding='utf-8').splitlines()]
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
groups={}
for i,c in enumerate(cases):
    files=sorted(root.glob(f'{i:03d}_*_01.png'))
    if not files:continue
    groups.setdefault(c[2],[]).append((i,c,files[0]))
for kind,items in groups.items():
    for start in range(0,len(items),16):
        batch=items[start:start+16];sheet=Image.new('RGB',(1280,816),(20,20,20));draw=ImageDraw.Draw(sheet)
        for j,(i,c,p) in enumerate(batch):
            pic=Image.open(p).convert('RGB');pic.thumbnail((320,180));x=j%4*320;y=j//4*204;sheet.paste(pic,(x,y))
            label=f'{i:03d} '+c[0].replace('FP_Boss_Yetuga_','').replace('Locomotion_','')
            draw.text((x+3,y+181),label[:43],font=font,fill='white')
        target=root/f'ReviewSheet_{kind}_{start//16:02d}.jpg';sheet.save(target,quality=93);print(target.name)
