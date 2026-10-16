"""Fresh-process readback; never edits or saves any Unreal package."""
from pathlib import Path
from collections import Counter, defaultdict
import ast
import hashlib
import json
import os
import runpy
import re
import traceback
import unreal

MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK=Path(unreal.Paths.project_dir()).resolve()
VERIFY_MAIN=os.environ.get('KZ_MONSTER_VFX_VERIFY_MAIN')=='1' or globals().get('KZ_MONSTER_VFX_VERIFY_MAIN') in (1,'1',True)
EXPECTED=MAIN if VERIFY_MAIN else Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan')
assert WORK==EXPECTED,'Saved-audit project/mode mismatch'
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None
OUT=MAIN/'Saved/ImportReports/MonsterVFX_20261008/Authoring'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
author=read(OUT/'PrivateAuthoring.json');assert author['status']=='passed'
content_revision_file=OUT/'ContentRebaseRevision.json'
rebased_definitions={}
if content_revision_file.exists():
    content_revision=read(content_revision_file)
    assert content_revision['status']=='passed' and content_revision['mode']=='apply'
    assert content_revision['author_before_sha256']==hashlib.sha256((OUT/'PrivateAuthoring.json').read_bytes()).hexdigest()
    assert content_revision['original_author_journal_preserved'] and content_revision['untouched493_sha_preserved']
    assert content_revision['main_mutations']==0 and content_revision['package_saves']==6
    rebased_definitions={r['relative']:r for r in content_revision['rows']}
    assert len(rebased_definitions)==6 and all(r['all_other_definition_fields_preserved'] for r in rebased_definitions.values())
planfile=OUT.parent/'PreparedPlaybackPlan.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(planfile)==author['plan_sha256'],'Prepared plan changed after authoring'
plan=read(planfile);expected={e['event_id']:e for e in plan['events']+plan.get('lifetime_sentinels',[])}
assert len(expected)==len(author['events'])
# The delivery module only defines functions unless explicitly run as __main__.
# Validate the untouched original journal first, then the separate exact revision.
D=runpy.run_path(str(MAIN/'Scripts/Art/deliver_monster_vfx_main_20261008.py'),run_name='monster_visual_delivery_readonly_helpers')
shared=D['shared_effects_rebase_revision'](delivered=VERIFY_MAIN)
material_revision=shared['visual_revision'] if shared else D['visual_material_repair_revision'](delivered=VERIFY_MAIN)
victim=D['victim_decal_revision_rows'](author,plan)
rebased_definitions=D['rebased_definition_rows'](author,plan,victim['sequences'] if victim else None)
victim_sequences=victim['sequences'] if victim else {}
victim_events=victim['events'] if victim else {}
if VERIFY_MAIN:
    # Import only read-only getter/export definitions. The author's unconditional
    # private project guard is never weakened or executed in Main.
    H={'Path':Path,'unreal':unreal,'json':json,'re':re,'hashlib':hashlib,'Counter':Counter,
        'WORK':WORK,'OUT':OUT/'MainSavedAuditExports'}
    H['OUT'].mkdir(parents=True,exist_ok=True)
    for source,names in [
        (MAIN/'Scripts/Art/player_attack_vfx_author.py',{'guid','f32','export'}),
        (MAIN/'Scripts/Art/monster_vfx_author_20261008.py',{'sha','relative','private','encode','data_fields',
            'track_names','state_events','actual_event','exported_struct_fields','raw_snapshot','preserved_snapshot','verify_preserved','montage_sections','semantic_montage_sections'})]:
        tree=ast.parse(source.read_text(encoding='utf-8-sig'))
        functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        assert {n.name for n in functions}==names
        exec(compile(ast.Module(body=functions,type_ignores=[]),str(source),'exec'),H)
    import struct
    H['struct']=struct
    H['STATE']=unreal.load_class(None,'/Script/Khazan.KZAnimNotifyState_MonsterVisual');assert H['STATE']
