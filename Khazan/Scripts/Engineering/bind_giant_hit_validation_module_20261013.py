from pathlib import Path
import json,hashlib,shutil
m=Path(__file__).resolve().parents[2];w=m.parent.parent/'Khazan_GiantHitOverlayWork_20261013/Khazan';o=m/'Metadata/GiantHitOverlay_20261013'
manifest=json.loads((m/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'));src=m/'Binaries/Win64'/manifest['Modules']['Khazan'];dst=w/'Binaries/Win64/UnrealEditor-KhazanGiantHitValidation20261013.dll';assert not dst.exists();shutil.copy2(src,dst);manifest['Modules']['Khazan']=dst.name;(w/'Binaries/Win64/UnrealEditor.modules').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
shutil.copytree(m/'Source',w/'Source',dirs_exist_ok=True)
(o/'ValidationModule.json').write_text(json.dumps(dict(main_module=str(src),work_module=str(dst),sha256=hashlib.sha256(src.read_bytes()).hexdigest()),indent=2),encoding='utf-8')
print('Fresh validated Source/DLL',src.name)