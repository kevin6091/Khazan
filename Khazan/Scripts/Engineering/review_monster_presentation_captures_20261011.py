"""Make indexed QA contact sheets; never alter source screenshots or game assets."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,math,sys
base=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/MonsterPresentationRepair_20261011').resolve()
root=(base/sys.argv[1]).resolve();assert root.is_relative_to(base)
out=root/'ContactSheets';out.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',12)
files=sorted(root.glob('Attack_*.png'));rows=[]
for page in range(math.ceil(len(files)/24)):
    batch=files[page*24:(page+1)*24];sheet=Image.new('RGB',(1440,6*236),(26,26,26));draw=ImageDraw.Draw(sheet)
    for i,path in enumerate(batch):
        x=(i%4)*360;y=(i//4)*236
        im=Image.open(path).convert('RGB');im.thumbnail((356,200));sheet.paste(im,(x,y))
        label=path.stem.removeprefix('Attack_');draw.text((x+3,y+202),label[:48],fill='white',font=font)
        if len(label)>48:draw.text((x+3,y+216),label[48:96],fill='white',font=font)
    name=f'AttackSheet_{page+1:02}.jpg';sheet.save(out/name,quality=95);rows.append({'image':name,'cases':[p.name for p in batch]})
(out/'Index.json').write_text(json.dumps({'attack_pngs':len(files),'pages':rows},indent=2),encoding='utf-8')
print(json.dumps({'attack_pngs':len(files),'contact_sheets':len(rows)}))
