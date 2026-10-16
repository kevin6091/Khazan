# Yetuga / Apes VFX 정리 — 2026-10-13

사용자가 직접 요청한 범위는 두 종의 발걸음 눈보라/내리찍기 눈 파편/얼음 브레스·필드/투석 준비·비행·충돌 및 모든 사용 VFX의 부착·밀도·분산·알파 품질이다. 런타임 소유자/cleanup은 Engineering ARCH-98 및 후속 정본으로 분리한다. 현재는 private 구현·검증 준비이며 Main 완료가 아니다.

원본 지식은 MONSTER_VFX_PLAYBACK_20261008.md 최신 완료, APES_YETUGA_PATTERN_SOURCE_AUDIT_20261008.md 및 Metadata/EnemyBehaviorResearch_20261008/PublicYetuga·PublicApes를 재사용했다. 새 인터넷 검색으로 Yetuga 전투/브레스 이미지와 Granite Jocko 전투를 표적 조회했다. 직접 열람한 원작 sheet는 dc_13(브레스/얼음 열/파쇄), PublicApes Main_00_20_to_00_29_5(점프/양팔 내려찍기)다. 원본 출처는 https://gall.dcinside.com/mgallery/board/view/?id=berserkerkhazan&no=19069 / https://www.inven.co.kr/board/party/6187/21 / https://www.youtube.com/watch?v=fjZsbwldgTw . 영상 시각은 참조용이며 gameplay timer가 아니다. shader·pixel·빌드 버전 전체 일치로 주장하지 않는다.

기존 저장된 manifest로 표적 한정하여 현재 실제129node/137sequence/49ParticleSystem을 Probe02에 기록했다. 49 actual PS의 module/material/mesh 객체는 ParticleExports01과 ParticleObjectCatalog.json에 보존한다. 숫자는 현재 임포트 PS 값/원작 direct/참조 TEMP를 구분한다. 예를 들어 FP_Boss_Yetuga_Footstep_Normal_01 ParticleModuleVelocity.StartVelocity의 현재 Min.Z=150/Max.Z=200과 기존 .01 component 크기를 함께 곱하면1.5–2cm/s가 된다. 이는 현재 renderer 계산 진단이며 아직 원본 직접 일치 판정이 아니다. 새 world-particle-unit 소비 선택값은 기존 PS size/velocity를 재저작하지 않고 그 자체의 cm를 유지한다. bone/model offset, source notify timing/root/FPS/audio는 그대로 두며 소유자 단위의 실제 화면으로 확인한다.

Sprite alpha는 현재 ParticleAlpha_20261013의 저장 texture/channel triage를 재사용한다. 새 두 종 전용 particle/material 복사본만 만든다. 공용 부모/원본 texture/RGB/원래 emitter/module 분산·타이밍을 덮어쓰지 않는다. constant A255 mask에는 검증된 R density를 쓰고 inward feather .03UV/최소1.25pixel 및 depth fade12cm는 어시스턴트 TEMP 표현 설정으로 소유 material parameter에 모은다. 실제 카드 경계·발밑/몸 교차·클로즈업/중거리/동작 중 화면에서 확인해 조절한다. Actor 강제 균일 배치로 보기 좋게 만든 가짜 파편을 완성품으로 두지 않는다.

최신 Main→Khazan_GiantVFXWork_20261013 snapshot/Baseline.json으로 시작했다. actual source animation 경로가 /Game/_Art/Enemies/...도 소비되어 두 종 Animations212파일을 추가 소유했고 SHA를 AnimationOwnership.json에 기록했다. Main 원본을 가리키는 junction은 자체 Work 내부에 보존하며 저작 전 실물 private path를 검사한다. 별도 ParticleAlpha·몬스터 보조 물리 작업을 보존한다. 모든 저작 단계는 새 label/영수증으로 진행하며 완료한 예전 monster author/import/Root/FPS/alias를 재실행하지 않는다.

