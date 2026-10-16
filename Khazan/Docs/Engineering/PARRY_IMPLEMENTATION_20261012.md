# 2026-10-12 — ARCH-90: 가드 시작 직후 패링

## 적용 상태와 책임

사용자의 직접 구현 요청으로 기존 Guard Ability, ASC 요청, Combo 충돌과 MonsterSkillObject 적중 경로를 확장했다. 현재 구현본은 `C:/Users/user/Desktop/GitProject/Khazan_ParryWork_20261012/Khazan`에서 build와 실제 RHI PIE를 통과했다. **Main 반영은 두 기존 Guard 에셋의 Windows 공유 잠금 때문에 아직 완료하지 않았다.** 기존 Main 에디터를 제어하거나 종료하지 않았다.

새 runtime 파일·class·component·Manager·태그·GameplayEffect는 0개다. 기존 runtime 6개 파일과 DEV 전용 `KZParryPIETest.cpp` 1개가 변경 대상이다. Guard는 자신이 소유한 held 입력, GuardStateHandle과 활성화별 종료 시각으로 판정한다. ASC의 기존 BlueprintCallable `TryGuardHit(float, AActor*)`는 유지하고, native 적중 생산자만 성공 패링 여부를 추가로 받는다. 애니메이션이나 캐릭터 bool에 공유 상태를 복제하지 않는다.

## 실제 판정과 수명

- Guard 활성화가 Guard GE와 이동 제약을 취득하면 `[활성화 시각, 활성화 시각 + ParryWindowSeconds)`를 연다. 이동 중 Start 모션을 생략해도 창은 열린다.
- held 입력·유효한 자기 Guard GE·생존 HP·공격 출처가 필요하다. 전방 2D 반공간의 blockable 공격만 패링한다. 출처 없는 기존 native 호출은 일반 Guard로 남는다. 후방, unblockable, 음수/비유한 피해와 부족한 비용은 성공하지 않는다.
- Parry 창 안의 독립된 연타는 각각 패링할 수 있다. 같은 HitGroup은 생산자의 기존 소비 기록으로 1회만 처리한다. 패링 성공 모션이나 유지 가드로 창을 다시 열지 않는다.
- 패링은 HP 피해를 막고 incoming stamina damage의 절반을 Guard 비용으로 지불한다. 해당 비용이 충분하면 원래 일반 가드 비용보다 적은 ST로도 성공할 수 있다. HP 공격의 ST 피해가 0인 경우에도 패링할 수 있다.
- 성공 결과를 비용 확정 직후 생산자에게 반환한다. 일반 Guard 사운드를 중복 재생하지 않는다. 기존 `AKZMonster::ReportAttackParried`가 몬스터 Definition의 피해, 고갈 정책과 활성 Pattern의 `Parried` 분기를 처리한다. 보스의 모든 공격을 무조건 취소하지 않는다.
- 앞/좌측 공격은 `Parry_L`, 나머지 전방은 `Parry_R`를 재생한다. Release, Cancel, 사망 및 UnPossess의 기존 cleanup에서 Guard handle과 패링 창을 함께 해제한다. GT에서 ASC·Actor·Montage Task를 사용하며 worker 접근은 추가하지 않았다.
- 성공 이펙트는 기존 `Weapon_R` 접촉 위치에 world scale 1로 생성한다. 회전·scale을 absolute로 유지하고 0.06초 후 world transform을 보존하여 detach한다. 이는 원본 impact point writer를 복원한 것이 아니라 기존 소켓을 사용하는 표현 adapter다. 이미 승인한 finite flash와 사운드는 자연 종료한다. 약한 component callback은 component가 없어지면 호출되지 않는다.

## 값의 출처

원본 JSON 루트: `Saved/Extracted/InGame_Playback_20261002/Metadata/BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/Guard/`. 파일 SHA와 정확한 property는 `Metadata/Parry_20261012/OriginalEvidence.json`에 보존했다.

