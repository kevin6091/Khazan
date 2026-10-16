from pathlib import Path
import os,subprocess,json,time,hashlib,shutil
m=Path(__file__).resolve().parents[2];o=m/'Metadata/GiantHitOverlay_20261013/MainObjectsLink10';assert not o.exists();o.mkdir()
rsp=next((m/'Intermediate/Build/Win64').rglob('UnrealEditor-Khazan.dll.rsp'));text=rsp.read_text(encoding='utf-8-sig');dest=o/'UnrealEditor-KhazanGiantHitFinal420261013.dll';pdb=dest.with_suffix('.pdb');new=[]
for line in text.splitlines():
 if line.startswith('/OUT:'):line='/OUT:"'+str(dest).replace('\\','/')+'"'
 elif line.startswith('/PDB:'):line='/PDB:"'+str(pdb).replace('\\','/')+'"'
 elif line.startswith('/IMPLIB:'):line='/IMPLIB:"'+str(dest.with_suffix('.lib')).replace('\\','/')+'"'
 new.append(line)
# Do not trigger an editor reload: this independent link writes outside watched Binaries.
response=o/'MainObjects.rsp';response.write_text('\n'.join(new)+'\n',encoding='utf-8')
link=Path('C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/link.exe');cmd=[str(link),'@'+str(response)]
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
start=time.monotonic()
with (o/'stdout.txt').open('w',encoding='utf-8') as log:
 p=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT,cwd="C:/Program Files/Epic Games/UE_5.8/Engine/Source",startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.BELOW_NORMAL_PRIORITY_CLASS)
 (o/'Launch.json').write_text(json.dumps(dict(pid=p.pid,command=cmd,source_response=str(rsp),reason='Default Main DLL mapped by another task. Only output/PDB names changed; exact stock Main object/link inputs retained, no editor reload.'),indent=2),encoding='utf-8');print('OWNED_MAIN_OBJECT_LINK',p.pid,flush=True);rc=p.wait()
receipt=dict(exit=rc,seconds=time.monotonic()-start,dll=str(dest),sha256=hashlib.sha256(dest.read_bytes()).hexdigest() if rc==0 else None)
(o/'Exit.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print(json.dumps(receipt),flush=True)
assert rc==0
w=m.parent.parent/'Khazan_GiantHitOverlayWork_20261013/Khazan';binary=w/'Binaries/Win64'/dest.name;assert not binary.exists();shutil.copy2(dest,binary)
manifest=json.loads((w/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'));manifest['Modules']['Khazan']=binary.name;(w/'Binaries/Win64/UnrealEditor.modules').write_text(json.dumps(manifest,indent=2),encoding='utf-8')