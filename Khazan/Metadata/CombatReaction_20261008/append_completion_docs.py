"""Append this task's verified result; never rewrite historical records."""
from pathlib import Path
import json, datetime, hashlib

out = Path(__file__).resolve().parent
main = out.parents[1]
proof = json.loads((out/'FinalVerification.json').read_text(encoding='utf-8-sig'))
assert proof['success'] and proof['status'] == 'MainDeliveredAndFreshVerified'
marker = '<!-- CombatReactionMainComplete_20261010 -->'
documents = {
'Docs/Engineering/COMBAT_REACTION_RUNTIME_20261008.md': '''
## 2026-10-10 — ARCH-85 Main 반영·최종 검증 완료

이 작업의 이전 Work-only/회귀 조사/stock build·Main 전달 대기 상태를 아래 실제 완료 결과로 보충한다. runtime16개(공통 HitReaction 신규 h/cpp2개와 기존14개), 에셋130개를 Main에 선택 전달했다. 별도 피격 Manager/Component/FSM은 추가하지 않았다. 기존 Combo collision/GE/ASC event/AbilityTask/Locomotion constraint/CharacterDefinition 및 Exhaustion·Brutal 실행을 재사용한다. 최종 증거는 [FinalVerification.json](../../Metadata/CombatReaction_20261008/FinalVerification.json), 실제 변경은 [RuntimeChanges.patch](../../Metadata/CombatReaction_20261008/RuntimeChanges.patch), 사용·조정 설명은 [UserGuide](../../Metadata/CombatReaction_20261008/UserGuide_20261010.md)의 최신 완료 절이다.

일반 피격은 공격 window의 Short/Knockback/Launch를 받아 해당 종의 비어 있지 않은 후보에서 랜덤 재생한다. 방향은 입력 공격각으로 고르지 않으며 물리 이동 방향은 공격자에서 멀어지는 방향이다. 지원되는 날림은 반응→착지→Down Loop→Getup을 같은 몽타주 수명으로 완료한다. In-place 원본의 이동은 engine RootMotionSource가 소유하며 종료·취소·재피격·사망·소진·UnPossess에서 자기 이동/루트모션/회전 제약을 정리한다. Main7 Definition에 공통 피격 grant/pool과 조정 가능한 world cm 설정이 실제 저장됐다.

SwordShield는 발견 후 전방 passive guard와 authored active-node guard window를 구분한다. 방어 성공은 HP 피해를 막고 해당 공격 window의 StaminaDamage를 소비하며 0이면 소진이 우선한다. 원본 FrontAngle180의 full-cone 해석은 native 확인이 안 된 프로젝트 adapter다. Player Guard의 기존 Suc_F/L/R 랜덤을 그대로 사용했다. Player 일반 공격의 저장 HP10/Stamina5는 변경 전 에셋의 실제 값을 보존했다. Monster35 공격의 HP10/Stamina5·blockable=true, Knockback250cm/Launch120cm·높이150cm, Down Loop0.3초 및 Monster 종류109Short/2Knockback/2Launch의 네 날림 window 선택은 어시스턴트 임시 설정이며 원작 절대값으로 주장하지 않는다. 기존 Definition/window에서 조절한다.

브루탈은 게임패드 X/기존 약공격 입력의 기존 우선 요청 경로를 사용한다. 소진 대상 claim→점진 capsule sweep 정렬→앞/뒤 짝 공격과 피해 반응→Hit2의 HP50 1회→양쪽 실제 완료→생존 대상 End 완료에서 MaxStamina 회복 순서다. 50은 사용자 임시 결정이다. 원본 MoveTo trigger0.03356초/Duration0.433283초와 CubicInOut을 참고하며 목적 간격은 live capsule와 기존 설정을 사용한다. .01 메시 배율을 actor 이동/시간에 다시 적용하지 않았다. 대상 capsule에 막히던 문제는 Exhaustion의 full-pair 수명에서 필요한 reciprocal move-ignore만 추가해 해결했다. 사전 entry는 보존하고 자기 추가분만 복구한다. 벽은 계속 sweep을 막고 짝 취소/cleanup이 실행된다.

실제 RHI native 검사는 피격32·브루탈15·Monster→Player 충돌3case, 1,066 assertion, 변형26종 및 캡처7장을 통과했다. 앞/뒤6종·접근 취소·벽·치사·50 1회·양쪽 완료·회복·사전 one-way ignore 보존·일반 반응 재진입·실제 이동/CMC 복구·Shield/Guard 경계를 검사했다. 새 PID23912의 Guard/Heal/PlayerAttackCollision/CombatPolicy stock 회귀4개도 실제 engine Success이며 인간4종 완료를 확인했다. 과거 Heavy 정책 timeout은 fresh debug run과 undebugged run에서 재현되지 않았고 원래 원인은 미확인이다. 그 실패를 이유로 제품 AI를 임의 수정하지 않았다. 뒤늦은 GPU device-removed와 timeout의 인과도 확인하지 않았다. 실패와 디버거 로그는 보존했다.

임시 author2/test1은 SHA 확인 후 archive하고 Work Source에서 정확3개만 제거했다. Build.cs는 Main의 정확 bytes로 복원했다. stock build Succeeded(5.19초), Source/Config103개는 전용 PIE 당시와 임시3 제거/Build.cs 복원만 다르며 production16개는 동일하다. 최종 stock DLL SHA는 `74a069363f9100a4784ac03a4941214f0a98f732b4dc296d3f7198c7e62d2983`이다. 전체 RHI 결과는 동일 production source의 helper 포함 이전 DLL에서 수행했고, 최종 stock DLL에서는 fresh saved 검증을 수행한 범위로 구분한다.

fresh Work PID29152와 fresh Main PID16544에서 각각 654,552검사/실패0/필수 미지원0/dirty0를 확인했고 정상 종료했다. Main 실제 loaded module은 `UnrealEditor-KhazanReaction20261008-74a069363f91.dll`, BuildId55116800이며 Main canonical DLL은 보존했다. 선택146행과 Main/Work bytes, Source/Config103개, 보호 baseline652개·dependency268개를 확인했다. 사용자/다른 task 에디터를 저장·PIE·종료·reload하지 않았다.

지원 한계는 유지한다. Heavy에는 대응 source Air chain이 없어 Launch가 Short로 fallback한다. Apes/Yetuga의 NoAirDamage/NoBlowDamage는 면역 bool이 아닌 전용 Damage_Grapple_Atk_02 애니메이션 fallback 참조로 사용한다. QuickStand4개는 정리했지만 현재 chain에 연결하지 않았다. 원본 미지원 shape11 occurrence는 임의 Box를 만들지 않고 제외했다. 원작 전체 pose/contact·pixel 완전 일치, 멀티플레이, Player 별도 사망 시스템·실제 패링 생산자는 이 완료 범위가 아니다. 조정은 기존 Definition/ComboDefinition에서 수행하고 과거 author/import/retime/delivery를 반복하지 않는다.
''',
'Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md': '''
## 2026-10-10 — ARCH-85 피격·SystemGuard·브루탈 최소 확장 Main 완료

ARCH-85 계약을 Main에 실제 적용했다. 신규 runtime class는 공통 UKZHitReactionAbility1개/h·cpp2개이며 기존14개 파일의 작은 확장으로 총16개다. ASC 태그/event와 기존 AbilityTask/GE/Locomotion 제약을 공유하고, 피해 확정은 Combo collision/Effect가, 실행·취소는 HitReaction/Brutal/Exhaustion이 소유한다. 별도 상태 사본·Manager·FSM을 만들지 않았다. 짝 capsule ignore는 기존 Exhaustion full-pair 수명에서 자기 추가분만 소유하고 복구한다. world wall 충돌·50 1회·양쪽 완료를 보존한다.

Main146행 전달·stock build·RHI32/15/3·stock 회귀4개·fresh Work/Main 각각654,552 saved checks가 성공했다. 현행·수치 출처·지원 fallback·검증 한계는 [피격 runtime 정본](COMBAT_REACTION_RUNTIME_20261008.md)의 2026-10-10 완료 절과 [최종 증거](../../Metadata/CombatReaction_20261008/FinalVerification.json)를 따른다. 기존 ARCH-84 MonsterVFX는 별도 작업이고 그 완료를 이번 결과로 주장하지 않는다. 후속 shared Source/Definition 변경은 새 Main alias/source/asset SHA를 받아 병합·검증해야 하며, 이전 Work baseline이나 old pending delivery를 다시 적용하지 않는다.
''',
'Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md': '''
## 2026-10-10 — ARCH-85 공통 피격·브루탈 짝 반응 실제 완료

현재 공통 ASC/Ability/Task/태그/GE/CharacterDefinition/Locomotion 경계를 재사용해 Player+Monster6 피격 pool, SystemGuard, 기존 Brutal의 swept 접근·짝 충돌 정리를 Main에 적용했다. 신규 계층·Manager·CharacterStateMachine은 없으며 신규 runtime class1개다. 일반 반응과 몬스터 소진/사망·브루탈 우선순위, 완료·취소·재진입 cleanup을 검증했다. 현재 결과는 [runtime 정본](COMBAT_REACTION_RUNTIME_20261008.md)의 Main 완료 절과 [FinalVerification](../../Metadata/CombatReaction_20261008/FinalVerification.json)이다.

stock build·RHI32reaction/15pair/3collision·기존 회귀4종·fresh Work/Main 저장 검사는 실제 성공이다. 전체 M단계·원작 피해 수치·실제 패링 producer·Player 사망 기능 완료로 확대하지 않는다. 이전 Work-only/정책 timeout 조사 pending은 이번 기능에 한해 해소됐다.
''',
'Docs/Engineering/ENGINEERING_PROJECT_STATE.md': '''
## 2026-10-10 — 일반 피격·Shield 방어·브루탈 Main 완료

Main에 runtime16개와 에셋130개를 실제 전달했다. Player/Monster6의 종류별 랜덤 피격·지원하는 쓰러짐/기상, SwordShield 전방/노드 방어, 기존 Guard 랜덤, 브루탈 접근·짝 피해 모션·사용자 HP50·양쪽 완료 후 생존 스태미나 회복을 연결했다. 신규 class1개이며 기존 구조를 재사용했다. 임시 helper3은 제품 Source에 없고 Build.cs/Config를 보존했다.

stock build와 RHI32/15/3·회귀4종·fresh Main654,552검사/실패0/dirty0 완료다. 현재 Main 선택 모듈은 `UnrealEditor-KhazanReaction20261008-74a069363f91.dll`이며 canonical은 보존했다. [정본](COMBAT_REACTION_RUNTIME_20261008.md), [사용/조정 설명](../../Metadata/CombatReaction_20261008/UserGuide_20261010.md), [최종 증거](../../Metadata/CombatReaction_20261008/FinalVerification.json)를 따른다. Heavy Launch·Giant 전용 fallback과 임시 world 이동/Monster 피해값의 출처를 원작 완전 복원으로 해석하지 않는다. 별도 VFX 작업의 완료 상태는 그 작업 문서를 따른다.
''',
'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md': '''
## 2026-10-10 — ARCH-85 정확 재개 작업 완료·재실행 금지 범위

중단 지점은 전용 native RHI 통과 후 Heavy CombatPolicy timeout 조사였다. 새 owned PID23912에서 debugger 실제 상태를 확인했으며 debug/undebugged 두 정책 실행은 인간4종까지 Success였다. 이후 stock Guard/Heal/PlayerAttackCollision/CombatPolicy4종 모두 통과했다. 원래 실패 원인은 미확인이고 제품 AI 변경은 없었다. 이전 실패/GPU crash/debugger 증거는 보존했다. 사용자 breakpoint8개는 유지하고 agent breakpoint3개 제거/detach·owned23912 정상 종료했다.

archive SHA 확인→임시 helper3 정확 제거→Build.cs exact Main 복원→stock build Succeeded→TestedSource103→fresh Work29152 저장 검사 성공/종료→Main baseline709/공유 asset CAS→runtime16+asset130=146 선택 전달→fresh Main16544 actual stock alias+654,552검사 성공/dirty0/종료→FinalVerification 성공까지 완료했다. 사용자/다른 작업 editor는 제어하지 않았다. 현재 [FinalVerification](../../Metadata/CombatReaction_20261008/FinalVerification.json)의 MainDeliveredAndFreshVerified를 읽는다. 기존 pending/PreparedDelivery는 과거 단계의 receipt이며 전체 author/import/retime/prepare/publish를 다시 실행하지 않는다.

후속 작업은 Router→Architecture ARCH-85 최신 완료→Migration→runtime 정본/UserGuide→최신 실제 Main Source/Definition 순으로 시작한다. 조정 가능한 pool/거리·높이/BrutalAlignmentSeconds/BrutalHPDamage/공격 window 수치는 기존 데이터에서 변경한다. 이후 다른 chat가 shared Source/Definition이나 모듈을 전달한 경우 이 alias로 임의 되돌리지 말고 새 current module/source SHA를 확인한다. 남은 미검증은 원작 full contact/pixel fidelity·멀티플레이·실제 패링 producer·별도 Player 사망, Heavy matching Air 및 제외 shape의 원본 geometry 확보다. 이는 이번 승인 범위의 미완료 전달이 아니다.
''',
'Docs/Art/COMBAT_REACTION_ANIMATION_AUDIT_20261008.md': '''
## 2026-10-10 — 분류·파생 몽타주 Main 저장본 검증 완료

이번 source/pose 정리의 Main 전달과 재로드가 완료됐다. 기존 Authoring_Final의97개와 CollisionAuthoring_Final의36 Definition의 공유3개를 제외한 합집합130개를 전달했다. source245 및 Player InGame 복제24의 실제 raw key/time/value/default와 재생률/root 계약을 fresh Work29152/Main16544에서 읽기 검증했다. 양쪽 각각654,552검사/실패0/필수 미지원0/dirty0, unique montage63/계획65·trimmed Loop16·Definition7·Guard3/window9·collision36/Monster113window/1498key·Player60window를 확인했다. 정확 증거는 [MainSavedReload](../../Metadata/CombatReaction_20261008/MainSavedReload.json), [WorkSavedReload](../../Metadata/CombatReaction_20261008/WorkSavedReload.json), [FinalVerification](../../Metadata/CombatReaction_20261008/FinalVerification.json)다.

다운 Loop16의0.3초 crop은 source 원본 길이·raw/rate를 바꾸지 않는 어시스턴트 임시 prone hold다. Player `.01` 공간 배율은 재생 시간이나 world displacement에 다시 적용하지 않았다. source root는 읽기 감사만 했고 child Root/Bip001 전사·재임포트·root track 수리는 하지 않았다. QuickStand4 후보는 InGame 정리만 했고 chain에 아직 연결하지 않았다.

Heavy matching Air가 없어 Short fallback, Apes/Yetuga는 원본 NoAir/NoBlow의 Damage_Grapple_Atk_02 전용 참조를 사용한다. 이를 면역 bool 또는 human air/down full chain으로 해석하지 않는다. Box source 합성100개/오차 최대0.0000821624cm는 원본 기반 계산 결과이고 Monster113 occurrence/1498key 저장과 실제3 collision contact는 별도 실행 근거다. unsupported11 occurrence는 추정 shape를 만들지 않고 제외했다. Player 기존18노드/60window HP10/Stamina5·geometry/time를 보존하고 반응 kind만 추가했다. Monster HP10/Stamina5·Blockable=true와 네 날림 window의 임시 선택은 원작 absolute 수치/면역 플래그가 아니다.

RHI32피격/15브루탈/3충돌와7PNG는 같은 production source의 Work에서 실제 수행했고 종료 후 임시 helpers를 제외한 stock DLL은 fresh Work/Main 저장 검증을 통과했다. 제한된 캡처/런타임 성공을 원작 전체 pixel/contact 동등성으로 확대하지 않는다. 원본 source 조사·Player retime·author/delivery를 반복하지 않는다. 조정·취소 책임은 [Engineering runtime 정본](../Engineering/COMBAT_REACTION_RUNTIME_20261008.md)의 최신 완료 절을 읽는다.
''',
'Docs/Art/ART_PROJECT_STATE.md': '''
## 2026-10-10 — CombatReaction 분류·InGame 파생 에셋 Main 완료

Player/몬스터6의 Short/Knockback/Launch·기상·방패 반응을 저장 pool과 몽타주로 정리해 Main에 반영했다. unique63 montage와 Player InGame24 clip의 원본 raw/재생률/root 계약, source245·Loop crop16·Definition7을 fresh Main에서 검증했다. Source root repair/재임포트/재리타이밍은 없었다. [Art 감사 정본](COMBAT_REACTION_ANIMATION_AUDIT_20261008.md)의 2026-10-10 완료 절, [최종 증거](../../Metadata/CombatReaction_20261008/FinalVerification.json), [사용 설명](../../Metadata/CombatReaction_20261008/UserGuide_20261010.md)을 따른다.

Main 에셋130 합집합·fresh654,552 readback/dirty0 완료다. Heavy Launch/Apes·Yetuga 전용 fallback, QuickStand 미연결, unsupported shape11 및 임시 Loop hold/거리·피해량은 원작 완전 재현과 구분한다. 실제 runtime/입력·회복은 Engineering 정본에 기록했다. 별도 MonsterVFX/PlayerVFX polish의 진행 상태는 해당 문서로 판단한다.
''',
'Docs/Art/ART_KNOWLEDGE_INDEX.md': '''
## 2026-10-10 — CombatReaction 현재 Main 정본과 재사용 증거

이 기능의 이전 “author/save/PIE 미확인” 상태는 [COMBAT_REACTION_ANIMATION_AUDIT_20261008.md](COMBAT_REACTION_ANIMATION_AUDIT_20261008.md)의 완료 절과 `Metadata/CombatReaction_20261008/{Authoring_Final,CollisionAuthoring_Final,NativePIE_Final,IntegratedRegression,WorkSavedReload,MainSavedReload,FinalVerification}.json`이 보충한다. Main146행(16Source/130asset)·원본245/raw 동일 Player24/63montage·16Loop crop·113Monster/60Player collision windows·fresh654,552checks가 실제 근거다. `Screenshots/*.png`7장과 RuntimeChanges.patch/UserGuide를 재사용한다.

AnimationClassification·ReactionAuthoringPlan·MonsterAttackCollisionPlan·Root audit의 원본 field/직접값/계산식과 임시 프로젝트 선택은 유지한다. Heavy Air/giant fallback/미지원11shape를 전체 원본 지원으로 바꾸지 않는다. `.01` 시간 배율 재적용이나 전체 metadata/retime/root repair/author/delivery를 다시 실행하지 않는다.
''',
'Docs/Art/ART_WORK_CONTINUITY.md': '''
## 2026-10-10 — CombatReaction Main 완료 후 Art 재개 기준

기존 중단 작업을 완료했다. 이미 저장된 plan/report만 사용해 runtime 검증·stock build·Main130 asset 선택 전달·새 Main saved readback을 수행했고 원본 재추출/재임포트/retime/root repair를 하지 않았다. [FinalVerification](../../Metadata/CombatReaction_20261008/FinalVerification.json)은 MainDeliveredAndFreshVerified이며 새 Work29152/Main16544 각각654,552검사/실패0/필수 미지원0/dirty0·정상 종료가 기록돼 있다. 사용자/별도 작업 editor를 제어하지 않았다.

다음 조회는 Router→Art state→[피격 Art 감사](COMBAT_REACTION_ANIMATION_AUDIT_20261008.md)의 완료 절→저장 분류/plan/readback→필요한 정확 source asset 순이다. author/helper/prepare/publish를 반복하지 않는다. 원본245/raw24/재생률/root 보존, Loop crop16 임시0.3초, Heavy Short fallback/giant dedicated fallback, QuickStand4 미연결 및 unsupported11 occurrence를 현재 계약으로 읽는다. 추가 수정은 새 현재 Main baseline을 확인한 뒤 표적 자산만 다루며 runtime 계약은 Engineering ARCH-85를 따른다. 별도 MonsterVFX 진행은 그 continuity 절의 상태를 유지한다.
''',
'0_DOCUMENT_ROUTER.md': '''
## 2026-10-10 — 공통 피격·Shield 방어·브루탈 접근 Main 완료 조회점

이 요청은 Mixed다. Architecture 최신 ARCH-85 완료→Migration→[CombatReaction runtime 정본](Docs/Engineering/COMBAT_REACTION_RUNTIME_20261008.md)의 완료 절→[사용·조정 설명](Metadata/CombatReaction_20261008/UserGuide_20261010.md)→실제 Main Source/Definition을 읽는다. 원본 분류·클립/raw/root·공격 형상은 [Art 감사](Docs/Art/COMBAT_REACTION_ANIMATION_AUDIT_20261008.md)와 기존 표적 plan을 재사용한다.

Main146행(16runtime/130asset)·stock build·RHI32피격/15브루탈/3충돌·회귀4종·fresh Work/Main654,552checks는 [FinalVerification](Metadata/CombatReaction_20261008/FinalVerification.json)으로 완료 확인됐다. 이전 Work-only/정책 timeout 조사/전달 pending을 현재 상태로 설명하지 않는다. 현재 모듈은 `UnrealEditor-KhazanReaction20261008-74a069363f91.dll`이며 canonical은 보존했다. Heavy Launch/Apes·Yetuga fallback·unsupported shape11 및 임시 수치의 출처는 각 정본을 따른다. 별도 MonsterVFX의 ARCH-84와 구분하고, 다른 후속 Main delivery가 있으면 새 current manifest/Source를 먼저 확인한다. 완료된 전체 author/metadata 추출/retime/delivery를 반복하지 않는다.
'''
}
for relative in documents:
    path = main / relative
    assert path.is_file() and marker not in path.read_text(encoding='utf-8-sig'), relative
rows = []
for relative, body in documents.items():
    path = main / relative
    content = ('\n\n' + marker + '\n' + body.strip() + '\n').encode('utf-8')
    with path.open('ab') as stream:
        stream.write(content)
    rows.append(dict(relative=relative, sha256_after=hashlib.sha256(path.read_bytes()).hexdigest()))
receipt = out / 'DocCompletionAppended_20261010.json'
assert not receipt.exists()
receipt.write_text(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                  append_only=True, documents=rows), ensure_ascii=False, indent=2), encoding='utf-8')
print('Appended completed result to', len(rows), 'documents')