| 값 | 구분·근거·적용 조건 |
| --- | --- |
| 원시 JustGuard `[0, 0.292)`초 | 직접 확인: `AC_Kazan_DualAxeSword_Com_Guard_Start.Properties.Notifies[3]`의 BeginJustGuard/Duration/EndJustGuard. 원시 애니메이션 시간이며 그대로 실제 초라고 주장하지 않는다. |
| 기본 창 `0.146`초 | 원작 기반 계산: 현재 `Metadata/InGamePlayback_20261002/PlaybackPlan.json`의 GuardStart `inverse_map [t_current,t_source]`에 source 0.292를 보간한다. current Start는 0.25초이다. 별도의 source Dilation을 중복 적용하지 않는다. |
| 비용 배율 `0.5` | 직접 확인: `SB_Kazan_DualAxeSword_Com_Guard_Normal_New.GuardSkillInfo.JustGuardReduseStaminaPowerRate`. 기존 회복 지연 0.5초는 유지한다. |
| 몬스터 패링 ST 피해 `5` | 기존 사용자 프로젝트 결정. 현재 각 Definition의 `ParryStaminaDamage`를 그대로 소비한다. 원본 `JustGuardStaminaAttackPower=14`로 교체하지 않았으며 5를 원본 수치라고 표현하지 않는다. |
| 성공 모션 22/60초 | 원작 기반 계산: Just_L/R AC `DilationCurve.DilationAnimPositions` 31개와 `DilationSequenceLength=0.36330757`을 반영한 포즈 시간축을 60Hz의 22 frame으로 한 번만 bake. segment/task/RateScale=1. |
| InputEnd 약 0.271796초 | 원작 기반 계산: 원시 cancel notify 0.405999 / 0.4059992초를 동일한 dilation 위치 샘플로 변환했다. 좌/우 정확한 값은 Author01에 있다. |
| detach `0.06`초 | 직접 확인: `PP_Damage_Spray.NewExtraData[7]`, `bHitAttach=true`, `DetachAfterTime=0.06`, `bAbsoluteRotation=true`. |

현재 Normal_Start는 원본 일반 Guard 시작이며, 해당 source skill의 `bEnableJustGuardAtStart=false`와 구분한다. 사용자의 “가드를 시작한 일정 타이밍” 요구로 Normal Guard 활성화에 이전 JustGuard 창을 연결한 프로젝트 정책이다. 원본 Normal Guard가 이미 패링이었다고 주장하지 않는다. 기존 Start 길이·InputEnd와 입력 키는 바꾸지 않았다.

## 에디터 설정과 에셋

`/Game/Bluprints/AbilitySystem/Abilities/Player/Guard/GA_Player_Guard` Class Defaults의 `KZ | Guard | Parry`: Window Seconds, Stamina Damage Scale, Impact Effect, Effect Socket, Effect Detach Seconds, Sound를 조정할 수 있다. 기존 `AM_DAS_Player_Guard`의 5개 재생 segment에 `Parry_L/R` 2개를 뒤에 추가한다. original composite의 Just_L는 `Def_JustGuard_R`, Just_R는 `Def_JustGuard_L`를 참조하므로 이름만 보고 좌/우 raw clip을 선택하지 않았다.

기존 5개 segment와 notify는 saved readback에서 동일했다. Montage refresh가 경계의 `Suc_R` 파생 link cache를 앞 segment로 재연결한 차이 1개는 `SavedAudit02.derived_section_cache_changes`에 명시했다. 절대 section 시각·이름·Next 및 실제 재생 segment는 변하지 않았고 일반 Guard PIE가 성공했다. Author01의 original_sections/original_notifies 리스트는 append 시 같은 리스트를 참조한 보고서 결함이 있으므로, 보존 비교는 변경 전 `Probe01/GuardMontageBefore.t3d`를 기준으로 한다.

모션·이펙트·알파 복원과 원본 사운드의 정확한 출처는 `Docs/Art/PLAYER_PARRY_SOURCE_20261012.md`를 따른다. 기존 Audio Notify와 공유 VFX 원본은 수정하지 않았다.

## 검증과 정확한 재개

`Metadata/Parry_20261012`의 Build07, PIE02, GuardRegression01, CollisionRegression01 및 SavedAudit02가 성공했다. 실제 melee/field sweep 15개 상황, 몬스터 6개 Definition의 패링 ST 소비, 고갈·좌측 모션·비용·중복·창 재개 금지·Release/Cancel/UnPossess를 검사했다. 일반 Guard 및 기존 PlayerAttackCollision의 실제 회귀도 성공했다. private native 모듈 SHA는 각 Driver.json에 기록했다. 알파의 최종 화면 검수는 Art 문서의 후속 결과를 따른다.

