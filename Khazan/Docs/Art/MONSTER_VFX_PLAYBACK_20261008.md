# Monster VFX 원본 자료·에셋·재생 정본

## 2026-10-08 — 여섯 가족 원본 자원 준비 완료, 실제 화면 검증 전

대상은 인간 Swordsman/SwordShield/HeavySwordsman/HalberdElite와 ApesStoneHandElite/Yetuga다. 행동, 이동, 공격, 피격, 소진, 사망의 source Notify를 현재 animation에 대응시킨다. 현재 원본 자료는 `Metadata/MonsterVFX_20261008/HumanOriginal` 및 `ApesYetugaOriginal`에 있으며 후속 작업은 이 저장 자료부터 시작한다. 원본 package path, source JSON SHA, raw payload SHA, 정확한 source field와 baked 시간 변환을 보존했다.

### 재사용 가능한 자료

- 인간 원본 manifest/timing contracts/현재 clip map와 동물 Manifest/EffectWindows/ActorVisualBindings는 원본 이벤트 및 조건부 actor 표현을 구분한다. actor binding이 있다는 이유로 모든 상시 aura/status 변형을 무조건 켜지 않는다.
- private `Saved/ImportReports/MonsterVFX_20261008/Resources/FinalResourceAudit.json`과 `ImportReport.json`은 자원 누락·import failure·기존 재사용 자원 변경 0을 확인했다. 2028개 기존 native 자원은 Main/private byte 동일하게 재사용했다.
- `ArtCandidateManifest.json`의 신규 파일은 457개다. 원본 재질/텍스처/mesh/vector field/particle 자원과 명시적 renderer/material adapters를 포함한다. 이 수량은 Main 적용 완료 수량이 아니다.
- 원본 native Cascade ParticleSystem 144개, LOD0 emitter 804개의 Required/Spawn/material 연결을 검사했다. 33개 Material, 150개 MI, 30개 mesh와 관련 curve/texture/vector 자원 연결을 검사했다.
- `NativeAdapterMap.json`은 47개 adapter의 원본 근거와 새 구현 구분을, `DecalCurveRegistry.json`은 GPU Decal의 rich curve 7개를 보존한다. Yetuga horn mesh의 원본 null slot은 emitter override material로 동작하므로 무관한 mesh slot을 채우지 않는다.

### 재질 보완과 원작 일치의 경계

원본 cooked shader topology/editor Niagara graph는 재작성 가능한 원본 graph가 아니다. NI renderer 정보로 만든 Cascade adapter 12개와 Decal material variant 29개, Rim overlay, Apes Execution material variant는 source texture/geometry/curve를 소비하는 재현 구현이다. source User defaults를 기록했지만 확인되지 않은 User→simulation/material 연결을 복원했다고 설명하지 않는다. Shader/Fresnel/dissolve adapter의 구현·임시값은 manifest와 Engineering 정본에 구분한다.

두 기존 Grass/Snow master의 누락된 static sourceTexture 소비 연결을 신규 private 자원에서 보완했다. source light-only SimpleLight03은 투명 sprite와 source component count limit을 사용해 불필요한 흰 billboard를 피한다. Apes Execution은 bone 위치/curve를 실제 replacement MID가 소비하도록 연결한다. 원본 물리/AI/투사체 동작까지 재현한 것으로 확대하지 않는다.

### 부착·저장·화면 검증

원본 attachment bone, transform, scale, location/rotation follow, 종료·tail 정책, source surface route와 material parameters는 `PreparedPlaybackPlan.json`의 typed event fields를 사용한다. 원본 trace 대상 미확인, missing correction bone 52, 임시 visual fallback 10+1은 [Engineering 정본](../Engineering/MONSTER_VFX_RUNTIME_20261008.md)에 명시했다.

private author는 487개 Sequence에 지원 구간 2855개와 clip 수명 경계를 추가하고 현재 gameplay 사본도 함께 작성할 계획이다. 기존 notify/curve/raw pose/root metadata 보존과 fresh saved readback 뒤 실제 RHI를 검사한다. 검사용 capture camera/FOV/샘플 주기는 QA 설정이며 원작 gameplay 수치가 아니다. 실제 화면 PNG의 가시성·부착·scale·재질·tail을 확인하기 전 화면 품질 완료를 선언하지 않는다.

Main 전달과 최종 화면 결과는 아래 dated 절 및 `ART_WORK_CONTINUITY.md` 최신 MonsterVFX 기록을 따른다. 원본 무늬·전체 Niagara/눈 변형/카메라/conditional hit 동작의 완전 일치를 주장하지 않는다.

## 2026-10-08 22:30 KST — 실행 재질 수치 해석 수정·조명 usage 보완, Main 전달 전

이번 기록은 `Khazan_MonsterVFXWork_20261008/Khazan`의 별도 작업본 결과다. Main의 게임 Source/Content에 전달한 기록이 아니다. private author는 Sequence 487개, 원본 대응 visual state 2855개와 clip 수명 state 487개(합계 3342개), 사망 presentation 6개를 저장했으며 mutation journal은 Sequence/Definition/Montage 499개다. 후속 검증은 이 실제 저장본과 최신 native DLL을 사용한다.

### Apes Execution 원시 곡선과 rendering adapter 수정

`ImportReport.json` 초기 구현의 `normalized_complete_value_1_forces_zero_opacity` 해석은 아래 실제 수정으로 대체한다. 이전 보고서·master bytes는 private `Resources/ExecutionRadiusRevisions`에 보존했다. 원작 scalar를 0–1로 제한하거나 값 1에서 몸 전체를 숨기는 방식은 원시 곡선 범위와 맞지 않았다.

원본은 `Content/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Metadata/Extraction_20260915/SourceMetadata.zip` 안의 다음 package다. 모든 key의 interpolation/tangent와 원시 값은 `Resources/ExecutionRadiusRevision.json.raw_curve_provenance`에 보존했다. 시간은 원본 curve의 초 단위이며 scalar 값의 원래 물리 단위와 cooked shader topology는 미확인이다.

| 원본 package (공통 prefix: `BBQ/Content/_Kazan_/Design/Monster/Apes/ApesStoneHand_E/Moving/Reaction/`) | 정확한 notify field·curve | 원시 key `(Time, Value)` |
| --- | --- | --- |
| `AC_ApesStoneHand_E_Die_F` | `Exports[14].Properties/Notifies[1]`, `Execution` | `(0, 1)` → `(3, 800)` |
| `AC_ApesStoneHand_E_DamFinalblow` | `Exports[18].Properties/Notifies[1]`, `Execution` | `(1, 0.000082644576)` → `(6, 999.9998)` |
| `AC_ApesStoneHand_E_DamFinalblow` | `Exports[19].Properties/Notifies[2]`, `ExecutionO` | `(4, -0.000020715945)` → `(6, 2000)` |

