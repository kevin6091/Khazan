"""Correct the existing Brutal ring alpha and soften its edge; no gameplay writes."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import traceback

import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = Path(os.environ['KZ_COMBAT_UI_OUTPUT'])
PATH = '/Game/UI/Combat/Materials/M_UI_BrutalRing'
FILE = ROOT / 'Content/UI/Combat/Materials/M_UI_BrutalRing.uasset'
LIB = unreal.MaterialEditingLibrary
mat = unreal.load_asset(PATH)
assert isinstance(mat, unreal.Material)
nodes = LIB.get_material_expressions(mat)
custom = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionCustom))
masks = [n for n in nodes if isinstance(n, unreal.MaterialExpressionComponentMask)]
texture_path = '/Game/UI/Combat/Textures/T_Icon_XB_B'
texture = unreal.load_asset(texture_path) if unreal.EditorAssetLibrary.does_asset_exist(texture_path) else None
report = {
    'status': 'inspected',
    'project': str(ROOT),
    'asset': PATH,
    'sha256': hashlib.sha256(FILE.read_bytes()).hexdigest(),
    'blend_mode': str(mat.get_editor_property('blend_mode')),
    'material_domain': str(mat.get_editor_property('material_domain')),
    'custom_code': custom.get_editor_property('code'),
    'masks': [dict(path=n.get_path_name(), **{c: n.get_editor_property(c) for c in 'rgba'}) for n in masks],
    'texture': {p: str(texture.get_editor_property(p)) for p in
                ['filter', 'compression_settings', 'compression_no_alpha', 'address_x', 'address_y', 'srgb']} if texture else None,
    'edge_parameters': [{'name': str(n.get_editor_property('parameter_name')),
                         'default': n.get_editor_property('default_value')} for n in nodes
                        if isinstance(n, unreal.MaterialExpressionScalarParameter)],
}
(OUT / 'AlphaInspection.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('COMBAT_UI_ALPHA_INSPECTED')

mode = os.environ.get('KZ_COMBAT_UI_ALPHA_MODE', 'inspect')
if mode in ['author', 'stage', 'preview']:
    try:
        assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
        assert len(masks) == 2
        assert mat.get_editor_property('material_domain') == unreal.MaterialDomain.MD_UI
        assert mat.get_editor_property('blend_mode') == unreal.BlendMode.BLEND_TRANSLUCENT
        shutil.copy2(FILE, OUT / 'Before_M_UI_BrutalRing.uasset')
        mat.modify()
        for mask in masks:
            # ComponentMask defaults include R/G. Opacity must select A exclusively.
            is_alpha = mask.get_editor_property('a')
            for c in 'rgba':
                mask.set_editor_property(c, c == 'a' if is_alpha else c != 'a')
            assert LIB.connect_material_expressions(custom, '', mask, '')
            assert LIB.connect_material_property(mask, '', unreal.MaterialProperty.MP_OPACITY
                                                if is_alpha else unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        parameter = next((n for n in nodes if isinstance(n, unreal.MaterialExpressionScalarParameter)
                          and str(n.get_editor_property('parameter_name')) == 'EdgeSoftnessPixels'), None)
        if parameter is None:
            parameter = LIB.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -500, 150)
        parameter.set_editor_property('parameter_name', 'EdgeSoftnessPixels')
        # TEMP presentation tuning requested by the user; not an original-game shader value.
        # 1.25 screen pixels feathers the inner/outer edges while preserving the source radii.
        parameter.set_editor_property('default_value', 1.25)
        inputs = []
        for name in ['UV', 'EdgeSoftnessPixels']:
            item = unreal.CustomInput()
            item.set_editor_property('input_name', name)
            inputs.append(item)
        custom.set_editor_property('inputs', inputs)
        # Original radii = OuterSizePercent98/200 and InnerSizePercent76/200.
        # Feather inward so the outer AA cannot reach/clamp against the image's square bounds.
        custom.set_editor_property('code', '''float d = length(UV - float2(0.5, 0.5));
float edge = max(fwidth(d) * max(EdgeSoftnessPixels, 0.0), 0.00001);
float outer = 1.0 - smoothstep(0.49 - edge, 0.49, d);
float inner = smoothstep(0.38, 0.38 + edge, d);
return float4(0.859375, 0.02238, 0.02238, outer * inner);''')
        uv = next(n for n in nodes if isinstance(n, unreal.MaterialExpressionTextureCoordinate))
        assert LIB.connect_material_expressions(uv, '', custom, 'UV')
        assert LIB.connect_material_expressions(parameter, '', custom, 'EdgeSoftnessPixels')
        errors = list(LIB.recompile_material(mat))
        assert not errors, errors
        stats = LIB.get_statistics(mat)
        assert hashlib.sha256(FILE.read_bytes()).hexdigest() == report['sha256'], 'Concurrent material change'
        saved_file = None
        if mode == 'author':
            assert unreal.EditorAssetLibrary.save_loaded_asset(mat, only_if_is_dirty=False), 'Material save failed'
            saved_file = FILE
        elif mode == 'stage':
            saved_file = OUT / 'Staged/Content/UI/Combat/Materials/M_UI_BrutalRing.uasset'
            saved_file.parent.mkdir(parents=True, exist_ok=True)
            unreal.SystemLibrary.execute_console_command(None,
                f'OBJ SAVEPACKAGE PACKAGE="{PATH}" FILE="{saved_file.as_posix()}" SILENT=true')
            assert saved_file.exists() and saved_file.stat().st_size > 0, 'Staged material save failed'
            assert hashlib.sha256(FILE.read_bytes()).hexdigest() == report['sha256'], 'Main must remain unchanged'
        # Original B texture RGBA/filter/address settings are preserved byte-for-byte.
        report.update(status='preview_compiled' if mode == 'preview' else 'saved', mode=mode, compile_errors=errors,
                      pixel_instructions=stats.num_pixel_shader_instructions,
                      edge_softness_pixels=1.25,
                      tuning_source='Assistant temporary presentation tuning requested by user; original shader unavailable',
                      masks_after=[dict(path=n.get_path_name(), **{c: n.get_editor_property(c) for c in 'rgba'}) for n in masks],
                      custom_code_after=custom.get_editor_property('code'),
                      files=[{'path': str(FILE.relative_to(ROOT)), 'before': report['sha256'],
                              'staged_file': str(saved_file) if saved_file else None,
                              'after': hashlib.sha256(saved_file.read_bytes()).hexdigest() if saved_file else None}])
    except Exception:
        report.update(status='failed', error=traceback.format_exc())
        raise
    finally:
        (OUT / 'AlphaAuthoring.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
