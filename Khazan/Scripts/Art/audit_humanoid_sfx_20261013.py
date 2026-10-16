"""Read current Player/humanoid action closure and original audio clocks. Saves0."""
from pathlib import Path
from collections import Counter
import json
import os
import re
import traceback
import unreal as u

ROOT=Path(os.environ['KZ_AUDIO_MAIN']);RUN=Path(os.environ['KZ_AUDIO_OUTPUT'])
PRIOR=ROOT/'Saved/ImportReports/GameplayAudio_20261011'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
registry=u.AssetRegistryHelpers.get_asset_registry();registry.search_all_assets(True)
lib=u.EditorAssetLibrary;al=u.AnimationLibrary
families=('Player','Swordsman','SwordShield','HeavySwordsman','HalberdElite')
report={'success':False,'package_saves':0,'animations':[],'combos':[],'definitions':[],'ability_defaults':[],'errors':[]}
expected={}
source_cues={r['asset']:r for r in read(PRIOR/'NativeCuePlan01.json')['cues']}
for e in read(PRIOR/'AudioAuthoringPlan01.json')['events']:
    if e['family'] in families:expected.setdefault(e['asset'],[]).append(e)

def scope(path):
    if '/Player/' in path or path.startswith('/Game/Data/ComboCommand/DA_Player_'):return 'Player'
    for family in families[1:]:
        if '/'+family+'/' in path or path.rsplit('/',1)[-1].endswith('_'+family):return family
    return None

def sound(s):
    if not s:return None
    path=s.get_path_name().split('.')[0];source=source_cues.get(path)
    r={'asset':path,'type':s.get_class().get_name(),'source_loop':source['loop'] if source else None}
    for prop in ('duration','max_distance'):
        try:r[prop]=s.get_editor_property(prop)
        except Exception:pass
    return r

def row_notify(e):
    obj=e.get_editor_property('notify') or e.get_editor_property('notify_state_class')
    row={'text':e.export_text(),'name':str(e.get_editor_property('notify_name')),'class':obj.get_class().get_name() if obj else None}
    if isinstance(obj,(u.KZAnimNotify_PlayAudio,u.KZAnimNotifyState_PlayAudio)):
        state=isinstance(obj,u.KZAnimNotifyState_PlayAudio)
        p=obj.get_editor_property('playback') if state else obj
        row.update(id=obj.get_name(),sound=sound(p.get_editor_property('sound')),
            start=float(re.findall(r'LinkValue=([-+0-9.eE]+)',e.export_text())[-1]),
            duration=float(re.search(r'Duration=([-+0-9.eE]+)',e.export_text()).group(1)) if state else 0.,
            source_package=p.get_editor_property('source_package'),source_field=p.get_editor_property('source_field'),
            anchor=str(p.get_editor_property('attach_name')),follow=p.get_editor_property('follow'),
            ground=p.get_editor_property('ground_material_switch'),stop=[sound(s) for s in p.get_editor_property('stop_sounds')],
            stop_fade=p.get_editor_property('stop_fade_seconds'),
            end_sound=sound(obj.get_editor_property('end_sound')) if state else None,
            stop_at_end=obj.get_editor_property('stop_at_end') if state else False,
            end_fade=obj.get_editor_property('fade_out_seconds') if state else 0.)
    return row

