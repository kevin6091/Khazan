"""Cold, read-only saved-package inspection. No actor movement, input, or asset save."""
from pathlib import Path
import ctypes, json, traceback
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
ALLOWED=[Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan'),Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')]
assert ROOT in ALLOWED,ROOT
OUT=ROOT/'Metadata/GiantCombatFall_20261011'
REPORT={'project':str(ROOT),'read_only':True,'errors':[],'families':[]}
def prop(o,n):return o.get_editor_property(n)
def path(o):return o.get_path_name() if o else None
def check(ok,message):
    if not ok:REPORT['errors'].append(message)
try:
    manifest=json.loads((ROOT/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.GetModuleHandleW.argtypes=[ctypes.c_wchar_p];k.GetModuleHandleW.restype=ctypes.c_void_p
    k.GetModuleFileNameW.argtypes=[ctypes.c_void_p,ctypes.c_wchar_p,ctypes.c_uint];k.GetModuleFileNameW.restype=ctypes.c_uint
    buf=ctypes.create_unicode_buffer(32768);h=k.GetModuleHandleW(manifest['Modules']['Khazan'])
    assert h and k.GetModuleFileNameW(h,buf,len(buf))
    REPORT['loaded_module']=buf.value
    assert Path(buf.value).resolve().is_relative_to(ROOT/'Binaries'),buf.value
    authored=json.loads((OUT/'AuthoringReport.json').read_text(encoding='utf-8'))
    packages=sorted(set(authored['saved_packages']))
    REPORT['packages']=len(packages)
    for p in packages:
        obj=unreal.load_asset(p)
        check(obj is not None,'Missing saved package: '+p)
        if isinstance(obj,unreal.Blueprint):
            check(unreal.load_class(None,p+'.'+p.rsplit('/',1)[-1]+'_C') is not None,'Missing generated class: '+p)
    for family,count,entries,choices in [('ApesStoneHandElite',48,19,10),('Yetuga',81,24,28)]:
        base='/Game/Monsters/'+family
        combo=unreal.load_asset(base+'/Data/DA_OriginalPatterns_'+family)
        nodes=list(prop(combo,'nodes'))
        montage=unreal.load_asset(base+'/Animations/AM_OriginalPatterns_'+family)
        row={'family':family,'nodes':len(nodes),'fastball':[]}
        check(len(nodes)==count,family+' source node count')
        ids={str(prop(n,'node_id')) for n in nodes}
        for n in nodes:
            for b in prop(n,'pattern_branches'):
                target=str(prop(b,'target_node'))
                check(target in ids or target=='PatternFinish',family+' dangling source branch: '+target)
            target=str(prop(n,'automatic_next_node'))
            check(target in ids or target=='None',family+' dangling automatic step: '+target)
        for n in nodes:
            nid=str(prop(n,'node_id'))
            if nid.startswith('FastBall_'):
                section_index=montage.get_section_index(prop(n,'section_name'))
                segment=prop(prop(montage,'slot_anim_tracks')[0],'anim_track').get_editor_property('anim_segments')[section_index]
                clip=prop(segment,'anim_reference')
                row['fastball'].append({'node':nid,'clip':path(clip),'seconds':clip.get_play_length(),'clip_rate':prop(clip,'rate_scale'),'segment_rate':prop(segment,'anim_play_rate'),
                    'actions':[{'action':str(prop(a,'action')),'event':str(prop(a,'event')),'notify':str(prop(a,'notify')),'object':str(prop(a,'object_id'))} for a in prop(n,'pattern_actions')]})
        owned=[p for p in packages if p.startswith(base+'/Abilities/GA_Original_')]
        check(len(owned)==entries,family+' source ability count')
        row['abilities']=len(owned)
        for p in owned:
            cdo=unreal.get_default_object(unreal.load_class(None,p+'.'+p.rsplit('/',1)[-1]+'_C'))
            check(path(prop(cdo,'combo_definition'))==path(combo),'Incorrect source combo: '+p)
            check(str(prop(cdo,'entry_node_id')) in ids,'Missing source entry: '+p)
        bp_path='/Game/Bluprints/Monsters/BP_Monster_'+family
        body=unreal.get_default_object(unreal.load_class(None,bp_path+'.BP_Monster_'+family+'_C'))
        rows=list(prop(body,'combat_patterns'))
        row['choices']=sum(prop(r,'weight')>0 for r in rows);row['cooldown_only_rows']=len(rows)-row['choices'];row['ordered']=prop(body,'bOrderedCombatPatterns')
        check(row['choices']==choices,family+' source choice count')
        check(row['ordered']==(family=='Yetuga'),family+' priority/weighted selection')
        check(prop(prop(body,'mesh'),'relative_scale3d')==unreal.Vector(1,1,1),family+' mesh scale preserved')
        character=unreal.load_asset(base+'/Data/DA_Character_'+family)
        stamina=prop(character,'monster_stamina')
        row['death_montage']=path(prop(stamina,'death_presentation_montage'))
        check(bool(row['death_montage']),family+' existing Monster VFX death presentation retained')
        row['brutal_damage']=prop(stamina,'brutal_hp_damage');check(row['brutal_damage']==50,family+' user Brutal 50 retained')
        if family=='Yetuga':
            row['raw_hp_gates']=[{'skill':str(prop(r,'skill')),'hp':prop(prop(r,'condition'),'max_hp'),'ratio':prop(prop(r,'condition'),'bHPIsRatio')} for r in rows if prop(prop(r,'condition'),'max_hp')>=0]
            for skill,hp in [('Armageddon',65),('IceBreath',60),('DempseyRoll',50)]:
                check(any(r['skill']==skill and r['hp']==hp and not r['ratio'] for r in row['raw_hp_gates']),'Original raw HP gate: '+skill)
        REPORT['families'].append(row)
    char=unreal.load_asset('/Game/Data/Character/DA_CharacterDefinition_Player')
    grants=[path(prop(g,'ability_class')) for g in prop(char,'initial_ability_grants')]
    for name,folder,plunge in [('Fall','Fall',False),('FallAttack','FallAttack',True)]:
        p='/Game/_Art/Player/Animation/InGame/DAS/'+folder+'/GA_DAS_'+name
        cls=unreal.load_class(None,p+'.GA_DAS_'+name+'_C')
        check(path(cls) in grants,'Player grant: '+name)
        check(prop(unreal.get_default_object(cls),'bPlungeAttack')==plunge,'Player ability mode: '+name)
    imc=unreal.load_asset('/Game/Input/IMC_Default')
    mappings=[{'action':path(prop(m,'action')),'key':str(prop(m,'key'))} for m in prop(imc,'mappings')]
    check(not any('/IA_Jump.' in (m['action'] or '') for m in mappings),'Jump mappings removed')
    REPORT['input_mappings']=mappings
    actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    monsters=[a for a in actors if a.get_class().get_name().startswith('BP_Monster_')]
    check(len(monsters)==12,'Existing DevMap 12-monster roster preserved')
    REPORT['map_monsters']=[{'label':a.get_actor_label(),'patterns':len(prop(a,'combat_patterns'))} for a in monsters]
    check(sum(len(prop(a,'combat_patterns'))>0 for a in monsters)==2,'Both saved giant instances updated')
    platforms=[a for a in actors if a.get_actor_label()=='DevTest_FallPlatform']
    check(len(platforms)==1,'Exactly one requested fall platform')
    if platforms:
        origin,extent=platforms[0].get_actor_bounds(False)
        REPORT['platform_top_cm']=origin.z+extent.z
        check(abs(REPORT['platform_top_cm']-1200)<.1,'Platform saved top height')
    starts=[a for a in actors if isinstance(a,unreal.PlayerStart)]
    REPORT['player_starts']=[{'x':a.get_actor_location().x,'y':a.get_actor_location().y,'z':a.get_actor_location().z} for a in starts]
    check(len(starts)==1 and starts[0].get_actor_location().z>1200,'Player starts above platform')
except Exception:
    REPORT['errors'].append(traceback.format_exc())
finally:
    REPORT['passed']=not REPORT['errors']
    (OUT/'SavedAssetAudit.json').write_text(json.dumps(REPORT,ensure_ascii=False,indent=2),encoding='utf-8')
    unreal.log('GIANT_FALL_SAVED_AUDIT '+json.dumps({'passed':REPORT['passed'],'errors':REPORT['errors']},ensure_ascii=False))
    unreal.SystemLibrary.quit_editor()
