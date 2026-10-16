"""Current source-backed composite->raw->baked audio mapping, without pose edits."""
from pathlib import Path
from collections import Counter
import ast
import bisect
import hashlib
import json
import re
from prepare_gameplay_audio_scope import ROOT,SourceCache,package,read
from prepare_gameplay_audio_playback import interpolate

OUT=ROOT/'Metadata/HumanoidSFX_20261013';PRIOR=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
inventory=read(OUT/'Inventory02/Inventory.json');assert inventory['success']
cache=SourceCache();original=read(PRIOR/'AudioAuthoringPlan01.json')
cache.roots.insert(0,OUT/'Events04')
cues={r['event_package']:r for r in read(PRIOR/'NativeCuePlan01.json')['cues']}
source_by_cue={r['asset']:r for r in cues.values()}
retime=read(ROOT/'Saved/Extracted/InGame_Playback_20261002/PlaybackPlan.json')
retime_rows={r['path']:r for r in retime['assets']}
for row in inventory['animations']:
    try:contract=json.loads(row['metadata'].get('TimingContract','{}'))
    except json.JSONDecodeError:continue
    if contract.get('path') in retime_rows and row['asset'] not in retime_rows:
        retime_rows[row['asset']]=retime_rows[contract['path']]
source_segments=read(ROOT/'Saved/ImportReports/PlayerAttackVFX_20261008/MetadataAudit/CurrentSegmentTimingPlan.json')
segment_parents={r['sequence'].split('.')[0]:r.get('sources',[]) for r in source_segments}
segment_sources={r['sequence'].split('.')[0]:r.get('OriginalPackage') for r in source_segments}
tree=ast.parse((ROOT/'Scripts/Animation/retime_ingame_from_metadata.py').read_text(encoding='utf-8-sig'))
function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='source_to_playback')
namespace={'bisect':bisect};exec(compile(ast.Module(body=[function],type_ignores=[]),'<existing source_to_playback>','exec'),namespace)
source_to_playback=namespace['source_to_playback']
pointtypes={'xxAnimNotify_AkEvent','xxAnimNotify_Footstep'}
statetypes={'xxAnimNotifyState_PostAudioEvent','xxAnimNotifyState_AkEventUntilAnimEnd','xxAnimNotifyState_CondAkEvent'}
collected={}

def collect(p,ancestors=()):
    if p in collected:return collected[p]
    result=cache.get(p)
    if not result or p in ancestors:return []
    exports,proof=result;top=next((o for o in exports if o.get('Type') in ('AnimSequence','AnimComposite','xxAnimComposite')),exports[0])
    prop=top.get('Properties',{});rows=[]
    for i,n in enumerate(prop.get('Notifies',[])):
        ref=n.get('Notify') or n.get('NotifyStateClass')
        if not ref:continue
        try:idx=int(ref['ObjectPath'].rsplit('.',1)[-1]);o=exports[idx]
        except (KeyError,ValueError,IndexError):continue
        typ=o.get('Type','')
        if typ not in pointtypes|statetypes:continue
        a=float(n.get('LinkValue',n.get('Time',0)));b=float(n.get('EndLink',{}).get('LinkValue',a+float(n.get('Duration',0))))
        if typ=='xxAnimNotifyState_AkEventUntilAnimEnd':b=float(prop.get('SequenceLength',b))
        rows.append({'type':typ,'properties':o.get('Properties',{}),'source_package':p,
            'field':f'Exports[{idx}].Properties / Notifies[{i}]','proof':proof,'raw_notify':n,'start':a,'end':b})
    for i,segment in enumerate(prop.get('AnimationTrack',{}).get('AnimSegments',[])):
        child=package(segment.get('AnimReference'));a=float(segment.get('AnimStartTime',0));b=float(segment.get('AnimEndTime',0))
        rate=abs(float(segment.get('AnimPlayRate',1)));start=float(segment.get('StartPos',0))
        if not child or not rate:continue
        for occurrence in range(int(segment.get('LoopingCount',1))):
            for e in collect(child,ancestors+(p,)):
                if not a<=e['start']<b:continue
                rows.append(dict(e,start=start+(b-a)/rate*occurrence+(e['start']-a)/rate,
                    end=start+(b-a)/rate*occurrence+(min(e['end'],b)-a)/rate,
                    field=e['field']+f' / {p}.AnimationTrack.AnimSegments[{i}] loop={occurrence}'))
    collected[p]=rows;return rows

