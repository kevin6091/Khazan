"""Unsaved, warmed native RHI comparison of source JustGuard and its soft halo."""
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[2]
os.environ['KZ_PARRY_MAIN'] = str(ROOT)
os.environ['KZ_PARRY_OUT'] = os.environ['KZ_PARRY_PHOTO_OUT']
script = ROOT / 'Scripts/Art/preview_player_parry_20261012.py'
code = script.read_text(encoding='utf-8').replace('PP_Player_Parry_Success', 'PP_Player_JustGuard_Halo')
code = code.replace("exec(compile(code,str(MAIN/'Scripts/Art/combat_effects_preview.py'),'exec'),globals())",
                    "code=code.replace('distance = 150.0','distance = 350.0')\nexec(compile(code,str(MAIN/'Scripts/Art/combat_effects_preview.py'),'exec'),globals())")
exec(compile(code, str(script), 'exec'), globals())
