"""Append actual completed Engineering evidence without replacing existing records."""
import json,hashlib,datetime,re
from pathlib import Path
ROOT=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=ROOT/'Metadata/PlayerAttackCollision_20261008'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
delivered=json.loads((OUT/'SourceContentDelivered.json').read_text(encoding='utf-8'))
native=json.loads((OUT/'NativeAliasDelivered.json').read_text(encoding='utf-8'))
saved=json.loads((OUT/'MainFreshSavedReadback.json').read_text(encoding='utf-8'))
assert delivered['status']=='SourceContentDelivered' and saved['success']
assert (saved['attack_nodes'],saved['window_count'],saved['key_count'])==(18,60,553)
assert saved['draw_green_enabled'] and not saved['dirty_content']
for row in delivered['files']:assert sha(ROOT/row['file'])==row['after']
for row in native['files']:assert sha(ROOT/row['file'])==row['sha256']
assert sha(ROOT/'Binaries/Win64/UnrealEditor.modules')==native['manifest_after_sha256']
assert all(sha(ROOT/'Binaries/Win64'/name)==value for name,value in native['stock_modules_preserved'].items())
log=(OUT/'MainFreshSavedEditor.log').read_text(encoding='utf-8',errors='replace')
assert "InternalLoadLibrary: 'Khazan' ('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Binaries/Win64/UnrealEditor-KhazanPlayerAttackCollision20261008.dll')" in log
changes={
'Docs/Engineering/PLAYER_ATTACK_COLLISION_CURRENT_IMPLEMENTATION.md': '''
## 2026-10-08 — Main 선택 반영 및 최종 검증 완료 (15:55 KST)

- 최신 Main Snow 변경 2개를 private Source에 읽어들인 뒤 실제 compile/link를 수행했다. `Build_FinalMatchedMainSource.log`는 11개 action과 Result: Succeeded를 기록한다. 이 module로 새 Work process에서 native 충돌 13개 case를 재실행해 Success를 확인했다(`FrozenFinalPlayerCollisionPIE.log`).
- 정상 실제 입력 전환 6건과 Weak05 조기 입력 거절 1건의 최종 판정을 `VerifiedComboExpectations.json`에 남겼다. Y press/release 9.701347~9.752812s는 현행 InputOpen 9.884994s 이전이며, raw timeout 기록을 성공 문자열로 고치지 않았다. Guard/Heal Success는 `FrozenRegressionPIE.log`와 `GuardHealRegression.json`에 보존한다.
- 검증된 기존 runtime Source 3개, DEV fixture 1개, Player ComboDefinition 및 신규 공통 Damage GE 2개를 Main에 선택 반영했다. 다른 Source/Config/Player BP·ABP·무기·physics/Monster 초기화 등 146개 보호 파일은 그대로 유지됐다. Main/Work 전체 Source hash 일치도 확인했다. `PreparedDeliveryManifest.json`, `SourceContentDelivered.json` 및 `Before/`가 정확한 범위와 이전 bytes를 보존한다.
- 실행 중 Main PID31344의 stock DLL은 바꾸지 않았다. 일치하는 private build를 별도 `UnrealEditor-KhazanPlayerAttackCollision20261008.dll/.pdb`로 전달하고 module manifest만 다음 실행에 맞췄다. BuildId 55116800과 기존 stock binary는 보존했다(`NativeAliasDelivered.json`). 기존 Main에 compile/PIE/native reload/save-all/close를 실행하지 않았다.
- 별도 새 Main PID2512가 전달 module을 실제 로드했다. 저장된 26 nodes 중 공격 node18, windows60, keys553, green draw=true, instant GE의 HP/Stamina SetByCaller modifier 2개, BP_Player UpToDate와 dirty content 없음이 모두 확인됐다(`MainFreshSavedReadback.json`, `MainFreshSavedEditor.log`). 읽기 전용 검사 후 이 소유 프로세스는 정상 종료했다.
- 현재 열린 Main PID31344는 여전히 `UnrealEditor-Khazan.dll`을 로드한다. **Main을 정상 재시작한 다음 Player ComboDefinition을 편집/PIE한다.** 구 native schema로 새 Player ComboDefinition을 다시 저장하지 않는다. 다른 작업용 editor도 새 schema를 반영한 native build 없이 해당 DA를 저장하지 않는다.
- 추가 화면 캡처 helper는 Python에 노출되지 않은 AbilitySystemBlueprintLibrary API를 사용해 완료하지 못했다. `ActualWeakNormalTarget.json`에 helper 실패를 기록했고 실제 gameplay 검증에 포함하지 않았다. 녹색 draw의 최종 화면 캡처나 정상 크기 target에서 모든 authored window의 시각적 정합 검증을 완료했다고 표현하지 않는다. 기존 native shape/range 검사 및 연타 횟수 검증과 구분한다.
- 남은 사용자 튜닝/원작 확인 범위는 Cylinder 높이, 미직렬화 Shape, OverFury 첫 CA 매핑, 절대 피해량/Guard 정책이다. 새 기능 추가나 자동 재작성 없이 기존 window editor 값으로 조정한다. 전체 재추출·재임포트는 필요하지 않다.
''',
'Docs/Engineering/ENGINEERING_PROJECT_STATE.md': '''
## 2026-10-08 — Player Combo 공격 충돌 Main 적용 완료

- 기존 Combo Ability/Definition의 작은 확장으로 공격 node18에 window60/key553, 공격별 편집 가능한 HP/Stamina damage와 초록색 debug draw를 연결했다. 기존 Monster ASC/Attribute/Guard를 재사용한다. 새 runtime class/component/manager는 없다.
- 최신 Source cold compile/link, 충돌 native13case, 실제 입력 전환6+조기입력 거절1, 기존 Guard/Heal 및 새 Main 저장 readback을 확인했다. 선택 전달6파일 외 보호146파일과 기존 stock DLL은 유지한다.
- 현행 정본: `Docs/Engineering/PLAYER_ATTACK_COLLISION_CURRENT_IMPLEMENTATION.md`. 원작 근거와 임시 Cylinder/OverFury/피해/Guard 설정, 검증 한계, 정확한 전달·build·PIE 증거는 이 문서를 사용한다.
- 실행 중 Main은 구 DLL이므로 정상 재시작 후 새 DA를 편집/PIE한다. 다른 작업용 구 schema editor에서 해당 Player ComboDefinition을 다시 저장하지 않는다.
''',
'Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md': '''
## 2026-10-08 — ARCH-81 실제 적용·검증 결과

- 공격 collision의 window/pose key/shape/extent/HitGroup/HP·Stamina damage는 기존 ComboDefinition node가, timer/query/대상별 중복 적중/전환·취소·종료 cleanup은 기존 ComboActionAbility가 소유하도록 실제 적용했다. 기존 ASC/AttributeSet와 instant SetByCaller GE를 재사용하며 새 runtime manager/component/state/tag/task는 추가하지 않았다.
- 원작 duration·baked geometry를 사용하되 recipient dedup/channel/Guard/절대 피해 환산은 원작 native 검증과 구분한다. 확인되지 않은 해석/임시값을 editor Source와 현행 구현 문서에 표시한다.
- Main 선택 전달, 최신 Source compile/link, 충돌13case와 실제 입력·Guard·Heal 검사, 별도 새 Main의 저장 schema readback이 완료됐다. 실행 중 Main 강제 reload/restart는 하지 않았다. 구 editor는 정상 재시작 후 해당 DA를 저장한다. 계약·검증·수치 정본은 `PLAYER_ATTACK_COLLISION_CURRENT_IMPLEMENTATION.md`와 task receipt를 따른다.
''',
'Docs/Engineering/PHYSICS_DIAGNOSTICS.md': '''
## 2026-10-08 — Player Combo 공격 query 충돌 정본

- 공격은 물리 simulate component 추가 없이 Ability의 활성 구간 query로 검사한다. Box/Sphere overlap+sweep 및 Cylinder broadphase+finite-cylinder/capsule narrowphase를 사용한다. 엔진 frame 사이에 지나간 authored key도 검사하며 green debug shape를 그린다.
- 원작 Box halfextent/offset은 stored Bounds116/116 재구성으로 확인했다. actor-facing groundcm baked center에 현행 mesh Z=-88cm만 적용하며 yaw/.01을 중복 적용하지 않는다. Cylinder height 의미는 미확인이므로 임시 halfheight=Size.Z/2로 표시한다.
- controlled 정상 capsule 적중/범위 밖 제외와 중복·취소·하한 등 native13case 통과. Spinning7/OverFury19 총횟수 검증은 큰 target capsule이며 정상 target의 모든 공격 시각 정합 검증과 구분한다. 구체 데이터/출처/보고서는 `Docs/Engineering/PLAYER_ATTACK_COLLISION_CURRENT_IMPLEMENTATION.md`를 사용한다. Player parts physics/BP/ABP는 이번 전달에서 보존했다.
''',
'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md': '''
## 2026-10-08 — Player Combo 공격 충돌 구현·전달 완료 / 구 Main 재시작 절차

- 상태: runtime3기존파일+DEVfixture1+DA/GE2 선택 전달 완료. 원작 기반 node18/window60/key553 및 editor damage/green draw 설정 포함. 별도 최신 compile/link Success, 충돌13case 재검증 Success, input6양성+1예상 거절, Guard/Heal Success, 새 Main 저장 readback Success.
- 마지막 검증: 새 Main PID2512가 전달 alias module로 전체 저장 schema/GE/Player BP/dirty없음을 확인하고 정상 종료했다. 실행 중 Main PID31344는 stock old DLL 유지; shared PIE/compile/save-all/restart 없음. 보호146files와 stock binary hash 보존. 정확한 후보/이전본/native source snapshot은 Metadata/PlayerAttackCollision_20261008/의 PreparedDeliveryManifest.json, SourceContentDelivered.json, NativeAliasDelivered.json, FinalDeliveryVerification.json, Before/를 사용한다.
- 별도 캡처 helper는 미노출 Python API 오류로 gameplay 검증에서 제외했다. ActualWeakNormalTarget.json 기록은 product 실패/원작 시각 일치 근거가 아니다. 원작 Cylinder 높이/미직렬화 Shape/OverFury 첫 mapping/절대 damage·Guard 근거는 여전히 미확인 또는 임시다.
- 정확한 다음 절차: (1) 사용자 Main을 정상 재시작한다. (2) /Game/Data/ComboCommand/DA_Player_Combo_Definition → Nodes → AttackWindows에서 HPDamage/StaminaDamage/shape/extent/window/keys를 확인하고 Draw Attack Collision checkbox로 green draw를 제어한다. (3) 정상 capsule Monster를 대상으로 실제 플레이해 범위·Cylinder 높이·첫 OverFury 타이밍과 피해량만 필요한 만큼 조정한다. (4) 결과를 현행 구현 정본 하단에 추가한다. 구 schema editor로 해당 DA를 저장하거나 이미 전달한 전체 asset/Source를 다시 덮어쓰지 않는다.
- 다른 Task가 module manifest나 Source를 새로 바꾸면 그 최신 구현을 보존하고 해당 task build를 사용한다. 과거 stock DLL로 되돌리거나 본 task alias를 무조건 재복사하지 않는다. 원작 source metadata·성공 fixture·author 작업을 근거 없이 반복하지 않는다.
'''
}
for relative,addition in changes.items():
    path=ROOT/relative
    assert path.is_file()
    assert addition.splitlines()[1] not in path.read_text(encoding='utf-8-sig'),'Do not append duplicate final record'
    with path.open('a',encoding='utf-8',newline='\n') as stream:stream.write('\n'+addition)
verification={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'VerifiedDelivered',
 'source_content_receipt_sha256':sha(OUT/'SourceContentDelivered.json'),'native_receipt_sha256':sha(OUT/'NativeAliasDelivered.json'),
 'saved_Main_readback_sha256':sha(OUT/'MainFreshSavedReadback.json'),'fresh_Main_pid':saved['pid'],
 'native_actual_load_log_verified':True,'data_counts':{'attack_nodes':18,'windows':60,'keys':553},
 'protected_files':146,'original_stock_binary_preserved':True,
 'runtime_product_files_added':0,'dev_fixture_added':True,
 'currently_running_Main_pid':31344,'current_Main_restart_required':True,
 'docs_appended':{p:sha(ROOT/p) for p in changes},
 'temporary_values_and_unverified_semantics':'See current implementation document; absolute damage10HP/5Stamina is temporary; no original damage formula claim',
 'optional_visual_helper':'Excluded Python API failure; no screenshot verification claim'}
(OUT/'FinalDeliveryVerification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
print('FINAL_DELIVERY_VERIFIED; dated Engineering records appended',len(changes))
