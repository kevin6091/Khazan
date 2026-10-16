"""Read saved Heal contracts only in the isolated editor; never saves assets."""
import json
import pathlib
import unreal

audit_root = pathlib.Path(unreal.Paths.project_dir()).resolve()
if audit_root != pathlib.Path('C:/Users/user/Desktop/GitProject/Khazan_HealWork_20261006/Khazan').resolve():
    raise RuntimeError('Heal audit requires the isolated project')

audit = {}
for asset_path in (
    '/Game/Bluprints/AbilitySystem/Effects/GE_Init_PlayerHealth',
    '/Game/Bluprints/AbilitySystem/Effects/GE_Player_Heal',
    '/Game/Bluprints/AbilitySystem/Abilities/Player/Heal/GA_Player_Heal',
):
    bp = unreal.EditorAssetLibrary.load_asset(asset_path)
    cdo = unreal.get_default_object(bp.generated_class())
    row = dict(class_path=bp.generated_class().get_path_name())
    if '/Effects/' in asset_path:
        row['duration_policy'] = str(cdo.get_editor_property('duration_policy'))
        row['modifiers'] = [m.export_text() for m in cdo.get_editor_property('modifiers')]
    else:
        row['montage'] = cdo.get_editor_property('HealMontage').get_path_name()
        row['effect'] = cdo.get_editor_property('HealEffect').get_path_name()
        row['cost'] = str(cdo.get_editor_property('cost_gameplay_effect_class'))
        row['cooldown'] = str(cdo.get_editor_property('cooldown_gameplay_effect_class'))
    audit[asset_path] = row

clip = unreal.EditorAssetLibrary.load_asset('/Game/_Art/Player/Animation/InGame/DAS/Heal/CA_P_Kazan_DualAxeSword_Heal_01')
audit['clip'] = dict(rate_scale=clip.get_editor_property('rate_scale'), enable_root_motion=clip.get_editor_property('enable_root_motion'))
montage = unreal.EditorAssetLibrary.load_asset('/Game/_Art/Player/Animation/InGame/DAS/Heal/AM_DAS_Player_Heal')
audit['montage'] = dict(
    slots=[t.export_text() for t in montage.get_editor_property('slot_anim_tracks')],
    sections=[str(montage.get_section_name(i)) for i in range(montage.get_num_sections())],
    blend_in=montage.get_editor_property('blend_in').export_text(),
    blend_out=montage.get_editor_property('blend_out').export_text(),
)
audit['notify_validation'] = 'Heal/InputEnd delivery and once/cancel semantics were validated by native Khazan.Heal.PIE; protected Notifies property is not read by Python.'
abp = unreal.EditorAssetLibrary.load_asset('/Game/_Art/Player/Character/Bluprints/ABP_Player')
audit['abp_status'] = str(abp.get_editor_property('status'))
input_data = unreal.EditorAssetLibrary.load_asset('/Game/Data/DA_InputData')
audit['input_rows'] = [r.export_text() for r in input_data.get_editor_property('InputActions')]
imc = input_data.get_editor_property('InputMappingContext')
audit['input_mappings'] = [m.export_text() for m in imc.get_editor_property('default_key_mappings').get_editor_property('mappings')]
definition = unreal.EditorAssetLibrary.load_asset('/Game/Data/Character/DA_CharacterDefinition_Player')
audit['initial_grants'] = [g.export_text() for g in definition.get_editor_property('InitialAbilityGrants')]
audit['initial_effects'] = [e.get_path_name() for e in definition.get_editor_property('InitialEffects')]
audit['locomotion_config'] = definition.get_editor_property('LocomotionConfig').export_text()
subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
game_world = subsystem.get_game_world()
audit['worlds'] = dict(editor=subsystem.get_editor_world().get_path_name(), game=game_world.get_path_name() if game_world else None)
audit['dirty_content'] = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
audit['dirty_maps'] = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
destination = audit_root / 'Saved/HealAssetAudit.json'
destination.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(dict(audit_file=str(destination), abp_status=audit['abp_status'], worlds=audit['worlds'], dirty_content=audit['dirty_content'], dirty_maps=audit['dirty_maps']), ensure_ascii=False))
