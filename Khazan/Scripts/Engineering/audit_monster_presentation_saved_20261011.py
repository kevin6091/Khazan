"""Fresh, read-only exact source offset/rotation/socket and corpse/UI graph audit."""
from pathlib import Path
import json, os, re, math, traceback, unreal
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');ROOT=Path(unreal.Paths.project_dir()).resolve();OUT=Path(os.environ['KZ_MONSTER_REPAIR_OUT'])
assert ROOT in [MAIN,Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')]
d={'status':'running','package_saves':0,'families':[],'attack_assets':[],'blood_decal_states':[],'masters':[]}
try:
    plan=json.loads((MAIN/'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json').read_text(encoding='utf-8-sig'))
    original=json.loads((MAIN/'Saved/ImportReports/MonsterVFX_20261008/Authoring/PrivateAuthoring.json').read_text(encoding='utf-8-sig'))
    by_guid={x['guid']:x for x in original['events']};rows={e['event_id']:e for e in plan['events']}
    blood={e['event_id'] for e in plan['events'] if e['notify_type']=='xxAnimNotifyState_Decal' and 'blood' in json.dumps(e['source']['properties']).lower()}
    meshes={}
    for f in ['Swordsman','SwordShield','HeavySwordsman','HalberdElite','ApesStoneHandElite','Yetuga']:
        cls=unreal.load_class(None,'/Game/Bluprints/Monsters/BP_Monster_'+f+'.BP_Monster_'+f+'_C');cdo=unreal.get_default_object(cls);m=cdo.get_editor_property('Mesh');meshes[f]=m
        socket=str(cdo.get_editor_property('CombatReticleSocket'));assert socket=='UI_Chest' and m.does_socket_exist(socket),f
        sk=m.get_editor_property('skeletal_mesh').get_editor_property('skeleton')
        assert cdo.get_editor_property('HitBloodEffect') and cdo.get_editor_property('DeathAshEffect')
        d['families'].append({'family':f,'chest_socket':socket,'skeleton':sk.get_path_name(),'dissolve_seconds':cdo.get_editor_property('DeathDissolveSeconds')})
    for asset in sorted({e['asset'] for e in plan['events'] if e['category']=='Attack'} | {e['asset'] for e in plan['events'] if e['event_id'] in blood}):
        seq=unreal.load_asset(asset);verified=[]
        for evt in unreal.AnimationLibrary.get_animation_notify_events(seq):
            state=evt.get_editor_property('notify_state_class')
            if not isinstance(state,unreal.KZAnimNotifyState_MonsterVisual):continue
            match=re.search(r'Guid=([A-Fa-f0-9]+)',evt.export_text());assert match
            guid=match.group(1).upper();old=by_guid.get(guid)
            if not old:continue
            eid=old['event_id'];e=rows.get(eid)
            if not e:continue
            fx=state.get_editor_property('Effect')
            if eid in blood:
                assert fx is None,(asset,eid,'Blood decal producer retained');d['blood_decal_states'].append({'asset':asset,'event':eid});continue
            if e['category']!='Attack':continue
            fields=e['effect_fields']
            if fields:
                assert fx and str(fx.get_editor_property('EventId'))==eid
                for key in ['SourceSocket','RelativeLocation','RelativeRotation','Scale3D','bAttached','bAbsoluteRotation','WindowStartTime','WindowEndTime','ParticleTemplate']:
                    if key not in fields:continue
                    expected=fields[key];value=fx.get_editor_property(key)
                    if isinstance(expected,dict):
                        for k,v in expected.items():assert math.isclose(getattr(value,k.lower()),v,rel_tol=1e-6,abs_tol=1e-5),(asset,eid,key,k)
                    elif isinstance(expected,bool):assert bool(value)==expected,(asset,eid,key)
                    elif isinstance(expected,(int,float)):assert math.isclose(float(value),expected,rel_tol=1e-6,abs_tol=1e-5),(asset,eid,key)
                    elif key=='ParticleTemplate':assert value.get_path_name().split('.')[0]==expected,(asset,eid,key)
                    else:assert str(value)==expected,(asset,eid,key)
                socket=str(fx.get_editor_property('SourceSocket'));assert socket=='None' or meshes[e['family']].does_socket_exist(socket)
            verified.append(eid)
        if any(e['asset']==asset and e['category']=='Attack' for e in plan['events']):d['attack_assets'].append({'asset':asset,'verified':verified})
    assert len(d['attack_assets'])==198
    assert sum(len(x['verified']) for x in d['attack_assets'])==1577
    assert len(d['blood_decal_states'])==42
    authored=json.loads((MAIN/'Metadata/MonsterPresentationRepair_20261011/MaterialAuthor05/MaterialAuthor.json').read_text(encoding='utf-8-sig'))
    lib=unreal.MaterialEditingLibrary
    for row in authored['corpse_masters']:
        m=unreal.load_asset(row['material']);assert lib.get_material_default_scalar_parameter_value(m,'KZDeathProgress')==0
        assert lib.get_material_default_scalar_parameter_value(m,'KZDeathNoiseTiling')==6
        noise=next(n for n in lib.get_material_expressions(m) if isinstance(n,unreal.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='KZDeathNoise')
        assert noise.get_editor_property('sampler_type')==unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE
        d['masters'].append({'material':m.get_path_name(),'baseline_progress':0,'temporary_noise_tiling':6,'noise_sampler':'LinearGrayscale','base_original_output':row['base_output'],'opacity_original_output':row['opacity_output']})
    ui=unreal.load_asset('/Game/UI/Combat/Materials/M_UI_GaugeBackground');assert ui
    for name,val in [('Mid',.8),('A1',.35),('A2',.2),('A3',.1)]:assert math.isclose(lib.get_material_default_scalar_parameter_value(ui,name),val,abs_tol=1e-6)
    d['status']='passed'
except Exception:d['status']='failed';d['error']=traceback.format_exc();unreal.log_error(d['error'])
(OUT/'SavedAudit.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
