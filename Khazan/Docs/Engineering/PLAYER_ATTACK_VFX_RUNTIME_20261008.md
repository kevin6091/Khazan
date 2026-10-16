# 2026-10-08 — Player 공격 VFX 실행 계약

## 현재 구조를 재사용하는 변경

기존 UKZComboActionAbility의 단일 PlayMontageAndWait와 OnPlayMontageNotifyBegin 경로를 재사용한다. 추가 runtime 파일은 data-only UKZAnimNotify_CombatEffect h/cpp 두 개다. 몽타주의 source event occurrence마다 동일 EventId인 시작·종료 marker를 저장한다. notify asset에 Pawn이나 실행 상태를 저장하지 않는다. Ability activation이 실제 MontageInstanceID와 avatar에 속하는 weak particle/decal resource record 및 GAS delegate handle을 소유한다. 새 VFX manager, 전역 상태 사본, Input/AnimInstance 변경은 없다.

local combo jump 전과 EndAbility에서 현재 실행 자원과 delegate를 정리한다. 정상·취소·실패·사망 cleanup을 기존 Ability 수명으로 처리한다. 원본 end destroy/deactivate/detach flags와 자연 종료를 구분한다. 혈흔 decal은 engine lifespan과 material age가 잔여 표시 수명을 소유한다. 타 Pawn, stale montage instance, 종료한 activation에는 기존 effect를 다시 적용하지 않는다.

적중 조건은 현재 공격 충돌의 SourceASC.ApplyGameplayEffectSpecToTarget 성공 callback을 소비한다. SourceObject가 현재 executing Ability이며 KZAttackHPDamage가 음수인 spec만 선택한다. animation notify를 지나기만 했다고 적중으로 취급하지 않는다. HP/Stamina damage 자체를 이번 이펙트 코드에서 다시 계산하거나 적용하지 않는다. 저프레임 원본 hit key sampling과 VFX window 대응은 실제 sampled montage time/instance를 전달하는 작은 현재 producer 확장으로 검증한다.

원본 source offset/particle mesh의 centimetre 좌표에서 actual socket world transform의 mesh scale을 분리한다. 임의 .01 배율은 넣지 않는다. explicit Scale3D가 legacy scalar보다 우선한다. first correction snapshot inverse anchoring, only-start-attach와 winter-owner 조건은 명시된 project adapter이고 원작 native code 확인값이 아니다.

floor/surface 경로는 actual anchor XY를 trace하고 CMC grounded/walkable 및 기존 capsule/step/snow depth 범위를 사용한다. 기존 AKZSnowDeformation.GetSnowSurfaceHeight 읽기 API를 재사용해 현재 WPO snow 높이와 dent를 반영한다. 원본 PM_DeepSnow=SurfaceType13은 Art 확인값이며 현재 aggregate snow를13으로 선택하는 것은 deep/thin 분리가 없는 프로젝트 adapter다. 기존 Snow 구현/지형/충돌/맵을 다시 작성하지 않는다.

## 작업 환경과 검증 상태

본 작업은 별도 hidden `Khazan_AttackVFXWork_20261008/Khazan`에서 수행한다. 사용자 Main 에디터 PID31344는 초기 read-only 상태 확인 시 PIEfalse, dirty content/map0이었다. 저장·PIE·카메라·종료 조작을 하지 않는다. 다른 공격 충돌 작업의 private editor도 조작하지 않는다.

별도 공격 충돌 작업의 SourceContentDelivered는 Main에 실제 반영됐으며 `SourceIntake/MainIntake.json`으로 당시 89개 Source를 기록했다. 두 작업이 공유하는 ComboAction h/cpp는 baseline과 최신 Main을 기준으로 병합한다. 오래된 Work source를 Main 전체에 덮어쓰지 않는다. 살아 있는 에디터의 loaded DLL을 덮어쓰지 않고 새 module delivery를 별도 검증한다.

이 절 작성 시 native build/marker author/실제 공격 QA/Main delivery는 아직 완료되지 않았다. 개발 automation fixture의 transient EntryNodeId/HP GE는 제품의 입력·원작 피해량을 바꾸지 않는다. fixture와 자연 actual hit, data author와 render QA를 분리 기록한다. 원본 이벤트·에셋·시간 변환 상세는 `Docs/Art/PLAYER_ATTACK_VFX_PLAYBACK_20261008.md`와 Main Saved/ImportReports를 따른다.

## 2026-10-08 추가 — 실제 producer provenance와 private build

