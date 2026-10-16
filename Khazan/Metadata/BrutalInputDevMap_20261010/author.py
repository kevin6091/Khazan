"""Caller-owned background editor authoring only; no PIE input or movement."""
from pathlib import Path
import unreal, json, hashlib, shutil, time, os, traceback

ROOT=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
OUT=ROOT/'Metadata/BrutalInputDevMap_20261010'
assert Path(unreal.Paths.project_dir()).resolve()==ROOT
assert not (OUT/'Authoring09.json').exists(), 'Keep earlier receipts'
report=dict(success=False,pid=os.getpid(),saved=[],world='/Game/Maps/DevMap')
editor=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=editor.get_editor_world()
actor_system=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
handle=None
navigation_settings=None
original_nav_update=None
performance=None
original_throttle=None
rebuild_requested=False
finishing=False
def path(value): return value.get_path_name() if value else None
def vec(value): return [float(value.x),float(value.y),float(value.z)]
def sha(file): return hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else None
def tag(value): return value.export_text()
def complete(error=None):
    global handle
    if handle is not None:
        unreal.unregister_slate_post_tick_callback(handle)
        handle=None
    if error: report.update(error=str(error),traceback=traceback.format_exc())
    if navigation_settings is not None and original_nav_update is not None:
        navigation_settings.set_editor_property('bNavigationAutoUpdate',original_nav_update,notify_mode=unreal.PropertyAccessChangeNotifyMode.ALWAYS)
        report['navigation_auto_update_restored']=navigation_settings.get_editor_property('bNavigationAutoUpdate')==original_nav_update
    if performance is not None:
        performance.set_editor_property('bThrottleCPUWhenNotForeground',original_throttle,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
        report['throttle_restored']=performance.get_editor_property('bThrottleCPUWhenNotForeground')==original_throttle
    (OUT/'Authoring09.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    unreal.SystemLibrary.execute_console_command(world,'QUIT_EDITOR')

try:
    assert world and world.get_path_name().split('.')[0]=='/Game/Maps/DevMap'
    packages=['/Game/Input/IMC_Default','/Game/Data/DA_InputData',
              '/Game/Data/Character/DA_CharacterDefinition_Player','/Game/Maps/DevMap',
              '/Game/Input/IA_BrutalAttack']
    before={}
    for package in packages:
        relative='Content/'+package[6:]+('.umap' if package=='/Game/Maps/DevMap' else '.uasset')
        file=ROOT/relative
        before[relative]=sha(file)
        backup=OUT/'Before'/relative
        assert not backup.exists() or sha(backup)==sha(file), relative
        if file.is_file():
            backup.parent.mkdir(parents=True,exist_ok=True)
            if not backup.exists(): shutil.copy2(file,backup)
    report['before']=before
    assert json.loads((OUT/'AssetBefore.json').read_text(encoding='utf-8'))==before, 'Assets changed after unsaved first attempt'

    data=unreal.load_asset('/Game/Data/DA_InputData')
    definition=unreal.load_asset('/Game/Data/Character/DA_CharacterDefinition_Player')
    mapping=data.get_editor_property('InputMappingContext')
    assert path(mapping)=='/Game/Input/IMC_Default.IMC_Default'
    def mappings(): return mapping.get_editor_property('DefaultKeyMappings').get_editor_property('Mappings')
    report['mappings_before']=[row.export_text() for row in mappings()]
    assert all(str(row.get_editor_property('Key').get_editor_property('KeyName'))!='Gamepad_FaceButton_Right' for row in mappings()), 'B already bound'
    inputs=list(data.get_editor_property('InputActions'))
    report['inputs_before']=[row.export_text() for row in inputs]
    grants=list(definition.get_editor_property('InitialAbilityGrants'))
    report['grants_before']=[row.export_text() for row in grants]
    new_tag=unreal.GameplayTag()
    new_tag.import_text('(TagName="Input.Action.B")')
    assert new_tag.export_text()=='(TagName="Input.Action.B")'
    action=unreal.AssetToolsHelpers.get_asset_tools().create_asset('IA_BrutalAttack','/Game/Input',unreal.InputAction,unreal.InputAction_Factory())
    assert action
    action.set_editor_property('ValueType',unreal.InputActionValueType.BOOLEAN)
    row=inputs[0].copy()
    assert row.import_text('(InputTag=(TagName="Input.Action.B"),InputAction="/Script/EnhancedInput.InputAction\'/Game/Input/IA_BrutalAttack.IA_BrutalAttack\'")')
    inputs.append(row)
    data.set_editor_property('InputActions',inputs)
    key=unreal.Key()
    key.import_text('Gamepad_FaceButton_Right')
    mapping.map_key(action,key)
    brutal_rows=[row for row in grants if path(row.get_editor_property('AbilityClass'))=='/Script/Khazan.KZBrutalAttackAbility']
    assert len(brutal_rows)==1 and tag(brutal_rows[0].get_editor_property('InputTag'))=='(TagName="Input.Action.X")'
    brutal_rows[0].set_editor_property('InputTag',new_tag)
    definition.set_editor_property('InitialAbilityGrants',grants)
    report['mappings_after']=[row.export_text() for row in mappings()]
    report['inputs_after']=[row.export_text() for row in data.get_editor_property('InputActions')]
    report['grants_after']=[row.export_text() for row in definition.get_editor_property('InitialAbilityGrants')]
    assert report['mappings_after'][:-1]==report['mappings_before']
    assert report['inputs_after'][:-1]==report['inputs_before']
    assert sum(a!=b for a,b in zip(report['grants_before'],report['grants_after']))==1

    actors=actor_system.get_all_level_actors()
    floors=[actor for actor in actors if actor.get_actor_label()=='Floor' and isinstance(actor,unreal.StaticMeshActor)]
    assert len(floors)==1
    floor=floors[0]
    old_scale=floor.get_actor_scale3d()
    origin,extent=floor.get_actor_bounds(False)
    report['floor_before']=dict(scale=vec(old_scale),origin=vec(origin),extent=vec(extent),mesh=path(floor.static_mesh_component.static_mesh))
    floor.set_actor_scale3d(unreal.Vector(old_scale.x*4,old_scale.y*4,old_scale.z))
    origin,extent=floor.get_actor_bounds(False)
    report['floor_after']=dict(scale=vec(floor.get_actor_scale3d()),origin=vec(origin),extent=vec(extent),mesh=path(floor.static_mesh_component.static_mesh))
    assert abs(extent.x/report['floor_before']['extent'][0]-4)<0.001
    assert abs(extent.y/report['floor_before']['extent'][1]-4)<0.001
    bounds=[actor for actor in actors if isinstance(actor,unreal.NavMeshBoundsVolume)]
    assert len(bounds)==1
    navigation=bounds[0]
    old_nav_scale=navigation.get_actor_scale3d()
    report['nav_before']=vec(old_nav_scale)
    navigation.set_actor_scale3d(unreal.Vector(old_nav_scale.x*4,old_nav_scale.y*4,old_nav_scale.z))
    report['nav_after']=vec(navigation.get_actor_scale3d())
    families=('Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga')
    report['existing_monsters']=[dict(name=actor.get_name(),label=actor.get_actor_label(),location=vec(actor.get_actor_location()))
                                 for actor in actors if path(actor.get_class()).startswith('/Game/Bluprints/Monsters/BP_Monster_')]
    report['created_monsters']=[]
    for family,y in [('ApesStoneHandElite',-2200),('Yetuga',2200)]:
        cls=unreal.load_class(None,f'/Game/Bluprints/Monsters/BP_Monster_{family}.BP_Monster_{family}_C')
        assert cls and not any(actor.get_class()==cls for actor in actors), family
        cdo=unreal.get_default_object(cls)
        height=cdo.get_component_by_class(unreal.CapsuleComponent).get_scaled_capsule_half_height()
        actor=actor_system.spawn_actor_from_class(cls,unreal.Vector(5500,y,height),unreal.Rotator(0,180,0))
        assert actor
        actor.set_actor_label('DevTest_'+family)
        actor.set_folder_path('DevMap/Monsters/Beasts')
        report['created_monsters'].append(dict(name=actor.get_name(),label=actor.get_actor_label(),family=family,location=vec(actor.get_actor_location())))
    for family in families:
        cls=unreal.load_class(None,f'/Game/Bluprints/Monsters/BP_Monster_{family}.BP_Monster_{family}_C')
        assert any(actor.get_class()==cls for actor in actor_system.get_all_level_actors()), family
    report['temporary_layout']=dict(floor_xy_multiplier=4,floor_area_multiplier=16,beast_x_cm=5500,beast_y_cm=[-2200,2200],source='User requested much larger DevMap; assistant test layout, not original metadata')
    started=time.monotonic()
    performance=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
    original_throttle=performance.get_editor_property('bThrottleCPUWhenNotForeground')
    performance.set_editor_property('bThrottleCPUWhenNotForeground',False,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    navigation_settings_class=unreal.load_class(None,'/Script/UnrealEd.LevelEditorMiscSettings')
    assert navigation_settings_class, 'Missing editor navigation settings class'
    navigation_settings=unreal.get_default_object(navigation_settings_class)
    original_nav_update=navigation_settings.get_editor_property('bNavigationAutoUpdate')
    report['navigation_auto_update_before']=original_nav_update
    navigation_settings.set_editor_property('bNavigationAutoUpdate',True,notify_mode=unreal.PropertyAccessChangeNotifyMode.ALWAYS)
    points=[unreal.Vector(x,y,0) for x,y in [(5500,-2200),(5500,2200),(-14000,0),(14000,0),(0,-14000),(0,14000)]]
    def finish_tick(delta):
        global rebuild_requested,finishing,handle
        try:
            if finishing: return
            if time.monotonic()-started<2: return
            if unreal.NavigationSystemV1.is_navigation_being_built_or_locked(world):
                assert time.monotonic()-started<180,'Navigation load/build lock timeout'
                return
            if not rebuild_requested:
                unreal.NavigationSystemV1.get_navigation_system(world).on_navigation_bounds_updated(navigation)
                unreal.SystemLibrary.execute_console_command(world,'RebuildNavigation')
                rebuild_requested=True
                report['rebuild_requested_after_unlocked']=True
                return
            projected=[unreal.NavigationSystemV1.project_point_to_navigation(world,point,None,None,unreal.Vector(100,100,500)) for point in points]
            if any(point is None for point in projected):
                assert time.monotonic()-started<180,'Expanded navigation missing test points'
                return
            report['navigation_points']=[vec(point) for point in projected]
            # Asset saves pump Slate; remove the callback before entering save APIs.
            finishing=True
            unreal.unregister_slate_post_tick_callback(handle)
            handle=None
            for relative,expected in before.items():
                assert sha(ROOT/relative)==expected,'Concurrent Main asset change: '+relative
            for package in (packages[0],packages[1],packages[2],packages[4]):
                assert unreal.EditorAssetLibrary.save_asset(package,only_if_is_dirty=False),package
                report['saved'].append(package)
            assert unreal.EditorLoadingAndSavingUtils.save_map(world,'/Game/Maps/DevMap')
            report['saved'].append('/Game/Maps/DevMap')
            report['after']={relative:sha(ROOT/relative) for relative in before}
            report['dirty_maps']=[path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
            report['dirty_content']=[path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
            report['success']=not report['dirty_maps'] and not report['dirty_content']
            complete()
        except Exception as error: complete(error)
    handle=unreal.register_slate_post_tick_callback(finish_tick)
except Exception as error:
    complete(error)