def convert(row,p,t):
    timing=retime_rows.get(row['asset'])
    if timing and timing['action']=='retime':
        selected=next(s for s in timing['selected_composites'] if s['package']==p)
        seg=selected['segment'];raw=float(seg.get('AnimStartTime',0))+(t-float(seg.get('StartPos',0)))*abs(float(seg.get('AnimPlayRate',1)))
        return source_to_playback(timing,raw)*row['seconds']/timing['target_duration'],{'raw_leaf_time':raw,'saved_inverse_map':str(ROOT/'Saved/Extracted/InGame_Playback_20261002/PlaybackPlan.json'),
            'mapped_target_duration':timing['target_duration'],'current_seconds':row['seconds'],'mapping':'source raw composite -> same AnimSegment raw leaf -> existing inverse_map -> current integer grid duration'}
    # A direct raw import (Heal/Fall) consumes its exact source segment clock;
    # it has never received the composite's dilation/trim as a pose bake.
    result=cache.get(p);top=result[0][0];props=top.get('Properties',{})
    if row['metadata'].get('OriginalPackage')==p and row['metadata'].get('PlaybackDerivation')=='CompositePlayback':
        curve=top.get('DilationCurve',props.get('DilationCurve',{})) or {}
        points=curve.get('SourceDilationCurve',curve.get('DilationAnimPositions',[])) if isinstance(curve,dict) else []
        if props.get('bApplyDilationCurve') is False:points=[]
        # Current weak clips are verified immutable bake prefixes. Their shorter
        # visible length is a crop, never a whole-composite normalization.
        return interpolate(t,points),{'dilation_points':points,'mapping':'Source CompositePlayback dilation clock; preserve verified current prefix crop without length normalization'}
    source=row['metadata'].get('OriginalPackage') or segment_sources.get(row['asset'])
    segments=props.get('AnimationTrack',{}).get('AnimSegments',[])
    segment=next((s for s in segments if package(s.get('AnimReference'))==source),None)
    if segment:
        return float(segment.get('AnimStartTime',0))+(t-float(segment.get('StartPos',0)))*abs(float(segment.get('AnimPlayRate',1))),{'segment':segment,'mapping':'Exact matching raw AnimReference; raw imported timeline, no composite dilation applied'}
    return None,{'mapping':'Unverified matching raw segment'}

events=[];replacements=[];unresolved=[];requests=set();adaptations=[]
old={e['event_id']:e for e in original['events']}
foot='BBQ/Content/_Kazan_/Sound/Player/Player_Common/PlayerLocomotion/Play_PLYR_Footsteps'
profiles={'voice':.85,'footsteps':.90,'weapon':1.0}

def event_data(row,e,a,b,p,proof):
    props=e['properties'];typ=e['type']
    if typ=='xxAnimNotify_Footstep':
        event=foot;endevent='';anchor='Bip001-L-Toe0' if props.get('bUseLeftFootCommonBone') else 'Bip001-R-Toe0';follow=True;ground=True
    else:
        event=package(props.get('Event') or props.get('AudioEvent') or props.get('BeginAudioEvent'))
        endevent=package(props.get('EndAudioEvent'));anchor=props.get('AttachName','')
        follow=props.get('bFollow',props.get('Follow',props.get('bAttachOnMeshComponent',props.get('AttachOnMeshComponent',False))))
        ground=props.get('SetGroundMaterialSwitch',False)
    if not event:return None
    requests.add(event)
    if endevent:requests.add(endevent)
    return {'event_id':'KZAH_'+hashlib.sha256(json.dumps([row['asset'],p,e['field'],event,a]).encode()).hexdigest()[:24],
        'asset':row['asset'],'family':row['family'],'event_package':event,'end_event_package':endevent,
        'start':max(0.,a),'end':min(row['seconds'],max(a,b)),'is_state':typ in statetypes,
        'anchor':anchor,'follow':follow,'ground_switch':ground,'source':e,'mapping':proof,
        'only_local_or_locked':bool(props.get('bCheckTargetCondition'))}

