"""Source attenuation field/curve provenance. Native DSP differences are explicit."""
import json
import xml.etree.ElementTree as ET
from collections import Counter
from prepare_gameplay_audio_scope import OUT,read
facts=read(OUT/'BankNodeFacts.json');rows=[]

def props(fact):
    fs=fact.get('fields',[]);result={}
    for i,f in enumerate(fs):
        if f['name']!='cProps':continue
        n=int(f['value']);ids=fs[i+1:i+1+n];vals=fs[i+1+n:i+1+2*n]
        if all(x['name']=='pID' for x in ids) and all(x['name']=='pValue' for x in vals):
            result.update({a['value']:b['value'] for a,b in zip(ids,vals)})
    return result

def inherited(sid):
    seen=set();chain=[]
    while sid and sid not in seen and sid in facts:
        seen.add(sid);f=facts[sid];chain.append(sid);p=props(f)
        if p.get('70') and p['70']!='0':return p['70'],chain
        sid=next((x['value'] for x in f['fields'] if x['name']=='DirectParentID'),None)
    return None,chain

def curve(sid):
    f=facts.get(sid,{})
    if not f.get('xml'):return None
    e=ET.fromstring(f['xml']);idx=next((int(x.get('value')) for x in e.iter('field') if x.get('name')=='curveToUse[0]'),-1)
    tables=[x for x in e.iter('object') if x.get('name')=='CAkConversionTable']
    if idx<0 or idx>=len(tables):return None
    t=tables[idx];scaling=next((x.get('value') for x in t.findall('field') if x.get('name')=='eScaling'),None)
    keys=[]
    for o in t.iter('object'):
        if o.get('name')!='AkRTPCGraphPoint':continue
        v={x.get('name'):x.get('value') for x in o.findall('field')}
        # Wwise bank's dB scaling stores a linear-amplitude-minus-one table.
        # Preserve raw data and distinguish conversion from a dB exponent.
        keys.append({'distance_cm':float(v['From']),'raw_to':float(v['To']),
            'gain':max(0.,float(v['To'])+1.) if scaling=='2' else float(v['To']),
            'source_interp':int(v['Interp'])})
    return {'attenuation_id':sid,'bank':f['bank'],'scaling':scaling,'keys':keys}

for c in read(OUT/'NativeCuePlan01.json')['cues']:
    targets=[]
    for x in facts.get(c['event_id'],{}).get('fields',[]):
        if x['name']!='ulActionID':continue
        a=facts.get(x['value'],{});typ=next((v.get('valuefmt','') for v in a.get('fields',[]) if v['name']=='ulActionType'),'')
        if '[Play]' not in typ:continue
        targets.extend(v['value'] for v in a['fields'] if v['name']=='idExt')
    inherited_rows=[inherited(t) for t in targets];ids=sorted({sid for sid,chain in inherited_rows if sid})
    curves=[v for sid in ids if (v:=curve(sid))]
    maximum=float(c['source']['duration_properties'].get('MaxAttenuationRadius',0.))
    selected=curves[0] if curves and all(v['keys']==curves[0]['keys'] for v in curves) else None
    if selected and selected['keys']:
        # Compare authored distance axis with AkAudioEvent radius. Don't invent
        # a metres->cm scale where the source metadata already uses UE cm.
        if abs(selected['keys'][-1]['distance_cm']-maximum)>.01:selected=None
    rows.append({'cue':c['asset'],'source_package':c['event_package'],'source_radius_field':'AkAudioEvent.MaxAttenuationRadius',
        'max_distance_cm':maximum,'source_attenuation_ids':ids,'inheritance_chains':inherited_rows,
        'curves':curves,'selected_curve':selected,'spatialize':'/Ambience/' not in c['event_package'],
        'policy':'Original bank volume points, UE linear/constant interpolation' if selected else 'Temporary native linear distance profile using exact source maximum radius; source curve absent/ambiguous',
        'temporary_reverb_send':{'min':.05,'max':.15},'source_metadata':c['source']['metadata_file']})
result={'cues':rows,'conversion':'distance_cm/source MaxAttenuationRadius -> normalized X; Wwise eScaling2 To+1 -> linear gain; source interp9 constant, otherwise native linear adapter',
    'temporary':'Native panning, reverb sends .05/.15 and linear profile when bank curve cannot be uniquely resolved; Wwise SDK DSP is not reproduced.'}
(OUT/'SpatialAudioPlan01.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('SPATIAL',len(rows),'SOURCE CURVES',sum(bool(r['selected_curve']) for r in rows),'RADII',Counter(r['max_distance_cm'] for r in rows))
