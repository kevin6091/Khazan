# Monster 행동·공격 VFX 실행 정본

## 2026-10-08 — ARCH-84 격리 구현 및 검증 계약

대상은 Swordsman, SwordShield, HeavySwordsman, HalberdElite, ApesStoneHandElite, Yetuga다. 사용자의 직접 부착·구현 요청에 따라 기존 GAS 실행 구조를 재사용한다. 이 절은 격리 구현 기록이며 Main 전달·실제 PIE 결과는 아래 날짜별 검증 절에서만 확정한다.

### 실제 소유자와 최소 확장

- `KZAnimNotifyState_MonsterVisual.h/.cpp` 두 runtime 파일은 저장된 이벤트 설정만 소유한다. 엔진 `NoMergeOnConcurrentPlay`와 실제 Notify instance ID로 Begin/Tick/End를 전달한다. 같은 Sequence를 여러 캐릭터가 재생해도 Notify 객체에 실행 상태를 기록하지 않는다.
- 기존 `KZMonster`가 실제 Mesh/AnimInstance/Notify ID별 파티클·데칼·트레일·MID와 원래 material/overlay 복구 수명을 소유한다. 취소, 애니메이션 종료, UnPossess, EndPlay에서 자기 자원만 정리한다. 전역 Tick, 별도 VFX manager/component, 전투 상태 사본은 없다.
- 기존 `KZAnimNotify_CombatEffect`의 stateless 생성 경로를 공유한다. 기존 `KZActionAbility`는 플레이어의 승인·실제 적중·자원 영수증·cleanup을 계속 소유한다. Combo/ASC/AI 실행 정책을 VFX로 대체하지 않는다.
- 기존 `CharacterDefinition.StaminaSettings.DeathPresentationMontage` optional field와 기존 Monster의 사망 표현 경로만 확장한다. ASC Dead/HP 결과 정책은 유지한다. 완료된 lethal Brutal 반응에는 별도 Death montage를 중복 재생하지 않는다.
- `bAnimationContextBoundary`는 clip 전체 길이의 기술적 수명 경계다. 원작 추가 이펙트나 gameplay 상태가 아니다. 짧은 Notify가 끝났어도 원작 `DestroyOnAnimEnd`에 해당하는 tail은 실제 재생 context가 끝날 때 정리한다.

### 데이터·시간·수치의 출처

원본 및 현재 clip 대응은 `Metadata/MonsterVFX_20261008/HumanOriginal`와 `ApesYetugaOriginal`에 보존한다. 계획과 정확한 field 값은 `Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json`을 따른다. 원본 LinkValue/Trigger offset을 현재 baked clip 시간으로 한 번만 변환하며 UE float32 저장값을 다시 읽는다. 기존 animation raw channels, curves, root 설정, sync markers, notify GUID와 시간은 보존 대상이다.

857개 현재 Sequence를 조사한 계획은 원본 이벤트 occurrence 3071개, 지원 재생 구간 2855개, 수정할 Sequence 487개와 기술적 경계 487개다. 지원 구간은 Particle 2783, Decal 62, Trail 4, Apes material 5, Rim 1이다. 인간 629개와 동물 library 212개 및 동물 현재 gameplay 사본 16개를 포함한다. 실제 저장 수량은 Authoring/readback report가 기준이다.

Yetuga Trail은 원본 `Root`, Scale `(2.8,2.8,1.5)`, Intensity `1`, BlendTime `.1s`와 원본 static mesh를 사용한다. Apes의 `ExecutionOffset_radius`는 원본 `Bip001-Spine1` 위치와 Execution/ExecutionO 곡선을 실제 mesh MID에 전달한다. Rim은 원본 Duration `1.2s`, BlendIn `0`, BlendOut `1.2s`, RGB `(2,0,0)`을 사용한다. 재현용 Fresnel exponent `5`는 assistant 임시 재질 값이다. 각 원본 package/field/raw 값과 SHA는 계획·원본 manifest·adapter map에 있다.

### 조건과 미확인 범위

- `bOnAttackSuccessed` 조건은 실제 적중 producer가 승인해야 한다. 애니메이션이 재생됐다는 이유로 피·적중 효과를 무조건 재생하거나 피해를 만들어내지 않는다. 최종 계획의 조건 구간은 43개다.
- Camera 43, DeepSnow 172, ChangeStatus 1은 일반 파티클 재생 구간으로 변조하지 않는다. 기존 snow 표현 소유자를 유지하며 원작 custom deformation/status/camera 전체 복원을 완료했다고 기록하지 않는다.
- Yetuga Prop 3개는 다른 rock skeleton의 source animation이다. 자료·저장 데이터 범위와 캐릭터 몸체의 실제 재생/별도 투사체 owner 구현을 구분한다. Apes/Yetuga autonomous AI는 이 작업의 구현 결과가 아니다.
- CorrectionInfos 52 occurrence에 원본 CorrectionBoneName이 없으므로 raw 자료를 보존하며 임의 Root anchor를 원작 확정값으로 넣지 않는다.
- 원본 NI의 cooked editor graph/VM 및 User parameter 소비 연결은 확보되지 않았다. source renderer와 geometry/material/defaults를 이용한 Cascade adapter이며 원본 Niagara의 완전한 graph 복원으로 설명하지 않는다.
- 원본 source/default route의 불투명 정보 때문에 Swordsman 10개는 동일 가족·같은 공격의 원본 non-blood grounded dust route를 임시 사용한다. Yetuga Armageddon Start 데칼 1개는 같은 가족 Death의 확인된 재질을 임시 사용하며 무늬 동일성을 주장하지 않는다.
- Heavy Death의 source surface route는 material 3개와 명시적 null 5개다. null/default 및 지정되지 않은 표면은 데칼을 억제한다. 현행 ground trace adapter와 원작 native 표면 선택 대상의 일치 여부는 미확인이다.

### 검증과 재개 위치

현재 stock private cold build Attempt5는 exit 0이고 private/Main inputs hash 불변이다. author는 Main/shared editor 쓰기를 차단하며 대상 경로 resolve, 사전 SHA, backup과 partial-save journal을 사용한다. 새 저장 감사는 실제 object fields/time와 raw 모델 fingerprint를 검사한다. 실제 RHI의 `Khazan.MonsterVisual.PIE`와 플레이어 `Khazan.CombatEffect.PIE`, PNG 육안 검증 뒤 Main 선택 전달한다. commandlet exit 0만으로 report 성공을 선언하지 않는다.

재개는 `ENGINEERING_WORK_CONTINUITY.md` 최신 MonsterVFX 절과 `Saved/ImportReports/MonsterVFX_20261008`의 실제 report를 먼저 확인한다. partial author 실패 시 journal과 backup SHA를 확인하고, 중복 author를 무조건 재실행하지 않는다.


## 2026-10-08 22:26 KST — Private 저장 검증 완료 및 Notify 기본 매칭 계약 보충

이 절은 `Khazan_MonsterVFXWork_20261008/Khazan`의 실제 Source·author·fresh saved 결과다. Main 전달 완료 기록이 아니다. 위 최초 절의 “NoMergeOnConcurrentPlay 사용” 설명은 아래 기본 매칭 정책으로 대체하며 과거 기록은 보존한다.

### 현재 확정한 Source·저장 데이터

- [Build/Attempt10/Exit.json](../../Saved/ImportReports/MonsterVFX_20261008/Build/Attempt10/Exit.json): exit `0`, `11.015s`, private/Main Source·Config·uproject 입력 SHA 불변. 격리 DLL SHA는 `e1a308d862751001fd1b92f71abd0821c4828797201515bbd033162d78ad8ab0`이다. 두 신규 NotifyState runtime 파일과 기존 소유자의 작은 확장을 포함한 task Source 변경은 11개이며 새 VFX manager·AI 구조는 없다.
- [PrivateAuthoring.json](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/PrivateAuthoring.json): private author 통과, Sequence `487`, source visual State `2855` + 기술적 수명 경계 `487` = `3342`, Death montage/Definition 각 `6`, mutation journal `499`다. 원본 pose/curves/root 설정, 기존 notify GUID·시간·field, sync markers, Definition의 나머지 field를 보존했다.
- [SavedReadback.json](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json): 새 PID `20124`의 세 번째 fresh 감사 통과(`52.843s`는 작업 driver 관측). `487` Sequence·`3342` State·Death `6`의 저장 field/시간을 읽었고, 선택 `499`개 파일의 전후 SHA가 동일하다. 에셋 save/mutation은 모두 `0`이다.
- 위 author/saved가 공유하는 [PreparedPlaybackPlan.json](../../Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json) SHA는 `638c64d7e1873d2e6cd2a8d6b73f0feffaf3c2140d4a878fe1f7545e2358d793`이다. typed State/Effect readback과 원본 package·field·raw 값·변환식은 이 계획 및 journal을 따른다.

### Notify 매칭과 실행 수명 — 최신 정책

`NotifyStateBehaviorFlags`는 엔진 기본값 `0`이고 `NoMergeOnConcurrentPlay` 비트는 끈다. fresh saved `3342`개가 모두 `0`임을 실제 확인했다. 이 값은 원작 gameplay 수치가 아니라 UE 5.8의 실행 매칭 정책이다. 현행 constructor는 별도 비트를 추가하지 않는다.

엔진 `AnimInstance.cpp`의 source-instance matching 분기는 NoMerge 설정 시 Montage/AssetPlayer context ID를 요구한다. context가 없는 BlendSpace/SingleNode 경로에서 이 비트를 강제하면 기존 State를 매칭하지 못해 Begin/End가 매 프레임 반복될 수 있으므로 기본 매칭을 사용한다. 실제 자원은 Monster별 Mesh·AnimInstance·Notify ID receipt가 소유하며 Notify UObject에 가변 실행 상태를 두지 않는다. 서로 다른 Actor의 동일 clip 재생은 각 Actor 영수증으로 분리한다. **한 Actor의 동일 AnimInstance에서 같은 Sequence의 같은 notify를 동시에 중첩 재생할 때는 엔진 기본 매칭이 합칠 수 있으며, 그러한 완전 독립 수명을 보장하지 않는다.**