재개 시 먼저 `Scripts/Engineering/deliver_player_parry_20261012.py preflight`로 현재 Main SHA/Windows 잠금을 다시 확인한다. 충돌이 없고 기존 Main 에디터가 저장 후 종료되어 잠금이 풀리면 `deliver`로 정확한 Source 7개/asset 13개를 복사한다. Main Config·uproject·Plugins·private DLL은 복사하지 않는다. 동시 작업이 대상 Source/asset을 바꿨으면 과거 준비본으로 덮어쓰지 않고 그 변경을 합친 뒤 재검증한다. 새 Main native suffix build와 fresh Main Parry/Guard/Collision PIE, saved audit가 통과한 실제 결과를 추가해야 Main 완료다. `stage`나 전체 author/import를 재실행하지 않는다.


## 2026-10-12 — 패링 최종 준비본 검증 확정 / Main 2개 잠금 유지

최종 Build08/PIE03(15 case 및 6종 Definition)/SavedAudit03/AlphaPreview07는 Exit0·passed다. native 실제 loaded module SHA는 PreparedVerification.json에 있고 현재 준비 Source7은 Build08 input과 동일하다. Gameplay 제품 Source6은 앞서 성공한 GuardRegression01/CollisionRegression01과 같은 코드다. source MI base-property overrides가 복원된 saved reload, DefaultParticle ellipse power2와 .04 UV/1.25px edge 연결을 확인했다. 실제 game viewport의 .13/.24초 효과 및 dark RHI burst를 직접 열어 원판·불투명 card 경계가 없음을 확인했다. Source shader/pixel 완전 일치와 실제 스피커 출력/Shipping/network 검증을 완료한 것은 아니다.

**Main product Source/package 변경0, 적용 완료가 아니다.** 마지막 preflight는 대상 SHA 충돌0·GA_Player_Guard/AM_DAS_Player_Guard의 Windows error32 2개다. 기존 Main editor PID19752가 계속 실행 중이다. 사용자에게 작업 저장 후 종료 상태만 요청했고 에디터를 임의로 종료하거나 잠금 handle을 강제로 닫지 않았다. exact resume는 Metadata/Parry_20261012/ResumeState.json, review diff는 PreparedSource.patch다. 잠금 해제 이후 해당 Source7/asset13만 반영하고 fresh Main build/PIE/audit를 추가한다. 전체 저작/추출과 과거 DLL 복원은 반복하지 않는다.


## 2026-10-12T08:17:34+09:00 — ARCH-90 패링 Main 적용·fresh 검증 완료

이전 준비본/Main 잠금 대기는 패링 범위에서 해소됐다. Main Source7(runtime6/DEV1)/package13(기존2/신규11)을 SHA 확인·백업 후 전달했다. 현재 전체 Main Source/Config로 MainBuild02가 성공한 뒤 일반 stock build가 현재 모듈 UnrealEditor-Khazan.dll을 선택했다. 이를 과거 suffix로 되돌리지 않고 현재 모듈에서도 다시 검증했으며 actual loaded DLL과 동일한 Source/13 asset SHA가 FinalVerification.json에 결속됐다. MainBuild01은 copy2의 과거 mtime 때문에 구 UHT PROLOG13/BODY16을 재사용하여 실패했다. 두 전달 헤더의 시각만 갱신해 PROLOG15/BODY18을 생성했고 제품 코드 내용은 바꾸지 않았다. 후속 전달 도구는 현재 write time을 사용한다.

새 MainPIE02의 Parry15개 상황/6종 Definition 소비·고갈·비용·연타·이동 Guard·좌측 response·release/cancel/UnPossess, 기존 Guard와 PlayerAttackCollision 회귀가 모두 성공했다. MainSavedAudit02는 저장0으로 설정/원본 5 playback segment·notify/7 section/source tag를 reload 검사했다. 실제 .13/.24초 화면에서 모션/weapon contact flash/연속 alpha를 직접 검수했다. 정상 가드 후 성공으로 창을 다시 열지 않으며 전방 blockable 공격만 패링한다. 기본 .146초는 기존 source→current inverse_map 계산, 비용 .5와 detach .06초는 source 값, 몬스터 ST 피해는 기존 Definition 사용자 결정이다.

이후 혈액 작업의 KZMonster runtime2/기존 DEV2와 모든 다른 Source/Config를 보존했다. 사용자/foreign editor 제어0·private DLL 복원0·Audio Notify 수정0이다. 초기 RHI에 GPU memory budget/낮은 FPS 표시가 관측됐으며 이번 fixed-step 기능 검사로 성능을 검증했다고 주장하지 않는다. 실제 스피커 출력(-nosound), 원작 shader/pixel/impact-point 완전 일치와 Shipping/network는 미확인이다. 필수 잔여0이며 최신 결과는 Metadata/Parry_20261012/FinalVerification.json과 ResumeState.json을 따른다. 과거 전체 author/추출/옛 alias를 다시 적용하지 않는다.


