"""Import targeted original UI images; reconstruct stripped UI materials, without touching other assets."""
from pathlib import Path
import hashlib, json, os, unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = ROOT / 'Metadata/CombatUI_20261011'
assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
report = {'project': str(ROOT), 'textures': [], 'materials': [], 'source': 'FModel active provider, UE4.27 cooked snapshot'}
names = ['T_Hud_Gauge_HP_01', 'T_Hud_Gauge_HP_02', 'T_Hud_Gauge_HP_04',
         'T_Hud_Gauge_Stamina_01', 'T_Hud_Gauge_Stamina_02', 'T_Hud_Hp_Bg03', 'T_Hud_Hp_Bg04', 'T_Hud_Hp_Bg05',
         'T_Hud_Gauge_HP_BG_00', 'T_Hud_Gauge_HP_BG_03', 'T_Hud_Gauge_HP_BG_04',
         'T_Hud_Gauge_HP_BG_Elite', 'T_Hud_LockOn_Excution', 'T_Fx_TargetLock',
         'T_Hud_Overhead_Groggy', 'T_Icon_XB_B']
tools = unreal.AssetToolsHelpers.get_asset_tools()
for name in names:
    files = list((OUT / 'Textures01').rglob(name + '.png'))
    assert len(files) == 1, name
    package = '/Game/UI/Combat/Textures/' + name
    existing = unreal.EditorAssetLibrary.load_asset(package)
    if not existing:
        task = unreal.AssetImportTask()
        task.filename = str(files[0]); task.destination_path = '/Game/UI/Combat/Textures'
        task.destination_name = name; task.automated = True; task.save = False; task.replace_existing = False
        tools.import_asset_tasks([task])
        existing = unreal.EditorAssetLibrary.load_asset(package)
    assert isinstance(existing, unreal.Texture2D), package
    existing.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    existing.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
    existing.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    existing.set_editor_property('srgb', True)
    existing.set_editor_property('never_stream', True)
    assert unreal.EditorAssetLibrary.save_loaded_asset(existing)
    report['textures'].append({'source_png': str(files[0]), 'source_sha256': hashlib.sha256(files[0].read_bytes()).hexdigest(),
                              'source_package': str(files[0].relative_to(OUT / 'Textures01').with_suffix('')).replace('\\', '/'),
                              'asset': package, 'size': [existing.blueprint_get_size_x(), existing.blueprint_get_size_y()]})

font_source = OUT/'FontData01/DNFForgedBlade-Medium.ttf'
assert font_source.read_bytes()[:4] == b'OTTO' # Cooked streaming payload is actually OpenType/CFF.
font_otf = OUT/'FontData01/DNFForgedBlade-Medium.otf'
if not font_otf.exists(): font_otf.write_bytes(font_source.read_bytes())
font_path = '/Game/UI/Combat/Fonts/FF_DNFForgedBlade_Medium'
font = unreal.load_asset(font_path)
if not font:
    factory = unreal.FontFileImportFactory()
    factory.set_editor_property('batch_create_font_asset', unreal.BatchCreateFontAsset.NO)
    task = unreal.AssetImportTask(); task.filename = str(font_otf)
    task.destination_path = '/Game/UI/Combat/Fonts'; task.destination_name = 'FF_DNFForgedBlade_Medium'
    task.automated = True; task.save = True; task.factory = factory
    tools.import_asset_tasks([task]); font = unreal.load_asset(font_path)
assert isinstance(font, unreal.FontFace), font_path
assert unreal.EditorAssetLibrary.save_loaded_asset(font)
report['font'] = {'asset': font_path, 'source': 'BBQ/Content/_Kazan_/UserInterface/Font/DNF_ForgedBlade/DNFForgedBlade-Medium.ufont',
                  'sha256':hashlib.sha256(font_source.read_bytes()).hexdigest(),'bytes':font_source.stat().st_size,'typeface':'Medium','format':'OpenType CFF',
                  'runtime':'Widget creates a one-face FCompositeFont with the source Medium name; no editor-only private font struct mutation'}

lib = unreal.MaterialEditingLibrary
def material(name, blend):
    path = '/Game/UI/Combat/Materials/' + name
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if not asset: asset = tools.create_asset(name, '/Game/UI/Combat/Materials', unreal.Material, unreal.MaterialFactoryNew())
    lib.delete_all_material_expressions(asset)
    asset.set_editor_property('material_domain', unreal.MaterialDomain.MD_UI)
    asset.set_editor_property('blend_mode', blend)
    return asset

