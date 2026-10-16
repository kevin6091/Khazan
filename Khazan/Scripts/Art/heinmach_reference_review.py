"""Inspect stored contracts and measure reference images without re-surveying assets."""
from pathlib import Path
import collections
import json
import re
import sys
import csv

ROOT=Path(__file__).resolve().parents[2]
STAGE=ROOT/'Saved/ArtStaging/HeinMachReference_20261006'
OUT=ROOT/'Saved/ImportReports/HeinMachReference_20261006'
sys.path.insert(0,str(ROOT/'Saved/Tools/HeinMachReference_20261006'))


def baseline():
    j=json.loads((STAGE/'Saved/ImportReports/HeinMachReference_20261006/BaselineProbe.json').read_text(encoding='utf-8'))
    parents=collections.Counter()
    for row in j['materials'].values():
        match=re.search("<Object '([^']+)'",row.get('parent',''))
        parents[match.group(1) if match else row.get('parent','')]+=1
    print('parents',dict(parents))
    for path,row in sorted(j['materials'].items(),key=lambda kv:-kv[1]['actor_count'])[:12]:
        print(path,row['actor_count'],{k:v for k,v in row.get('vector_parameters',{}).items()
                                     if 'Component' in k or 'Normal' in k})
    print('bounds',j.get('bounds',{}))
    print('PP policies',[(r['label'],r['policy'],r['settings']['scene_color_tint']) for r in j['postprocess']])
    for cls,methods in j['api'].items():
        print(cls,{k:v for k,v in methods.items() if any(t in k for t in
                 ['find_emitter','get_emitter','create_system','find_module','set_parameter'])})


