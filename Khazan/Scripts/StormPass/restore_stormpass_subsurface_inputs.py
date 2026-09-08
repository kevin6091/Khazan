"""Restore source-authored SSS flags and texture inputs, never Tex_E emission.

Uses the exact inherited source package chain and newly decoded textures.
Only the 25 live WorldProp MIs explicitly authored MSM_Subsurface are in scope.
"""
import hashlib
import os
import runpy

import unreal

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '../..'))
base = runpy.run_path(os.path.join(ROOT, 'Scripts/StormPass/restore_stormpass_surface_controls.py'))
read, write = base['read'], base['write']
TEXTURE_ROOT = '/Game/_Art/Kazan/Environment/StormPass/Reconstructed/MaterialRepairs/Surfaces/Textures'
PARENT_ROOT = base['PARENT'].rsplit('/', 1)[0]
MANIFEST = os.path.join(ROOT, 'Saved/Extracted/StormPass/AdditionalTextures_20260908/TargetedTextureManifest.json')
REPORT = os.path.join(base['META'], 'StormPass_SubsurfaceRestoration_20260908.json')


def import_textures():
    textures, records = {}, []
    unreal.EditorAssetLibrary.make_directory(TEXTURE_ROOT)
    for row in read(MANIFEST):
        package = row['source_object_path'].split('.')[0]
        source = next(r for r in read(os.path.join(base['RAW'], package + '.json')) if r.get('Type') == 'Texture2D')
        props = source.get('Properties') or {}
        suffix = hashlib.sha256(package.lower().encode()).hexdigest()[:8]
        name = 'T_SP_Source_' + row['source_object_name'] + '_' + suffix
        path = TEXTURE_ROOT + '/' + name
        texture = unreal.load_asset(path)
        if not texture:
            task = unreal.AssetImportTask()
            for key, value in [('filename', row['path']), ('destination_path', TEXTURE_ROOT),
                               ('destination_name', name), ('automated', True), ('save', True),
                               ('replace_existing', False)]:
                task.set_editor_property(key, value)
            # AssetTools.cpp only chooses Interchange when SpecifiedFactory is
            # null. Explicit legacy TextureFactory avoids the UE5.8 TaskGraph
            # reentrancy assertion observed through the live Rider callback.
            task.set_editor_property('factory', unreal.TextureFactory())
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            texture = unreal.load_asset(path)
        if not isinstance(texture, unreal.Texture2D):
            raise RuntimeError('Source texture import failed: ' + package)
        srgb = props.get('SRGB', True)
        normal = str(props.get('CompressionSettings', '')).endswith('TC_Normalmap') or row['source_object_name'].endswith('_N')
        texture.set_editor_property('srgb', False if normal else srgb)
        texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP if normal else unreal.TextureCompressionSettings.TC_DEFAULT)
        unreal.EditorAssetLibrary.set_metadata_tag(texture, 'StormPassExactSourcePackage', package)
        if not unreal.EditorAssetLibrary.save_loaded_asset(texture, only_if_is_dirty=False):
            raise RuntimeError('Texture save failed: ' + path)
        textures[package.lower()] = texture
        records.append({'source_package': package, 'asset': texture.get_path_name(), 'srgb': bool(texture.get_editor_property('srgb')),
                        'source_png_sha256': hashlib.sha256(open(row['path'], 'rb').read()).hexdigest(), 'width': row['width'], 'height': row['height']})
    write(os.path.join(base['META'], 'StormPass_AdditionalTextureImports_20260908.json'), {'textures': records})
    return textures


