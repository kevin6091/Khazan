
# HeinMach 후처리 제거 및 공격 VFX 경계 교정

## 2026-10-11 — 실제 Main 적용과 검증 완료

이번 정본은 최신 Main의 후처리 제거 → 차지/OverFury 셰이더 교정 → 혈액 분사 보완 → 몬스터 루트모션/카메라 확인 순서로 수행한 작업이다. 앞선 continuity의 진행 중/미확인 항목은 아래 최종 증거로 보충한다. 옛 private AttackVFXWork Source나 delivery를 Main 위에 다시 덮어쓰지 않는다.

최종 파일 해시·사용 모듈·검증 범위: [Completion.json](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion.json). 작업 전후 Source/Config의 작은 변경은 [OwnSourceChanges.patch](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/OwnSourceChanges.patch)에 있다. 제품 C++ 수정은 기존 KZMonster.cpp 하나이며 새 runtime 파일/class/component/manager는 없다.

### HeinMach에서 제거한 후처리

실제 맵은 `/Game/Maps/L_HeinMach_Environment`다. 옛 `_Art/.../Maps` 경로는 redirector다. HM_PreviewPostProcess와 HM_Environment_PP_HeinMach_Light_209..215의 8개 볼륨 및 연결된 툰/외곽선/지역 색보정 blendable을 제거했다. 볼륨/PP Component는 새 프로세스와 실제 PIE에서 모두 0이며 PlayerCamera의 authored override도 없다. 나머지 9,861개 actor/component의 설정·transform은 작업 전과 동일하다. 그중 Sky/Fog/조명 198개도 유지됐다.

Config의 Bloom/MotionBlur/LensFlare는 껐고 LocalExposure의 Highlight/ShadowContrastScale은 엔진 중립값 1로 설정했다. 이들은 원작 메타데이터 수치가 아닌 사용자 요청을 위한 renderer 설정이며 프로젝트 기본값에 적용된다. AutoExposure=False 시험은 실제 HeinMach 지형의 백색 clipping 때문에 철회했고 최종 기본 장면 metering은 켜져 있다. 기본 HDR 화면 변환·AA·물리 안개까지 제거했다고 표현하지 않는다.

발광 VFX의 실제 Particle/Niagara 참조와 기존 Effects root 집합 151개 중 128개 Surface emissive 부모에 엔진 EyeAdaptationInverse를 연결했다. 원래 발광 계산을 보존한 뒤 엔진의 역노출만 적용한다. 나머지 23개는 기존 보정/발광 없음/non-scene/data writer 등으로 제외했다. 128개 모두 resource compile/save에 성공했고 새 프로세스에서 그래프와 최종 해시를 재확인했다. 현재 맵의 색보정 차이를 제거하고 장면 노출 변화에 따른 발광 색·밝기 변화를 보정한 것이다. 임의의 미래 PP 색보정까지 무조건 우회하는 별도 compositor는 구현하지 않았다. 물리 Fog/굴절/가림은 계속 작동한다.

증거: `PPRemove01/Removed.json`, `PPColdReadback01`, `VFXExposure01/Applied.json`, `FinalAssetReadback02/Readback.json`, `HeinMachRHI03/HeinMach.json`. 실제 화면: [Entry](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/HeinMachRHI03/Entry.png), [ReferenceStart](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/HeinMachRHI03/ReferenceStart.png), [OpenSky](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/HeinMachRHI03/OpenSky.png).

### ChargeAttack의 직사각형 원인과 교정

차지 실제 1.051초의 7개 emitter 격리에서 slot0 FMI_Smoke_03 → FM_Smoke의 회색 평면을 확인했다. 원본 Main_tex/Sub_tex/Dist_tex와 opacity 소비가 연결되지 않은 복원 그래프가 원인이었다. 원본 smoke R 채널·noise·UV/scalar·ParticleColor alpha·DepthFade를 연결했다. texture A가 불투명 상수인 경우 전체 사각형을 alpha mask로 사용하지 않는다.

