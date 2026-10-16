import os,sys
from pathlib import Path
base=Path(os.environ['TEMP'])/'yetuga_public_evidence_20261008';sys.path.insert(0,str(base/'pylib'))
from PIL import Image,ImageDraw
for name,first,last,step in [('dc_04',270,334,4),('dc_05',0,400,12),('dc_14',420,635,12),('dc_16',0,290,12)]:
 im=Image.open(base/(name+'.webp'));selection=list(range(first,min(last,im.n_frames-1)+1,step));rows=(len(selection)+3)//4
 sheet=Image.new('RGB',(1600,rows*220),(25,25,25));draw=ImageDraw.Draw(sheet)
 for slot,index in enumerate(selection):
  im.seek(index);im.load();frame=im.convert('RGB');frame.thumbnail((400,190));x=slot%4*400;y=slot//4*220
  sheet.paste(frame,(x,y));draw.text((x+4,y+193),f'{name} frame{index} (clip time approx {index/60:.3f}s)',fill='white')
 sheet.save(base/(name+'_detail.jpg'),quality=96)
print('rendered detail sheets')
