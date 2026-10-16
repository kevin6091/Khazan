"""Scoped Main commandlet: author user-chosen temporary total HP damage50, or fresh readback."""
import datetime, hashlib, json, os, pathlib, shutil, unreal
MAIN = pathlib.Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
OUT = MAIN/'Metadata/MonsterBrutalDamage50_20261008'
assert pathlib.Path(unreal.Paths.project_dir()).resolve() == MAIN
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()
assert not unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()
VERIFY = '-BrutalDamageVerify' in unreal.SystemLibrary.get_command_line()
VALUE = 50.0  # User-selected temporary HP points per complete Brutal Attack; not original metadata.
FAMILIES = ('Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga')
OTHER_SETTINGS = ('enabled','parry_stamina_damage','exhaustion_seconds','exhaustion_montage',
    'brutal_attack_range','brutal_alignment_distance','brutal_front_player_montage','brutal_back_player_montage',
    'brutal_front_victim_montage','brutal_back_victim_montage','damage_effect','dead_state_effect')
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def value(v):
    if isinstance(v,unreal.Object): return v.get_path_name()
    if hasattr(v,'export_text'): return v.export_text()
    if isinstance(v,(str,int,float,bool)) or v is None: return v
    return [value(i) for i in v]
def snapshot(obj):
    settings = obj.get_editor_property('monster_stamina')
    result = {field:value(obj.get_editor_property(field)) for field in
        ('locomotion_config','unaware_routines','initial_ability_grants','initial_effects')}
    result['other_stamina_settings'] = {field:value(settings.get_editor_property(field)) for field in OTHER_SETTINGS}
    return result
report = dict(mode='verify' if VERIFY else 'author',pid=os.getpid(),project=str(MAIN),success=False,
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),value=VALUE,provenance='User-requested temporary tuning',rows=[])
OUT.mkdir(parents=True,exist_ok=True)
target = OUT/('FreshSavedReadback.json' if VERIFY else 'Authoring.json')
assert not target.exists(), 'Preserve prior result'
def record(): target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
try:
    loaded = []
    previous = json.loads((OUT/'Authoring.json').read_text(encoding='utf-8')) if VERIFY else None
    if VERIFY: assert previous['success']
    for family in FAMILIES:
        package='/Game/Monsters/'+family+'/Data/DA_Character_'+family
        filename=MAIN/('Content/'+package.removeprefix('/Game/')+'.uasset')
        obj=unreal.load_asset(package); assert obj and obj.get_class().get_name()=='KZCharacterDefinitionData'
        before=snapshot(obj); damage=float(obj.get_editor_property('monster_stamina').get_editor_property('brutal_hp_damage'))
        loaded.append((family,package,filename,obj,before,damage))
    for family,package,filename,obj,before,damage in loaded:
        row=dict(family=family,package=package,damage_before=damage,hash_before=sha(filename),other_fields=before)
        report['rows'].append(row); record()
        if VERIFY:
            authored=next(r for r in previous['rows'] if r['family']==family)
            assert damage==VALUE and before==authored['other_fields']
            assert sha(filename)==authored['hash_after']
            row.update(damage_after=damage,hash_after=sha(filename),other_fields_unchanged=True)
        else:
            backup=OUT/'Before'/filename.relative_to(MAIN)
            assert not backup.exists(); backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(filename,backup)
            assert sha(backup)==row['hash_before']
            settings=obj.get_editor_property('monster_stamina')
            settings.set_editor_property('brutal_hp_damage',VALUE)
            obj.set_editor_property('monster_stamina',settings)
            assert snapshot(obj)==before
            assert unreal.EditorAssetLibrary.save_loaded_asset(obj,only_if_is_dirty=False),package
            row.update(damage_after=float(obj.get_editor_property('monster_stamina').get_editor_property('brutal_hp_damage')),
                hash_after=sha(filename),other_fields_unchanged=True,saved=True)
            assert row['damage_after']==VALUE
        record()
    report.update(success=True,dirty_content=[p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
        dirty_map=[p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
    assert not report['dirty_content'] and not report['dirty_map']
    record(); print('MonsterBrutalDamage50Complete='+json.dumps(dict(mode=report['mode'],success=True,pid=os.getpid(),families=len(report['rows']),damage=VALUE)))
except Exception as error:
    report['error']=str(error); record(); raise