실제 수정은 `/Game/_Art/Effects/Monsters/Execution/`의 `M_EN_ApesStoneHandElite_SurfacePreview_Execution` 및 `M_EN_ApesStoneHandElite_EyePreview_Execution` 두 master에 한정했다. 원시 양수 `max(0, max(Execution, ExecutionO))`를 source bone XYZ를 중심으로 증가하는 world-space cm 반경으로 소비한다. 이 단위·원형 경계 해석은 **원작 graph 미확인에 따른 임시 rendering adapter**다. source texture와 기존 UV 배율로 경계 noise를 계산하고, 기존 opacity alpha에 감소 mask를 곱한다. 조정 가능한 `KZExecutionBoundaryWidth=10cm`는 몸 크기에 비해 좁은 전이 경계를 위한 어시스턴트 임시값이며 원작 `Test_ExecutionStr=150/20`의 단위나 의미로 대체하지 않는다. source MI scalar/vector/texture 값, 원시 곡선, 기존 기본 shading은 수정하지 않았다.

두 master의 저장·NullRHI compile과 shader input 보존을 확인했다. 이 결과만으로 실제 몸의 dissolve 화면이 정상이라고 선언하지 않는다. `ExecutionRadiusRevision.json`은 이후 조명 수정에서도 bytes를 유지한 정본이며, 두 master의 수정 후 SHA도 그대로 보존한다.

### 실제 RHI에서 확인된 조명 fallback과 별도 수정

`PrivateMonsterRuntimePIE/Attempt2/PrivatePIE.log`에서 `M_MonsterLightOnly missing usage flag ParticleSprites! Default Material will be used in game.`를 확인했다. 원본 SimpleLight03의 component-light를 Cascade로 표현하는 zero-opacity 재질에 sprite renderer 사용 flag가 빠진 문제였다.

root 소유 별도 commandlet PID 20556에서 `Scripts/Art/monster_vfx_light_usage_repair_20261008.py`를 실행했다. 실제 수정은 `/Game/_Art/Effects/Monsters/Light/M_MonsterLightOnly`의 `UMaterial.bUsedWithParticleSprites=false→true` 하나다. zero-opacity constant·연결·원본 light 값은 그대로이며 compile errors는 0이다. 다른 private Effects 2494개와 private Source 99개가 byte 동일했고, Art 후보 457개의 현재 SHA를 다시 검사했다. 향후 importer도 construction tag guard 밖에서 이 flag를 설정하도록 보완했다.

`Resources/LightUsageRevision.json`의 status는 `passed`다. 원본 package는 `BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Light/FP_SimpleLight_03`, source SHA는 `50fe75f7b1cbd56f105b98610be29ed85c90557a9889f78214498c4af76bf6db`다. 변경 전 asset/reports는 `Resources/LightUsageRevisions`에 보존했다. NativeAdapterMap 47개와 기존 ExecutionRadiusRevision은 변경하지 않았고, 이전 radius proof → LightUsageRevision → 현재 ArtCandidateManifest/FinalResourceAudit의 SHA chain으로 검사한다. 조명 수정 이후의 실제 RHI 재검사는 아직 완료하지 않았다.

### RHI 실패 범위·재개 조건

Attempt2는 editor exit code 0이지만 native `Khazan.MonsterVisual.PIE`와 Driver는 **failed**다. 실제 native assertion은 대표 clip 두 개의 resource 관측 부재와 Apes paired/death material consumer 부재를 보고했다. saved BP 및 mesh의 저장 reference를 확인한 결과 실제 Apes slot은 `CM_M_ApesStoneHandElite_{Face,Body,Leg,Eye,Dissolve}` NON-V3 MI이고, 원본 visual override는 V3 MI를 가리켜 그대로는 exact-object binding이 맞지 않는다. source NON-V3/V3의 Tex_D와 Eye 색상, Body PollutionPatternScale 차이도 확인했다. 실제 현재 body shading을 보존하면서 source V3 이벤트를 현재 slot에 대응시키는 명시적 binding과 fresh native 검증이 필요하며, 기존 BP/mesh/shared MI를 이 기록에서 수정하지 않았다.

Attempt2 PNG는 900개 제한에 먼저 도달해 인간 네 가족만 저장됐다. Apes/Yetuga, Trail, Rim, Execution, Frozen 후반 화면의 visual pass 근거로 사용할 수 없다. root는 capture 제한을 보완해 별도 RHI 재검증을 준비하고 있다. QA 카메라·샘플 수는 원작 gameplay 수치가 아니다.

Main 전달 helper `Scripts/Art/deliver_monster_vfx_main_20261008.py`는 기본적으로 Saved manifest만 준비하며 root가 최종 proof를 갖춘 뒤 명시적 `--apply`로 실행한다. Source whitelist는 runtime 9개와 DEV test 2개, 합계 11개다. immutable Main baseline Source 96개와 현재 private Source 99개가 맞으며 새 파일은 notify class의 `.h/.cpp` 두 개와 DEV test `.cpp` 한 개뿐이다. 새 runtime class는 기존 Ability/actor 수명을 소비하는 `KZAnimNotifyState_MonsterVisual` 하나이며 추가 manager/component는 없다. Light proof chain 검토와 Python AST 검사는 통과했지만 helper의 Main apply는 실행하지 않았다.

재개는 root의 현재 slot·MI parent read-only probe → source alias/현재 uniform 보존 처리 → 최신 cold build → fresh saved readback → 인간 네 가족과 Apes/Yetuga 및 특수 효과/사망 frozen 실제 RHI → root PNG 확인 → Player 회귀 → 현재 SHA에 묶인 integrity proof → guarded Main 전달 순서다. root의 최종 성공 보고 전까지 Main 반영·화면 품질·원작 전체 일치는 미완료로 둔다.


<!-- MonsterVFX_ApesGrapple_Rim_PrivateCheckpoint_20261010 -->
## 2026-10-10 20:11 KST — Apes 현재 material alias 적용·Rim 표적 RHI, 최종 시각 판정 전

현재 private Art 후보는457개이며 원본/renderer adapter47/GPU Decal curve7과 기존 source 자료를 재사용한다. 전체 재추출·487 Sequence 재저작은 하지 않았다. Apes 현재 NONV3 슬롯 대응은 `Resources/ApesCurrentMaterialBindingEvidence.json`의 정확한5개 alias를 기존 원작 V35행에 추가한 명시적 프로젝트 binding adapter다. `Authoring/ApesCurrentMaterialBindingRevision/Applied.json`은 State5/Sequence2만 저장하고 나머지497 author 파일·original Main-before journal·source/effect fields 보존을 확인했다. current uniform 복사로 현재 Tex_D/색/비율을 보존하며 BP/mesh/원본 MI를 변경하거나 NONV3와V3의 외형 동등성을 주장하지 않는다.

