"""Bind the current Main build/assets to actual PIE and append completion."""
from pathlib import Path
from datetime import datetime, timezone
import json, runpy
MAIN=Path(__file__).resolve().parents[2];META=MAIN/'Metadata/Parry_20261012'
D=runpy.run_path(str(MAIN/'Scripts/Engineering/deliver_player_parry_20261012.py'),run_name='parry_main_final')
RUN=runpy.run_path(str(MAIN/'Scripts/Engineering/parry_task_20261012.py'),run_name='parry_inputs')
delivery=json.loads((META/'Delivery.json').read_text());assert delivery['status']=='delivered'
build=json.loads((META/'MainBuild02/Launch.json').read_text());assert json.loads((META/'MainBuild02/Exit.json').read_text())['exit']==0
source=RUN['inputs'](MAIN);assets=RUN['parry_assets'](MAIN)
assert source==build['source'],'Main Source/Config changed after build'
assert assets==build['parry_assets']
for row in delivery['rows']:assert D['sha'](MAIN/row['path'])==row['candidate'],row['path']
manifest=json.loads((MAIN/'Binaries/Win64/UnrealEditor.modules').read_text())
module=MAIN/'Binaries/Win64'/manifest['Modules']['Khazan'];module_sha=D['sha'](module)
results={}
for name,test in [('MainPIE02','Khazan.Parry.PIE'),('MainGuardRegression01','Khazan.Guard.PIE'),('MainCollisionRegression01','Khazan.Combat.PlayerAttackCollision.PIE')]:
    launch=json.loads((META/name/'Launch.json').read_text());driver=json.loads((META/name/'Driver.json').read_text())
    assert launch['source']==source and launch['parry_assets']==assets
    assert driver['status']=='passed' and driver['test']==test and not driver['shader_failures']
    assert Path(driver['actual_module']['path'])==module and driver['actual_module']['sha256']==module_sha
    assert json.loads((META/name/'Exit.json').read_text())['exit']==0
    results[name]={'test':test,'status':'passed','driver_sha':D['sha'](META/name/'Driver.json'),'module':driver['actual_module'],'seconds':driver['seconds']}
audit=json.loads((META/'MainSavedAudit02/SavedAudit.json').read_text())
assert audit['status']=='passed' and audit['asset_saves']==0 and Path(audit['project'])==MAIN
assert audit['existing_playback_segments_preserved'] and audit['existing_guard_sections_notifies_preserved']
assert json.loads((META/'MainSavedAudit02/Launch.json').read_text())['parry_assets']==assets
assert json.loads((META/'MainSavedAudit02/Exit.json').read_text())['exit']==0
body_preserved={rel:source[rel] for rel in ['Source/Khazan/Character/KZMonster.h','Source/Khazan/Character/KZMonster.cpp','Source/Khazan/Tests/KZMonsterPresentationRepairPIETest.cpp','Source/Khazan/Tests/KZPlayerAttackCollisionPIETest.cpp']}
for rel,h in body_preserved.items():assert h==json.loads((META/'MainBuild01/Launch.json').read_text())['source'][rel]
audio='Source/Khazan/Animation/Notifies/KZAnimNotify_PlayAudio.cpp'
assert D['sha'](MAIN/audio)==D['BASE'][audio]
shots={name:D['sha'](META/'MainPIE02'/(name+'.png')) for name in ['01_ActualParryFlash','02_ActualParryMotion','03_ActualParryEffectTail']}
log=(META/'MainPIE02/Editor.log').read_text(encoding='utf-8',errors='replace')
R={'utc':datetime.now(timezone.utc).isoformat(),'status':'MainDeliveredAndFreshVerified','complete':True,'main_delivered':True,
   'runtime_changed_files':6,'runtime_new_files_classes':0,'dev_new_files':1,'existing_assets':2,'new_assets':11,
   'delivery':{'path':'Metadata/Parry_20261012/Delivery.json','sha256':D['sha'](META/'Delivery.json')},
   'main_source_and_config':source,'main_assets':assets,'actual_module':{'path':str(module),'sha256':module_sha},
   'build':{'run':'MainBuild02','exit':0,'source_matches':True,'schema_refresh':'Old copy2 mtimes left UHT PROLOG13/BODY16; touch two delivered headers rebuilt PROLOG15/BODY18 without source-content changes. Subsequent stock build selected the current canonical DLL and removed the old suffix; current manifest was preserved and reverified.'},
   'results':results,'saved_audit':{'run':'MainSavedAudit02','sha256':D['sha'](META/'MainSavedAudit02/SavedAudit.json'),'status':'passed','saves':0},
   'visual_review':{'viewed':['MainPIE02/02_ActualParryMotion.png','MainPIE02/03_ActualParryEffectTail.png'],'shots':shots,'alpha':'Continuous edge and rounded spark caps; no opaque card/sphere background boundary in actual Main output.'},
   'preserved_blood_work':body_preserved,'attached_audio_notify_unchanged':True,'private_dll_restored':False,'user_foreign_editor_control':False,
   'runtime_cases':[s.strip() for s in log.splitlines() if 'LogAutomationController: PARRY_CASE' in s],
   'verification_limits':['Original cooked shader/pixel/impact-writer exact parity','Actual speaker output (PIE uses -nosound)','Shipping/network/performance'],
   'qa_observation':'Early Main RHI viewport reported GPU memory budget exhaustion / 2-4 FPS while preparing scene resources. Functional tests use fixed timestep; no production performance claim or global quality-setting change.'}