추가로 slot1 FM_Simple_UVSprite_FluidSmoke_6의 작은 자홍색 사각형은 source Set_Mat_Color/Use_2Color/Use_ColorMap=false를 기존 부모가 무시하면서 사용하지 않을 HighColor를 소비한 문제였다. Base_ShockWave_Sprite_001에 해당 child만 활성화하는 KZRecoverFluidSmoke6 static branch를 추가해 원본 BaseTex/MaskTex/UVTexture/SubDistTex·power/strength/DepthFade와 ParticleColor를 사용한다. 다른 child는 기존 false branch를 유지한다. 굴절 shock parent도 미연결 Refraction 소비와 raw UV 지원 범위를 교정했다. 이식용 연속 UV support는 기술적 경계 처리이며 원작 그래프를 직접 확인한 것으로 표현하지 않는다.

발생 시점/크기/수명/색 곡선이나 montage notify를 줄여 문제를 숨기지 않았다. 0.773초의 아직 효과가 나오지 않은 최초 격리는 해결 증거에서 제외한다. 최종 `ChargeFinalIsolated03`의 실제 1.1235459초 All/slot1 화면에서 큰 회색 평면과 자홍색 사각형 제거를 확인했다. [최종 전체 화면](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/ChargeFinalIsolated03/All.png), [slot1](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/ChargeFinalIsolated03/Slot1.png).

원본 메타데이터 기준 경로는 `Saved/Extracted/CombatEffects_20261006/Source/BBQ/Content/_Kazan_/Art/VFX/VFX_Material/Smoke/FMI/FMI_Smoke_03.json`, `.../ShockWave/MI/FMI_RefractionShock_2.json`, `.../BBQ_Material/Simple/FM_Simple_UVSprite_FluidSmoke_6.json`이다. 상세 연결/원시 scalar/원본 override 구분은 `fix_charge_smoke.py`, `fix_charge_fluid_preset.py`와 각 Applied.json에 보존했다.

### OverFury 마지막 큐브의 원인과 교정

`FP_Kazan_DualaxeSword_Fatalblood_slash_01` slot2의 VAT_Blood_04_mesh는 복원용 일반 큐브가 아니라 원본 dynamic-remeshing VAT 데이터의 carrier mesh다. 부모 M_BloodVAT에 VAT decode/WPO 소비가 없어서 인코딩된 carrier가 그대로 렌더링된 것이 원인이다. mesh를 삭제하거나 emitter를 끄지 않고 원본 VAT4 position/rotation/color/lookup을 decoder에 연결했다.

원본 `.../VFX_Mesh/BBQ_Mesh/Physics/VAT_BLOODSET/VAT/Blood_VAT4/MI_BloodVAT4_1.json`의 Manual/AutoPlayback=false, LegacyParams/Instancing=true, PositionsRequireTwoTextures=false와 기존 bounds/FPS/offset을 재사용했다. 원본 DynamicParameter Param1의 1..90 수동 frame, source lifetime 1.2..1.5초를 유지한다. 데이터 texture는 point/no-mip/no-stream으로 읽고 carrier mesh의 full-precision UV를 켰다. 새 MF 하나는 `/Game/_Art/Effects/Shared/Functions/VAT/Houdini_VAT_DynamicRemeshing`이며 별도 runtime plugin은 설치하지 않았다.

