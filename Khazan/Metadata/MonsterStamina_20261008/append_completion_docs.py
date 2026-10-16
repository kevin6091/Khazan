import json, pathlib
MAIN = pathlib.Path(__file__).resolve().parents[2]
OUT = MAIN/'Metadata/MonsterStamina_20261008'
assert json.loads((OUT/'FinalVerification.json').read_text(encoding='utf-8'))['complete']
marker = '<!-- MonsterStaminaMainComplete_20261008 -->'
common = '\n\n'+marker+'\n## 2026-10-08 17:29 KST — 몬스터 소진·브루탈 어택 Main 완료\n\n'
sections = {
'0_DOCUMENT_ROUTER.md': '''이번 기능은 Mixed 완료다. 현재 구현은 Architecture ARCH-82의 최신 완료 절 → Migration → [소진·브루탈 정본](Docs/Engineering/MONSTER_STAMINA_EXHAUSTION_20261008.md)을 읽는다. 원작 값·Fortitude/Stamina 차이·클립 매핑은 [Art 감사](Docs/Art/MONSTER_STAMINA_ORIGINAL_AUDIT_20261008.md)와 기존 표적 metadata를 재사용한다. Main 전달105파일/stock build/453 native checks/회귀5종/새 Main saved readback이 완료됐고, 이전 Work-only·파일 잠금 대기 상태를 현행으로 사용하지 않는다. NPC4 추적 회전·Combat BS4의 대기 변경도 최신 Source와 함께 Main에 반영됐다. 상세 검증 범위와 미구현 실제 패링 생산자는 정본을 따른다. 전체 재추출·retime·authoring·과거 alias 재전달은 하지 않는다.
''',
'Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md': '''ARCH-82를 실제 Main에 적용했다. 기존 ASC/AttributeSet/CharacterDefinition/Instant damage GE/몽타주 Task/Locomotion handle/StateTree를 재사용하고, 별도 수명인 Exhaustion과 BrutalAttack Ability 두 클래스(새 runtime4파일)만 추가했다. State.Exhausted/State.Dead의 공유 상태는 ASC가 소유하며 Ability의 내부 phase/completion은 자기 실행 순서다. HP/Stamina 결과는 다음 tick에 묶어 death 우선으로 소비한다. 플레이어·피해자 양쪽 실제 Task 완료가 모인 뒤 생존자의 End 완료에서 현재 MaxStamina를 한 번 설정한다.

AI의 bPausedForCombatReaction은 게임 상태 사본이 아니라 이 반응이 StateTree Pause를 취득했는지 나타내는 cleanup 소유권이다. 다른 이유로 멈춘 Tree를 임의 Resume하지 않으며 target 기억을 유지한다. pending ARCH-80의 추가 회전은 실제 active Monster Attack과 일치할 때만 CMC에 적용하고 소진 제약 중 제외한다. 기존 ComboAction의 충돌/사용자 Jump·Down/입력 계약을 보존했다. 개발용 최초 Sight 격리·Heal observer 보완의 과거 Work 변경은 이번에 전체 파일로 덮어쓰지 않았다.

Main 선택 전달 runtime15/dev1/assets89, stock Build.cs 유지·임시 editor cpp3 제외, Work native453/0실패 및 Facing/CombatPolicy/Guard/Heal/PlayerAttackCollision 회귀5종 Success, 새 Main 실제 DLL·저장 참조·BS4/CDO·dirty0 검증이 완료됐다. 정확 근거는 Metadata/MonsterStamina_20261008/FinalVerification.json이며 물리적 패링 생산자·별도 cinematic Execution·Apes/Yetuga 자율 AI는 후속 범위다.
''',
'Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md': '''ARCH-82는 Main 실제 적용 완료다. 이전 15:52의 Work 초안 상태를 대체한다. shared ASC 상태/기존 피해 GE/실제 Task와 cause-owned 이동 제약을 사용한다. 신규 runtime class2/파일4 외 거대 상태 구조는 없다. pending ARCH-80의 NPC4 보간·추적 회전도 최신 Main Source에 추가 방식으로 병합했다. Source15/dev1/asset89 전달과 stock link, native453검사/회귀5종, 새 Main DLL·saved/CDO/dirty0를 확인했다. 상세 현재 수치·상태 수명·검증 한계는 MONSTER_STAMINA_EXHAUSTION_20261008.md 및 MONSTER_FACING_SMOOTHING_20261008.md 최신 절을 따른다.
''',
'Docs/Engineering/ENGINEERING_PROJECT_STATE.md': '''여섯 몬스터의 stamina 정책·0 소진·전후 Brutal pair·양쪽 정상 완료 후 생존 Max 회복을 Main에 적용했다. 패링 hook은 실제 GE 감소/소진까지 검증했고 실제 Monster→Player 적중·패링 생산자는 아직 없다. 일반 Guard 성공을 패링으로 취급하지 않는다. 편집값은 각 DA_Character_<family>의 Monster Stamina와 Player ComboDefinition의 Nodes → AttackWindows → StaminaDamage다. Parry5는 사용자값, BrutalHPDamage0은 미할당, ExhaustionSeconds5/8은 저장 원작 값의 기회 시간 채택이며 0이면 무기한이다.

pending NPC4 Motion도 최신 Source와 같이 반영했다. native453/0실패, 회귀 Facing/Policy/Guard/Heal/Collision5종 Success, stock link 및 Main fresh readback/CDO/BS4/dirty0가 완료됐다. FinalVerification.json이 최종 증거다. 선택105행 외 보호 Source/Config82·asset138package·기존 canonical DLL은 hash 동일하다. 실제 선택 DLL은 UnrealEditor-KhazanStamina20261008-70158bc21dbb.dll이며 이전 task alias를 무조건 복원하지 않는다. 현재 사용자 editor를 제어/저장/PIE/종료하지 않았고 마지막 inventory에는 열린 UnrealEditor.exe가 없다.

Apes/Yetuga는 기존 Art body를 사용하는 gameplay BP/ABP/registry가 추가됐지만 autonomous AI/StateTree/DevMap 배치는 추가하지 않았다. 정확한 사용법·미검증 범위는 소진 정본 최신 절을 읽는다.
''',
'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md': '''이번 요청의 Main 전달·검증은 완료다. 기존 다른 Task의 미완료 상태를 이 절로 취소하거나 완료 처리하지 않는다. 최종 evidence: Metadata/MonsterStamina_20261008/FinalVerification.json complete=true, NativePIE.json 453/0실패, IntegratedRegression.json 회귀5종 Success, StockDeliveryBuild.log Succeeded, DeliveryReceipt.json105행, MainSavedReload.json 실제 alias/CDO/BS4/dirty0. 새 Main readback PID16924는 commandlet 성공 exit0으로 종료했다. 사용자가 쓰던 editor는 조작하지 않았고 별도 Work30028/11040만 정상 quit했다.

최초 native 실패는 초기 intent fixture 문제, 최초 충돌 실패는 Work에 없는 최신 Main montage/sequence 참조 문제였다. NativePIE_FirstFailure와 첫 Regression log를 보존했다. 최신 Main 참조30개 중 누락10+stale3를 Work에만 가져온 LatestCollisionClipIntake.json 이후 충돌13case가 Success다. Main 기존 collision Source/DA/GE를 다시 author하거나 입력을 Python으로 주입하지 않았다.

다음 사용 절차: (1) Main 프로젝트를 정상 새 실행한다. (2) DA_Character_<family> → Monster Stamina에서 parry/timeout/BrutalHPDamage/range를 조절한다. (3) DA_Player_Combo_Definition → Nodes → AttackWindows에서 공격별 StaminaDamage를 설정한다. (4) 공격으로 0까지 소진시킨 뒤 가까이 앞/뒤에서 X로 Brutal을 실행한다. 생존 시 양쪽 완료와 End 후 Max 회복, 죽으면 회복 없음이 예상 결과다. BrutalHPDamage는 현재 미할당0이므로 원하는 피해값을 먼저 설정한다. 기회 시간을 무기한으로 원하는 경우 ExhaustionSeconds=0으로 바꾼다.

실제 패링 판정 생산자가 생기면 성공한 사건 한 번에 AKZMonster::ReportAttackParried(Defender)를 호출한다. 일반 Guard 성공에는 연결하지 않는다. Apes/Yetuga 시험은 해당 BP를 DevMap에 배치할 수 있으나 자율 AI는 후속 구현이다. 별도 lethal Execution 연출과 pose-contact 원작 동일성은 완료로 보지 않는다.

정확한 재검사: 격리 Work에서 Scripts/Engineering/MonsterStaminaPIEEditor.cpp만 Source/Khazan/Tests로 복사하고 Work Build.cs에 QA용 Json dependency를 임시 추가한 뒤 cold build한다. 전용 mailbox editor를 새 실행하고 그 Ready.json의 PID/project를 확인해 Automation RunTests Khazan.Monster.StaminaPIE와 native PIE를 실행한다. fixture의 실제 source SHA8ba086cd0e52a291d662e592435765fd65f291667ebf41b93d0df14a24e9efca를 확인한다. author cpp 두 개는 이미 적용된 에셋 재작성 용도이므로 테스트만을 위해 복사/실행하지 않는다. 테스트 후 임시 fixture/Build.cs 변경을 제거하고 stock build한다. 사용자 editor에 mailbox/test/compile/save-all을 보내지 않는다. 새로운 Source/manifest 변경이 있으면 최신 작업을 보존하고 과거 payload를 재전달하지 않는다.
''',
'Docs/Engineering/MONSTER_FACING_SMOOTHING_20261008.md': '''앞선 파일 잠금 대기 전달은 이번 MonsterStamina 통합으로 완료됐다. 과거 전체 후보 파일/Heal test를 덮어쓰지 않고 최신 Main의 NPC4/ComboAction에 필요한 추적 회전/const query와 Facing dev class만 추가했다. BS4도 최신 Main을 먼저 읽어 원작 TargetWeightInterpolationSpeedPerSec6/10/10/5 한 필드만 수정했다. MotionMerge.json과 LatestCombatBlendSpaceAuthoring.json이 병합·수치 근거다.

실제 attack 동안 FixedTurn 추가 steering60deg/s, 다음 combo 준비180deg/s와 .15s는 어시스턴트 임시 튜닝이며 원작 확인값이 아니다. root 회전을 삭제하지 않고 CMC bAllowPhysicsRotationDuringAnimRootMotion=true로 bounded 추가 steering을 함께 처리한다. 소진 중에는 공격 steering을 제외하고 AI는 자기 reaction Pause 소유권만 Resume한다.

최신 통합 tested Source에서 FacingPIE35공격/55node와 CombatPolicy/Guard/Heal/Collision이 모두 Success다. 원본 Halberd root yaw540.002/180/180도 유지됐다. stock에서 temporary author/test3를 제외한 DLL을 Main 선택 manifest로 반영했고 별도 fresh Main16924가 BS4저장값·BP/ABP up-to-date·실제 CDO 설정·loaded module SHA·dirty0를 확인했다. 근거 Metadata/MonsterStamina_20261008/{IntegratedRegression,DeliveryReceipt,MainSavedReload,FinalVerification}.json이다.

과거 full Monster.PIE의32방향/contact 결과는 당시 Work proof이며 이 latest 통합에서 같은 full test를 다시 실행했다고 주장하지 않는다. 이번 전달의 test 파일은 기존 Main body를 유지하고 Facing class만 추가했으므로 이전 Sight 격리·Heal observer 보완 파일을 재전달하지 않는다. 최종 scope와 추적 회전 조건은 현재 Source를 기준으로 한다.
''',
'Docs/Art/ART_KNOWLEDGE_INDEX.md': '''원작 소진·브루탈 어택의 첫 조회점은 [MONSTER_STAMINA_ORIGINAL_AUDIT_20261008.md](MONSTER_STAMINA_ORIGINAL_AUDIT_20261008.md) 최신 절이다. Metadata/EnemyStaminaResearch_20261008의 TargetedFindings/StatusAndHoldingSupplement/TargetedOriginal01–04와 Metadata/MonsterStamina_20261008/AnimationPlan.json을 재사용한다. cooked CS/AP/SI/SB/SD의 package/field/raw/hash와 공식 공개 자료를 구분했다. native 양쪽 완료 후 exact Max sequence를 직접 복원했다고 표현하지 않는다.

기존 보정 clip49를 InGame용으로 복제했고 bone payload/재생률/root옵션은 author audit에서 보존했다. Skeleton2에는 필요한 DefaultSlot만 등록하고 reference bone 이름/parent/pose를 보존했다. Yetuga New Composite의 GroggyStand와 old GroggyStr/PartGroggy, Apes variant01과 skill25 variant02를 섞지 않는다. Main 전달·새 saved readback은 완료이며 runtime 동작은 Engineering 정본을 읽는다. 전체 추출/retime/root repair를 반복하지 않는다.
''',
'Docs/Art/ART_PROJECT_STATE.md': '''원작 소진·브루탈 AP/SI/SB/SD/CS 표적 감사와 현재 재사용 클립 authoring을 완료했다. Source/수치 해석은 MONSTER_STAMINA_ORIGINAL_AUDIT_20261008.md, 구현은 Engineering/MONSTER_STAMINA_EXHAUSTION_20261008.md로 분리한다. 선택 복제49sequence/20montage 및 최소 gameplay 연결이 Main에 반영됐고 fresh Main saved readback이 완료됐다. 두 Skeleton의 DefaultSlot 외 reference bone 변경은 없다. 기존 .01 Player/baked timing/root motion을 추가 배율로 보정하지 않았다.

이번 Art 범위는 저장 원작 포즈/클립 매핑·재사용 보존과 필요한 slot 등록이다. Apes/Yetuga는 기존 Art body·material·scale1을 재사용했고 원작 Apes .8 character scale/native bone modifier/원작 전체 접촉 포즈를 복원한 결과로 설명하지 않는다. autonomous AI나 별도 lethal cinematic Execution 완료가 아니다. 기존 다른 Art/VFX 작업의 진행 상태는 유지한다.
''',
'Docs/Art/ART_WORK_CONTINUITY.md': '''소진·브루탈 표적 분석/클립 선택 작업은 Main 적용·fresh saved reload까지 완료다. 다른 VFX task의 미완료 checkpoint와 별개다. 원본 분석 재개가 필요하면 MONSTER_STAMINA_ORIGINAL_AUDIT_20261008.md → 저장 TargetedFindings/StatusAndHoldingSupplement → AnimationPlan의 정확 package/field/hash 순으로 확인한다. 원작 natural recovery의 인간형 positive value와 강적 Fortitude 차이를 전체 동일 native 규칙으로 합치지 않는다.

재사용 author 증거는 Metadata/MonsterStamina_20261008/Authoring.json의47clip raw bone/rate/root/keys 비교와 skeleton2reference preservation, BodiesAuthoring.json idle2/기존 body audit, MainSavedReload.json 저장49clip/20montage다. 클립 retime/root repair/전체 재추출을 반복하지 않는다. 실제 접촉 pose·원작 scale modifier·cinematic Execution가 후속 Art 범위이며 조정 전 기존 payload와 metadata 근거를 보존한다.
''',
'Docs/Art/MONSTER_STAMINA_ORIGINAL_AUDIT_20261008.md': '''선택 에셋의 Main 실제 반영과 새 프로세스 저장 재로드를 완료했다. 원본 감사/metadata 출처와 native 구현을 분리한다. Authoring47clip+body idle2의 기존 raw bone data/길이/rate/root flags를 보존했고20montage는 기존 보정 클립을 이어 사용한다. Player Front/Back의 notify 시간은 기존 원작 window→dilation→60fps 계산으로 authoring했으며 현재 Player .01에 추가 100배 보정을 하지 않았다. Skeleton2의 DefaultSlot만 추가하고 reference bone 이름/parent/pose를 그대로 유지했다.

새 Main actual module16924에서49copies/20montages/6monsterDefs+Player/35cost-free attack BP/2body의 saved reference를 확인했고 dirty0였다. 이것은 원작 native stamina recovery 순서 또는 시각 접촉의 정확 재현을 증명하는 것이 아니다. 원작의 positive human recovery와 Fortitude 정책 차이, separate Execution asset 경로, Yetuga GroggyStand/New와 old GroggyStr/PartGroggy 차이는 앞선 분석 그대로 유지한다. 정확 원본과 구현/사용자 수치 구분은 각 표적 report 및 Engineering 정본으로 연결한다.
'''
}
for relative, body in sections.items():
    path = MAIN/relative
    assert path.is_file()
    existing = path.read_text(encoding='utf-8')
    assert marker not in existing, relative
    with path.open('a',encoding='utf-8',newline='') as stream: stream.write(common+body)
print('Appended completion sections:',len(sections))
