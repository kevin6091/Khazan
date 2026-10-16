"""Read current six character consumers; save no Unreal packages."""
from pathlib import Path
import unreal,os,json,traceback,runpy
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');ROOT=Path(unreal.Paths.project_dir()).resolve()
OUT=Path(os.environ['KZ_MONSTER_CONTACT_OUT']);registry=unreal.AssetRegistryHelpers.get_asset_registry()
d={'status':'running','asset_saves':0,'families':[],'definitions':[],'montages':[],'sequences':[]}
clips={};montages={};definitions={}
def prop(o,n):return o.get_editor_property(n)
def path(o):return o.get_path_name() if o else None
def vec(v):return [float(v.x),float(v.y),float(v.z)]
def rot(v):return [float(v.pitch),float(v.yaw),float(v.roll)]
def transform(t):return {'translation':vec(t.translation),'rotation_xyzw':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'scale':vec(t.scale3d)}
def animation(a,owner,role):
    if not a:return
    if isinstance(a,unreal.AnimSequence):
        clips.setdefault(path(a),{'asset':a,'uses':set()})['uses'].add((owner,role));return
    if isinstance(a,unreal.AnimMontage):
        if path(a) in montages:
            montages[path(a)]['uses'].add((owner,role));return
        row={'asset':path(a),'uses':{(owner,role)},'segments':[],'sections':[str(a.get_section_name(i)) for i in range(a.get_num_sections())]}
        montages[path(a)]=row
        for track in prop(a,'slot_anim_tracks'):
            for s in prop(prop(track,'anim_track'),'anim_segments'):
                clip=prop(s,'anim_reference')
                row['segments'].append({'clip':path(clip),'start':prop(s,'start_pos'),'clip_start':prop(s,'anim_start_time'),'clip_end':prop(s,'anim_end_time'),'rate':prop(s,'anim_play_rate'),'loops':prop(s,'looping_count')})
                animation(clip,owner,role)
def ability(cls,family):
    if not cls:return
    cdo=unreal.get_default_object(cls)
    if not isinstance(cdo,unreal.KZComboActionAbility):return
    definition=prop(cdo,'ComboDefinition')
    if not definition:return
    if path(definition) in definitions:return
    row={'asset':path(definition),'family':family,'ability':path(cls),'nodes':[]};definitions[path(definition)]=row
    for n in prop(definition,'Nodes'):
        m=prop(n,'Montage');animation(m,family,'ability:'+str(prop(n,'NodeId')))
        node={'id':str(prop(n,'NodeId')),'montage':path(m),'section':str(prop(n,'SectionName')),'collision_to_actor':transform(prop(n,'CollisionToActor')),'windows':[]}
        for w in prop(n,'AttackWindows'):
            node['windows'].append({'start':prop(w,'StartTime'),'end':prop(w,'EndTime'),'shape':str(prop(w,'Shape')),'extent':vec(prop(w,'Extent')),'group':str(prop(w,'HitGroup')),'hp':prop(w,'HPDamage'),'stamina':prop(w,'StaminaDamage'),'source':str(prop(w,'Source')),'keys':[{'time':prop(k,'Time'),'center':vec(prop(k,'Center')),'rotation':rot(prop(k,'Rotation'))} for k in prop(w,'Keys')]})
        row['nodes'].append(node)
    for obj in prop(definition,'PatternObjects'):
        for name,a in prop(obj,'Animations').items():animation(a,family,'skill_object:'+str(prop(obj,'Id'))+':'+str(name))
def abp_animations(cls,family):
    # Traverse only actual animation graph dependencies, not the whole asset library.
    pending=[path(cls).split('.')[0]];seen=set()
    options=unreal.AssetRegistryDependencyOptions(include_hard_package_references=True,include_soft_package_references=True,include_searchable_names=False,include_hard_management_references=False,include_soft_management_references=False)
    while pending:
        package=pending.pop()
        if package in seen:continue
        seen.add(package)
        for ref in registry.get_dependencies(package,options) or []:
            ref=str(ref)
            for data in registry.get_assets_by_package_name(ref) or []:
                kind=str(data.asset_class_path.asset_name)
                if kind in ['AnimSequence','AnimMontage']:animation(data.get_asset(),family,'anim_graph')
                elif kind in ['AnimBlueprint','BlendSpace','BlendSpace1D','AnimComposite']:pending.append(ref)
    return sorted(seen)