else:
    H=runpy.run_path(str(MAIN/'Scripts/Art/monster_vfx_author_20261008.py'),run_name='monster_visual_audit_definitions')
selected={r['path'] for r in author['sequences']}|{d[k] for d in author['death_presentations'] for k in ('definition','montage')}
before_hashes={path:sha(H['private'](path)) for path in selected}
report={'schema':'Khazan.MonsterVFX.SavedReadback.v1','status':'running','pid':os.getpid(),'project':str(WORK),
    'mode':'main_read_only' if VERIFY_MAIN else 'private_read_only',
    'asset_saves':0,'asset_mutations':0,'sequences':[],'events':[],'death_presentations':[],'plan_sha256':sha(planfile)}
if rebased_definitions:
    report['content_rebase_revision_sha256']=sha(content_revision_file)
if victim:
    report['victim_decal_policy_revision_sha256']=victim['sha256']
if shared:
    report['shared_effects_rebase_revision_sha256']=shared['sha256']
    report['shared_dependency_sha_before']=shared['after_sha256']
if material_revision:
    report['visual_material_repair_revision_sha256']=material_revision['sha256']
    report['visual_material_repair_sha_before']={p:sha(WORK/p) for p in material_revision['rows']}
    report['visual_material_repair_readbacks']=[]

def material_graph(master):
    lib=unreal.MaterialEditingLibrary
    roots={label:(obj.get_path_name() if obj else None) for label,prop in
        [('BaseColor',unreal.MaterialProperty.MP_BASE_COLOR),('EmissiveColor',unreal.MaterialProperty.MP_EMISSIVE_COLOR),
         ('Opacity',unreal.MaterialProperty.MP_OPACITY),('Normal',unreal.MaterialProperty.MP_NORMAL)]
        for obj in [lib.get_material_property_input_node(master,prop)]}
    nodes={}
    for obj in lib.get_material_expressions(master):
        pins=list(lib.get_material_expression_input_names(obj))
        values=list(lib.get_inputs_for_material_expression(master,obj));assert len(pins)==len(values)
        nodes[obj.get_name()]={'class':obj.get_class().get_name(),
            'inputs':{str(k):v.get_path_name() if v else None for k,v in zip(pins,values)}}
    return {'settings':{name:str(master.get_editor_property(name)) for name in
        ('material_domain','blend_mode','shading_model','two_sided','use_material_attributes')},'roots':roots,'nodes':nodes}