## 2026-10-13 — private 리소스·표현 재질 보완, Main 전달 전

원작 추가 참조는 dc_03(양팔 내리찍기), dc_12(투석), dc_14(연속 내려찍기)와 PublicApes/Main_00_10_to_00_19_5(이동·공격), 앞서 본 dc_13(브레스·필드), Apes/Main_00_20_to_00_29_5다. 저장한 영상/사진의 눈 분말+각진 실제 얼음 3D 파편+접촉면에서 솟는 필드를 기준으로 비교했다. 원작 사진에서 보이는 자연스러운 얼음 모서리와 잘못된 스프라이트 사각 경계를 구분했다.

새 추출은 ObjectOriginal/Requests.json의 FP_Boss_Yetuga_IceBreath_explosion_01 및 Smash_04 두 package metadata, MeshRequests.json의 BBQ_Mesh/FS_Ice_Spear_002 및 FS_Ice_Floor_003 ActorX payload 두 개뿐이다. FModel snapshot EnemyExtractor 결과·source SHA·payload SHA와 누락 mesh/material 보완은 FieldDeps01/FieldDependencies.json에 기록했다. FieldDeps01 commandlet은 temporary imported material-token lookup error1로 exit1이지만 script/saved 결과는 완료됐으며 이후 fresh saved audit는 active null binding0이다. 이 초기 실패를 소급 성공으로 표시하지 않는다.

부착 중 world location이 이중 합산된 원인은 Engineering debugger 기록에 분리했다. 수정 후 WorkAll02의 실제 154 field_00에서 원본 얼음 창 mesh가 floor에서 돌출하고 field_02에서는 파쇄 tail이 보이는 양성을 확인했다. collider geometry·damage·life/speed/원래 source timing은 바꾸지 않았다. Actual skill emitter state 적용은 새 renderer adapter이며 원작 virtual AnimationObject timeline 전체 복원이 아니다.

표현 TEMP: SoftSnowMist의 DepthFade12cm, spatial support power2, SnowTint linear RGB(.68,.74,.8), ParticleTintInfluence.25; IceDebris tint(.24,.48,.65)/roughness.35; StoneDebris tint(.17,.18,.20)/roughness.8이다. 원작 shader cook topology가 없어 source palette/scene-colour/ice shading 전체 일치 근거는 없다. editable material parameter/graph에 모았고 Source PC.A는 0–1로 제한하며 HDR RGB와 알파를 구분한다. Apes의 새 StoneImpact는 기존 source burst/motion을 재사용하고 ice horn 대신 실제 FS_Rock_01 3D mesh를 사용한다. geometry card를 억지로 채우는 평면 대신 실제 입체 파편을 사용한다.

ParticleSpriteVertexFactory.ush의 TexCoord0는 SubUV atlas-space다. 원래 단일 UV feather만으로 quad 경계를 막을 수 없어 각 RequiredModule의 SubImages_Horizontal/Vertical 값을 instance AtlasColumns/Rows로 전달하고 frac(UV*grid)로 frame-local support를 계산한다. 이는 engine 좌표 계산 근거이며 원작 shader 수치라고 설명하지 않는다. SnowAtlas01의322 Required binding과 정확한 Base_Axis helper renderer만 기록했다. DefaultParticle preview dot의 PC RGB0는 검은 덩어리가 되어 PreviewDots01의10 Required binding을 두 종 전용 SoftPowder로 변경했다. source smoke atlas 첫 프레임 1/9은 texture 이름/9x9 grid에 대한 좌표 계산이며 새 random velocity/빈도 수치는 넣지 않았다. source distributions·burst/수명·notify/GUID/프레임·raw tracks는 보존했다.

