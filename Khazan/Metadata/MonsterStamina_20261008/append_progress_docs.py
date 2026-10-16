from pathlib import Path

root = Path(__file__).resolve().parents[2]
marker = '## 2026-10-08 15:52 KST — MonsterStamina 작업 중 및 이전 stats 기록 가독성 보충'
stats = '''
기존 15:00 KST 몬스터 초기 수치 기록의 일부 한국어가 작성 과정에서 물음표로 손실되어 이 절에 가독성 있는 사실을 추가한다. 이전 기록은 삭제하지 않는다. 몬스터6의 GE_Init/CharacterDefinition 12개는 이미 Main 적용과 fresh saved readback을 완료했다. 값은 Swordsman/SwordShield HP100·Stamina50, HeavySwordsman/HalberdElite HP200·Stamina50, Apes HP400·Stamina100, Yetuga HP1000·Stamina150이고 모두 current=max이다. 근거는 Metadata/MonsterStats_20261008/FinalVerification.json complete=true 및 WorkSavedReload/MainSavedReload.json이다. 그 작업은 설정만 한 것으로 소진/회복/피격 기능 완료와 구분한다. Player 초기 GE2와 당시 Source/Config를 보존했다. Apes/Yetuga 당시에는 Definition/GE만 있고 gameplay BP/registry 연결은 없었다.
'''
progress = '''
새 사용자 요청은 여섯 몬스터 공통 무자동회복·무공격Cost, 편집 가능한 피격/패링 감소량, 스태미너0 소진, 브루탈 어택의 양쪽 정상 완료 후 생존 MaxStamina 회복이다. 상세 계약과 수치 출처/미확인은 Docs/Engineering/MONSTER_STAMINA_EXHAUSTION_20261008.md를 따른다. 현재 native 구현은 별도 Khazan_MonsterWork_20261006/Khazan에만 있으며 Main 게임 Source/에셋 미전달이다. 첫 빌드는 다른 editor의 전역 LiveCoding mutex로 거부되어 독립 Work 출력에 NoHotReloadFromIDE로 재시도 중이다. 실제 성공 전 build/PIE 완료로 쓰지 않는다.
'''
sections = {
    '0_DOCUMENT_ROUTER.md': stats + '\n이번 요청은 Engineering 구현과 원작 metadata 분석이 결합된 Mixed다. Router→Architecture 최신 ARCH-82 계약→Migration→MONSTER_STAMINA_EXHAUSTION_20261008.md/표적 evidence→현재 Source 순서다. Art 원작 숫자·클립 매핑은 해당 Art 감사와 Metadata/EnemyStaminaResearch_20261008을 사용한다.\n',
    'Docs/Engineering/MONSTER_AI_IMPLEMENTATION_20261006.md': stats + progress,
    'Docs/Engineering/ENGINEERING_PROJECT_STATE.md': stats + progress,
    'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md': stats + progress + '''
현재 소유: root는 Work CharacterDefinition·Tags·Action·ASC·Monster·AIController 및 BrutalAbility를, yetuga_public_patterns는 ExhaustionAbility와 새 native PIE test 하나를, apes_public_patterns는 Main Scripts/Engineering의 scoped author helper를 담당한다. 원작 조사 결과19packages/CS6/AP6는 저장 evidence를 재사용한다. 새 전체 Content 조사/재추출/재임포트는 하지 않는다.

정확 재개: NativeInitialBuild_NoHotReload.log 결과 확인→선택 author helper를 Work 임시 Editor deps/include로 컴파일→Work 자기PID/project/mailbox만으로 작성→새 프로세스 저장 재로드→native Stamina PIE 실제 피해·패링hook·소진·paired 완료/취소/죽음 테스트→Editor helper/deps 제거 후 stock build→최신 Main Source/asset CAS 및 외부 Combo 피해 작업과 교차 병합→선택 전달→별도 자기 Main 검증·정상 quit→완료 기록. 현재 Main user PID31344와 외부 Combo26104/AttackVFX9424는 비소유이며 조작/종료하지 않는다. PID는 재개 시 새로 조회한다.

이전 NPC4 Facing/보간 Main 전달도 미완료다. 최신 Main Source intake가 필요해 WorkBefore에 이전 Work Source/Config/DLL/PDB를 보존한 뒤 현행 Main93 Source/Config를 Work에 복사했다. MainSourceBefore.json과 WorkBefore.json이 정확한 시작점이다. 예전 Motion DLL a6bed... 및 VerifiedDeliveryProof는 현행 전체 Source와 달라 그대로 전달하면 안 된다. 이번 초기 stats의12asset을 반복 authoring하지 않는다. 원래 별도 Facing 재병합·검증 의무는 보존하며 이번 스태미너 완료와 혼동하지 않는다.
''',
    'Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md': '''
이번 ARCH-82는 기존 ASC/AttributeSet/CharacterDefinition·Instant 피해 GE·MontageTask·Locomotion constraint·StateTree를 재사용한다. AKZMonster가 attribute 결과를 coalesce해 death/exhaustion을 선택한다. 공유 상태는 ASC State.Exhausted/State.Dead이며 내부 montage phase는 Ability 실행 상태로 한정한다. 다른 Actor/AI/AnimInstance에 독립 exhaustion bool을 중복 저장하지 않는다.

추가 runtime 클래스2는 몬스터 Exhaustion(피격·timer·회복)과 Player BrutalAttack(입력·타깃·notify)의 서로 다른 실행 수명 때문에 필요하다. 새 manager/component/FSM/shared helper는 없다. 피격량은 ARCH-81의 기존 window·damage GE가 소유하고 이번 구현은 수치 결과를 소비한다. 두 작업의 ComboAction Source/data 소유권을 섞지 않는다. 패링은 성공 결과 생산자의 ReportAttackParried hook이며 정상 Guard 성공을 패링으로 대체하지 않는다.

각 Ability가 자기 task/timer/notify/constraint handle을 정상·실패·취소·UnPossessed·EndPlay에서 정리한다. 양쪽 정상 완료와 생존 검사가 있어야 현재 MaxStamina 충전하며 OnEndEffect/NotifyEnd 하나에 회복을 맡기지 않는다. 정책 숫자/타이밍/입력 제안과 원작 직접 확인은 MONSTER_STAMINA_EXHAUSTION_20261008.md로 구분한다. 현재 Work 구현 진행 중이며 Main·PIE 완료를 뜻하지 않는다.
''',
    'Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md': '''
ARCH-82는 기존 현재 GAS 기반 초기화·피해 결과 소비 경로의 작은 확장이다. CharacterDefinition monster-only 설정, Exhaustion/Brutal 실행 Ability2, ASC tags와 기존 AI Pause/Resume를 사용한다. 몬스터 스태미너는 사용자 정책으로 Player Cost/regen과 분리한다. 입력 X는 기존 grant 동적 tag 우선 시도로 연결하고 타깃 없으면 일반 X 경로를 보존한다. 현재 Work 초안/빌드 진행 상태이고 Main 단계 완료로 기록하지 않는다. 상세 수치/원작 차이/테스트·재개는 해당 Stamina 문서와 Continuity 최신 절을 따른다.
'''
}
for relative, body in sections.items():
    path = root / relative
    text = path.read_text(encoding='utf-8-sig')
    if marker not in text:
        with path.open('a', encoding='utf-8', newline='\n') as stream:
            stream.write('\n\n' + marker + '\n\n' + body)
        print(relative)