공유 producer `QueryAttackCollision`는 기존 실제 HP/Stamina damage Spec에 sampled absolute montage time/actual montage instance/current AttackExecution을 `KZAttackMontageTime`/`KZAttackMontageInstance`/`KZAttackExecution`으로 추가한다. effect consumer는 source Ability·avatar·ASC·현재 node/instance/execution과 HP 음수 값을 함께 확인한다. 적중이 조건부 notify보다 앞선 경우 현재 node/execution의 실제 적중 관측을 보존해 뒤의 알림을 처리하고 EventId 중복을 방지한다. animation-only 또는 timestamp 없는 임의 HP spec은 혈흔을 재생하지 않는다. 원작 BattleEffectIndex/super-armour의 native 판정과 동일하다고 표현하지 않는다.

natural montage 완료 직전 엔진이 instance를 제거하는 경우 마지막 collision flush 동안만 scoped cached instance를 허용한다. 취소 이후의 재생 권한으로 확장하지 않는다. slow-frame에서 이미 End marker를 지난 실제 적중의 looping effect를 복원하면 authored window 길이만큼 emission timer를 소유하며, source destroy/deactivate 정책으로 종료한다. 종료 시 timer/delegate/weak resource cleanup은 기존 Ability 실행 수명에서 처리한다.

private native build는 첫 C4458 변수 shadowing을 수정한 뒤 증분 빌드 Result:Succeeded/exit0, 44.687초를 확인했다(`Build/PrivateBuild.log`, `Build/Exit.json`). `NativeBuildCandidateProof.json`은 당시 Main Source89개가 intake와 동일하며, private 변경이 runtime6개+development test1개로 제한됐음을 확인한다. 몽타주 author도 별도 nullRHI Cmd에서6개 저장을 완료했다. 제품 Main Source/Content는 이 추가 절 시점에는 아직 전달하지 않았다.

사용자가 별도로 에디터를 재시작해 현재 read-only 연결 PID는22560이다. 당시 DevMap/PIEfalse/dirty content0/dirty map0이며 normal UnrealEditor-Khazan.dll이 로드돼 있다. 이 작업은 사용자 프로세스를 재시작·PIE·저장하지 않았다. 새로운 notify schema는 구 모듈의 실행 중 에디터에 강제로 reload하지 않고, 검증된 native module을 고유 alias로 전달한 뒤 자체 fresh process에서 확인한다.

## 2026-10-08 18:36 KST — 최신 Main 소진·브루탈 의존성 intake와 통합 native 대기

후속 private RHI 실패에서 Main의 최신 shared CharacterDefinition은 native `/Script/Khazan.KZBrutalAttackAbility` 및 `/Script/Khazan.KZExhaustionAbility`를 부여하지만 private DLL/Source는 이전 상태였다. `RuntimePIE/PrivatePIE.log`의 Player `Input.Action.X`와 몬스터 `InitialAbilityGrant AbilityClass=None`, BrutalFront/Back package load 실패를 이 불일치로 확인했다. Main fresh saved readback `Metadata/MonsterStamina_20261008/MainSavedReload_ConcurrentBuild.json`은 실제 Player의 Brutal X grant와 몬스터6의 Exhaustion grant, 현재 canonical 모듈 및 저장 몽타주/클립 참조를 확인한다. grant를 지우거나 오류를 숨기지 않았다.

기존 intake 이후 Main Source 변경16개 중 ComboAction h/cpp 두 개만 VFX 소유 변경과 겹쳐 immutable old intake 기준으로 병합했다. 나머지14개 Source와 정확히 신규 `DAS/BrutalAttack` 몽타주2/시퀀스5를 private에 CAS로 가져왔다. `SourceIntakeHistory/20261008T092852045375Z/{Prepared,Applied}.json`과 `PreviousSourceIntake`에 이전 전체 intake·실제 before/after SHA·backup을 보존했다. 현재 `SourceIntake/MainIntake.json`은 Main 전체93 Source hash를 기록한다. Main Source/Content/Config 및 private Config는 변경하지 않았고, 기존 여섯 VFX 몽타주·리타이밍 시퀀스 bytes를 보존했다. 상세 증거는 `MetadataAudit/LatestMainSourceAndBrutalDependencyAudit.json`이다.

