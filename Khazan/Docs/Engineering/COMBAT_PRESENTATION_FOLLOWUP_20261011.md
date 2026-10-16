# CombatPresentationFix Main 후속 구현 — 2026-10-11

사용자의 모든 백그라운드 작업 Main 통합 요청으로 중단된 `Khazan_GiantFallWork_20261011` 후속을 재개했다. 이전에 완료된 MonsterVFX/GiantFall/PlayerVFXPolish/HeinMachCleanPresentation의 Main 결과는 유지한다. UI는 [별도 정본](COMBAT_UI_RUNTIME_20261011.md), 표현 수치·화면은 [Art 기록](../Art/COMBAT_PRESENTATION_FOLLOWUP_20261011.md)이다.

## 실제 변경

기존 Brutal/Exhaustion Ability가 paired 실행 동안 이전 AnimInstance RootMotionMode를 보존하고 임시 IgnoreRootMotion을 소유한다. 기존 종료/취소/실패 cleanup에서 자신이 소유한 변경만 복구한다. 기존 UpdateAlignment는 live victim 위치와 현재 capsule radius 합으로 목적지를 갱신해 exhaustion Start의 잔여 이동 때문에 간격이 줄어들지 않도록 한다. RootMotion enum은 엔진의 기술적 설정이며 원작 직접 수치가 아니다. ARCH-87의 모든 적격 조건 및 locked target 우선 선택은 유지한다. 별도 manager/FSM/새 runtime 파일은 없다.

낙하 montage는 저장된 원작→기존 baked 시간축의 inverse map을 한 번만 적용한다. `FallPlan.json`의 original StartEnd .273s/LoopEnd .29s는 현재 baked .3443923188s/3.7417676356s로 대응하며 Land가 기존 sequence 끝5.7666669s까지 재생된다. InputEnd local .4261631293s 및 공격 window end .1210816308s도 같은 변환이다. 직접 원본값과 계산값을 혼동하지 않으며 source plan은 `Metadata/InGamePlayback_20261002/PlaybackPlan.json`이다. sequence raw data/Player .01/비용·피해·blend 설정은 바꾸지 않았다.

설원은 기존 level-owned AKZSnowDeformation의 조정 가능한 PlayerCapsulePaddingCm와 기존 접촉 계산만 확장했다. 실제 capsule/snow 교차의 접촉 반경에 padding을 더하고 기존 rim support1.4를 나누어 전체 footprint가 지정 경계에 들어가게 한다. 실제 접촉이 없는 공중에서는 파이지 않는다. 게임 collider/CMC를 바꾸지 않는 표시 수명이며 비용·피해·Ability 상태를 소유하지 않는다.

## Main 전달과 검증

Source8/Content19를 baseline SHA/CAS/byte backup으로 전달했다. 정확한 파일은 `Metadata/CombatPresentationFix_20261011/MainResume/DeliveryReceipt.json`, backup은 `Saved/CombatPresentationMainBackup_20261011/20261011_114106`이다. private author wrapper·대량 editor dependencies·옛 native DLL은 전달하지 않았다. 이후 DEV snow fixture1과 UI ring 연결1은 receipt에 별도 기록했다.

MainBuild01/02 stock Editor target 성공. MainSavedResume01 새 read-only 검사 성공. MainNativeResume01은 원본 landed 완결과6종 front/back12사례 실제 B/paired montage/이전 root mode 복구/최소 capsule 간격에 통과했다. 간격은 현재 프로젝트 실제 capsule 합으로부터 계산된 값이며 원작 직접 거리 확인으로 부르지 않는다. MainSnowResume03은 실제 GPU40cm, foot 목표35cm(측정34cm), capsule 바깥0 및 이동·회피·평가된 공격·공중·몬스터4종 접촉을 통과했다. 실제 표본/허용오차는 native test와 NativeSnowQA를 따른다.

MainSnowResume01의 잘못 열린 DevMap과 Resume02의 바위에 막힌 단일 +X probe는 fixture 문제로 판별했다. canonical map을 직접 열고 검증하며 노출된 radial axis를 선택하도록 수정했다. gameplay 변경으로 검사 실패를 숨기거나 판정을 삭제하지 않았다. 기존 SnowQA를 보존했다. UI 최종 PIE05는 전체 기능과 shader fallback0/Exit0이다. 마지막 VFX observer의 최종 상태는 하단 완료 절 및 FinalVerification을 따른다. full original shader/VM/pixel/frame·네트워크·Shipping 성능은 미검증이다.
## 2026-10-11 — Main 최종 완료

