"""Use the existing real game viewport scene capture, with this task's receipts."""
from pathlib import Path
import os
main=Path(os.environ['KZ_HM_COLOUR_MAIN'])
os.environ.update(KZ_LOOK_OUT=os.environ['KZ_HM_COLOUR_OUT'],KZ_LOOK_MAIN=str(main),
                  KZ_LOOK_LEVEL=os.environ.get('KZ_HM_COLOUR_LEVEL','HeinMach'),KZ_LOOK_MODE='capture')
source=(main/'Scripts/Art/scene_look_capture_20261012.py').read_text(encoding='utf-8')
exec(compile(source,__file__,'exec'),globals())
if os.environ.get('KZ_HM_COLOUR_VIEWS'):
    requested=set(os.environ['KZ_HM_COLOUR_VIEWS'].split(','))
    VIEWS=[view for view in VIEWS if view[0] in requested]
    assert VIEWS,requested
