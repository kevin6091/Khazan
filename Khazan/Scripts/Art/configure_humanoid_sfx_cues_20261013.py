from pathlib import Path
import json
import os
import unreal as u
ROOT=Path(os.environ['KZ_AUDIO_MAIN']);OUT=ROOT/'Metadata/HumanoidSFX_20261013';RUN=Path(os.environ['KZ_AUDIO_OUTPUT'])
plan=json.loads((OUT/'SpatialAudioPlan01.json').read_text(encoding='utf-8-sig'))
u.SystemLibrary.execute_console_command(None,'KZ.Audio.ApplySpatialPlan "'+str(OUT/'SpatialAudioPlan01.json')+'"')
rows=[]
names=set(os.environ.get('KZ_AUDIO_SPATIAL_NAMES','').split(',')) if os.environ.get('KZ_AUDIO_SPATIAL_NAMES') else None
for r in plan['cues']:
    if names and r['cue'].rsplit('/',1)[-1].removeprefix('SC_') not in names:continue
    cue=u.EditorAssetLibrary.load_asset(r['cue']);assert cue
    assert u.EditorAssetLibrary.save_loaded_asset(cue,only_if_is_dirty=False)
    rows.append({'asset':r['cue'],'radius':cue.get_editor_property('max_distance'),'source':r['max_distance_cm']})
(RUN/'Spatial.json').write_text(json.dumps({'success':True,'cues':rows},indent=2),encoding='utf-8')