필수 잔여 작업은 없다. [FinalVerification](../../Metadata/CombatPresentationFix_20261011/MainResume/FinalVerification.json)은 MainDeliveredAndFreshVerified다. 새 canonical DLL SHA256 `c908da8696b7844df39c7d476aa3ea8c10b96d206137b359c9252940d13c98bf`, MainBuild02 및 saved/paired12/Snow/UI 최종 검사를 결속한다. MainVFXResume02는 native18+Brutal5 Success/392 PNG/material fallback0/Exit0이다. 동일 카메라 HeinMach3 및 actor9861/PP0/save0도 완료됐다. task-owned editor는 전부 종료했고 외부 editor/Rider 제어0이다. 다음 수정은 현행 Main과 이 receipt/관련 원본 metadata에서 시작하며 author 증량이나 전체 private 복사를 반복하지 않는다.


## 2026-10-12T13:12:55+09:00 — ARCH-92 사망·브루탈·액션 VFX Main 완료

Main Source10(runtime6/DEV4), montage8, 새 runtime 파일0을 적용했다. baseline Source121 중 무관111파일을 보존했고 원본 Root88/게임플레이 공격 창·피해·오디오·UI·애니메이션 raw pose는 변경하지 않았다. FinalBuild05 current canonical build/input동일, fresh SavedAudit02 8/55/dirty0/save0가 통과했다. Main 기존 파일을 직접 보완했으며 private DLL/Config 전달0이다.

일반 사망은 interruption을 완료로 간주해 현재 포즈를 멈추던 것이 원인이었다. 기존 RefreshCombatState로 다음 tick에 사망 동작을 재시작한다. DeathBaseline01의 중단6 오차167–441cm → DeathFixed02의 정상6/중단6 terminal pose 오차0. 짝 사망은 task blend-out 완료 시 source 마지막 pose가 이미 idle로 섞이는 문제가 있었다. HP0인 자기 victim instance만 auto blend-out을 끄고 Monster의 기존 GT tick이 finite end를 관측하여 Exhaustion의 기존 완료를 호출한다. shared asset/비치명타 recovery/정상·취소·EndPlay cleanup은 유지한다. LethalPairFixed01 실제 Front/Back12 terminal pose 최대0.015341 model cm, 접촉 XY offset0이 통과했다. 이는 사용자 전체 플레이에서 interruption 빈도를 계측한 결과가 아니다.

Brutal Root particle의 원본 source offset은 현재 capsule 짝 간격/수입 mesh yaw와 맞지 않았다. 기존 effect receipt만 찾아 detach/world XY 두 actor 중점·Z 두 chest 평균에 배치하고 기존 composed rotation/scale·피해·시간·수명은 유지했다. PresentationFinal02는 실제 LockOn→B 6종 Front/Back12, 비치명타 recovery/root-mode 복원 및 실제 낙하/착지/벽 옆 ground debris를 통과했다. EffectsFinal01 기존18+Brutal5, CollisionFinal01 실제16(Spin7/Fury19/miss/cancel/끝 접근), ParryFinal01 실제15/6종 정책도 통과했다. DEV-only viewport readback 추가 이후로만 실제 게임 화면을 판단한다. LethalPairFixed01의 이전 전역 screenshot은 editor viewport였으므로 시각 근거에서 제외한다.

혈흔은 기존 accepted-hit particle1회와 ground projector/fade/snow·walkable 계약을 유지하며 class 설정의6개 작은 satellite를90–280cm 범위/전체 방위로 생성한다. 독립 FRandomStream, 장애물/바닥/가파른 면 제외를 사용한다. DeathFixed01의 scatter0은 QA floor의 Static mobility로 scale이 반영되지 않은 fixture 문제였고 Movable fixture의 DeathFixed02 실제6종에서 main+6=7 /네 방향/범위/하향 normal을 확인했다. 제품 collision/지형을 바꾸지 않았다.