clip 수명 경계는 실제 source sequence/Montage·AssetPlayer context를 이용한다. 일반 종료·취소·UnPossess·EndPlay에서 자기 자원만 정리한다. 자연 종료된 사망/완료 lethal paired Brutal의 execution material은 실제 종료 owner와 corpse 수명으로 남길 수 있다. 살아남은 paired Brutal victim에는 사망용 원본 dissolve를 적용하지 않으며 이 조건은 프로젝트 피해 결과 계약이다. 임의 시간 timer로 사망이나 이펙트 수명을 대신하지 않는다.

### float 시간 및 fresh load 비교의 정확한 범위

- 시작 시간은 `AnimationLibrary.get_anim_notify_event_trigger_time()`의 native float 결과를 authored float32와 비교한다. Duration은 `get_anim_notify_event_duration()`의 실제 저장 float와 `f32(end-start)`를 비교한다. 보호된 `LinkValue`를 메모리로 직접 읽거나 구조체 배치를 가정하지 않는다.
- Python에서 보호된 EndLink는 UE `export_text()`의 소수 6자리 표현을 읽는다. 따라서 끝점 검사는 `f32(round(end,6))`의 텍스트 경계이고 정확한 native end-link 비트 비교로 표현하지 않는다. 원본 offset은 LinkValue에 한 번만 더한 saved 시간 변환을 사용하며 현재 clip 길이에 맞춰 늘리지 않는다.
- rich curve export가 기본 `Time=0`/`Value=0`을 생략하는 것을 parser가 복원한다. key 수·시간·값·tangent/weight/interpolation/extrapolation을 유지하되 float text precision의 한계를 구분한다. raw DataModel T3D와 설정 fingerprint 보존은 reflected 데이터 검증이며 전체 압축 animation buffer의 비트 일치 주장과 다르다.
- UE montage `PostLoad`가 채우는 `LinkedMontage/LinkedSequence/SegmentIndex/SegmentBeginTime/SegmentLength/CachedLinkMethod`만 파생 cache로 제외한다. section index·이름·시작 시간·slot·LinkMethod·Next·기타 metadata는 비교한다. Death `6`은 Default section 시작 `0`, slot `0`, `Next=None`, `enable_auto_blend_out=false`이며 기존 family Exhaustion montage의 blend 설정을 재사용한다. 이 blend 선택은 원작 death 수치 확인이 아닌 프로젝트 표현 adapter다.

### Apes 5.9999s와 curve 원본 — 재타이밍 아님

원본은 `Metadata/MonsterVFX_20261008/ApesYetugaOriginal/Manifest.json` 및 `Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/SourceMetadata.zip`의 `BBQ/Content/_Kazan_/Design/Monster/Apes/ApesStoneHand_E/Moving/Reaction` 아래 두 AC다. 시간 단위는 sequence-local 초, RateScale `1`, dilation 미적용이다.

| 원본/field | 직접 저장값과 적용 계산 |
| --- | --- |
| `AC_ApesStoneHand_E_DamFinalblow` Notifies `[0]/[1]`, export `[17]/[18]` | EndLink `6` + EndTriggerTimeOffset `-0.0001` = 종료 `5.9999s`. bone 창 시작 `-0.0001s`는 현재 clip의 `0s`로 자르고 scalar 창 시작은 `0.0001s`다. |
| 같은 AC `Exports[0].Properties.RawCurveData.FloatCurves[0].FloatCurve` (`execution`) | `(1s, 8.2644576e-05)`, `(6s, 999.9998)`; 마지막 key `6s`를 State 종료 시간에 맞춰 옮기지 않는다. |
| 같은 AC Notifies `[2]`, export `[19]`; `FloatCurves[1]` (`executionO`) | 창 종료 `5.959529s`(End offset `0`), key `(4s,-2.0715945e-05)`, `(6s,2000)` 그대로다. |
| `AC_ApesStoneHand_E_Die_F` Notifies `[0]/[1]`, export `[13]/[14]`; `FloatCurves[1]` (`execution`) | 동일 계산으로 종료 `5.9999s`; key `(0s,1)`, `(3s,800)`을 유지한다. |

DamFinalblow 원본 JSON SHA는 `754e522c3f468e0118b771c41bf974a50cc0973000858d6015ba2e276e008ba1`, Die_F는 `e73733e03236a6a0006872378cf3c443e89408aacc827c6fd9dfd236a023ecb9`다. scalar 값의 원작 물리 단위와 shader 공간 의미는 미확인이다. `ScalarParameterName=CurveName`, `Bip001-Spine1`의 world XYZ 전달 및 execution override shader는 공개된 프로젝트 adapter이며 원본 native shader의 완전 복원으로 기록하지 않는다.

현재 real-RHI `PrivateMonsterRuntimePIE/Attempt2`가 Build10으로 실행 중이다. 최종 native 성공·Player 회귀·PNG 확인·source/resource integrity 결속 → guarded prepare/apply → 새 Main read-only saved/native 검사 순서가 남았다. 이 추가 기록에서는 Main 에셋/Source/에디터를 조작하지 않았다.


<!-- MonsterVFX_ApesGrapple_Rim_PrivateCheckpoint_20261010 -->
## 2026-10-10 20:11 KST — Private alias 적용·Grapple 검증 정정·Rim 표적 재생, Main 전달 전

이 절은 앞선 paired execution 설명의 실제 적용 범위를 보충한다. task 범위는 runtime Source9 + DEV2, Sequence487/State3342(visual2855+수명 경계487)/Death presentation6, Art 후보457이다. Apes 현재 NONV3 alias 수정은 두 private Sequence의 State5에 한정했고 기존 원작 V3 첫5행, source/effect fields, raw pose/curve/time, 나머지497 author 파일과 original Main-before journal499를 보존했다. [Applied](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/ApesCurrentMaterialBindingRevision/Applied.json) 및 fresh [SavedReadback](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json)이 통과했다. schema SHA `58d4696c6b98900bcf6b380ea8d4049d48e7c1d8b3d39bd41c04b574f76e36cf`, 현재 plan SHA `aee394cf819993a74d7113b7b778638f69e5365faa46b585999dc36a15861bca`다.

### 실제 Grapple source와 실패를 분리

[PrivateMonsterRuntimePIE/Attempt3](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt3/Driver.json)는 exit0이지만 native/Driver failed였다. assertion20개는 paired terminal의 replacement-parent와 Execution 값 기대 두 종류였다. 현재 Apes `Damage_Grapple_Atk_01/_02/_B_01/_B_02` 및 각 InGame 사본에는 각각 원본 Particle4개, material notify0개가 있다. 원작 material State5는 `AC_ApesStoneHand_E_DamFinalblow`의3개와 `AC_ApesStoneHand_E_Die_F`의2개에만 존재한다. source package·export/notify field는 PreparedPlaybackPlan과 ApesYetugaOriginal Manifest를 따른다. **현재 paired Grapple에 FinalBlow dissolve가 재생된다고 설명하지 않는다.**

ordinary Apes Death는 Execution800/actual Consumers5를 종료와 재확인에서 관측했다. 이 검사를 paired terminal shader 유지의 실제 producer 검증으로 확대하지 않는다. 해당 producer가 없는 현행 경로에서 paired Execution retention은 미검증이며, QA의 잘못된 기대를 맞추기 위해 새 dissolve나 gameplay producer를 추가하지 않는다. Build13에서 보완한 것은 실제 source clip에 맞는 paired QA이고 게임 코드 추가 수정은 없다.

### Rim 실제 compatible component 검사와 시각 한계

[PrivateRimQA/Attempt2/Driver.json](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt2/Driver.json)은 실제 RHI 통과, PID29484/38.187s/exit0, package save0/asset mutation0/material fallback0이다. `Damage_Disease`의 source skeleton은 `SKEL_EN_C_I_Halberd_WeaponV2`로, body `SKEL_EN_C_M_HalberdV2`에 재생하지 않고 실제 BP의 호환 `EnemyWeapon_R`에서 재생했다. 실제 overlay MID 생성·weight 감쇠·자연 종료 baseline(null) 복원을 확인했다. 예를 들어 sequence0.170666s에서 weight0.857779, 1.186092s에서0.011590, 1.325060s에서0, 1.453943s 표본에서 baseline 복원이다. 이는 관측 표본이며 종료 시각을 새 gameplay 튜닝으로 변경한 값이 아니다.

원작 Rim Duration1.2s/BlendIn0/BlendOut1.2s/RGB(2,0,0) 및 기존 shader adapter는 유지한다. 위 표적 검사에서 실제 로드 DLL은 Build12의 `01932d7b…3727`이었다. Root가 PNG를 직접 봤지만 역광 때문에 red rim의 시각 강도는 확정하지 않았고 추가 시각 QA 중이다. runtime weight/cleanup 통과를 최종 visual pass나 원작 pixel parity로 기록하지 않는다.

[Build/Attempt13/Exit.json](../../Saved/ImportReports/MonsterVFX_20261008/Build/Attempt13/Exit.json)은16.422s/exit0, private/Main 입력 불변이며 현재 private DLL SHA는 `29bd3daf30f104afbc38d649bf330b07098827b3a547c6cd73d8e999e2b69a9b`다. 현재 `PrivateMonsterRuntimePIE/Attempt4`가 PID25160으로 실행 중이다. 전체 native 성공·Player 회귀·Rim 및 전체 PNG 검토·현재 source/resource integrity 결속·최신 Main 동시 변경 CAS/병합·guarded 전달·fresh Main 검사까지 남았다. **MonsterVFX Main은 아직 미전달이며 전체 성공/시각 완료로 기록하지 않는다.**


