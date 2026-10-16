# 플레이어 회복 VFX 원본·표현 정본

## 2026-10-13 — Source 원본과 native 표시 경계

사용자 직접 요청으로 플레이어의 현재 회복 모션에 효과를 연결한다. 최신 실제 Main 완료 여부는 `Metadata/HealVFX_20261013/FinalVerification.json`, 중단 상태는 `ResumeState.json`을 먼저 확인한다. 이전 전체 추출/author를 재실행하지 않는다. Engineering 실행 수명은 `Docs/Engineering/PLAYER_HEAL_VFX_RUNTIME_20261013.md`다.

기존 FModel 설정을 읽는 `Scripts/Enemies/EnemyExtractor`의 표적 index/metadata/export를 사용했다. index의 회복 관련220개 경로에서 실제 `SB_Kazan_Recovery_C.UpperAnim`이 지목한 `AC_Kazan_Recovery`를 확인했다. `AC_Kazan_Recovery1`도 같은 다섯 효과를 사용하지만 현재 연결 근거는 SB의 기본 UpperAnim이다. 정확한 source JSON/field/raw/SHA는 `Metadata/HealVFX_20261013/Original`, `SourceEvents.json`, `Payload/ExportReport.json`과 Author03의 curve_sources다.

### 원작 직접 확인값

package prefix는 `BBQ/Content/_Kazan_/Design/Kazan/Skill/Common/Recovery/AC_Kazan_Recovery`다. 아래는 그 `Properties.Notifies`와 해당 `xxAnimNotifyState_Particle.Properties.ParticleInfo`다. 시간은 원본 애니메이션 축의 초이며 source-game 실제 world timing과 동일하다고 단정하지 않는다.

| Notify index | 원본 Niagara | 시작 / Duration (s) | 원본 부착 |
| --- | --- | --- | --- |
| 2 | FP_DrainCore | 0.098107 / 0.750875 | Bip001-L-Hand; RelativeLocation=(9.125063,-6.3773155,-1.9570816) cm |
| 5 | FP_DrainCore_Explo1 | 0.789754 / 0.676912 | FX-L-Finger32 |
| 6 | FP_KazanGhostHand_Init | 0.840501 / 0.6261657 | Root; skeletal DI filtered UpperArm/Forearm/Hand |
| 7 | FP_KazanGhostHand_A_Finger_init | 0.842957 / 0.6237097 | Root; skeletal DI filtered Finger01/Finger1–4/Hand 및 FX finger sockets |
| 10 | FP_DrainCore_Explo | 0.860931 / 0.6057357 | Bip001-L-Hand; 위와 같은 RelativeLocation |

시스템 package prefix는 `BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/PC/Recovery/`다. 양쪽 GhostHand의 `ParticleFloatParams.User.EmitterDuration=0.626166s`도 직접 값이다. 원작 core는 Notify End/Anim End destroy, Expload/ghost는 각 export의 deactivate/destroy policy를 보존된 JSON에서 조회한다. native 표시의 유한 수명/취소 정책과 구분한다.

source mesh3(`FS_Sphere`, `FS_SmallRing_01`, `FS_BloodRing_01`) 및 `FT_Trail`을 표적 ActorX/PNG export했다. 결과4/4 성공이며 원본 payload SHA를 native metadata tag에 기록했다. source `FMI_WPO_Mesh_A_02.TextureParameterValues[MainTex/G]`는 `FT_Trail`을 지목하므로 native shader는 불투명 A 대신 **G density**를 사용한다. texture SRGB=false는 linear-mask 해석이다.

`FP_KazanGhostHand_Init` export174의 `NiagaraMeshRendererProperties.Properties.Meshes[0]`에는 Scale=(4,1,1), PivotOffset=(0,3,0), PivotOffsetSpace=Mesh가 직접 기록돼 있다. native 작은 ring emitter의 StartSize와 EmitterOrigin으로 대응했다. source finger blood ring renderer의 Scale=(5,5,5)도 유지했다. source mesh는 재조형하지 않았다.