try:
    for family in ['Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga']:
        cls=unreal.load_class(None,'/Game/Bluprints/Monsters/BP_Monster_'+family+'.BP_Monster_'+family+'_C');assert cls,family
        cdo=unreal.get_default_object(cls);mesh=prop(cdo,'Mesh')
        # Character resolves this existing tagged asset at BeginPlay; it is not assigned on the CDO.
        definition=prop(cdo,'CharacterDefinition') or unreal.load_asset('/Game/Monsters/'+family+'/Data/DA_Character_'+family);assert definition,family
        animcls=prop(mesh,'anim_class')
        row={'family':family,'definition':path(definition),'mesh_transform':transform(mesh.get_relative_transform()),'skeletal_mesh':path(prop(mesh,'skeletal_mesh')),'anim_class':path(animcls),'anim_graph_packages':abp_animations(animcls,family) if animcls else []}
        if animcls:row['root_motion_mode']=str(prop(unreal.get_default_object(animcls),'root_motion_mode'))
        for grant in prop(definition,'InitialAbilityGrants'):ability(prop(grant,'AbilityClass'),family)
        for routine in prop(definition,'UnawareRoutines'):ability(prop(routine,'AbilityClass'),family)
        reactions=prop(definition,'HitReactions')
        for field in ['ShortHits','Knockbacks','Launches','ShieldBlocks']:
            for a in prop(reactions,field):animation(a,family,'reaction:'+field)
        stamina=prop(definition,'MonsterStamina')
        for field in ['ExhaustionMontage','DeathPresentationMontage','BrutalFrontVictimMontage','BrutalBackVictimMontage']:animation(prop(stamina,field),family,'stamina:'+field)
        d['families'].append(row)
    d['definitions']=list(definitions.values())
    d['montages']=[dict(r,uses=sorted(r['uses'])) for r in montages.values()]
    for p,entry in sorted(clips.items()):
        a=entry['asset']
        d['sequences'].append({'asset':p,'uses':sorted(entry['uses']),'root_motion':prop(a,'enable_root_motion'),'force_root_lock':prop(a,'force_root_lock'),'root_lock':str(prop(a,'root_motion_root_lock')),'seconds':a.get_play_length(),'rate_scale':prop(a,'rate_scale'),'skeleton':path(prop(a,'skeleton'))})
    d['summary']={'families':len(d['families']),'definitions':len(d['definitions']),'nodes':sum(len(r['nodes']) for r in d['definitions']),'windows':sum(len(n['windows']) for r in d['definitions'] for n in r['nodes']),'montages':len(d['montages']),'used_sequences':len(clips),'root_motion_disabled':[r['asset'] for r in d['sequences'] if not r['root_motion']],'root_lock_disabled':[r['asset'] for r in d['sequences'] if not r['force_root_lock']]}
    d['dirty_content']=[p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
    d['status']='passed'
except Exception:d.update(status='failed',error=traceback.format_exc());unreal.log_error(d['error'])
(OUT/'Usage.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
if d['status']=='passed':
    runpy.run_path(r'C:/Users/user/.codex/skills/unreal-root-motion-repair/scripts/audit_root_motion.py',init_globals={'ROOT_MOTION_AUDIT_ASSETS':[{'asset':p,'expects_root_motion':False,'motion_bones':[]} for p in sorted(clips)],'ROOT_MOTION_AUDIT_REPORT':str(OUT/'RootAudit.json')},run_name='__main__')
print('MONSTER_CONTACT_USAGE',d['status'],d.get('summary',{}))
