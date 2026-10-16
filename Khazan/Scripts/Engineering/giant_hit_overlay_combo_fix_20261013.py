from pathlib import Path
import json,hashlib
m=Path(__file__).resolve().parents[2];o=m/'Metadata/GiantHitOverlay_20261013';p=m/'Source/Khazan/Ability/Combo/KZComboActionAbility.cpp';b=p.read_bytes();s=b.decode('utf-8');assert s.count('Anim->GetCurrentActiveMontage()')==2
backup=o/'Before/Source/Khazan/Ability/Combo/KZComboActionAbility.cpp';backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(b)
s=s.replace('Anim->GetCurrentActiveMontage()','GetCurrentMontage()');assert p.read_bytes()==b;p.write_bytes(s.encode('utf-8'))
d=json.loads((o/'SourceChanges.json').read_text(encoding='utf-8'));d[p.relative_to(m).as_posix()]={'before_sha256':hashlib.sha256(b).hexdigest(),'after_sha256':hashlib.sha256(p.read_bytes()).hexdigest()};(o/'SourceChanges.json').write_text(json.dumps(d,indent=2),encoding='utf-8')