원작 Apes Grapple 앞/뒤01/02와 현재 InGame 사본은 각각 Particle4/material0이다. material State5는 FinalBlow3+Die_F2에만 존재한다. 현재 paired Grapple에 FinalBlow dissolve가 연결됐다는 해석과 그 terminal shader 검증 주장은 철회한다. 필요한 producer가 없는 paired Execution은 미검증이며, 원작 source에 없는 dissolve를 QA 성공을 위해 추가하지 않는다. RHI3 failure20은 이 잘못된 paired replacement/value 기대였고 ordinary Death에서는 Execution800/consumer5를 실제 관측했다.

[PrivateRimQA/Attempt2/Driver.json](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt2/Driver.json)은 Damage_Disease를 실제 compatible WeaponV2 skeleton의 BP EnemyWeapon_R에 재생하여 overlay MID 생성·감쇠·자연 종료 baseline 복원에 통과했다. body skeleton에 임의 재생하지 않았다. 실제 RHI PID29484/38.187s/exit0, capture20, package save0/asset mutation0/material fallback0이다. 원작 RGB(2,0,0)/Duration1.2s/BlendOut1.2s 및 source graph 미확인 Fresnel adapter 구분을 유지한다. root는 PNG를 직접 확인했으나 역광에서 rim의 시각 강도를 확정하지 못해 추가 QA 중이다. 데이터/cleanup 통과와 최종 visual pass를 구분한다.

최신 private Build13은16.422s/exit0, current DLL `29bd3daf…a9b`이며 원작 Grapple source에 맞는 paired QA만 보완했다(추가 게임 코드 수정0). SavedReadback4는487 Sequence/3342 State/Death6 및 선택499 파일 byte 불변을 확인했다. PrivateMonsterRHI4는 실행 중이다. 실제 전체 native·Player 회귀·PNG 품질 및 최신 Main source/resource proof 결속과 전달·새 Main 검사까지 남았으며 **MonsterVFX Main 미전달/최종 화면 품질 미완료**다. 별도 CombatReaction Main 완료와 혼동하지 않는다.


<!-- MonsterVFX_VictimRimBuild18_Checkpoint_20261010 -->
## 2026-10-10 21:17 KST — Decal 원본 생략 field와 정책 개정·Rim 실제 양성 PNG·Yetuga 경계

### 피해자 animation이 소유하는 Decal43 창

원본 Damage26/Death17 Decal의43개 instance export에는 `bOnAttackSuccessed`가 없다. 정확한 source package/JSON/ZIP export와 SHA는 [VictimDecalPolicyRevision의 source_absent_field_evidence43](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VictimDecalPolicyRevision.json)에 보존했다. 원작 CDO 기본값/조건은 미확인이므로 생략을 원작 false로 단정하지 않는다. 기존 Blood 이름에서 inferred true로 채웠던 조건은 원작 검증값이 아니었다. 새 명시적 프로젝트 policy는 피해자 Damage/Death source sequence가 원래 Decal timing window를 소유하게 하며 해당 추론을 대체한다. fake hit나 새 피해 상태/producer는 없다.

probe29200/apply30084 passed, 최종 revision SHA `9b3609b797c23f64cf66169515f1d456d9783b4ad522c39fab7e2231fe7516ec`다. Effect43개 `bOnAttackSuccessed=true→false`만 변경하여 Sequence26을 저장했고 Main mutation0이다. 원본 Effect의 material/surface/size/lifespan과 다른 State fields·Notify timing/GUID·raw pose/curve는 그대로다. whole-sequence before/after/saved export의43 bool line 외 차이와 나머지473 author asset 차이는 없다. original499/Main-before journal·plan·Apes Applied·ContentRebase는 immutable로 보존하고 새 report의26 SHA override만 후속 검사에 사용한다. fresh [SavedReadback](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json)은487 Sequence/3342 State/Death6·victim43/26 marker/선택 byte 불변·저장0을 통과했다.

### Rim8의 실제 붉은 신호와 source 값 보존

[Rim8 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt8/Driver.json)는 actual DLL16 `11dd0c914b84132f2785e274d70738f631b38d6de5b9e31040f4a08752e58805`에서63 captures/package0/asset mutation0/material compile failures[]다. Damage_Disease를 actual EnemyWeapon_R/compatible WeaponV2 skeleton에 재생했다. Root가 직접 검토한 양성 화면은 [PNG24 StatisticsSynced SourceOverlay](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt8/024_Halberd_Rim_Diagnostic_StatisticsSynced_SourceOverlay_WeaponFrontOblique.png), [PNG27 OriginalExposure SourceOverlay](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt8/027_Halberd_Rim_Diagnostic_Recompiled_OriginalExposure_SourceOverlay_WeaponFrontOblique.png), [PNG39 ManualEV0 SameMIDBase](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt8/039_Halberd_Rim_Diagnostic_Recompiled_ManualEV0_SameMIDBase_WeaponFrontOblique.png)다.

GetStatistics가 compile 완료를 기다린 직후 PNG24에 붉은 Rim이 나타났고 explicit RecompileMaterial 전이었다. 원래 exposure의 후속 PNG27에도 나타나 QA exposure를 제품 수치로 변경할 근거로 쓰지 않았다. source RGB(2,0,0)/Duration1.2초/BlendOut1.2초 및 actual MID weight를 유지했고 shader/master/MI 저장 bytes와 graph는 동일했다. in-memory diagnostic compile은 저장하지 않았고 owner overlay/slots·Nanite disallow·camera 설정을 복원했다. 이는 Editor 첫 shader 준비 지연의 추론을 지지하며 원작 native shader pixel parity를 검증한 결과가 아니다.

Root가 기존 Source 첫 MID 생성 전에 WITH_EDITOR EnsureIsComplete만 추가했다. Build17 DLL 잠금 LNK1104 실패는 보존했고 종료 후 [Build18](../../Saved/ImportReports/MonsterVFX_20261008/Build/Attempt18/Exit.json)이5.234초/exit0·입력 불변으로 통과했다. 현재 DLL `1506acfae8845cc87e8ada5cbe674d22dba2668a020bdfc366a2623c70576304`의 regular Rim9는 GetStatistics/RecompileMaterial 없이 실행 중이다. 최초 표시와 자연 종료의 새 actual PNG 검토 전에는 Source 보완의 최종 visual pass로 기록하지 않는다.

### Yetuga writer 확인과 cleanup 재검증

[Yetuga2 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt2/Driver.json)는38 captures/failed/save0다. Root는 actual snow writer의 main/depth/shadow=false와 [PNG10](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt2/0010_Yetuga_Attack_NormalAtk01_03_Playing_011_FrontOblique.png)의 dome 소실을 확인했다. 이후 cleanup 표본의 world-owner Breath2 및 actor-owner BodyDust1 active로 검사가 실패했으므로 전체 성공으로 읽지 않는다. 원본 finite Breath 최대3.5초 대비 QA1초 관측 간격 및 BodyDust lifetime/sentinel 근거를 표적 확인 중이다. 수명/pose/scale/재질을 바꾸지 않고 원본 수명에 맞는 QA 관측 여유만 보완한다.