for row in inventory['animations']:
    if row['type']!='AnimSequence':continue
    try:contract=json.loads(row['metadata'].get('TimingContract','{}'))
    except json.JSONDecodeError:contract={}
    timing=retime_rows.get(row['asset'])
    parents=[s['package'] for s in contract.get('selected_composites',[])]
    if row['family']=='Player' and not parents:
        parents=segment_parents.get(row['asset'],parents)
    if row['family']=='Player' and row['asset'].endswith('/CA_P_Kazan_DualAxeSword_Heal_01'):
        parents=['BBQ/Content/_Kazan_/Design/Kazan/Common/AC_Kazan_Recovery']
        # Actual saved source path from the recent Heal VFX audit.
        known=ROOT/'Metadata/HealVFX_20261013/Original'
        candidates=list(known.rglob('AC_Kazan_Recovery.json'))
        if candidates:
            rel=str(candidates[0]).replace('\\','/');parents=[rel[rel.index('BBQ/'):][:-5]]
            cache.explicit[parents[0]]=candidates[0]
    if row['family']=='Player' and parents:
        new=[]
        for p in sorted(set(parents)):
            source=cache.get(p)
            if not source:
                unresolved.append({'asset':row['asset'],'source':p,'reason':'Parent source metadata unavailable'});continue
            for e in collect(p):
                a,proof=convert(row,p,e['start']);b,_=convert(row,p,e['end'])
                if a is None:
                    unresolved.append({'asset':row['asset'],'source':p,'reason':'Matching raw segment unresolved'});continue
                if not 0<=a<row['seconds']:continue
                value=event_data(row,e,a,b,p,proof)
                if value:new.append(value)
        if new:
            # The raw child's events are included recursively, so the canonical
            # parent recipe replaces this clip's old partial raw-only recipe.
            unique={json.dumps([e['event_package'],e['start'],e['end'],e['anchor']]):e for e in new}
            events.extend(unique.values());replacements.append(row['asset']);continue
    for n in row['notifies']:
        if not n.get('id'):continue
        e=old.get(n['id'])
        if not e:continue
        events.append(dict(e,start=n['start'],end=n['start']+n['duration'],duration=n['duration'],
            timing_preserved_from_current=True,mapping={'mapping':'Current saved notify clock after latest integer-FPS correction; no stale timestamp restoration'}))

# Missing ordinary damage cries have no serialized audio notify on their
# original short/weak composites. Use each family's verified original short
# damage event at first reaction pose as an explicit presentation adapter.
voices={'HalberdElite':'SC_vo_empirehalberd_damage_s','HeavySwordsman':'SC_vo_empireswshield_e_dmg_s',
        'SwordShield':'SC_vo_empireswshield_n_dmg_s','Swordsman':'SC_vo_empiresword_dmg_s'}
paths_with_voice={e['asset'] for e in events if '/VO/' in e['event_package'] or '/vo/' in e['event_package'] or e['event_package'].rsplit('/',1)[-1].startswith('vo_')}
for row in inventory['animations']:
    if row['type']!='AnimSequence' or row['family'] not in voices or row['asset'] in paths_with_voice:continue
    if '/Damage/' not in row['asset'] or not any(x in row['asset'].rsplit('/',1)[-1] for x in ('Damage_Normal','Damage_Weak')):continue
    cue='/Game/Audio/Original/Events/'+voices[row['family']];src=source_by_cue[cue]
    e={'event_id':'KZAH_'+hashlib.sha256((row['asset']+cue).encode()).hexdigest()[:24],
        'asset':row['asset'],'family':row['family'],'event_package':src['event_package'],'end_event_package':'',
        'start':0.,'end':0.,'is_state':False,'anchor':'Bip001-Head','follow':True,'ground_switch':False,
        'only_local_or_locked':False,'source':{'source_package':src['event_package'],'field':'Original event; TEMP current reaction-start dispatch (native original callback not serialized)',
            'proof':{'file':src['source']['metadata_file'],'sha256':src['source']['metadata_sha256']}},
        'mapping':{'mapping':'TEMP first reaction pose; original short cry from same family, no original native callback timestamp available'}}
    events.append(e);adaptations.append({'asset':row['asset'],'cue':cue,'reason':e['mapping']['mapping']})