<!-- MonsterVFX_VictimRimBuild18_Checkpoint_20261010 -->
## 2026-10-10 21:17 KST — 피해자 Decal revision 계약·Editor 최초 Rim 준비·검증 경계

### Decal43의 실제 원본 근거와 새 프로젝트 정책

[VictimDecalPolicyRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VictimDecalPolicyRevision.json)은 Damage26+Death17 원본 Decal export의 source JSON/ZIP/member SHA와 property를 표적 확인했다. `bOnAttackSuccessed`는43개 모두 생략돼 있다. 생략으로 original CDO=false를 입증하지 않으며 native CDO 조건은 미확인이다. 기존 prepared plan의 Blood 이름 기반 true guard는 프로젝트가 추론한 조건이었다. 이를 피해자 Damage/Death source sequence가 원래 Decal timing window를 소유하는 명시적 프로젝트 표현 정책으로 대체했다. outgoing attack 성공을 victim 조건으로 쓰거나 fake hit·새 persistent bool/timer/getter를 추가하지 않았다.

probe PID29200은 저장0/전체499 SHA 불변, apply PID30084는 Sequence26 saves/Effect43 mutations/Main0으로 passed다. 수정 field는 `bOnAttackSuccessed=true→false` 하나뿐이며 전체 Effect/State readback, Notify GUID/시간, raw DataModel·pose/curves/settings와 whole-sequence before/after/saved T3D의 다른 내용은 보존했다. report SHA는 `9b3609b797c23f64cf66169515f1d456d9783b4ad522c39fab7e2231fe7516ec`; 다른473 author 파일도 불변이다. original PrivateAuthoring499/Main-before journal·PreparedPlaybackPlan·Apes Applied·ContentRebaseRevision을 다시 쓰지 않는다. saved/candidate/delivery/finalizer는 original proof 검증 후 정확한26 Sequence의 after SHA와43 bool readback을 별도 override로 소비해야 한다.

최신 [SavedReadback](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json), SHA `b6c3c8fda3dae75879bcd7d1b91743fe9e8445bc0cd2e9818ccb7b7e1b49d890`, PID6036은487 Sequence/3342 State/Death6·ContentRebase6 및 victim revision43/26 marker를 passed로 확인했다. 저장0/선택 bytes 불변이다. 이 결과를 이후 DLL의 native/RHI 완료 증거로 대신하지 않는다.

### Rim의 shader compilation 완료와 실제 화면

[Rim8](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt8/Driver.json)은 actual DLL16 `11dd0c914b84132f2785e274d70738f631b38d6de5b9e31040f4a08752e58805`에서63 captures/저장0/asset mutation0/material compile failures[]를 통과했다. 실제 BP_HalberdElite의 WeaponV2-compatible EnemyWeapon_R에서 원래 Damage_Disease를 재생했다. Root는 [PNG24](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt8/024_Halberd_Rim_Diagnostic_StatisticsSynced_SourceOverlay_WeaponFrontOblique.png)의 red Rim을 확인했다. 같은 actual MID/source RGB·weight에서 GetStatistics의 synchronous FinishCompilation 이후, explicit RecompileMaterial 전에 신호가 나타났다. 이후 원래 exposure의 PNG27도 red였다. 저장 graph/master/MI SHA는 불변이며 owner overlay/slot/disallow_nanite/camera 설정은 복원했다. 이는 Editor on-demand shader readiness 문제라는 추론을 지지하며 특정 shader resource의 이전 런타임 상태를 debugger로 읽은 증거는 아니다.

Root는 private `KZMonster::AcquireBinding`의 기존 첫 MID 생성 분기에만 `#if WITH_EDITOR Replacement->EnsureIsComplete(); #endif`를 추가했다. 기존 owner receipt·fade·종료/취소 cleanup과 source 수치는 유지하고 새 runtime 파일/manager를 만들지 않았다. cooked 경로에 Editor 동기 compile 호출을 넣지 않는다. Build17의 LNK1104는 별도 saved 프로세스의 DLL 파일 잠금 실패로 보존한다. 프로세스 종료 뒤 [Build18](../../Saved/ImportReports/MonsterVFX_20261008/Build/Attempt18/Exit.json)이 PID22032/5.234초/exit0·Main/private inputs 불변을 통과했고 DLL SHA는 `1506acfae8845cc87e8ada5cbe674d22dba2668a020bdfc366a2623c70576304`다. 이 DLL의 regular Rim9는 진단 compile API 없이 실행 중이며 최초 표시의 visual pass는 아직 없다.

### Yetuga와 전달 전 남은 검사

[Yetuga2](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt2/Driver.json)는 failed/38 captures/package0다. actual snow writer main/depth/shadow=false 및 Root PNG10의 dome 소실은 확인했지만 종료 후 Breath2/BodyDust1 active 표본으로 cleanup 검사가 실패했다. QA의1초 대기가 원본 finite Breath 최대3.5초보다 짧은 문제와 BodyDust lifetime/sentinel을 표적 조사 중이며 gameplay 수명 predicate를 바꾸지 않는다. 원본 lifetime을 반영한 QA 여유 보완 후 fresh actual RHI와 cleanup/Root PNG가 필요하다.

정확 재개는 Build18/current loaded-DLL·saved43/26 marker → regular Rim 최초 red 검증 → Yetuga 새 cleanup/시각 → current DLL full Monster native/Player 회귀 → original499/plan/Art457와 Main intake·ContentRebase6·Victim26 및 fresh supplemental SHA의 candidate integrity → closed Main census/current Source·Content·module CAS 선택 전달 → fresh Main saved/native/regular Rim/Yetuga/Root visual/finalizer다. MonsterVFX Main 전달0·사용자 Main PID9460 열린 상태라는 Root 관측을 유지한다. 진단 성공을 최종 Source 보완의 검증 완료로 승격하지 않는다.


<!-- MonsterVFX_RegularRim9_Positive_20261010 -->
## 2026-10-10 21:18 KST — Build18 일반 Rim 최초 표시 실제 통과·전체 검증 진행 중

앞선 checkpoint 직후 [PrivateRimQA Attempt9](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/Driver.json)가 passed로 종료했다. actual loaded DLL SHA는 `1506acfae8845cc87e8ada5cbe674d22dba2668a020bdfc366a2623c70576304`, diagnostic_mode=false, PNG30/package saves0/asset mutations0/material compile failures[]이며 [Exit](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/Exit.json)는62.594초/exit0이다. Driver SHA는 `cd5af174d284ec6e6696a31c313f4b8f5e673eaf43c816e13e7e344169365a0f`다. Root는 [Active03 Front PNG006](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/006_Halberd_Rim_Active_03_WeaponFrontOblique.png)와 [Active06 Front PNG009](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/009_Halberd_Rim_Active_06_WeaponFrontOblique.png)를 직접 보고 첫 표시의 강한 붉은 Rim을 확인했다. 별도 GetStatistics/RecompileMaterial/노출 변경 없이 기존 editor shader 준비 보완이 실제 첫 화면에서 작동했다. 원작 RGB/weight/시간·저장 shader asset을 변경한 결과가 아니다.

이 결과로 regular Rim의 최초 표시·fade/복원 검증은 통과했지만 MonsterVFX 전체/Main 전달 완료는 아니다. Root가 같은 Build18의 PrivateMonster full RHI6을 시작했고 Player 회귀 및 원본 lifetime에 맞춘 Yetuga cleanup/시각 재검증이 뒤따른다. 최종 candidate SHA 결속·closed Main CAS/guarded 전달·fresh Main saved/실제 RHI/Root visual/finalizer까지 앞 절의 재개 순서를 유지한다. Source/Art 후보는 Build18 이후 동일하고 이번 보충은 문서만 추가했다.


<!-- MonsterVFX_CurrentQAExternalB_Checkpoint_20261010 -->
## 2026-10-10 21:39 KST — current DLL 표적 검증과 실패 baseline의 분리

current Build18 DLL SHA는 `1506acfae8845cc87e8ada5cbe674d22dba2668a020bdfc366a2623c70576304`다. [Yetuga3](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt3/Driver.json)는 이 실제 loaded module로82.578초/104 captures/package0·asset mutation0, regular Rim9는 진단 compile API 없이 최초 표시/fade·baseline 복구를 passed로 확인했다. source 수명 predicate 변경 없이 원작 serialized lifetime6/7/6초에 QA scheduling margin1초만 더한 tail 관측이다. 원작 수치·계산 bound·QA 임시 여유를 혼합하지 않는다.

[Native6](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt6/Interruption.json)은387.719초 뒤 InterruptedKnownFailedCandidate로 중단했다. 시작 시 `Cant find InputAction for InputTag [Input.Action.B]` Error가 있었고 driver/full native Success 자료가 없으므로 부분 캡처를 전체 통과로 승격하지 않는다. 이는 최신 외부 Controller/Tag4 Source 연결에 대응하는 Input asset baseline이 아직 저장되지 않았던 시점의 실패이며 ExpectedError로 가리거나 Controller 동작을 바꾸지 않는다.

외부 [Authoring09](../../Metadata/BrutalInputDevMap_20261010/Authoring09.json)의5 unique 저장 에셋은 Main/private 공유 경로에서 exact SHA가 일치한다. Root의 새 Native7 session72778은 이 실제 baseline을 검증하는 실행 중 단계다. [DeliveryReadiness](../../Saved/ImportReports/MonsterVFX_20261008/DeliveryReadiness.json)은 complete=false이고 current Source/Config/native/selected bytes와 원본499 journal·Definition6·Victim43/26 분리 증거를 기록했다. FinalResourceAudit는 실제 `passed=true`/status 없음인데 candidate helper가 status를 요구하는 schema 불일치도 아직 남아 있다.