다음은 current DLL/saved revision 확인 → regular Rim 최초 red/복원 PNG → Yetuga lifetime 근거·fresh cleanup/근접 PNG → Root full visual과 current DLL Monster/Player → original Art457/author499와 별도 ContentRebase6·Victim26를 결속한 candidate → closed Main CAS/guarded 선택 전달 → fresh Main saved/RHI/Root PNG/finalize다. Main 전달은0이고 사용자 Main PID9460은 Root 관측상 열려 있다. 전체 추출/import/author/retime·Apes alias apply를 다시 실행하지 않는다.


<!-- MonsterVFX_RegularRim9_Positive_20261010 -->
## 2026-10-10 21:18 KST — Build18 일반 Rim 최초 표시 실제 통과·전체 검증 진행 중

앞선 checkpoint 직후 [PrivateRimQA Attempt9](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/Driver.json)가 passed로 종료했다. actual loaded DLL SHA는 `1506acfae8845cc87e8ada5cbe674d22dba2668a020bdfc366a2623c70576304`, diagnostic_mode=false, PNG30/package saves0/asset mutations0/material compile failures[]이며 [Exit](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/Exit.json)는62.594초/exit0이다. Driver SHA는 `cd5af174d284ec6e6696a31c313f4b8f5e673eaf43c816e13e7e344169365a0f`다. Root는 [Active03 Front PNG006](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/006_Halberd_Rim_Active_03_WeaponFrontOblique.png)와 [Active06 Front PNG009](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt9/009_Halberd_Rim_Active_06_WeaponFrontOblique.png)를 직접 보고 첫 표시의 강한 붉은 Rim을 확인했다. 별도 GetStatistics/RecompileMaterial/노출 변경 없이 기존 editor shader 준비 보완이 실제 첫 화면에서 작동했다. 원작 RGB/weight/시간·저장 shader asset을 변경한 결과가 아니다.

이 결과로 regular Rim의 최초 표시·fade/복원 검증은 통과했지만 MonsterVFX 전체/Main 전달 완료는 아니다. Root가 같은 Build18의 PrivateMonster full RHI6을 시작했고 Player 회귀 및 원본 lifetime에 맞춘 Yetuga cleanup/시각 재검증이 뒤따른다. 최종 candidate SHA 결속·closed Main CAS/guarded 전달·fresh Main saved/실제 RHI/Root visual/finalizer까지 앞 절의 재개 순서를 유지한다. Source/Art 후보는 Build18 이후 동일하고 이번 보충은 문서만 추가했다.


<!-- MonsterVFX_CurrentQAExternalB_Checkpoint_20261010 -->
## 2026-10-10 21:39 KST — Yetuga 세 clip의 실제 재생·원본 tail bound 검증 범위

[PrivateYetugaQA Attempt3](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt3/Driver.json)는 actual DLL1506/82.578초/104PNG/package0·asset mutation0으로 passed다. 원본 saved NormalAtk01_03/RushGrab_Slow/Recovery_StaminaRecover를 실제 BP/mesh에서 재생했고 Root는 세 PNG를 직접 검토했다. actor-tagged Root trail과 recovery NI renderer adapter, 종료 후 owned visual 정리 및 baseline 재질 복원을 확인했다. 기존 source layout·timeline·수명은 보존했다.

수명 근거는 [TailLifetimeEvidence](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/TailLifetimeEvidence.json)의 정확한 source package/export/LOD0 Lifetime이다. source serialized 전체 최대6/7/6초는 같은 세 clip 순서의 보수적 bound이며 active-or-unknown emitter 최대는6/6/6초다. +1초는 QA scheduling 여유여서 실제 관측시간7/8/7초로 계산했고 원작 gameplay 값으로 주장하지 않는다. 실제 PSC time scale을 반영하는 관측이며 원본 Duration·Retiming·Particle Lifetime을 다시 author하지 않았다. static 보고서의 당시 natural_end_verified=false는 이력으로 남고, 새 actual playback 결과는 Attempt3 Driver를 출처로 읽는다.

이 표적 visual/cleanup 통과와 regular Rim9의 양성 화면을 전체 Source shader/NI graph 복원·모든 pose의 품질 통과로 확대하지 않는다. recovery 화면의 dust edge와 attack 상체의 희미한 geometry는 owner/material chain을 분리 확인하는 추가 RCA 대상이며 다른 DevMap actor FX라고 단정하지 않는다. 원본 cooked graph stripped 한계와 임시 native renderer adapter의 출처 상태를 유지한다.

[DeliveryReadiness](../../Saved/ImportReports/MonsterVFX_20261008/DeliveryReadiness.json)은 Art457 및 기존 baseline Effects2034 byte 불변을 확인한 Main 전달 전 기록이다. Native6는 Input B 오류로 중단된 실패 이력이고 외부 Authoring09의 저장된5개 baseline을 사용해 Root Native7 session72778이 진행 중이다. full Native/Player·Root 전체 PNG/VisualQA·schema RCA/candidate·guarded 전달/fresh Main 검증은 남아 있다. MonsterVFX Main 전달0이며 Main에서 최종 표현 완료라고 기록하지 않는다.


<!-- MonsterVFX_SharedPolishIntake_Native7QA_20261010 -->
## 2026-10-10 22:00 KST — 실제 atlas mask의 정정과 공유14 최신 baseline

반입 전 [SharedDustShaderReadback](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt1/SharedDustShaderReadback.json)의 actual master SHA는 `93814b114851baa1cd508b76ebdbade1589e12be23ccd62ab1435e8eb3b6c1d2`다. Opacity의 실제 연결은 `Tex_Opa.R(full UV) × ParticleColor.A × Opa_Str × Tex_SubUV.R(Custom_0 atlas UV)`이고 Custom_0의 Age는 DynamicParameter.SubUV_frame, grid는 SubUV_U/V다. Emissive는 별도 ParticleRelativeTime 기반 Custom_1 atlas의 Tex_SubUV.RGB×ParticleColor.RGB×Emi_Pow다. MI02는 Tex_Opa=T_Flat_White/Tex_SubUV=FTW_Subuv_Smoke_007/grid8×8이므로 white만으로 전체 card alpha가 된다는 이전 단정은 철회한다. source Breath Dynamic50의 SubUV_frame0→1도 실제 metadata에 있어 두 시간축이 불일치한다고 즉시 단정하지 않는다.