landing_asset='/Game/_Art/Player/Animation/InGame/DAS/Fall/CA_P_Kazan_DualAxeSword_Fall_End'
landing_package='BBQ/Content/_Kazan_/Sound/Player/Player_Common/PlayerLocomotion/foley_kz_landing'
events.append({'event_id':'KZAH_FallLand','asset':landing_asset,'family':'Player','event_package':landing_package,'end_event_package':'',
    'start':0.,'end':0.,'is_state':False,'anchor':'Bip001-Pelvis','follow':False,'ground_switch':True,'only_local_or_locked':False,
    'source':{'source_package':landing_package,'field':'Original landing foley, TEMP current Land section first-pose dispatch; native source landing callback unavailable'},
    'mapping':{'mapping':'TEMP actual Land section start; never emitted by airborne loop'}})
requests.add(landing_package)

# Source native callbacks are not serialized on these raw sequences. Keep
# original event/media identity, but explicitly label the dispatch adapter.
def adapter(row,event,reason,anchor='Bip001-Pelvis',ground=False):
    if any(e['asset']==row['asset'] and e['event_package']==event for e in events):return
    requests.add(event)
    events.append({'event_id':'KZAH_'+hashlib.sha256((row['asset']+event+reason).encode()).hexdigest()[:24],
        'asset':row['asset'],'family':row['family'],'event_package':event,'end_event_package':'',
        'start':0.,'end':0.,'is_state':False,'anchor':anchor,'follow':False,
        'ground_switch':ground,'only_local_or_locked':False,
        'source':{'source_package':event,'field':'Original event; TEMP '+reason},
        'mapping':{'mapping':'TEMP '+reason}})
    adaptations.append({'asset':row['asset'],'event_package':event,'reason':'TEMP '+reason})

movement='BBQ/Content/_Kazan_/Sound/Player/Player_Common/PlayerLocomotion/'
for row in inventory['animations']:
    if row['type']!='AnimSequence' or row['family']!='Player':continue
    path=row['asset'];name=path.rsplit('/',1)[-1]
    if '/Dodge/' in path and name.endswith('_M1'):
        direction=name.split('Off_Dodge_',1)[1].split('_M1',1)[0]
        variant='Front' if direction in ('F','RF','LF') else 'Rear'
        adapter(row,movement+'Play_PLYR_Dodge_'+variant,'current dodge first pose; front/rear native selection not serialized')
        adapter(row,movement+'foley_kz_dodge','current dodge first pose; original body/gear layer',ground=True)
    if '/Equip/' in path:
        event='dualaxesword_unarmed' if name.endswith('_UnArmed') else 'dualaxesword_armed'
        adapter(row,movement+event,'current equip first pose; original native callback not serialized')
    if '/Reaction/Clips/' in path and ('DamageWeak' in name or 'DamageAir' in name):
        adapter(row,'BBQ/Content/_Kazan_/Sound/Player/Player_Common/Player_VO/Play_PLYR_VO_Dmg',
            'current first reaction pose; original player damage cry',anchor='Bip001-Head')
    if name in ('DAS_Player_Run_Stop_LF','DAS_Player_Run_Stop_RF'):
        anchor='Bip001-L-Toe0' if name.endswith('_LF') else 'Bip001-R-Toe0'
        adapter(row,foot,'current run stop initial support contact; original raw stop has no serialized audio notify',anchor=anchor,ground=True)
    if name=='Player_GuardBreak_Start':
        adapter(row,'BBQ/Content/_Kazan_/Sound/Player/Player_Common/Player_Weapon_Com_Swish/Play_PLYR_DualAxeSword_Guard_Brk',
            'current guard break first pose; original AC Guard_Brk uses a different raw pose')

