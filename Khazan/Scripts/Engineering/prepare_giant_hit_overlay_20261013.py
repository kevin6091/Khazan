from pathlib import Path
import os, json, shutil, hashlib, subprocess, datetime
M=Path(__file__).resolve().parents[2]; W=M.parent.parent/'Khazan_GiantHitOverlayWork_20261013/Khazan'; O=M/'Metadata/GiantHitOverlay_20261013'
assert not W.exists(); O.mkdir(parents=True,exist_ok=True); W.mkdir(parents=True)
for folder in ('Source','Config'):shutil.copytree(M/folder,W/folder)
shutil.copy2(M/'Khazan.uproject',W/'Khazan.uproject')
env=dict(os.environ,KZ_JUNCTION_PATH=str(W/'Plugins'),KZ_JUNCTION_TARGET=str(M/'Plugins'))
r=subprocess.run(['powershell.exe','-NoProfile','-Command','New-Item -ItemType Junction -Path $env:KZ_JUNCTION_PATH -Target $env:KZ_JUNCTION_TARGET | Out-Null'],env=env,capture_output=True);assert r.returncode==0
count=0
for root,dirs,files in os.walk(M/'Content'):
 dst=W/Path(root).relative_to(M);dst.mkdir(parents=True,exist_ok=True)
 for f in files:
  os.link(Path(root)/f,dst/f);count+=1
manifest=json.loads((M/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'));src=M/'Binaries/Win64'/manifest['Modules']['Khazan']; dst=W/'Binaries/Win64';dst.mkdir(parents=True)
alias='UnrealEditor-KhazanGiantHitBaseline20261013.dll';shutil.copy2(src,dst/alias);manifest['Modules']['Khazan']=alias
(dst/'UnrealEditor.modules').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
receipt=dict(main=str(M),work=str(W),hardlinked_content_files=count,baseline_module=str(src),baseline_module_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
(O/'Baseline.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
(O/'ResumeState.json').write_text(json.dumps(dict(status='investigating',remaining=['source metadata conditions','additive source configuration and independent slot','runtime minimal route','fresh native/visual verification','Main merge and documentation']),indent=2),encoding='utf-8')
print(json.dumps(receipt))