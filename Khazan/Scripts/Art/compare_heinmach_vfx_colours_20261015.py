"""Compare actual game screenshots; particle randomness is not pixel parity."""
from pathlib import Path
from PIL import Image,ImageChops,ImageDraw,ImageFont,ImageStat
import colorsys,json,math,sys
root=Path(__file__).resolve().parents[2]/'Metadata/HeinMachColourVFX_20261015'
dev,hein,out=(root/name for name in sys.argv[1:4]);out.mkdir(exist_ok=False)
a,b=(json.loads((folder/'Probe.json').read_text(encoding='utf-8')) for folder in (dev,hein))
assert a['status']==b['status']=='passed'
assert [row['asset'] for row in a['rows']]==[row['asset'] for row in b['rows']]
backgrounds=[Image.open(folder/'Background.png').convert('RGB') for folder in (dev,hein)]
font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',13)
rows=[];bounds={}
def sample(path,background):
    im=Image.open(path).convert('RGB');assert im.size==background.size
    diff=ImageChops.difference(im,background)
    mask=diff.convert('L').point(lambda x:255 if x>12 else 0)
    box=mask.getbbox()
    # Exclude outer UI/black borders from measurements; both use identical ROI.
    w,h=im.size;roi=(int(w*.1),int(h*.1),int(w*.9),int(h*.88))
    foreground=ImageChops.subtract(im,background).crop(roi).resize((320,130))
    absolute=diff.crop(roi).resize((320,130))
    energy=ImageStat.Stat(absolute).sum
    emission=ImageStat.Stat(foreground).sum
    total=sum(emission);signature=[x/total for x in emission] if total else [0.,0.,0.]
    support=sum(x>12 for x in absolute.convert('L').getdata())
    return {'support_pixels_QA':support,'absolute_energy':sum(energy),'positive_energy':total,
            'emission_signature_rgb':signature,'bbox':box,'resolution':im.size}
for left,right in zip(a['rows'],b['rows']):
    index=left['index'];files=[folder/left['image'] for folder in (dev,hein)]
    assert all(path.is_file() for path in files),files
    values=[sample(path,bg) for path,bg in zip(files,backgrounds)]
    s,t=(x['emission_signature_rgb'] for x in values)
    n=math.sqrt(sum(x*x for x in s)*sum(x*x for x in t))
    angle=math.degrees(math.acos(min(1.,max(-1.,sum(x*y for x,y in zip(s,t))/n)))) if n else None
    ratio=values[1]['absolute_energy']/values[0]['absolute_energy'] if values[0]['absolute_energy'] else None
    visible=all(x['support_pixels_QA']>=12 for x in values)
    # Thresholds are review heuristics, not original values or a parity guarantee.
    flag=visible and (angle is not None and angle>10 or ratio is not None and not .65<=ratio<=1.6)
    rows.append({'index':index,'asset':left['asset'],'dev':values[0],'hein':values[1],
                 'visible_in_both':visible,'signature_angle_deg':angle,'energy_ratio':ratio,
                 'review_flag':bool(flag),'completed_before_sample':left['completed_before_sample'] or right['completed_before_sample']})
    boxes=[x['bbox'] for x in values if x['bbox']]
    if boxes:
        w,h=backgrounds[0].size
        box=(min(x[0] for x in boxes),min(x[1] for x in boxes),max(x[2] for x in boxes),max(x[3] for x in boxes))
        cx,cy=(box[0]+box[2])/2,(box[1]+box[3])/2
        width=max(180,box[2]-box[0]+60);height=max(90,box[3]-box[1]+30)
        bounds[index]=(max(0,int(cx-width/2)),max(0,int(cy-height/2)),min(w,int(cx+width/2)),min(h,int(cy+height/2)))
def sheet(items,name):
    image=Image.new('RGB',(1080,50+len(items)*165),(22,25,30));draw=ImageDraw.Draw(image)
    draw.text((12,10),'DEV MAP (left) / HEIN MACH (right), same native system, independent random particles',font=font,fill='white')
    for offset,row in enumerate(items):
        y=50+offset*165;idx=row['index']
        draw.text((10,y),str(idx)+' '+row['asset'].split('/')[-1],font=font,fill=(255,190,120) if row['review_flag'] else 'white')
        for column,folder in enumerate((dev,hein)):
            im=Image.open(folder/a['rows'][idx]['image']).convert('RGB')
            if idx in bounds:im=im.crop(bounds[idx])
            im.thumbnail((520,132),Image.Resampling.LANCZOS)
            image.paste(im,(10+column*540,y+24))
    image.save(out/(name+'.jpg'),quality=92)
for start in range(0,len(rows),8):sheet(rows[start:start+8],'All_'+str(start//8).zfill(2))
flags=sorted((x for x in rows if x['review_flag']),key=lambda x:x['signature_angle_deg'] or 0,reverse=True)
for start in range(0,len(flags),8):sheet(flags[start:start+8],'Review_'+str(start//8).zfill(2))
selected=[]
for token in ('PP_Dmg_Blood_Trail_Sub','HitBloodReference','KZ_Slash','Parring_Distort','Heal_DrainBurst','Heal_GhostArm',
              'ChargeAttack','Grapple_01','LVL_WBP_LightObj_001_FIRE_medium','Yetuga','IceShock','BurstAttack'):
    found=next((row for row in rows if token.lower() in row['asset'].lower() and row not in selected),None)
    if found:selected.append(found)
for start in range(0,len(selected),8):sheet(selected[start:start+8],'Representative_'+str(start//8))
report={'status':'paired_complete','paired_images':len(rows),'visible_in_both':sum(x['visible_in_both'] for x in rows),
        'review_flags':len(flags),'rows':rows,'method':'background-subtracted colour/energy signatures; native random particle shapes vary',
        'limits':'One isolated 0.2s sample. Hidden/finished effects and skeletal/parameter dependent effects require actual combat evidence. Lit debris/refraction respond to the scene.'}
(out/'Comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({key:value for key,value in report.items() if key!='rows'}))