현재 브루탈은 실제 별도 `UKZActionAbility` 소비자이므로 기존 Combo VFX 실행 코드를 Action 소유 경계에서 최소 공유하는 private 후속 구현을 진행한다. 변경 범위는 기존 runtime10개와 개발 test1개이며 새로운 공통 manager/상태 사본은 추가하지 않는다. 앞선 Source89/7후보 DLL 성공은 당시 결과로 보존한다. 최신 Source93 및 브루탈 소비자를 합친 새로운 native build/자연 gameplay·실제 RHI 검증은 이 절 시점에 아직 대기 중이며, 저장본 Art 검사 통과를 runtime 통과로 표현하지 않는다. 현재 Source/모듈과 저장 Data를 같은 버전으로 검증한 뒤 Main 선택 전달을 진행한다. 브루탈 원본 시간·54구간/통합401구간·802child 저장본 결과는 Art 정본의 최신 추가 절을 따른다.

<!-- PlayerAttackVFXMainComplete_20261008_1911 -->
## 2026-10-08 19:11 KST — ARCH-83 Main 전달·실제 RHI·저장 재로드 완료

앞선 18:36의 통합 검증 대기 상태를 이 범위에서 대체한다. 최신 Main의 Stamina/Brutal·NPC 회전·사용자 공격 변경을 보존한 전체 Source로 private native build를 성공한 뒤, Main에 Source11개(runtime10개와 기존 development test1개), 몽타주8개, Art 재질·텍스처15개를 선택 전달했다. 총34파일/23패키지이며 전체 Main Source가 최신 빌드 snapshot과 일치한다. 고유 모듈은 `UnrealEditor-KhazanPlayerAttackVFX20261008.dll`, SHA `ece6db2ebaaaa98fbbd0235553bba1691d5e520a12a563410aad2ee082032a99`다. 기존 canonical DLL/독립 변경/Config를 보존했다. 근거: [선택 전달](../../Saved/ImportReports/PlayerAttackVFX_20261008/MainDelivery/Delivered.json), [전체 빌드 후보](../../Saved/ImportReports/PlayerAttackVFX_20261008/NativeBuildCandidateProof.json), [실제 Main 모듈](../../Saved/ImportReports/PlayerAttackVFX_20261008/MainRuntimePIE/ActualNativeModule.json).

기존 ActionAbility가 Start/Stop/ClearCombatEffect와 weak resource record를 공유하고 Combo/Brutal이 자기 실제 montage instance·avatar·적중·취소 수명을 검증한다. 새 공통 manager/component/전역 Tick은 없다. 신규 runtime 파일은 data-only Notify h/cpp 두 개다. Combo의 sampled time/instance/execution과 HP 음수 producer 검증, 현재 node의 실제 적중 관측·EventId 재생 중복 방지, 자연 마지막 collision flush의 제한된 cached instance, 저프레임 복원 효과의 원본 window 길이 timer를 유지했다. Brutal은 동기 GE 반환 후와 복원 entry마다 기존 montage/instance/target/avatar/ASC/Anim identity를 재확인한다. 조건 없는 효과는 hit bypass 없이 중복 검사를 유지한다. 정상·취소 cleanup은 자기 자원만 처리하고, 명시된 종료 flag와 잔여 particle/engine decal lifespan을 구분한다.

새 hidden Main RHI PID12708에서 실제 전달 alias를 로드해 `Khazan.CombatEffect.PIE`를 실행했다. 실제18 Combo 진입과 Brutal5case, 원래 notify/input 흐름·취소·재시작·stale instance·다른 avatar·늦은 marker 거부가 Success다. 실제 Weak01 collision에서 몬스터 HP110→100과 조건부 효과2개를 관측했다. Front/Back의 제품 BrutalHPDamage0에서는 HP100 유지·조건부 효과0개가 올바른 결과였다. HP/16=6.25는 transient Definition을 사용하는 개발 fixture뿐이며 저장 제품 피해량을 바꾸지 않았다. 그 fixture에서는 HP100→93.75와 Front4개/Back3개 조건부 효과를 확인했다. 176개 화면을 수집했고 머테리얼 compile/default fallback0, package save0, exit0(136.063초)이다. [Main RHI 결과](../../Saved/ImportReports/PlayerAttackVFX_20261008/MainRuntimePIE/Driver.json).

별도 새 Main commandlet PID32404는 8개 저장 몽타주의401개 EventId에 Start/End 각각1개, 원본 gameplay GUID/실제 trigger/section/slot 및8,308개 필드 검사를 통과했다. package bytes unchanged, Source/asset save0, exit0(9.781초)이다. 원본401개는347개 Combo와54개 Brutal(Particle48/Decal6)의 저장 occurrence 수이며, 모든 조건부 occurrence가 매 공격마다 실제 화면에 나왔다는 의미가 아니다. [Main 저장 감사](../../Saved/ImportReports/PlayerAttackVFX_20261008/MainCombinedSavedAssetAudit.json), [통합 최종 근거](../../Saved/ImportReports/PlayerAttackVFX_20261008/FinalVerification.json).

