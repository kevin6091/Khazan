"""Set real existing monster BP UI defaults; fresh readback also validates native controller consumption."""
from pathlib import Path
import hashlib, json, os, shutil, unreal
ROOT = Path(unreal.Paths.project_dir()).resolve()
OUT = Path(os.environ['KZ_COMBAT_UI_OUTPUT'])
assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
rows = []
write = os.environ.get('KZ_UI_READ_ONLY') != '1'
widget_path = '/Game/UI/Combat/WBP_CombatHUD'
widget = unreal.load_asset(widget_path)
if write and not widget:
    factory = unreal.WidgetBlueprintFactory()
    factory.set_editor_property('parent_class', unreal.load_class(None,'/Script/Khazan.KZCombatHUDWidget'))
    widget = unreal.AssetToolsHelpers.get_asset_tools().create_asset('WBP_CombatHUD','/Game/UI/Combat',unreal.WidgetBlueprint,factory)
    unreal.BlueprintEditorLibrary.compile_blueprint(widget)
    assert unreal.EditorAssetLibrary.save_loaded_asset(widget)
assert widget
widget_class = unreal.load_class(None,widget_path+'.WBP_CombatHUD_C')
assert widget_class
for family in ['Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga']:
    path = '/Game/Bluprints/Monsters/BP_Monster_' + family
    bp = unreal.load_asset(path); cls = unreal.load_class(None, path + '.' + path.rsplit('/',1)[1] + '_C')
    assert bp and cls, path
    cdo = unreal.get_default_object(cls); mesh = cdo.get_editor_property('Mesh')
    bones = [str(mesh.get_bone_name(i)) for i in range(mesh.get_num_bones())]
    # Exact bone strings are recorded, not invented shared socket names.
    head = [n for n in bones if n.lower() == 'head']
    if not head: head = [n for n in bones if n.lower() in ['bip001-head','bip001_head','bip01-head','bip01_head']]
    if not head: head = [n for n in bones if n.lower().endswith('_head') or n.lower().endswith('-head')]
    assert len(head) == 1, (family, 'Cannot unambiguously author actual head bone', head, bones[:35])
    if write:
        disk = ROOT/'Content/Bluprints/Monsters'/('BP_Monster_'+family+'.uasset')
        backup = OUT/'Before'/disk.relative_to(ROOT); backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(disk,backup)
        cdo.set_editor_property('bUseBossCombatHUD', family == 'Yetuga')
        cdo.set_editor_property('bUseEliteCombatGauge', family in ['HalberdElite','ApesStoneHandElite'])
        cdo.set_editor_property('CombatDisplayName', unreal.Text('예투가') if family == 'Yetuga' else unreal.Text(''))
        cdo.set_editor_property('CombatGaugeHeadBone', head[0])
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        assert unreal.EditorAssetLibrary.save_loaded_asset(bp)
    assert cdo.get_editor_property('bUseBossCombatHUD') == (family == 'Yetuga')
    assert str(cdo.get_editor_property('CombatGaugeHeadBone')) == head[0]
    rows.append({'asset':path,'boss':cdo.get_editor_property('bUseBossCombatHUD'),'elite':cdo.get_editor_property('bUseEliteCombatGauge'),
                 'name':str(cdo.get_editor_property('CombatDisplayName')),'actual_mesh_head_bone':head[0],
                 'sha256':hashlib.sha256((ROOT/'Content/Bluprints/Monsters'/('BP_Monster_'+family+'.uasset')).read_bytes()).hexdigest()})
pc_path = '/Game/_Art/Player/Character/Bluprints/BP_PlayerController'
pc = unreal.load_class(None,pc_path+'.BP_PlayerController_C')
assert pc
if write:
    disk = ROOT/'Content/_Art/Player/Character/Bluprints/BP_PlayerController.uasset'
    backup = OUT/'Before'/disk.relative_to(ROOT); backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(disk,backup)
    unreal.get_default_object(pc).set_editor_property('CombatHUDClass',widget_class)
    pc_bp = unreal.load_asset(pc_path); unreal.BlueprintEditorLibrary.compile_blueprint(pc_bp)
    assert unreal.EditorAssetLibrary.save_loaded_asset(pc_bp)
hud = unreal.get_default_object(pc).get_editor_property('CombatHUDClass')
assert hud and hud.get_name() == 'WBP_CombatHUD_C', str(hud)
textures = []
for a in unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_path('/Game/UI/Combat', recursive=True):
    obj = a.get_asset()
    if isinstance(obj,unreal.Texture2D):
        assert obj.get_editor_property('compression_settings') == unreal.TextureCompressionSettings.TC_EDITOR_ICON
        assert obj.get_editor_property('lod_group') == unreal.TextureGroup.TEXTUREGROUP_UI
        textures.append(str(a.package_name))
assert len(textures) == 16
font = unreal.load_asset('/Game/UI/Combat/Fonts/FF_DNFForgedBlade_Medium')
assert isinstance(font, unreal.FontFace)
(OUT/'SavedReadback.json').write_text(json.dumps({'status':'passed','write':write,'monster_bp':rows,'actual_player_controller_hud_class':hud.get_path_name(),'textures':textures,'font':font.get_path_name(),'requested_widget_parent':'/Script/Khazan.KZCombatHUDWidget','actual_native_inheritance_check':'Native PIE Cast<UKZCombatHUDWidget> and tick/resource validation'},ensure_ascii=False,indent=2),encoding='utf-8')
unreal.log('COMBAT_UI_SAVED_READBACK_PASSED')