WorkAll02는155case/465PNG technical pass이지만 이후 atlas/palette 보완 전의 진단 증거다. WorkQuality01은103 actual source animation/8 affected standalone particles/3 objects, current private module8e56cac7…152b3f4에서114case/342PNG·input 동일·shader failures0/attachment regression 통과다. 모든 snapshot이 peak emission 또는 원작 pixel 완전 일치를 뜻하지 않는다. 마지막 PreviewDots01 후 Focus 검토·fresh saved audit·Main 선택 전달 및 Main 새 build/RHI가 남아 있다. continuity/ResumeState와 최신 영수증으로 재개하며 완료한 author나 과거 전체 import를 반복하지 않는다.

## 2026-10-13 — 중단 지점 재개 / 눈먼지 검정 출력 미해결

WorkFocus01(16case/48PNG)과 ForcePalette01 뒤 DustPalette01은 실행 검사를 통과했으나 Yetuga 눈먼지가 여전히 검은 덩어리로 출력돼 시각 검수는 실패다. 새 snow instance의 ParticleTintInfluence=0은 어시스턴트 TEMP 진단 설정이며 앞선 .25를 현재 후보에서 대체했다. 이것만으로 검정 출력이 해결됐다고 기록하지 않는다. Roar의 기술용 axis mesh도 저장 뒤 다시 보이는 문제가 남아 있다.

LODAudit01은 모든 enabled LOD의 재질 연결을 확인했고 runtime debugger에서도 LOD2 material[1]이 새 atlas MI다. 따라서 'LOD2가 구재질을 사용한다'는 원인 추정은 철회했다(DustDiagnosisCorrection.json). 실제 black 출력 branch를 구분하기 위해 private Diagnostics의 8개 단일 emitter fixture만 추가하고 RendererIsolationRHI01을 실행한다. 원본/production PS의 분산·수명·burst를 다시 저작하지 않는다. Main 게임 파일 반영은 아직 0이다.

## 2026-10-13 — 눈먼지 노출·메시 재질·볼륨 경계 수정

검정 원인은 Substrate 변경으로 확인되지 않았다. SnowSubstrateRHI01의 같은 emitter에 대한 legacy/Substrate 두 control은 모두 검정이었다. 새 두 snow parent에 현행 DefaultEngine.ini의 기존 물리 조명/발광 노출 방침인 EyeAdaptationInverse가 빠져 있었다. SnowExposure01에서 두 parent의 발광 경로에 전체 보정을 연결한 뒤 DustExposure01 동일 장면은 흰색으로 출력됐다. Source density/PC alpha/분산·수명은 그대로이며 임의 HDR 발광 증폭값을 넣지 않았다.

Roar의 Required.Material을 숨김 재질로 바꿔도 TypeDataMesh.bOverrideMaterial=false면 메시 슬롯을 렌더한다. MeshMaterialBinding01은 해당 Roar renderer 한 곳만 true로 바꿨고 WorkFocusFinal02의005_Roar_01에서 삼각 표시가 사라졌다. 기술 renderer 두 곳의 모든 LOD에는 투명0 재질을 연결했다. Source module 자체를 삭제하거나 transient SoloTracking에만 의존하지 않는다.

브레스의 회수된 Base_S_Spheremask_01은 카드 경계가 남아 FogSphereCard01에서 두 종 전용 유기적인 source smoke mask로 바꿨다. 아직 넓은 안개 경계가 남은 WorkFocusFinal02는 시각 완료로 표시하지 않는다. VolumeSupport01은 두 snow parent의 alpha에 native SphericalParticleOpacity를 곱해 실제 particle center/radius/opaque scene depth로 sphere extinction과 near-plane fade를 계산한다(Engine/Shaders/Private/MaterialTemplate.ush GetSphericalParticleOpacity). VolumeDensity=1은 차원이 없는 어시스턴트 TEMP 표현 설정이며 parent scalar parameter로 조정한다. 원작 shader 직접 수치가 아니다. 깊이와 near plane을 포함한 engine 계산은 technical 근거이며 원작 출처라고 표시하지 않는다.

