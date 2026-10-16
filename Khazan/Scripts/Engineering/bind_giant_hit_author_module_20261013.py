from pathlib import Path
import json,hashlib,shutil
m=Path(__file__).resolve().parents[2];w=m.parent.parent/'Khazan_GiantHitOverlayWork_20261013/Khazan';o=m/'Metadata/GiantHitOverlay_20261013'
manifest=json.loads((m/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'));src=m/'Binaries/Win64'/manifest['Modules']['Khazan'];alias='UnrealEditor-KhazanGiantHitAuthor20261013.dll';dst=w/'Binaries/Win64'/alias;assert not dst.exists();shutil.copy2(src,dst);manifest['Modules']['Khazan']=alias;(w/'Binaries/Win64/UnrealEditor.modules').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(o/'AuthorModule.json').write_text(json.dumps(dict(main_module=str(src),work_module=str(dst),sha256=hashlib.sha256(src.read_bytes()).hexdigest()),indent=2),encoding='utf-8')
print('Fresh Main DLL -> isolated author project:',src.name)