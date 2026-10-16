"""Receive the current main map into the private snow workspace; never deliver an old map."""
from pathlib import Path
import json
import shutil
import datetime
import heinmach_snow_stage as stage

snapshot=stage.OUT/'Resume20261007'
snapshot.mkdir(parents=True,exist_ok=True)
for relative in ('Content/Maps/L_HeinMach_Environment.umap',
                 'Source/Khazan/Environment/KZSnowDeformation.h',
                 'Source/Khazan/Environment/KZSnowDeformation.cpp',
                 'Source/Khazan/Tests/KZSnowDeformationPIETest.cpp'):
    source=stage.STAGE/relative
    if source.is_file():
        dest=snapshot/'BeforePrivateChanges'/relative
        if not dest.exists():
            dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
exec(compile((stage.ROOT/'Scripts/Art/heinmach_snow_intake.py').read_text(encoding='utf-8'),
             'heinmach_snow_intake.py','exec'),{'__file__':str(stage.ROOT/'Scripts/Art/heinmach_snow_intake.py')})
map_rel=Path('Content/Maps/L_HeinMach_Environment.umap')
shutil.copy2(stage.ROOT/map_rel,stage.STAGE/map_rel)
rows=[]
for rel in ('Source','Config'):
    rows += [dict(path=p.relative_to(stage.ROOT).as_posix(),sha256=stage.sha(p))
             for p in (stage.ROOT/rel).rglob('*') if p.is_file()]
rows.append(dict(path=map_rel.as_posix(),sha256=stage.sha(stage.ROOT/map_rel)))
(snapshot/'MainBaseline.json').write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    files=rows,map_received_from_current_main=True),indent=2),encoding='utf-8')
print('SNOW_LATEST_MAIN_RECEIVED',stage.sha(stage.STAGE/map_rel))