수치와 resource/표시 변경은 Art 최신 절을 따른다. 정확한 변경/각 실제 DLL/원본 보존/실패 기록은 Metadata/CombatFinishFollowup_20261012/FinalVerification.json에 있다. 원작 shader/pixel 완전 일치·Shipping stress/두 레벨 연속 전투는 이번 범위가 아니다. 이후는 현행 Main과 이 receipt에서 시작하며 stage/전체 author/Root·Parry 이전 전달을 반복하지 않는다. Main 정상 editor ready 여부는 후속 기록으로 분리한다.


## 2026-10-12T21:06:38.746735+09:00 — ARCH-95 최신 추가 Slash·타격 표현 Main 완료

사용자 최신 지시로 몬스터의 지정 Niagara 교체를 철회하고 원본120개 효과 occurrence를 복구했다. Player 원본50 start/stop쌍을 복구하고 별도 KZWeaponSlash child50쌍만 추가했다. immutable before package와220개 객체×21개 수정 field를 비교해 차이0이다. 원래 notify GUID/clock, ARCH-96 FPS·넉백, ARCH-94 방어/AI, SlamDistort·혈액/사망/UI/오디오를 보존했다. 과거 패키지 bytes 전체 또는 private DLL을 Main으로 덮어쓰지 않았다.

추가 Slash는 기존 Action effect receipt와 finalized-bone delegate로 소유한다. 실제 Weapon_L/R 뼈에 reference cutting-edge geometry를 연결하고 successive actor-space tip pose에서 이동을 뺀 swing tangent를 계산한다. FX marker의 별도 animation track은 실제 장착 무기의 대체 pose로 사용하지 않는다. X는 실제 접선, Y는 절삭면이며 requested mesh의200cm reference span/renderer yaw180·centre를 보정한다. Niagara component의 CurveRotation0/CurveScale1·Rotation0만 neutralise하고 shared Niagara asset은 보존한다. 정상/취소/node 교체·사망/UnPossess/EndPlay cleanup은 기존 receipt가 처리한다. 새 runtime class/component/manager/tag0, 새 개발 plunge QA1이다.

Native Player18+Brutal5/실제 승인 hit blood, collision16/Parry17·received-hit feedback/monster-overlap plunge ground·cancel, human33 actual attacks 및 original4-family FX·requested Niagara0이 통과했다. saved100 package에서 original monster120/player100+added player100을 확인했다. 실제 코드·에셋·loaded module 및 모든 검증은 Metadata/CombatImpactUpgrade_20261012/FinalVerification.json이다. 최신 normal Main editor를 열고 loaded module·dirty0 및 설정을 확인했다. Runtime Source가 같은 전체 suite와 DEV-only isolated4 preview를 구분한다. 이전 replace33 검증·실패 camera API·tail assertion은 최신 완료 계약의 근거로 쓰지 않는다.

## 2026-10-13 — 플레이어 피격의 추가 보라·파랑 불꽃 제거 Main 완료

사용자 직접 요청으로 Main /Game/Data/Character/DA_CharacterDefinition_Player의 HitReactions.ImpactEffect를 PP_Combat_HitBurst에서 None으로 변경했다. 현재 KZCharacter::PlayHitReaction은 확정 피격 뒤 선택적 ImpactEffect가 있을 때만 KZReceivedHitImpact 컴포넌트를 생성하므로 기존 경로에서 생성이 사라진다. 첨부 KZAbilitySystemComponent.cpp의 피해 승인/무적/Guard/HP/ST 경로는 변경하지 않았다. 새 runtime 파일/class/component/태그/수치0이며 피격 모션과 짧은 제어 제한을 유지한다.

공유 PP_Combat_HitBurst 자체, Guard GA의 ParryImpactEffect, 몬스터 승인 적중의 FP_Monster_HitBloodReference는 SHA 그대로다. 패링/플레이어 공격 적중/다른 캐릭터 표현을 함께 제거하지 않았다. Player Definition의 내보낸 전체 필드는 ImpactEffect 참조 생략 이외 같았으며 asset 1개만 저장했다. 선택적 설정의 의미에 맞춰 기존 KZParryPIETest.cpp:134의 받은 피해 효과 기대값을 설정 유무로 구분하는 한 줄만 보완했다. 이는 DEV 회귀이며 gameplay C++ 변경0이다.

