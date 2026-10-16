"""Intake completed concurrent work into the private snow project, preserving snow edits."""
from pathlib import Path
import hashlib
import json
import shutil
import re
import heinmach_snow_stage as stage

assert not any(stage.STAGE.glob('Saved/SnowMailbox/*.running'))
before=[]
for path in (stage.STAGE/'Source').rglob('*'):
    if path.is_file():before.append(dict(path=path.relative_to(stage.STAGE).as_posix(),sha256=stage.sha(path)))
for name in ('Source','Config'):
    shutil.copytree(stage.ROOT/name,stage.STAGE/name,dirs_exist_ok=True)
shutil.copy2(stage.ROOT/'Khazan.uproject',stage.STAGE/'Khazan.uproject')
build=stage.STAGE/'Source/Khazan/Khazan.Build.cs'
text=build.read_text(encoding='utf-8-sig')
if '"RHI"' not in text:
    text=re.sub(r'(PrivateDependencyModuleNames.AddRange\(new string\[\] \{\s*)(\}\);)',
                r'\1"RHI" \2',text,count=1)
assert '"RHI"' in text
build.write_text(text,encoding='utf-8')
config=stage.STAGE/'Config/DefaultEngine.ini'
text=config.read_text(encoding='utf-8-sig')
if 'r.Nanite.AllowTessellation=1' not in text:text+='\n[SystemSettings]\nr.Nanite.AllowTessellation=1\nr.Nanite.Tessellation=1\n'
config.write_text(text,encoding='utf-8')
for child in (stage.ROOT/'Content').iterdir():
    if child.is_dir() and not (stage.STAGE/'Content'/child.name).exists():
        stage.content_tree(child,stage.STAGE/'Content'/child.name,child.name)
(stage.OUT/'CompletedWorkIntake.json').write_text(json.dumps(dict(before=before,
    main_source=[dict(path=p.relative_to(stage.ROOT).as_posix(),sha256=stage.sha(p))
        for p in (stage.ROOT/'Source').rglob('*') if p.is_file()],
    main_map_sha256=stage.sha(stage.ROOT/'Content/Maps/L_HeinMach_Environment.umap')),indent=2),encoding='utf-8')
print('Latest main Source/Config/new Content roots received; private snow sources retained')
