"""Targeted saved inputs; source packages/resources are kept intact."""
from pathlib import Path
import os,json,csv,unreal,hashlib,shutil
ROOT=Path(unreal.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_COMBAT_FINISH_OUT'])
result={'families':[],'montages':[],'fall':[]}
exporter=unreal.ObjectExporterT3D();assets=unreal.EditorAssetLibrary
def export(obj, name):
    task=unreal.AssetExportTask();task.object=obj;task.filename=str(OUT/(name+'.t3d'));task.exporter=exporter;task.automated=True;task.prompt=False
    assert unreal.Exporter.run_asset_export_task(task)
def save_before(asset):
    p=ROOT/('Content/'+asset.split('.')[0].removeprefix('/Game/')+'.uasset')
    dest=ROOT/'Metadata/CombatFinishFollowup_20261012/AssetsBefore'/p.relative_to(ROOT)
    if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
for family in ['Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga']:
    definition=unreal.load_asset('/Game/Monsters/'+family+'/Data/DA_Character_'+family)
    settings=definition.get_editor_property('monster_stamina');death=settings.get_editor_property('death_presentation_montage')
    export(definition,'Definition_'+family);export(death,'Death_'+family)
    save_before(death.get_path_name())
    for key in ['brutal_front_victim_montage','brutal_back_victim_montage']:
        export(settings.get_editor_property(key),'Victim_'+family+'_'+key)
    result['families'].append({'family':family,'definition':definition.get_path_name(),'death':death.get_path_name(),'length':death.get_play_length(),'auto_blend_out':death.get_editor_property('enable_auto_blend_out')})
windows=list(csv.DictReader((ROOT/'Saved/ImportReports/PlayerAttackVFX_20261008/CombinedPlaybackWindows.csv').open(encoding='utf-8')))
paths=sorted(set(x['montage'] for x in windows))
for index,path in enumerate(paths):
    asset=unreal.load_asset(path);export(asset,'PlayerMontage_'+str(index));save_before(path)
    result['montages'].append({'path':path,'export':'PlayerMontage_'+str(index)+'.t3d'})
for path in ['/Game/_Art/Player/Animation/InGame/DAS/FallAttack/AM_DAS_FallAttack','/Game/_Art/Player/Animation/InGame/DAS/Fall/AM_DAS_Fall']:
    export(unreal.load_asset(path),'Fall_'+path.rsplit('/',1)[-1].split('.')[0]);save_before(path);result['fall'].append(path)
guard=unreal.EditorAssetLibrary.load_blueprint_class('/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard')
export(unreal.get_default_object(guard),'GuardCDO')
result['dirty']=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
(OUT/'Inputs.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('TARGETED_PROBE',len(result['families']),len(result['montages']),len(result['fall']))
