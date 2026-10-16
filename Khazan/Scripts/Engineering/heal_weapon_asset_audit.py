"""Read only. Saved Heal weapon contracts in the isolated project; no player input."""
import json
import pathlib
import unreal

root = pathlib.Path(unreal.Paths.project_dir()).resolve()
if root != pathlib.Path('C:/Users/user/Desktop/GitProject/Khazan_HealWeaponWork_20261006/Khazan').resolve():
    raise RuntimeError('Isolated work editor required')
audit = {'project': str(root), 'montages': {}, 'clips': {}}
for name in ('AM_DAS_Player_Heal', 'AM_DAS_Player_HealDraw'):
    asset = unreal.load_asset('/Game/_Art/Player/Animation/InGame/DAS/Heal/' + name)
    audit['montages'][name] = dict(length=asset.get_play_length(),
        slots=[t.export_text() for t in asset.get_editor_property('slot_anim_tracks')],
        sections=[str(asset.get_section_name(i)) for i in range(asset.get_num_sections())],
        blend_in=asset.get_editor_property('blend_in').export_text(),
        blend_out=asset.get_editor_property('blend_out').export_text())
for name in ('Armed', 'UnArmed'):
    asset = unreal.load_asset('/Game/_Art/Player/Animation/InGame/DAS/Equip/CA_P_Kazan_DualAxeSword_' + name)
    model = asset.controller.get_model_interface()
    audit['clips'][name] = dict(length=asset.get_play_length(),
        rate_scale=asset.get_editor_property('rate_scale'),
        root_motion=asset.get_editor_property('enable_root_motion'),
        frame_rate=model.get_frame_rate().export_text(),
        frames=model.get_number_of_frames(), tracks=[str(t) for t in model.get_bone_track_names()],
        metadata={str(k): str(v) for k, v in unreal.EditorAssetLibrary.get_metadata_tag_values(asset).items()})
bp = unreal.load_asset('/Game/Bluprints/AbilitySystem/Abilities/Player/Heal/GA_Player_Heal')
cdo = unreal.get_default_object(bp.generated_class())
audit['ability'] = {p: str(cdo.get_editor_property(p)) for p in ('HealMontage','DrawMontage','HealEffect','LeftBackSocket','RightBackSocket','cost_gameplay_effect_class','cooldown_gameplay_effect_class')}
abp = unreal.load_asset('/Game/_Art/Player/Character/Bluprints/ABP_Player')
audit['abp_status'] = str(abp.get_editor_property('status'))
worlds = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
game = worlds.get_game_world()
audit['worlds'] = dict(editor=str(worlds.get_editor_world()), game=str(game) if game else None)
audit['dirty_content'] = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
audit['dirty_maps'] = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
destination = root / 'Saved/HealWeaponAssetAudit.json'
destination.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(dict(file=str(destination), abp_status=audit['abp_status'], worlds=audit['worlds'], dirty_content=audit['dirty_content'], dirty_maps=audit['dirty_maps']),ensure_ascii=False))