## 2026-10-13 — ARCH-95 패링 성공 카메라 적용·검증 / 외관 최종 일치 미확정

기존 KZGuardAbility의 성공 분기에 ParryCameraShake 설정과 local controller ClientStartCameraShake를 추가했다. camera modifier가 finite 수명/fade를 소유한다. runtime C++ 변경은 기존 header/cpp2개, 새 runtime 파일/class/component/tag0개다. ASC의 피해·비용·입력·창·몽타주·몬스터 결과를 재구현하지 않았다. 기존 DEV Parry 테스트에 승인 성공 전용 camera/실제 FOV 변화/만료와 template·개별 입자 값 진단을 추가했다.

source Just_L composite xxCameraMod_Shake_0의 Duration .35907653s, FadeIn/FadeOut.BlendTime .17953826s, LocOscillation.Y amplitude -100 × FinalScale .1=-10cm, FOV amplitude3 × .1=.3deg, raw frequency25, offsetzero를 엔진 LegacyCameraShake BP에 연결했다. frequency25를25Hz라고 표현하지 않는다. 원작 camera stack/timebase 및 오른쪽 원본 동일값은 미확인이다. single_instance는 프로젝트 adapter다. BP 경로는 PlayerParry/Reference/BP_Parry_SourceCameraShake다.

Build01/02/03는 성공했다. current 다른 Main build의 manifest를 과거 suffix로 복원하지 않았다. 최신 Native14의 actual loaded module은 UnrealEditor-Khazan-2026101354.dll(SHA321fecc91080e22eb251465f1f74b5dbedb6bae2fb514f5e73e36088f06ef6d5)이며17개 melee/field/lifetime/빠른release·6종Definition·HP/ST·dedup·고갈·cancel/unpossess·성공 전용 camera/FOV·만료 검사는 통과했다. 외관 합격과 component/입자 생성 성공을 구분한다. Shader02/저장 readback은 새 camera/PS 참조와 Player ImpactEffect=None을 확인했다. CurrentVerification.json에 Source3/asset18 SHA·보존 대상·actual native proof를 결속했다. 기존 attack contact/혈액/피격 VFX 제거3개의 SHA는 동일했다.

Native10은 다른 RHI 실행과 겹쳐180s QA timeout으로 끝났다. Native11–14는 통과했으며 QA driver에서 owned process의 Lumen atlas/VSM page budget만 임시 축소해 재현 가능한 검사 비용을 낮췄다. Project Settings 저장/다른 process 제어는 하지 않았다. Native07의 shader sampler 오류 후 정리한20316은 이 작업의 Launch.json으로 식별한 owned process뿐이다.

Art 결과/임시 shader 수치·source routing 차이·미확정 외관은 PLAYER_PARRY_SOURCE 최신 절과 Art continuity를 따른다. 현재 접촉 광/굴절/카메라와 alpha 개선은 적용됐지만 실제 HeinMach의 사진과 동일한 broad halo 외관까지 완료로 기록하지 않는다. 원작 shader/GPU/impact writer pixel parity와 Shipping/network/성능은 미확인이다. 재개 시 현재 Source/BP/manifest를 먼저 확인하고 과거 full author/전체 import/DLL 복원을 반복하지 않는다.

## 2026-10-13 패링 디스토션·카메라 가시성 Main 후속 검증
기존 UKZGuardAbility::TryGuardHit 성공 분기와 local PlayerController의 카메라 피드백을 보완했다. Guard GA가 붉은·보라 파티클 PP와 기존 카메라 BP를 계속 참조하고, 새 화면 후처리 M_Parry_ScreenRadialBlur도 참조한다. 성공한 패링에서만 일시적인 엔진 APostProcessVolume을 생성해 충돌 없이 화면 굴절 재질을 적용하고 .46745299초(원작 .16745299초 유지 + .3초 fadeout 계산) 후 자동 만료한다. 새 runtime class/component는 없다. ClientStartCameraShake 배율 3은 원작 직접값이 아닌 체감 가시성용 임시 튜닝이며, 원작 BP의 duration .35907653초/fade .17953826초와 원본 -10cm/.3도는 유지했다. 후처리 priority 100과 재질 UV 배율 .12 역시 임시 기술/가시성 설정이다. 일반 Guard·피격에는 전용 화면/카메라 효과가 생성되지 않는다. KZAnimNotify_CombatEffect.cpp는 범용 애니메이션 파티클 통로이므로 변경하지 않았다.

