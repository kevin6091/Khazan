from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib,math
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Metadata/MonsterRootCollisionRepair_20261012'
def read(p):return json.loads((OUT/p).read_text(encoding='utf-8-sig'))
assert not (OUT/'FinalVerification.json').exists()
build=read('MainBuild02/Exit.json');assert build['exit']==0 and build['input_unchanged']
tests={n:read(n+'/Driver.json') for n in ['MainRootPoses01','MainContacts01','MainPlayerCollision01']}
for n,t in tests.items():assert t['status']=='passed' and t['module_sha256']==build['module_sha256'],n
delivered=read('Delivered.json')
for r in delivered['files']:assert hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['after_sha256'],r['path']
before=read('MainUsageAudit02/Usage.json');saved=read('MainSavedAudit01/Usage.json');assert saved['status']=='passed' and saved['dirty_content']==[]
assert saved['summary']==before['summary'] and saved['definitions']==before['definitions'] and saved['montages']==before['montages']
changes=set(r['asset'] for r in read('RootLockPlan.json')['assets'])
old={r['asset']:r for r in before['sequences']}
for r in saved['sequences']:
    expected=dict(old[r['asset']]);expected['root_lock']=r['root_lock']
    assert r==expected and r['root_motion'] and r['force_root_lock'],r['asset']
    assert ('REF_POSE' in r['root_lock'])==(r['asset'] in changes),r['asset']
raw={r['asset']:r for r in read('RootPreservationBefore01/RootPoses.json')}
poses=read('MainRootPoses01/RootPoses.json');assert len(poses)==392
for r in poses:
    assert r['data_model_sha1']==raw[r['asset']]['data_model_sha1'] and r['notifies_sha1']==raw[r['asset']]['notifies_sha1'],r['asset']
    assert r['root_offset_cm']<.01 and r['root_angle_degrees']<math.degrees(1e-4)