try:
    paths=set(expected)
    roots=['/Game/_Art/Player/Animation/InGame']
    roots += ['/Game/Monsters/'+f for f in families[1:]]
    roots += ['/Game/_Art/Enemies/HeinMach/Humanoids/'+f for f in families[1:]]
    for folder in roots:
        for ad in registry.get_assets_by_path(folder,True):
            if str(ad.asset_class_path.asset_name) in ('AnimSequence','AnimMontage'):paths.add(str(ad.package_name))
    for path in sorted(paths):
        obj=lib.load_asset(path);assert obj,path
        row={'asset':path,'family':scope(path),'type':obj.get_class().get_name(),'seconds':obj.get_play_length(),
             'notifies':[row_notify(e) for e in al.get_animation_notify_events(obj)],
             'metadata':{str(k):str(v) for k,v in lib.get_metadata_tag_values(obj).items()}}
        if isinstance(obj,u.AnimSequence):
            model=obj.controller.get_model_interface();rate=model.get_frame_rate()
            row.update(rate_scale=obj.get_editor_property('rate_scale'),frames=model.get_number_of_frames(),fps=[rate.numerator,rate.denominator])
            data=obj.get_editor_property('asset_import_data');row['import_source']=data.get_first_filename() if data else None
        else:row['slots']=[s.export_text() for s in obj.get_editor_property('slot_anim_tracks')]
        report['animations'].append(row)
    for ad in registry.get_assets_by_class(u.TopLevelAssetPath('/Script/Khazan','KZComboDefinitionData'),True):
        path=str(ad.package_name);family=scope(path)
        if not family:continue
        obj=ad.get_asset();row={'asset':path,'family':family,'nodes':[]}
        for n in obj.get_editor_property('nodes'):
            row['nodes'].append({'id':str(n.get_editor_property('node_id')),
                'montage':n.get_editor_property('montage').get_path_name().split('.')[0] if n.get_editor_property('montage') else None,
                'text':n.export_text(),'windows':[{'text':w.export_text(),'impact':sound(w.get_editor_property('impact_sound')),
                    'guard':sound(w.get_editor_property('guard_sound')),'hp':w.get_editor_property('hp_damage')} for w in n.get_editor_property('attack_windows')]})
        report['combos'].append(row)
    for prior in read(PRIOR/'BindingAuthor02_Persistent/Bindings.json')['definitions']:
        path=prior['asset']
        if any(x in path.lower() for x in ('apes','yetuga')):continue
        obj=lib.load_asset(path);hit=obj.get_editor_property('hit_reactions');stamina=obj.get_editor_property('monster_stamina')
        row={'asset':path,'hit':hit.export_text(),'stamina':stamina.export_text(),'impact':sound(hit.get_editor_property('impact_sound')),
             'grants':[g.export_text() for g in obj.get_editor_property('initial_ability_grants')]}
        for g in obj.get_editor_property('initial_ability_grants'):
            cls=g.get_editor_property('ability_class');cdo=u.get_default_object(cls) if cls else None
            if not cdo:continue
            props={}
            for name in ('combo_definition','entry_node_id','guard_montage','parry_sound','success_sound','heal_montage','draw_montage','fall_montage','fall_attack_montage','player_montage'):
                try:
                    value=cdo.get_editor_property(name);props[name]=value.get_path_name() if isinstance(value,u.Object) else str(value)
                except Exception:pass
            report['ability_defaults'].append({'definition':path,'class':cls.get_path_name(),'properties':props})
        report['definitions'].append(row)
    report['expected_audio_events']=sum(len(v) for v in expected.values())
    report['expected_audio_sequences']=len(expected)
    by_asset={r['asset']:r for r in report['animations']}
    missing=[];changed=[]
    for path,rows in expected.items():
        actual={n.get('id'):n for n in by_asset[path]['notifies'] if n.get('id')}
        for e in rows:
            n=actual.get(e['event_id'])
            if not n:missing.append({'asset':path,'id':e['event_id'],'expected':e});continue
            cue=(n['sound'] or {}).get('asset','')
            if cue!=e['cue'] or abs(n['start']-e['start'])>.001 or abs(n['duration']-(e['duration'] if e['state'] else 0))>.001:
                changed.append({'asset':path,'id':e['event_id'],'expected':e,'actual':n})
    report.update(missing_original_events=missing,changed_original_events=changed,
        family_counts=dict(Counter(r['family'] for r in report['animations'])))
    report['success']=True
except Exception:
    report['errors'].append(traceback.format_exc());u.log_error(report['errors'][-1])
(RUN/'Inventory.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
if not report['success']:raise RuntimeError('Humanoid SFX current inventory failed')
