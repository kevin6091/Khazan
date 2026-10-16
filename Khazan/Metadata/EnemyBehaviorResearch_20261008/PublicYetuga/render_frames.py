import os,sys,json
from pathlib import Path
base=Path(os.environ['TEMP'])/'yetuga_public_evidence_20261008';sys.path.insert(0,str(base/'pylib'))
from PIL import Image,ImageDraw
manifest=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
for item in manifest:
    if 'file' not in item:continue
    im=Image.open(item['file']);time=0;selected=[];next_time=0
    for index in range(im.n_frames):
        im.seek(index);im.load();duration=im.info.get('duration',0)
        if time>=next_time:
            frame=im.convert('RGB');frame.thumbnail((400,250));selected.append((frame.copy(),time,index));next_time=time+400
        time+=duration
    rows=(len(selected)+3)//4;sheet=Image.new('RGB',(1600,rows*275),(25,25,25));draw=ImageDraw.Draw(sheet)
    for slot,(frame,t,index) in enumerate(selected):
        x=slot%4*400;y=slot//4*275;sheet.paste(frame,(x,y));draw.text((x+4,y+250),f"{item['id']} clip {t/1000:.3f}s frame{index}",fill='white')
    sheet.save(item['sheet'],quality=92);item['duration_ms']=time
(base/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in i.items() if k in ('id','duration_ms','sheet')} for i in manifest],indent=2))
