"""Freeze timing repairs and copy only owned animation packages into the existing private workspace."""
from pathlib import Path
from fractions import Fraction
import hashlib,json,os,shutil,stat,subprocess
MAIN=Path(__file__).resolve().parents[2]
WORK=MAIN.parent.parent/'Khazan_SlamDistortWork_20261012/Khazan'
OUT=MAIN/'Metadata/AnimationTimingKnockback_20261012';OUT.mkdir(exist_ok=True)
assert not (OUT/'Baseline.json').exists(),'Preserve the previous repair baseline'
inventory=json.loads((MAIN/'Metadata/PlayerSlamDistort_20261012/FPSInventory01/Inventory.json').read_text(encoding='utf-8'))
assert inventory['success']
shutil.copyfile(MAIN/'Metadata/PlayerSlamDistort_20261012/FPSInventory01/Inventory.json',OUT/'InventoryBefore.json')
seq=[]
for row in inventory['sequences']:
    fps=Fraction(*row['fps'])
    if fps.denominator==1:continue
    # Existing source-composite bake uses a nominal 60Hz clock; raw source tracks use 30Hz.
    # Choose the closer of these compatible clock grids, not a gameplay speed.
    target=min([30,60],key=lambda rate:abs(float(fps)-rate))
    new_duration=row['frames']/target;factor=new_duration/row['seconds']
    seq.append(dict(row,target_fps=target,time_scale=factor,new_seconds=new_duration,new_rate_scale=row['rate_scale']*factor))
by={s['asset']:s for s in seq}
montages=[c for c in inventory['composites'] if any(s['asset'] in by for s in c['segments'])]
files={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def writable(rel):
    assert rel.startswith('Content/') and '..' not in Path(rel).parts
    cursor=WORK
    for part in Path(rel).parts:
        cursor=cursor/part
        assert cursor.absolute().is_relative_to(WORK.absolute())
        if cursor.exists() and cursor.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            target=cursor.resolve();assert target.is_relative_to(MAIN/'Content'),target
            children=list(target.iterdir());os.rmdir(cursor);cursor.mkdir()
            for child in children:
                dest=cursor/child.name
                if child.is_dir():
                    startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
                    cmd=['powershell.exe','-NoProfile','-Command','New-Item -ItemType Junction -Path "'+str(dest)+'" -Target "'+str(child)+'" | Out-Null']
                    subprocess.run(cmd,check=True,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=startup)
                else:shutil.copy2(child,dest)
        elif not cursor.exists():cursor.mkdir()
paths=[s['asset'] for s in seq]+[m['asset'] for m in montages]
for path in paths:
    rel='Content/'+path.removeprefix('/Game/')+'.uasset'
    files[rel]=sha(MAIN/rel)
    dest=OUT/'Before'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(MAIN/rel,dest)
    writable(str(Path(rel).parent).replace('\\','/'))
    shutil.copyfile(MAIN/rel,WORK/rel)
for folder in ['Source','Config']:
    for p in (MAIN/folder).rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(MAIN).as_posix();files[rel]=sha(p)
        d=OUT/'Before'/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d)
        d=WORK/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,d)
(OUT/'Plan.json').write_text(json.dumps({'sequences':seq,'montages':montages,
  'contract':'same frame-index bone keys; integer nominal clock; RateScale multiplied by new/old duration; local sequence notify/marker times and montage source trim coordinates scaled; montage world event/section/segment times unchanged',
  'source_policy':'60Hz CompositeBake TimePerFrame vs 30Hz original samples; original numeric motion preserved through a calculated RateScale correction'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'Baseline.json').write_text(json.dumps({'main':str(MAIN),'work':str(WORK),'files':files,'plan_sha256':sha(OUT/'Plan.json')},indent=2)+'\n',encoding='utf-8')
print('TIMING_REPAIR_STAGED',len(seq),len(montages),len(files),flush=True)
