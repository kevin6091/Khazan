# 2026-10-12 — Player JustGuard 모션·이펙트

## 준비본과 원작 근거

사용자가 직접 요청한 가드 시작 패링의 표현 에셋을 task-owned `Khazan_ParryWork_20261012/Khazan`에서 작성했다. 현재 Main의 가드 GA·Montage는 Windows 공유 잠금으로 교체 대기 중이다. 새 모션 2, particle 1, material master 3/MI 5 = 새 에셋 11개이며 기존 Guard Montage·GA 2개를 갱신하는 준비본이다. 공유 원본 material·texture·mesh·audio는 저장하지 않았다.

원본 source package와 SHA는 `Metadata/Parry_20261012/OriginalEvidence.json`, native 저장 전 링크·material은 `Probe01`, 실제 author 결과·포즈 대응은 `Author01/Authoring.json`에 있다. 재전수 추출 대신 기존 DAS 리소스와 저장 metadata를 표적 확인했다.

`AC_Kazan_DualAxeSword_Com_Guard_Suc_Just_L`은 `CA_P_Kazan_DualAxeSword_Def_JustGuard_R`, Just_R은 `Def_JustGuard_L`를 참조한다. 각 raw sequence의 0.5초/15 frame을 source `DilationAnimPositions` 31개/`DilationSequenceLength=0.36330757`에 맞춰 60Hz 22 frame(0.366666667초)으로 bake했다. 원시 포즈와 샘플 위치 오차 0cm, 회전 component 오차는 약 6e-7 이하다. 기존 .01 mesh/topology adapter를 보존했으며 Root를 100배 재스케일하지 않았다. Guard의 기존 CMC 정책에 따라 root motion off/forceRootLock으로 저장했다.

`PP_Damage_Spray.ItemList[7].NewJustGuard`는 `PP_AtkEx_JustGuard`를 참조한다. Flow stance `Parrying`의 `PP_AtkEx_Parry`와 구분했다. source package는 `BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Physics/PP_Attack/PP_AtkEx_JustGuard`, cached source SHA256은 `6c9f1364097eb714caa781a716c088ee44c1b154df71394a71635294ca7a106a`이다. 13 emitter/단일 LOD의 native graph·distribution·texture·tint·mesh를 복제하여 `/Game/_Art/Effects/Combat/GuardParry/PlayerParry/PP_Player_Parry_Success`에 연결했다.

원본 `PP_Damage_Spray.NewExtraData[7]`는 hit attach, absolute rotation, detach 0.06초와 impact offset 50을 갖는다. 구현은 기존 Weapon_R 소켓을 쓰고 0.06초 detach만 직접 재사용한다. 원본 impact point/offset writer와의 위치 일치는 미확인이다. world scale 1을 유지해 .01 skeletal mesh scale을 particle에 적용하지 않는다.

기존 `/Game/Audio/Original/Events/SC_Play_PLYR_DualAxeSword_JustGuard_Suc`를 재사용했다. NativeCuePlan의 source event ID는 4132611353이며 `BBQ/Content/_Kazan_/Sound/Player/Player_Common/Player_Weapon_Com_Swish/Play_PLYR_DualAxeSword_JustGuard_Suc`다. native random media 718782593/464072581과 기존 cue의 -3dB leaf adapter를 사용한다. 새 음원을 생성하거나 현재 Audio Notify를 수정하지 않았다. 별도의 원작 오디오/햅틱 내부 실행과 sample parity를 이 작업에서 검증했다고 표현하지 않는다.

## 알파 경계와 임시 복원 수치

원본 cooked shader graph가 제거되어 기존 복원 parent를 재사용했다. 패링 전용 로컬 parent/MI에만 수정했다. 원본 graph 완전 일치나 원작 pixel/frame parity가 아니다.

- source 마스크의 Alpha-only component 출력에서 RGB가 opacity에 섞이지 않도록 했다.
- local DefaultParticle의 기존 Masked OpacityMask를 연속 Translucent Opacity로 연결했다.
- 로컬 3개 parent에 `ParryEdgeFeatherUV=0.04` 및 `ParryEdgeSoftnessPixels=1.25`를 노출했다. inward UV smoothstep과 화면 UV 미분으로 texture/card 외곽을 연속 fade한다. **둘 다 어시스턴트 임시 표현 수치**다. 사각 경계가 남지 않을 정도의 최소 feather를 목적으로 선택했으며 원작 확인값이 아니다.
- local Fluid alpha에 emissive가 0인 검은 영역의 visibility gate를 추가했다. 기존 tint·texture·particle curve는 그대로다.
- 최초 dark RHI 검사에서는 복원 재질의 검은 원판이 보였다. 단일 굴절 MI만 바꾼 보정으로 해결되지 않아 로컬 5개 MI의 blend를 Additive로 통일했다. 이는 black mask/refraction pixel이 배경을 가리지 않도록 하는 **임시 복원 adapter**다. source의 MI별 blend와 구분하며 기존 공유 재질에는 적용하지 않는다.

