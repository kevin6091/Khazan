from pathlib import Path
import hashlib,json,datetime,sys
main=Path(__file__).resolve().parents[2]; out=main/'Metadata/CombatReaction_20261008'
work=main.parent.parent/'Khazan_MonsterWork_20261006/Khazan'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
values={p.relative_to(work).as_posix():sha(p) for directory in ['Source','Config'] for p in sorted((work/directory).rglob('*')) if p.is_file()}
target=out/sys.argv[1]
assert not target.exists(), 'Preserve existing source evidence'
result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),work=str(work),source_config=values,
    selected_module=json.loads((work/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig')),
    dll_sha256=sha(work/'Binaries/Win64/UnrealEditor-Khazan.dll'))
target.write_text(json.dumps(result,indent=2),encoding='utf8')
print('Source snapshot:',len(values),target.name)