남은 것은 source artifact/증거 schema RCA, current full Native·Player, frozen Root VisualQA/candidate, 최신 Main CAS 선택 전달과 fresh Main 검증이다. MonsterVFX Main apply는0이다. 외부 Main Null 검증 PID16396은 다른 작업 소유이며 제어하지 않았고 과거 사용자 에디터 상태를 현행으로 재사용하지 않는다. 이번 절은 runtime 추가 수정이나 최종 완료 증거가 아니다.


<!-- MonsterVFX_SharedPolishIntake_Native7QA_20261010 -->
## 2026-10-10 22:00 KST — Native7 실패의 QA 입력 원인·새 baseline 검증 대기

[Native7](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt7/Driver.json)은1390 captures 뒤 failed, [Exit](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt7/Exit.json)은 PID22164/449.312초/exit0이다. 정상 process exit와 자동화 성공을 구분한다. 실패1은 [log](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt7/PrivatePIE.log)의 `Actual granted player Brutal claims actual Apes exhaustion`(DEV test269행)이다. Root가 확인한 obsolete X press 대 current DA의 B grant가 원인이라 제품 Brutal failure로 일반화하지 않는다. private DEV2를 실제 B 입력 경로에 맞춘 새 build/runtime 검증이 필요하며 직접 Ability 강제 활성화·ExpectedError masking으로 대체하지 않는다.

외부 Source3+Art14의 [delivered receipt](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/Delivered.json)는 SHA `a75fa980…7ed7fa9`, UTC12:47:50/fresh Main validation pending이다. 현재 Source3 semantic intake·Build19는 완료 증거 결속 전이다. Art14의 private exact-byte intake만 [SharedEffectsRebaseRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SharedEffectsRebaseRevision.json) SHA `33e13db1…bb422`로 passed이며 원본 plan/author/resource/adapter·Light/Radius 보고서와 own457 후보는 변경하지 않았다. 새 공유 resource baseline의 증거를 별도 revision으로 소비하며 이전 current-input/RHI 증거를 새 후보의 검증으로 재사용하지 않는다.

Yetuga Diagnostic1의 pose-invariant failure는 pause_anims editor setter의 포즈0초 reset이고 동일 game time/camera에서 발생했다. 해당 진단 Source/asset writes0·shader SHA 불변이다. 기존 SingleNode.set_playing(False)로 재생만 멈추는 QA 대안은 준비 단계이며 제품 animation/particle 수명·shader 수치를 변경한 결과가 아니다. 반입 전 실제 shader의 atlas opacity mask가 이미 연결됐다는 Art readback으로 MI02 white→full-card 단정은 철회했다.

남은 계약은 current semantic Source/build + shared14 saved readback → fresh all RHI/Player와 Root VisualQA → immutable original499/457 및 Definition6/Victim26/Shared14 revision을 결속한 candidate → guarded Main 전달과 fresh Main 검사다. **MonsterVFX Main apply0·전체 성공/최종 시각 품질 미완료**이며 외부 polish의 전달을 본 기능의 Main 완료로 기록하지 않는다.


<!-- MonsterVFX_Build19_Saved7_Diagnostic2_Native8_20261010 -->
## 2026-10-10 22:16 KST — semantic Source·fresh saved·전체 Native8의 실제 검증 결속

[Build19](../../Saved/ImportReports/MonsterVFX_20261008/Build/Attempt19/Exit.json)은85.828초/exit0·Main/private 입력 불변으로 passed다. [PlayerPolishSourceIntake](../../Saved/ImportReports/MonsterVFX_20261008/MainRebase/PlayerPolishSourceIntake.json) SHA `4a44ccc6…77c08e4`의 Main98/private101 및 VFX 차이11 계약, current B grant를 소비하는 DEV QA 보완을 포함하며 current DLL SHA는 `b84df875135de6fbc786650a6481ad81d3401eb29d6300bd08b45315559e311a`다. 새 runtime class/file/schema 확장이나 원본 Source receipt 덮어쓰기는 이번 checkpoint에서 수행하지 않았다.

fresh [Saved7](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json), SHA `78843fc56aaec1e4991acc75dc8cc1acdbb8430c322afdb8473df423ac0ba25d`는85.813초/PID12728·487 Sequence/3342 State/Death6·Definition6 override·Victim43/26·[Shared14 revision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SharedEffectsRebaseRevision.json) SHA `33e13db1…bb422` marker를 passed로 확인했다. saves/mutations0·선택499와 공유2034 byte 불변이며 original plan/author499·Apes Applied·ContentRebase/원본 resource 보고서는 immutable로 유지한다.

[Native8](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt8/Driver.json)은 current DLL을 Win32 actual loaded module로 확인한 뒤 automation Result=Success/passed,1568 captures/package saves0/material compile failures[]다. Driver SHA는 `67aae89583e1ebea09b265f1129bab548d61305d049e612cbdcba121f0b5f98c`, [Exit](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt8/Exit.json)는 PID30504/492.813초/exit0이다. 정상 종료만으로 통과를 주장했던 것이 아니라 native completion Success와 Driver 결과를 함께 읽었다. obsolete X를 누른 Native7의 단일 실패와 구분한다.

[Diagnostic2](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt2/Driver.json)는 같은 current DLL에서62.625초/102PNG·두 동일 pose/time/camera 비교·filter/replay 상태 복원을 통과했고 saves/mutations0이다. 이는 QA의 editor setter 포즈 reset을 기존 SingleNode.set_playing(False)로 피한 결과이며 제품 animation/particle 수명 수치 변경이 아니다. Player 회귀는 Root wrapper session45759 실행 중·pass 미확정, candidate/Main 전달/fresh Main 검사도 남아 있다. runtime/Saved 통과를 원작 pixel parity·모든 시각 품질·MonsterVFX Main 완료로 확대하지 않는다. 재개 순서는 [Engineering continuity](ENGINEERING_WORK_CONTINUITY.md)의 이 날짜 checkpoint를 따른다.


<!-- MonsterVFX_PrivateMaterialRepair_LateDiagnostic_D00Tail_20261010 -->
## 2026-10-10 22:52 KST — private 재질3 수정과 제한 진단·원본 데칼 수명 관측 정정

Root가 private에서 [WPO 부모1 저장](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Roar02/Attempt1/Repair.json)과 [Decal 부모2 저장](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Decal/Apply1/Repair.json)을 실제 완료했다. SM6 statistics는 WPO pixel/vertex/sampler163/344/6, Decal 각512/344/6이며 현재 SHA는 WPO `57c664d6…d5b20ab`, Decal `c717eefe…82f5a5`·`8a1e4c66…fad206`이다. PS/MI/texture·499 author 파일/Notify GUID·원본 시간/수명·나머지455 own Art와 Main bytes를 보존한 표현 수정이다. 원본 cooked shader 연결 미확인은 Art 정본의 adapter 경계를 따른다.

Root가 결속한 `JointVisualMaterialRepairRevision.json` SHA `138dc65cb89362a72d1374edbe6c17943e33c74cc967296b53be387bc92e107a`의 선택 후보는 Source11+author499+Art457+기존 reused WPO1=968이다. 기존 plan/PrivateAuthoring/Apes·Definition6/Victim43/Shared14 revision은 보존하고 재질3 override를 별도 결속한다. Build19/Saved7/Native8/Player1/Rim10의 이전 성공은 유지하지만 그 실행은 이번 재질3 이후 전체 회귀를 대신하지 않는다.

[D00 QA1](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt1/Driver.json)은 동일 pose1.1967237초/game time1.3063558초·카메라·visibility/재생 복구가 모두true였으나 전체 tail 단언만 failed다. clipend+10.0098초 잔존은 D00이 아닌 `KZMVFX_15485a2fbbf4570ee1571640` 혈흔이다. 원본 `AC_ApesStoneHand_E_Die_F` ZIP JSON SHA `e73733e0…3ecb9`의 Exports[5].Properties.DecalCreateData.LifeSpan=9초(Notifies[6], D00), Exports[6] 같은field=30초(Notifies[15], 혈흔)를 표적 검증했다. [QA-only 수정](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/TailObservationRevision/TailObservationRevision.json)은 D009+여유1초, 전체max(9,30)+여유1초를 클립 종료 뒤 관측하며 제품 수명을 변경하지 않았다.

문서 작성 중 저장된 [D00 QA2](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt2/Driver.json)은 passed, [Exit](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt2/Exit.json)는PID13520/90.187초/exit0다. D00은+10.0014초 잔존0, 전체 데칼은+31.0109초 잔존0이고 same pose/time/camera·복구·saved bytes 불변, saves/asset/shader writes0·compile failures[]다. overall_visual_pass=false이며 이 제한 결과를 최종 품질 통과로 확대하지 않는다.

[Late Diagnostic4](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt4/Driver.json)은 current Build19 DLL에서49.469초/50PNG·passed, source pose2.2320659초의 불변식/복구·save0/shader bytes 불변이다. Root의0022 Normal/0034 OnlyRoar02 관측은 해당 후반 검은 면이 사라진 제한 증거이며 regular3-case·전체 timeline 양성 검증은 아니다. 재질3 이후 fresh Saved 및 Monster/Player/Rim/Yetuga 전체 재실행·Root VisualQA/candidate·최신 Main CAS/guarded 전달·fresh Main이 남아 있다. **이번 MonsterVFX Main 전달0·전체 완료/최종 visual pass 미확정**이다.


### 2026-10-10 22:53 KST — revision 실제 경로와 제한 검증 경계 추가 확인