WorkBuild08은 별도 HealVFX 빌드의 engine mutex 대기 중 우리 build만 중단했고 compile action0이다. 타 작업을 제어하지 않았다. WorkBuild09는 실제 최신 private Source에서 새 module4da21e21…fdf41dd로 성공했다. Main의 완료된 보조 물리 초기화는 전달 시 최신 Main KZMonster.cpp에 VFX scale 한 줄만 병합하도록 준비했다. WorkFocusFinal03와 fresh all-LOD WorkAuditFinal03 및 actual GAS patterns 후 Main 선택 전달/최신 build/RHI가 남아 있다.


## 2026-10-13T13:11:51.008812+09:00 — GiantVFX Main 실제 반영·시각 잔여 분리

Main 선택 전달196파일(기존 Source8/변경asset86/신규asset102)은 MainDelivery.json에 결속했다. 이후 CloseGrabSmash 1PS의 혈액 mesh 초기 크기4분포에 TEMP .01 단위 어댑터를 적용해 MainGrabFixed01의 전체 화면을 덮는 붉은 면이 사라졌다. .01은 수입 mesh 단위 대응을 위해 선정한 임시 무차원 배율이며 원작 VAT shader의 직접 복원값이 아니다. 원작 count/velocity/lifetime/notify는 유지했고 재실행하면 배율이 중복되므로 author를 반복하지 않는다. GrabMeshUnitDelivery.json이 후속 전달 정본이다.

RefractionPlaneDelivery.json의 소유 MI3를 기존 SoftPowder 부모로 바꿨지만 MainRefractionFixed01/013·014 Armageddon 실제 화면의 흰 판은 남았다. private 화면의 양성을 Main 시각 완료로 해석하지 않는다. 해당 원인은 미확정이며 실제 active component/renderer 및 부착 object를 확인해야 한다. 원작 cooked VAT/refraction shader와 전체 픽셀 일치는 미확인이다. 기술 검사155case/465PNG 및 후속23case/69PNG의 성공과 시각 미완료를 분리했다. FinalVerification.json: technical_passed=true, passed=false, visual_status=pending_armageddon_white_plane.


## 2026-10-13T14:16:31.407968+09:00 — GIant VFX 흰 데칼 투영의 실제 수정·Main 검증

흰 판의 최종 원인은 PS/LOD/충격파 MI가 아니라 Armageddon_Start가 남긴 FMI_Decal_Deferred_D_02의 투영이다. MainAffectedResume01 연속23에서 재현, ShockRendererIsolation01 및 AllParticleHideIsolation01에서 지속, DecalHideIsolation01에서 제거를 확인했다. 위치(219.84259,0,10010)cm, projection extent(200,900,900)cm의 단일 WorldSettings DecalComponent이며 숨기기 실험은 unsaved own world였다. 이전 MI3 재부모화가 이 흰 판을 해결한다는 주장은 철회한다.

원본 cooked distortion shader는 미복원이다. 현재 imported parent의 unlit emission과 공간 alpha support 부족을 Yetuga 전용 parent/MI 사본으로 보완했다. 원래 temporal alpha/colour/roughness와 event clock/GUID/위치/크기/수명은 유지하고 emission=0, DefaultLit base colour, inward radial envelope 및 원본 CachedReferencedTextures의 FT_Dirt_Tex_01.R을 사용한 임시 frost mark로 표시한다. 원작 package는 Metadata/MonsterVFX_20261008/HumanOriginal/Source/BBQ/Content/_Kazan_/Art/VFX/VFX_Material/Decal/MI/FMI_Decal_Deferred_D_02.json, ScalarParameterValues.Roughness 원시 .1(무차원)이다. R density 채널 해석과 radial envelope는 직접 복원값이 아닌 TEMP다. KZGiantDecalOpacity=.12는 어시스턴트 선정 임시 무차원 값이며 넓은 투영의 대비와 몸체 덮임을 줄이기 위한 선택이다. MI/parent에서 조절 가능하고 사각 edge/과한 중심 대비/눈 mark 가시성을 실제 겨울 바닥에서 조정 기준으로 삼는다.

