"""Decode each distinct source/trim once, original gain stays in native cue."""
from concurrent.futures import ThreadPoolExecutor,as_completed
from collections import Counter
from pathlib import Path
import array
import hashlib
import json
import re
import subprocess
import wave
import os
from prepare_gameplay_audio_scope import OUT,EXTRACT,read

OUT=Path(os.environ.get('KZ_AUDIO_DATA_ROOT',str(OUT)))
EXTRACT=Path(os.environ.get('KZ_AUDIO_DATA_ROOT',str(EXTRACT)))
plan=read(os.environ.get('KZ_AUDIO_CUE_PLAN') or OUT/'NativeCuePlan01.json')
dest=EXTRACT/'NativeDecoded01';dest.mkdir(exist_ok=True)
recipes=OUT/'NativeLeafRecipes01';recipes.mkdir(exist_ok=True)
vgm='C:/Users/user/Downloads/63a7cbccd9fbaae9db45240069a49bd6a3a00b73/Output/.data/vgmstream-cli.exe'
def decode(row):
    p=recipes/(row['key']+'.txtp');p.write_text(row['media']+' '+row['commands']+'\n',encoding='utf-8')
    wav=Path(row['wave_file'])
    meta=subprocess.run([vgm,'-m',row['media']],capture_output=True).stdout.decode(errors='replace')
    args=[vgm,'-i','-o',str(wav),str(p)]
    proc=subprocess.run(args,capture_output=True) if not wav.exists() else None
    result=dict(row,decode_args=args,source_sha256=hashlib.sha256(Path(row['media']).read_bytes()).hexdigest() if Path(row['media']).exists() else '',source_metadata=meta)
    if proc and proc.returncode!=0:return dict(result,status='failed',error=proc.stdout.decode(errors='replace'))
    with wave.open(str(wav),'rb') as f:
        result.update(channels=f.getnchannels(),sample_rate=f.getframerate(),frames=f.getnframes(),sample_bytes=f.getsampwidth(),seconds=f.getnframes()/f.getframerate())
        data=f.readframes(f.getnframes())
    samples=array.array('h',data)
    result.update(status='decoded',wave_sha256=hashlib.sha256(wav.read_bytes()).hexdigest(),peak=max((abs(x) for x in samples),default=0)/32768,clipped_samples=sum(abs(x)>=32767 for x in samples))
    if row['needed_loop']:
        start=re.search(r'loop start: (\d+)',meta);end=re.search(r'loop end: (\d+)',meta)
        result['loop_start']=int(start[1]) if start else 0;result['loop_end']=int(end[1]) if end else result['frames']
        if result['loop_start']!=0 or result['loop_end']!=result['frames']:
            parts=[];align=result['channels']*result['sample_bytes']
            for label,a,b in (('Intro',0,result['loop_start']),('Loop',result['loop_start'],result['loop_end'])):
                if a==b:continue
                path=wav.with_stem(wav.stem+'_'+label)
                with wave.open(str(path),'wb') as f:
                    f.setnchannels(result['channels']);f.setsampwidth(result['sample_bytes']);f.setframerate(result['sample_rate']);f.writeframes(data[a*align:b*align])
                parts.append({'kind':label,'asset':row['asset']+'_'+label,'wave_file':str(path),'start_frame':a,'end_frame':b,'wave_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
            result['loop_parts']=parts
    return result
rows=[]
with ThreadPoolExecutor(max_workers=4) as pool:
    futures=[pool.submit(decode,r) for r in plan['waves']]
    for i,future in enumerate(as_completed(futures),1):
        rows.append(future.result())
        if i%150==0:print('NATIVE DECODE',i,'/',len(futures),flush=True)
(OUT/'NativeDecodedManifest01.json').write_text(json.dumps(sorted(rows,key=lambda r:r['key']),ensure_ascii=False,indent=2),encoding='utf-8')
print('NATIVE DECODE COMPLETE',Counter(r['status'] for r in rows),'source clipped samples',sum(r.get('clipped_samples',0) for r in rows),'split loop media',sum('loop_parts' in r for r in rows),flush=True)
assert all(r['status']=='decoded' for r in rows)