decoder는 [SideFX 공식 VAT3 자료](https://www.sidefx.com/docs/houdini/nodes/out/labs--vertex_animation_textures-3.1.html)와 [SideFXLabs Unreal 자료](https://github.com/sideeffects/SideFXLabs/blob/Development/unreal/5.1/VAT%20Import%20Settings%20Guide.txt)의 native function을 사용했다. 다운로드 blob/hash는 Saved/ImportReports/HeinMachCleanPresentation_20261011/SideFX_Labs 증거에, 배포 license는 [ThirdParty/SideFX_Labs_LICENSE.md](ThirdParty/SideFX_Labs_LICENSE.md)에 보존했다. 원작 cooked 그래프가 stripped되어 source 데이터의 native 소비를 재구성한 것이며 원작 shader topology/pixel 복제 완료는 아니다.

`ChargeVATRepair07`은 commandlet에서 StaticMeshEditorSubsystem이 없어 마지막 mesh 설정에서 실패한 부분 저장 보고서다. 앞선 MF/MI/texture 저장은 완료했고 mesh precision은 `VATPrecision01`에서 별도로 완료했다. 실패 report의 success=false를 exit0로 통과시킨 것이 아니다. 이후 VFXRepairReadback01/FinalVFXPIE03의 실제 마지막 구간에서 carrier cube 대신 흐르는 혈액 형태를 확인했다. [OverFury 연속 화면](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/FinalVFXPIE03/OverFuryReview.jpg).

### 혈액 분사와 데칼: 수치 출처

원본 기준 파일은 `.../VFX_Particle/Physics/PP_Damage/PP_Dmg_Blood_Trail.json`, `PP_Dmg_Blood_Trail_Sub.json`이다. 아래 증가는 사용자가 원하는 더 많은 Blood Effect/Particle을 위해 어시스턴트가 고른 **임시 표현 튜닝**이다. 원작 확정 밀도로 표현하지 않는다.

| 대상/field | 원작 직접 값 | 이번 값과 출처 | 영향·검증 |
|---|---|---|---|
| Trail SpawnPerUnit.UnitScalar | 80cm | 임시 density3 → 80/3=26.6667cm | 이전 density2/40cm보다 실제 분사 간격 1.5배 조밀. 저장값 fresh readback |
| Sub 실제 sprite burst Count | [5,10,5,2], 총22 | 임시 [15,30,15,6], 총66 | 이전 총44보다 1.5배. 원본 Time=[.1,.1,.2,.3]초/수명/속도는 유지 |
| Mesh decal emitter Spawn.Rate | 15개/초 | 임시 0개/초 | 이동 경로에 계속 찍히는 규칙적 자국 중단. death-event spawn_child/Count1와 원래 타격 decal notify는 유지 |
| FM_MeshDecal 경계 | source mesh local half-size2.5 | 임시 CornerFraction=.25 / EdgeFeather=.08 | 각진 투영 외곽 완화. 부모의 KZBloodProjection… parameter에 모아 조정 가능 |

packed decal texture의 RGB mask를 유지하며 A=255 상수를 마스크로 쓰지 않았다. source random yaw 0..1 turns도 유지했다. 추가 decal notify나 decal count 증가는 하지 않았다. 실제 sprite/혈액 VAT 분사에 양을 더했다. [혈액 실제 연속 화면](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/FinalVFXPIE03/BloodReview.jpg).

중요한 재사용 지식: DistributionFloatConstant.Constant=0만 바꾸면 native RawDistributionFloat의 Min/Max/Table에 기존15가 남을 수 있다. 이번 `BloodBakedRate01`에서 엔진 공개 StructBase.import_text로 동일 Rate struct의 파생 lookup까지 0으로 저장했다. `FinalAssetReadback02`의 새 프로세스는 Constant0뿐 아니라 export_text Values=(0.000000), 기존15 없음까지 assert했다. T3D의 0 default field 생략을 캐시15 잔존과 혼동하지 않는다. 01의 편집 값 검사만으로 완료 판정하지 않는다.

### 검증 범위와 후속 작업

MainBuild02가 성공했고 현재 Khazan 모듈은 `UnrealEditor-Khazan-2026101101.dll`이다. FinalVFXPIE03 실제 native 공격18+Brutal5가 Success/compile·fallback 오류0, Save0이며 실제12마리의 모든 PrimitiveComponent Camera Ignore와 player camera authored override0도 확인했다. 이 전체 회귀 이후의 마지막 FluidSmoke6 교정은 ChargeFinalIsolated03 실제 RHI로, 마지막 혈흔 baked rate 교정은 FinalAssetReadback02 cold readback으로 검증했다. 전체 회귀를 마지막 두 수정 뒤 재실행한 것으로 표기하지 않는다.

실제 몬스터 BP7개(legacy TEST 포함)의 hard/soft closure1380에서 사용 AnimSequence238과 ABP6을 조사했다. 238개가 이미 모두 root motion enabled였고 disabled0이었다. 재임포트/root-track/force-lock/rate/length/ABP mode 변경0이며 RootMotionFromMontagesOnly를 유지한다. 카메라 Source 변경과 정확한 역할은 Engineering 정본에 분리 기록했다.

작업 에디터는 task-owned hidden background process만 사용했으며 사용자 Rider/editor 제어0이다. Shader/pixel 원작 완전 일치, 전체401 구간의 모든 시각 효과, Shipping GPU cost/FPS는 이번 완료 범위가 아니다. 혈액 입자 증가에 따른 비용은 기존 source lifetime/culling을 보존했지만 Shipping 측정으로 확정하지 않았다.

필수 잔여 작업은 없다. 후속 조정 시 Completion과 현재 Main을 먼저 대조한다. fresh 재검증이 필요하면 `run_editor.py <새 고유 run 이름> capture_heinmach_clean.py --pie`를 사용한다. helper는 반드시 canonical map을 명시적으로 load_map한다. 이전 HeinMachRHI01은 DevMap 캡처이므로 재사용하지 않는다. VFX 확인은 고유 run 이름으로 capture_final_vfx.py --pie, 자산 읽기는 final_asset_readback.py로 수행한다. 저장/author/전체 retime/과거 전달을 반복하지 않는다.

<!-- HeinMachCleanPresentation_20261011_FinalVerified -->

## 2026-10-11 — 최종 혈액 분사/데칼 death-event 수량 분리와 최신 snapshot

이 절과 [Completion_FinalBloodEvents.json](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion_FinalBloodEvents.json)이 직전 Completion.json snapshot을 보충한다. 나머지138개 제품 에셋과 Source/Config 해시는 그대로이고 PP_Dmg_Blood_Trail_Sub 하나의 event 설정만 추가 교정했다. 기존 snapshot/검증/날짜 기록은 보존한다.

직전 “데칼 count 증가는 하지 않았다”는 직접 SpawnCount/추가 notify를 늘리지 않았다는 의미였다. 최종 연결 조사에서 sprite66개의 death-event가 mesh-decal을 간접적으로 늘릴 수 있음을 확인했다. `ParticleModuleEventGenerator_1.Events[0]`, Type=EPET_Death/CustomName=spawn_child는 혈액 sprite SpawnModule_0의 death를 MeshDecal SpawnModule_5/receiver1로 연결한다. 기존 Frequency0은 매 death를 전달한다.

사용자의 혈액 분사 증가/데칼 증가 제외 의도를 위해 Frequency를 **어시스턴트 임시 튜닝3**으로 조정했다. 원작 직접 확인값으로 표현하지 않는다. source sprite22 → 새66의 비율66/22=3을 선택 근거로 삼았다. 엔진 `ParticleModules_Event.cpp::HandleParticleKilled`는 DeathTrackingCount를 증가한 뒤 Frequency==0 또는 count%Frequency==0인 때만 전달하므로 정상적으로66개가 모두 죽으면22개의 death event가 전달된다. 이전 Main44/빈도0보다 시스템당 이론상 절반이며 실제 입자66개는 그대로다. Trail interval의 이전40cm→26.6667cm도 함께 반영하면 동일 거리/모든 정상 death 조건에서 이 경로의 이론상 이전 대비 비율은 (40/26.6667)×(22/44)=.75다. 이는 계산 결과이며 실제 runtime 이벤트 총량이나 Shipping 비용을 측정한 값은 아니다.

연속 mesh-decal Rate editable/baked0, receiver SpawnCount1, source timing/수명/속도/random yaw와 원래 hit decal notify는 유지한다. 새 프로세스 `FinalAssetReadback03`에서 Frequency3/혈액 burst[15,30,15,6]/Rate0 및128개의 emissive root/최종 static branch/hash를 확인했다. 마지막 event frequency 변경은 cold 저장값과 실제 엔진 분기식으로 검증했으며 실제 공격 회귀/연속 화면은 앞선 FinalVFXPIE03, 마지막 차지 셰이더는 ChargeFinalIsolated03의 별도 RHI 증거다. 최종 필수 잔여 작업은 없다. 후속 수량 변경 시 분사와 death-event 수량을 함께 계산한다.

<!-- HeinMachCleanPresentation_20261011_FinalBloodEventSeparation -->
