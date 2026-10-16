import datetime, hashlib, json, pathlib, shutil
MAIN = pathlib.Path(__file__).resolve().parents[2]
WORK = MAIN.parent.parent / 'Khazan_MonsterWork_20261006' / 'Khazan'
OUT = MAIN / 'Metadata/MonsterStamina_20261008'
target = OUT / 'LatestCollisionClipIntake.json'
assert not target.exists()
mapping_path = MAIN / 'Metadata/PlayerAttackCollision_20261008/AssetAudit/CurrentNodeMapping.json'
mapping = json.loads(mapping_path.read_text(encoding='utf-8'))
packages = set()
for node in mapping['nodes']:
    packages.add(node['montage'])
    for segment in node['segments']: packages.add(segment['sequence'])
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
rows = []
for package in sorted(packages):
    assert package.startswith('/Game/_Art/Player/Animation/InGame/DAS/')
    relative = 'Content/' + package.removeprefix('/Game/') + '.uasset'
    source, destination = MAIN / relative, WORK / relative
    requested, before = sha(source), sha(destination)
    assert requested is not None
    if requested != before:
        if destination.is_file():
            backup = OUT / 'WorkBeforeLatestCollisionClips' / relative
            backup.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(destination, backup)
        destination.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, destination)
    assert sha(destination) == requested and sha(source) == requested
    rows.append(dict(relative=relative, package=package, main=requested, work_before=before, work_after=requested, copied=requested!=before))
target.write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), main_write=False,
    scope='Only current authored combo-node montage and segment references; latest Main is authoritative. No authoring or rate changes.',
    mapping_sha256=sha(mapping_path), rows=rows), indent=2), encoding='utf-8')
print(json.dumps(dict(checked=len(rows), copied=sum(r['copied'] for r in rows))))
