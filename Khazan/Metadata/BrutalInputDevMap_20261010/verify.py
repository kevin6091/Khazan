"""Fresh owned Main editor: saved reads, passive PIE observation, existing native QA.

No Python player input, transforms, ability activation, asset edits or saves.
"""
from pathlib import Path
from collections import Counter
import unreal, json, os, time, hashlib, traceback, ctypes
from ctypes import wintypes

ROOT=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan').resolve()
OUT=ROOT/'Metadata/BrutalInputDevMap_20261010'
assert Path(unreal.Paths.project_dir()).resolve()==ROOT
assert not (OUT/'FreshSavedVerification02.json').exists()
report=dict(success=False,pid=os.getpid(),project=str(ROOT),read_only_assets=True,python_player_input=False,checks=0)
runtime=dict(success=False,pid=os.getpid(),passive_observation=True,python_player_input=False)
subsystem=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
world=subsystem.get_editor_world()
handle=None
performance=None
original_throttle=None
started=time.monotonic()
stage='saved'
native_pie_requested=False
test_name='Khazan.Monster.CombatPolicyPIE'
log_file=OUT/'Verify02.log'

def path(value): return value.get_path_name() if value else None
def vec(value): return [float(value.x),float(value.y),float(value.z)]
def sha(file): return hashlib.sha256(file.read_bytes()).hexdigest() if file.is_file() else None
def need(condition,message):
    report['checks']+=1
    assert condition,message