if all(unreal.EditorAssetLibrary.does_asset_exist('/Game/UI/Combat/Materials/' + n) for n in ['M_UI_LockOn','M_UI_BrutalRing']):
    for n in ['M_UI_LockOn','M_UI_BrutalRing']:
        asset = unreal.load_asset('/Game/UI/Combat/Materials/' + n)
        assert isinstance(asset, unreal.Material) and asset.get_editor_property('material_domain') == unreal.MaterialDomain.MD_UI
        report['materials'].append({'asset':asset.get_path_name(),'status':'existing original reconstruction preserved without graph mutation'})
else:
    lock = material('M_UI_LockOn', unreal.BlendMode.BLEND_ADDITIVE)
    sample = lib.create_material_expression(lock, unreal.MaterialExpressionTextureSampleParameter2D)
    sample.set_editor_property('parameter_name', 'Texture')
    sample.set_editor_property('texture', unreal.load_asset('/Game/UI/Combat/Textures/T_Fx_TargetLock'))
    lib.connect_material_property(sample, 'RGB', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    lib.connect_material_property(sample, 'A', unreal.MaterialProperty.MP_OPACITY)
    # Original parent has AutoRotateSpeed=.2 but cooked expression/function graph is absent.
    # Static sampled texture deliberately avoids claiming an unrecovered rotation formula.
    lib.recompile_material(lock); assert unreal.EditorAssetLibrary.save_loaded_asset(lock)
    report['materials'].append({'asset': lock.get_path_name(), 'source': 'MI_UI_SimpleAdd_Target.Texture=T_Fx_TargetLock; parent MD_UI/BLEND_Additive',
                                'adapter': 'direct texture RGB/alpha; cooked UV rotation graph not recovered'})

    ring = material('M_UI_BrutalRing', unreal.BlendMode.BLEND_TRANSLUCENT)
    uv = lib.create_material_expression(ring, unreal.MaterialExpressionTextureCoordinate)
    custom = lib.create_material_expression(ring, unreal.MaterialExpressionCustom)
    inp = unreal.CustomInput(); inp.set_editor_property('input_name', 'UV'); custom.set_editor_property('inputs', [inp])
    custom.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT4)
    # Calculated normalized radii from original OuterSizePercent98/InnerSizePercent76.
    # The fwidth edge is an engine presentation adapter, not the original stripped shader.
    custom.set_editor_property('code', 'float d=length(UV-float2(.5,.5)); float aa=max(fwidth(d),.0001); float a=(1-smoothstep(.49-aa,.49+aa,d))*smoothstep(.38-aa,.38+aa,d); return float4(.859375,.02238,.02238,a);')
    lib.connect_material_expressions(uv, '', custom, 'UV')
    rgb = lib.create_material_expression(ring, unreal.MaterialExpressionComponentMask)
    for prop in ['r', 'g', 'b']: rgb.set_editor_property(prop, True)
    alpha = lib.create_material_expression(ring, unreal.MaterialExpressionComponentMask)
    # ComponentMask defaults R/G=true; opacity must consume only the computed alpha.
    for channel in ['r', 'g', 'b', 'a']: alpha.set_editor_property(channel, channel == 'a')
    assert lib.connect_material_expressions(custom, '', rgb, '')
    assert lib.connect_material_expressions(custom, '', alpha, '')
    assert lib.connect_material_property(rgb, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    assert lib.connect_material_property(alpha, '', unreal.MaterialProperty.MP_OPACITY)
    errors=lib.recompile_material(ring); assert not errors,errors
    assert unreal.EditorAssetLibrary.save_loaded_asset(ring)
    report['materials'].append({'asset': ring.get_path_name(), 'source': 'MI_UI_CircleProgress_Finish OuterSizePercent98 InnerSizePercent76 GaugeColor(.859375,.02238,.02238)',
                                'adapter': 'analytic full availability ring; original native progress/time and cooked shader not recovered'})
report['status'] = 'imported_and_saved'
(Path(os.environ.get('KZ_COMBAT_UI_OUTPUT',str(OUT))) / 'ImportReport.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
unreal.log('COMBAT_UI_IMPORT_COMPLETE ' + str(len(report['textures'])))
if os.environ.get('KZ_COMBAT_UI_EDITOR_MODE') == 'asset_editor': unreal.SystemLibrary.quit_editor()
