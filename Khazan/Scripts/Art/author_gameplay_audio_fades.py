"""Targeted original play fade authoring and dependent ambient wrapper refresh."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import traceback
import unreal as u

ROOT=Path(os.environ['KZ_AUDIO_MAIN']);OUT=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
RUN=Path(os.environ['KZ_AUDIO_OUTPUT']);lib=u.EditorAssetLibrary
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
plan=read(OUT/'SourcePlayFadePlan01.json');paths=sorted({r['cue'] for r in plan['fades']})
wrappers=read(OUT/'BindingAuthor02_Persistent/Bindings.json')['wrappers']
dependent=[w for w in wrappers if w['source'] in paths]
report={'success':False,'cues':paths,'wrappers':dependent,'fades':plan['fades'],'errors':[]}
try:
    for path in paths+[w['target'] for w in dependent]:
        file=ROOT/'Content'/(path[6:]+'.uasset');backup=OUT/'BeforeAudioFades'/file.relative_to(ROOT)
        if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,backup)
    u.SystemLibrary.execute_console_command(None,'KZ.Audio.ApplyPlayFades "'+str(OUT/'SourcePlayFadePlan01.json')+'"')
    for row in plan['fades']:
        obj=lib.load_asset(row['cue']);pending=[obj.get_editor_property('first_node')];seen=set();found=False
        while pending:
            node=pending.pop()
            if not node or node in seen:continue
            seen.add(node)
            if node.get_name().startswith('KZAOriginalPlayFade_Target'+row['target']):found=True
            pending.extend(node.get_editor_property('child_nodes'))
        assert found,(row['cue'],row['target'])
    if dependent:
        file=RUN/'Wrappers.json';file.write_text(json.dumps({'wrappers':dependent}),encoding='utf-8')
        u.SystemLibrary.execute_console_command(None,'KZ.Audio.BuildAmbientWrappers "'+str(file)+'"')
    paths += [w['target'] for w in dependent]
    file=RUN/'Finalize.json';file.write_text(json.dumps({'cue_paths':paths}),encoding='utf-8')
    u.SystemLibrary.execute_console_command(None,'KZ.Audio.FinalizeCues "'+str(file)+'"')
    for path in paths:
        obj=lib.load_asset(path);assert obj
        lib.set_metadata_tag(obj,'OriginalPlayFadeSource','SourcePlayFadePlan01; source CAkActionPlay TransitionTime ms/1000 and target media closure; Linear exact; Log1/Exp1 temporary native shape adapter')
        assert lib.save_loaded_asset(obj,only_if_is_dirty=False)
    report['success']=True
except Exception:report['errors'].append(traceback.format_exc());u.log_error(report['errors'][-1])
(RUN/'Fades.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert report['success'],report['errors']