Main build HeinCameraBuild03 성공. 실제 로드된 Main UnrealEditor-Khazan-731310.dll SHA fa63a0dd8ca0ca50b03adb2b041bb114e9423dbfc3b06f5e7681f1150c33cc31로 HeinMach RHI의 Khazan.Parry.PIE 17/17 성공, 저장 package 0. EarlyMelee 카메라 출력은 최대 위치 29.1216cm/FOV .87365도 변화했고 정상 Guard는 둘 다 0이다. 승인된 패링만 카메라와 화면 volume 활성, 만료 후 없음도 검증했다. QA 촬영은 기록된 HeinMach scene-look 카메라/PlayerStart 위치를 사용했고 사용자의 일반 플레이 카메라 체감 및 Shipping/network/performance 검증을 대신하지 않는다. 사진의 넓은 보라 광막 외관은 여전히 미완료다. 증거·현재 hash·원작 대비 임시값은 Metadata/ParryPhoto_20261013/VisibilityFollowupVerification.json에 있다.

## 2026-10-14 — 원본 JustGuard 후처리 값과 저장된 Guard 효과 연결

UKZGuardAbility::TryGuardHit의 기존 성공 분기와 일시적 APostProcessVolume에 원본 CPP_PC_JustGuard_C.Settings의 SceneFringeIntensity=1.5, ChromaticAberrationStartOffset=.25 및 각 override를 추가했다. 수치는 Metadata/ParryVFXRebuild_20261013/OriginalCPP의 해당 직접 field 값이다. 기존 패링 전용 SceneTexture radial blur, 카메라 shake, 성공 1회 실행/만료 구조는 유지했다. 범용 KZAnimNotify_CombatEffect.cpp와 Guard 실패·일반 방어의 효과 경로는 수정하지 않았다. CPP 원본 xxPostprocessVol의 .05초 blend-in/.25초 blend-out은 현행 radial volume 수명과 완전히 같지 않아 원작 시간축 동일성은 미확인이다.

Main GA_Player_Guard.ParryImpactEffect를 기존 PP_Player_Parry_Reference에서 새 PP_Player_JustGuard_Halo로 저장했다. ParryCameraShake와 ParryScreenDistortion 참조는 보존했다. Main 저장 readback은 Metadata/ParryPhoto_20261013/JustGuardMainRHI01/SavedReadback.json, 변경 전 Guard backup은 JustGuardBindMain01/GA_Player_Guard_Before.uasset이다. 파일 잠금이 풀린 뒤 원본 SHA를 대조해 저장했으며 현재 메인 에셋에 반영됐다.

실제로 로드된 Main 모듈 UnrealEditor-Khazan-2026101401.dll SHA 58cf48aae3170eb3fbef996bf69d03ec423bdb4085de49f7072ef8801ea3a85d로 HeinMach D3D12 Khazan.Parry.PIE 17/17 통과, 테스트 저장 package 0이다. EarlyMelee에는 효과 1회, 일반/불가 방어에는 전용 효과 0회이며 카메라와 화면 후처리는 성공에만 발생했다. 실제 emitter 위치 X=12117.961,Y=13905.011,Z=290.290와 flare 입자 Active=1을 로그로 확인했다. 별도 새 runtime class/component는 없다. 화면 외관과 원본 셰이더 미확인 범위는 Art PLAYER_PARRY_SOURCE 최신 절과 Metadata/ParryVFXRebuild_20261013/FinalVerification.json을 따른다.


## 2026-10-14 — ARCH-99 패링 카메라 교체·내려찍기 디스토션 재사용

기존 UKZGuardAbility의 승인된 TryGuardHit 분기에서 ParryCameraShake BP/ClientStartCameraShake 호출을 제거하고 로컬 UKZCombatCameraModifier 이벤트로 대체했다. 원본 AC_Kazan_DualAxeSword_Com_Guard_Suc_Just_L의 xxCameraMod_Shake: Y=-100 cm/25 Hz, FOV=3도/25 Hz, FinalScale=.1, 구간 .35907653 s, FadeIn/Out=.17953826 s를 사용한다. 수치 출처는 Metadata/ParryPhoto_20261013/VisibilityFollowupVerification.json의 source_metadata와 원본 export다. 유효 구간 .17953827 s+fade-out .17953826 s는 합계 .35907653 s를 맞춘 계산이다. 가시성 gain2와 원본 0축 교차 움직임6%는 원작값이 아닌 TEMP이며 Guard 설정과 modifier에 모았다.

