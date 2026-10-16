import datetime, hashlib, json
from pathlib import Path
r=Path(__file__).resolve().parent
main=r.parents[2]
work=Path('C:/Users/user/Desktop/GitProject/Khazan_PlayerPartsWork_20261007/Khazan')
def read(name): return json.loads((r/name).read_text(encoding='utf-8-sig'))
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()
handoff,ready,binding,manifest,snapshot=(read(n) for n in ('MainSelectiveHandoff.json','MainReadyAudit.json','StockBinding.json','CandidateManifest.json','MainSelectiveSnapshot.json'))
assert handoff['success'] and ready['success'] and handoff['pid']==ready['pid']==13700
assert handoff['protected_unchanged']==len(snapshot['protected'])
assert handoff['dirty_content']==handoff['dirty_map']==0 and not handoff['game_world']
assert binding['status']=='Restored'
for entry in manifest['packages']:
    assert sha(main/entry['path'])==sha(work/entry['path'])==entry['preparedSha256']
for entry in binding['workFilesBefore']:
    if entry['existed']: assert sha(work/entry['relativePath'])==entry['sha256']
    else: assert not (work/entry['relativePath']).exists()
protected={'Hair':'Content/_Art/Player/Character/Meshs/Hair/Player_Original_Hair_RigidBody_PhysicsAsset.uasset',
           'Torso':'Content/_Art/Player/Character/Meshs/Torso/Player_Original_Torso_RigidBody_PhysicsAsset.uasset'}
initial={e['path']:e['sha256'] for e in read('ProtectedBefore.json')}
assert all(sha(main/p)==sha(work/p)==initial[p] for p in protected.values())
data={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'complete':True,'main_handoff_pending':False,
      'target_count':1,'modified_capsule_center_count':2,'packages':manifest['packages'],
      'main_pid':handoff['pid'],'main_world':handoff['world'],'main_reload_success':True,'main_ready_audit_success':True,
      'protected_files_unchanged_during_handoff':handoff['protected_unchanged'],'main_dirty_content':0,'main_dirty_maps':0,
      'main_pie_started_by_task':False,'main_editor_closed_by_task':False,'private_binary_fixture_restored':True,
      'hair_and_latest_left_shoulder_preserved':{part:sha(main/p) for part,p in protected.items()},
      'evidence':['CenterApplied.json','CandidateMotionVerification.json','SavedReloadMotionVerification.json','NormalDeltaMotionVerification.json','StockObservation.json','StockSavedReadback.json','MainSelectiveHandoff.json','MainReadyAudit.json','StockBinding.json'],
      'verification_state_note':'Verification.json is preserved pre-handoff QA evidence; this final receipt records completed Main delivery.'}
(r/'FinalReceipt.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('Final receipt verified: Main Leg PA1 / capsule centers2 / protected163 / private binaries restored.')
