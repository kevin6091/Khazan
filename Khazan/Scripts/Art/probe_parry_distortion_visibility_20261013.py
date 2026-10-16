"""Unsaved RHI on/off comparison for the Main parry refraction emitter."""
from pathlib import Path
import os
import re
import unreal

root = Path(__file__).resolve().parents[2]
out = Path(os.environ['KZ_PARRY_PHOTO_OUT'])
base = '/Game/_Art/Effects/Combat/GuardParry/PlayerParry/Reference'
code = (root / 'Scripts/Art/combat_effects_preview.py').read_text(encoding='utf-8')
code = code.replace('import traceback\n', 'import traceback\nimport os\n')
code = code.replace("OUT = ROOT / 'Saved/ImportReports/CombatEffects_20261006/Preview'", "OUT = Path(os.environ['KZ_PARRY_PHOTO_OUT'])")
code = code.replace("(META / 'RepresentativeEffectRendering.json')", "(OUT / 'Render.json')")
code = code.replace('BY_NAME = {r[\'name\']',
                    "original = next(r for r in ROWS if r['name']=='PP_AtkEx_Parry')\n"
                    "ROWS += [dict(original,name=n,destination='" + base + "/PP_Player_Parry_Reference') "
                    "for n in ['RefractionOn','RefractionOff']]\nBY_NAME = {r['name']")
code = re.sub(r'NAMES = \[.*?\]\nSTART', "NAMES = ['RefractionOn','RefractionOff']\nSTART", code, count=1, flags=re.S)
code = code.replace('    c = capture.get_component_by_class(unreal.SceneCaptureComponent2D)',
    """    grid = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(-300, 300, 0))
    grid.set_actor_label('KZFX_StaticRefractionGrid')
    grid.set_actor_scale3d(unreal.Vector(.2, 12, 12))
    mesh = grid.get_component_by_class(unreal.StaticMeshComponent)
    mesh.set_static_mesh(unreal.load_asset('/Engine/BasicShapes/Cube.Cube'))
    grid_mat = unreal.AssetToolsHelpers.get_asset_tools().create_asset('M_KZUnsavedRefractionGrid', '""" + base + """', unreal.Material, unreal.MaterialFactoryNew())
    lib = unreal.MaterialEditingLibrary
    uv = lib.create_material_expression(grid_mat, unreal.MaterialExpressionTextureCoordinate)
    pattern = lib.create_material_expression(grid_mat, unreal.MaterialExpressionCustom)
    pattern.set_editor_property('code', 'float2 p=frac(UV*float2(24,14));float v=(p.x<.5)!=(p.y<.5);return lerp(float3(.04,.04,.04),float3(2,2,2),v);')
    pattern.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    pin = unreal.CustomInput()
    pin.set_editor_property('input_name', 'UV')
    pattern.set_editor_property('inputs', [pin])
    assert lib.connect_material_expressions(uv, '', pattern, 'UV')
    assert lib.connect_material_property(pattern, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    assert not list(lib.recompile_material(grid_mat))
    mesh.set_material(0, grid_mat)
    KEEP.extend([grid, grid_mat])
    c = capture.get_component_by_class(unreal.SceneCaptureComponent2D)""")
code = code.replace('    distance = max(300.0, min(800.0, extent * 2.5))',
                    '    center = unreal.Vector(0, 0, 0)\n    distance = 400.0')
code = code.replace('    assert COMPONENT, name',
    """    assert COMPONENT, name
    for emitter in ['refrac','light','flare_circle','ParryPhotoHalo','spark_par_sphere','smoke_blur','spark_1','spark_02']:
        COMPONENT.set_emitter_enable(emitter, name == 'RefractionOn' and emitter == 'refrac')""")
code = code.replace('            setup()\n            REQUESTED = True',
                    '            REQUESTED = True\n            setup()')
code = code.replace('            CAPTURE = next(a for a in actors',
    """            for actor in actors:
                if isinstance(actor, unreal.Pawn):
                    actor.set_actor_hidden_in_game(True)
            REPORT['grid_actor_in_pie'] = [(a.get_actor_label(), str(a.get_actor_location())) for a in actors if a.get_actor_label() == 'KZFX_StaticRefractionGrid']
            CAPTURE = next(a for a in actors""")
exec(compile(code, str(root / 'Scripts/Art/combat_effects_preview.py'), 'exec'), globals())