원작 native BattleEffectIndex/첫 Brutal 적중 연결·super-armour gate·생략된 CDO 기본값은 미확인이다. 현재 execution의 실제 HP hit를 뒤의 조건부 window가 소비하는 정책, 겨울 actor/aggregate snow→SurfaceType13, 첫 correction snapshot, only-start-attach, additive random 및 signed decal 크기/곡선 lifespan 정규화는 명시된 프로젝트 adapter다. 원작 셰이더 topology·픽셀 일치/멀티플레이와 GE 내부의 즉시 취소·재활성화 실동작 시험은 완료로 주장하지 않는다. 세부 Art 근거와 남은 원작 차이는 [Art 재생 정본](../Art/PLAYER_ATTACK_VFX_PLAYBACK_20261008.md)을 따른다.

사용자 Main PID16572는 마지막 읽기 확인에서 DevMap/PIEfalse/dirty0이었다. 이 작업은 해당 에디터를 저장·PIE·종료·native reload하지 않았다. 현재 열린 에디터는 구 모듈이므로 정상 재시작 후 새 Notify schema와 몽타주를 확인한다. 구 모듈 세션에서 새 schema 에셋을 다시 저장하지 않으며 전체 재추출·재작성·과거 alias 재전달을 반복하지 않는다.

최종 receipt 상태는 `MainDeliveredAndFreshVerified`이며 full Source/선택 bytes/보호 자산 검사를 통과했다.401개는 Particle345/Decal56개다. 검사한 Main4장에 한한 transparency/silhouette 확인은 통과했으나 shipping 성능 profiling은 수행하지 않았다. 별도 원본 environment notify인 Snow65개+Brutal Snow4개/Water20개는 원작 전용 실행을 복원하지 않았으며 기존 눈 변형 구현을 이 원본 window 전체의 동일 재생 증거로 대체하지 않는다. OverFury B01 prelude의 대응 원본 effect notify도 미확인으로 남긴다. FinalVerification의 현재 결과가 frozen pre-delivery metadata의 pending runtime/Main 필드를 대체하며, 그 역사 기록은 보존한다.


<!-- MonsterBrutalDamage50_20261008 -->
## 2026-10-08 19:48 KST — 브루탈 어택 총 HP 피해 임시50 설정

사용자 요청으로 Swordsman/SwordShield/HeavySwordsman/HalberdElite/ApesStoneHandElite/Yetuga의 `/Game/Monsters/<family>/Data/DA_Character_<family>` → Monster Stamina → `BrutalHPDamage`를0에서50으로 저장했다. 단위는 HP 절대량이고 원작 환산값이 아닌 사용자 지정 임시 튜닝이다. 앞/뒤 공통 브루탈1회당 총량이며 기존 `BrutalHit2`에서 한 번 적용한다. 패링·일반 공격의 Stamina 감소량과는 별개다. 이전 미할당0/조건부혈흔0 기록은 당시 검증 상태로 보존하며 현재 설정은 이 절의50을 따른다.

수정은 CharacterDefinition6개의 해당 필드뿐이다. 다른 stamina 설정·LocomotionConfig·UnawareRoutines·InitialAbilityGrants·InitialEffects를 수정 전후 및 새 별도 Main commandlet 재로드에서 동일하게 확인했다. Source/런타임 클래스/몽타주/모듈 선택은 편집하지 않았다. metadata 증거는 `Metadata/MonsterBrutalDamage50_20261008/Authoring.json`, `FreshSavedReadback.json`이며 원본6파일은 같은 경로 Before에 보존했다. 두 commandlet은 별도 프로세스로 성공 종료했고 사용자 에디터를 제어하지 않았다.

이번 검증은 저장된 값50과 다른 필드 보존의 읽기 검사다. 기존 양수 피해/중복 방지/양쪽 완료 native 검사와 VFX transient6.25 검사는 과거 결과이며50으로 PIE를 새 실행한 것으로 기록하지 않는다. 기존 확정 적중을 읽는 VFX 정책은 이제 실제 양수50 피해에 적용될 수 있으며 VFX가 추가 피해를 만들지 않는다. 조정은 같은 DA의 BrutalHPDamage에서 수행하고, 과거0인 author receipt/asset payload를 현재 설정 위에 다시 전달하지 않는다.
<!-- PlayerAttackVFXPolish_ARCH83_2127 -->
## 2026-10-08 21:27 KST — ARCH-83 표현 좌표의 현재 포즈 보정 착수

