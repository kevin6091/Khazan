import os,sys,re,json,urllib.request,concurrent.futures
from pathlib import Path
base=Path(os.environ['TEMP'])/'yetuga_public_evidence_20261008'
sys.path.insert(0,str(base/'pylib'))
from PIL import Image,ImageDraw
pages={'inven':'https://www.inven.co.kr/board/party/6187/21','dc':'https://gall.dcinside.com/mgallery/board/view/?id=berserkerkhazan&no=19069'}
items=[]
for name,url in pages.items():
    request=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
    html=urllib.request.urlopen(request).read().decode('utf-8','replace')
    if name=='inven':
        urls=list(dict.fromkeys(re.findall(r'https://upload3.inven.co.kr/upload/2025/01/17/bbs/i[^"<> ]+\.webp',html)))
    else:
        urls=list(dict.fromkeys(re.findall(r'https://dcimg1\.dcinside\.com/viewimage\.php[^"<> ]+',html)))
    for index,source in enumerate(urls): items.append({'id':f'{name}_{index+1:02}','source':source,'page':url})
def get(item):
    path=base/(item['id']+'.webp')
    try:
        req=urllib.request.Request(item['source'],headers={'User-Agent':'Mozilla/5.0','Referer':item['page']})
        path.write_bytes(urllib.request.urlopen(req).read())
        im=Image.open(path); time=0; frames=[]
        for i in range(getattr(im,'n_frames',1)):
            im.seek(i); duration=im.info.get('duration',0)
            frames.append((i,time,duration));time+=duration
        item.update(file=str(path),frame_count=len(frames),duration_ms=time,size=im.size,format=im.format)
        selected=[]; next_time=0
        for i,t,d in frames:
            if t>=next_time:
                im.seek(i); frame=im.convert('RGB'); frame.thumbnail((400,250))
                selected.append((frame.copy(),t,i));next_time=t+400
        rows=(len(selected)+3)//4
        sheet=Image.new('RGB',(1600,rows*275),(25,25,25));draw=ImageDraw.Draw(sheet)
        for slot,(frame,t,i) in enumerate(selected):
            x=(slot%4)*400;y=(slot//4)*275
            sheet.paste(frame,(x,y));draw.text((x+4,y+250),f"{item['id']} clip {t/1000:.3f}s frame{i}",fill='white')
        sheet_path=base/(item['id']+'_sheet.jpg');sheet.save(sheet_path,quality=92)
        item['sheet']=str(sheet_path)
    except Exception as e:item['error']=str(e)
    return item
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool: results=list(pool.map(get,items))
(base/'manifest.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in i.items() if k not in ('source','page')} for i in results],ensure_ascii=False,indent=2))