MI06 actual effective Tex_Opa/Tex_SubUV는 같은 T_Smoke03_SubUV_9x9/grid9×9이며 앞의 full UV mask와 뒤의 atlas mask가 함께 곱해진다. 원본 instance의 Opa_SubUV_Switch=true override는 source 확인값이지만 native graph에 switch가 없어서 getter=false였으며 이를 원작 CDO false로 표현하지 않는다. 이 연결의 원작 shader 일치나 관측한 ground-ring edge의 직접 원인은 미확인이다. [Diagnostic1](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt1/Driver.json)은 pause editor setter에 따른 source pose0초 reset으로 동일 pose 비교에 실패했고 game time/camera는 불변·shader bytes/Source/asset writes0이었다. SingleNode.set_playing(False) 기반 QA 보완은 준비만 됐고 actual visual pass가 아니다.

[외부 Delivered17](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/Delivered.json) SHA `a75fa980…7ed7fa9`의 UTC12:47:50 선택 전달로 Main shared master가 `f5511be641c2a56b0cbe335511c8dc97d8d7acf6b5d40e30cdf5d29ac0e06954` 및 기존 resource14 새 bytes로 바뀌었다. 외부 상태는 fresh Main validation pending이다. [SharedEffectsRebaseRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SharedEffectsRebaseRevision.json) SHA `33e13db1…bb422`는 그 exact14를 private에 byte-copy한 passed 증거로,2034 reuse 중14 승인 갱신·2020 보존 및 own Art457 SHA/Main-before CAS 불변을 확인했다. 원본 source identity/ArtManifest/ResourceAudit/AdapterMap/Light·Radius와499 journal은 덮어쓰지 않았으며 새 리소스·import/resave·Main 제품 수정0이다. 위 반입 전 graph를 반입 후 실제 graph 검사로 대체하지 않는다.

Native7은449.312초/1390 captures/exit0에도 obsolete X press 대 current B grant의 QA assertion1로 failed다(Engineering 정본). 새 Build19의 current semantic Source와 shared14에 대한 fresh saved/전체 RHI·Player/Root visual/candidate 및 guarded 전달/fresh Main은 남아 있다. **본 MonsterVFX Main 전달0·전체 완료/최종 visual pass 미확정**이다. 원본487 전체 author·457 전체 import나 임의 MI 대체를 재실행하지 않는다.


<!-- MonsterVFX_Build19_Saved7_Diagnostic2_Native8_20261010 -->
## 2026-10-10 22:16 KST — current shared shader의 동일 pose 진단·fresh 전체 캡처 검증 범위

[Diagnostic2 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt2/Driver.json)는 current Build19 actual DLL `b84df875135de6fbc786650a6481ad81d3401eb29d6300bd08b45315559e311a`로 passed이며 [Exit](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt2/Exit.json)는 PID25084/62.625초/exit0다. PNG102·두 실제 source clip RushGrab_Slow/Recovery_StaminaRecover의 same_pose/same_game_time/same_camera_per_view가 모두true, owned filter 및 원래 SingleNode 재생 상태 복원·baseline material/cleanup도 passed다. 저장0·asset mutation0·diagnostic shader bytes 불변이며 shader A/B 변경을 수행하지 않았다.

Root의 실제 확인 화면은 [0018 NormalScene](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt2/0018_Yetuga_Attack_RushGrab_Slow_Diagnostic_NormalScene_FrontOblique.png)/[0020 OwnFocus](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt2/0020_Yetuga_Attack_RushGrab_Slow_Diagnostic_OwnFocusAndTaggedWorldPSCs_FrontOblique.png), [0068 NormalScene](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt2/0068_Yetuga_Recovery_StaminaRecover_Diagnostic_NormalScene_FrontOblique.png)/[0070 OwnFocus](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt2/0070_Yetuga_Recovery_StaminaRecover_Diagnostic_OwnFocusAndTaggedWorldPSCs_FrontOblique.png)의 clean plate 관측이다. 동일 pose 비교를 허용한 QA 재생 정지만 보완했고 원작 clip·particle lifetime·scale·geometry를 재author하지 않았다. source lifetime bound6/7/6초 및 QA margin1초의 기존 출처 구분은 유지한다. 반입 전 MI02 white→full-card 단정은 철회된 상태이며 원작 cooked graph 완전 복원이나 모든 pose의 pixel parity를 주장하지 않는다.

[Shared14 revision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SharedEffectsRebaseRevision.json) SHA `33e13db1…bb422`와 Source intake `4a44ccc6…77c08e4`를 사용하는 Build19는85.828초/exit0, fresh Saved7은85.813초·487 Sequence/3342 State/Death6·Victim43/26·shared2034/선택499 불변·saves0으로 passed다. own Art457·2020 unchanged reused bytes·원본 report/GUID/pose/curve 계약을 유지한 후보다. [Native8](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt8/Driver.json)은 동일 actual loaded DLL의 Success/passed·1568 captures(0000…1567)/package0/compile failures[]이고492.813초/exit0으로 종료했다. 이는 새 전체 runtime 검증이며 Native7의 obsolete X failure를 소급 성공으로 바꾸지 않는다.

현재 Player 회귀는 Root wrapper session45759 실행 중·pass 미확정이다. 전체 representative PNG/최종 VisualQA와 candidate SHA 결속, guarded Main 전달 및 fresh Main saved/실제 화면 확인은 남아 있다. 별도 Player polish Main 시각 hold와 source shader adapter의 미확인 경계를 보존한다. **이번 MonsterVFX Main 전달0·전체 visual pass/최종 완료가 아니다.** 정확 재개는 [Art continuity](ART_WORK_CONTINUITY.md)의 이 날짜 절을 따른다.


<!-- MonsterVFX_PrivateMaterialRepair_LateDiagnostic_D00Tail_20261010 -->
## 2026-10-10 22:52 KST — 실제 Roar02·D00 pixel 소유 정정과 작은 shader adapter 수정

앞22:22의 Roar01 원인 추정은 철회한다. [LateDiag3 review](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt3/DiagnosticVisualHoldReview.json)의 동일 source pose2.3321199초/world time2.5276663초에서 WithoutRoar01은 검은 면 유지·OnlyRoar01은 깨끗했고, WithoutRoar02(0026/0027)는 깨끗함·OnlyRoar02(0028/0029)는 검은 spiral card를 재현했다. producer는 own `KZMVFX_f7a3c448d031f689d731840f`/FP_Boss_Yetuga_Roar_02 PSC이며 WorldSettings outer만으로 다른 actor 효과로 읽지 않는다. 이 정정은 기존 이미지/실패를 지우지 않는다.