contacts=read('MainContacts01/MonsterContactCases.json');assert len(contacts)==30
for r in contacts:assert r['hits']==(1 if r['case'] in [0,4] else 0) and r['hp_delta']==(7 if r['case'] in [0,4] else 0)
fx=read('AllAttackEffects01/Runtime.json');assert fx['status']=='passed' and fx['attack_assets']==198 and fx['source_occurrences']==1577 and fx['death_families']==6
stamp=datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
report={'status':'main_applied_build_and_fresh_runtime_complete','date':stamp,'main':str(ROOT),'root_options_audited':395,'body_sequences':392,'prop_sequences':3,'root_lock_packages_changed':88,'body_pose_samples':1176,'complete_models_and_notifies_unchanged':392,'monster_window_cases':30,'player_collision_cases':16,'attack_effect_assets':198,'effect_occurrences':1577,'death_families':6,'effect_runtime_project':'private project with the same delivered runtime Source; Main fresh root/contact/player plus exact package/Source verification','main_build':build,'tests':tests,'delivered':'Delivered.json','native_preservation':'MainRootPoses01/RootPoses.json vs RootPreservationBefore01/RootPoses.json','source_damage_windows_and_montages_unchanged':True,'saved_packages_dirty':0,'new_runtime_files':0,'backup':['RootAssetsBefore','MainBefore'],'limitations':['Original native shaders / exact pixel parity / full two-level continuous combat / multiplayer are not asserted.','Corrected-curve per-pose branch is preserved structurally; this occurrence report contains no active correction-curve rows.'],'failed_history':['Initial source-basis Python API errors preserved.','Root pose before89 technical failures includes88 real first-root offsets and existing .0020149deg compressed RoundAttack angle.','Private first contact fixture: recovery reuse and deferred brain restart; isolated fresh controller fixture passed30.','MainBuild01 compiler PCH virtual-memory exhaustion C3859/C1076; MainBuild02 serial build passed.']}
(OUT/'FinalVerification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
resume=dict(report,status='complete',remaining=[])
(OUT/'ResumeState03.json').write_text(json.dumps(resume,ensure_ascii=False,indent=2),encoding='utf-8')
eng=f'''\n\n## {stamp} — ARCH-91 Root·공격 콜라이더·VFX Main 완료
Main에 Source7(runtime4/DEV3) 및 RootMotionRootLock 옵션만 바꾼 Animation88 package를 exact SHA/CAS로 반영했다. 새 runtime file/class/manager0, 다른 baseline610파일 보존, private DLL/Config 전달0. MainBuild01은 source 오류 없이 PCH virtual-memory C3859/C1076로 실패했고, 병렬1/noXGE MainBuild02는 Succeeded/input unchanged다. 현재 canonical UnrealEditor-Khazan.dll SHA `{build['module_sha256']}`를 사용한다.
실제 사용395 Root enabled/force lock/true-root·track0 및 Body392의1176포즈를 확인했다. 첫 프레임 누적 origin88개만 RefPose lock으로 정렬했으며 근거는 RootLockPlan의 imported RAW root first transform와 skeleton reference pose/UE FRootMotionReset이다. RootAssetBefore 및 MainBefore 백업을 보존한다. 전체 DataModel 모든 key/curve/attribute와 notify event/object SHA392개가 변경 전=private 후=Main fresh로 동일하다. source montage126/definition57/node220/window405의 geometry key·time·HP/Stamina·group·audio와 rate/나머지옵션이 fresh saved audit에서 동일하다. Props3는 다른 skeleton으로 body1176포즈에서 분리하고395 옵션/track audit에 포함했다.
Main actual RootPoses/MonsterHits30/PlayerAttackCollision16 Success. monster30은6종별 한 window 안1회 / 종료 후접근0 / exact-end pause후접근0 / 취소후접근0 / live mesh scale와actor yaw 반영을 실제 HP GE로 확인한다. player16의 기존 Spin7/Fury19와blood13 기반행동도 보존한다. source scale/last-End 경계·timer 종료만 기존 ComboAction에 보완했다. VFX198 assets/1577 source occurrences 및Death6는 동일 delivered Source의 private 실제RHI Success, finite world transforms / deterministic uncorrected source geometry max position3.46e-13cm·angle4.83e-6deg / template identity / body size를 확인했다. 이 보고서의 active correction-curve row는0이므로 해당 branch의 per-pose 실행을 실제 데이터 검증했다고 표현하지 않는다. source 없는 VFX actor axes/mesh origin 및 body scale은 적용했으며 curve branch는 기존 receipt의 latest GT clock→finalized-bone callback으로 구조 보완했다. 원작 native shader/pixel parity·전체두레벨연속전투·network는 검증 완료 범위가 아니다.
Main 파일·canonical build·fresh saved/actual runtime 완료. FinalVerification.json / ResumeState03.json 및 exact Delivered95를 재개 정본으로 읽는다. stage/old alias/full author/retime/reimport를 반복하지 않는다. Main editor 정상 재시작 후 직접 Play에서 green debug volume이 실제 공격 window에서만 나타나고 칼의 크기·방향/몸체 alignment를 확인할 수 있다.\n'''
for rel in ['Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md','Docs/Engineering/ENGINEERING_PROJECT_STATE.md','Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md','Docs/Engineering/MONSTER_ATTACK_ROOT_MOTION_20261007.md','Docs/Engineering/MONSTER_VFX_RUNTIME_20261008.md']:
    with (ROOT/rel).open('a',encoding='utf-8') as f:f.write(eng)
art=f'''\n\n## {stamp} — 사용 애니메이션 Root88 / VFX basis·scale Main 완료
현재 사용395개/body392+prop3에 대해 Root 옵션/track을 확인하고 native first/mid/end1176포즈를 검사했다. Animation88의 first-frame 누적 origin을 RefPose lock으로 정렬했다. Root raw channels, 전체 model·notify392 SHA, 모든 timing/Root enable/force/normalized scale 및 original resources는 보존됐다. exact imports 기준 수치는 RootLockPlan.json의 first-root/skeleton reference 필드이며 신규 원작 튜닝값이 아니다. actor 좌표의 root-stripped source collision에 live body scale을 한 번 반영, socket 없는FX는actor orientation+mesh origin/offset·size body scale 적용. VFX198/1577 및 death6는 delivered Source와 동일한 private RHI Success이고 Main current canonical/freshRoot·HP30·Player16·saved 원본 유지가 Success다. active correction-curve rows0 / 원작 native·pixel parity·전체두레벨·network는 완료 검증으로 표현하지 않는다. Metadata/MonsterRootCollisionRepair_20261012/FinalVerification.json 및 ResumeState03.json, MainBefore/RootAssetsBefore 백업을 따른다.\n'''
for rel in ['Docs/Art/ART_PROJECT_STATE.md','Docs/Art/ART_WORK_CONTINUITY.md','Docs/Art/ENEMY_ANIMATION_ORGANIZATION_20261007.md','Docs/Art/MONSTER_PRESENTATION_REPAIR_20261011.md']:
    with (ROOT/rel).open('a',encoding='utf-8') as f:f.write(art)
with (ROOT/'0_DOCUMENT_ROUTER.md').open('a',encoding='utf-8') as f:f.write(f'\n\n## {stamp} — 몬스터 Root·충돌·이펙트 Main 완료 조회\nMixed 요청은 Architecture ARCH-91 완료→Migration→Engineering MONSTER_ATTACK_ROOT_MOTION_20261007 / MONSTER_VFX_RUNTIME_20261008, Art ENEMY_ANIMATION_ORGANIZATION_20261007 / MONSTER_PRESENTATION_REPAIR_20261011의 최신 추가 절 및 Metadata/MonsterRootCollisionRepair_20261012/FinalVerification.json·ResumeState03.json을 따른다. Source7/RootLock88·current canonical build·fresh MainRoot1176/monster30/player16/saved 동일, 동일 Source privateFX198/1577/death6 완료. 다른 Source/자산·오래된alias/fullauthor/reimport를 반복 전달하지 않는다.\n')
print('MAIN_CONTACT_FINAL_COMPLETE',stamp)