직접 RGBA `ShaderLUT`는 FP_DrainCore export1, FP_DrainCore_Explo1 export0/4, GhostHand_Init export0, GhostHand_A_Finger_init export0에서 읽었다. curve source JSON SHA/export-index/53·79·102·53·91 sample 및 RGBA는 Author03의 curve_sources와 Original 파일에 보존한다. 예: core RGB=(2,0,0), alpha1→0; burst white RGB2와 alpha max≈0.5; arm RGB0.05; finger RGB1.5/alpha max3. normalized age의 균등 LUT grid를 native linear curve로 대응한 것은 **계산/해석 adapter**이며 source VM의 원래 연결과 pre-cook editor keys를 복원한 것으로 표현하지 않는다.

### 현재 clock 계산과 표시 adapter

현재 Heal sequence1.4666667s/rate1와 Stow offset1s를 유지한다. native start=`StowStart+source LinkValue/rate`, end=`StowStart+(LinkValue+Duration)/rate`다. start1.098107/1.789754/1.840501/1.842957/1.860931s다. source DilationCurve에는 DilationSequenceLength1.3497161s가 존재하지만 current Heal pose/clock을 재저작하지 않는다. 실제 원작 dilation 적용 조건 및 exact world/pixel parity는 미확인이다. source Notify end 소수 precision과 engine montage endpoint의 -0.0001s trigger-offset도 구분한다.

cooked Niagara의 편집 그래프, GPU/VM 실행 구조 및 material/WPO graph가 없어 그대로 native 재생할 수 없다. five event roles를 native Cascade5로 재구성했다. Root-attached source skeletal DI를 실제 현재 골격에 붙는 UpperArm/Forearm/Hand3 및 fingers5의 effect children으로 대응한다. core/burst/flash와 합쳐11 receipt다. 원작 skin surface sampling/전체 renderer 수/point-light/custom toon response를 그대로 복원한 것은 아니다. light flash는 유한 soft-glow emitter로 표시한다. 공격·맵·몸체 재질에는 연결하지 않는다.

### 어시스턴트 TEMP 값과 조정 위치

원작 VM/stripped shader에서 아래 값을 확인하지 못했다. 사용자 요구의 화려한 붉은 에너지와 매끄러운 alpha를 위한 표시 값이며 gameplay 수치가 아니다. `/Game/HealVFX/Materials` 및 `/Game/HealVFX/Particles`에 모여 있고 명명한 material parameters와 Cascade modules에서 조정한다.

- Shader: EdgeFeatherUV0.04, 최소1.25 pixel 미분 feather, DepthFadeCM8, EmissiveGain8, RecoveryTint=(1,0.03,0.008), trail U panning0.3cycle/s, sphere Fresnel power3. opacity는 density×saturate(ParticleAlpha)×continuous edge×DepthFade다. HDR RGB는 clamp하지 않는다.
- ExposureCompensation1: EyeAdaptationInverse의 LightValueInput/AlphaInput을 사용해 이 효과 emissive만 scene auto-exposure에 보정한다. 밝은 DevMap의 미약한 초기 결과를 보완하며 레벨 조명/전체 노출은 바꾸지 않는다. Source shader 일치가 아닌 표시 TEMP다.
- Core: sprite1.2cm, burst12/rate40 per s, spread9cm, attractor strength65/range40cm, sphere scale0.12. source window duration을 사용하되 모트 lifetime0.75s는 TEMP다.
- Burst: 42 spark, size1.8cm/lifetime0.6s/spread3cm/velocity32cm/s, glow22cm/lifetime0.5s. Arm mote10, size0.8cm/lifetime0.55s/spread5cm/velocity5cm/s. flash16cm/lifetime0.4s. counts/velocities/point force는 source emitter VM의 직접값이 아니다.

정상 모션에서 알파가 끊기거나 사각형이 보이면 먼저 mask 채널/usage flags/compile errors를 확인한다. 뼈 부착·actual primitive size/RGBA/clock/viewport flags는 Runtime.ndjson로 확인하며, 광량이 약하면 ExposureCompensation/EmissiveGain을 먼저 점검한다. 원작 직접 LUT/모션/HP를 편의상 다시 튜닝하지 않는다.