SnowDecalRepair01은 texture input pin 이름 오류로 저장 전 실패했다. UVs를 사용한 SnowDecalRepair02는 성공했고 WorkSnowDecalAudit01 원본84 보존 및 WorkSnowDecalFinal02 연속23/69PNG를 통과했다. SnowDecalDelivery01은 기존 Armageddon_Start 1파일의 DecalMaterial만 변경하고 새 parent/MI2만 Main에 CAS/backup 전달했다. 공유 original material/texture, game Source/Config/Map/DLL resume 수정0이다. MainSavedSnowDecal01 원본84/null0 및 MainSnowDecalFinal01 연속23/69 실제 화면에서 흰 판 제거/나머지 눈·얼음 유지가 확인됐다. 최종 actual GAS/완료 상태는 FinalVerification.json을 따른다. 픽셀 원작 일치/Shipping/모든 frame 완전 일치는 미확인이다.

## 2026-10-14 — Apes/Yetuga PartGroggy 음향·이펙트 Main 적용

두 종의 부위 파괴는 원본 `Damage_PartGroggy_Start/Loop/End` clip을 전용 finite montage로 이어 사용한다. 원본 clip에 현재 연결된 `KZAnimNotify_PlayAudio`/`KZAnimNotify_CombatEffect` 수는 Apes Start·Loop·End 각각 SFX `3/2/3`, VFX `7/0/2`; Yetuga SFX `6/2/2`, VFX `14/7/9`다. 별도 특수 패턴 clip은 Apes `Damage_JustGuardReaction` SFX 3/VFX 2, Yetuga `Attack_ChargeTackle_Stun`과 `_Stun_End` 합계 SFX 4/VFX 21이며 기존 패턴 분기와 재생 시점을 보존했다. Exhaustion의 기존 Start/Loop/End notify도 그대로 사용한다. 바인딩을 다시 읽은 결과는 `Metadata/GiantReaction_20261014/AuditMain02/Audit.json`, 새 montage 저작 값은 `Author02/Authoring.json`이다.

Main RHI에서 원본 공유 `FP_Boss_Yetuga_PartGroggy_blood_01`의 VAT mesh 3개가 큰 불투명 붉은 판으로 나타났다. 해당 PS를 끄는 진단에서 판이 사라지는 것을 확인한 뒤, 원본 공유 에셋은 유지하고 두 종 PartGroggy Start notify만 새 `Content/Monsters/Shared/VFX/FP_PartGroggy_Blood_UnitFixed.uasset`로 연결했다. 복사본의 VAT mesh 3개에는 기존 opacity 0 기술 재질을 `bOverrideMaterial=true`로 적용하고, 혈흔·연기·작은 방울 sprite 3개와 원래 burst/분산·타이밍은 보존했다. 원작 cooked VAT shader가 없어서 이 메시 자체의 시각 재현은 미확인인 **기술 대체 표현**이다. 알파가 없는 불투명 메시의 사각 경계를 그대로 노출시키지 않으면서 source sprite 표현을 남긴 선택이다. 관련 진단은 `PIENoBlood01`, `BloodParticleAudit03`, `BloodHidden01/BloodHidden.json`이다.

Main 빌드 뒤 별도 에디터의 `MainPIEFinal/Driver.json`은 RHI 두 종 테스트 성공·material compile failure 0이다. `MainPIEFinal/PartGroggy_0_2.png`, `PartGroggy_1_2.png` 및 각 후속 프레임에서 붉은 판 없이 모션·작은 혈흔·눈/먼지 표현을 확인했다. 첫 Apes 캡처 두 장은 PIE 카메라가 전환되기 전 화면이라 시각 판정에 사용하지 않는다. 오디오 장치가 정상 초기화됐고 관련 notify/cue 바인딩에 로드 오류는 없었지만, 실제 청감·원작 믹스/DSP 동일성까지 검증한 결과는 아니다. 기존 공용 음향·VFX와 원본 package는 변경하지 않았다.