try:
    if material_revision:
        decal_rows={r['relative']:r for r in material_revision['decal']['selected_assets']}
        for relative,revision in material_revision['rows'].items():
            package='/Game/'+relative.removeprefix('Content/').removesuffix('.uasset')
            master=unreal.load_asset(package);assert isinstance(master,unreal.Material)
            custom=unreal.find_object(master,'MaterialExpressionCustom_0');assert isinstance(custom,unreal.MaterialExpressionCustom)
            code=custom.get_editor_property('code')
            actual=material_graph(master)
            inputs=list(custom.get_editor_property('inputs'))
            if revision['kind']=='OriginalArtOverride':
                expected_graph=decal_rows[relative]['graph_after']
                assert actual==expected_graph and code==material_revision['decal']['hlsl']
                assert [str(i.get_editor_property('input_name')) for i in inputs]==['P'+str(i) for i in range(9)]
            else:
                source=material_revision['wpo']
                assert code==source['hlsl']
                assert {name:str(master.get_editor_property(name)) for name in source['settings_after']}==source['settings_after']
                assert unreal.MaterialEditingLibrary.get_material_property_input_node(master,unreal.MaterialProperty.MP_OPACITY)==custom
                assert [str(i.get_editor_property('input_name')) for i in inputs]==['Mask','OpacityPower','OpacityStrength','ParticleAlpha','Dissolve']
                expected_names={'Mask':'MaterialExpressionTextureSampleParameter2D_0','OpacityPower':'MaterialExpressionScalarParameter_110',
                    'OpacityStrength':'MaterialExpressionScalarParameter_40','ParticleAlpha':'MaterialExpressionParticleColor_0',
                    'Dissolve':'MaterialExpressionDynamicParameter_0'}
                assert {k:Path(v.split(':')[-1]).name for k,v in actual['nodes'][custom.get_name()]['inputs'].items()}==expected_names
                dissolve=inputs[4].export_text();assert 'OutputIndex=3' in dissolve and 'MaskA=1' in dissolve
                dynamic=unreal.find_object(master,'MaterialExpressionDynamicParameter_0')
                assert [str(n) for n in dynamic.get_editor_property('param_names')]==['Uoffset','Wpo_str','Dist_str','Opa_Dissolve']
            report['visual_material_repair_readbacks'].append({'relative':relative,'sha256':sha(WORK/relative),
                'fields_and_links_equal':True,'custom_code_sha256':hashlib.sha256(code.encode('utf-8')).hexdigest(),
                'actual_graph':actual,'custom_input_exports':[i.export_text() for i in inputs]})
    groups=defaultdict(list)
    for e in author['events']:
        groups[e['asset']].append(e)
    for record in author['sequences']:
        revision=victim_sequences.get(record['relative'])
        file=H['private'](record['path']);assert sha(file)==(revision['after_sha256'] if revision else record['after_sha256'])
        asset=unreal.load_asset(record['path']);assert asset
        current=H['verify_preserved'](asset,record['before'])
        assert current==record['after'],'Saved sequence fingerprint differs from authored readback'
        events={H['guid'](e.export_text()):e for e in H['state_events'](asset)}
        for e in groups[record['path']]:
            planned=expected[e['event_id']]
            assert e['effect_fields']==planned['effect_fields'] and e['state_fields']==planned['state_fields']
            assert e['start_time']==H['f32'](planned['start_time']) and e['end_time']==H['f32'](planned['end_time'])
            actual=events[e['guid']];state=actual.get_editor_property('notify_state_class');assert state
            assert state.get_class()==H['STATE']
            # UE5.8 NoMerge (1<<0) cannot match contextless BlendSpace/SingleNode
            # lifecycles. This is an engine flag, not a gameplay tuning number.
            behavior_flags=int(state.get_editor_property('NotifyStateBehaviorFlags'))
            assert behavior_flags & 1 == 0,'Saved state retained incompatible NoMerge flag'
            assert unreal.AnimationLibrary.get_anim_notify_event_trigger_time(actual)==e['start_time']
            timing=H['actual_event'](actual)
            assert timing['duration']==H['f32'](e['end_time']-e['start_time'])
            assert timing['end_link_value']==H['f32'](round(e['end_time'],6))
            effect=state.get_editor_property('Effect')
            assert H['data_fields'](state,e['state_fields'])==e['state_readback']
            revised=victim_events.get(e['event_id'])
            effect_fields=revised['after_effect_fields'] if revised else e['effect_fields']
            expected_readback=revised['after_effect_readback'] if revised else e['effect_readback']
            assert (H['data_fields'](effect,effect_fields) if effect_fields else {})==expected_readback
            row={'asset':record['path'],'guid':e['guid'],'event_id':e['event_id'],
                'fields_and_timing_equal':True,'notify_state_behavior_flags':behavior_flags}
            if revised:
                actual_bool=effect.get_editor_property('bOnAttackSuccessed');assert actual_bool is False
                row.update(victim_decal_policy_verified=True,bOnAttackSuccessed=actual_bool,original_bOnAttackSuccessed=True)
            report['events'].append(row)
        report['sequences'].append({'path':record['path'],'relative':record['relative'],'sha256':sha(file),
            'raw_pose_curves_settings_unchanged':True,'existing_gameplay_guids_triggers_fields_unchanged':True,'added_states':len(groups[record['path']])})
    for d in author['death_presentations']:
        definition=unreal.load_asset(d['definition']);montage=unreal.load_asset(d['montage']);assert definition and montage
        settings=definition.get_editor_property('MonsterStamina')
        revised=rebased_definitions.get(d['definition_relative'])
        assert settings.export_text()==(revised['settings_after'] if revised else d['settings_after'])
        assert settings.get_editor_property('DeathPresentationMontage')==montage
        assert sha(H['private'](d['definition']))==(revised['merged_after_sha256'] if revised else d['definition_after_sha256'])
        assert sha(H['private'](d['montage']))==d['montage_after_sha256']
        assert montage.get_editor_property('enable_auto_blend_out') is False
        assert [v.export_text() for v in montage.get_editor_property('slot_anim_tracks')]==d['montage_slot_tracks']
        current_sections=H['montage_sections'](montage)
        section_semantics=H['semantic_montage_sections'](current_sections)
        assert section_semantics==H['semantic_montage_sections'](d['montage_sections'])
        assert len(section_semantics)==1 and section_semantics[0]['fields']['NextSectionName']=='None'
        assert section_semantics[0]['fields']['LinkValue']==0 and section_semantics[0]['fields']['SlotIndex']==0
        assert abs(montage.get_play_length()-d['seconds'])<1e-5
        report['death_presentations'].append({'family':d['family'],'definition':d['definition'],'montage':d['montage'],'saved_fields_equal':True,
            'section_semantics':section_semantics,'section_export_after_postload':current_sections,
            'section_comparison':'Only PostLoad-derived linked object/segment caches excluded; names/time/slot/next/metadata preserved.'})
    if victim:
        report['victim_decal_policy_verified_event_count']=sum(e.get('victim_decal_policy_verified') is True for e in report['events'])
        report['victim_decal_policy_verified_sequence_count']=len(victim_sequences)
        assert report['victim_decal_policy_verified_event_count']==43 and report['victim_decal_policy_verified_sequence_count']==26
    report['status']='passed';report['all_checks_passed']=True