이번 직접 품질 수정 요청에서 기존 first correction inverse×live socket 경로가 branching notify 시점에 이전 프레임의 published bone을 읽는 문제를 확인했다. 원본 correction22건을 현재 sequence pose와 표적 대조한 증거는 `Saved/ImportReports/PlayerAttackVFXPolish_20261008/RuntimeTransformAudit/{DirectionCorrectionProposal,NotifyPoseOrderingSourceAudit}.json`에 둔다. 원본 queued field와 현행 UAnimNotify_PlayMontageNotify의 강제 native branching을 구분한다. 현재 source/engine frame 순서 및 일부 이전 raw pose key와의 대응은 검증했고, 모든 spawn callstack을 디버거로 측정했다는 뜻은 아니다.

ARCH-83의 Ability 소유 표현 수명은 유지한다. 새 class/component/manager/runtime file, gameplay 상태 사본, 전역 yaw/scale 수치를 만들지 않는다. 명시된 비부착 world/top-owner9건은 기존 Avatar 회전 및 Mesh 원점을 통해 authored ground-origin cm를 해석하는 프로젝트 adapter로 보완할 계획이다. 다른13건의 부착 동작은 보존하며 기존 source-local 보정 계산에 필요한 첫 socket pose만 같은 Mesh의 bone-finalized callback에서 확정할 계획이다. Callback은 실제 생성 component의 첫 프레임에만 사용하고 취소/End/무효 component에서 해제하며, 기존 Stop/Clear 수명에 둔다. 새 입력/피해/콤보 dispatch 수명이나 montage retime을 추가하지 않는다.

현재는 private 구현 착수이며 적용/build/PIE/Main 전달 완료가 아니다. 생산 변경 범위는 기존 KZActionAbility h/cpp와 이미 변경한 개발 KZCombatEffectPIETest.cpp이다. 이후 새 build와 sparse 방향 A/B, 전체 actual RHI, cleanup/isolation·현재 Brutal50 사례, unchanged8/401 저장 감사 및 Main 선택 전달을 통과해야 실제 완료로 추가 기록한다. 원본 cooked correction interpolation 코드와 shader topology는 미복원이며 이 해석을 원작 실행 코드 직접 복원으로 표현하지 않는다.

## 2026-10-11 — ARCH-83 공격 VFX polish의 최신 Main 실제 실행 검증 완료

앞선 재개 checkpoint의 Main 검증 대기를 [새 Art-only 완료 receipt](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/ArtFollowupV5/Prepared_20261010T164700280003Z/Completion.json)로 대체한다. 후속 Main 제품 변경은 선택 Art6이며 이 재개에서 Source/native/modules 쓰기0이다. 원래 Player Source3/old14 provisional 기록은 보존하고, 외부 Monster immutable Delivered12f3…/successful Build19 compiled Source101/current module b84df875…를 보존한 상태에서 fresh Main 검증을 새로 실행했다. private98/d195 결과를 최신 Main 코드의 실행 완료로 재명명하지 않았다. 기존 Player alias와 다른 B 입력·Definition·맵 등은 보존됐다.

현재 생성은 `UKZAnimNotify_CombatEffect::SpawnComponent`의 외부 공유 factory를 사용한다. Action은 동일하게 sampled local 값을 복원해 최초 bone-finalized callback을 Activate 전에 연결하고 random을 재추첨하지 않는다. world/top-owner9 해석과 attached13의 현재 포즈·일회 callback/취소 cleanup 계약은 유지한다. `EnsureIsComplete`의 WITH_EDITOR 보완은 decal material에만 있었다. PSC Activate 경로에도 그런 API를 추가했다는 이전 독립 검토 문구는 source-obvious 확인 후 철회했다. 새 runtime class/manager/component/상태 사본을 이 재개에서 추가하지 않았으며 ARCH-83/v2의 소유 수명을 바꾸지 않았다.

fresh Main RHI02 PID29752는175.63797초/exit0으로 실제 공격18개와 Brutal5case, authored total HP50 양수·transient0 음수 사례 및 current-instance/wrong-avatar/late-marker cleanup을 통과했다. `ActualNativeModule.json`의 실제 모듈 b84와 Main Source101/Config5/DAS203/Effects6335/native snapshot before==after를 확인했다. 현재 source migration이 포함된 callback 최초 transform은 FirstPoseMain02에서13/13개 확인했고 최대 회전 잔차2.119010463505988e-05도다. 이는 측정된 부동소수점 검증 결과이며 gameplay 튜닝값이 아니다. private13/13 잔차0 결과도 예비 증거로 별도 보존했다.