Build01은 Main Editor Development target에 ModuleWithSuffix=Khazan,731301을 사용해 정상 완료했다. 실행 중 에디터의 원래 DLL을 교체하거나 HotReload/LiveCoding하지 않았다. Native02가 Main Binaries의 UnrealEditor-Khazan-731301.dll SHA 3f0ef023d75715c065404b25668851d81f61d7854a1600aaa99c234f26c03c63을 실제 로드했다. 새 프로세스의 저장 설정 None 재조회, 실제 melee/field/guard/cancel/소진/빠른 release의 17개 사례 Success/Exit0이다. 그중 HP100→93의 실제 피격 5개에서 KZReceivedHitImpact 수 0을 검사했다. HP/ST·패링 효과 수와 source L/R 성공 포즈의 기존 검증도 유지했다. native 검증 package save0이다.

Apply01은 UE ObjectExporter가 None/default struct 필드를 생략하는 데 대한 비교 가정이 잘못돼 저장 전에 실패했다. Main asset SHA를 확인하고 표적 정규화를 수정한 Apply02가 저장했다. Native01은 기존 일반 driver의 begin-play와 KZParryQA::FWait의 RequestPlaySession이 중복되어 새 pawn을 없앤 검증 실패다. driver만 수정한 Native02의 성공이 최종 근거이며 제품 코드를 바꿔 실패를 숨기지 않았다. 최초 로그는 보존한다.

완료 근거는 Metadata/PlayerReceivedHitVFXRemoval_20261013/FinalVerification.json, Apply02/{Result,Definition_Before,Definition_After}, Build01/Build.log, Native02/{Result,Driver,Editor.log,Exit}. 사용자 editor PID31508 및 외부 GiantVFX editor는 저장/종료/PIE 제어하지 않았다. RiderLink 연결false, 공식 Python remote discovery node0으로 현재 열린 사용자 세션의 cached Definition은 읽거나 갱신하지 못했다. 저장 프로젝트/새 프로세스의 검증은 완료이며 이전에 로드한 editor에서 효과가 계속 보이면 해당 Player Definition의 Reload가 필요하다. 전체 gameplay/Shipping/network/스피커 출력 검증으로 확대하지 않는다.

<!-- PlayerReceivedHitVFXRemoval_20261013_complete -->


## 2026-10-13T13:16:42.496440+09:00 — OverFury 원래 VFX 복구·나머지 Slash Main 완료

OverFury의 추가 KZWeaponSlash17쌍을 제거하고 원래 효과를 보존했다. 다른 공격의 추가33쌍은 KZ_Slash를 유지하면서 실제 무기 tip/radius/sweep와 asset의 initial particle rotation·size를 함께 반영했다. 기존 finalized-bone receipt에서 world tip−actor translation으로 body yaw도 포함하고, component의 User.ScaleLerp0 및 child yaw90/span400/location0을 사용한다. shared Niagara/mesh/material/texture 변경·새 runtime class/file/tag0, ASC·피해/콜라이더 수정0이다. 원작 숫자라고 표현하지 않는 asset 직접값/계산은 ARCH-95 최신 절과 NiagaraGeometryEvidence.json을 따른다.

MainApply01은 대상4 Source+6 montage SHA를 먼저 비교하고 atomic 교체하여 hardlink/병행 작업을 보존했다. Main build 후 full presentation18+Brutal5·actual accepted hit/cancel/두 avatar, 실제 GPU70 samples/17 nodes의 endpoint/절삭면, 원본1359×37 및 clocks/GUID를 재조회했다. 여러 시점/타이밍의 game captures와 actual grips를 중심으로 한 공중 Spin 검수를 했다. 새로 결합된 병행 build도 MainRHI04ComposedPreview에서 확인했다. native collision16은 Spin7/Fury19 HP/ST·miss/cancel/late approach를 포함해 Success다. 정확 module/SHA/모든 실패/진단은 Metadata/PlayerSlashAlignment_20261013/FinalVerification.json에 있다.

MainCollisionRHI01의 native 테스트는 Success지만 editor driver는 별도 Parry Reference M_Parry_Distortion/MI_FMI_fluid_A_162에서 FT_PerlinNoise_RG sampler Linear Color→Color 불일치로 failed다. 이를 전체 shader QA 합격으로 바꾸지 않는다. 해당 병행 Parry 소유자용 진단만 남겼으며 다른 material/texture를 수정하지 않았다. 원작 shader/pixel 완전 일치·Shipping/network stress는 이번 검증 범위가 아니다.

<!-- PlayerSlashAlignment_20261013_complete -->