## 2026-10-14 — 최종 설정 변경 후 화면 재검증

약점 box half extent를 편집 가능한 Definition 설정으로 옮긴 뒤 Main을 다시 빌드하고 `Metadata/GiantReaction_20261014/MainPIETuningFinal`에서 두 종 RHI PartGroggy를 재생했다. `Driver.json` 성공, material compile failure 0, 8장 캡처 중 Apes `PartGroggy_0_2.png`와 Yetuga `PartGroggy_1_2.png`를 다시 시각 확인했다. 작은 혈흔·먼지 유지와 큰 불투명 붉은 판 제거가 유지된다. 최종 DLL/asset hash 및 원본 shader·청감의 한계는 `FinalVerificationTuning.json`을 따른다.


## Apes·Yetuga 잡기 경고 UI·SFX 원본 복원 (2026-10-14)

FModel 원본 증거는 `Metadata/EnemyBehaviorResearch_20261008/YetugaOriginal/AC_Yetuga_CloseGrab_Start{,_Ori}.json`, `AC_Yetuga_RushGrab{,_Slow}.json` 및 `Metadata/EnemyBehaviorResearch_20261008/ApesOriginalEvidence.json`의 `xxHoldingAttackWarning` NotifyState다. 원본 경고 리소스는 `BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/UI/FP_UI_BurstAttact_Grab`(Cascade 9 emitters: mesh 6, sprite 3), 텍스처 `FT_UI_BurstAttack_Font`, `_Blur`, `FT_Splash_Decal_02`, 메시 `FS_BurstA_001~003`이다. `ParticleModuleColorOverLife_12~17.ColorOverLife.Table.Values`의 처음 RGB는 `(5, 2.5, 0)`, 0.25 normalized time의 끝 RGB는 `(0.1, 0, 0)`이고, BG `_11`은 `(0.5, 0.25, 0)`에서 `(0.1, 0.05, 0)`이다. CameraOffset 원본 모듈은 10/50/80/99~102 cm 값을 갖는다. 원본 UI음 후보는 `BBQ/Content/_Kazan_/Sound/Ui/ui_holding_attack`, EventId `1713520362`, `BBQ/Content/WwiseAudio/Media/881646502.wem`이다. 복원 PCM은 48 kHz stereo, 4.360875초다. 독점 `xxHoldingAttackWarning` 네이티브 구현의 직접 particle/audio 참조는 추출 metadata에 없으므로 Notify 이름과 전용 asset·sound 명칭의 대응은 **근거 있는 추론**이지 원본 실행 코드의 직접 확인은 아니다.

원본 Notify와 현행 clip의 재생률/시간축을 대조해 `Metadata/GiantGrabWarning_20261014/WarningPlan.json`에 7개 창을 기록했다. 현행 적용초는 Yetuga CloseGrab Start/Ori `0.426349079~0.601462825`, RushGrab `0.300323580~0.469503228`, RushGrab_Slow `0.431678243~0.627242855`; Apes CloseGrab Start `0.0001~0.264423162`, Start2_Stone `0.000139266~0.468124387`, Start_Stone `0~0.268416542`다. 이는 원본 property 직접값이 아니라 원본 Notify 시점과 현행 재생축의 **계산 적용값**이다. 원본 추출 메타데이터와 계산 근거는 위 `WarningPlan.json` 및 `Scripts/Art/prepare_giant_grab_warning_20261014.py`에 남겼다.