별도 Main Saved02 PID31340/133.56034초/exit0은 저장 몽타주8/401구간/8,308필드와 Art18의 exact source/hash/graph/SM6를 확인했다. fresh Main 두 검사 모두 save0·compile/default fallback 오류0이다. 입력13개는 `AfterDelivery_MainProofClosed_20261010T165522461653Z.json` SHA05dbc86f…에서 변경0이며, 기존 브루탈 B mapping을 보존했다. 실제 물리 B 버튼을 새로 눌러 검증했다는 뜻은 아니다. Root 화면 검사9장·독립 검사 및 남은 작은 glints/gray bands·원작 shader/pixel 일치/Shipping 미검증은 [Art 재생 정본](../Art/PLAYER_ATTACK_VFX_PLAYBACK_20261008.md)의 이번 날짜 추가 절을 따른다.

최신 결과는 `ArtFollowupDeliveredAndFreshMainVerified`이며 original receipt/Frozen/Ready 및 보호 Main 파일을 덮어쓰지 않았다. 이번 범위는 선택된 품질 artifact 보정과 현재 native 동작 검증 완료다. 후속 작업은 현재 Main manifest/Source를 먼저 읽고 이 완료 receipt·actual02 증거를 기준으로 시작하며, old private native 또는 과거 alias로 복원하지 않는다. 사용자/외부 에디터 제어0, Root 숨김 검증 에디터는 모두 종료됐다.

<!-- PlayerAttackVFXPolish_Resume20261011_Main18Complete -->

## 2026-10-11 — HeinMach clean presentation: 카메라·루트모션 검증 완료

기존 AKZMonster ctor의 Capsule/Mesh 및 BeginPlay의 실제 UPrimitiveComponent 전체에 ECC_Camera=Ignore를 적용했다. Blueprint collision profile/modular parts 초기화 뒤에도 유지하며 Pawn/Visibility/World 응답과 SpringArm probe는 변경하지 않는다. 작성자/소비자는 기존 Monster 초기화/기존 SpringArm이고 game thread의 Pawn 수명에 묶여 새 상태/handle/cleanup/Ability 수명은 필요 없다. Source1파일, 새 runtime 파일0이며 ARCH-83/v2의 효과 생성·실행/취소·피해 책임은 유지했다. 현재 KZActionAbility/Combo/Notify timing은 이번 작업에서 편집하지 않았다.

MainBuild02 성공/입력 해시 불변, 현재 Main 모듈 UnrealEditor-Khazan-2026101101.dll. 실제 FinalVFXPIE03 native18+Brutal5 Success/compile·fallback0/save0이며12마리 모든 PrimitiveComponent Camera Ignore를 확인했다. 기존 GiantCombatFall/MonsterVFX/Player alias 및 gameplay 구현 위에서 빌드했으며 옛 private native alias로 되돌리지 않았다.

MonsterAnimationAudit02의 BP7/hard·soft closure1380에 연결된 사용 AnimSequence238은 전부 이미 root motion enabled, disabled0이었다. animation write0, ABP6의 RootMotionFromMontagesOnly/force-lock/rate/length는 유지했다. RootMotionFromEverything 전환이나 root displacement repair를 한 것으로 표기하지 않는다.

Art의 PP8 제거/nonPP9861 유지, exposure128, 차지/OverFury/혈액 교정·원본/TEMP 수치와 검증 범위는 [Art 정본](../Art/HEINMACH_CLEAN_PRESENTATION_20261011.md)에 분리했다. Engine 기본 exposure/HDR/AA/Fog는 유지하며 프로젝트 Bloom/MotionBlur/LensFlare/LocalExposure 기본값은 Art 요청을 위해 조정했다. [Completion](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion.json), [정확한 Source/Config diff](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/OwnSourceChanges.patch)가 최신 적용 증거다.

<!-- HeinMachCleanPresentation_20261011_FinalVerified -->

## 2026-10-11 — 최종 혈액 분사/데칼 event 분리 증거 보충

최신 제품 snapshot은 [Completion_FinalBloodEvents.json](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion_FinalBloodEvents.json)이다. sprite 분사66은 유지하면서 death→mesh-decal의 기존 Frequency0을 임시3으로 조정해 간접 decal 증가도 억제했다. 연속 Rate editable/baked0과 최종 Frequency3을 FinalAssetReadback03에서 확인했다. 정상66개 death 조건의 이론상22 events는 계산값이며 runtime 총량 실측은 아니다. 이전 snapshot과 실제 native/RHI 검증은 보존하며 다른138 asset/Source/Config는 그대로다. 상세 원본/TEMP 구분·검증 범위는 [Art 정본](../Art/HEINMACH_CLEAN_PRESENTATION_20261011.md)의 최종 추가 절을 따른다. 필수 잔여 작업은 없다.