AlphaPreview01–04의 스크립트 완료는 외관 합격을 의미하지 않는다. 일부 짧은 flash 캡처는 cold MI/GPU shader 준비 전이었다. 후속 preview는 각 MI permutation 통계와 unsaved particle 3초 RHI warmup 후 검사하도록 했다. 이 3초·카메라·노출·30FPS·캡처 프레임은 QA 설정이며 gameplay 수치가 아니다. native GPU backend 활성 개수와 복제 후 개수 차이는 관측으로 남기고 원본 backend 동일성으로 확대하지 않는다.

## 저장 검증과 재개

SavedAudit02에서 22 frame/RateScale 1/source tag/기존 5개 Guard segment·notify, parry 설정(.146/.5/.06/Weapon_R/원작 cue), parent continuous opacity/.04 UV/1.25px 연결과 MI Additive override를 reload하여 확인했다. 파생 Montage link cache 차이는 Engineering 문서에 기록했다. 실제 PIE02에서는 좌/우 response section 평가와 정확한 성공 횟수의 particle spawn을 확인하고 실제 게임 viewport를 캡처했다. 최종 alpha warmup preview와 후속 결과는 하단에 추가한다.

Main 반영에는 기존 두 Guard 에셋의 잠금 해제가 필요하다. 준비본을 다시 추출/일괄 재임포트하지 않는다. `deliver_player_parry_20261012.py preflight`로 대상 SHA와 잠금을 확인한 뒤 Source·13개 패키지를 함께 반영하고 fresh Main saved audit/RHI를 검사한다. private DLL이나 과거 Main module manifest를 복원하지 않는다. source shader/원작 impact writer/pixel 일치/Shipping 성능은 미확인 범위다.


## 2026-10-12 — Player Parry 준비본과 alpha 검사 정정

원작 Just_L/R composite의 반대 이름 raw sequence 참조, DilationAnimPositions 31개를 사용한 22/60초 bake, PP_Damage_Spray.NewJustGuard→PP_AtkEx_JustGuard의 13 emitter, 기존 원작 성공 cue를 연결했다. 새 motion2/particle1/master3/MI5=11개와 기존 Guard GA/Montage2개가 준비본이다. 정확한 package/SHA·수치·현재 검증 범위는 [PLAYER_PARRY_SOURCE_20261012.md](PLAYER_PARRY_SOURCE_20261012.md)에 기록했다. 공유 원본·Audio Notify·다른 작업은 저장하지 않았다.

최초 어두운 effect preview의 검은 원판은 shader 결함이라는 가설과 달리 검사 전용 빈 GameModeBase 맵에 생성된 **DefaultPawn_0의 구형 메시**였다. AlphaPreview06의 hidden_fixture_pawns에 origin(0,0,0)을 기록했고 이 Pawn만 숨긴 실제 RHI 캡처에서 원판이 사라졌다. AlphaPreview01–05 및 Isolate03은 그 fixture가 가려 외관 합격 근거로 사용하지 않는다. 보호된 LOD property를 직접 변경하려던 Isolate01/02는 API 실패로 끝났으며 task-owned process만 정리했다.

불필요한 local5 MI의 Additive 통일과 black-emissive gate는 AlphaFinalize02에서 철회했다. 모든 MI의 원본 base-property overrides를 복원했으며 particle의 13 emitter를 모두 유지했다. local3 parent의 continuous opacity와 0.04 UV / 최소1.25px edge feather만 유지한다. untextured DefaultParticle spark는 elliptic alpha와 ParrySparkSoftnessPower=2로 모서리·끝을 부드럽게 했다. 이 세 수치는 원작이 아닌 어시스턴트 임시 표현 값이다. root shader/source pixel parity·Shipping 성능은 미확인이다. 최종 preview/saved readback 결과는 PreparedVerification과 하단 후속 기록을 따른다.