def build_parent(texture):
    srgb = bool(texture.get_editor_property('srgb'))
    name = 'M_SP_WorldSurface_Subsurface_' + ('Color' if srgb else 'Linear')
    path = PARENT_ROOT + '/' + name
    material = unreal.load_asset(path)
    if material:
        if unreal.EditorAssetLibrary.get_metadata_tag(material, 'StormPassSubsurfaceAdapter') != 'v1':
            raise RuntimeError('Unrecognized SSS parent')
        return material
    material = unreal.EditorAssetLibrary.duplicate_asset(base['PARENT'], path)
    if not material:
        raise RuntimeError('SSS parent duplication failed')
    material.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_SUBSURFACE)
    expr, connect, scalar, binary, output = [base[n] for n in ('expression', 'connect', 'scalar', 'binary', 'output')]
    mask = expr(material, unreal.MaterialExpressionTextureSampleParameter2D)
    mask.set_editor_property('parameter_name', 'SP_SSS_Mask')
    mask.set_editor_property('texture', texture)
    mask.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_COLOR if srgb else unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    color = expr(material, unreal.MaterialExpressionVectorParameter)
    color.set_editor_property('parameter_name', 'SP_SSS_Color')
    color.set_editor_property('default_value', unreal.LinearColor(1, 1, 1, 1))
    mel = unreal.MaterialEditingLibrary
    base_color = mel.get_material_property_input_node(material, unreal.MaterialProperty.MP_BASE_COLOR)
    tinted = binary(material, unreal.MaterialExpressionMultiply, base_color, color)
    mask_scaled = binary(material, unreal.MaterialExpressionMultiply, mask, scalar(material, 'SSS_Intensity', 1), 'R')
    subsurface = binary(material, unreal.MaterialExpressionMultiply, tinted, mask_scaled)
    output(material, subsurface, unreal.MaterialProperty.MP_SUBSURFACE_COLOR)
    output(material, scalar(material, 'SSS_Opacity', 1), unreal.MaterialProperty.MP_OPACITY)
    # This parent is selected only for source EmissiveOn=0. Keep a constant
    # zero emissive output; do not turn the transmission mask into a light.
    zero = expr(material, unreal.MaterialExpressionConstant)
    zero.set_editor_property('r', 0)
    output(material, zero, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    mel.recompile_material(material)
    mel.layout_material_expressions(material)
    unreal.EditorAssetLibrary.set_metadata_tag(material, 'StormPassSubsurfaceAdapter', 'v1')
    if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
        raise RuntimeError('SSS parent save failed')
    return material


def apply_batch(offset=0, limit=5):
    helper = runpy.run_path(os.path.join(ROOT, 'Scripts/StormPass/repair_stormpass_surface_rendering.py'))
    helper['actors']()
    imports = read(os.path.join(base['META'], 'StormPass_AdditionalTextureImports_20260908.json'))
    textures = {r['source_package'].lower(): unreal.load_asset(r['asset']) for r in imports['textures']}
    rows = [r for r in read(base['PLAN'])['materials'] if r['source_use_sss']]
    report = read(REPORT) if os.path.isfile(REPORT) else {'materials': {}}
    for row in rows[offset:offset + limit]:
        if row['source_shading'] != 'MSM_Subsurface' or row.get('source_emissive_on', 0) != 0:
            raise RuntimeError('Unexpected source SSS policy: ' + row['source_package'])
        package = row['sss_mask']['ObjectPath'].split('.')[0]
        texture = textures[package.lower()]
        parent = build_parent(texture)
        material = unreal.load_asset(row['asset'])
        helper['fixer'].backup_asset(row['asset'])
        unreal.MaterialEditingLibrary.set_material_instance_parent(material, parent)
        unreal.MaterialEditingLibrary.update_material_instance(material)
        overrides = material.get_editor_property('base_property_overrides')
        overrides.set_editor_property('override_shading_model', True)
        overrides.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_SUBSURFACE)
        material.set_editor_property('base_property_overrides', overrides)
        unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(material, 'SP_SSS_Mask', texture)
        for name, value in [('SP_SSS_Intensity', row['sss_intensity']), ('SP_SSS_Opacity', row['sss_opacity'])]:
            unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(material, name, value)
        color = row['sss_color']
        unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(material, 'SP_SSS_Color', unreal.LinearColor(*(color[k] for k in 'RGBA')))
        unreal.MaterialEditingLibrary.update_material_instance(material)
        if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError('SSS MI save failed')
        report['materials'][row['asset']] = {'parent': parent.get_path_name(), 'source_package': row['source_package'],
                                           'mask': texture.get_path_name(), 'sss_color': color,
                                           'sss_intensity': row['sss_intensity'], 'sss_opacity': row['sss_opacity']}
        write(REPORT, report)
    print('SSS restored: %d / %d' % (len(report['materials']), len(rows)))