<!-- HeinMachCleanPresentation_20261011_FinalBloodEventSeparation -->


## 2026-10-12T18:14:49.705318+09:00 — 내려찍기 KZ_Parring_Distort Main 완료

기존 FallAttack의 Start3.741868019104004/End3.8630430698394775 branching 부모 안에 KZExtra_PlungeDistort child 한 쌍을 추가했다. 기존 source ground dust·GUID·section/segment·공격 판정/피해/오디오·RateScale은 보존했다. 최신 Main ARCH-95의 NiagaraTemplate/공통 UFX 실행·종료·module 의존성을 재사용하고 shared factory에 실제 traced floor normal의 User.KZFloorNormal와 sort/dilation 처리만 합쳤다. UObject receipt·끝/취소 cleanup은 기존 ActionAbility 소유다. UE5.8에서는 UFXSystemComponent가 기존 ParticleSystemComponent.h에 선언되므로 없는 별도 include 두 줄을 제거했다. 새 runtime class/file/tag0이다.

선택 전달8행(기존 runtime factory1/DEV1/asset6)과 include 보완2, MainBuild03 exit0, fresh MainSaved01 저장0, MainPIE02 actual input fall→landing의 유효1개·바닥/분리/normal·정지·기존 dust 유지가 통과했다. 실제 loaded current canonical module와 파일 SHA는 Metadata/PlayerSlamDistort_20261012/FinalVerification.json에 있다. 초기 floor rotation90도 trial은 철회했고 최종 RelativeRotation0/Scale1과 normal binding을 사용한다. 사용자/foreign editor 저장·종료·reload0이며 후속 stock build의 current manifest를 보존했다. 필수 잔여0; 전체 author/과거 alias 전달은 반복하지 않는다.


<!-- CombatVFXSequencer_20261013_MainApplied -->
## 2026-10-13 18:10 KST — ARCH-95 공격 Niagara 시퀀서 편집 경로와 Main 적용

사용자가 애니메이션과 Niagara를 같은 타임라인에서 보고 위치·회전·크기·시점을 조절하도록 기존 CombatEffect notify와 Action receipt를 확장했다. 새 runtime class/component/manager/tag는 없다. 에디터 전용 Content/Python/kz_combat_vfx_sequencer.py가 LevelSequence의 Player 애니메이션, Niagara Transform, Niagara Life Cycle을 구성한다. 적용 명령은 Sequencer 엔진이 평가한 actor-relative 변환을 애니메이션 FPS 간격으로 읽어 기존 몽타주의 FRuntimeVectorCurve 9축과 시작·종료 Notify에 기록한다. 런타임은 montage seconds에서 이 곡선을 샘플하고 기존 Ability effect receipt와 finalized-bone callback으로 갱신·취소·정리한다. 이전 Niagara/Particle/Decal 및 공격·피격·오디오·Root/FPS 경로는 별도 계약으로 유지한다.

WeakAttack02 편집 에셋은 /Game/Tools/CombatVFX/LS_DAS_Player_WeakAttack02_VFX다. 현행 WeakAttackCombo 몽타주 segment StartPos 2.0초를 시퀀서 0초로 사용한다. 공격 애니메이션의 60 FPS를 채집 간격으로 사용하고, 메인에는 KZWeaponSlash_KZFX_7b29e7a3260186fbb7016da5 한 Niagara의 115개 변환 키와 Life Cycle만 적용했다. 초기 35개 궤도 포즈의 출처는 이전 Main 실행에서 캡처한 실제 Niagara 컴포넌트 transform(Metadata/CombatVFXSequencer_20261013/ImportedMotion.json)이며 원작 게임 metadata 직접값으로 표시하지 않는다. 첫 Transform section은 잠긴 출발값, 두 번째 Additive section은 사용자가 편집할 조정값이다. QA의 X+20 cm/Pitch+7도/Scale+0.1 및 1프레임 구간 이동은 테스트 프로세스 메모리에서만 사용했고 Main에 저장하지 않았다.