원본 텍스처·PSKX와 9-emitter Cascade 그래프를 Main의 `/Game/_Art/Effects/Combat/GrabWarning/`으로, 디코딩한 원본 media를 `/Game/Audio/Original/Media/SW_UI_HoldingAttack`으로 가져왔다. 원본 cooked shader graph는 확보할 수 없어 세 Material은 마스크·particle alpha와 sharp/blur 텍스처를 사용하는 프로젝트 어댑터다. `FM_BurstAttack_BG`의 2x2 atlas 첫 cell 선택도 어댑터다. 원본 shader/믹싱·DSP/픽셀 일치로 표시하지 않는다. 기존 몬스터 VFX를 제거하거나 대체하지 않고 `UI_Chest`의 별도 GrabWarning 트랙에 추가했다. Apes의 0초 단발 오디오 Notify가 실제 PIE에서 건너뛰어져, 7개 모두 원본 경고 창과 같은 시작의 `KZAnimNotifyState_PlayAudio`로 바꾸고 유한 sound tail을 보존했다.

초기 Main PIE는 경고 PSC 8~9개 active particle과 양 종의 원본 음향 로그를 보였지만, UI가 몸체에 묻혀 화면에서 보이지 않았다. 원본 PS의 단독 실제 게임 렌더 `Metadata/GiantGrabWarning_20261014/ParticlePreview/Frame_93.png`는 검은 붓획과 금빛 섬광을 보여 재질 전체 실패가 아님을 분리했다. `KZAnimNotify_CombatEffect`의 명시적 UI용 옵션은 `UI_Chest` 위치에서 실제 mesh world AABB 앞면을 카메라 방향으로 계산해 배치·회전한다. 새 gameplay 수치 literal은 없으며 이 화면 배치는 원본 네이티브 구현이 확인되지 않은 **기술 어댑터**다. Notify 창 종료 뒤 `OnNotifyEndDeattach`로 잔여 입자를 분리한다. 마지막 Main RHI `Metadata/GiantGrabWarning_20261014/PIE/RuntimeReport.json`은 `Khazan.GiantFall.PIE` 성공, 경고 재생 5회, Apes/Yetuga active particle 및 `SW_UI_HoldingAttack` 로그 양성이다. `PIE/Yetuga_0.png`, `Apes_2.png`와 후속 캡처에서 두 몬스터 앞의 붓획/금빛 플래시와 사각 텍스처 경계가 드러나지 않는 것을 눈으로 확인했다. `SavedReadback.json`은 7개 asset의 UI·음향 state·분리 설정과 이전 단발 음향 0개를 새 에디터에서 재확인했다. 원작 실게임 같은 프레임과의 나란한 픽셀·청감 비교는 아직 수행하지 않았다.

## 2026-10-15 — Yetuga 작은 눈먼지 격자 배열 표시 Main 수정 완료

사용자가 이동/행동 때 작은 눈먼지가 오와열로 재생된다고 지적했다. 기존 AssetAuthor02/Author.json, ParticleObjectCatalog.json을 출발점으로 현재 dust/footstep 23 PS의 all-LOD renderer·관련 material12/texture4만 표적 검사했다. SavedAudit.json passed/save0이다. 원인은 아래 두 GiantPolish instance가 1x1 particle SubUV 설정에서 9x9 atlas 전체를 표시하던 복원 sampler다. 전체 atlas의 반복 구름이 각 입자 내부에 격자로 보였으며 실제 spawn 위치를 임의로 재배치하지 않고 sampler를 교정했다.