**Main 에셋 반영은 잠금으로 대기한다.** 다른 에디터/채팅은 제어하지 않았다. 재추출/전체 author를 반복하지 않고 DeliveryPreflight/ResumeState의 대상만 SHA 확인 후 복사하고 fresh Main saved/RHI를 검증한다.



## 2026-10-12 — 패링 최종 준비본 검증 확정 / Main 2개 잠금 유지

최종 Build08/PIE03(15 case 및 6종 Definition)/SavedAudit03/AlphaPreview07는 Exit0·passed다. native 실제 loaded module SHA는 PreparedVerification.json에 있고 현재 준비 Source7은 Build08 input과 동일하다. Gameplay 제품 Source6은 앞서 성공한 GuardRegression01/CollisionRegression01과 같은 코드다. source MI base-property overrides가 복원된 saved reload, DefaultParticle ellipse power2와 .04 UV/1.25px edge 연결을 확인했다. 실제 game viewport의 .13/.24초 효과 및 dark RHI burst를 직접 열어 원판·불투명 card 경계가 없음을 확인했다. Source shader/pixel 완전 일치와 실제 스피커 출력/Shipping/network 검증을 완료한 것은 아니다.

**Main product Source/package 변경0, 적용 완료가 아니다.** 마지막 preflight는 대상 SHA 충돌0·GA_Player_Guard/AM_DAS_Player_Guard의 Windows error32 2개다. 기존 Main editor PID19752가 계속 실행 중이다. 사용자에게 작업 저장 후 종료 상태만 요청했고 에디터를 임의로 종료하거나 잠금 handle을 강제로 닫지 않았다. exact resume는 Metadata/Parry_20261012/ResumeState.json, review diff는 PreparedSource.patch다. 잠금 해제 이후 해당 Source7/asset13만 반영하고 fresh Main build/PIE/audit를 추가한다. 전체 저작/추출과 과거 DLL 복원은 반복하지 않는다.


## 2026-10-12T08:17:34+09:00 — Player Parry 에셋 Main 전달·fresh 검수 완료

새 motion2/particle1/local master3·MI5와 기존 Guard Montage·GA를 합친13 package를 Main에 전달했고 fresh MainSavedAudit02·MainPIE02에서 확인했다. source composite/dilation/22 frame/source cue와 기존 Guard segment·notify는 유지했다. 실제 Main의 성공 모션/weapon contact flash/꼬리 프레임을 열어 불투명 card/원판 경계가 없고 입자 끝이 연속 fade하는 것을 확인했다. source MI blend overrides는 복원됐으며13 emitter를 유지한다. local parent의 .04 UV/1.25px와 spark ellipse power2는 사용자 요구에 대한 임시 표현 수치다. 기존 공유 재질·texture·audio를 재저장하지 않았다.

Main DLL/source/asset SHA와 실제 RHI/저장 검사 결과는 Metadata/Parry_20261012/FinalVerification.json에 결속됐다. 이전 Main 잠금/준비본 pending은 이 범위에서 해소됐다. DefaultPawn 검은 원판 가설 정정과 이전 실패 proof는 보존한다. 초기 RHI의 메모리 budget/FPS 경고, 원작 stripped shader/pixel/impact writer parity, 실제 스피커 출력(-nosound) 및 Shipping 성능은 범위를 구분한다. 정확한 runtime은 Engineering PARRY_IMPLEMENTATION_20261012.md, 완료 후 재개 기준은 ResumeState.json이다. 전체 추출/저작/과거 DLL 전달을 반복하지 않는다.


## 2026-10-13 — 패링 사진 광막·굴절 후속 적용 / 원작 외관 일치 미확정

현재 Main의 Guard GA는 `PlayerParry/Reference/PP_Player_Parry_Reference`를 재생한다. 전용 폴더17 asset(PS1, camera BP1, parent6, MI9)과 기존 GA1의 현재 SHA는 `Metadata/ParryPhoto_20261013/CurrentVerification.json`에 기록했다. 기존 원본/공유 공격 VFX·혈액·Player received-hit 제거 설정은 동일 SHA로 보존됐다. 새 runtime class/component/tag는 없으며 정확한 코드 책임/카메라 검증은 Engineering의 PARRY_IMPLEMENTATION 최신 절을 따른다.

