"""Unsaved isolated renderer diagnosis; main gameplay screenshots remain authoritative."""
from pathlib import Path
import os, json, re, unreal
MAIN=Path(__file__).resolve().parents[2];OUT=Path(os.environ['KZ_HEAL_VFX_OUT'])
assert Path(unreal.Paths.project_dir()).resolve()==MAIN.parent.parent/'Khazan_HealVFXWork_20261013/Khazan'
code=(MAIN/'Scripts/Art/combat_effects_preview.py').read_text(encoding='utf-8')
rows=[]
for name in ['PS_Heal_DrainCore','PS_Heal_DrainBurst','PS_Heal_GhostArm','PS_Heal_GhostFinger','PS_Heal_LightFlash']:
    rows.append(dict(name=name,source_type='ParticleSystem',destination='/Game/HealVFX/Particles/'+name,
                     source_package='Recovery native rendering adapter',source_json=str(MAIN/'Metadata/HealVFX_20261013/Author03'/(name+'.json'))))
code=code.replace("ROWS = json.loads((META / 'AssetManifest.json').read_text(encoding='utf-8'))",'ROWS = '+repr(rows))
code=code.replace("OUT = ROOT / 'Saved/ImportReports/CombatEffects_20261006/Preview'","OUT = Path(os.environ['KZ_HEAL_VFX_OUT'])")
code=code.replace('import traceback\n','import traceback\nimport os\n')
code=code.replace("(META / 'RepresentativeEffectRendering.json')","(OUT / 'Preview.json')")
code=re.sub(r'NAMES = \[.*?\]\nSTART',"NAMES = "+repr([r['name'] for r in rows])+"\nSTART",code,count=1,flags=re.S)
code=code.replace('center = unreal.Vector(0, 0, 50)','center = unreal.Vector(0, 0, 0)')
code=code.replace('distance = max(300.0, min(800.0, extent * 2.5))','distance = 35.0')
code=code.replace('            CAPTURE = next(a for a in actors',"""            for actor in actors:
                if isinstance(actor,unreal.Pawn):actor.set_actor_hidden_in_game(True)
            CAPTURE = next(a for a in actors""")
exec(compile(code,'<existing unsaved renderer preview>','exec'),globals())
