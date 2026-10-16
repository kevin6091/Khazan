"""Create the explicitly isolated Player Original-parts project snapshot."""
import json
import os
import pathlib
import shutil
import datetime

MAIN = pathlib.Path(__file__).resolve().parents[2]
WORK = MAIN.parents[1] / 'Khazan_PlayerPartsWork_20261007' / 'Khazan'
REPORT = MAIN / 'Metadata/PlayerParts_20261007'
REPORT.mkdir(parents=True, exist_ok=True)
if WORK.exists():
    raise RuntimeError('Work project already exists; inspect rather than overwrite it')
WORK.mkdir(parents=True)
for name in ('Khazan.uproject',):
    shutil.copy2(MAIN / name, WORK / name)
for name in ('Source', 'Config', 'Plugins', 'Binaries'):
    shutil.copytree(MAIN / name, WORK / name, dirs_exist_ok=True)
linked = copied = 0
for src in (MAIN / 'Content').rglob('*'):
    if not src.is_file():
        continue
    relative = src.relative_to(MAIN)
    dst = WORK / relative
    dst.parent.mkdir(parents=True, exist_ok=True)
    # All possible edited existing assets are independent copies. Other content
    # is a read-only snapshot: only explicitly named packages may be saved.
    if str(relative).replace('\\', '/').startswith('Content/_Art/Player/Character/'):
        shutil.copy2(src, dst)
        copied += 1
    else:
        os.link(src, dst)
        linked += 1
report = dict(main=str(MAIN), work=str(WORK), utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              independent_player_character_files=copied, readonly_content_hardlinks=linked,
              runtime_source_changes=False, editor_process_reused=False)
(REPORT / 'WorkSnapshot.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