## 2026-10-13 — ARCH-95 WeakAttack01 방향·전방 표현 Main 완료

사용자 사진의 반대 방향 Slash를 수정했다. 월드 좌표로 재생하는 원래 PlaneSlash의 CorrectionBoneName=Weapon_L을 추가 Slash의 공격 손으로 해석한 이전 author 휴리스틱이 원인이다. 실제 첫 약공격의 0.35→0.40초 포즈에서 Weapon_L 쪽 FX tip은 위로 회수되고 Weapon_R 쪽은 우측 위에서 좌측 아래로 이동한다. 이는 현재 실제 포즈 관측이며 원작 실행 코드의 확인으로 표현하지 않는다. 정확한 데이터·근거는 Metadata/WeakAttack01Slash_20261013/CuttingHandEvidence.json과 EquippedGeometryObservation.json이다. addon SourceField의 기존 L 문구는 초기 생성 이력이며 현행 Near/Tip 설정과 이번 override를 우선한다.

AM_DAS_WeakAttackCombo의 첫 KZFX_bab7be8e310a56b59c0b9461 및 KZWeaponSlash start/end4 객체만 변경했다. 추가 효과 Near/Tip을 FX_R_Sword_02/01로 바꾸어 실제 내려베는 Weapon_R을 따른다. 기존 RelativeLocation을 Action finalized-pose receipt에서 avatar-local cm로 더하는 작은 계산만 추가했다. 양수 scale/zero offset의 나머지 공격과 기존 수명/취소 cleanup은 유지한다. 새 runtime 파일/class/component/manager/tag0이며 실행 Source1/Notify 설명1/기존 DEV1/asset1이다. 중간 음수 scale 반전 후보는 시각 실패로 철회했고 관련 product 코드도 제거했다.

전방35cm·평면 크기1.15배는 요청한 전방 확대를 위한 TEMP이며 원작 직접값이 아니다. 에디터에서 첫 notify child의 RelativeLocation/Scale3D로 조정한다. 최신 Main montage 사본에 선택 저작하고 전체 직렬화 diff를 검사한 뒤 SHA CAS/atomic replace로 반영했다. Main SavedMain01은 FinalAuthor01 전체 export와 완전히 동일하다. notify clock/GUID·다른 효과와 오디오/HP/ST/피해/콜라이더/Physics 및 다른 montage5는 보존한다.

MainBuild04 성공, 실제 MainRHI01의18 natural node·Brutal4/실제 승인 HP110→100·두 avatar/조건부 효과·정상 종료/취소 및 실제 GPU70개·17공격은 성공했다. 세 actor-relative 시점·초기/중기/후기 장면289개를 검수했고, MainYaw90RHI01에서 actor를90도 회전시킨 첫 약공격도 성공했다. 각 프로세스의 실제 DLL df9764361d10eec695f0855e34b0dacfb98da06138303a1c8db17cbd7a1f0ed3를 결속했다. GPU 최대0.000031cm는 reference marker+명시된35cm offset에 대한 검수 오차이며 실제 메시 vertex와 완전 일치라는 뜻이 아니다. 현재 Imperial_R tip과 가상 marker의 가장 가까운 vertex 차13.147cm 및 원작 shader/pixel parity 미확인 경계를 보고서에 명시했다.

정본은 Metadata/WeakAttack01Slash_20261013/FinalVerification.json, 재개는 ResumeState.json이다. 필수 잔여0, own editor0, 외부 editor 제어0이다. 실패한 TGA/NullRHI FBX export·문자열 진단·mirror 후보 및 중단한 private 전체 build는 보존한다. 이후 현재 Main Source/first4 객체에서 시작하고 stale private Source/DLL·전체6 montage author·mirror 후보를 전달하지 않는다. 앞선 SlashAlignment의 축/GPU 합격이 사용자 사진의 반대 방향을 해소했다는 판단은 이번 actual hand/시각 검증으로 대체한다.

<!-- WeakAttack01Slash_20261013_complete -->

## 2026-10-14 — 브루탈 치명타 사망 몽타주 전환

이전 `LethalPairFixed01`은 HP0 짝 피해자의 `Damage2` 마지막 프레임을 정확히 고정했다. 그러나 그 검사는 실제 사망 몽타주를 실행하지 않았고, 마지막 짝 포즈가 서 있는 시체로 남을 수 있었다. 현재 `KZExhaustionAbility::FinishDeath`는 짝 Ability의 몽타주와 이동 제약을 정리한 다음 기존 `AKZMonster::FinishDeathPresentation()`을 호출하여 Definition의 `DeathPresentationMontage`를 재생한다. 완료 전의 짝 반응·Hit2 피해와 비치명 소진 회복은 유지한다.

