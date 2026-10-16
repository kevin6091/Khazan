from pathlib import Path
from PIL import Image,ImageDraw
import sys,json
root=Path(__file__).resolve().parents[2]/'Metadata/MonsterBloodReference_20261012'/sys.argv[1]
files=sorted(root.glob('Blood_*.png'));sheets=[]
for batch in range((len(files)+11)//12):
    subset=files[batch*12:(batch+1)*12];sheet=Image.new('RGB',(1440,320*((len(subset)+2)//3)),(24,24,24));draw=ImageDraw.Draw(sheet)
    for index,p in enumerate(subset):
        im=Image.open(p).convert('RGB');im.thumbnail((470,282));x=index%3*480;y=index//3*320
        sheet.paste(im,(x,y+28));draw.text((x+5,y+7),p.stem,fill='white')
    path=root/('BloodReview%02d.png'%batch);sheet.save(path);sheets.append(path.name)
(root/'CaptureIndex.json').write_text(json.dumps({'blood_frames':len(files),'sheets':sheets},indent=2),encoding='utf-8')
deaths=sorted(root.glob('DeathAsh_*.png'))+sorted(root.glob('LateDeathAsh_*.png'))
if deaths:
    sheet=Image.new('RGB',(1440,320*((len(deaths)+2)//3)),(24,24,24));draw=ImageDraw.Draw(sheet)
    for index,p in enumerate(deaths):
        im=Image.open(p).convert('RGB');im.thumbnail((470,282));x=index%3*480;y=index//3*320
        sheet.paste(im,(x,y+28));draw.text((x+5,y+7),p.stem,fill='white')
    sheet.save(root/'DeathReview.png')