패링 성공 시 기존 공중 내려찍기 Niagara NS_Player_Plunge_ParringDistort를 접촉점에서 카메라 방향으로 80 cm 당긴 곳에 scale .4로 재생한다. User.KZFloorNormal과 컴포넌트 전방을 카메라 방향으로 설정해 카메라 쪽을 향하게 했다. 이 위치/scale/.25 s tail은 어시스턴트 TEMP 표현값이다. 기존 JustGuard halo 및 일시적 radial blur/SceneFringe는 유지한다. 이전 Deactivate만으로 Niagara가 다음 방어까지 활성으로 남은 실제 PIE 오류를 DeactivateImmediate+DestroyComponent 타이머로 수정했다. 성공하지 않은 가드에서는 새 효과가 실행되지 않는다.

Main Build07과 최신 로드 DLL SHA, HeinMach RHI 캡처 및 Main RHI 17개 실제 패링/정상 방어/수명 회귀 성공을 Metadata/GiantCamera_20261014/FinalVerification.json에 기록했다. 현재 프로젝트의 Guard asset 저장 readback에서 새 Niagara binding을 확인했다. 원본 카메라 modifier 구현/셰이더가 없어 화면 픽셀·프레임 완전 일치는 미확인이다.


## 2026-10-15 — 현재 패링 VFX 교체와 선형 카메라 힘 적용 완료

사용자 직접 수정 요청으로 이전 ParryImpactEffect/halo, 바닥용 plunge Niagara 연결, ParryScreenDistortion 후처리 volume 생성 경로를 제거했다. 기존 Guard 승인/성공 좌우 모션/스태미너 비용/공격자 알림은 유지한다. `ParryBillboardDistortion`은 `/Game/VFX/03_SlashHit/KZ_Parring_Distort`로 저장했다. XY는 두 actor 중점, Z는 실제 `Bip001-Spine2` 흉부 높이의 평균이며 카메라를 향하게 한다. camera pull 상수와 바닥 normal parameter는 사용하지 않는다. Guard montage의 남은 particle/Niagara Notify 연결은 0이다.

기존 CombatEffect SpawnComponent를 재사용하는 editor Instanced `ParryBrutalEffects`에 현재 BrutalFront의 접촉 효과 `PP_AtkEx_Grapple_01`, `PP_Dmg_Blood_Trail_Sub`, `PP_AtkEx_Grapple_02` 3개를 복사해 승인된 패링에 함께 재생한다. source_notify/source_package/source_field, parameter/scale/원본 duration은 Author02에 기록했다. 원본 duration은 WindowEndTime−WindowStartTime 계산이며 방출 정지 뒤 기존 alpha/lifetime drain을 보존한다. 요청 Niagara native scale1, 방출 종료 .5s/최대 수명2.5s는 TEMP 유한 수명 정책으로 조절 가능하다. 실제 Guard BP와 두 giant BP 총3 package만 이 작업에서 저장했다. 범용 CombatEffect runtime/원래 Brutal particle asset은 교체하지 않았다.

모든 현행 camera shake producer(giant source notify 86창 및 Guard 성공)는 기존 KZCombatCameraModifier의 선형 방향 힘/복원으로 소비한다. 최소 상승 .08s/복원 .16s/최대 반복4Hz는 사용자가 자연스러운 선정값을 허용한 TEMP이다. 원본 amplitude/FOV/scale/거리 attenuation/window는 유지하며, 반복 pulse는 반대 방향으로 되풀이한다. 취소/Notify End/mesh 소멸에서는 마지막 실제 화면 기여(거리 배율 포함)를 저장해 그 위치에서 선형으로 복원한다. 독립 이벤트의 중첩과 유한 cleanup을 유지하며 gameplay RNG를 소비하지 않는다.

FinalRHI01은 실제 D3D12 패링17/17 Success와 위치/모션/tail3장, 정상 가드/취소/자원/소진 회귀를 포함한다. Physics03의 LinearCamera4 및 GiantCamera4는 Success(같은 suite의 당시 AI 실패와 구분). 신규 AI만 후속 수정됐으며 각 실제 로드 DLL hash는 최종 receipt의 runs에 별도로 기록했다. 최신 원작 shader pixel 일치/Shipping 성능을 검증한 것으로 표현하지 않는다. 정본: `Metadata/CombatFeel_20261015/FinalVerification.json`. Art 외관은 PLAYER_PARRY_SOURCE_20261012.md의 같은 날짜 최신 절.

