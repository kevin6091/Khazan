"""Compare unmodified game viewport screenshots; never edit product images/assets."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Metadata/SceneLook_20261012'
font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',28)
def comparison(name,pairs):
    first=Image.open(pairs[0][0]).convert('RGB');w,h=first.size
    sheet=Image.new('RGB',(w*2,h*len(pairs)+56*len(pairs)),(22,25,29));draw=ImageDraw.Draw(sheet)
    for i,(old,new,label) in enumerate(pairs):
        y=i*(h+56)
        draw.text((16,y+10),'수정 전 · '+label,font=font,fill=(238,238,238))
        draw.text((w+16,y+10),'수정 후 · '+label,font=font,fill=(238,238,238))
        for x,path in [(0,old),(w,new)]:
            im=Image.open(path).convert('RGB');assert im.size==(w,h)
            sheet.paste(im,(x,y+56))
    sheet.save(OUT/name,quality=94)
    return {'file':name,'single_view_pixels':[w,h],'comparison_pixels':list(sheet.size),'colors_unmodified':True}
new_dev=OUT/('MainDevAfter01' if (OUT/'MainDevAfter01/Capture.json').exists() else 'DevAfter02')
new_hm=OUT/('MainHeinAfter01' if (OUT/'MainHeinAfter01/Capture.json').exists() else 'HeinAfter04')
rows=[comparison('DevMap_BeforeAfter.jpg',[(OUT/'DevBefore01/PlayerFront.png',new_dev/'PlayerFront.png','플레이어 역광'),
    (OUT/'DevBefore01/Player.png',new_dev/'Player.png','플레이어·바닥 그림자')]),
    comparison('HeinMach_BeforeAfter.jpg',[(OUT/'HeinBefore01/Entry.png',new_hm/'Entry.png','눈·바위·횃불'),
    (OUT/'HeinBefore01/ReferenceStart.png',new_hm/'ReferenceStart.png','길·음영·표면')])]
(OUT/'VisualComparison.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(rows)