[WPO 부모 Repair](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Roar02/Attempt1/Repair.json)은 기존 FM_WPO_Trail_A의 발광 입력을 Emi_Tex RGB로 연결하고 Opa_Tex RGB density에 원본 Opa_pow(자식18 override1.5)·Opa_str·실제 DynamicParameter channelA/Opa_Dissolve를 소비하도록 opacity를 보완했다. maxRGB density 및 누락 stream의0 identity는 원본 graph 복원이 아닌 명시된 renderer adapter다. 실제1 save/17.406초·SM6 163/344/6, SHA `57c664d6…d5b20ab`; PS/MI/texture·원본 scale/color/timing은 그대로다. [LateDiag4](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt4/Driver.json)은49.469초/50PNG·passed이며 Root가 실제본 [0022 Normal](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt4/0022_Yetuga_Recovery_StaminaRecover_Diagnostic_NormalScene_FrontOblique.png)과 [0034 OnlyRoar02](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Diagnostics/Attempt4/0034_Yetuga_Recovery_StaminaRecover_Diagnostic_OnlyOwnTemplate01_FrontOblique.png)은 후반 검은 면이 없다. 이 source pose2.2320659초 비교를 전체 timeline positive·regular3-case 통과로 확대하지 않는다.

Apes Death의 흰 사각 면은 [D00 QA1](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt1/Driver.json)의 Normal0000/WithoutD000004/OnlyD000006 실제 화면으로 D00 소유가 확인됐다. 전체 tail 실패와 pixel attribution을 구분한다. [Decal 부모2 Repair](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Decal/Apply1/Repair.json)은 기존 M_New_Decal_Deferred_D·FM_Decal_Deferred_D의 source 선언/값을 보존해 polar mask와 추가mask를 사용하고, unit disk 밖 기여0 및 actual texture texel-centre clamp로 wrap 경계의 흰 면을 제한했다. 이는 stripped cooked topology 대신 해석한 표현 adapter이며 원작 pixel parity는 미확인이다. 실제2 save/56.109초·각 SM6 512/344/6, SHA `c717eefe…82f5a5`/`8a1e4c66…fad206`; PS/MI/나머지455 Art·499 author·Main 변경0이다.

QA1 tail 잔존은 D00이 아니라 Mi_PD_Blood_SuperRound 원본 LifeSpan30초였다. 원본 AC_ApesStoneHand_E_Die_F Exports[5]/Notifies[6]의 D00 LifeSpan9와 Exports[6]/Notifies[15]의 혈흔30을 ZIP JSON SHA `e73733e0…3ecb9`에서 검증했다. [QA-only tail revision](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/TailObservationRevision/TailObservationRevision.json)은 원본 수명 유지·D009+기술여유1/전체max30+여유1로 관측만 보완했다. [D00 QA2](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt2/Driver.json)는90.187초·same pose/time/camera/복구·자연 소멸·저장0 passed지만 overall_visual_pass=false다. Root의 전체 repaired 시각 승인과 fresh Saved/네 회귀/candidate/Main 전달·fresh Main은 남아 있으며 **본 MonsterVFX Main 전달0·최종 완료가 아니다.**


### 2026-10-10 22:53 KST — 정확한 결속 report와 Roar02 양성 관측 대기

위 결속 report의 실제 경로는 [Authoring/VisualMaterialRepairRevision.json](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json), SHA `138dc65c…e107a`다. late4 clean pose는 검은 면 제거의 제한 관측이며 Roar02 효과의 정상 positive visibility·전체 재생 품질을 아직 증명하지 않는다. receipt 자체도 overall_visual_pass=false이며 Root의 새로운 네 회귀와 전체 대표 화면 검수를 요구한다.


<!-- MonsterVFX_138_FourFreshRHI_D00Hold_202610102348 -->
## 2026-10-10 23:48 KST — 재질 revision 이후 네 실제 회귀 통과·D00 바닥 양성 검증 보류

private [WPO 부모1](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Roar02/Attempt1/Repair.json)과 [Decal 부모2](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Decal/Apply1/Repair.json)를 결속한 [VisualMaterialRepairRevision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json) SHA `138dc65c…e107a`를 유지한다. 기존 PS/MI/texture·원본 attachment/scale/color/Notify 시간/데칼 수명과 Art457/author499/Shared14 원본 보고서는 덮어쓰지 않았다. [Saved8 readback](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json)의 graph/pin readback3과 bytes 불변 passed, [Native9 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt9/Driver.json)/[Player2 Driver](../../Saved/ImportReports/MonsterVFX_20261008/PrivatePlayerRegression/Attempt2/Driver.json)/[regular Rim11](../../Saved/ImportReports/MonsterVFX_20261008/PrivateRimQA/Attempt11/Driver.json)/[regular Yetuga5](../../Saved/ImportReports/MonsterVFX_20261008/PrivateYetugaQA/Attempt5/Driver.json)의 새 실제 current DLL 통과는 이 revision 뒤 실행의 기술 증거다. 원작 cooked shader 완전 복원이나 전체 PNG 품질 승인을 의미하지 않는다.

Root는 [Native9 Roar02 실제 화면1216](../../Saved/ImportReports/MonsterVFX_20261008/PrivateMonsterRuntimePIE/Attempt9/1216_MonsterVFX_Yetuga_Recovery_StaminaRecover_Sequence.png)의 양성 helix를 실제로 확인했다. 이는 late4 clean pose 이후 필요한 positive visibility 증거이며 Roar01 temporal 추정의 철회와 Roar02 only/exclude 소유 확정은 유지한다. D00은 [D00 QA6](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt6/Driver.json)의14PNG/87.156초·same pose/time/camera/복구/자연 소멸/저장0을 통과했지만 Root의 순수 바닥 OnlyD00NoParticles vs NoDecalsNoParticles 비교에서 양성 footprint가 아직 확인되지 않았다. floor receives_decals=true, 원래 LifeSpan9/TimeScale1/CurveIndex0 및 actual MID 기록을 보존하며 화면이 깨끗하다는 이유로 효과가 정상 출력된 것으로 판정하지 않는다.

정정: actual Custom0 P5는 M_New ScalarParameter_10/FM ScalarParameter_8의 **FadeOut=1**이다(두 부모의 node index가 서로 다름). M_New node8의 Param_1=.2를 P5로 잘못 읽었던 설명과 “FadeOut 미연결”, .2를 곱한 opacity 추정은 철회한다. P0는 Constant4Vector RGBA1, P6는 원본 Param RGB(.12,.12,.12)만 소비하며 alpha0는 opacity에 곱하지 않는다. Source MaskTex/MaskATex 모두 FT_Line_01, source MaskTexUV=(1,.866667,0,.17)/MaskATexUV=(1,.866667,0,.1), 기존 Custom1 수명 곡선 연결은 변경되지 않았다.

