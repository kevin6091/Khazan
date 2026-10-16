from pathlib import Path
import json
import os
import unreal as u
ROOT=Path(os.environ['KZ_AUDIO_MAIN']);OUT=ROOT/'Saved/ImportReports/GameplayAudio_20261011';RUN=Path(os.environ['KZ_AUDIO_OUTPUT'])
plan=json.loads((OUT/'BindingAuthor02_Persistent/Bindings.json').read_text(encoding='utf-8-sig'))
rows=[]
for r in plan['combos']:
    obj=u.EditorAssetLibrary.load_asset(r['asset']);objects=obj.get_editor_property('pattern_objects')
    rows.append({'asset':r['asset'],'objects':[o.export_text() for o in objects],
                 'windows':[w.export_text() for n in obj.get_editor_property('nodes') for w in n.get_editor_property('attack_windows')]})
(RUN/'Readback.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