원본 PP_AtkEx_Parry12 emitter를 기반으로 로컬 재질만 복원했다. 이 원본은 NewParrying/Flow 계열이며 기존 NewJustGuard→PP_AtkEx_JustGuard와 동일 라우팅이 아니다. 첨부한 패링 사진은 Parry_PinkPurpleHalo.png다. cooked shader가 제거되어 광막/색/굴절/알파는 사진 기반 어시스턴트 임시 복원이며 원작 shader/pixel 일치로 표현하지 않는다. 원형 shader는 UV 반지름 바깥을 연속 fade해 카드 모서리를 0으로 만들고, magenta/violet 불규칙 arc를 구성한다. 검은 영역이 배경을 가리지 않게 colour layer는 Additive, 별도 굴절 parent는 Opacity0/PixelNormalOffset를 사용한다. 원본 texture의 실제 sRGB에 맞춰 Color sampler로 수정했다. Shader02는 parent6/MI9 모두 실제 D3D12 shader 오류0·유효 permutation을 확인했고 저장0이다.

Native10에서 원형 입자 Y/Z=0 및 굴절 입자의 실제 Color.A=0을 관측했다. source refrac에는 활성 StartColor module이 없고 ColorScaleOverLife module은 disabled다. 이를 원작 StartAlpha field가 직접0이라는 의미로 확대하지 않는다. 원형 slot13은 명시적인 CPU sprite로 대체하고 원작 life .2s/color(.421875,.323095,.193952)/alpha .7 및 기존 완전한 growth module22를 재사용했다. 원본 subobjects를 삭제하지 않았다. CPU square extent(125,125,125)cm와 finite alpha fade는 임시 adapter다. 원본 StartSize(250,0,0)와 구분한다. 원본 카메라 방향200cm offset은 두 원형 레이어에서 제외했다. 굴절은 원본 lifespan을 유지하고 `1-ParticleRelativeTime` 임시 envelope로 fade한다. IOR offset .06, halo intensity4, palette(3.2,.1,1.2)/(1.1,.05,3.5), ring UV radius .72/width .15·edge .83, noise breakup/arc 수치는 source shader 근거 미확인인 로컬 표현 튜닝이다. 정확한 나머지 HLSL 값은 finish_parry_photo_halo_20261013.py와 저장 재질 graph에 모였다.

Native13/14는 실제 새 template/입자 생성과17상황 판정·카메라를 통과했다. 실제 DevMap 캡처에는 붉은 분홍 접촉 광·잔광·약한 heat warp가 있고 불투명 사각 경계/검은 가림은 보이지 않는다. **첨부 사진 같은 넓은 보라색 광막이 실제 밝은 DevMap 화면에서 충분히 읽힌다고 합격 판정하지 않았다.** Isolate02의 dark All_4/Circles_2/4에는 원형 magenta/violet arc와 red centre가 명확하며 모서리 가림이 없다. Isolate02는 실행 이후 emitter-name 필터가 갱신돼 refraction-only도 CPU halo를 포함했으므로 굴절 단독 비교 proof로 쓰지 않는다. Native10의 concurrent RHI 과부하 timeout, Native07의 sampler error, CPUHalo01의 concurrent module manifest race, CPUHalo02의 helper property schema 실패, Extent01의 error32 저장 실패는 보존했다. Extent01의250cm 복원은 적용되지 않았으며 현재 저장값은125cm다.

아직 완료로 확정하지 않은 범위: 실제 HeinMach combat camera에서 사진과 광막 footprint/색/가림 비교, 원작 GPU/shader/impact writer 일치, Shipping/network/스피커/성능. 현재 구현과 검증 상태를 완료로 과장하지 않는다. 다음 표적 작업은 Art continuity의 절차를 따른다.

## 2026-10-13 패링 화면 가시성 재검증 — Main 적용, 원작 광막 외관 미완료
이전의 이펙트 생성·빌드 성공은 HeinMach 화면에서 디스토션과 카메라 반응이 뚜렷하게 보인다는 증거가 아니었다. Main Guard GA에는 기존 PP_Player_Parry_Reference와 BP_Parry_SourceCameraShake 결합을 유지하고, 새 M_Parry_ScreenRadialBlur를 연결했다. 원작 Guard_Suc_Just_L의 xxPP_RadialBlur Duration .16745299초, BlendIn .02초, BlendOut .3초, EndScalar .2를 시간/입력 근거로 썼다. UV 배율 .12는 원본 shader가 없어 선정한 임시 가시성 튜닝값이다. 화면 재질은 후처리 SceneTexture 기반이며 카드 사각 경계가 없다. 기존 파티클 굴절은 DistortionGrid04의 켜짐/꺼짐 배경 비교에서 실제 픽셀 이동을 확인했다. PS halo 크기를 125→250cm로 키우는 시도는 실전 캡처에서 더 약해 보여 정확한 이전 package로 되돌렸다.