원본 [FT_Line_01 PNG](../../Metadata/MonsterVFX_20261008/HumanOriginal/Payload/BBQ/Content/_Kazan_/Art/VFX/VFX_Texture/Shock/FT_Line_01.png) SHA `0d0d6eb10a961dd1158899aabbf3730b39cfeb6581d1386acedb421c2f912a14`는512×512 RGBA8이며 중앙(255,255)/(256,255)/(255,256)/(256,256)이 모두(255,255,255,255)다. 원본 texture JSON SHA `ea5f80f520377e2096f4ec960f27500914723553dc88958b6f1fb7946d1a475d`의 SRGB=false/AddressY=TA_Clamp를 확인했다. 현재 native FT_Line_01 SHA는 `28e753086d97766c40364580c9a87deda55ea3c806184ee9d1ccbca8c551006b`이며 source PNG 확인을 GPU texel readback으로 표현하지 않는다. UV(.5,.5) diagnostic은 이 원본 흰 texel 근거를 사용할 수 있지만 제품 UV 값이나 original graph 복원으로 기록하지 않는다.

[D00 QA4](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt4/Driver.json)의 미노출 get_component_location API 실패는0PNG/모든 finally 복구 true/bytes 불변이며 보존한다. QA5/6의 카메라·exposure·source curve phase·NoParticles/NoDecals 필터는 QA 조건이지 gameplay 변경이 아니다. 다음 owned MID-only curve bypass/white Param/확인된 흰 texel UV 진단도 실제 원본 입력과 구분하고 exact restore·shader/asset save0를 요구한다. 결과가 나와도 Source/asset 수정 승인이나 원작 pixel parity를 자동으로 의미하지 않는다.

현재968 선택 CAS와 original/Shared/재질 revision은 passed다. 외부 Player Shock/SubUV follow-up Main2는 아직 없으므로 기존 Shared33e13/재질138dc report를 재작성하지 않는다. **D00 바닥 양성·Root VisualQA/candidate/Main 전달은 보류**이며 정확 다음 절차는 [Art continuity](ART_WORK_CONTINUITY.md)의 이번 checkpoint를 따른다.



<!-- MonsterVFX_DecalReauthorStaging2_202610102357 -->
## 2026-10-10 23:57 KST — QA8 알파 분리·staging 보존과 새 Decal2 적용, 전체 검증 대기

[QA8](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt8/Driver.json)의 D0020은 source RGB(.12,.12,.12)+alpha1, E0022는 white RGB+alpha0였다. 둘 다 C의 constant UV를 실제 원래 UV로 복원하고 CurveIndex=-1만 유지한 same pose/time/camera·D00-only/noPSC 비교다. Root가 D는 거의 보이지 않고 E는 부드러운 원으로 관측해 Param alpha가 지웠다는 해석은 제외한다. Param 벡터를 곧바로 색으로 해석한 연결은 원작 근거 미확인이라 철회했다. 원본 Param/마스크·크기·수명·시간축을 바꾸지 않고 기존 ImageRGB×PC fallback을 유지하는 최소 shader adapter로 전환한다. stripped 원작 graph의 정확 색/공간 의미·pixel parity는 여전히 미확인이다.

23:51:21 KST [Staging2](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Decal/ReauthorStaging2/Staging.json)는 private M_New/FM 두 부모만 Apply1/Before의 정확 원본 bytes로 복원하고 이전 c717…/8a1e… 수정2와 원본138을 보존한 중간 기록이다. append 전23:54분 Root [Probe2/Apply2](../../Saved/ImportReports/MonsterVFX_20261008/MaterialVisualRepairRevision/Decal/Apply2/Repair.json)가 실제 passed로 끝났고 현재2는 `52d746d6…474dc0a`/`c4eb1ca6…5d33798`다. Main/Source/native/PS/MI/time 및 나머지455 Art 보존이다. 새 revision·fresh Saved/네 회귀·정상 D00 positive·Root 시각 승인/guarded Main/fresh Main은 아직 남는다. 이전138 기반 성공을 현재2의 최종 visual pass로 읽지 않는다.


### 2026-10-10 23:58 KST — current revision6309 실제 결속 추가 확인

[현재6309 revision](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json)은14:56:40 UTC에 실제 생성됐고 기존138의 Main/Private 원본은 [Archive.json](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairHistory/Revision1_138dc65c/Archive.json)으로 보존됐다. 새 Apply2 부모2의 기술 저장 결과와 실제 정상 D00 화면을 분리한다. Root QA9 owned session19559가 실행 중이며 overall_visual_pass=false, 새 revision의 fresh Saved/네 회귀·Root/guarded 전달/Main fresh는 아직 완료되지 않았다.


<!-- MonsterVFX_6309_Saved9_QA10_PSCBlocker_202610110018 -->
## 2026-10-11 00:18 KST — D00 정상 양성 확인·세 PSC 검은 카드 보류

[current6309](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json)에 결속한 [Saved9](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/SavedReadback.json)는 PID31520/99.75초/exit0·graph3/readback·bytes 불변/저장0 passed다. [QA9](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt9/Driver.json)는 PID23764/84.985초/24PNG/exit0·기존 상태와 자연 수명 복원을 통과했다. Root는 정상0008 D00-only/noPSC의 부드러운 흰 원과0012 무데칼 바닥을 실제 비교해 양성을 확인했다. [RootD00Review](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt9/RootD00Review.json), SHA `6e68bf2d…fab27e0`의 승인은 D00에 한정된다. Normal0000의 검은 PSC 카드로 전체 시각 검수는 HOLD다.

기록 직전 [QA10](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt10/Driver.json)이 PID17540/89.328초/30PNG/exit0·복구/저장0 passed로 완료됐다. Root 실제0024의 FP_DeathEffect는 검은 카드1개,0026의 world fall PSC는4개,0028의 다른 world fall PSC는 여러 카드와 회색 checker를 보였다. 세 producer가 모두 양성이며 FP 임시 burst12만으로 단일 원인을 확정하지 않는다. actual template/material slot identity와 current native graph 표적 readback·원인 판단은 대기이며 원작 shader/pixel parity도 미확인이다.

이전138의 네 회귀를6309 검증으로 재사용하지 않는다. [QA7 ReferenceResolution](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/QA7PixelAnalysis/ReferenceResolution.json)은 immutable 분석 `fc5fb913…dd00e0a`를 바꾸지 않고 archived138을 연결한다. 이번 추가는 문서 기록만이며 MonsterVFX Main 전달0이다. Native10 current6309 실행·후속 검증은 [Engineering 정본](../Engineering/MONSTER_VFX_RUNTIME_20261008.md)의 같은 checkpoint를 따른다.


<!-- MonsterVFX_MainDelivered_MainSavedFailed_20261011010443 -->
## 2026-10-11 01:04 KST — Main968 전달 완료·새 Main 저장 검증 실패 확인

앞선 QA10 black/checker 카드 HOLD는 [QA11 Root 검토](../../Saved/ImportReports/MonsterVFX_20261008/PrivateDecalQA/Attempt11/RootShaderReadinessReview.json), SHA `721efae2…768088`의 shader-only 준비 뒤 해소됐다. 비교 대상8 asset bytes를 보존했고 새 alpha-mask 제품 수정을 넣지 않았다. per-GPU fallback identity나 원작 shader topology 복원을 입증한 것은 아니다.

