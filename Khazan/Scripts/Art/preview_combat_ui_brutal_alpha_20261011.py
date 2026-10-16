"""Review preview or actual saved alpha in the task-owned RHI editor; no Main writes."""
from pathlib import Path
import os
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
saved = os.environ.get('KZ_COMBAT_UI_ALPHA_MODE') == 'saved'
os.environ['KZ_COMBAT_UI_ALPHA_MODE'] = 'inspect' if saved else 'preview'
for relative in ['Scripts/Art/soften_combat_ui_brutal_alpha_20261011.py',
                 'Scripts/Engineering/combat_ui_pie_20261011.py']:
    source = root / relative
    exec(compile(source.read_text(encoding='utf-8'), str(source), 'exec'))
    if saved and relative.endswith('soften_combat_ui_brutal_alpha_20261011.py'):
        alpha = next(n for n in masks if n.get_editor_property('a'))
        assert [alpha.get_editor_property(c) for c in 'rgba'] == [False, False, False, True]
        assert report['edge_parameters'] == [{'name': 'EdgeSoftnessPixels', 'default': 1.25}]