except Exception:
    report['status']='failed';report['all_checks_passed']=False;report['error']=traceback.format_exc();unreal.log_error(report['error'])
after_hashes={path:sha(H['private'](path)) for path in selected}
report['selected_asset_sha_before']=before_hashes;report['selected_asset_sha_after']=after_hashes
report['all_selected_bytes_unchanged']=before_hashes==after_hashes
if before_hashes!=after_hashes:
    report['status']='failed';report['all_checks_passed']=False
    report['changed_asset_bytes']=[p for p in selected if before_hashes[p]!=after_hashes[p]]
if report['status']=='passed':
    try:
        D['verify_saved_victim_revision'](victim,report)
        if material_revision:
            after_material=D['visual_material_repair_revision'](delivered=VERIFY_MAIN)
            report['visual_material_repair_sha_after']={p:sha(WORK/p) for p in after_material['rows']}
            report['visual_material_repair_bytes_unchanged']=report['visual_material_repair_sha_before']==report['visual_material_repair_sha_after']
            D['verify_saved_visual_revision'](after_material,report)
        if shared:
            shared_after=D['shared_effects_rebase_revision'](delivered=VERIFY_MAIN)
            report['shared_dependency_sha_after']=shared_after['after_sha256']
            report['shared_dependency_bytes_unchanged']=report['shared_dependency_sha_before']==report['shared_dependency_sha_after']
            D['verify_saved_shared_revision'](shared_after,report)
    except Exception:
        report.update(status='failed',all_checks_passed=False,error=traceback.format_exc())
        unreal.log_error(report['error'])
name='MainSavedReadback.json' if VERIFY_MAIN else 'SavedReadback.json'
target=OUT/name;temp=target.with_suffix('.json.tmp');temp.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');os.replace(temp,target)
if not VERIFY_MAIN:
    private=WORK/'Saved/ImportReports/MonsterVFX_20261008/Authoring';private.mkdir(parents=True,exist_ok=True)
    (private/name).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('KZ_MONSTER_VFX_SAVED_'+report['status'].upper(),flush=True)