[current6309](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/VisualMaterialRepairRevision.json)의 private Saved9·Native10·Player3·Rim12·Yetuga6와 [RootVisualQA](../../Saved/ImportReports/MonsterVFX_20261008/VisualQA.json), SHA `55178750…802bd15`는 passed다. [Delivered](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/Delivered.json), SHA `12f3af9d…c86603a`로 선택968(Source11+author499+Art457+reused WPO1)을 실제 전달했고 alias는 `UnrealEditor-KhazanMonsterVFX20261008.dll`이다.

전달 후 fresh [MainSavedReadback](../../Saved/ImportReports/MonsterVFX_20261008/Authoring/MainSavedReadback.json)은 PID31324/status=failed·저장0·effect field 대조 실패다. Root가 지목한 event `KZMVFX_f3af66febacc3ab35102cf8b`는 Halberd Damage_FinalBlow_Composite_Variant01이며 연결 FP_BloodSplit_01은 현재 Main에서 누락/작업본에는 존재한다. 그 누락과 실패의 정확한 인과·다른 의존성은 확인 중이고 수정은 아직 없다. 새 MainMonster는 실행 중이며 전체 완료를 주장하지 않는다. 재개는 [Engineering continuity](../Engineering/ENGINEERING_WORK_CONTINUITY.md)의 같은 checkpoint를 따른다.


<!-- MonsterVFX_AdapterSupplement972_FreshMainPending_20261011012157 -->
## 2026-10-11 01:21 KST — 누락 혈흔 adapter4 별도 전달·Main972 재검증 중

[Main1 정확 진단](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/Diagnostics/Main1/Readback.json), SHA `e0fa8f00…5de5b`에서 Halberd FinalBlow event `KZMVFX_f3af66febacc3ab35102cf8b`의 ParticleTemplate만 null이고 나머지 Effect fields는 일치했다. [Private1 registry](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/Diagnostics/Private1/Readback.json), SHA `2d4fc32b…6b8`는 consumer316의 표적 closure22=Main/private 동일18+누락 root adapter4를 확인했다. Union rerun의 reused_native=true/existing_native_sha256=null 분류 때문에 새 global NI→Cascade adapter4가 original Art457에서 빠진 원인이다.

[SupplementalDelivered](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/SupplementalDelivered.json), SHA `d7487b50…1ed44`의 상태는 `FourAdapterDependenciesDeliveredFreshMainRequired`다. `Content/_Art/Effects/Combat/Blood`의 FP_BloodSplit_01/02, FP_Dmg_Blood_Base, FP_Dmg_Blood_Base_BK 네 파일을 기존 Main 파일을 덮어쓰지 않는 strict CAS로 추가해 총972=원래968+별도4다. 원래968/Art457/6309 영수증은 그대로이며 Source/native/material graph/private package 변경0, 이번 asset copy4·save0이다. 기존 private Saved9/Native10/Player3/Rim12/Yetuga6/RootVisualQA는 private bytes가 불변인 범위에서 유지하고 새 Main 검증을 대체하지 않는다.

[FailureHistory archive](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/FailureHistory/Archive.json), SHA `cc4c51ad…66323`는 첫 MainSaved failed와 pre-supplement MainMonster Success(1560PNG/517.265초/exit0)를 보존하며 후자를 최종 proof로 쓰지 않는다. fresh MainSaved2는 Exit0/PID30360로 종료됐고 최종 검증은 대기다, MainMonster2는 진행 중이며 아직 Exit이 관측되지 않았다. FinalVerification은 아직 없다. canonical MainSaved가 첫 failed 값이면 archive로 보존한 역사 값이며 새 시도 완료로 읽지 않는다. 실제 Main 품질 검토와 FinalVerification 전에는 전체 완료를 주장하지 않는다. 재개 명령은 [Engineering continuity](../Engineering/ENGINEERING_WORK_CONTINUITY.md)의 같은 checkpoint를 따른다.


<!-- MonsterVFX_MainComplete_20261011 -->
## 2026-10-11 01:41 KST — current6309 Main 전달·표본 시각 검토 완료

[FinalVerification](../../Saved/ImportReports/MonsterVFX_20261008/FinalVerification.json)의 실제 `MainDeliveredAndFreshVerified`로 최종 선택972(Source11+author499+Art457+reused WPO1+adapter supplement4), six-family Sequence487·지원 source2855+technical sentinel487=State3342·Death6를 완료 확인했다. own decal 부모2/reused WPO1의 current6309, 외부 Source3/Shared14·그 밖의 reused2019·원본 Art/report/backup을 보존했다. fresh Main saved/네 실제 RHI·Root actual 표본 검토를 private Native10(1578PNG/476.359초)·Player3(385/159.64)·Rim12(30/44.719)·Yetuga6(76/99.625)와 분리 실행했다. 새 alias는 `UnrealEditor-KhazanMonsterVFX20261008.dll`다.

Root는 정상 D00 soft-circle, Yetuga Roar02 density/dissolve·Apes Death decal을 확인했다. QA10 black/checker 카드는 QA11 shader 준비 뒤 exact8 assets 불변으로 사라졌으며 신규 alpha-mask 제품 수정/GPU fallback identity 직접 측정은 없다. neutral image RGB·polar mask·Roar02/Apes/Rim shader 및12 Niagara renderer는 공개된 프로젝트 재구성이고 victim Decal43은 source 미직렬화 CDO 복원이 아니다. Camera43/DeepSnow172/status1·snow receiver/correction52/surface selector·Yetuga projectile3·shipping 성능/전체 pixel parity·외부 follow-up/ARCH-86은 완료 밖이다.

원본 Delivered968·Art457을 다시 쓰지 않았다. original union의 reused_native=true/null-baseline 오류로 빠진 global adapter4(FP_BloodSplit_01/02, FP_Dmg_Blood_Base·FP_Dmg_Blood_Base_BK)를 [strict supplement](../../Saved/ImportReports/MonsterVFX_20261008/MainDelivery/AdapterSupplement/SupplementalDelivered.json)로 추가했다. consumer316의 closure22 중18은 Main/private byte-equal였으며 추가4만 전달해 최종972다. 원작·private particle/NI adapter bytes나 Source/native/material graph를 고치거나 private 회귀를 재실행한 것으로 기록하지 않는다. 새 Main saved/RHI·Root 검토는 supplement 뒤 실제 결과다.

Root fresh MainVisualQA는 PNG11+targeted6의 실제 표본 승인이다(SHA `1586f77a…e44cd2`). Swordsman10/Yetuga Armageddon1 Decal의 임시 fallback·원작 단위 미확인 Apes radius의 임시10cm 경계·미수리 VAT TextureCube→2D 경고는 남는다. Apes 파편/소멸과 투명 다각형 debris를 원작 의도나 전체 pixel parity로 단정하지 않는다.
