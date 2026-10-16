"""Root-launched private-only, two-package correction of five Apes material states.

Default probe saves no assets. Set KZ_MONSTER_VFX_APES_BINDING_MODE='apply'
through runpy init_globals for the explicit targeted revision. Original V3
bindings/source evidence and the original Main-before journal stay intact.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import os
import runpy
import shutil
import traceback
import unreal

MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK=Path(unreal.Paths.project_dir()).resolve()
assert WORK==Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterVFXWork_20261008/Khazan'), 'Main/shared revision blocked'
assert unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world() is None, 'Stop own PIE first'
ROOT=MAIN/'Saved/ImportReports/MonsterVFX_20261008'
AUTHOR=ROOT/'Authoring/PrivateAuthoring.json'
PLAN=ROOT/'PreparedPlaybackPlan.json'
SAVED=ROOT/'Authoring/SavedReadback.json'
EVIDENCE=WORK/'Saved/ImportReports/MonsterVFX_20261008/Resources/ApesCurrentMaterialBindingEvidence.json'
SCHEMA=MAIN/'Metadata/MonsterVFX_20261008/CurrentRuntimeFieldSchema.json'
OUT=ROOT/'Authoring/ApesCurrentMaterialBindingRevision'
OUT.mkdir(parents=True,exist_ok=True)
MODE=globals().get('KZ_MONSTER_VFX_APES_BINDING_MODE','probe')
assert MODE in ('probe','apply')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def write(path,value,expected=None):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.apes-binding.tmp')
    assert not temp.exists(),str(temp)
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if expected is not None:assert sha(path)==expected,'Report CAS changed: '+str(path)
    os.replace(temp,path)


def immutable(source,dest,expected):
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():assert sha(dest)==expected,'Retained backup differs: '+str(dest)
    else:shutil.copy2(source,dest)
    assert sha(dest)==expected


def package_file(path):
    assert path.startswith('/Game/'),path
    result=WORK/('Content/'+path.split('.')[0].removeprefix('/Game/')+'.uasset')
    assert result.resolve()==result and result.is_relative_to(WORK),'Shared/junction path blocked'
    return result


def identity(value):
    return value.get_path_name().split('.')[0] if value else None


def selected_hashes(author):
    return {p:sha(package_file(p)) for p in
        {s['path'] for s in author['sequences']}|{d[k] for d in author['death_presentations'] for k in ('definition','montage')}}


def main():
    report={'schema':'Khazan.MonsterVFX.ApesCurrentMaterialBindingRevision.v1',
        'status':'running','mode':MODE,'pid':os.getpid(),'utc':datetime.now(timezone.utc).isoformat(),
        'project':str(WORK),'asset_saves':0,'asset_mutations':0,'files':[],
        'original_source_policy':'Retain five V3 source rows and raw source evidence; add current NONV3 aliases using the same replacement. This is an explicit project presentation adapter.',
        'runtime_policy':'AcquireBinding copies effective earliest current baseline uniforms into a new nonoverlay MID before source Execution writes; original materials/BP/mesh are not edited.'}
    try:
        assert not (OUT/'Applied.json').exists(),'Already applied; use fresh saved audit, never repeat'
        plan=read(PLAN);author=read(AUTHOR);evidence=read(EVIDENCE)
        before_report_sha={str(p):sha(p) for p in (PLAN,AUTHOR,SAVED,EVIDENCE,SCHEMA)}
        assert author['status']=='passed' and author['plan_sha256']==sha(PLAN)
        assert len(author['sequences'])==487 and len(author['events'])==3342 and len(author['mutation_journal'])==499
        assert len(evidence['aliases'])==5 and sha(evidence['source_manifest'])==evidence['source_manifest_sha256']
        original_author=copy.deepcopy(author)
        before_assets=selected_hashes(author)
        H=runpy.run_path(str(MAIN/'Scripts/Art/monster_vfx_author_20261008.py'),run_name='apes_binding_revision_helpers')
        alias={r['source_v3_native']:r['current_native'] for r in evidence['aliases']}
        assert len(alias)==5 and len(set(alias.values()))==5
        for row in evidence['saved_native_identity']:
            # These are read-only identities; the reused Blueprint may be a
            # Main-backed junction. Only the two mutation targets must be physical.
            file=WORK/row['relative_file'];resolved=file.resolve()
            assert resolved.is_relative_to(WORK) or resolved.is_relative_to(MAIN),str(resolved)
            assert sha(file)==row['private_sha256'],row['relative_file']
        cls=unreal.load_class(None,'/Game/Bluprints/Monsters/BP_Monster_ApesStoneHandElite.BP_Monster_ApesStoneHandElite_C')
        assert cls,'Current Apes Blueprint missing'
        cdo=unreal.get_default_object(cls);mesh=cdo.get_editor_property('mesh');assert mesh
        slots=[identity(mesh.get_material(i)) for i in range(mesh.get_num_materials())]
        assert len(slots)==5 and set(slots)==set(alias.values()),('Loaded current Apes slots differ',slots)
        report['loaded_current_material_slots']=slots
        report['loaded_mesh']=identity(mesh.get_skeletal_mesh_asset())
        report['aliases']=evidence['aliases'];report['evidence_sha256']=sha(EVIDENCE)
        targets=[e for e in plan['events'] if e['family']=='ApesStoneHandElite' and e['state_fields'].get('MaterialOverrides')]
        paths={e['asset'] for e in targets}
        assert len(targets)==5 and len(paths)==2,(len(targets),paths)
        assert all(p.startswith('/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/') for p in paths)
        records={r['event_id']:r for r in author['events']}
        sequence_records={r['path']:r for r in author['sequences']}
        journal={r['path']:r for r in author['mutation_journal']}
        loaded={};prepared=[]
        for path in sorted(paths):
            record=sequence_records[path];assert before_assets[path]==record['after_sha256']
            asset=unreal.load_asset(path);assert isinstance(asset,unreal.AnimSequence)
            assert H['verify_preserved'](asset,record['before'])==record['after']
            loaded[path]=asset
        for e in targets:
            record=records[e['event_id']];assert record['state_fields']==e['state_fields']
            old=e['state_fields']['MaterialOverrides'];assert len(old)==5 and {r['SourceMaterial'] for r in old}==set(alias)
            rows=copy.deepcopy(old)+[{'SourceMaterial':alias[r['SourceMaterial']],'ReplacementMaterial':r['ReplacementMaterial']} for r in old]
            assert len({r['SourceMaterial'] for r in rows})==10
            for row in rows:
                assert unreal.load_asset(row['SourceMaterial']) and unreal.load_asset(row['ReplacementMaterial'])
            event=next(v for v in H['state_events'](loaded[e['asset']]) if H['guid'](v.export_text())==record['guid'])
            state=event.get_editor_property('notify_state_class');assert state.get_class()==H['STATE']
            assert int(state.get_editor_property('NotifyStateBehaviorFlags'))==0
            assert H['data_fields'](state,e['state_fields'])==record['state_readback']
            fields=copy.deepcopy(e['state_fields']);fields['MaterialOverrides']=rows
            prepared.append((e,record,event,state,fields))
        report.update(plan_before_sha256=sha(PLAN),author_before_sha256=sha(AUTHOR),
            source_schema_sha256=sha(SCHEMA),target_states=5,target_packages=sorted(paths),
            selected_before_sha256=before_assets,original_main_before_journal_preserved=True)
        if MODE=='probe':
            transient=unreal.new_object(H['STATE'])
            H['assign_extra'](transient,{'MaterialOverrides':prepared[0][4]['MaterialOverrides']})
            assert len(H['data_fields'](transient,{'MaterialOverrides':[]})['MaterialOverrides'])==10
            assert selected_hashes(author)==before_assets
            report['status']='passed';report['transient_only_probe']=True
            write(OUT/'Probe.json',report)
        else:
            for path,expected in before_report_sha.items():assert sha(path)==expected
            for p in (PLAN,AUTHOR,SAVED):immutable(p,OUT/'BeforeReports'/p.name,sha(p))
            for path in sorted(paths):
                immutable(package_file(path),OUT/'BeforeAssets'/H['relative'](path),before_assets[path])
            for e,record,event,state,fields in prepared:
                old_text=event.export_text();old_timing=H['actual_event'](event)
                loaded[e['asset']].modify()
                H['assign_extra'](state,{'MaterialOverrides':fields['MaterialOverrides']})
                assert event.export_text()==old_text and H['actual_event'](event)==old_timing
                assert int(state.get_editor_property('NotifyStateBehaviorFlags'))==0
                e['state_fields']=fields
                e.setdefault('limitations',[]).append('Explicit current NONV3 mesh material aliases added to the five preserved original V3 bindings. Native MID copies effective current uniforms; no original shader/body material identity equivalence claimed.')
                e['current_material_binding_adapter']={'kind':'original_v3_to_current_nonv3_alias','evidence':str(EVIDENCE),'evidence_sha256':sha(EVIDENCE)}
                record['state_fields']=copy.deepcopy(fields)
                record['state_readback']=H['data_fields'](state,fields)
                assert H['data_fields'](state.get_editor_property('Effect'),record['effect_fields'])==record['effect_readback']
                report['asset_mutations']+=1
            for path in sorted(paths):
                assert sha(package_file(path))==before_assets[path]
                asset=loaded[path];after=H['verify_preserved'](asset,sequence_records[path]['before'])
                assert unreal.EditorAssetLibrary.save_loaded_asset(asset,False)
                after_sha=sha(package_file(path));report['asset_saves']+=1
                sequence_records[path]['after']=after;sequence_records[path]['after_sha256']=after_sha
                journal[path]['saved_sha256']=after_sha
                report['files'].append({'path':path,'relative':H['relative'](path),'revision_before_sha256':before_assets[path],
                    'after_sha256':after_sha,'original_main_before_sha256':sequence_records[path]['before_sha256'],
                    'backup_path':str(OUT/'BeforeAssets'/H['relative'](path))})
            after_assets=selected_hashes(author)
            assert all(after_assets[p]==h for p,h in before_assets.items() if p not in paths)
            assert len(after_assets)==499
            assert all(j['before_sha256']==old['before_sha256'] and j.get('backup_path')==old.get('backup_path')
                and j.get('backup_sha256')==old.get('backup_sha256') for j,old in zip(author['mutation_journal'],original_author['mutation_journal']))
            assert author['death_presentations']==original_author['death_presentations']
            assert all(e==old for e,old in zip(author['events'],original_author['events']) if e['event_id'] not in {v[0]['event_id'] for v in prepared})
            plan.setdefault('source_inputs',{})[str(EVIDENCE)]=sha(EVIDENCE)
            plan['current_material_binding_revision']={'kind':'ApesCurrentMaterialBindingRevision','target_states':5,'target_packages':2,
                'original_plan_sha256':before_report_sha[str(PLAN)],'evidence':str(EVIDENCE),'evidence_sha256':sha(EVIDENCE)}
            assert sha(SCHEMA)==before_report_sha[str(SCHEMA)]
            write(PLAN,plan,expected=before_report_sha[str(PLAN)])
            author['plan_sha256']=sha(PLAN)
            author.setdefault('presentation_revisions',[]).append({'kind':'ApesCurrentMaterialBindingRevision','script_sha256':sha(__file__),
                'previous_author_sha256':before_report_sha[str(AUTHOR)],'previous_plan_sha256':before_report_sha[str(PLAN)],'files':report['files']})
            write(AUTHOR,author,expected=before_report_sha[str(AUTHOR)])
            private_reports=WORK/'Saved/ImportReports/MonsterVFX_20261008'
            write(private_reports/'PreparedPlaybackPlan.json',plan)
            write(private_reports/'Authoring/PrivateAuthoring.json',author)
            report.update(status='passed',plan_after_sha256=sha(PLAN),author_after_sha256=sha(AUTHOR),selected_after_sha256=after_assets,
                unselected_author_asset_bytes_unchanged=True,source_schema_unchanged=True,fresh_saved_audit_required=True)
            write(OUT/'Applied.json',report)
            write(private_reports/'Authoring/ApesCurrentMaterialBindingRevision.json',report)
        print('KZ_MONSTER_VFX_APES_BINDING_'+report['status'].upper(),flush=True)
    except Exception:
        report['status']='failed';report['error']=traceback.format_exc()
        if 'before_assets' in locals():
            report['current_asset_hashes']={p:sha(package_file(p)) for p in before_assets}
        report['retry_contract']='No automatic retry/rollback. Close only own process unsaved; CAS changed two private packages against captured current SHA and verified BeforeAssets backups. Restore report bytes from immutable BeforeReports after exact report CAS. Main-original journal/Before assets must never be rebased.'
        write(OUT/('Failed_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json'),report)
        unreal.log_error(report['error']);print('KZ_MONSTER_VFX_APES_BINDING_FAILED',flush=True)
        raise


if __name__=='__main__':main()