def write(name,value): (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def dirty(): return dict(content=[path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()],maps=[path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
def console(command): unreal.SystemLibrary.execute_console_command(subsystem.get_game_world() or subsystem.get_editor_world(),command)
def complete(error=None):
    global handle
    if handle is not None:
        unreal.unregister_slate_post_tick_callback(handle)
        handle=None
    if error: runtime.update(error=str(error),traceback=traceback.format_exc())
    if performance is not None:
        performance.set_editor_property('bThrottleCPUWhenNotForeground',original_throttle,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
        runtime['throttle_restored']=performance.get_editor_property('bThrottleCPUWhenNotForeground')==original_throttle
    runtime['final_dirty']=dirty()
    runtime['final_hashes']={relative:sha(ROOT/relative) for relative in expected_hashes}
    runtime['saved_bytes_unchanged']=runtime['final_hashes']==expected_hashes
    if runtime['success']:
        runtime['success']=runtime['saved_bytes_unchanged'] and not any(runtime['final_dirty'].values())
    write('FreshPIEVerification02.json',runtime)
    console('QUIT_EDITOR')

expected_hashes={}
try:
    author=json.loads((OUT/'Authoring09.json').read_text(encoding='utf-8'))
    need(author['success'] and len(set(author['saved']))==5,'Authoring has not completed')
    expected_hashes=author['after']
    need({relative:sha(ROOT/relative) for relative in expected_hashes}==expected_hashes,'Saved assets changed since authoring')
    need(subsystem.get_game_world() is None and not any(dirty().values()),'Fresh saved audit requires clean editor')
    manifest_file=ROOT/'Binaries/Win64/UnrealEditor.modules'
    manifest=json.loads(manifest_file.read_text(encoding='utf-8-sig'))
    module=(manifest_file.parent/manifest['Modules']['Khazan']).resolve()
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetModuleHandleW.argtypes=[wintypes.LPCWSTR]
    kernel.GetModuleHandleW.restype=wintypes.HMODULE
    kernel.GetModuleFileNameW.argtypes=[wintypes.HMODULE,wintypes.LPWSTR,wintypes.DWORD]
    kernel.GetModuleFileNameW.restype=wintypes.DWORD
    module_handle=kernel.GetModuleHandleW(module.name)
    need(bool(module_handle),'Current selected Khazan module is not actually loaded')
    buffer=ctypes.create_unicode_buffer(32768)
    need(0<kernel.GetModuleFileNameW(module_handle,buffer,len(buffer))<len(buffer),'Cannot read own module')
    need(Path(buffer.value).resolve()==module,'Own loaded module differs from manifest')
    report['loaded_module']=dict(path=str(module),sha256=sha(module),build_id=manifest['BuildId'])
    data=unreal.load_asset('/Game/Data/DA_InputData')
    mapping=data.get_editor_property('InputMappingContext')
    mappings=list(mapping.get_editor_property('DefaultKeyMappings').get_editor_property('Mappings'))
    inputs=list(data.get_editor_property('InputActions'))
    definition=unreal.load_asset('/Game/Data/Character/DA_CharacterDefinition_Player')
    grants=list(definition.get_editor_property('InitialAbilityGrants'))
    for name,rows in [('mappings',mappings),('inputs',inputs),('grants',grants)]:
        report[name]=[row.export_text() for row in rows]
        need(report[name]==author[name+'_after'],'Fresh serialized '+name+' differs')
    b_rows=[row for row in mappings if str(row.get_editor_property('Key').get_editor_property('KeyName'))=='Gamepad_FaceButton_Right']
    need(len(b_rows)==1 and path(b_rows[0].get_editor_property('Action'))=='/Game/Input/IA_BrutalAttack.IA_BrutalAttack','Physical gamepad B mapping missing')
    brutal_rows=[row for row in grants if path(row.get_editor_property('AbilityClass'))=='/Script/Khazan.KZBrutalAttackAbility']
    need(len(brutal_rows)==1 and brutal_rows[0].get_editor_property('InputTag').export_text()=='(TagName="Input.Action.B")','Brutal grant does not consume B')
    action=unreal.load_asset('/Game/Input/IA_BrutalAttack')
    need(action.get_editor_property('ValueType')==unreal.InputActionValueType.BOOLEAN,'Brutal input must be boolean')
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    actor_by_name={a.get_name():a for a in actors}
    floor=next(a for a in actors if a.get_actor_label()=='Floor' and isinstance(a,unreal.StaticMeshActor))
    origin,extent=floor.get_actor_bounds(False)
    report['floor']=dict(location=vec(floor.get_actor_location()),scale=vec(floor.get_actor_scale3d()),origin=vec(origin),extent=vec(extent),mesh=path(floor.static_mesh_component.static_mesh),collision=str(floor.static_mesh_component.get_collision_enabled()))
    need(report['floor']['scale']==author['floor_after']['scale'] and report['floor']['extent']==author['floor_after']['extent'],'Expanded floor not serialized')
    probe=json.loads((OUT/'Probe02.json').read_text(encoding='utf-8'))
    original_floor=next(a for a in probe['actors'] if a['label']=='Floor')
    need(report['floor']['location']==original_floor['location'] and report['floor']['collision']==original_floor['collision'] and report['floor']['mesh']==original_floor['mesh'],'Floor height/mesh/collision changed')
    for old in author['existing_monsters']:
        actor=actor_by_name.get(old['name'])
        need(actor is not None and actor.get_actor_label()==old['label'] and vec(actor.get_actor_location())==old['location'],'Original human placement changed: '+old['name'])
    report['monsters']=[]
    for actor in actors:
        cls_path=path(actor.get_class())
        if cls_path.startswith('/Game/Bluprints/Monsters/BP_Monster_'):
            report['monsters'].append(dict(name=actor.get_name(),label=actor.get_actor_label(),class_path=cls_path,location=vec(actor.get_actor_location()),rotation=actor.get_actor_rotation().export_text(),scale=vec(actor.get_actor_scale3d()),state_tree=path(actor.get_editor_property('AIStateTree'))))
    report['family_counts']=dict(Counter(row['class_path'].split('BP_Monster_')[1].split('.')[0] for row in report['monsters']))
    need(report['family_counts']==dict(Swordsman=7,SwordShield=1,HeavySwordsman=1,HalberdElite=1,ApesStoneHandElite=1,Yetuga=1),'DevMap six family population differs')
    nav=next(a for a in actors if isinstance(a,unreal.NavMeshBoundsVolume))
    need(vec(nav.get_actor_scale3d())==author['nav_after'],'Navigation volume scale not saved')
    points=[unreal.Vector(x,y,0) for x,y in [(5500,-2200),(5500,2200),(-14000,0),(14000,0),(0,-14000),(0,14000)]]
    projected=[unreal.NavigationSystemV1.project_point_to_navigation(world,p,None,None,unreal.Vector(100,100,500)) for p in points]
    need(all(p is not None for p in projected),'Saved expanded navmesh lacks required points')
    report['navigation_points']=[vec(p) for p in projected]
    report['dirty']=dirty()
    need(not any(report['dirty'].values()),'Saved readback dirtied assets')
    report['success']=True
    write('FreshSavedVerification02.json',report)
    performance=unreal.get_default_object(unreal.load_class(None,'/Script/UnrealEd.EditorPerformanceSettings'))
    original_throttle=performance.get_editor_property('bThrottleCPUWhenNotForeground')
    performance.set_editor_property('bThrottleCPUWhenNotForeground',False,notify_mode=unreal.PropertyAccessChangeNotifyMode.NEVER)
    monster_class=unreal.load_class(None,'/Script/Khazan.KZMonster')
    expected_stats=dict(Swordsman=(100,50),SwordShield=(100,50),HeavySwordsman=(200,50),HalberdElite=(200,50),ApesStoneHandElite=(400,100),Yetuga=(1000,150))
    stage='passive_pie'
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
    def tick(delta):
        global stage,native_pie_requested
        try:
            need(time.monotonic()-started<420,'Fresh PIE observation/native policy QA timeout')
            game=subsystem.get_game_world()
            if stage=='passive_pie':
                if game is None or unreal.GameplayStatics.get_time_seconds(game)<1: return
                monsters=unreal.GameplayStatics.get_all_actors_of_class(game,monster_class)
                need(len(monsters)==12,'PIE did not create all twelve saved monsters')
                rows=[]
                for actor in monsters:
                    family=path(actor.get_class()).split('BP_Monster_')[1].split('.')[0]
                    attr=actor.get_editor_property('AttributeSet')
                    asc=actor.get_editor_property('AbilitySystemComponent')
                    definition=actor.get_editor_property('CharacterDefinition')
                    mesh=actor.get_component_by_class(unreal.SkeletalMeshComponent)
                    need(attr and asc and definition and mesh and mesh.get_anim_instance(),'Missing initialized live character/animation: '+family)
                    values={name:float(attr.get_editor_property(name).get_editor_property('CurrentValue')) for name in ('HP','MaxHP','Stamina','MaxStamina')}
                    hp,stamina=expected_stats[family]
                    need(values==dict(HP=hp,MaxHP=hp,Stamina=stamina,MaxStamina=stamina),'Live six-family initial stats differ: '+family)
                    rows.append(dict(family=family,label=actor.get_actor_label(),definition=path(definition),asc=path(asc),animation_instance=path(mesh.get_anim_instance()),values=values,location=vec(actor.get_actor_location())))
                runtime['live_monsters']=rows
                runtime['six_family_initialization_success']=True
                stage='before_native'
                unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
            elif stage=='before_native':
                if game is not None: return
                stage='native'
                console('Automation RunTests '+test_name)
            elif stage=='native':
                text=log_file.read_text(encoding='utf-8',errors='replace')
                completions=[line for line in text.splitlines() if 'Test Completed.' in line and ('Path={'+test_name+'}') in line]
                if completions:
                    runtime['native_test']=dict(path=test_name,completion=completions[-1],success='Result={Success}' in completions[-1])
                    need(runtime['native_test']['success'],'Native combat policy test failed')
                    stage='finished'
                    if game is not None:
                        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
                    return
                if not native_pie_requested and 'Test Started.' in text and ('Path={'+test_name+'}') in text and game is None:
                    native_pie_requested=True
                    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
            elif stage=='finished':
                if game is not None: return
                runtime['success']=True
                runtime['elapsed_seconds']=time.monotonic()-started
                complete()
        except Exception as error: complete(error)
    handle=unreal.register_slate_post_tick_callback(tick)
except Exception as error:
    report.update(error=str(error),traceback=traceback.format_exc())
    write('FreshSavedVerification02.json',report)
    complete(error)