### 실제 검수와 역사적 실패

Author01의 CustomInput 생성 API, Author02의 ParticleModule outer=ParticleSystem 요구, Saved01 Python get_mesh 미노출, Saved02 private plugin link 중 시작은 도구 실패로 보존했다. native vector Uniform fixed-array setter의 warning은 Finalize02에서16 배열의 공개 typed setter로 교정했다. 최초 RHI의 Material ParticleSprites/MeshParticles usage 누락은 신규3 재질에만 플래그를 저장해 해결했다.

NativeProbe01/02에서 입자 size/RGBA/scale1/finite location과 actual clock, viewport Particles=1/Translucency=1을 확인했다. initial low visibility를 source event 미실행으로 오판하지 않는다. VisibilityPolish02 뒤 PrivatePolished01의 actual game viewport1.3667s/1.9667s를 직접 열었다. 붉은 모트·손 섬광/mesh outline이 보이며 해당 프레임의 사각 card/불투명 테두리/black quad가 없었다. 실제 Heal functional regression은11 역할/부착/반복·종료·취소/HP·weapon/이동·UnPossess를 통과했다. Shader errors0와 pixel instructions179/189/207을 분리 기록했다. 두 프레임은 전체 모든 카메라/원작 화면 동일성/Shipping 성능 검증이 아니다.

Main 전달은 runtime1/기존 DEV1/asset13(신규12+기존 Heal Montage1)의15 파일만 SHA/CAS한다. private DLL/Config/다른 VFX/physics/몽타주를 전달하지 않는다. 최신 Main build/saved/runtime 결과는 완료 절과 FinalVerification을 따른다.


## 2026-10-13T09:39:54.076603+09:00 ? ???? ?? VFX Main ??

?? Recovery?5 effect role/core?burst???????light flash? ?? Heal/Stow ??? ????. source raw LinkValue+?? Stow offset/rate? ???? ?? HP/InputEnd/weapon/??/?? ??/FPS/root/audio? ????. runtime1/?? DEV1/asset13(??12+?? Heal Montage1)?15 ??? exact SHA/CAS? ????. ? runtime file/class/component/manager/tag0, private DLL/Config/Build ??0, ?? 133 ?? SHA ??0??. ? Source? Main?? canonical build??.

MainBuild01 exit0/22.04s, MainSaved01 save0??? notify/GUID/?? ?11bone/22pair, MainFinalPIE01 ?? Khazan.Heal.PIE/Khazan.Combat.PlayerAttackCollision.PIE Success?. ??11 child emit?parent bone?finite values/HP????????? ?????/???UnPossess cleanup? ???? actual loaded canonical DLL SHA? 39ab3b029cc36dd7c78213f55fc2e22446110268952cbd932571a6a96488a46d?. shader errors0/pixel instructions179?189?207, Main ?? Core1.3667s/hand burst1.9667s ??? energy/continuous edge? ????. missing ParticleSprites/MeshParticles usage ?? default fallback warning0??. ?? editor/???/??/??? owned process fixture, package/map ??0, ???/foreign editor ??0??.

Source mesh3/FT_Trail.G/ShaderLUT?source numeric? clock ??/TEMP? PLAYER_HEAL_VFX_SOURCE_20261013.md? ????. cooked Niagara/VM/material/WPO graph ???? ?? native Cascade? ??? ????? original skin sampling/light/full shader/pixel ????? camera/Shipping/network/??? ???? ???. ExposureCompensation1/EmissiveGain8/feather0.04???1.25px/DepthFade8cm ?? ????? TEMP?. Source Dilation1.3497161s? ?? raw Heal1.4666667s? ???? ??? retime?? ???. ?? ??/???? ???? ?? ?? ? Main ???? ????.

?? ??0. ?? evidence? Metadata/HealVFX_20261013/FinalVerification.json, ResumeState.json, Changes.patch?. ??? ?? ???current /Game/HealVFX/Materials?Particles ? Heal marker? ?? ????. ?? full author/?? ??/?? ????/?? VFX?physics/root/FPS ?? private DLL ??? ???? ???. ?? ??/???/?? ??? ? ??? ????.
