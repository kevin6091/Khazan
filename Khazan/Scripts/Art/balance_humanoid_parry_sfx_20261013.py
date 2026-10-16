"""One measured TEMP mix adjustment, preserving the source cue graph."""
from pathlib import Path
import json
import os
import unreal as u

ROOT=Path(os.environ['KZ_AUDIO_MAIN']);RUN=Path(os.environ['KZ_AUDIO_OUTPUT'])
cue=u.EditorAssetLibrary.load_asset('/Game/Audio/Original/Events/SC_Play_PLYR_DualAxeSword_JustGuard_Suc');assert cue
before=cue.get_editor_property('volume_multiplier')
# TEMP -6.02dB cue trim: actual consecutive-parry capture peaked at .999847.
# Keep Wwise leaf gains, random choices and media tails unchanged.
cue.set_editor_property('volume_multiplier',.5)
saved=u.EditorAssetLibrary.save_loaded_asset(cue,only_if_is_dirty=False)
(RUN/'Balance.json').write_text(json.dumps({'success':saved,'cue':cue.get_path_name(),'before':before,'after':.5,
    'numeric_source':'Assistant TEMP measured headroom trim; MainParry02 peak .999847412109375, zero clipped samples. Recheck same actual parry fixture.',
    'source_graph_modified':False},indent=2),encoding='utf-8')
assert saved