위 JointVisualMaterialRepairRevision 표기의 실제 저장 파일은 [Authoring/VisualMaterialRepairRevision.json](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json)이며 schema=Khazan.MonsterVFX.VisualMaterialRepairRevision.v1, SHA `138dc65c…e107a`다. passed는 재질3·기존 원본/CAS의 결속 검사이고 overall_visual_pass=false/fresh_saved_runtime_and_root_visual_review_required=true다. Roar02가 정상 효과를 보이는 positive visibility는 아직 미확정이며 후반 검은 면 없음으로 이를 대신하지 않는다. Root의 fresh 네 회귀/Saved·전체 시각 검토·candidate/Main은 계속 남아 있다.


<!-- MonsterVFX_138_FourFreshRHI_D00Hold_202610102348 -->
## 2026-10-10 23:48 KST — 재질 revision 이후 네 실제 회귀 통과·D00 바닥 양성 검증 보류

현재 실행 정본은 [Source intake4a44](../../Saved/ImportReports/MonsterVFX_20261008/MainRebase/PlayerPolishSourceIntake.json) 및 [Build19](../../Saved/ImportReports/MonsterVFX_20261008/Build/Attempt19/Exit.json)의 Main98/private101 Source·전체 입력104/107/native3다. current DLL SHA `b84df875135de6fbc786650a6481ad81d3401eb29d6300bd08b45315559e311a`/BuildId55116800을 실제 loaded module로 검증했다. 기존 runtime9+DEV2=Source11 및 victim-animation-owned Decal43 정책, original CDO condition unknown/no fake-hit 계약을 유지하며 추가 Source/header/schema/manager 변경은 없다.

[VisualMaterialRepairRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json) SHA `138dc65cb89362a72d1374edbe6c17943e33c74cc967296b53be387bc92e107a`는 기존 own Art457 내 부모2 override와 reused WPO 의존1을 결속한다. 원본 plan/PrivateAuthoring499/Apes Applied/Definition6/Victim43·26/Shared14/Source chain은 immutable다. 전달 선택은 Source11+499+457+1=968이며 기존 원본967 집합을 재author하지 않는다. [Saved8 readback](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json)의 실제 graph/pin3·State3342/Sequence487/Death6·선택 bytes 불변·저장0/all_checks_passed가 이 revision SHA를 소비한다.

| 실제 private 실행 | current 결과 | PNG | 시간/Exit |
| --- | --- | ---: | --- |
| [Native9 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt9/Driver.json) | passed/native Success·package0·compile failures[] | 1549 | PID31392/581.219초/exit0 |
| [Player2 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivatePlayerRegression/Attempt2/Driver.json) | passed/native Success·package0·compile failures[] | 388 | PID18124/144초/exit0 |
| [regular Rim11](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt11/Driver.json) | passed·regular·save0/mutation0·compile failures[] | 27 | PID19200/40.109초/exit0 |
| [regular Yetuga5](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt5/Driver.json) | passed·regular·save0/mutation0·compile failures[] | 106 | PID28536/80.438초/exit0 |

모두 위 actual DLL을 로드한 재질 revision 이후 fresh 실행이다. 각 Native automation completion과 Driver passed를 process exit0와 함께 확인했으며 캡처 수가 원작 시각 일치 검사를 의미하지는 않는다. Root가 Native9 Roar02 positive helix1216을 실제 확인한 Art 결과는 [Art 정본](../Art/MONSTER_VFX_PLAYBACK_20261008.md)에 분리했다. D00 순수 바닥 양성은 아직 미확정이므로 네 회귀 통과만으로 Root VisualQA/candidate를 만들지 않는다.

[D00 QA4](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt4/Driver.json)의 get_component_location AttributeError는 제품 failure가 아니라 QA Python 노출 API 오류였다. Driver failed/0PNG와 모든 finally restore true/saved bytes unchanged를 보존하고 보완 후 [D00 QA6](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt6/Driver.json)의 same pose/game time/camera·원본9초 수명 및 기존 상태 복구/저장0을 passed로 확인했다. Root의 현행 입력은 실제 MID SpawnTime/TimeScale1/LifeSpan9/CurveIndex0와 floor receives_decals=true다. 기존 shader/current pin에서 P0 상수RGBA1·P5 FadeOut1이 확인돼 “alpha0” 및 “P5=.2/미연결 FadeOut” 추정을 철회했다. 원본 graph 미확인 수치를 gameplay Source에 새로 채우지 않는다.

현재 readonly selected968·Main-before/private-after·full Source/config/project/native CAS, Shared2034/history 및 saved marker/frozen helper4는 passed다. 외부 Player 추가 부모2의 Main follow-up은 absent이며 해당 task를 제어하지 않았다. frozen census는 절대경로 다른 uproject를 unknown으로 분류하지 않으므로 PID30020 자체가 delivery blocker라는 앞 설명은 철회한다. 23:43:09 KST 실제 census empty/closed-Main gate passed였다.

**남은 실제 blocker는 D00 양성 및 Root 최종 시각 승인**이다. VisualQA/candidate/Prepared/Delivered는 아직 없고 MonsterVFX Main apply0다. owned transient MID-only 진단을 원본/제품 변경과 구분해 exact restore로 마친 뒤 필요 수정의 새 revision·fresh Saved/RHI를 결속하고, 최신 Main/외부2/process CAS를 다시 확인하여 guarded968 전달 및 fresh Main saved/네 실제 회귀/Root VisualQA/finalizer까지 진행한다. 재개 절차는 [Engineering continuity](ENGINEERING_WORK_CONTINUITY.md)의 이번 checkpoint를 따른다.



<!-- MonsterVFX_DecalReauthorStaging2_202610102357 -->
## 2026-10-10 23:57 KST — QA8 알파 분리·staging 보존과 새 Decal2 적용, 전체 검증 대기

[D00 QA8](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt8/Driver.json)는 PID30456/74.672초/exit0·24PNG, 동일 pose/time/camera·MID/visibility/animation/postprocess 복원 및 원본 자연 수명 검사를 passed로 완료했다. package/asset/shader writes0다. Root 실제 D0020(source RGB+alpha1)은 거의 보이지 않고 E0022(white RGB+alpha0)는 부드러운 원이 보였다. 이는 현 adapter에서 Param alpha가 효과를 지웠다는 가설을 제외하는 제한 QA이고 원작·전체 품질 완료가 아니다. Source/header/schema 수치를 바꾸지 않았다.

23:51:21 KST의 [ReauthorStaging2](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Decal/ReauthorStaging2/Staging.json), SHA `5dbc6a39…1af1e0`는 private 부모2를 Apply1/Before 정확 원본으로 복원한 중간 상태와 이전2 bytes/기존138 보존을 기록한다. 문서 append 전 Root의 [Probe2](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Decal/Probe2/Repair.json)(PID12592/save0) 및 [Apply2](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Decal/Apply2/Repair.json)(PID17048/save2)가 실제 passed로 추가됐다. 현재2 SHA는 `52d746d6…474dc0a`/`c4eb1ca6…5d33798`이고 Main/Source/native·기존455 Art는 보존했다. 원본138/이전 Saved8·네 회귀는 새2 bytes의 현행 승인 증거가 아니다. 새 assembler revision 결속 뒤 fresh Saved/네 회귀·정상 D00 positive/Root 검토·guarded968/Main fresh가 남고 MonsterVFX Main apply0다.


### 2026-10-10 23:58 KST — current revision6309 실제 결속 추가 확인

위 staging 기록 뒤 Root가14:56:40 UTC에 [현재 VisualMaterialRepairRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json), SHA `6309ef7d0b9f91a4c9182e9e179a15fda75116eb23f01d8638db3b33621be60e`를 실제 결속했다. passed는 새 Apply2의 source/CAS 결속이며 overall_visual_pass=false/fresh_saved_runtime_and_root_visual_review_required=true다. [이전138 archive](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairHistory/Revision1_138dc65c/Archive.json)의 MainSaved/PrivateSaved 원본138 bytes를 확인했다. Root QA9 owned wrapper session19559 실행 중이고 current6309의 fresh Saved·네 회귀/RootVisual/Main은 아직 대기다.


<!-- MonsterVFX_6309_Saved9_QA10_PSCBlocker_202610110018 -->
## 2026-10-11 00:18 KST — current6309 Saved9·QA10 통과, 실제 Native10 실행 중

Build19의 기존 runtime9+DEV2/Source intake와 DLL을 유지하며 Source/header/schema·게임 수명 변경은 없다. [current6309](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json), SHA `6309ef7d…21be60e`를 소비한 [Saved9](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json)는 PID31520/99.75초/exit0·actual graph3/readback·selected bytes 불변·저장0/all_checks_passed다. [QA9](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt9/Driver.json)는 PID23764/84.985초/24PNG/exit0·원래 수명·상태 복구를 passed로 완료했다. [RootD00Review](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt9/RootD00Review.json) SHA `6e68bf2d…fab27e0`는 정상 D00-only/noPSC0008 soft circle vs 무데칼0012 양성에 한정되며 Normal0000의 검은 카드로 전체 visual HOLD다.

[QA10](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt10/Driver.json)은 PID17540/89.328초/30PNG/exit0·상태 복원/저장0 passed다. Root actual only-component0024/0026/0028에서 FP_DeathEffect1과 world fall2 모두 카드가 보였다. source FP burst12는 단일 producer proof가 아니며 template/material slot3/6/6 identity와 current shader graph 소비·원인은 추가 확인 중이다. 기존 regular의 정상 dust와 QA10의 default-like cards 차이는 첫 로드/Usage/shader 가설을 만들지만 증명은 아니다. compile failures[]만으로 이를 제외하거나 source 재질 결함으로 확정하지 않는다.

Root [Native10 launch](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt10/Launch.json) current6309/PID10736은 실행 중이다. 이전138 네 회귀는6309로 재사용하지 않으며 Player3/Rim12/Yetuga6는 원인·수정 판단 뒤 대기다. [QA7 ReferenceResolution](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/QA7PixelAnalysis/ReferenceResolution.json)은 원래 분석 `fc5fb913…dd00e0a`를 보존해 archived138에 연결했다. 이번 문서 기록 외 제품/Source/helper 변경·agent UE 실행0, MonsterVFX Main apply0다. 시각 범위는 [Art 정본](../Art/MONSTER_VFX_PLAYBACK_20261008.md), 재개는 [Engineering continuity](ENGINEERING_WORK_CONTINUITY.md)의 같은 checkpoint를 따른다.


