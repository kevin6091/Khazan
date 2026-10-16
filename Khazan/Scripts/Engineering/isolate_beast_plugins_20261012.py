"""Move only the task-owned junction; retain its link and clone reusable plugin files."""
from pathlib import Path
import json
import os
import shutil

MAIN=Path(__file__).resolve().parents[2]
WORK=MAIN.parent.parent/'Khazan_BeastDodgeWork_20261012/Khazan'
link=WORK/'Plugins'; retained=WORK/'BorrowedPluginsReadOnly'
assert WORK.name=='Khazan' and WORK.parent.name=='Khazan_BeastDodgeWork_20261012'
if not retained.exists():
    assert link.is_junction() if hasattr(link,'is_junction') else link.resolve()==MAIN/'Plugins'
    assert link.resolve()==MAIN/'Plugins'
    os.rename(link,retained) # Rename the reparse point itself, never its resolved source.
    link.mkdir()
assert retained.resolve()==MAIN/'Plugins' and link.resolve()==link
for name in ('Cog','UnrealPSKPSA'):
    source=MAIN/'Plugins'/name
    shutil.copytree(source,link/name,dirs_exist_ok=True)
receipt={'status':'isolated','work_plugins':str(link),'retained_read_only_link':str(retained),'source':str(MAIN/'Plugins')}
(MAIN/'Metadata/BeastDodge_20261012/PluginIsolation.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(json.dumps(receipt),flush=True)