- 현재 texture: /Game/_Art/Effects/Shared/Textures/BBQ_Texture/SubUV/T_Smoke03_SubUV_9x9. Metadata/YetugaSnowLayout_20261015/Textures/T_Smoke03_SubUV_9x9.png에서 9열×9행을 직접 확인했다. grid9/9 및 frame81은 현재 imported texture layout/계산이며 gameplay 임시 수치가 아니다.
- 기존 MI: GiantPolish/Materials/MI_Atlas_MI_KZGiant_Snow_FMI_World_SubUV_color_A_05_1x1 및 _A_06_1x1. 기존 scalar AtlasColumns/Rows=1/1, texture Tex_Opa=위 9x9 atlas였다. 검사한 dust/footstep 23개 중17 PS가 두 재질을 사용한다. 큰 fluid/blur 레이어의 다른 material은 그대로다.
- Main 실제 수정: 기존 M_KZGiant_SoftSnowMist를 같은 Materials 폴더의 M_KZGiant_SnowFlipbook9x9로 복사하고 두 MI의 parent를 새 재질로 연결했다. 신규 material1/기존 MI2 총3 package, runtime Source·class·PS·animation·texture 변경0이다. 원래 공유 parent를 전역 교체하지 않았다.

새 재질의 SnowTextureColumns/Rows=9/9는 텍스처 레이아웃이다. R-density sampler만 (cell+quadUV)/grid로 한 프레임씩 읽고 인접 프레임을 선형 보간한다. 기존 ParticleRelativeTime의 normalized age a에 frame=a×(81−1), i=floor(frame), next=min(i+1,80), blend=frac(frame)를 사용한다. cell=(i mod9,floor(i/9))이며 모든 인덱스와 grid는 무차원이다. **이 수명 기반 재생 시계는 원작 custom shader 미확인의 TEMP 복원**이고 원작 FPS/clock 직접값으로 표현하지 않는다. 원래 PS의 birth/lifetime/velocity/위치·회전 분산을 유지해 각 입자의 원래 차이가 남으며 새 random gameplay literal을 넣지 않았다. 향후 source shader clock을 얻으면 이 전용 density sampler의 시간 입력만 맞춘다.

기존 soft-alpha Custom 코드, spherical extinction/near-plane fade, DepthFade, EyeAdaptationInverse, tint/particle-alpha 정책은 복사본에서도 유지한다. 두 MI의 scalar override/기존 texture override는 동일하다. 기존 parent를 포함한 보호 file39와 PS23의 SHA는 수정 직전/완료 시 동일하다. 앞선 사망 흰 데칼 수정8개도 SHA 그대로 유지했다. 원작 shader/pixel 완전 일치를 주장하지 않는다.

BeforeRHI02와 fresh AfterRHI01은 기존 Khazan.GiantVFX.ReviewPIE를 사용해 각각 particle7/source 이동·행동6/실제 saved GAS pattern2(NormalAtk01_Step1/DempseyRoll_Step1) 총15 case를 D3D12에서 재생했고 Success/shader compile·fallback failure0이다. Native PSI를 새로 만들지 않고 현재 저장 PS/clip/granted Ability를 소비했다. 008_Locomotion_SideMove_L_Long_01 전후 및 009_Locomotion_TurnBackRun_00에서 작은 격자 구름이 부드러운 한 덩어리 눈먼지로 합쳐진 외관을 확인했다. 늦은 standalone frame 일부는 짧은 burst 종료 후라 시각 양성 근거로 사용하지 않는다. 병행 QA의 GPU memory budget 경고가 한 action frame에 있어 성능 검증 완료로 읽지 않는다.

정본: Metadata/YetugaSnowLayout_20261015/FinalVerification.json, Authoring.json, BeforeRHI02/Driver.json, AfterRHI01/Driver.json 및 해당 전후 PNG. 수정 직전 MI2는 Backup/Content에 있다. 이번 작업의 빌드는 재실행하지 않았다. 독립 native build가 진행되어 before loaded DLL SHA80221660…/after8ab30b71…는 서로 다르며, 실제 사용 모듈을 그대로 기록하고 Source/Config/DLL을 과거 버전으로 되돌리지 않았다. Main 적용/표적 재생 검증 완료, 필수 잔여0이다. 후속은 이 report와 실제 instance parent부터 확인하며 완료된 author 전체를 재실행하지 않는다.
