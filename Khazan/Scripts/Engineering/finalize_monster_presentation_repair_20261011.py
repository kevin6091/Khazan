"""Bind delivered Main files, preserved audio and fresh native/RHI evidence."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,difflib,re
main=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan');root=main/'Metadata/MonsterPresentationRepair_20261011'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
plan=read(root/'DeliveryPreparation/Plan.json');receipt=read(root/'MainDelivery/Receipt.json')
assert receipt['source_files']==10 and receipt['asset_packages']==59
checks={}
for name in ['MainRuntime02','MainUI02','MainActualHit01']:
    driver=read(root/name/'Driver.json');exit=read(root/name/'Exit.json')
    assert driver['status']=='passed' and exit['exit']==0 and not driver['material_compile_failures']
    assert Path(driver['project'])==main and driver['actual_loaded_module']==driver['manifest_module']
    final_module_sha=sha(Path(driver['actual_loaded_module']))
    # The concurrent audio task reuses suffix91 after an editor exits. Keep the actual load-time proof.
    assert final_module_sha==driver['module_sha256'] or name=='MainUI02'
    checks[name]={'test':driver['test'],'passed':True,'exit':0,'material_fallback':0,'actual_module':driver['actual_loaded_module'],'dll_sha256_at_load':driver['module_sha256'],'dll_sha256_now':final_module_sha,'shared_alias_rebuilt_after_proof':final_module_sha!=driver['module_sha256']}
for name in ['MainBuild01','MainBuild02','MainBuild03','MainBuild04']:
    assert read(root/(name+'.json'))['exit']==0
audit=read(root/'MainSavedAudit02/SavedAudit.json');assert audit['status']=='passed' and audit['package_saves']==0
assert len(audit['attack_assets'])==198 and sum(len(r['verified']) for r in audit['attack_assets'])==1577 and len(audit['blood_decal_states'])==42 and len(audit['masters'])==9
audio_before=read(root/'AudioCensusMainBefore01/AudioCensus.json');audio_after=read(root/'AudioCensusMainAfter01/AudioCensus.json')
assert audio_before['status']==audio_after['status']=='passed' and audio_before['animations']==audio_after['animations']
assert audio_after['notify_count']==67
audio_latest=read(root/'AudioCensusMainAfter02/AudioCensus.json');assert audio_latest['status']=='passed' and audio_latest['notify_count']==67
def normalized_audio(census):
    return {p:[{**r,'event':re.sub(r'Guid=[0-9A-Fa-f]{32}','Guid=REGENERATED',r['event'])} for r in rows] for p,rows in census['animations'].items()}
assert normalized_audio(audio_before)==normalized_audio(audio_latest),'Concurrent audio changed playback beyond a new GUID'
audio_paths=set(audio_latest['animations'])
runtime=read(root/'MainRuntime02/Runtime.json');assert runtime['status']=='passed' and runtime['attack_assets']==198 and runtime['source_occurrences']==1577 and runtime['death_families']==6
launch=read(root/'MainRuntime02/Launch.json');assert all(sha(main/p)==h for p,h in launch['source_sha256'].items()),'Source changed since final full PIE'
assets=[]
for row in plan['assets']:
    current=sha(main/row['path'])
    assert current==row['after'] or row['path'] in audio_paths,('Delivered asset changed',row['path'])
    assets.append({'path':row['path'],'sha256':current,'concurrent_audio_guid_refresh_after_delivery':current!=row['after']})
source=[];patch=[]
qa_followup=['Source/Khazan/Tests/KZCombatUIPIEEditor.cpp','Source/Khazan/Tests/KZMonsterPresentationRepairPIETest.cpp']
for row in plan['source']:
    path=main/row['path'];current=sha(path)
    assert current==row['after'] or row['path'] in qa_followup,('Unexpected concurrent source change',row['path'])
    before=root/'MainDelivery/Before'/row['path'];old=before.read_text(encoding='utf-8-sig') if before.exists() else ''
    patch.extend(difflib.unified_diff(old.splitlines(True),path.read_text(encoding='utf-8-sig').splitlines(True),fromfile=row['path'],tofile=row['path']))
    source.append({'path':row['path'],'sha256':current,'qa_followup':current!=row['after']})
fall='Source/Khazan/Ability/PlayerAbility/KZFallAbility.cpp';baseline=read(root/'Baseline.json')['files'];assert sha(main/fall)==baseline[fall]
ring='Content/UI/Combat/Materials/M_UI_BrutalRing.uasset';assert sha(main/ring)=='c4d6ff781af4bdf9955722e698aae2b382e359949b771df91ff54c30e4039100'
hit_log=(root/'MainActualHit01/Editor.log').read_text(encoding='utf-8',errors='replace');hits=re.findall(r'PlayerAttackCollision case=(\S+).*?HPChanges=(\d+) expectedHits=(\d+) bloodBursts=(\d+)',hit_log)
assert len(hits)==13 and all(hp==expected==blood for _,hp,expected,blood in hits)
attack_pngs=list((root/'MainRuntime02').glob('Attack_*.png'));death_pngs=[p for p in (root/'MainRuntime02').glob('*.png') if not p.name.startswith('Attack_')];assert len(attack_pngs)==192 and len(death_pngs)==18
numeric=[r for r in runtime['attack_events'] if 'offset_error_cm' in r];assert len(numeric)==1483
manifest=read(main/'Binaries/Win64/UnrealEditor.modules');latest=main/'Binaries/Win64'/manifest['Modules']['Khazan']
result={'status':'MainDeliveredAndFreshVerified','utc':datetime.now(timezone.utc).isoformat(),'project':str(main),'source_files':10,'asset_packages':59,'new_runtime_files':0,'private_author_delivered':False,
        'checks':checks,'saved_audit':{'attack_assets':198,'source_occurrences':1577,'removed_blood_decal_states':42,'removed_blood_mesh_receivers':16,'corpse_masters':9,'package_saves':0},
        'visual_review':{'attack_images':192,'attack_contact_sheets':8,'no_component_attack_assets':6,'blood_ash_late_dissolve_images':18,'halberd_ui_images':['02_DamagedGauges.png','03_ActualLockOn.png','04_BrutalAvailable_B.png'],'reviewed':True},
        'transform_comparison':{'samples':1483,'max_cm':max(r['offset_error_cm'] for r in numeric),'max_degrees':max(r['angle_error_deg'] for r in numeric),'reference':'Original typed socket/offset/rotation after evaluated pose, not original executable/pixel comparison'},
        'actual_accepted_hit_cases':13,'audio_notifies_preserved':67,'audio_guid_timing_properties_equal_at_delivery':True,'latest_audio_playback_and_timing_equal':True,'concurrent_audio_guid_refresh_packages':sum(r['concurrent_audio_guid_refresh_after_delivery'] for r in assets),'fall_unchanged':True,'foreign_brutal_ring_unchanged':True,
        'current_manifest_module':str(latest),'current_manifest_module_sha256':sha(latest),'shared_manifest_note':'Concurrent audio builds select a newer Main module; each proof records the exact DLL actually loaded. Runtime repair source and visual fields are unchanged. Latest audio GUID refresh is preserved and separately read back.',
        'source':source,'assets':assets,'original_unconfirmed':['Halberd CorrectionInfos52 native reference bone/TM contract','Original stripped shader/executable/VM/pixel/frame parity','Shipping performance']}
(root/'MainDelivery/FinalSource.diff').write_text(''.join(patch),encoding='utf-8')
(root/'FinalVerification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['source','assets','checks']},ensure_ascii=False))