기존 `Khazan.CombatPresentation.PIE`의 치명 6종×정면/후면12 검사를 사망 몽타주 관측 및 해당 몽타주의 terminal bone pose 비교로 수정했다. 실제 Main DevMap D3D12의 `BrutalDeathVisual01`은 12/12 성공, terminal pose 오차 최대 4.55e-13 model cm, 최종 화면 12장을 기록했다. Swordsman `Death_00.png`, Apes `Death_09.png`, Yetuga `Death_10.png`에서 바닥에 쓰러진 시체를 직접 확인했다. 독립 `Khazan.CombatFinish.DeathPose.PIE`는 일반 사망 정상/중단 6종×2=12건 성공이다. 검증 모듈은 `UnrealEditor-Khazan-2026101401.dll`이며 기존에 열려 있던 사용자 에디터는 재시작 전 이 코드를 로드하지 않는다. 상세 증거와 SHA는 `Metadata/PlayerImpactSFX_20261013/FinalVerification.json`이다.


## 2026-10-14 — ARCH-95 KZ_Slash 무기 바깥 배치 계약 Main 완료

기존 `UKZActionAbility`의 finalized-bone effect receipt에서 실제 장착 무기의 좌·우 선택, tip, 스윙 접선, 절삭면을 계속 계산한다. 추가 효과 Notify에 `WeaponSlashOutwardOffsetCm` 하나를 추가하고 기존 leading mesh endpoint 위치를 구한 뒤 캐릭터→실제 tip의 지면 평면 방향으로 이 거리만 이동한다. 칼날 방향만 따라 밀면 차지 타격 중 칼끝이 몸을 향하는 프레임에서 효과도 몸 안쪽으로 들어오는 문제가 있어 방향을 분리했다. 값 0은 기존 배치를 유지한다. Sequencer 소유 WeakAttack02와 원래 Cascade/Decal, 수명·취소·피해·오디오는 건드리지 않는다. 새 runtime class/component/manager/tag/file은 없다.

다섯 몽타주 33쌍 중 32쌍의 좌·우 무기와 크기·거리만 변경했다. 수치는 25–100cm/XY 1.12–1.25배의 **TEMP 시각 튜닝**이며 원작 값으로 표현하지 않는다. 격리본의 원본 해시 확인·T3D 허용 field diff·백업 후 메인 에셋 5개를 SHA 비교/교체했다. 새 프로세스 저장 재검사는 원래 효과 882개와 Notify 시간·GUID가 동일하고 WeakAttack02 Sequencer 두 객체가 변하지 않았음을 통과했다. Main `KhazanEditor` 빌드 및 실제 D3D12 `Khazan.CombatEffect.PIE`가 성공했고 GPU 입자 끝점 68건의 목표 위치 최대 오차는 0.000042cm다. 실제 로드된 표준 DLL SHA, 작업본의 단독/합성 캡처, Main 288장과 저장 에셋 영수증은 `Metadata/PlayerSlashOuter_20261014/FinalVerification.json`에 결속했다. 이 오차는 현행 무기 marker/추가 효과 계약 검수이지 원작 영상 픽셀 일치나 Shipping 성능 증명이 아니다.


## 2026-10-15 — 6종 치명 브루탈 피해자→사망 관성 연결 완료

기존 paired victim/Hit2 피해/terminal hold/죽음 owner를 유지하고 `AKZMonster::FinishDeathPresentation`에서 원본 death BlendIn과 `FKZMonsterStaminaSettings::DeathTransitionBlendSeconds` 중 큰 시간으로 montage inertialization을 요청한다. 새 .24s 최소값은 원작 직접값이 아닌 TEMP이며 기존 Definition 설정에서 조정한다. 더 긴 원본 blend는 보존한다. 포즈를 즉시 바꾸거나 짝 반응 중간에 사망 몽타주를 실행하지 않는다.