def photos():
    import numpy as np
    from PIL import Image
    rows=[]
    for path in (ROOT/'Docs/Art').glob('*HeinMach*'):
        if path.suffix.lower() not in ('.png','.jpg'):
            continue
        a=np.asarray(Image.open(path).convert('RGB'),dtype=np.float64)/255
        # Scene centre only: exclude most title, HUD, subtitles and publisher watermark.
        h,w=a.shape[:2]
        roi=a[int(h*.1):int(h*.78),int(w*.15):int(w*.86)]
        y=roi@np.array([.2126,.7152,.0722])
        row={'file':str(path.relative_to(ROOT)),'resolution':[w,h],
             'centre_RGB_mean':np.mean(roi,axis=(0,1)).tolist(),
             'centre_display_luma_percentiles':np.percentile(y,[5,25,50,75,95]).tolist(),
             'boundary':'Display image measurements, not source linear lighting values or same-scene fidelity score.'}
        rows.append(row)
    (OUT/'ReferencePhotoAnalysis.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(rows,ensure_ascii=False,indent=2))


def locations():
    j=json.loads((STAGE/'Saved/ImportReports/HeinMachReference_20261006/BaselineProbe.json').read_text(encoding='utf-8'))
    for label,pose in j['actor_poses'].items():
        if ('tent' in label.lower() and (pose[0]-10494)**2+(pose[1]+6517)**2<3000**2) or label.startswith('HM_PreviewRouteFill_Mission01_Boss'):
            print(label,pose[:6])


def source():
    paths=[ROOT/'Content/_Art/Player/Environment/Rendering/Metadata/LookRestoration_20261002/SourceManifest.json']
    for path in paths:
        j=json.loads(path.read_text(encoding='utf-8-sig'))
        if 'HeinMach' not in j:continue
        print('manifest',str(path))
        for name,row in j['HeinMach'].items():
            if not isinstance(row,dict) or 'components' not in row:continue
            c=row['components'];fog=c['fog']['properties']
            print(name,{k:v for k,v in fog.items() if any(x in k for x in ('Color','Emissive','Density','Distance','Opacity'))})


def motion():
    import numpy as np
    from PIL import Image,ImageDraw
    base=STAGE/'Saved/ImportReports/HeinMachReference_20261006/motion'
    report=json.loads((base/'MotionVerification.json').read_text())
    assert 'error' not in report
    names=[row['name'] for row in report['variants']]
    examples=['010.png','026.png','046.png','stop_002.png','stop_024.png']
    canvas=Image.new('RGB',(4*320,len(examples)*330+36),(30,30,30))
    draw=ImageDraw.Draw(canvas)
    for col,name in enumerate(names):draw.text((col*320+8,8),name,fill='white')
    for row,example in enumerate(examples):
        # Wide enough for every controlled lateral position. Analysis crop only.
        for col,name in enumerate(names):
            crop=Image.open(base/name/example).crop((570,345,890,655))
            canvas.paste(crop,(col*320,row*330+36))
            draw.text((col*320+8,row*330+349),example,fill='white')
    canvas.save(OUT/'MotionComparison.jpg',quality=94)
    rows=[]
    for name in names:
        early=np.asarray(Image.open(base/name/'stop_002.png').convert('RGB'),dtype=np.float32)
        late=np.asarray(Image.open(base/name/'stop_024.png').convert('RGB'),dtype=np.float32)
        delta=np.abs(early[345:655,570:890]-late[345:655,570:890])
        rows.append({'variant':name,'stop_2_to_24_crop_mean_abs_display_channel_delta':float(delta.mean()),
                     'boundary':'Includes Lumen/shadow noise and AA differences; not a pure ghosting score.'})
    (OUT/'MotionImageAnalysis.json').write_text(json.dumps({'frames_per_variant':[len(v['frames']) for v in report['variants']],
        'samples':rows,'comparison':str(OUT/'MotionComparison.jpg')},indent=2)+'\n')
    print(json.dumps(rows,indent=2))


def performance():
    import numpy as np
    capture=json.loads((STAGE/'Saved/ImportReports/HeinMachReference_20261006/PerformanceCapture.json').read_text())
    assert 'error' not in capture
    metrics=('FrameTime','GPUTime','GPU/NiagaraGPUSimulation','GPU/Translucency','GPU/TemporalSuperResolution')
    result={'conditions':capture,'variants':[],'timing_unit':'milliseconds',
            'boundary':'Sequential 200-frame Development offscreen sample with another editor open; not a shipping FPS guarantee.'}
    for row in capture['variants']:
        with open(row['csv'],newline='',encoding='utf-8-sig') as stream:
            data=list(csv.DictReader(stream))
        summary={'name':row['name'],'particles':row.get('particles'),'metrics':{}}
        for metric in metrics:
            values=[]
            for item in data:
                try:values.append(float(item[metric]))
                except (ValueError,KeyError,TypeError):pass
            if not values:
                assert row['name']=='NoSnow' and metric=='GPU/NiagaraGPUSimulation'
                summary['metrics'][metric]={'frames':0,'status':'No active snow system; GPU stat not emitted'}
                continue
            summary['metrics'][metric]={'frames':len(values),'median':float(np.median(values)),
                                       'p95':float(np.percentile(values,95))}
        result['variants'].append(summary)
    (OUT/'PerformanceVerification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['variants'],indent=2))


def comparisons():
    from PIL import Image,ImageDraw,ImageFont
    font=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',22)
    small=ImageFont.truetype('C:/Windows/Fonts/malgun.ttf',17)
    before=STAGE/'Saved/ImportReports/HeinMachReference_20261006/baseline'
    after=OUT/'final'
    views=['Player','Entry','ReferenceStart','OpenSky']
    canvas=Image.new('RGB',(1280,4*402+54),(23,26,31))
    draw=ImageDraw.Draw(canvas)
    draw.text((12,12),'수정 전 · 같은 프로젝트 / 같은 카메라',font=font,fill='white')
    draw.text((652,12),'수정 후 · 메인 프로젝트 저장본',font=font,fill='white')
    for row,name in enumerate(views):
        y=54+row*402
        for col,base in enumerate((before,after)):
            im=Image.open(base/(name+'.png')).convert('RGB')
            assert im.size==(1280,720)
            canvas.paste(im.resize((640,360),Image.Resampling.LANCZOS),(col*640,y))
            draw.text((col*640+12,y+366),name+' · 1280×720 원본의 축소 보기',font=small,fill='white')
    canvas.save(OUT/'BeforeAfter.jpg',quality=95)
    # Source photos are retained as supplied. Different viewpoints/builds are
    # explicitly labelled; these are visual references, not pixel-match scores.
    files=[ROOT/'Docs/Art'/name for name in
           ('HeinMach 원작.jpg','HeinMach원작.jpg','HeinMach 원작 (2).jpg',
            'HeinMach 원작.png','HeinMach 원작 보스 전장.jpg')]
    refs=Image.new('RGB',(1280,3*404+64),(23,26,31));draw=ImageDraw.Draw(refs)
    draw.text((12,12),'사용자 원작 사진 5장 · 위치/카메라/버전 차이 있음',font=font,fill='white')
    for i,path in enumerate(files):
        im=Image.open(path).convert('RGB');im.thumbnail((640,360),Image.Resampling.LANCZOS)
        x=(i%2)*640;y=64+(i//2)*404
        refs.paste(im,(x+(640-im.width)//2,y))
        draw.text((x+12,y+366),path.name,font=small,fill='white')
    refs.save(OUT/'OriginalReferences.jpg',quality=95)
    print(json.dumps({'before_after':str(OUT/'BeforeAfter.jpg'),'references':str(OUT/'OriginalReferences.jpg')}))


if __name__=='__main__':
    {'baseline':baseline,'photos':photos,'locations':locations,'source':source,'motion':motion,
     'performance':performance,'comparisons':comparisons}[sys.argv[1]]()
