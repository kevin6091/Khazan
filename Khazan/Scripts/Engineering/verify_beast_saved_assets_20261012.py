"""Fresh readback of selected asset contracts; save nothing."""
from pathlib import Path
import json
import os
import unreal

project=Path(unreal.Paths.project_dir()).resolve()
main=Path(__file__).resolve().parents[2]
assert project==main or project==main.parent.parent/'Khazan_BeastDodgeWork_20261012/Khazan'
report={'status':'checking','project':str(project),'dodges':[],'families':[],'source_vfx_files_changed':False}
registry=unreal.AssetRegistryHelpers.get_asset_registry()
for data in registry.get_assets_by_path('/Game/Bluprints/AbilitySystem/Abilities/Player/Dodge',recursive=True):
    if str(data.asset_class_path.asset_name)!='Blueprint':continue
    bp=data.get_asset();c=unreal.get_default_object(unreal.load_class(None,bp.get_path_name()+'_C'))
    if not isinstance(c,unreal.KZDodgeAbility):continue
    row={'asset':bp.get_path_name(),'invulnerability_seconds':c.get_editor_property('invulnerability_seconds'),'dodge_scale':c.get_editor_property('dodge_effect_scale'),'success_scale':c.get_editor_property('success_effect_scale')}
    for key in ('dodge_effect','success_effect','success_sound'):
        value=c.get_editor_property(key);assert value;row[key]=value.get_path_name()
    assert abs(row['invulnerability_seconds']-.1)<1e-6
    assert abs(row['dodge_scale']-.12)<1e-6 and abs(row['success_scale']-.15)<1e-6
    report['dodges'].append(row)
assert len(report['dodges'])==8
for family,expected in [('ApesStoneHandElite',19),('Yetuga',28)]:
    base='/Game/Monsters/'+family
    definition=unreal.load_asset(base+'/Data/DA_Character_'+family)
    assert definition
    grants=list(definition.get_editor_property('initial_ability_grants'))
    classes=[g.get_editor_property('ability_class') for g in grants]
    patterns=[c for c in classes if c and isinstance(unreal.get_default_object(c),unreal.KZMonsterPatternAbility)]
    assert len(patterns)==expected,(family,len(patterns))
    tree=definition.get_editor_property('original_pattern_state_tree');assert tree
    report['families'].append({'family':family,'state_tree':tree.get_path_name(),'pattern_grants':len(patterns),'class_paths':[c.get_path_name() for c in patterns]})
report['status']='passed'
(Path(os.environ['KZ_BEAST_OUT'])/'SavedAssets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SAVED_BEAST_ASSETS '+json.dumps(report),flush=True)
