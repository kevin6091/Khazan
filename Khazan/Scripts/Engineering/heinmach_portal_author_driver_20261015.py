"""Warm the real editor world's collision scene before targeted placement."""
from pathlib import Path
import json, os, time, traceback, unreal as u

out = Path(os.environ['KZ_PORTAL_OUT'])
assert u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/Maps/L_HeinMach_Environment')
start = time.monotonic()
done = False

def tick(delta):
    global done
    if done or time.monotonic() - start < 5:
        return
    done = True
    u.unregister_slate_post_tick_callback(handle)
    try:
        script = Path(u.Paths.project_dir()).resolve() / 'Scripts/Engineering' / os.environ.get('KZ_PORTAL_AUTHOR_SCRIPT', 'place_heinmach_portal_20261015.py')
        exec(compile(script.read_text(encoding='utf-8'), str(script), 'exec'), globals())
    except Exception:
        (out / 'AuthorError.json').write_text(json.dumps(dict(error=traceback.format_exc()), indent=2), encoding='utf-8')
    finally:
        u.SystemLibrary.quit_editor()

handle = u.register_slate_post_tick_callback(tick)