FinalRHI01 실제 Main D3D12에서 Swordsman/SwordShield/HeavySwordsman/HalberdElite/ApesStoneHandElite/Yetuga 6종×정면/후면12 lethal pair가 모두 Success다. 실제 death montage, 완료 terminal pose, capsule/root scale 복원, spacing을 확인하고 pair→death 첫.4s를.08s 간격5장씩 기록했다. transition frame/bone velocity는 진단 자료이며 임의 threshold로 원작 일치를 주장하지 않는다. 최종 근거와 각 run의 실제 DLL hash는 `Metadata/CombatFeel_20261015/FinalVerification.json`. 기존 dissolve/ash/일반 사망/비치명 groggy 회복과 관련 없는 Source를 일괄 교체하지 않았다.



## 2026-10-15 — ARCH-88/95 승인 피격 혈액 재사용 Main 완료

사용자 최신 요청으로 기존 Player ImpactEffect=None을 대체하여 Player와 몬스터6종 Definition의 HitReactions.ImpactEffect에 정확한 현재 Brutal PP_Dmg_Blood_Trail_Sub를 연결했다. 기존 AKZCharacter::PlayHitReaction의 승인 후 분기에서 흉부 socket 높이와 현재 scaled capsule axial segment의 최근접점을 구하고, 공격자 방향으로 capsule radius만큼 이동해 몸 밖 표면에 재생한다. 숫자 튜닝/새 gameplay 상태·태그·class·manager 없이 현재 캡슐 치수를 소비한다. 피해 승인/가드·회피/Ability 수명과 기존 Additive 반응을 변경하지 않는다. 원본 PS의 수명/개수/곡선·Notify 시간과 나머지 Definition 설정을 보존했다.

MainHitsHein01 실제 표준 Main 모듈(7f2e1da8def438bcddf20694628269efe1dca60bf6eb52212381b8295e0c3857)에서 Khazan.Parry.PIE, Khazan.MonsterRepair.PIE, Khazan.Combat.PlayerAttackCollision.PIE 모두 Success, 저장0/재질 compile failure0이다. 플레이어 승인 피해의 received-hit effect1과 가드/패링 blood0, 몬스터6종·사망·경사면/접지 없음/독립 혈흔 수명을 확인했다. 넓은 기존 CombatEffect montage 검사는 QA fixture/AI 간섭 및 후속 wall watchdog으로 일부만 완료됐고 전체 성공으로 기록하지 않는다. 이번 변경은 montage clock/particle template을 바꾸지 않았다.

그 뒤 기존 DEV QA 파일 KZMonsterPresentationRepairPIETest.cpp의 editor/dev automation guard 안에 작은 KZ.QA.ColourShot console command를 추가했다. paused PIE의 global Shot이 editor viewport를 찍는 문제를 실제 GameViewport ReadPixels로 해결한다. shipping 기능/새 runtime 파일은 없다. MainCaptureBuild02 표준 빌드 성공, 새 모듈73fed22564f0657a1d1bc7b2c56d8c6637b7f2279974645e13d1c354313d40cd의 native 색 비교가 성공했다. 전후 모듈을 같은 hash의 검사로 표현하지 않는다.

정확한 작업 전 대비 source diff2개, Main105 전달/SHA, saved readback, 각 모듈·PIE·촬영 근거는 Metadata/HeinMachColourVFX_20261015/FinalVerification.json에 결속했다. 장면·혈흔 TEMP 색 수치는 Art 정본으로 분리했다. 기존 사용자/병행 변경은 보존하고 Rider/타 editor를 종료·저장·reload하지 않았다.

<!-- HeinMachColourVFX_20261015_complete -->

## 2026-10-15 — 컨트롤러 전투 진동 소스 반영 (검증은 사용자 요청으로 생략)

기존 AKZPlayerController에 정적 PlayCombatRumble(Source,bStrong)와 조정값만 추가하고 UE PlayDynamicForceFeedback을 사용한다. 로컬 Controller/현재 Pawn만 출력하며 Player 효과는 자기 Controller로만 전달한다. 몬스터 효과는 각 로컬 Pawn과의 거리에 따라 감쇠한다. bCombatRumbleEnabled와 엔진 bForceFeedbackEnabled를 존중한다. 새 runtime 파일/class/manager/component/태그·에셋0이다.

