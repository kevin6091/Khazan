"""Unsaved RHI comparison of the FModel JustGuard emitter roles."""

from pathlib import Path
import os
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(os.environ["KZ_PARRY_PHOTO_OUT"])
code = (ROOT / "Scripts/Art/combat_effects_preview.py").read_text(encoding="utf-8")
code = code.replace("import traceback\n", "import traceback\nimport os\n")
code = code.replace(
    "OUT = ROOT / 'Saved/ImportReports/CombatEffects_20261006/Preview'",
    "OUT = Path(os.environ['KZ_PARRY_PHOTO_OUT'])",
)
code = code.replace("(META / 'RepresentativeEffectRendering.json')", "(OUT / 'Render.json')")
code = code.replace(
    "BY_NAME = {r['name']",
    "original = next(r for r in ROWS if r['name']=='PP_AtkEx_JustGuard')\n"
    "ROWS += [dict(original,name=n,destination='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/PP_Player_Parry_Success') "
    "for n in ['SuccessAll','SuccessNoSparks','SuccessHaloOnly']]\n"
    "BY_NAME = {r['name']",
)
code = re.sub(
    r"NAMES = \[.*?\]\nSTART",
    "NAMES = ['SuccessAll','SuccessNoSparks','SuccessHaloOnly']\nSTART",
    code,
    count=1,
    flags=re.S,
)
code = code.replace("distance = 150.0", "distance = 350.0")
code = code.replace(
    "if name in ('PP_AtkEx_Guard', 'PP_AtkEx_JustGuard', 'PP_AtkEx_Parry'):",
    "if name in ('SuccessAll', 'SuccessNoSparks', 'SuccessHaloOnly'):",
)
code = code.replace(
    "    assert COMPONENT, name\n",
    "    assert COMPONENT, name\n"
    "    if name in ('SuccessNoSparks','SuccessHaloOnly'):\n"
    "        disabled = ['spark_par_collision','spark_par_sphere','spark_1','emitter1']\n"
    "        if name == 'SuccessHaloOnly': disabled += ['flare_line','flare_line_center_glow','flare_line_glow']\n"
    "        for emitter in disabled:\n"
    "            COMPONENT.set_emitter_enable(emitter, False)\n",
)
code = code.replace(
    "            CAPTURE = next(a for a in actors",
    "            for actor in actors:\n"
    "                if isinstance(actor, unreal.Pawn): actor.set_actor_hidden_in_game(True)\n"
    "            CAPTURE = next(a for a in actors",
)
exec(compile(code, str(ROOT / "Scripts/Art/combat_effects_preview.py"), "exec"), globals())