# Successful guard audio already has an approved-hit producer in the current
# attack window. The success pose must not replay it a second time.
callback_owned=[]
kept=[]
for e in events:
    if '/Guard/Player_Guard_Suc_' in e['asset'] and e['event_package'].endswith('/Play_PLYR_DualAxeSword_Guard_Suc'):
        callback_owned.append(dict(e,reason='Current approved melee guard result dispatches Window.GuardSound once'))
    else:kept.append(e)
events=kept

# Parent + nested child can carry the same initial cry within a single current
# pose frame. Coalesce just these identical voice onsets; preserve separate
# weapon layers, feet and later vocalizations.
voice_coalesced=[];kept=[];last_voice={};contact_coalesced=[];last_contact={}
by_asset={r['asset']:r for r in inventory['animations']}
for e in sorted(events,key=lambda e:(e['asset'],e['start'],e['event_id'])):
    voice=e['event_package'].rsplit('/',1)[-1].startswith(('vo_','Play_PLYR_VO'))
    key=(e['asset'],e['event_package'],e['anchor'])
    row=by_asset[e['asset']];fps=row.get('fps',[30,1]);frame=float(fps[1])/fps[0]
    if voice and not e.get('is_state',e.get('state',False)) and key in last_voice and e['start']-last_voice[key]['start']<frame:
        voice_coalesced.append({'kept':last_voice[key]['event_id'],'removed':e,'reason':'Same event/anchor within one current animation frame'})
        continue
    contact=e['event_package'].endswith('/Play_PLYR_Footsteps')
    if contact and key in last_contact and e['start']-last_contact[key]['start']<frame:
        contact_coalesced.append({'kept':last_contact[key]['event_id'],'removed':e,'reason':'Identical same-foot source contacts within one current pose frame'})
        continue
    kept.append(e)
    if voice:last_voice[key]=e
    if contact:last_contact[key]=e
events=kept

for e in events:
    event=e['event_package'];role='voice' if event.rsplit('/',1)[-1].startswith(('vo_','Play_PLYR_VO')) or '/vo/' in event else 'footsteps' if 'footstep' in event.lower() else 'weapon'
    e['volume_multiplier']=profiles[role];e['mix_role']=role;e['preserve_finite_tail']=True
for event in requests:
    if event not in cues and event not in original['nonplay_events']:unresolved.append({'event':event,'reason':'Additional source event resource required'})
plan={'events':events,'replace_audio_tracks':replacements,'reaction_voice_adapters':adaptations,'unresolved':unresolved,
    'callback_owned_events':callback_owned,'coalesced_voice_events':voice_coalesced,'coalesced_contact_events':contact_coalesced,
    'additional_events':sorted(e for e in requests if e not in cues and e not in original['nonplay_events']),
    'profiles':{'values':profiles,'source':'Assistant TEMP mix, original leaf gain stays unchanged. Voice -1.41dB, footstep -0.915dB, weapon unity; validate peak and short/long interplay.'},
    'scope':['Player','Swordsman','SwordShield','HeavySwordsman','HalberdElite'],
    'counts':{'events':len(events),'sequences':len(set(e['asset'] for e in events)),'canonical_parent_tracks':len(replacements),'reaction_adapters':len(adaptations),'families':dict(Counter(e['family'] for e in events))}}
(OUT/'PlaybackPlan01.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(plan['counts']),flush=True)
print('ADDITIONAL',len(plan['additional_events']),plan['additional_events'],flush=True)
print('UNRESOLVED',len(unresolved),[r for r in unresolved if 'asset' in r][:6],flush=True)
