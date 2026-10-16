"""Fresh canonical Main build using current complete Source."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,time,sys
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Metadata/MonsterRootCollisionRepair_20261012'/(sys.argv[1] if len(sys.argv)>1 else 'MainBuild01');OUT.mkdir(exist_ok=False)
assert (ROOT/'Metadata/MonsterRootCollisionRepair_20261012/Delivered.json').exists()
def sources():return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'Source/Khazan').rglob('*') if p.suffix in ['.cpp','.h','.cs']}
before=sources();cmd=['C:/Program Files/Epic Games/UE_5.8/Engine/Build/BatchFiles/Build.bat','KhazanEditor','Win64','Development',str(ROOT/'Khazan.uproject'),'-WaitMutex','-NoHotReloadFromIDE','-MaxParallelActions='+('1' if len(sys.argv)>1 else '2')]
if len(sys.argv)>1:cmd.append('-NoXGE')
(OUT/'Input.json').write_text(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'command':cmd,'source_sha256':before},indent=2),encoding='utf-8')
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0;start=time.monotonic()
with (OUT/'Build.log').open('wb') as log:
    p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW);code=p.wait()
manifest=json.loads((ROOT/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'));module=ROOT/'Binaries/Win64'/manifest['Modules']['Khazan']
(OUT/'Exit.json').write_text(json.dumps({'exit':code,'seconds':time.monotonic()-start,'input_unchanged':before==sources(),'module':str(module),'module_sha256':hashlib.sha256(module.read_bytes()).hexdigest()},indent=2),encoding='utf-8')
print('MAIN_CONTACT_BUILD',code,'input_unchanged',before==sources(),flush=True)
raise SystemExit(code)