<!-- MonsterVFX_MainDelivered_MainSavedFailed_20261011010443 -->
## 2026-10-11 01:04 KST — Main 선택968 적용 완료·fresh MainSaved 첫 실패

[Delivered](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/Delivered.json)의 실제 상태는 `SourceContentAndNativeAliasDelivered`, SHA `12f3af9d3a3e3fb50ec8caf42f652e50786d1f452c9ffb4bbea6cb5e5c86603a`다. Source11(runtime9+DEV2)+author499+Art457+reused WPO1=968을 전달했고 기존 native/Config·비대상 Source·Source intake4a/외부 Source3·Shared14/B 입력·DevMap을 보존했다. alias는 `UnrealEditor-KhazanMonsterVFX20261008.dll`, module manifest SHA `6424d4611c4907308042fef7d1aa5dee404ca36e8855891fb303ca3a873dc993`다.

current6309/private Saved9와 Native10(1578PNG/476.359초), Player3(385/159.64), Rim12(실제 Driver30/44.719), Yetuga6(76/99.625)는 passed이며 [private RootVisualQA](../../Saved/ImportReports/MonsterVFX_20261008/VisualQA.json) SHA `55178750…802bd15`가 표본 승인을 결속했다. QA10 카드 현상은 QA11 shader-only 준비/8 bytes 불변 뒤 해소된 관측이며 새 제품 alpha-mask 수리/GPU fallback identity 직접 증명이 아니다.

첫 fresh [MainSavedReadback](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/MainSavedReadback.json), SHA `1d8535b0…dfa50`, PID31324는 status=failed/Exit1·저장/변경0이다. helper line156 Effect data_fields 대조가 실패했고 Root가 식별한 event는 `KZMVFX_f3af66febacc3ab35102cf8b`(Halberd Damage_FinalBlow_Composite_Variant01)다. plan의 ParticleTemplate `/Game/_Art/Effects/Combat/Blood/FP_BloodSplit_01`은 Main 파일이 없고 private에는 있으나 이것이 실제 실패 field인지/다른 closure 누락인지는 표적 감사 중이다. [새 MainMonster launch](../../Saved/ImportReports/MonsterVFX_20261008/MainMonsterRuntimePIE/Attempt1/Launch.json) PID30664는 검증 중이다. 전달 성공과 최종 검증 성공을 구분하며 전체 완료를 주장하지 않는다.


<!-- MonsterVFX_AdapterSupplement972_FreshMainPending_20261011012157 -->
## 2026-10-11 01:21 KST — Main972 의존성 supplement 적용·fresh 검증 대기

[Main1](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/Diagnostics/Main1/Readback.json)의 실패 field는 event `KZMVFX_f3af66febacc3ab35102cf8b`의 ParticleTemplate null 하나다. [Private1](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/Diagnostics/Private1/Readback.json)의 consumer316/closure22(동일18+Main 누락4)와 original importer provenance로 누락을 확인했다. 원인은 Union rerun의 reused_native=true·existing_native_sha256=null 분류이며 Source/Notify schema나 runtime factory의 field 변경이 아니다.

[SupplementalDelivered](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/SupplementalDelivered.json), SHA `d7487b5085e02d8ea1da66d80cd9a0383ca66e0df8d4e1fd25478a130bc1ed44`가 absent Main adapter4의 정확 private bytes 복사를 완료했다. 상태 `FourAdapterDependenciesDeliveredFreshMainRequired`, 범위972=original968+supplement4다. 원래968/Art457/6309 영수증은 그대로이며 Source/native/material graph/private package 변경0, 이번 asset copy4·save0이다. 기존 private Saved9/Native10/Player3/Rim12/Yetuga6/RootVisualQA는 private bytes가 불변인 범위에서 유지하고 새 Main 검증을 대체하지 않는다. alias `UnrealEditor-KhazanMonsterVFX20261008.dll`과 기존 module/Config/B 입력/DevMap·Source intake4a/ARCH85·외부 Source3/Shared14를 보존했다.

[ToolRevision](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/HelperRevision/ToolRevision.json), SHA `df7925cc…8aa26`는 별도 supplement helper의 exact4/closure/immutable original968/실패 archive 및 finalizer의 post-supplement fresh Main proof gate를 결속한다. 원래 deliver/saved/candidate helper는 불변이다. [Archive](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/FailureHistory/Archive.json)에서 첫 MainSaved failed 및 pre-supplement MainMonster Success1560/517.265초를 보존했으며 최종 검증으로 재사용하지 않는다.

fresh MainSaved2는 Exit0/PID30360로 종료됐고 최종 검증은 대기다, MainMonster2는 진행 중이며 아직 Exit이 관측되지 않았다. FinalVerification은 아직 없다. canonical MainSaved가 첫 failed 값이면 archive로 보존한 역사 값이며 새 시도 완료로 읽지 않는다. 현재 재개는 실행 중 두 결과 확인→fresh Main Player/Rim/Yetuga→Root MainVisualQA→finalizer 순서다. 실제 `FinalVerification.status=MainDeliveredAndFreshVerified`까지 최종9문서 기록은 보류한다. 정확 명령은 [Engineering continuity](ENGINEERING_WORK_CONTINUITY.md)의 같은 절에 있다.


<!-- MonsterVFX_MainComplete_20261011 -->
## 2026-10-11 01:41 KST — Source11·최종 선택972 Main 전달/재검증 완료

[FinalVerification](../../Saved/ImportReports/MonsterVFX_20261008/FinalVerification.json)의 실제 `MainDeliveredAndFreshVerified`로 Source11(runtime9=기존7+MonsterVisual Notify h/cpp2, DEV2), author499(Sequence487+Definition6+Death montage6), Art457+reused WPO1+adapter supplement4의 최종 선택972을 완료 확인했다. 지원 source2855와 기술 sentinel487(State3342)을 분리한다. [Source intake4a](../../Saved/ImportReports/MonsterVFX_20261008/MainRebase/PlayerPolishSourceIntake.json)/Build19의 최신 Main98/private101 통합본에서 task11만 전달했고 Config·다른 Source·기존 native·ARCH-85/B 입력/DevMap·외부 Source3/Shared14를 보존했다. 실제 alias는 `UnrealEditor-KhazanMonsterVFX20261008.dll`, DLL 내용 SHA는 `b84df875135de6fbc786650a6481ad81d3401eb29d6300bd08b45315559e311a`다.

기존 Action factory/engine Notify와 Monster의 mesh·Anim·NotifyID/context receipts가 tail·clip/loop/cancel·material overlap·death freeze/UnPossess/EndPlay를 정리한다. optional ordinary Death/Execution material은 유지하고 실제 Grapple material recipe0에는 FinalBlow dissolve를 붙이지 않는다. 사용자 피해50을 보존하며 VFX fake hit/피해/새 gameplay 상태·AI는 없다. engine default merge를 사용하므로 동일 Actor/동일 clip 동시 재생 지원으로 확대하지 않는다.

current6309/Saved9와 private Native10/Player3/Rim12/Yetuga6 뒤 fresh Main saved/네 RHI·Root 표본 검토를 별도 완료했다. victim Decal43/Sequence26 정책·NONV3 alias5/baseline uniform·Definition6의 다른 field·shared2034=외부14+ownWPO1+2019 보존을 확인했다. QA11 shader 준비 뒤 QA10 카드는8 asset bytes 불변으로 사라졌다. original CDO/stripped shader·NI bindings·unsupported216·correction52/surface selector·전체 pixel parity/shipping 성능은 미확인이고 새 ARCH-86은 독립이다. 옛 pending/138 결과나 전체 private Source를 다시 적용하지 않는다.

초기 Delivered968/Art457은 불변으로 보존했다. 첫 MainSaved 실패의 event KZMVFX_f3af66febacc3ab35102cf8b는 ParticleTemplate만 null이고 다른 Effect fields는 일치했다. union 재검사에서 existing_native_sha256=null인데 reused_native=true로 표시된 신규 global NI→Cascade adapter가 Art457에서 제외된 것이 확인됐다. 실제 consumer316/closure22 중 Main/private 동일18은 보존하고, 누락4(FP_BloodSplit_01/02·FP_Dmg_Blood_Base·FP_Dmg_Blood_Base_BK)만 [별도 strict supplement](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/SupplementalDelivered.json)로 전달해 총972가 됐다. Source/native/material graph와 private bytes는 바꾸지 않았으므로 기존 private proof를 유지하고 Main 검증만 supplement 이후 새로 결속했다. pre-supplement MainMonster Attempt1의 Success/1560PNG/517.265초는 최종 Main 증거로 재사용하지 않는다.

최종 gate14는 모두 true이며 MainSaved2(Exit0/150.203초), MainMonster2(1600PNG/494.203초), MainPlayer1(384/205.141), MainRim1(30/67.485), MainYetuga1(106/95.953)이 모두 supplement 이후의 실제 모듈/Exit0/저장·대상 bytes 불변을 확인했다. Root MainVisualQA는 정상 PNG11+targeted6 표본을 검토했다. 증거 FinalVerification SHA `e4b2390f0ab95a0168d8c41031bf00681ac601e98ac7a7d26653f149d065b994`의 확정 시각은 2026-10-11 01:41:38 KST다.


