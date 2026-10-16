"""Reuse the established unsaved Cascade RHI preview on source/local Parry only."""
from pathlib import Path
import os, re, unreal
MAIN=Path(os.environ['KZ_PARRY_MAIN']);OUT=Path(os.environ['KZ_PARRY_OUT'])
code=(MAIN/'Scripts/Art/combat_effects_preview.py').read_text(encoding='utf-8')
code=code.replace("OUT = ROOT / 'Saved/ImportReports/CombatEffects_20261006/Preview'","OUT = Path(os.environ['KZ_PARRY_OUT'])")
code=code.replace('import traceback\n','import traceback\nimport os\n')
code=code.replace("(META / 'RepresentativeEffectRendering.json')","(OUT / 'EffectRendering.json')")
code=code.replace("BY_NAME = {r['name']", "original = next(r for r in ROWS if r['name'] == 'PP_AtkEx_JustGuard')\nlocal = dict(original, name='PP_Player_Parry_Success', destination='/Game/_Art/Effects/Combat/GuardParry/PlayerParry/PP_Player_Parry_Success', source_json=str(Path(os.environ['KZ_PARRY_MAIN']) / original['source_json']))\noriginal['source_json'] = str(Path(os.environ['KZ_PARRY_MAIN']) / original['source_json'])\nROWS.append(local)\nBY_NAME = {r['name']")
code=re.sub(r'NAMES = \[.*?\]\nSTART',"NAMES = ['PP_AtkEx_JustGuard', 'PP_Player_Parry_Success']\nSTART",code,count=1,flags=re.S)
code=code.replace("('PP_AtkEx_Guard', 'PP_AtkEx_JustGuard', 'PP_AtkEx_Parry')","('PP_AtkEx_Guard', 'PP_AtkEx_JustGuard', 'PP_AtkEx_Parry', 'PP_Player_Parry_Success')")
code=code.replace('(1, 2, 4, 8, 16)','(1, 2, 3, 4, 6, 8, 12, 16)')
code=code.replace('FRAMES = 0\nKEEP = []','FRAMES = 0\nWARM_STARTED = None\nWARM_COMPONENTS = []\nKEEP = []')
code=code.replace('global REQUESTED, WORLD, CAPTURE, CAMERA, FRAMES','global REQUESTED, WORLD, CAPTURE, CAMERA, FRAMES, WARM_STARTED')
code=code.replace('            CAPTURE = next(a for a in actors', '''            REPORT['hidden_fixture_pawns'] = []
            for actor in actors:
                if isinstance(actor, unreal.Pawn):
                    REPORT['hidden_fixture_pawns'].append({'name': actor.get_name(), 'class': actor.get_class().get_name(), 'location': str(actor.get_actor_location())})
                    actor.set_actor_hidden_in_game(True)
            CAPTURE = next(a for a in actors''')
code=code.replace("            next_effect()\n            return\n        FRAMES += 1", """            # Unsaved RHI warmup: compile every material permutation and GPU
            # particle resource before measuring this very short flash.
            for name in NAMES:
                asset = unreal.load_asset(BY_NAME[name]['destination'])
                WARM_COMPONENTS.append(unreal.GameplayStatics.spawn_emitter_at_location(WORLD, asset, unreal.Vector(), auto_destroy=False))
            WARM_STARTED = time.monotonic()
            return
        if INDEX < 0:
            if time.monotonic() - WARM_STARTED < 3.0: return
            for component in WARM_COMPONENTS: component.destroy_component(component)
            next_effect()
            return
        FRAMES += 1""")
# Read-only warmup/compile checks before the short burst starts. No package save.
lib=unreal.MaterialEditingLibrary
for name in ['FM_fluid_A','FM_Subuv_Atlas_B','DefaultParticle']:
    mat=unreal.load_asset('/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Materials/'+name)
    stats=lib.get_statistics(mat)
    assert stats.num_pixel_shader_instructions>0,name
for name in ['FMI_fluid_A_11','FMI_fluid_A_13','FMI_fluid_A_15','FMI_fluid_A_133','FMI_Subuv_Atlas_B_01']:
    assert lib.get_statistics(unreal.load_asset('/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Materials/'+name)).num_pixel_shader_instructions>0,name
for path in ['/Game/_Art/Effects/Shared/Materials/Fluid/FM_fluid_A',
             '/Game/_Art/Effects/Shared/Materials/SubUV/FM_Subuv_Atlas_B',
             '/Game/_Art/Effects/Shared/Materials/Other/DefaultParticle']:
    assert lib.get_statistics(unreal.load_asset(path)).num_pixel_shader_instructions>0,path
if os.environ.get('KZ_PARRY_ALPHA_ISOLATE')=='no_refraction':
    code=code.replace('    assert COMPONENT, name','    assert COMPONENT, name\n    if name == "PP_Player_Parry_Success": COMPONENT.set_emitter_enable("refrac", False)')
    unreal.log('PARRY_UNSAVED_ISOLATION instance refraction emitter disabled with public engine API; no package save')
exec(compile(code,str(MAIN/'Scripts/Art/combat_effects_preview.py'),'exec'),globals())
