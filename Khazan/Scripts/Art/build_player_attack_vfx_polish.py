"""Use the established private build runner with new immutable task evidence."""
from pathlib import Path
import sys
MAIN = Path(__file__).resolve().parents[2]
source = MAIN / 'Scripts/Art/build_player_attack_vfx_work.py'
code = source.read_text(encoding='utf-8')
old = "OUT = ROOT / 'Saved/ImportReports/PlayerAttackVFX_20261008/Build'"
assert code.count(old) == 1
name = sys.argv[1] if len(sys.argv) > 1 else 'Build'
assert name.replace('_', '').isalnum()
destination = MAIN / 'Saved/ImportReports/PlayerAttackVFXPolish_20261008' / name
assert not destination.exists(), 'Use distinct build evidence; preserve earlier builds'
code = code.replace(old, "OUT = ROOT / 'Saved/ImportReports/PlayerAttackVFXPolish_20261008/" + name + "'")
exec(compile(code, str(source), 'exec'), dict(__name__='__main__', __file__=str(source)))