## 2026-10-12T11:04:18+09:00 — ARCH-91 Root·공격 콜라이더·VFX Main 완료
Main에 Source7(runtime4/DEV3) 및 RootMotionRootLock 옵션만 바꾼 Animation88 package를 exact SHA/CAS로 반영했다. 새 runtime file/class/manager0, 다른 baseline610파일 보존, private DLL/Config 전달0. MainBuild01은 source 오류 없이 PCH virtual-memory C3859/C1076로 실패했고, 병렬1/noXGE MainBuild02는 Succeeded/input unchanged다. 현재 canonical UnrealEditor-Khazan.dll SHA `e14ca4b34c8a8a8042c2087fca2e646196b51e617d906c1884bee4e6c29cf511`를 사용한다.
실제 사용395 Root enabled/force lock/true-root·track0 및 Body392의1176포즈를 확인했다. 첫 프레임 누적 origin88개만 RefPose lock으로 정렬했으며 근거는 RootLockPlan의 imported RAW root first transform와 skeleton reference pose/UE FRootMotionReset이다. RootAssetBefore 및 MainBefore 백업을 보존한다. 전체 DataModel 모든 key/curve/attribute와 notify event/object SHA392개가 변경 전=private 후=Main fresh로 동일하다. source montage126/definition57/node220/window405의 geometry key·time·HP/Stamina·group·audio와 rate/나머지옵션이 fresh saved audit에서 동일하다. Props3는 다른 skeleton으로 body1176포즈에서 분리하고395 옵션/track audit에 포함했다.
Main actual RootPoses/MonsterHits30/PlayerAttackCollision16 Success. monster30은6종별 한 window 안1회 / 종료 후접근0 / exact-end pause후접근0 / 취소후접근0 / live mesh scale와actor yaw 반영을 실제 HP GE로 확인한다. player16의 기존 Spin7/Fury19와blood13 기반행동도 보존한다. source scale/last-End 경계·timer 종료만 기존 ComboAction에 보완했다. VFX198 assets/1577 source occurrences 및Death6는 동일 delivered Source의 private 실제RHI Success, finite world transforms / deterministic uncorrected source geometry max position3.46e-13cm·angle4.83e-6deg / template identity / body size를 확인했다. 이 보고서의 active correction-curve row는0이므로 해당 branch의 per-pose 실행을 실제 데이터 검증했다고 표현하지 않는다. source 없는 VFX actor axes/mesh origin 및 body scale은 적용했으며 curve branch는 기존 receipt의 latest GT clock→finalized-bone callback으로 구조 보완했다. 원작 native shader/pixel parity·전체두레벨연속전투·network는 검증 완료 범위가 아니다.
Main 파일·canonical build·fresh saved/actual runtime 완료. FinalVerification.json / ResumeState03.json 및 exact Delivered95를 재개 정본으로 읽는다. stage/old alias/full author/retime/reimport를 반복하지 않는다. Main editor 정상 재시작 후 직접 Play에서 green debug volume이 실제 공격 window에서만 나타나고 칼의 크기·방향/몸체 alignment를 확인할 수 있다.


## 2026-10-12T13:12:55+09:00 — ARCH-92 사망·브루탈·액션 VFX Main 완료

Main Source10(runtime6/DEV4), montage8, 새 runtime 파일0을 적용했다. baseline Source121 중 무관111파일을 보존했고 원본 Root88/게임플레이 공격 창·피해·오디오·UI·애니메이션 raw pose는 변경하지 않았다. FinalBuild05 current canonical build/input동일, fresh SavedAudit02 8/55/dirty0/save0가 통과했다. Main 기존 파일을 직접 보완했으며 private DLL/Config 전달0이다.

일반 사망은 interruption을 완료로 간주해 현재 포즈를 멈추던 것이 원인이었다. 기존 RefreshCombatState로 다음 tick에 사망 동작을 재시작한다. DeathBaseline01의 중단6 오차167–441cm → DeathFixed02의 정상6/중단6 terminal pose 오차0. 짝 사망은 task blend-out 완료 시 source 마지막 pose가 이미 idle로 섞이는 문제가 있었다. HP0인 자기 victim instance만 auto blend-out을 끄고 Monster의 기존 GT tick이 finite end를 관측하여 Exhaustion의 기존 완료를 호출한다. shared asset/비치명타 recovery/정상·취소·EndPlay cleanup은 유지한다. LethalPairFixed01 실제 Front/Back12 terminal pose 최대0.015341 model cm, 접촉 XY offset0이 통과했다. 이는 사용자 전체 플레이에서 interruption 빈도를 계측한 결과가 아니다.

Brutal Root particle의 원본 source offset은 현재 capsule 짝 간격/수입 mesh yaw와 맞지 않았다. 기존 effect receipt만 찾아 detach/world XY 두 actor 중점·Z 두 chest 평균에 배치하고 기존 composed rotation/scale·피해·시간·수명은 유지했다. PresentationFinal02는 실제 LockOn→B 6종 Front/Back12, 비치명타 recovery/root-mode 복원 및 실제 낙하/착지/벽 옆 ground debris를 통과했다. EffectsFinal01 기존18+Brutal5, CollisionFinal01 실제16(Spin7/Fury19/miss/cancel/끝 접근), ParryFinal01 실제15/6종 정책도 통과했다. DEV-only viewport readback 추가 이후로만 실제 게임 화면을 판단한다. LethalPairFixed01의 이전 전역 screenshot은 editor viewport였으므로 시각 근거에서 제외한다.

혈흔은 기존 accepted-hit particle1회와 ground projector/fade/snow·walkable 계약을 유지하며 class 설정의6개 작은 satellite를90–280cm 범위/전체 방위로 생성한다. 독립 FRandomStream, 장애물/바닥/가파른 면 제외를 사용한다. DeathFixed01의 scatter0은 QA floor의 Static mobility로 scale이 반영되지 않은 fixture 문제였고 Movable fixture의 DeathFixed02 실제6종에서 main+6=7 /네 방향/범위/하향 normal을 확인했다. 제품 collision/지형을 바꾸지 않았다.

수치와 resource/표시 변경은 Art 최신 절을 따른다. 정확한 변경/각 실제 DLL/원본 보존/실패 기록은 Metadata/CombatFinishFollowup_20261012/FinalVerification.json에 있다. 원작 shader/pixel 완전 일치·Shipping stress/두 레벨 연속 전투는 이번 범위가 아니다. 이후는 현행 Main과 이 receipt에서 시작하며 stage/전체 author/Root·Parry 이전 전달을 반복하지 않는다. Main 정상 editor ready 여부는 후속 기록으로 분리한다.


## 2026-10-13T13:11:51.008812+09:00 — GiantVFX Main 실제 반영·시각 잔여 분리

ARCH-98은 기존 Monster visual receipt/SkillObject 소유 수명을 사용해 거대형 VFX를 Main에 연결했다. Source 변경은 새 runtime class/file/manager 없이 기존7파일과 DEV1이다. selected effect의 bUseWorldParticleUnits가 원복된 Cascade의 world cm 크기를 소비하고, 기존 원작 correction/부착 transform 수명을 유지한다. SkillObject의 SetAbsolute(false,false,true)를 KeepWorld attachment보다 먼저 호출해 nonzero parent translation이 두 번 더해지는 실제 오류를 수정했다. 종료/cancel/EndPlay는 기존 weak receipt로 정리한다. 원작 gameplay geometry/창·피해·root/FPS는 보존했다.

MainBuild02/보존84/allLOD null0, MainAll01 실제155, MainPatterns02 GAS8+objects3 및 종료 정리, MainCollision01을 통과했다. MainRefractionFixed01 기술23은 화면 승인과 다르며 Armageddon 흰 판은 남았다. 최신 PlayerSlash의 CombatEffect 공장 변경은 동일 Main에서 보존한다. exact per-run module와 선택 전달은 Metadata/GiantVFX_20261013을 따른다. 상태는 구현 반영·기술 검증 완료/시각 검수 미완료이며 전체 완료가 아니다.


## 2026-10-13T14:16:31.407968+09:00 — GIant VFX 흰 데칼 투영의 실제 수정·Main 검증

ARCH-98 후속: 흰 판은 실제 particle component가 아닌 Armageddon_Start의 WorldSettings decal였다. native paused stack/PSC values와 unsaved suppression 비교를 저장했고, DecalHideIsolation01의 단일 projector를 exact source notify로 결속했다. 기존 factory/Monster receipt/시간·offset·size·lifetime·cleanup 계약은 변경하지 않았다. Source 추가 수정0/새 runtime class·file·manager0이다. 변경은 Source notify의 전용 DecalMaterial reference 한 필드 및 owned shader2이다. audit의 reverse mapping에는 이 한 material substitution만 명시적으로 추가했고 다른 raw/root/FPS/event/object 값은 여전히 strict다.

SnowDecalDelivery01/Delivery.json의 Main3 선택 전달 뒤 MainSavedSnowDecal01 원본84, MainSnowDecalFinal01 실제 연속23/69PNG를 통과했다. PlayerSlash의 현재 CombatEffect.cpp23c27… 변경과 최신 Heal/Parry/SFX/보조 물리 Source를 보존했고 protected parallel hashes를 따로 기록했다. 정확 최종 자료는 Metadata/GiantVFX_20261013/FinalVerification.json이며 과거 finalize_giant_vfx의 old-source assumptions를 재실행하지 않는다. 수치·Shader 재구성 경계는 Art GIANT_VFX_REFINEMENT_20261013.md 최신 절을 따른다.


## 2026-10-14 — ARCH-99 Yetuga·Apes 원본 카메라 이벤트 연결