실제 Main HeinMach RHI 캡처 Metadata/ParryPhoto_20261013/HeinCameraRHI03/01_ActualParryImpact.png 및 02_ActualParryMotion.png에는 분홍 접촉광과 화면 방사형 흐림이 보인다. 그러나 참조 사진 Metadata/CombatVFXReferenceReview_20261013/References/Parry_PinkPurpleHalo.png의 넓은 붉은·보라 고리/광막보다 현행 halo는 현저히 약하다. 원작 NewJustGuard 계열의 CPP_PC_JustGuard_C preset/cooked shader가 추출되지 않았고 현행 PP의 주된 출처는 NewParrying/Flow 계열이므로 픽셀 일치나 원작 완료를 주장하지 않는다. 정확한 Main asset SHA와 촬영/검증 범위는 Metadata/ParryPhoto_20261013/VisibilityFollowupVerification.json에 기록했다.

## 2026-10-14 — NewJustGuard 원본 광막 재구성·메인 연결

원본 FModel provider 설정과 설치된 pak을 사용하는 표적 추출기로 BBQ/Content/Art/ArtRendering/AR_PostProcess/CPP/CPP_PC_JustGuard를 추출했다. Metadata/ParryVFXRebuild_20261013/OriginalCPP/.../CPP_PC_JustGuard.json의 Default__CPP_PC_JustGuard_C.Properties.Settings에는 SceneFringeIntensity=1.5 및 ChromaticAberrationStartOffset=0.25와 두 override=true가 직접 기록되어 있다. 성공 모션 AC_Kazan_DualAxeSword_Com_Guard_Suc_Just_L의 xxPostprocessVol은 이 프리셋을 참조하고 BlendInTime=.05초, BlendOutTime=.25초다. 이는 기존 NewParrying/Flow PS와 별개인 PP_Damage_Spray.NewJustGuard→PP_AtkEx_JustGuard 경로다.

기존 Main Guard GA의 NewParrying 계열 PP_Player_Parry_Reference 대신 원본 PP_AtkEx_JustGuard에서 복제한 PlayerParry/PP_Player_JustGuard_Halo를 연결했다. 원본 13 emitter와 원래의 수명·크기·색 곡선·카메라 오프셋을 보존하고 flare_circle2, refrac, light만 활성화했다. 이동 스파크 spark_par_collision/spark_par_sphere/emitter1은 사용자의 제거 요청으로 껐다. 원본의 flare_line_center_glow와 flare_line_glow도 복원 셰이더에서 큰 원판·직선 광으로 보여 껐다. 중앙 glow를 켠 임시 검사 JustGuardCenterRHI01은 채택하지 않았고 원래 패키지 hash로 되돌렸다.

원본 FMI_fluid_A_15의 FT_Flare_004_LSY 발광 텍스처, T_GradientGlow 중심 마스크, Emi_pow=.8과 원본 ParticleColor를 사용하는 패링 전용 M_Parry_JustGuardFlare를 만들었다. cooked 원본 셰이더 그래프가 없어 발광 합성은 복원 adapter이며 원본 shader/pixel 일치가 아니다. 0.04 UV edge feather는 기존 패링 임시 경계 보정의 재사용이고 ParryVisibilityGain=16은 HeinMach 눈 배경에서 원본 텍스처가 묻히는 것을 보정한 어시스턴트 임시 선형 발광 배율이다. 색상·입자 분포·수명 자체는 임의로 바꾸지 않았다.

최종 독립 D3D12 렌더 JustGuardFlareRHI05는 보라·붉은 고리와 연속 alpha를 보였고 카드 사각 경계는 관측되지 않았다. 저장된 Main Guard를 새 프로세스에서 읽은 JustGuardMainRHI01/02_ActualParryMotion.png에는 스파크 없이 같은 고리와 화면 왜곡이 보인다. 첨부 원작 사진 Parry_PinkPurpleHalo.png에 비해 충돌 중심의 밝은 백색/적색 발광과 프레임별 완전 일치는 아직 부족하다. 원본 라인 광을 그대로 켜면 오히려 부자연스러운 원판이 생겨 제외했다. 패키지·소스·렌더 SHA와 미확인 범위는 Metadata/ParryVFXRebuild_20261013/FinalVerification.json에 있다.