assert len([s for s in R['runtime_cases'] if 'PARRY_CASE ' in s])==15
(META/'FinalVerification.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
(META/'ResumeState.json').write_text(json.dumps({'status':R['status'],'complete':True,'final':'Metadata/Parry_20261012/FinalVerification.json','next':'Normal editor launch uses current module and saved Parry assets. No required remaining work; no repeated author/import/delivery or old DLL restoration.','limits':R['verification_limits']},indent=2),encoding='utf-8')
stamp=datetime.now().astimezone().isoformat(timespec='seconds')
eng=f'''## {stamp} — ARCH-90 패링 Main 적용·fresh 검증 완료

이전 준비본/Main 잠금 대기는 패링 범위에서 해소됐다. Main Source7(runtime6/DEV1)/package13(기존2/신규11)을 SHA 확인·백업 후 전달했다. 현재 전체 Main Source/Config로 MainBuild02가 성공한 뒤 일반 stock build가 현재 모듈 {module.name}을 선택했다. 이를 과거 suffix로 되돌리지 않고 현재 모듈에서도 다시 검증했으며 actual loaded DLL과 동일한 Source/13 asset SHA가 FinalVerification.json에 결속됐다. MainBuild01은 copy2의 과거 mtime 때문에 구 UHT PROLOG13/BODY16을 재사용하여 실패했다. 두 전달 헤더의 시각만 갱신해 PROLOG15/BODY18을 생성했고 제품 코드 내용은 바꾸지 않았다. 후속 전달 도구는 현재 write time을 사용한다.

새 MainPIE02의 Parry15개 상황/6종 Definition 소비·고갈·비용·연타·이동 Guard·좌측 response·release/cancel/UnPossess, 기존 Guard와 PlayerAttackCollision 회귀가 모두 성공했다. MainSavedAudit02는 저장0으로 설정/원본 5 playback segment·notify/7 section/source tag를 reload 검사했다. 실제 .13/.24초 화면에서 모션/weapon contact flash/연속 alpha를 직접 검수했다. 정상 가드 후 성공으로 창을 다시 열지 않으며 전방 blockable 공격만 패링한다. 기본 .146초는 기존 source→current inverse_map 계산, 비용 .5와 detach .06초는 source 값, 몬스터 ST 피해는 기존 Definition 사용자 결정이다.

이후 혈액 작업의 KZMonster runtime2/기존 DEV2와 모든 다른 Source/Config를 보존했다. 사용자/foreign editor 제어0·private DLL 복원0·Audio Notify 수정0이다. 초기 RHI에 GPU memory budget/낮은 FPS 표시가 관측됐으며 이번 fixed-step 기능 검사로 성능을 검증했다고 주장하지 않는다. 실제 스피커 출력(-nosound), 원작 shader/pixel/impact-point 완전 일치와 Shipping/network는 미확인이다. 필수 잔여0이며 최신 결과는 Metadata/Parry_20261012/FinalVerification.json과 ResumeState.json을 따른다. 과거 전체 author/추출/옛 alias를 다시 적용하지 않는다.
'''
art=f'''## {stamp} — Player Parry 에셋 Main 전달·fresh 검수 완료

새 motion2/particle1/local master3·MI5와 기존 Guard Montage·GA를 합친13 package를 Main에 전달했고 fresh MainSavedAudit02·MainPIE02에서 확인했다. source composite/dilation/22 frame/source cue와 기존 Guard segment·notify는 유지했다. 실제 Main의 성공 모션/weapon contact flash/꼬리 프레임을 열어 불투명 card/원판 경계가 없고 입자 끝이 연속 fade하는 것을 확인했다. source MI blend overrides는 복원됐으며13 emitter를 유지한다. local parent의 .04 UV/1.25px와 spark ellipse power2는 사용자 요구에 대한 임시 표현 수치다. 기존 공유 재질·texture·audio를 재저장하지 않았다.

Main DLL/source/asset SHA와 실제 RHI/저장 검사 결과는 Metadata/Parry_20261012/FinalVerification.json에 결속됐다. 이전 Main 잠금/준비본 pending은 이 범위에서 해소됐다. DefaultPawn 검은 원판 가설 정정과 이전 실패 proof는 보존한다. 초기 RHI의 메모리 budget/FPS 경고, 원작 stripped shader/pixel/impact writer parity, 실제 스피커 출력(-nosound) 및 Shipping 성능은 범위를 구분한다. 정확한 runtime은 Engineering PARRY_IMPLEMENTATION_20261012.md, 완료 후 재개 기준은 ResumeState.json이다. 전체 추출/저작/과거 DLL 전달을 반복하지 않는다.
'''
for rel in ['Docs/Engineering/PARRY_IMPLEMENTATION_20261012.md','Docs/Engineering/ENGINEERING_PROJECT_STATE.md','Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md','Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md','Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md','Docs/Engineering/GUARD_IMPLEMENTATION_20261002.md']:
    with (MAIN/rel).open('a',encoding='utf-8',newline='\n') as f:f.write('\n\n'+eng+'\n')
for rel in ['Docs/Art/PLAYER_PARRY_SOURCE_20261012.md','Docs/Art/ART_PROJECT_STATE.md','Docs/Art/ART_KNOWLEDGE_INDEX.md','Docs/Art/ART_WORK_CONTINUITY.md']:
    with (MAIN/rel).open('a',encoding='utf-8',newline='\n') as f:f.write('\n\n'+art+'\n')
router=f'''## {stamp} — 가드 시작 패링 Main 완료 조회

패링은 Mixed다. Architecture 최신 ARCH-90 → Migration → Docs/Engineering/PARRY_IMPLEMENTATION_20261012.md와 Docs/Art/PLAYER_PARRY_SOURCE_20261012.md의 Main 완료 절 → Metadata/Parry_20261012/FinalVerification.json을 따른다. Main Source7/asset13·build/fresh Parry15/6종·Guard/PlayerAttackCollision·saved audit가 성공했다. 현재 모듈은 {module.name}이며 동시 stock build 뒤 현 Source와 함께 검증했다. 이전 Main 잠금/Work-only를 현재 상태로 읽지 않으며 전체 author/추출/옛 DLL 복원은 반복하지 않는다. 기본 창 .146초는 source clock 계산이며 alpha 표현 TEMP와 원작 완전 일치 미확인 범위를 구분한다.
'''
with (MAIN/'0_DOCUMENT_ROUTER.md').open('a',encoding='utf-8',newline='\n') as f:f.write('\n\n'+router+'\n')
print('PARRY_MAIN_COMPLETE Source7 Assets13 Build02 Parry15/6families Guard Collision SavedAudit PASS',flush=True)