Main 적용은 Metadata/CombatVFXSequencer_20261013/MainApply01/MainApplyReport.json에 기록했다. 몽타주 SHA256은 44c839b8869db097b1e4a40d9992f8b42d3325a40eb0da83890f5f5d68a15682에서 c6187baa705f6807fffc9f933bd8de87f20cce7e283d5c14f457b47ec34c7c66로 바뀌었고 직전 파일 백업은 MainApplyBackup에 있다. T3D 전후 비교에서 기존 Notify GUID 116개와 설정은 동일했고 새 대상 시작·종료 Notify 2개만 추가됐다(SavedScopeAudit.json). 공유 KZ_Slash와 SM_VFX_SlashRing_01 package SHA는 각각 3b9eb34b6bb2963ee8fe0eb1bc698ed427e742d59c9c43abe30494d6036f4a37 및 bb17545e9cd539f7af1448a182518672552f041ae1a28b4384a76bfc1f9362a8로 유지됐다.

RuntimeBuildFinal01 빌드 통과. 인메모리 편집 공격 검증 EditorToAttack02에서 Niagara 활성 27프레임이 편집 곡선과 최대 0.00008 cm/0.00086도 수준으로 일치했다. 저장 후 fresh Main FreshSavedPIE01은 PIE 성공·정상 종료했고 실제 활성 35프레임과 저장 시퀀스가 최대 0.00013 cm/0.00086도 일치했다. 잘못된 효과 구간은 저장 전 거부됨을 확인했다. 자동 에디터 렌더 캡처에서는 Niagara 컴포넌트가 Active이고 DesiredAge가 0.1396초까지 진행됐지만 Slash 형상은 별도로 식별되지 않았다. 따라서 대화형 에디터에서의 픽셀 수준 미리보기와 원작 화면 일치는 아직 검증 범위 밖이다. 정확한 재개 위치는 Metadata/CombatVFXSequencer_20261013/ResumeState.json과 Engineering continuity에 남긴다.


<!-- CombatVFXSequencer_20261013_VisualResolved -->
## 2026-10-13 18:31 KST — 시퀀서 Slash 미리보기 형상 검증 보완

앞 절의 자동 에디터 캡처에서 미확인이던 입자 형상 문제를 해결했다. Niagara System Life Cycle의 DesiredAge와 Active는 갱신됐으나 프레임을 seek한 편집 뷰포트에서는 입자가 렌더되지 않았다. 같은 컴포넌트에 ReinitializeSystem과 AdvanceSimulationByTime을 사용한 QA 캡처 EditorForceSimPreview15에서 실제 붉은 Slash가 나타났고, RenderingEnabled만 강제한 EditorForceRenderPreview16에서는 나타나지 않았다. 기존 runtime 및 공유 Niagara 자산은 바꾸지 않았다.

Content/Python/kz_combat_vfx_sequencer.py의 에디터 전용 Slate callback은 관리 대상 LevelSequence에서만 프레임·Transform·Life Cycle·시스템 변경을 감지한다. seek 또는 같은 프레임 편집 시 해당 시퀀서 시작점부터 Niagara를 재시뮬레이션하고 연속 재생 중에는 1프레임씩 진행한다. 편집 결과 수집 중에는 미리보기를 중지하며 시퀀서를 닫으면 상태를 비운다. EditorAutoVisual18 실제 시퀀서 재생 화면에서 붉은 Slash 형상을 확인했다. EditorScrubVisual19에서는 정지 프레임에서 자동 형상 표시와 저장하지 않은 Additive X+50cm 검증 편집에 따른 실제 화면 이동 및 actor transform 정확히 50cm 이동을 확인했다. QA 편집값은 Main 또는 LevelSequence에 저장하지 않았고, fresh runtime 결과와 Main 몽타주 SHA는 유지된다. 긴 Life Cycle/다수 Niagara 동시 편집의 에디터 성능은 이번 한 효과 검증 범위를 넘는다.

<!-- CombatVFXSequencer_20261013_FinalPreviewVerification -->
## 2026-10-13 18:40 KST 최종 에디터 미리보기 재검증

에디터 전용 자동 미리보기가 Niagara 시스템과 Life Cycle 변경까지 감지하도록 보완했다. 변경 후 EditorScrubFinal20에서 정지 프레임의 붉은 Slash 형상이 변경 전후 화면에 나타났고, 저장하지 않은 Additive X 50cm 조정에 따른 actor X 차이가 정확히 50.0cm였다(ScrubVisualReport.json, Exit.json exit 0). Python AST 검사에 통과했다. Main WeakAttackCombo SHA256은 c6187baa705f6807fffc9f933bd8de87f20cce7e283d5c14f457b47ec34c7c66으로 유지됐다. 현재 WeakAttack02 작업에 추가 필수 구현은 없으며, 다른 공격은 각 AnimSequence와 실제 Notify 배치를 확인해 개별 적용한다.
