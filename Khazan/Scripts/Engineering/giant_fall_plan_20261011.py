"""Targeted saved-original reader. No Unreal character input or animation edits."""
import csv, hashlib, json, re, zipfile
from pathlib import Path

MAIN = Path(r'C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK = Path(r'C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
OUT = WORK / 'Metadata/GiantCombatFall_20261011'
OUT.mkdir(parents=True, exist_ok=True)
RESEARCH = MAIN / 'Metadata/EnemyBehaviorResearch_20261008'
library = list(csv.DictReader((RESEARCH / 'CurrentApesYetugaLibrary.csv').open(encoding='utf-8-sig')))
mapping = {r['OriginalPackage']: r for r in library}

def enum(value):
    return str(value or 'None').split('::')[-1]

def refpath(ref):
    return (ref or {}).get('ObjectPath', '').rsplit('.', 1)[0]

class Original:
    def __init__(self, family, path, prefix):
        self.family, self.prefix = family, prefix
        self.zip = zipfile.ZipFile(MAIN / path)
        self.names = set(self.zip.namelist())
        self.cache = {}
    def package(self, name):
        if name not in self.cache:
            if name+'.json' in self.names:
                self.cache[name] = json.loads(self.zip.read(name + '.json'))
            else:
                # Two explicitly targeted source curves missing from the archived monster closures.
                local=OUT/'OriginalCommonCurves'/(name+'.json')
                self.cache[name]=json.loads(local.read_text(encoding='utf-8-sig')) if local.exists() else json.loads(self.zip.read(name+'.json'))
        return self.cache[name]
    def resolve(self, ref):
        path = (ref or {}).get('ObjectPath', '')
        if not path or '.' not in path or path.startswith('/Script/'):
            return {}
        package, index = path.rsplit('.', 1)
        return self.package(package)[int(index)]
    def props(self, ref):
        return self.resolve(ref).get('Properties', {})
    def cdo(self, package):
        exports = self.package(package)
        return next((x.get('Properties', {}) for x in exports if x['Name'].startswith('Default__')), exports[0].get('Properties', {}))

origins = [
    Original('ApesStoneHandElite', 'Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/SourceMetadata.zip', 'BBQ/Content/_Kazan_/Design/Monster/Apes/ApesStoneHand_E'),
    Original('Yetuga', 'Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911/SourceMetadata.zip', 'BBQ/Content/_Kazan_/Design/Monster/Boss/01_Yetuga'),
]

unhandled = []
def skill_id(name):
    for prefix in ('SB_ApesStoneHand_E_', 'SI_ApesStoneHand_E_', 'SB_Yetuga_', 'SI_Yetuga_'):
        name = name.removeprefix(prefix)
    return name

def gate(raw):
    angle = raw.get('AngleCondition', {})
    range_ = raw.get('Range', {})
    result = dict(min=range_.get('Min', raw.get('RangeMin', 0)), max=range_.get('Max', raw.get('RangeMax', 0)),
                  range=raw.get('bRangeCheck', raw.get('bCheckRange', True)),
                  yaw=angle.get('BaseDegree', 0), left=angle.get('LeftDegree', 180), right=angle.get('RightDegree', 180),
                  height_min=raw.get('HeightRange', {}).get('Min', -float('inf')),
                  height_max=raw.get('HeightRange', {}).get('Max', float('inf')),
                  statuses=raw.get('StatusConditions', []))
    result['height_min'] = max(result['height_min'], -1e9)
    result['height_max'] = min(result['height_max'], 1e9)
    trace = raw.get('SkillTraceCondition', {})
    if trace.get('bLineTraceToTarget') is False:
        result.update(wall_angle=trace.get('LineTraceAngle', 0), wall_distance=trace.get('LineTraceDist', 0), wall_clear=True)
    return result

def condition(o, obj):
    p, kind = obj.get('Properties', {}), obj.get('Type', '')
    if kind.endswith('FindTarget'):
        info = p.get('CheckStateInfo', {})
        trace = info.get('InstantTargetTraceInfo', {})
        circle = trace.get('CircleTraceInfo', {})
        return dict(kind='target', min=circle.get('RangeMin', 0), max=circle.get('RangeMax', 1e9),
                    yaw=trace.get('OffsetRotatorYaw', circle.get('OffsetYaw', trace.get('OffsetRotator',{}).get('Yaw',0))), left=circle.get('Yaw', 360)/2, right=circle.get('Yaw', 360)/2,
                    height_min=trace.get('HeightMin', -1e9), height_max=trace.get('HeightMax', 1e9),
                    invert=enum(p.get('CheckType', p.get('CheckResult', 'Success'))) == 'Fail')
    if kind.endswith('TargetCondition'):
        angle = 180
        yaw = 0
        if p.get('bCheckBaseDirection'):
            direction = enum((p.get('CheckHitDirections') or ['Front'])[0])
            yaw = {'Front':0,'Right':90,'Back':180,'Left':-90}.get(direction,0)
            angle = p.get('FrontBaseAngle',90)/2
        return dict(kind='target', min=p.get('MinDistance',0) if p.get('bCheckDistance') else 0,
                    max=p.get('MaxDistance',1e9) if p.get('bCheckDistance') else 1e9,
                    yaw=yaw,left=angle,right=angle,height_min=-1e9,height_max=1e9,invert=False)
    if kind.endswith('DynamicStatus') or kind.endswith('SelfStatus'):
        d = p.get('CheckDynamicStatus', p.get('DynamicStatusInfo', {}))
        return dict(kind='status', raw=d)
    if kind.endswith('Random'):
        return dict(kind='random', chance=p.get('RandomRate', .5), provenance='Raw RandomRate; independent probability adapter; native normalization unknown')
    if 'WallCheck' in kind:
        return dict(kind='wall', raw=p)
    if kind.endswith('AttackSuccess'):
        return dict(kind='confirmed_hit')
    if kind.endswith('NotifyEnable'):
        return dict(kind='parried', raw=p)
    if kind.endswith('HoldingSuccess'):
        return dict(kind='holding', raw=p)
    unhandled.append(dict(type=kind, properties=p))
    return dict(kind='unsupported', source_type=kind)

def object_definition(o, reference):
    root=o.props(reference); setup=o.props(root.get('SkillSetupInfo')); info=setup.get('ProjectileInfo',{})
    result=dict(id=o.resolve(reference).get('Name',''),source=refpath(reference),life=setup.get('LifeTime',0),
                radius=setup.get('CapsuleRadius',setup.get('CapsuleHalfHeight',0)),scale=setup.get('Scale',1),animations={},
                curve={},curve_scale={},move_seconds=0,damage_hp=10,damage_stamina=5)
    # Raw exported mesh/animation source; Apes omits the projectile model/default.
    result['mesh_source']=refpath(setup.get('CustomMesh'))
    result['field']='Field_OBJ' in result['id']
    result['end_with_ability']=False # Source LifeTime owns launched rocks/fields; cancellation still cleans this run's objects.
    if 'IceBreath_OBJ' in result['id']:
        result['linear_speed']=3000 # raw AC_Yetuga_IceBreath_OBJ_Straght_Move.UseForceData.ForceVec.X; native operator units are an adapter
        for entry in setup.get('SubStateInfos',[]):
            for event in entry['Value'].get('SkillEventMap',[]):
                tag=o.resolve(event['Value'].get('SkillTag'))
                if tag.get('Type')!='xxSimpeEvnetTagOnTimerLoop':continue
                for fn in event['Value'].get('Funcs',[]):
                    function=o.resolve(fn)
                    if function.get('Type')=='xxFuncSkillObjectSpawn':
                        result['trail_object']=o.resolve(function['Properties']['SkillObejctInfo'])['Name']
                        result['trail_interval']=tag.get('Properties',{}).get('Time',0)
                        result['trail_count']=tag.get('Properties',{}).get('MaxCount',0)
    if result['field']:
        idle=o.props(info.get('IdleStep'));ac=o.props(idle.get('Animation'))
        for nt in ac.get('Notifies',[]):
            nn=o.resolve(nt.get('NotifyStateClass'))
            if nn.get('Type')=='xxAnimNotifyState_Attack':result['field_extent']=nn.get('Properties',{}).get('Size',{});break
    for state,field in [('Idle','IdleStep'),('Move','MoveStep'),('Impact','ExplosionStep'),('Expire','DestructionStep'),('World','WorldExplosionStep'),('Parried','ParryingReactionStep')]:
        step=o.props(info.get(field)); ap=refpath(step.get('Animation'))
        if ap in mapping:result['animations'][state]=mapping[ap]['CurrentAsset']
        if state=='Move' and ap:
            ac=o.props(step['Animation'])
            for nt in ac.get('Notifies',[]):
                nn=o.resolve(nt.get('NotifyStateClass'))
                p=nn.get('Properties',{})
                curve=p.get('PositionInfo',{}).get('UseCurveData',{})
                if curve.get('CurveVector'):
                    result['curve']=o.props(curve['CurveVector']);result['curve_source']=refpath(curve['CurveVector']);result['curve_scale']=curve.get('CustomCurveScale',{})
                    result['move_seconds']=nt.get('Duration',0)
                    result['keep_end_velocity']=p.get('PositionInfo',{}).get('ToralTargetTraceMoveData',{}).get('bUseKeepSpeed',False)
        if state=='Expire' and ap:
            for nt in o.props(step['Animation']).get('Notifies',[]):
                nn=o.resolve(nt.get('NotifyStateClass'))
                if nn.get('Type')=='xxAnimNotifyState_Attack':result['destruction_radius']=nn.get('Properties',{}).get('Size',{}).get('X',0)
    return result

families = []
for o in origins:
    # Read only source design SB/SI/AC packages referenced by the saved research.
    packages = sorted(n[:-5] for n in o.names if n.startswith(o.prefix + '/') and '/Skill/' in n and n.endswith('.json'))
    sb_packages = [n for n in packages if n.rsplit('/',1)[-1].startswith('SB_')]
    si_packages = [n for n in packages if n.rsplit('/',1)[-1].startswith('SI_')]
    skill_infos = {}
    for p in si_packages:
        d = o.cdo(p)
        sid = skill_id(p.rsplit('/',1)[-1])
        skill_infos[sid] = dict(package=p, end_cooldown=d.get('EndCooltime', 0), start_cooldown=d.get('BattleStartCooltime', 0), raw=d)
    nodes, skills, reactions, objects = [], [], [], {}
    for package in sb_packages:
        sid = skill_id(package.rsplit('/',1)[-1])
        cdo = o.cdo(package)
        steps = cdo.get('SubStateInfos', [])
        if not steps: continue
        added = []
        for step in steps:
            key, v = enum(step['Key']), step['Value']
            anim = refpath(v.get('SkillAnimation'))
            if not anim or anim not in mapping:
                if anim: unhandled.append(dict(skill=sid, step=key, animation=anim, reason='No saved current sequence mapping'))
                continue
            row = mapping[anim]
            ac = o.props(v['SkillAnimation'])
            duration = float(row['Seconds'])
            notify_exports = o.package(anim)
            # Stored event-time mapping already incorporates original dilation.
            if o.family == 'ApesStoneHandElite':
                events = json.loads((MAIN / 'Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/PlaybackEventTimes.json').read_text(encoding='utf-8-sig'))
            else:
                events = json.loads((MAIN / 'Content/_Art/Enemies/HeinMach/Bosses/Yetuga/Metadata/Extraction_20260911/PlaybackEventTimes.json').read_text(encoding='utf-8-sig'))
            if isinstance(events, dict): events = events.get('events', [])
            times = {e['notify_index']:e for e in events if e.get('source_package') == anim}
            ntimes = []
            for i, n in enumerate(ac.get('Notifies', [])):
                typeref = n.get('NotifyStateClass') or n.get('Notify')
                obj = o.resolve(typeref)
                np = obj.get('Properties', {})
                rawtime = n.get('LinkValue', n.get('Time', 0))
                tm = times.get(i, {}).get('playback_start_seconds', rawtime)
                endtm=times.get(i,{}).get('playback_end_seconds',rawtime+n.get('Duration',0))
                ntimes.append(dict(type=obj.get('Type', ''), properties={k:v for k,v in np.items() if k not in ('BakingAttackDirections','PostCleaningAttackInfo')}, time=tm, end_time=endtm, raw_time=rawtime, index=i))
            branches, actions = [], []
            for event in v.get('SkillEventMap', []):
                ev = event['Value']; tag = o.resolve(ev.get('SkillTag')); tp = tag.get('Properties', {})
                trigger = enum(tp.get('EventTag'))
                if trigger == 'None':
                    trigger = {'xxSimpeEvnetTagAttackerDamagerSkillReaction':'Parried',
                               'xxSimpeEvnetTagOnAttack':'ConfirmedHit',
                               'xxSimpleSkillEventTagHoldingSucess':'HoldingSuccess',
                               'xxSimpeEvnetTagOnCollisionWall':'Collision',
                               'xxSimpleSkillEventTagEndMoveToByStopCondition':'Landed',
                               'xxSimpeEvnetTagOnTimerLoop':'Timer'}.get(tag.get('Type'), 'UnknownDefault')
                checks = [condition(o, o.resolve(r)) for r in tp.get('SkillTagCondition', [])]
                functions = []
                for r in ev.get('Funcs', []):
                    fn = o.resolve(r); fp = fn.get('Properties', {}); ft = fn.get('Type', '')
                    if ft == 'xxChangeNextStepFunc':
                        dest=enum(fp.get('NextSubStateStep'))
                        functions.append(dict(target=sid+'_'+dest if dest!='None' else 'PatternFinish', deferred=True))
                    elif ft == 'xxPlayAnimatiomFunc':
                        rp=refpath(fp.get('SkillAnimation'))
                        if rp in mapping:
                            rid=sid+'_Reaction';rowr=mapping[rp]
                            if not any(n['id']==rid for n in reactions):
                                reactions.append(dict(id=rid,skill=sid,step='Reaction',asset=rowr['CurrentAsset'],source=rp,
                                    seconds=float(rowr['Seconds']),rate=1,loops=1,blend=fp.get('AnimBlendAlpha',.3),next='',
                                    next_time=float(rowr['Seconds'])-1/30,branches=[],source_notifies=[],attack_windows=[],actions=[],step_properties={}))
                            functions.append(dict(target=rid,deferred=False))
                    elif ft in ('xxFuncSkillObjectSpawn','xxHoldingStartFunc','xxTargetDirectAttack','xxSimpleSkillEventFuncSkillCoolTime','xxSimpleSkillFunc_ChangeTargetSkill'):
                        action=dict(event=enum(event['Key']),trigger=trigger,checks=checks,type=ft,raw=fp,
                                            spawn=o.props(fp.get('SpawnType')) if fp.get('SpawnType') else {},source=package)
                        if ft=='xxFuncSkillObjectSpawn':
                            definition=object_definition(o,fp.get('SkillObejctInfo'));objects[definition['id']]=definition;action['object']=definition['id']
                        actions.append(action)
                    elif ft == 'xxSimpleSkillEventFunc_NextSkillEnable':
                        info=fp.get('ChangeNextSkillCustomInfo',{})
                        soft=info.get('NextSkillInfo',{}).get('AssetPathName','').split('.')[-1]
                        if soft:
                            functions.append(dict(target=skill_id(soft)+'_'+enum(info.get('CustomSubStateStep','Step1')),
                                                  deferred=enum(info.get('ChangeNextSkillCustomType'))!='NowNextSkill',
                                                  cooldown=info.get('bUseCoolTime',False),weight=fp.get('RandomRate',1)))
                        else: unhandled.append(dict(type=ft,skill=sid,step=key,raw=fp))
                    elif ft == 'xxSimpleSkillEventFunc_NextSkillRandom':
                        for option in fp.get('ChangeNextSkillInfoList',[]):
                            targetid=skill_id(o.resolve(option['NextSkillInfo'])['Name'])
                            functions.append(dict(target=targetid+'_'+enum(option.get('CustomSubStateStep','Step1')),
                                                  deferred=enum(fp.get('ChangeNextSkillCustomType'))!='NowNextSkill',
                                                  cooldown=option.get('bUseCoolTime',False),weight=option.get('RandomRate',1)))
                    elif ft == 'xxChangeSkillFunc':
                        info = fp.get('ChangeSkillInfo', fp.get('SkillInfo', {}))
                        # Actual nested object shape preserved in diagnostics when unresolved.
                        reference = info.get('SkillSetting', {}).get('SkillInfo', info.get('SkillInfo'))
                        if reference:
                            targetid = skill_id(o.resolve(reference).get('Name',''))
                            functions.append(dict(target=targetid + '_' + enum(fp.get('SubStateStep', fp.get('ChangeSubStateStep', 'Step1'))), deferred=False))
                        else: unhandled.append(dict(type=ft, skill=sid, step=key, raw=fp))
                    else:
                        unhandled.append(dict(type=ft, skill=sid, step=key, raw=fp))
                event_index = enum(event['Key'])
                matched = [n for n in ntimes if 'SkillEventTag' in n['type'] and enum(n['properties'].get('Index')) == event_index]
                event_windows=[dict(start=n['time'],end=n['end_time']) for n in matched]
                for fn in functions:
                    branches.append(dict(event=event_index, trigger=trigger, checks=checks,
                                         times=[n['time'] for n in matched],windows=event_windows, source=package, **fn))
                for a in actions:
                    if a['event']==event_index:a.update(times=[n['time'] for n in matched],windows=event_windows,timer=tp.get('Time',0),max_count=tp.get('MaxCount',1))
            if v.get('bUseSkillObjectSpawn'):
                fp=v['SpawnSkillObjectInfo'];definition=object_definition(o,fp.get('SkillObejctInfo'));objects[definition['id']]=definition
                # This step field supplies the notify's object configuration; it is
                # not an instruction to create a second object at every step entry.
                # Yetuga's pickup marker omits BeginSkillAction, while the throw
                # marker explicitly exports Use. Treat omitted pickup as Spawn;
                # the native class default is not exported, so record the inference.
                for nt in ntimes:
                    if nt['type']=='xxAnimNotifyState_SkillAction' and nt['properties'].get('bNotifyBegin'):
                        action=enum(nt['properties'].get('BeginSkillAction','Spawn'))
                        assert action in ('Spawn','Use'),(anim,action)
                        actions.append(dict(event='NativeUse'+str(nt['index']),trigger='AnimationNotifyStart',checks=[],type='xxFuncSkillObjectSpawn',
                            raw={**fp,'SkillActionType':action},spawn=o.props(fp.get('SpawnType')),source=anim+f'.Notifies[{nt["index"]}]'+
                            ('; inferred omitted pickup default Spawn (native CDO unavailable)' if 'BeginSkillAction' not in nt['properties'] else ''),
                            object=definition['id'],times=[nt['time']],windows=[],timer=0,max_count=1))
            cancel = next((n['time'] for n in ntimes if 'EnableCancelSK' in n['type']), duration-1/30)
            node = dict(id=sid+'_'+key, skill=sid, step=key, asset=row['CurrentAsset'], source=anim,
                        seconds=duration, rate=v.get('AnimPlayRate', 1), loops=v.get('AnimLoopCount',1),
                        blend=v.get('AnimBlendAlpha', .2), next=sid+'_'+enum(v['NextSubStateStep']) if enum(v.get('NextSubStateStep')) != 'None' else '',
                        next_time=duration*max(1,v.get('AnimLoopCount',1))-1/30, cancel_time=cancel, branches=branches, source_notifies=ntimes,
                        attack_windows=[], actions=actions, moves=[], step_properties=v)
            for nt in ntimes:
                if nt['type']!='xxAnimNotifyState_MoveTo':continue
                p=nt['properties'];pos=p.get('PositionInfo',{})
                if enum(p.get('MoveToType'))=='OnlyRotation' or not pos:continue
                cv=pos.get('UseCurveData',{});curve={}
                if cv.get('CurveVector'):
                    try:curve=o.props(cv['CurveVector'])
                    except KeyError:unhandled.append(dict(type='MoveCurveMissing',source=refpath(cv['CurveVector'])))
                dest=pos.get('UsePositionData',{}).get('DestPosition',cv.get('CustomCurveScale',pos.get('UseForceData',{}).get('ForceVec',{})))
                if not any(dest.values()):continue
                trace=pos.get('ToralTargetTraceMoveData',{});stop=pos.get('StopCondition',{})
                node['moves'].append(dict(start=nt['time']/node['rate'],end=nt['end_time']/node['rate'],destination=dest,
                    target=bool(p.get('TotalSelectTargetTraceInfo',{}).get('bUseSelect')),target_min=trace.get('TargetTraceMinLimitVec',{}).get('X',0),
                    target_max=trace.get('TargetTraceMaxLimitVec',{}).get('X',0),target_offset=trace.get('TargetTraceMoveOffestVec',{}).get('X',0),
                    stop_distance=stop.get('NearDistanceByMoveToTraceTarget',0) if pos.get('bStopCondition') and stop.get('bNearByMoveToTraceTarget') else 0,
                    curve=curve,curve_source=refpath(cv.get('CurveVector')),source=anim+f'.Notifies[{nt["index"]}]',
                    conversion='Serialized cm/time inputs; target clamp/offset and curve axes use documented CMC adapter; native MoveTo operator is unavailable'))
            # FastMove has no exported SkillEventTag marker. Scope its source tick branch
            # to the actual MoveTo interval as an explicit adapter, rather than drop the follow-up.
            if o.family=='ApesStoneHandElite' and sid=='FastMove':
                for branch in node['branches']:
                    if branch['trigger']=='AnimationNotifyTick' and not branch['windows']:
                        branch['windows']=[dict(start=m['start']*node['rate'],end=m['end']*node['rate']) for m in node['moves']]
                        branch['source']+='; adapter: missing event marker scoped to original MoveTo window'
            for i, notify in enumerate(ac.get('Notifies',[])):
                obj=o.resolve(notify.get('NotifyStateClass') or notify.get('Notify'))
                if obj.get('Type')!='xxAnimNotifyState_Attack':continue
                props=obj.get('Properties',{});clean=props.get('PostCleaningAttackInfo',{})
                source_keys=clean.get('AttackBoxList',[])
                event=times.get(i,{})
                keys=[]
                # Map the saved piecewise source/playback event table. Do not rescale enemy coordinates by Player .01.
                def mapped(t):
                    pairs=[]
                    for et in times.values():
                        pairs.extend([(et['original_start_seconds'],et['playback_start_seconds']),(et['original_end_seconds'],et['playback_end_seconds'])])
                    pairs=sorted(set(pairs))
                    if not pairs:return t
                    for (a,pa),(b,pb) in zip(pairs,pairs[1:]):
                        if a<=t<=b:return pa+(pb-pa)*(t-a)/(b-a) if b>a else pa
                    return t+(pairs[0][1]-pairs[0][0]) if t<pairs[0][0] else t+(pairs[-1][1]-pairs[-1][0])
                for k in source_keys:
                    val=k['Value'];keys.append(dict(time=mapped(float(k['Key']))/node['rate'],center=val.get('LocalCenterPos',{}),rotation=val.get('LocalRotator',{})))
                if keys:
                    node['attack_windows'].append(dict(start=event.get('playback_start_seconds',notify.get('LinkValue',0))/node['rate'],
                        end=event.get('playback_end_seconds',notify.get('LinkValue',0)+notify.get('Duration',0))/node['rate'],
                        group=enum(props.get('Group')),shape=enum(props.get('Shape')),extent=props.get('Size',{}),keys=keys,
                        source=anim+f'.Notifies[{i}]',hp=10,stamina=5,blockable=True,capture=False,
                        damage_source='Existing project temporary monster collision policy HP10/Stamina5, editable per node; not original absolute damage'))
            damages=skill_infos.get(sid,{}).get('raw',{}).get('DamageInfos',[])
            for w in node['attack_windows']:
                # Match the source notify's actual damage-info index, never a similarly named SD from another package.
                index=int(ntimes[int(w['source'].rsplit('[',1)[-1][:-1])]['properties'].get('DamageInfoIndex',0))
                if index<len(damages):
                    sd=o.props(damages[index]);attack=sd.get('AttackInfo',{});w['blockable']=not attack.get('GuardDamageInfo',{}).get('bDontGuard',False)
                    w['capture']='HoldAttack' in enum(attack.get('AttackType'));w['damage_info_source']=refpath(damages[index])
            nodes.append(node); added.append(node['id'])
        if added: skills.append(dict(id=sid, entry=added[0], source=package, **{k:v for k,v in skill_infos.get(sid,{}).items() if k!='raw'}))
    nodes.extend(reactions)
    ids = {n['id'] for n in nodes}|{'PatternFinish'}
    for n in nodes:
        if n['next'] and n['next'] not in ids:
            unhandled.append(dict(node=n['id'], unresolved_next=n['next'])); n['next']=''
        for b in n['branches']:
            if b['target'] not in ids: b['enabled']=False
            else: b['enabled']=not any(c['kind']=='unsupported' for c in b['checks'])
    candidates=[]
    if o.family=='ApesStoneHandElite':
        ev=json.loads((RESEARCH/'ApesOriginalEvidence.json').read_text(encoding='utf-8-sig'))
        for r in ev['ai_skill_groups']:
            if r['package'].endswith('/AI_ApesStoneHand_E_Early'):
                val=r['value']; raw=val['Skill']; si=raw['SkillSetting']['SkillInfo']; sid=skill_id(o.resolve(si)['Name'])
                candidates.append(dict(skill=sid, weight=val['Rate'], provenance=r['package'], **gate(raw)))
    else:
        summary=json.loads((RESEARCH/'YetugaOriginal/AIContractSummary.json').read_text(encoding='utf-8-sig'))
        by_index={r['export_index']:r['fields'] for r in summary['can_use_skill_conditions']}
        for band, chain in [('near',summary['near_front_can_use_chain']),('middle',summary['middle_front_can_use_chain'])]:
            for idx in chain:
                p=by_index[idx]; si=p['UseSkill']; sid=skill_id(o.resolve(si)['Name'])
                g=gate(p)
                if band=='near': g['max']=min(g['max'] or 800,800)
                else: g['min']=max(g['min'],799);g['max']=min(g['max'] or 2500,2500)
                candidates.append(dict(skill=sid, weight=1, provenance=f'BT_Yetuga.{idx}', rear=False, **g))
        # Rear selector, exact serialized ranges/angles. Part destruction remains the existing intact-part state.
        rear=[]
        for sid,mx,yaw,angle in [('JumpBackPress',600,180,45),('TurnAtk',400,180,120),('TurnBackRun',1500,180,70),('TurnBackRun_Short',1500,180,70)]:
            rear.append(dict(skill=sid,weight=1,provenance='BT_Yetuga rear selector',rear=True,**gate(dict(Range={'Max':mx},AngleCondition=dict(BaseDegree=yaw,LeftDegree=angle,RightDegree=angle)))))
        candidates=rear+candidates
    locomotion=[]
    for key,suffix in [('idle','_Stand_F'),('run','_Run_F'),('F','_LockOnMove_F'),('B','_LockOnMove_B'),('L','_LockOnMove_L'),('R','_LockOnMove_R')]:
        match=next((r for r in library if r['Family']==o.family and r['OriginalPackage'].endswith(suffix) and (key!='idle' or '/Yetuga/Ani/' in r['OriginalPackage'])),None)
        if not match: raise RuntimeError(f'Missing exact mapped locomotion {o.family} {key}')
        locomotion.append(dict(key=key,asset=match['CurrentAsset'],source=match['OriginalPackage']))
    ai_package=o.prefix+'/Base_Setting/'+('AI_Yetuga' if o.family=='Yetuga' else 'AI_ApesStoneHand_E_Early')
    aip=o.cdo(ai_package)
    families.append(dict(family=o.family, ordered=o.family=='Yetuga', nodes=nodes, skills=skills, candidates=candidates,locomotion=locomotion,
                         objects=list(objects.values()),
                         recognition=aip.get('RecognitionValue'),recognition_source=ai_package,
                         source_zip=str(o.zip.filename), source_zip_sha256=hashlib.sha256(Path(o.zip.filename).read_bytes()).hexdigest()))

fall_dir=MAIN/'Saved/Extracted/InGame_Playback_20261002/Metadata/BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/FallAtk'
fall_end=next(fall_dir.glob('AC_*End.json'))
fall_exports=json.loads(fall_end.read_text(encoding='utf-8-sig'))
fall_ac=fall_exports[0]['Properties'];plunge_windows=[]
for i,nt in enumerate(fall_ac.get('Notifies',[])):
    ref=(nt.get('NotifyStateClass') or {}).get('ObjectPath','')
    if not ref:continue
    e=fall_exports[int(ref.rsplit('.',1)[-1])]
    if e['Type']!='xxAnimNotifyState_Attack':continue
    p=e.get('Properties',{});keys=[]
    for k in p.get('PostCleaningAttackInfo',{}).get('AttackBoxList',[]):
        keys.append(dict(time=float(k['Key']),center=k['Value'].get('LocalCenterPos',{}),rotation=k['Value'].get('LocalRotator',{})))
    if not keys:
        # This source uses a constant AbsoluteOffset, not a baked moving collider.
        for t in (nt.get('LinkValue',0),nt.get('LinkValue',0)+nt.get('Duration',0)):
            keys.append(dict(time=t,center=p.get('AbsoluteOffset',{}),rotation={}))
    plunge_windows.append(dict(start=nt.get('LinkValue',0),end=nt.get('LinkValue',0)+nt.get('Duration',0),group=enum(p.get('Group')),
        shape=enum(p.get('Shape')),extent=p.get('Size',{}),keys=keys,source=str(fall_end)+f'.Notifies[{i}]',hp=0,stamina=0,blockable=True))
plan=dict(schema=1, families=families, plunge_windows=plunge_windows, unsupported=unhandled,
          policy='Original serialized ranges and rates. Missing native event/capture/part-destruction semantics are explicit unsupported records, never treated as successful branches.')
(OUT/'AuthoringPlan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'families':[{k:(len(v) if isinstance(v,list) else v) for k,v in f.items() if k in ('family','nodes','skills','candidates')} for f in families], 'unsupported':len(unhandled)},ensure_ascii=False))