- UKZComboActionAbility.UpdateAttackCollision: 실제 authored hit창에 진입했을 때 HitGroup별1회. 현행 WeakAttack 접두 Node는 약한 진동, Strong/Charge/Spinning/OverFury 등 나머지 Player 공격은 강한 진동이다. 미스도 실제 스윙 시점에는 재생한다. 자연 완료의 과거 hit창 flush에서는 뒤늦은 진동을 발생시키지 않는다. 새 RumbledAttackGroups는 기존 ResetAttackCollision에서 초기화하며 피해자 hit dedup은 변경하지 않는다.
- 몬스터 node 시작은 약한 준비동작 진동, 공격창은 강한 진동이다. MonsterPatternAbility의 별도 분기/판정을 수정하지 않고 기존 ComboAction 상속 경로를 사용한다. 인간형 Elite의 현행 공격 경로도 이 공통 코드를 소비한다.
- Guard의 실제 bParried 승인 분기에 강한 진동을 연결했다. 카메라 gain/VFX 유무와 별도이며 가드 입력 시작·일반 가드 성공을 패링으로 간주하지 않는다.
- 기존 MonsterVisual 원본 카메라 notify의 양수 scale/비영 amplitude 시점에 강한 충격 진동을 연결한다. 기존 내려찍기/착지/포효 등의 authored 시계를 재사용한다. footstep/ground-material audio notify는 약한 이동 진동이다. 사운드의 기존 local/locked 게이트는 유지한다.

설정 위치는 PlayerController Class Defaults의 KZ|Feedback / KZ|Feedback|Temporary다. FVector2D.X는 UE normalized intensity0~1, Y는초(s)다. 원작 진동 metadata 미확인으로 아래는 모두 어시스턴트 TEMP이며 장치 체감 검증값이 아니다.

| 용도 | 강도 X | 시간 Y |
| --- | --- | --- |
| WeakAttack | .22 | .06s |
| Strong/Spinning/OverFury/승인 패링 | .90 | .10s |
| 몬스터 준비/이동/발걸음 | .14 | .045s |
| 몬스터 공격/충격 | .65 | .12s |

몬스터는400cm 이내 기본 강도,400~3000cm 선형 감쇠,3000cm 이상 출력0이다. 짧은 타격 구분/먼 적에 의한 방해 방지가 선정 이유이며, 후속 체감 조정은 이 Controller 설정에 모은다. 엔진 유한 dynamic pulse가 종료 수명을 소유하고 다른 피드백을 일괄 정지시키지 않는다. 별도 게임플레이 상태/효과 정리 timer/Notify mutable state는 추가하지 않는다.

사용자의 “검증은 거치지 마”에 따라 build/PIE/자동 테스트/정적 검증/실기 진동 검사는 모두 실행하지 않았다. 적용 상태는 **메인 소스 반영·미빌드/미검증**이다. 기존 실행 중인 editor/DLL을 변경하거나 reload하지 않았으며 새 C++ 실행에는 빌드와 에디터 정상 재시작이 필요하다. 원본 입력/피해/AI/카메라/VFX/SFX 자산은 수정하지 않았다. 변경 목록과 정확한 재개는 Metadata/ControllerRumble_20261015/Implementation.json을 따른다.


## 2026-10-15 — ARCH-83/95 Spinning 표현 데이터 Main 완료

기존 Action/CombatEffect batch/receipt·정상/취소 cleanup을 그대로 사용했다. Spinning montage에서 KZ_Slash6쌍을 OverFury 전용 PS로 바꾸고 Charge3+2쌍을 조합했다. 원래176 효과·clock/GUID·donor montage/피해/HP/ST/입력/오디오·GAS 수명은 보존한다. 새 runtime file/class/manager/component/state0, 이번 Source/Config/DLL 저작·전달/build0이다. 실제 Main DevMap의 Khazan.CombatEffect.PIE(Spinning 선택+공유 회귀) 및 PlayerAttackCollision 두 suite가 Success이며 새 Main 모듈a8df6850...에 결속했다. HeinMach 자연 Spin/cleanup·충돌은 확인했고 broad suite의 이후 rear-Brutal fixture 실패는 보존했다. 타 세션 Source/진동/포탈 기능을 이 작업으로 복원하거나 별도 검증했다고 표현하지 않는다. 외관/TEMP/두 material만 다른 전용 PS와 최종 근거는 Art HEINMACH_BLUE_SPINNING_20261015.md 및 Metadata/HeinMachLookSpin_20261015/FinalVerification.json이다.

<!-- HeinMachLookSpin_20261015_complete -->