## 2026-10-14 — 공중 내려찍기 굴절의 패링 화면 적용

패링 성공의 기존 붉은·보라 JustGuard halo 위에 로컬 NS_Player_Plunge_ParringDistort를 다시 재생한다. 기존 내려찍기 재질/renderer를 재저작하지 않고 카메라 방향 normal을 User.KZFloorNormal로 지정해 카드가 카메라를 바라보게 했다. scale .4, 충돌점에서 카메라 쪽 80 cm, .25 s 꼬리는 원작 메타데이터가 아닌 어시스턴트 TEMP 화면 배치다. 기존 일시적 radial blur와 SceneFringe도 함께 재생한다. 컴포넌트가 정상 방어까지 남던 오류는 즉시 정지·파괴로 수정했다.

Metadata/GiantCamera_20261014/ParryHeinRHI02의 실제 HeinMach 01_ActualParryImpact.png, 02_ActualParryMotion.png, 03_ActualParryEffectTail.png를 시각 확인했다. 붉은·보라 광막과 화면 중심 굴절이 보이고 사진 3장에서는 카드 사각 경계나 불투명 검은 판을 관측하지 않았다. Main RHI의 17개 상황에서는 성공 때만 활성/꼬리 후 종료를 확인했다. 캡처 환경은 낮은 FPS의 offscreen RHI이므로 원작 사진과 픽셀 동일성·정상 프레임레이트의 체감 세기까지 확정하지 않는다. 원본 cooked 셰이더가 없는 한계와 기존 광막 복원 상태는 이 문서의 이전 절을 유지한다.


## 2026-10-15 — 사용자 지정 KZ_Parring_Distort 및 Brutal 접촉 burst Main 완료

최신 사용자 지정 효과는 `/Game/VFX/03_SlashHit/KZ_Parring_Distort`다. 원본 camera-facing Niagara renderer/material을 유지하고 두 캐릭터 사이 흉부 높이에 배치했다. 이전 JustGuard halo/바닥 전용 Niagara/화면 PP 재생 연결은 현재 Guard에서 제거했다. 해당 원본 에셋 자체를 삭제하거나 공유 shader를 이 작업에서 바꾸지 않았다. native scale1은 요청 에셋 원래 크기를 사용한 것이며 방출 종료.5s/최대 수명2.5s는 TEMP 표시 수명이다. runtime source/cleanup은 Engineering PARRY_IMPLEMENTATION 최신 절을 따른다.

현재 BrutalFront의 `PP_AtkEx_Grapple_01`, `PP_Dmg_Blood_Trail_Sub`, `PP_AtkEx_Grapple_02` 접촉 burst 3개를 parameter/scale/원본 window와 함께 재사용한다. source package/field는 Author02/Author.json과 AuditFinal/Audit.json에 있다. 첫 Author01 full9 연결의 손/무기 잔상 레이어에서는 회색 큰 면이 나타나 layer isolation으로 확인했고, 실제 접촉 burst만 남긴 Author02가 최종이다. 이 선택은 source 전체 Brutal 재현 완료를 뜻하지 않으며 실제 Brutal montage/공유 PS는 보존한다. 이전9개 임시 연결 기록은 보존하고 현재 저장 연결3개로 대체한다.

FinalRHI01의 01_ActualParryImpact/02_ActualParryMotion/03_ActualParryEffectTail에서 camera-facing 왜곡 및 같은 접촉 입자를 실제 플레이어 패링 성공 시 확인했다. full9 손 잔상의 회색 slab는 최종 재생에 없다. requested Niagara-only/mesh-only 진단은 원인 분리 자료이고 기능검증 통과로 집계하지 않는다. 실제 기능은 Main D3D12 Parry17 Success이며, 저장 Guard BP 현재 SHA가 Author02와 동일한 새 프로세스 readback을 통과했다. 원작 shader pixel identity를 새로 확보한 결과로 표현하지 않는다. 최종 근거: `Metadata/CombatFeel_20261015/FinalVerification.json`. 본 작업의 unique package 저장은 Guard+두 monster BP3개이며 새로운 Art particle/shader asset은 없다.