기존 Metadata/MonsterVFX_20261008/ApesYetugaOriginal/ActorVisualBindings.json의 xxCameraMod_Shake 88개를 각 SourceMetadata.zip의 source entry SHA와 대조했다. Yetuga72, Apes16이다. DilationCurve.DilationAnimPositions의 원본→재생 시간 piecewise 변환 후 Metadata/AnimationTimingKnockback_20261012/CurrentAnimationLibrary_IntegerFPS.csv의 Seconds/PreviousSeconds를 적용했다. 결과는 Metadata/GiantCamera_20261014/OriginalCameraEvents.json에 각 original package, export index, 원시 property/단위, 변환 입력·출력과 근거 SHA로 저장했다. 현행 AnimSequence가 있는 86개를 48개 에셋의 MonsterCamera 트랙에 저장했다. 범위는 공격51, 이동28, 피해5, prop1, idle1이다. Apes CloseGrab_Success_01 및 Apes/08_DashAtk 아래 AC_Yetuga_RushGrab 원본 2개는 현행 동일 AnimSequence가 없어 임의로 다른 클립에 붙이지 않았다.

직접값 사례: AC_Yetuga_NormalAtk02_01의 LocOscillation.Z.Amplitude=-1300 cm/Frequency=18 Hz, CameraShakeScale=.5, FinalScale=.1이며 현행 Attack_NormalAtk02_01의 변환 구간은 1.83585684–2.30597926 s다. Yetuga Idle_Social은 X=300/Y=-50/Z=-50 cm, 각 50 Hz, scale=.05/final=.1, 구간 .46528283–1.90601510 s다. Apes CloseGrab_Success_01_Turn은 Y=-500/Z=600 cm 각22 Hz, scale=.3/final=.1, 현행 1.61076049–1.84996046 s다. Apes Run_Loop_Composite_Variant01은 Y=100 cm/30 Hz, Z=-800 cm/15 Hz, scale=.1/final=.05가 한 루프의 네 구간에 기록되어 있다. 이 수치들은 위 report의 각 source_zip_entry/raw_camera_properties/raw_axis_* field에서 직접 확인하고, 현행 초만 위 변환으로 계산했다.

FadeOut.BlendOption이 기록된 84개는 QuadraticInOut, 2개는 옵션 미기록이다. 공용 원본 BBQ/Content/_Common/Camera/Curve/FadeInOut은 Metadata/MonsterVFX_20261008/ApesYetugaOriginal/Source/BBQ/Content/_Common/Camera/Curve/FadeInOut.json에 선형 key(-.0011494309,0), (1.9955248,1.0014802), (2.999888,1.0014802)가 있다. UE 5.8 FAlphaBlend는 BlendOption=Custom일 때만 CustomCurve를 평가하므로 명시된 QuadraticInOut은 그 엔진 동작으로 재현했다. 원작 전용 xxCameraMod가 곡선을 별도로 소비했는지는 미확인이다. fade가 notify 구간보다 긴 70개는 NotifyEnd 뒤 release로 해석했다.

기존 visual receipt의 VFX 실행은 보존하고 카메라 전용 notify만 로컬 camera modifier로 분기했다. 위치/FOV 연속 sine와 quadratic easing을 사용하며 매 이벤트 진폭 ±12%, 원본 0축에 지배축의 최대6% 교차 이동, 합산 위치90 cm/FOV2도 clamp를 적용했다. 이 랜덤/교차/clamp, 누락 scale의 1·final scale의 .1, 누락 주파수의 단일 pulse, 거리 radius의 정렬은 모두 어시스턴트 TEMP 어댑터이며 원본 직접값이 아니다. 현재 저장 readback은 48개/86개 전 필드와 시간, 기존 notify 수 보존을 확인했다. 실제 Main RHI PIE는 Yetuga 공격·idle 및 Apes grab·run 네 클립에서 세 축 출력과 fade 종료를 통과했다. 다른 병행 잡기 작업이 저장한 4개 파일을 최종 재검토했고 카메라 이벤트 누락0으로 최신 저장본을 다시 읽었다. 증거는 Metadata/GiantCamera_20261014/FinalVerification.json 및 SavedReadback.json이다.

## 2026-10-15 — 사망 흰 원판 8개 연결 오류 원인 및 Main 적용

기존 PreparedPlaybackPlan.json의 Death 항목 18개와 death_presentations 6종을 출발점으로 현재 저장 에셋과 CDO를 표적 확인했다. 흰 원판은 KZMonster의 accepted-hit 혈흔이나 DeathAsh가 아니라 사망 AnimSequence의 KZAnimNotifyState_MonsterVisual → 내장 KZAnimNotify_CombatEffect → DecalMaterial → SpawnDecalAtLocation 경로다. world-owned DecalComponent에 KZCombatEffect/EventId 태그가 붙는다. 범용 CombatEffect 공장을 삭제하거나 몬스터의 혈흔 정책을 끄지 않는다.

D3D12 IsolationRHI01은 18개 사망 시퀀스를 재생하고 남은 바닥 데칼 9개를 한 컴포넌트씩 숨긴 전후 프레임을 저장했다. FMI_Decal_Deferred_D_02/MI_Decal_Deferred_D_00에 해당하는 8개만 흰 원판을 만들며, 컴포넌트 단독 숨김으로 소실이 확인됐다. Swordsman Death_Down_Die_B_Wraith의 PD_Dirt_SuperRound_MonsterCurve_7b611d5a(KZMVFX_986b658027a1c380c80b9db3)는 정상 흙 자국이므로 유지한다. 재질 원인은 Art의 MONSTER_PRESENTATION_REPAIR_20261011.md 같은 날짜 절과 Base_01/Base_02 T3D에 기록한다.

실제 Main 변경은 아래 8개 AnimSequence 안에서 해당 Effect.DecalMaterial=None 한 필드뿐이다. 기존 Notify/Effect/EventId/SourcePackage/SourceField/재생 시각/길이/애니메이션 데이터 및 다른 파티클은 유지한다. 해당 이벤트의 particle/Niagara/trail/routes/batch가 비어 있음을 먼저 확인해 None 변경으로 다른 fallback이 활성화되지 않는다. 기존 ARCH-88의 정상 accepted-hit 바닥 혈흔과 검은 ash/dissolve 계약을 유지하며 새 runtime 파일·class·설정·튜닝값은 추가하지 않는다.

| Family | 사망 시퀀스 | 제거한 EventId |
|---|---|---|
| Yetuga | Death_Die_F | KZMVFX_0b34a270c8a31c95892e6754 |
| HeavySwordsman | Death_Die_F | KZMVFX_e9b8b3974f8040cef6c255bd |
| HeavySwordsman | Death_Die_F_Wraith | KZMVFX_a29158bc70fc8fda01dfe9be |
| Swordsman | Death_Down_Die_B_Wraith | KZMVFX_e0db0f3cc5a6bca82b1e8626 |
| Swordsman | Death_Down_Die_F_Wraith | KZMVFX_d922e1ce123c9f9282484967 |
| Swordsman | Death_Ground_Die_F_Wraith | KZMVFX_2d02b1b88351a10cf63c5dda |
| Swordsman | Death_Ground_Die_F_Wraith02 | KZMVFX_234e0a264e90ffa658978ea5 |
| ApesStoneHandElite | Death_Die_F | KZMVFX_d3f1b3f723e1c147b406fa5c |

Script: Scripts/Engineering/remove_monster_death_white_decals_20261015.py. 수정 직전 package는 Metadata/MonsterDeathWhiteDisc_20261015/Backup/Content에 보존했다. Authoring.json passed/save8/source0이며 전체 T3D 비교에서 해당 material 포인터 이외의 변화가 없고, Notify struct 및 나머지 사망 패키지 10개 SHA도 동일하다. 현재 재생 회귀는 진행 중이며 그 완료 결과는 뒤에 별도 추가한다. 스크립트를 재실행해 이미 적용된 패키지를 다시 author하지 않는다.

## 2026-10-15 — 사망 흰 원판 Main 수정 검증 완료

위의 진행 중 기록을 완료 상태로 갱신한다. AfterRHI01은 새 main 프로세스에서 저장된 8개 None 바인딩·Notify GUID/시각/길이 보존·다른 사망 패키지 10개 SHA·6종 blood/ash CDO 보존을 확인한 뒤 D3D12 PIE 사망 시퀀스 18개를 끝까지 재생해 Success다. 문제 D00/D02 EventId/DecalComponent 관측은 0, 정상 dirt EventId KZMVFX_986b658027a1c380c80b9db3는 재생됐다. 다른 실제 파티클 peak component 수는 수정 전후 18/18 동일하고 liveParticles>0이다.

기존 Khazan.MonsterRepair.PIE를 quick_visual=1/BLOOD_REFERENCE_POLICY=1로 재사용한 PresentationRHI01도 Success/death_families=6이다. 실제 HP=0 → FinishDeathPresentation 경로의 3종 사망 montage + 3종 terminal pose 사망, 모든 6종 accepted-hit live blood/바닥 혈흔, 검은 ash/dissolve/despawn, 경사면 배치·접지 없는 피격·피해자 파괴 이후 독립 데칼 수명 정책을 통과했다. 6종 blood live 402~408, ash live 각630은 이 QA 실행 관측이며 원작 수치나 신규 튜닝값이 아니다. quick mode는 attack_assets/source_occurrences=0이며 전체 공격 전수 회귀로 기록하지 않는다.

수정은 main AnimSequence 8개이고 runtime C++/공유 재질 변경0이다. 빌드는 이번에 재실행하지 않았으며 실제 검증 프로세스들은 이전 Main 성공 빌드의 canonical UnrealEditor-Khazan.dll SHA 6f1c6bfe41382cb6f6308130e403ce568b6b76f560e2b154707f4f9810b2d25e를 로드했다. 관련 재질 compile/fallback 실패0, 작업 소유 editor들은 정상 종료했다. 최종 재사용 근거는 Metadata/MonsterDeathWhiteDisc_20261015/FinalVerification.json이다. DevMap D3D12의 표적 사망/혈흔 회귀 범위이며 원작 shader 완전 일치·Shipping/network 전수 검증으로 확장하지 않는다. 이번 요청의 적용/검증 잔여 작업 없음.
