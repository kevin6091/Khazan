"""Summarize saved fire CSVs and original atlas channels; no asset changes."""
from pathlib import Path
import csv
import json
import math
import statistics
import struct
import zlib

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Saved/ImportReports/HeinMachTutorialFires_20261006'
capture=json.loads((OUT/'PerformanceCapture.json').read_text())
assert capture['passed'],'Profiling callback failed; do not summarize stale CSV files'
results=[]
for variant in capture['variants']:
    path=Path(variant['csv']);rows=list(csv.reader(path.open(encoding='utf-8-sig',newline='')))
    header=rows[-2] if rows[-2][0]=='EVENTS' else rows[0]
    samples=[]
    for row in rows[1:]:
        if not row or row[0]=='EVENTS' or len(row)>len(header):continue
        try:samples.append([float(v or 0) for v in row[1:]]+[0.]*(len(header)-len(row)))
        except ValueError:continue
    assert len(samples)>=200,(variant['name'],len(samples))
    stats={}
    for i,key in enumerate(header[1:]):
        if key.startswith('GPU/') or key in ('FrameTime','Exclusive/GameThread/Effects') or key.startswith('Particles/GameThread/'):
            xs=[s[i] for s in samples]
            stats[key]={'median_ms':statistics.median(xs),'p95_ms':sorted(xs)[math.ceil(len(xs)*.95)-1]}
    md=dict(zip(rows[-1][::2],rows[-1][1::2]))
    results.append({'name':variant['name'],'samples':len(samples),'live_particles':variant['live_particles'],'timings':stats,
                    'hardware':{k:md.get('['+k+']') for k in ('cpu','gpu','rhiname','rhifeaturelevel','config','systemresolution.resx','systemresolution.resy')}})
off=results[1]['timings'];diff={}
for key in off:
    if key in results[0]['timings'] and key in results[2]['timings']:
        diff[key]=statistics.fmean(r['timings'][key]['median_ms'] for r in (results[0],results[2]))-off[key]['median_ms']
report={'variants':results,'on_average_minus_off_median_ms':diff,'limits':capture['limits'],'units':'milliseconds',
        'gpu_cost_conclusive':False,
        'interpretation':'The user editor shares the GPU with this sequential probe. Large changes in unchanged shadow/base/TSR passes prevent an aggregate GPU cost conclusion; negative differences do not indicate a performance improvement. Game-thread differences are observations under these capture conditions.'}
(OUT/'PerformanceVerification.json').write_text(json.dumps(report,indent=2)+'\n')

def extrema(path):
    data=path.read_bytes();assert data[:8]==b'\x89PNG\r\n\x1a\n'
    pos=8;compressed=bytearray()
    while pos<len(data):
        size=struct.unpack_from('>I',data,pos)[0];kind=data[pos+4:pos+8];payload=data[pos+8:pos+8+size];pos+=size+12
        if kind==b'IHDR':w,h,depth,color,_,_,interlace=struct.unpack('>IIBBBBB',payload)
        elif kind==b'IDAT':compressed+=payload
    assert depth==8 and color in (2,6) and interlace==0,(depth,color,interlace)
    bpp=4 if color==6 else 3;stride=w*bpp;raw=zlib.decompress(compressed);previous=bytearray(stride);lo=[255]*4;hi=[0]*4
    for y in range(h):
        base=y*(stride+1);mode=raw[base];row=bytearray(raw[base+1:base+1+stride])
        for i in range(stride):
            a=row[i-bpp] if i>=bpp else 0;b=previous[i];c=previous[i-bpp] if i>=bpp else 0
            if mode==1:row[i]=(row[i]+a)&255
            elif mode==2:row[i]=(row[i]+b)&255
            elif mode==3:row[i]=(row[i]+((a+b)//2))&255
            elif mode==4:
                p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
                row[i]=(row[i]+(a if pa<=pb and pa<=pc else b if pb<=pc else c))&255
            else:assert mode==0
        for ch in range(bpp):
            values=row[ch::bpp];lo[ch]=min(lo[ch],min(values));hi[ch]=max(hi[ch],max(values))
        previous=row
    if bpp==3:lo[3]=hi[3]=255
    return dict(zip('RGBA',zip(lo,hi)))

channels=[]
for name,rel in [('FTW_Subuv_Smoke_007','World/FTW_Subuv_Smoke_007.png'),('T_Smoke03_SubUV_9x9','SubUV/T_Smoke03_SubUV_9x9.png')]:
    p=ROOT/'Saved/Extracted/CombatEffects_20261006/Payload/BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/BBQ_Texture'/rel
    channels.append({'name':name,'original_payload':str(p.relative_to(ROOT)).replace('\\','/'),'source_pixel_format':'PF_DXT1','extrema':extrema(p),
                     'native_recovery':'R grayscale smoke density; A is constantly opaque, so A-only creates visible sprite rectangles.'})
(OUT/'SmokeChannelEvidence.json').write_text(json.dumps(channels,indent=2)+'\n')
print(json.dumps({'samples':[r['samples'] for r in results],'gpu_differences_ms':{k:v for k,v in diff.items() if k in ('GPU/Total','GPU/Translucency','GPU/Lights','GPU/ShadowDepths','Exclusive/GameThread/Effects')},'smoke_channels':channels},indent=2))
