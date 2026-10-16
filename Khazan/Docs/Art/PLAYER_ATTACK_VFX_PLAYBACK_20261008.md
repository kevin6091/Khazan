# 2026-10-08 — Player 공격 VFX 원본 분석·재생 이관

## 원본·현재 범위

원작 데이터는 기존 FModel 설정을 사용하는 EnemyExtractor/CUE4Parse의 UE4.27 DesktopMobile 표적 추출이다. 원작 설치 build/patch 번호와 native notify 코드는 미확인이다. 현재 Player ComboDefinition의 공격 18 node, 자동 후속 ChargeAttack04/SpinningAttack02, OverFury의 반복 segment를 대상으로 하며, 회피 이동 8 node는 공격으로 집계하지 않는다.

정본 리포트는 `Saved/ImportReports/PlayerAttackVFX_20261008`이다. `CurrentAssets/CurrentPlayerAssets.json`, `MetadataAudit/OriginalSourceTimingContracts.json`, `MappedOriginalEffectWindows.json`, `PreparedPlaybackPlan.json`에 원본 package/field/raw 값/초 단위와 현재 몽타주 위치를 보존한다. 클래스나 리소스 이름만으로 효과를 선택하지 않는다. StrongAttack01–03의 원본 None 상태 trail도 기본 PA_StatusAttack_DualAxeSword 경로를 따른다.

현재 구간에 대응하는 원본 이벤트는 Particle297, Decal50, DeepSnow65, Water20이다. Particle297의 93개는 원본에 적중 조건이 명시됐다. 상태별 분기는 현재 구현된 None만 선택한다. 원본 적중 조건 없는 혈흔 데칼은 피격 없는 혈흔을 피하기 위한 프로젝트 adapter로 적중 조건을 적용하며, 원작 CDO default 확인값으로 취급하지 않는다. 눈 변형은 기존 Snow owner를 사용한다. 실제 물 접촉 owner 없는 Water feedback은 무조건 파티클로 대체하지 않는다.

## 시간 변환과 수치의 출처

원본 Notifies.LinkValue/Duration/TriggerTimeOffset와 실제 AnimationTrack.AnimSegments, Dilation 적용 여부에서 현재 InGame 시간축으로 변환한다. montage offset과 segment 재생률을 적용하고 실제 현재 clip 끝에서 자른다. 잘린 WeakAttack01–04에 현재 전체 길이로 stretch하는 계산은 사용하지 않는다. Weak5 전 raw bone track/frame key와 불변 preExact60 전체 bake 앞부분을 비교했다. `CurrentAssets/WeakPrefixPoseProof.json`에 139 bone 전체 비교와 변동성 검증을 보존한다. OverFury _02_2/_02_3의 포즈는 _02와 모든 raw key가 동일하다.

OverFury _B_02 반복의 원본 leaf 시작 .54초와 현재 RateScale1/1.5/2는 원본·현재 실제 필드 기반 계산이다. _B_01 prelude에 이름이 비슷한 Yaksha Start의 다른 leaf 효과를 붙이지 않는다. 대응 원본 notify는 아직 미확인이다. Spinning01 앞부분 시간 대응의 추가 독립 포즈 비교 범위는 리포트의 mapping_proof를 따른다.

Decal의 크기/위치/회전 랜덤 범위와 LifeSpan은 원본 DecalCreateData를 보존한다. 누락된 FC_Decal_FadeOut_SlowIn/FastIn_SlowOut/FadeOut_Fast는 별도 표적 추출했다. 원본 RichCurve의 선형·cubic key와 tangent를 사용한다. curve 마지막 시간과 서로 다른 LifeSpan에 따른 정규화는 native 코드 미복원 상태의 해석이며 직접 원본 확인으로 표현하지 않는다.

## 머테리얼 복원의 한계

기존 751개 Cascade/2,028개 native effects의 선택 리소스와 원본 참조·hash를 표적 확인했다. 기본 복원 graph에서 소비하지 못하던 DynamicParameter와 RGB density mask를 다섯 master에 연결하는 작업은 private Effects에서만 수행한다. 원본 DP channel 명칭/값/커브/texture는 확인값이고 노드 연결 topology는 복원 해석이다. cooked expression graph가 없으므로 원작 shader와 픽셀 동등성을 보증하지 않는다.

첫 five-master RHI author는 5개 모두 compile error0과 저장을 확인했으나, After QA를 같은 Slate callback에서 재시작하는 helper의 재진입으로 private process가 crash했다. Before30 image/원본 backup/HLSL/실패 로그를 보존했다. fresh After 및 실제 공격 렌더 검증 전에는 화면 비교 완료로 기록하지 않는다.

## 현재 적용 상태·재개

이 절 작성 시 Main 런타임/몽타주/머테리얼은 아직 본 작업으로 변경하지 않았다. private `Khazan_AttackVFXWork_20261008/Khazan`의 DAS/Effects만 writable이며 나머지 Content junction에는 저장하지 않는다. `SourceIntake/MainIntake.json`으로 별도 공격 충돌 작업이 전달한 최신 Main Source를 보존하고 재사용한다. 다음은 native build → private marker author → RHI/실제 공격·취소 QA → Main 변경 보호 검사와 선택 전달이다. 런타임 계약은 `Docs/Engineering/PLAYER_ATTACK_VFX_RUNTIME_20261008.md`를 따른다.

## 2026-10-08 추가 — 시간 계약 교정과 private 저장 검증

약공격 원본의 `Properties.DilationCurve.BakedDilationCurveName="Dilation"`은 중첩된 필드다. 이전 조사 helper가 top-level만 확인해 dilation을 놓친 결과는 `MetadataAudit/BeforeCompositeDilationFix_*`에 보존하고 대체했다. 현재 `MappedOriginalEffectWindows.json`/`PreparedPlaybackPlan.json`/`AttackEffectPlayback.csv`는 원본 dilation inverse map과 full quantized bake의 시간 계약을 사용한다. 예를 들어 Weak01 원본 .3739509초는 현재 .33407066782초이며, 이전 선형 .36371050708초는 사용하지 않는다. authored full duration3.432643413543701초와 quantized3.433333333333333초의 차이는 계산값이며 게임 튜닝값이 아니다.

Spinning01의 독립 비교도 `MetadataAudit/SpinningPrefixPoseProof.json`에 실제 완료했다. 원본 불변 백업과 현재 139 bone×60 raw key의 8,340개 비교를 inverse map으로 수행했으며 position 최대 잔차4.12774784e−5 model units, quaternion angular 잔차5.04040450e−5 rad다. 시간에 따른 실제 포즈 변동을 검사해 refpose 비교를 배제했다. relocated backup의 UMetaData tag 부재는 명시하고, archive SHA/path와 기존 PlaybackPlan source identity를 함께 보존했다. Config·원본 백업·제품 sequence에는 저장하지 않았다.

private montage author는 종료 코드0과 `Authoring/PrivateAuthoring.json.status=passed`로 완료했다. 현재 적용 대상은 6개 몽타주의 347개 효과 window(Particle297/Decal50), 시작·종료 child694개다. 동일 trigger의 child는 하나의 native branching marker에 묶어 엔진의 동시 marker 누락을 방지한다. 기존 gameplay notify GUID/field와 section/sequence는 보존한다. UE의 기술적 endpoint offset ±KINDA_SMALL_NUMBER는 source gameplay time의 새 튜닝이 아니다. 아직 이 추가 절 시점에는 Main 전달 및 실제 공격 렌더 QA가 완료되지 않았다.

저장된 CSV에서 duration은 source emission/eligibility window이고, particle component의 잔여 수명은 원본 emitter lifetime/loop 및 destroy/deactivate/detach 정책을 따른다. decal LifeSpan과 opacity curve는 별도 열에 기록한다. retimed collision author의 별도 시간 계산에는 최대0.9035ms 차이가 보고됐지만 본 작업에서 피해 구간·충돌 geometry를 임의 재작성하지 않았다(`MetadataAudit/PreparedTimeCorrection.json`).

## 2026-10-08 18:36 KST — 현재 브루탈 어택 추가 범위·private 8몽타주 저장본 검사

병행 작업이 Main에 실제 추가한 `UKZBrutalAttackAbility`의 `AM_DAS_BrutalFront`/`AM_DAS_BrutalBack`을 현재 모든 공격 범위에 포함했다. 참조 원본은 `BBQ/Content/_Kazan_/Design/Kazan/Skill/DualAxeSword/Common/Grapple/`의 `AC_Kazan_DualSwordAxe_Com_Grapple_Start`, `AC_Kazan_DualAxeSword_Com_Grapple_Atk_01/_02`, `AC_Kazan_DualAxeSword_Com_Grapple_BackAtk_01/_02`다. 이름이 비슷한 `Grapple_SoulBringer` 자료를 대체 근거로 사용하지 않는다. 기존 Effects binding JSON/`AnimationEffectNotifies.json`의 정확한 `Properties.Notifies[index]`/원시 event·particle/decal property와 SHA를 재사용했으며 새로운 전수 추출은 없다.

고유 원본 5개에는 Particle45/Decal6/DeepSnow4 구간이 있다. 공통 Start의 Particle3이 Front와 Back에 각각 재생되므로 현재 몽타주 occurrence는 Particle48/Decal6/DeepSnow4다. 추가 authorable54개 중 원본에 `bOnAttackSuccessed=true`가 명시된 Particle10/Decal6은 실제 적중을 요구한다. 나머지 Particle38의 flag 부재는 원작 CDO default 확인값이 아니며 기존 프로젝트 adapter를 그대로 따른다. DeepSnow4는 기존 눈 변형 owner의 구간으로 보존하고 중복 무조건 파티클을 작성하지 않는다.

`PreparedBrutalPlaybackPlan.json`에는 정확한 source package/field/raw 값과 각 segment의 시간 변환을 별도 기록했다. `Metadata/MonsterStamina_20261008/AnimationPlan.json`의 적용된 composite bake dilation 계약 및 `MainSavedReload_ConcurrentBuild.json`에서 읽은 저장 시퀀스 길이·montage offset/rate를 사용한다. 원본 `DilationCurve.DilationAnimPositions`의 T_Original→T_Dilation 보간 뒤 exact60/authored 길이 비율을 적용하며, 이미 bake된 시간을 다시 전체 clip 길이로 stretch하지 않는다. 기존 `PreparedPlaybackPlan.json` 347개와 여섯 몽타주 author receipt는 덮어쓰지 않았다. 추가 계획과 합친 `CombinedPreparedPlaybackPlan.json`은 Particle345/Decal56, 총401개 구간이며, [추가 CSV](../../Saved/ImportReports/PlayerAttackVFX_20261008/BrutalPlaybackWindows.csv)와 [통합 CSV](../../Saved/ImportReports/PlayerAttackVFX_20261008/CombinedPlaybackWindows.csv)에 시간·window 길이·소켓·custom dilation·decal LifeSpan을 기록했다. 각 수치는 원본 직접 필드와 현재 시간축 계산값을 구분한다.

private author Cmd PID13676은 exit0, `BrutalAuthoring/PrivateAuthoring.json.status=passed`로 두 몽타주만 저장했다. 추가54개 window는 start/end child108개이며, 기존694개와 합친 `Authoring/CombinedPrivateAuthoring.json`은 8몽타주/401window/802child다. Front47/Back50개 branching marker를 추가했으며 기존 gameplay GUID/실제 trigger/section/segment를 보존했다. 원래 여섯 VFX 몽타주 bytes와 private retimed 시퀀스는 변경하지 않았다. 별도 fresh Cmd PID23028의 `CombinedSavedAssetAudit.json`은 8몽타주/401ID/401start/401end/8,308개 정확한 native field 검사 및 package bytes unchanged를 통과했고 exit0, asset save0이었다. 이는 저장·재로드·field 검사 결과이며 최신 실제 공격 RHI·원작 시각 일치·Main 전달 완료를 의미하지 않는다.

Main의 현재 BrutalHPDamage는 여섯 가족 모두0이며 원작 피해량을 확인하지 못해 미할당된 기존 설정이다. source success-only16개를 animation만으로 재생하거나 피해량을 임의로 채우지 않는다. 기존 cooked shader graph 미확보·source CDO 부재·native adapter 해석 한계는 유지한다. 다음은 최신 병행 Source를 합친 native build와 실제 브루탈/기존18공격·취소·avatar 격리 RHI 검증 후 선택 전달이다. 소스 intake와 빌드 상태는 Engineering 정본의 같은 날짜 추가 절을 따른다.

<!-- PlayerAttackVFX_20261008_MainComplete_1911 -->

## 2026-10-08 21:28 KST — 공격 VFX polish의 World atlas·ground density·Spinning alpha private 보완

새 사용자 요청의 사각 면·어색한 내려찍기·회전 공격을 `Saved/ImportReports/PlayerAttackVFXPolish_20261008`에서 별도 조사했다. 앞선 19:11 완료 보고서는 당시 결과로 보존한다. 이번 Art 담당 변경은 private `Khazan_AttackVFXWork_20261008/Khazan`의 기존 6 package이고 신규 에셋은 0이다. Main 제품 Source·Effects·DAS·맵에는 이 담당자가 저장하지 않았으며, 병행 혈흔 4 package는 별도 담당자의 범위다. 현재 6 package는 root의 전체 공격 RHI 검사 대기 상태로 동결했다. 이 절은 Main 전달 완료 기록이 아니다.

- `FM_World_SubUV_color_A`와 원본 static override가 명시된 자식 `_05`, `_06`, `_Breath`, `_Breath1`: 원본 `StaticParameters.StaticSwitchParameters.Opa_SubUV_Switch`의 `Value=true/bOverride=true`를 native switch 계약으로 복원했다. 원본 parent default는 확인되지 않아 native false default는 기존 plain UV 소비자를 보존하는 복원 선택이다. 원본 smoke atlas 색상·밀도가 서로 다른 프레임 입력을 사용하던 native graph를 같은 기존 atlas UV로 연결했다. 그 입력은 원본 `CachedExpressionData.DynamicParameterNames[0]=SubUV_frame`과 실제 Cascade slot0 lookup table이다. 9×9/8×8 등의 source MI grid 값은 변경하지 않았다. 정확한 원작 FlipBook 보간 shader graph는 stripped 상태다.
- 같은 World master의 추가 density 보완: 원본 `FP_P_World_Pc_Default_smash_weak`의 `ParticleSpriteEmitter_13`/Required13→`FMI_World_SubUV_color_A_04`에서 `ParticleModuleColorScaleOverLife_7.AlphaScaleOverLife.Table.Values` 최대 23.516392, `ParticleModuleParameterDynamic_7.DynamicParams[2].ParamName=Opa_dissolve`와 값 `[0,.38390103,.80018234,.9953124]`, TimeScale3을 직접 확인했다. Required6→`_07`의 AlphaScaleOverLife0 최대 12.173806도 원본 table 값이다. source `_04/_07`의 `DepthFade=50cm`, `SubUV_Pow=1`, `Emi_Pow=.5/.7` 등 override를 그대로 유지하고 기존 shader가 소비하지 않던 DP2/Pow/Strength/DepthFade를 연결했다. `max(0,pow(SubUV,SubUV_Pow)*SubUV_Str-saturate(DP2))*pow(Opa,Opa_Pow)*Opa_Str*saturate(ParticleAlpha)`의 density 조합과 **texture mask를 곱하기 전에 particle alpha를 0–1로 한정하는 순서**는 공개한 recovery adapter다. 원작 topology의 직접 복원이 아니다. Source particle alpha·색·size·lifetime 분포는 변경하지 않았다. Translucent Opacity에는 source DepthFade를 적용하며 Masked branch에는 같은 density만 전달한다.
- `FM_meshoffset_A`: 실제 Spinning 활성 4 emitter 중 `_272/_271`의 원본 StartAlpha500/300이 native Custom opacity의 마지막 texture-mask 곱 뒤에서 사용되어 넓게 포화되는 경로를 좁혀 보완했다. Custom 한 줄의 `*P48.a`만 `*saturate(P48.a)`로 바꾸었다. 이 alpha boundary도 recovery adapter이며 source HDR color/alpha 원시 값·MI·texture·회전·크기·수명·다른 Custom 계산은 유지했다. 원본 UI clamp/static graph를 확인했다고 기록하지 않는다.

현재 private 부모 최종 SHA는 World `f5511be641c2a56b0cbe335511c8dc97d8d7acf6b5d40e30cdf5d29ac0e06954`, MeshOffset `4f55b3a0262b3fcf18d73e5d9e4a23d6e0e5a634a1917e096e509eb8aead4efa`다. 실제 World 자식 11종과 Spinning/OverFury MeshOffset 자식 7종의 SM6 resource 통계가 양수이고 author/focused RHI log의 Failed-to-compile/Default-Material fallback은 없다. `GroundDensityAuthor/47dfe5cba5644a28b5f305873b953e18`, `MeshAlphaAuthor/9ebdc60ced8f495595ba4c6ca7991449`에 Before binary/T3D, After graph, compile 통계를 보존했다. 첫 density author의 Python CustomInput 생성 실패는 save0/exit1로 보존하고 재시도는 정상 exit0이다. 기존 숫자를 올려 모양을 가리거나 valid emitter를 임의 비활성화하지 않았다.

실제 이미지 검사는 `FocusedGroundMeshVisualReview.json`을 참조한다. 이전 `GroundIsolation/3072bb...`의 검은 polygon pillow는 density 적용 후 `GroundFocusedAfter/27158d286cee4ec481ca83f83904ea25/00_FP_P_World_Pc_Default_smash_weak_all_t0.8.png`에서 낮고 부드러운 먼지로 바뀌었다. smoke_1_t.15도 비어 있지 않은 부드러운 분산이며, 같은 technical lit floor의 Slashdust/Footdash/Crack에서 큰 검은 사각 면은 보이지 않았다. `MeshAlphaFocusedAfter/19b87a53d83e41b1a1d1035757099216`의 Spinning/RING_LOCAL은 넓은 검은 halo가 없지만, 흰 floor에서 흰 emission의 대비가 낮으므로 실제 gameplay 장면의 효과 강도가 검증됐다고 주장하지 않는다.

Strong03의 전체 공격 화면에 남은 **녹색 바닥 면은 아직 producer 미확정**이다. 읽은 native Crack child Color=(0,0,0,.5), EmisivePower0, parent BaseColor=Color였고 standalone source-black Crack는 회색 균열만 재현했다. source-obvious green debug collision wireframe 경로는 존재하지만 actual saved `bDrawAttackCollision` 값을 읽기 전까지 원인으로 확정하지 않는다. Root의 postfreeze 전체 공격 RHI와 실제 runtime component/flag 관측이 다음 절차다. 원작 full pixel parity·모든 방향/포즈·shipping 성능 검증은 이 절의 완료 범위가 아니다.

방향 판단에서는 `NativeRotationUnits.json`의 실제 source/native 24 lookup 값이 최대 1e−6 이내로 일치했다. Base001 StartRotation(.75,.15,.5)은 turns이며 계산값은 (270°,54°,180°), Flow Strong TypeData RollPitchYawRange(90,-180,0)는 degrees다. native mesh bounds 11종은 source ExtendedBounds의 비대칭 origin/axis와 일치하므로 global mesh yaw/mirror 보정은 근거가 없어 적용하지 않았다. DefaultParticle의 의심 carrier는 실제 `ERM_LightsOnly`로 sprite를 렌더하지 않았고, WorldFluid의 일반 TextureCoordinate에는 local UE sprite vertex factory가 Required SubUV frame UV를 이미 전달하므로 이 두 자산은 수정하지 않았다. 원본 metadata·native readback·local Engine 사실과 graph 재구성 판단을 구분한다.

<!-- PlayerAttackVFXPolish_20261008_PrivateWorldMeshFreeze_2128 -->
## 2026-10-08 19:11 KST — 현재 공격 VFX Main 반영·새 Main 실제 렌더 검증 완료

현재 범위의 선택 전달과 fresh Main 검증을 완료했다. [FinalVerification.json](../../Saved/ImportReports/PlayerAttackVFX_20261008/FinalVerification.json)의 상태는 `MainDeliveredAndFreshVerified`다. 최종 전달은 34파일/23패키지이며, Art15개(기존 master9/신규 dependency6)와 현재 몽타주8개를 포함한다. [CombinedPlaybackWindows.csv](../../Saved/ImportReports/PlayerAttackVFX_20261008/CombinedPlaybackWindows.csv)는 source 기반401구간(Particle345/Decal56)과 시간·소켓·조건·LifeSpan을 구분한다. 저장된 start401/end401 및 정확한 native field8,308개를 새 Main 저장본으로 대조했다. 추가 Brutal Snow4는 unsupported source 환경 구간으로 보존했으며 authorable401에 넣거나 무조건 particle로 대체하지 않았다. 기존 source Snow65/Water20도 같은 미지원 경계로 유지한다. 기존 Snow owner 구현과 이 원작 환경 notify의 완전 이관은 서로 다른 범위다.

Art 선택 변경은 source texture·DynamicParameter 이름/곡선·parameter/default/MI override를 보존하고 필요한 density/opacity/Masked 출력과 atlas 입력을 복구했다. Masked parent/Translucent child 및 그 반대의 출력 누락을 각각 보완했고, Masked 경로에는 translucent 전용 DepthFade 앞의 density를 사용했다. WorldSubUV는 기존 Custom_0.UV null을 기존 TextureCoordinate_1에 연결하는 한 입력 수정으로 SM6 fallback을 해결했다. native opacity가 이미 R였던 Base_Particle의 불필요 Mask 추가는 그 파일만 guarded restore하고 최종 후보에서 제외했다. 초기 opaque 면/네모, 체크무늬 fallback, 재진입 crash와 author guard 실패 기록은 삭제하지 않았다.

fresh Main RHI PID12708은 일반 공격18 및 Brutal 검사5를 통과했고176캡처, material compile/fallback 오류0, package save0, 136.063초/exit0을 남겼다. `MainRuntimePIE/ActualNativeModule.json`에서 실제 `UnrealEditor-KhazanPlayerAttackVFX20261008.dll`, SHA `ece6db2ebaaaa98fbbd0235553bba1691d5e520a12a563410aad2ee082032a99`를 확인했다. 별도 fresh Main saved Cmd PID32404도9.781초/exit0으로401구간과 저장 field 검사를 통과했다. 선택 asset의 Main SHA는 frozen manifest의 private expected SHA와 일치하며, 보호 Config/Data/Maps/미선택 DAS·Effects 및 원래 DLL을 보존했다. 실행·적중·취소/Avatar 수명 계약은 [Engineering 정본](../Engineering/PLAYER_ATTACK_VFX_RUNTIME_20261008.md)을 따른다.

Root는 private 실제11이미지와 Main 실제4이미지를 검토했으며, 이 Art 담당도 fresh Main OverFury121/123을 직접 열었다. textured 붉은·검은 strand와 투명 brown smoke/debris가 보이고, 이전의 불투명 effect 면/네모와 WorldGrid checkerboard는 사라졌다. Spinning의 흰 궤적, Brutal의 흰 궤적·붉은 spark도 검토 범위에서 확인했다. 바닥 Decal/Blood8개는 최신 전달 SHA가 lit-floor proof와 동일해 해당 mask·투명 외곽 검사를 재사용했다. 고정 `ArtCandidateManifest.json`의 초기 pending·Main변경0·`actual_overfury_visual_pass=false` 필드는 당시 준비 기록으로 보존하며, 현재 결과는 FinalVerification의 `frozen_manifest_supersession`과 `ReviewedAttackAndFloorProof.json`, 양쪽 `RootVisualReview.json`을 읽는다.

원작 cooked material/function expression graph, static-switch/VAT dynamic-remeshing 및 refraction/normal/scene-depth topology는 미확보다. RGB density·channel3=maxRGB·atlas mapping과 Decal `age*TimeScale/LifeSpan*lastKeyTime`은 근거를 공개한 native 해석이며 원작 graph 직접 복원값이 아니다. 0.5초 캡처 간격이 짧은 Weak/Strong 효과를 놓칠 수 있고 Back Brutal은 victim에 가려지는 구간이 있어401개 모두의 화면 가시성을 확인했다고 하지 않는다. 바닥 blood의 옅은 pink/red는 mask 가시성 증거이며 원작 농도 일치 증거가 아니다. OverFury B01 prelude의 대응 원작 notify, 원작 전체 pixel parity, 모든 HeinMach/StormPass 실제 카메라의 일치 및 shipping 최악 GPU 성능은 미검증이다. 새 native notify schema는 일반 에디터 재시작으로 로드해야 하며 Live Coding/schema reload로 대신하지 않는다. 사용자 PID16572는 DevMap/PIE없음/dirty0으로 보존했고 사용자 에디터 저장·reload·종료는 수행하지 않았다.

## 2026-10-08 추가 — 혈액량·네모 외곽 개선의 private 최종 후보와 검증 범위

사용자의 더 많은 혈액과 네모 없는 표현 요청에 따라 private `Khazan_AttackVFXWork_20261008/Khazan`에서 기존 에셋 네 개만 보완했다. 대상은 `/Game/_Art/Effects/Combat/Blood/PP_Dmg_Blood_Trail`, `PP_Dmg_Blood_Trail_Sub`, `/Game/_Art/Effects/Shared/Materials/BBQ_Material/Decal/FM_MeshDecal`, `/Game/_Art/Effects/Shared/Materials/BBQ_Material/Base/Base_DefaltParticle_Masked`다. 신규 에셋·게임 Source·HP·피해량·Data·Map 변경은 없다. 기존 `Base_Blood_Decal`과 혈흔 MI는 이번 Blood4 수정 대상이 아니다. [BloodCandidateManifest_Final.json](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/Blood/BloodCandidateManifest_Final.json)에 원본 package/SHA, Main 이전 SHA, private backup/최종 SHA와 author receipt를 보존한다. 이 절 시점의 Main 네 파일은 이전 SHA 그대로이며 아직 전달 완료가 아니다.

원작 `BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Physics/PP_Damage/PP_Dmg_Blood_Trail`의 `ParticleModuleSpawnPerUnit_2.UnitScalar` 원시80을 private40으로 바꿨다. 엔진 이동 거리의 cm 계약에 따라 같은 이동에서 분출 빈도를 두 배로 만드는 **어시스턴트 선정 튜닝값**이다. `PP_Dmg_Blood_Trail_Sub`의 `ParticleModuleSpawn_0.BurstList.Count` 원시 `[5,10,5,2]`·총22를 `[10,20,10,4]`·총44로 바꿨으며, 원시 Time `[.1,.1,.2,.3]`초는 보존했다. 크기·속도·collision·색·원작 emitter lifetime을 함께 확대하지 않았다. 이40/44는 사용자 요청에 대한 양 조절이며 사용자 직접 지정값이나 원작 재현값으로 표현하지 않는다. 정확한 field/raw 값과 두 배 계산은 `Blood/Author/08c81adf21ee4bd8b769da877110af9f/BloodPolish.json` 및 최종 manifest를 따른다.

`FM_MeshDecal`은 source의 뒤쪽 scene-depth 투영과 packed RGB density를 현재 engine World→Instance/Particle 변환에 연결했다. 개별 particle rotation/size를 포함하며, 복원 UV의 footprint를 source cube의 실제 크기로 제한해 큰 직사각형 투영을 제거했다. source cube의 unscaled 전체 너비5cm·native particle scale2.5에서 계산한12.5cm는 geometry 기반 계산값이다. DynamicParameter `InObjectUnitSize`의 원시34–36을 cm로 단정했던 초기 기록은 대체한다. 해당 DP의 원작 단위는 **미확인**이며 원작 WPO/투영 graph도 미확보다. `Base_DefaltParticle_Masked`의 density 입력은 Alpha 대신 source grayscale R, emissive 입력은 source `ParticleColor.RGB`로 연결하는 두 입력만 보완했다. 이 두 master의 최종 graph와 투영 해석은 원작 cooked shader topology의 직접 복원 증거가 아니다.

source PNG 자체의 alpha도 다시 검사했다. `T_Droplet_Mask2`는 Alpha255이지만 RGB 네 변의 경계값이 모두0이어서 R 기반 mask의 투영 테두리는 투명해진다. 반면 `FT_Bsse_Particle.png`의 Alpha는0–255로 변한다. 초기 “FT source alpha가 모두 불투명” 해석은 잘못됐으며 이 절과 [BloodVisualReview_Final.json](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/Blood/BloodVisualReview_Final.json)이 이를 바로잡는다. native R-opacity 연결은 source grayscale density를 사용하는 복원 adapter이며, 원작 opacity/alpha 압축 graph를 정확하게 확인했다는 뜻은 아니다.

별도 private RHI After3 PID7776은42.672초/exit0으로 두 시스템의12PNG와 네 파일 fresh saved readback을 남겼다. Root와 Art 담당이 핵심 실제 렌더 프레임을 확인했으며, 회색 불투명 바닥에 둥글고 불규칙한 붉은 물방울, 사라지는 혈흔, 움직이는 붉은 ribbon이 보이고 이전 공중 검은 상자·빈 사각 ribbon·직사각형 footprint는 해당 관측에서 제거됐다. 범위는 `Blood/Preview/bac9c8de032f4953912785fd8df44d52/BloodPreview.json`과 위 VisualReview를 따른다. 이는 중립 바닥 fixture 검증이며 HeinMach 최종 composition, 원작 농도·pixel parity, GPU/shipping 성능 검증이 아니다.

[ActualAttackConsumptionAudit.json](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/Blood/ActualAttackConsumptionAudit.json)에서 현재 통합401구간의 direct montage 참조를 확인했다. Trail56·Sub47, 총103구간이 실제 여덟 몽타주에 연결되어 있어 별도 Cascade child-event bridge에 의존하는 fixture 전용 튜닝이 아니다. 이103개는 confirmed-damage 조건 구간이며 After01 실제 로그의 PP 생성8건은 Weak01 및 적중한 Brutal Front/Back의 소비를 확인한다. 여덟 로그를103구간 전부의 화면 검증으로 확대하지 않는다. 실제 적중 카메라에서 최종 혈액량·가시성의 종합 검토와 Main 선택 전달은 아직 남아 있다. Source 수명·dispatch 교정은 Engineering 정본에 별도로 기록하고 이 Art 절에 중복하지 않는다.

## 2026-10-08 추가 — 브루탈 Recovery 흰 면의 private 선택적 외곽 보완

Root의 `Processes/FinalPrivate01/215_AM_DAS_BrutalFront_Attack2.png`에서 흰 노이즈 사각 면이 남아 실제 화면 검수를 보류했다. [BrutalFatalDiagnosis.json](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/Blood/BrutalFatalDiagnosis.json)은 현재401구간·실제 생성 로그·원본5 PS를 표적 대조한다. `FP_Kazan_DualaxeSword_Fatalblood_slash_01`은 브루탈 참조0이며, OverFury Finish 원본 `Properties.Notifies[18]`의 현재3.842533–4.228736초 한 구간에만 직접 연결된다. 비활성 `PP_AtkEx_Grapple_02` SubUV emitter7도 흰 사각 면의 원인에서 제외했다. 회색 Grapple slash의 Spear master 보완은 별도 담당 범위다.

흰 노이즈 후보는 원본 `BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/PC/DualAxeSword/FP_Kazan_recovery_stamina_01`의 `ParticleSpriteEmitter_10`/Required9/`Aura_00`이다. 원본 PS SHA는 `95e6e87eb0d76772c1b19498d918606477ba52fb1103274bf8df00aa8c9011a1`이다. Source Size9의100×170cm·Lifetime9의.7초, Required9의Delay.4초·local=true·PSA_Rectangle, ColorScaleOverLife8의RGB2·AlphaScale 최대1.4320999는 보존했다. MI243의 원본 `CameraFade_hardness=.5`, `CameraDistance=50`, `Tex_opa_clamp=3`, DepthFade250, OpaPow1.5, Emi tiling3×3·SpeedV.54를 [RecoverySheetRawContract.json](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/Blood/RecoverySheetRawContract.json)에 정확한 field·원시 table·package/SHA와 기록한다. Opacity texture `FT_Noise_Simple_Smoke_001`의 Alpha는255 상수이고 RGB 최대174지만 native Fluid는 이미 maxRGB density를 읽는다. 따라서 이 후보를 Alpha 채널 오선택으로 다시 설명하거나 채널을 임의 교체하지 않았다.

private 기존 `/Game/_Art/Effects/Shared/Materials/Fluid/FM_fluid_A`와 child `MI/FMI_fluid_A_243` 두 파일만 선택 보완했다. Parent의 새 scalar `KZFXRecoverySpatialEnvelope`는 기본0이고 child243만1이다. Texture tiling/distortion 전 UV에서 `xy=2*UV-1`, `smoothstep(0,hardness,saturate(1-dot(xy,xy)))`의 부드러운 타원 외곽과 `pow(saturate(PixelDepth/CameraDistance),hardness)`의 근접 카메라 fade를 곱한다. 이 수식은 누락된 공간 경계를 위한 **명시된 recovery adapter**다. 원본 .5/50을 사용하지만 그 의미·원본 cooked graph와 `Tex_opa_clamp=3` enum 매핑은 미확인이며 직접 복원값으로 표현하지 않는다. 작은0.0001은 나눗셈·pow의 기술적 영점 보호다. 원본 particle 색·alpha 분포·size·lifetime·재생 구간·template와 다른 Fluid 자식은 변경하지 않았고 추가 texture sample·신규 에셋·runtime 파일도 없다. 기존 Blood4는 그대로다.

저장 author PID32008은 양수 SM6 통계와 두 save 뒤 Windows 상대 경로의 `\\`/`/` 비교에서 실패했다. 앞선 PID23568의 commandlet rendering 설정 실패는 save0이고 두 실패 기록을 보존했다. 새 RHI PID30236은62.078초/exit0으로 저장된 default0/child1/입력4 연결·source.5/50·SM6 pixel222/vertex344/sampler6을 새로 확인했으며, 최종 log의 compile/fallback 오류0·package save0·36PNG를 남겼다. 새 검증은220개 미선택 Fluid 파일과 Main Effects2,034개 SHA 보존을 확인했다. Aura의.5/.6/.75초 실제 이미지에서 불규칙한 반투명 연기와 둥글게 사라지는 외곽이 보였고, 해당 분리 화면에 단단한 사각 테두리는 보이지 않았다. 전체 PS의 난수·위상은 실행마다 다르며 현재 검수를 원작 pixel parity나 자연 브루탈215 프레임 해결 완료로 확대하지 않는다. 50cm 근접 카메라 자체의 별도 화면 검사도 아직 하지 않았다.

[RecoveryCandidateManifest_Final.json](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/RecoverySheet/RecoveryCandidateManifest_Final.json)은 원본 package/SHA·Main 이전 SHA·binary backup·실제 Before/After·후속 저장 검증으로 post-save 경로 오류를 대체한 근거를 포함한다. 최종 private SHA는 parent `80574d50f50d3aba2531e70c8465e7e73d29d43b4d257c7a6f752cbca8ed109a`, MI243 `941801880e4418dc36d453fec8dd28124ae878e0005a931b5324a3daeb6161be`다. 이 담당자의 UE는 모두 종료됐고 Main 두 제품 파일은 이전 그대로다. 다음은 Root의 동일 최종 후보를 사용한 자연 브루탈 실제 공격 프레임 확인이며, Main 전달·완전 원작 일치·GPU/shipping 성능은 아직 완료 범위가 아니다.


<!-- PlayerAttackVFXPolish_Resume_20261010_SpearEarlyPreview -->
## 2026-10-10 ? Spear ?? ?? ?? ??? ?? ?? revision

?? `/Game/_Art/Effects/Shared/Materials/Slash/FM_Kazan_Spear_A` ? ??? ??? private ??? ??? `Saved/ImportReports/PlayerAttackVFXPolish_20261008/SpearCandidateManifest_OpacityRevision_20261010.json`??. ??4a163 ?? manifest? ?? ??? ???? ???. ??75833c9bff85c9233255cde90de62a73b013ef5d8a0b99b7d88b53dab95785b2? ?? opacity? MainCurve.A?boundedParticleAlpha? ???? HighlightCurve.A? radiance?? ???. source numeric/MI/PS/mesh/curve atlas ??? ??. U?UT?Offset ? V?VT/row.5, highlight radiance? ??? ??? adapter?? ?? shader graph ?? ???? ???? ???. source Normal? Main03/Highlight04?HighLight_Pow1, _06? Main01/Highlight02?parentPow50?? ?? source override? ?? ????.

? hidden private author PID16544? master ??1, parent/child2 ?? SM6 PS166/VS344/sampler6, ???Effects2033 ??, Main parent baselinecbbfb22... ?? ?50.515?/exit0??. ?? actualRHI PID29176? shader/capture? warm source PSC? ?? ?? ? ???? ?? source PS? ? PSC? ??? ? ??age.03333?? ????. `.03/.06/.1/.15/.25/.4/.65` ??? ??age`.03333/.08188/.12558/.16866/.26390/.40681/.66295`? ?? ???? source lifetime.5??particle?? ??? ???. ? ??/??? ??0, ?? ?? ??0/38.047?/exit0?current package hash ???compile/fallback log match0??.

???? ?? `.03`, `.15`, `.4` ? ???? ???. ? ????? ?? ?? ? ???? ?? ??? tail? ??? ??? ?? ? ?? ??? band? ?? ????? ??? ???. ??? ???? crescent, ???? ?? ?? ? mesh ???? ????. ?? ? ??? geometry cut? ??? ? technical floor? tail ??? ???? ?? ?? ?? ?? ??? ?? parity? ???? ???. ?? ??? ?? image SHA? `Resume_20261010/SpearOpacityVisualReview.json`, ???capture/source boundary? `SpearOpacityPreview/6b9195f39df74ee0bccfa43951f86598/SpearAfter.json`??.

?? ??? own UE? ?? ?? ????. Main ?? ???0?? Root? current75833 ?? front/back attack ??? ?? ? producer ??? ?? ??. ?? root13 ??/saved13?unchanged8???401/??18??+Brutal5/?? Main ???fresh Main ??? ???? ? ? ??? Main ??? ???? ???. ?? row? `Resume_20261010/FrozenAdditionalRows_OpacityRevision_Proposal.json`?? FrozenCandidateManifest ??? ???? ???? ???.

## 2026-10-11 — 중단된 Player 공격 VFX polish 재개·Art18 Main 검증 완료

중단 지점은 후속 전체 공격 검사에서 SpinningAttack02의 강한 내려찍기에 남은 큰 삼각형 연기였다. Actual15의 동일 pose/time/camera/history 슬롯 제외 검사로 `FP_P_World_Pc_Default_smash_strong` slot5→`FMI_World_SubUV_color_A_03`를 특정했다. Root RCA SHA7c4e1f12…와 이전 실패/철회 기록을 보존했다. Shock/World07에 대한 초기 추정과 잘못된 author draft는 실제 제품 수정으로 적용하지 않았다.

원본 Required7의 `CutoutTexture=FT_Sphere_CutOutTex`, `OpacitySourceMode=OSM_ColorBrightness`, `AlphaThreshold=0.5`를 근거로 기존 World 부모와 child03만 보완했다. 부모 `KZ_World03CutoutThreshold=0`은 기술적 비활성값이고 child03만 원본0.5와 RGB Sphere texture를 사용한다. 기존 Custom 8입력에 RGB/threshold 2입력을 더하고 emission·source scalar·native inherited switchfalse/overridefalse를 보존했다. RGB 평균의 정규화 remap과 기존 Mask.R에도 적용되는 Sphere override는 공개한 reconstruction adapter다. 원본 inherited static default·stripped shader topology·live native DDC geometry는 미확인이며, CPU 정수 평균과 shader 연속 실수 평균의 차이를 원작 픽셀 일치로 표현하지 않는다. 원본 particle 크기·수량·회전·수명·구간을 바꾸거나 emitter를 없애 삼각형을 숨기지 않았다. 실제 private save2/SM6 성공 receipt SHA3b9d1f21…, 부모2b492194…/child03 92e677ba…를 Frozen18 SHA660863c6…에 결속했다.

최종 Main 후속 전달은 기존 머테리얼6개(World 부모/child03, Spear, Shock, SubUV, Ribbon)뿐이고 Source/native/modules 쓰기는0이다. 앞선 original14와의 최종 Art 합집합은18개다. 원래 provisional 전달·Frozen17·PrivateReady·source metadata·backup은 보존했다. 병행 Monster가 이미 전달한 Source101/Build19와 현재 b84 alias, 기존 Player alias를 exact CAS로 보존했다. 최신 의존성461개 및 외부 WPO1의 동기화는 private 검증 환경에만 적용했고, 해당 Main 파일을 이 작업에서 재작성하지 않았다. [최종 완료 receipt](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/MainDelivery/ArtFollowupV5/Prepared_20261010T164700280003Z/Completion.json)의 `ArtFollowupDeliveredAndFreshMainVerified`가 이전의 Private11/Art17 HOLD와 followup pending을 이 검증 범위에서 대체한다. 원래 old14 helper/receipt를 덮어쓰거나 finalize하지 않았다.

실제 private12는 PID4828/155.920535초/exit0, 별도 Saved12는 PID3600/116.693587초/exit0이다. 최신 Main RHI02는 PID29752/175.63797초/exit0으로 공격18+Brutal5 및 취소/instance/avatar/late-marker cleanup을 통과했고264캡처를 남겼다. 별도 Main Saved02 PID31340/133.56034초/exit0은 몽타주8/401구간/8,308필드와 Art18의 source/hash/graph/양수 SM6 통계 검사를 통과했다. 두 fresh Main process 모두 실제 selected `UnrealEditor-KhazanMonsterVFX20261008.dll` SHA b84df875… 로드, source/config/effects/DAS/project/native snapshot before==after, save0, compile/default fallback 오류0이다. private98/d195는 예비 Art 회귀 증거이고 Main101/b84가 최신 실행 검증이다. 보호 입력13개도 전후 변경0이다.

Root의 [실제 Main 화면 검토](../../Saved/ImportReports/PlayerAttackVFXPolish_20261008/Resume_20261010/ArtFollowupPlans/Main02V5Bound_20261010T165705559241Z/RootVisual_Main02_ACTUAL_ROOT_ACCEPTED.json)는 직접 연9장의 SHA/실제 시간을 결속한다. Weak005 0.50686초는 양수인 가는 곡선 슬래시이며 바로 전004는 아직 렌더 전이다. Strong038 9.93967초는 좁은 곡선 궤적과 국소 먼지가 보인다. Spin121/122의2.07965/2.22464초에는 이전 큰 sky triangle/흰 바닥 원판 없이 충분한 brown dust와 암석이 남는다. Front215/243/244 및 Back260은 분산된 붉은 혈액·sparks를 유지하면서 이전 큰 불투명 흰 Ribbon 카드·거대 흰 beam·검은 면이 보이지 않는다. actual14/15의 원인 격리와 fresh12/Main02의 다른 시점 품질 관측은 동일 픽셀 A/B 비교로 혼동하지 않는다. 독립 Main 검토 SHA8ae7945c…와 Weak positive 보충 SHA36d79fa0…도 별도로 보존했다.

혈액80→40cm 및 burst총22→44는 사용자의 더 많은 혈액 요청에 따른 기존 **어시스턴트 임시2배 튜닝**이다. Spear의0.10 raw UV 보정도 임시 adapter이며 원작 검증 수치가 아니다. Source emission Pow/alpha boundary/RGB mask/normal·refraction 연결과 source cutout 소비 복구를 원작 cooked graph의 직접 복원으로 표현하지 않는다. Shock는 inactive0 equality/active1 반응 증거까지만 확인했고 원작과 같은 선명한 wave를 확인했다고 하지 않는다.

작은 흰 사각 glints, 짧은 회색 Spear 띠와 옅은 ghost sheet가 남는다. 원작의 정확한 밝기·normal/refraction·전체 shader/pixel parity, 모든401구간의 화면 가시성, HeinMach/StormPass의 모든 실제 카메라와 Shipping 최악 GPU 성능은 미검증이다. 큰 표적 artifact 보정과 최신 Main 동작 검사는 완료했다. 원작 룩을 추가로 좁힐 때는 이 final hash/캡처를 기준으로 해당 MI와 원작 같은 공격 프레임을 표적 비교하며 전체 추출/authoring/delivery를 다시 시작하지 않는다. Root 소유 숨김 프로세스들은 종료됐고 사용자/외부 에디터 제어는0이다.

<!-- PlayerAttackVFXPolish_Resume20261011_Main18Complete -->

## 2026-10-11 — HeinMach clean presentation 및 공격 VFX 경계 교정 완료

[이번 작업 정본](HEINMACH_CLEAN_PRESENTATION_20261011.md)과 [Completion](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion.json)을 우선한다. HeinMach authored PP/툰/외곽선8 제거, 나머지9861 actor/component 및 Sky/Fog/조명198 보존을 fresh canonical-map RHI에서 확인했다. VFX128 emissive root에 역노출 보정을 적용했다. AutoExposure=False trial은 백색 clipping 때문에 철회했으며 기본 장면 metering/HDR/AA/물리 Fog는 남는다.

차지 slot0 smoke의 미연결 마스크와 slot1의 false color-switch 오소비를 교정했고 최종 실제1.1235초 격리 화면에서 두 사각형 제거를 확인했다. OverFury cube는 VAT decode/WPO 누락을 원본 VAT4 데이터+공식 native decoder로 교정했다. 혈액은 이전보다 실제 sprite 분사를1.5배 늘리는 임시 튜닝이며 decal 증가는 없다. 이동 경로 mesh-decal의 source15/s는 임시0/s로 중단했고 마지막 baked cache까지 fresh readback으로 확인했다. source 숫자/임시 숫자·원작 stripped shader 경계는 새 정본을 따른다.

<!-- HeinMachCleanPresentation_20261011_FinalVerified -->

## 2026-10-11 — 최종 혈액 분사/데칼 event 분리 증거 보충

최신 제품 snapshot은 [Completion_FinalBloodEvents.json](../../Saved/ImportReports/HeinMachCleanPresentation_20261011/Completion_FinalBloodEvents.json)이다. sprite 분사66은 유지하면서 death→mesh-decal의 기존 Frequency0을 임시3으로 조정해 간접 decal 증가도 억제했다. 연속 Rate editable/baked0과 최종 Frequency3을 FinalAssetReadback03에서 확인했다. 정상66개 death 조건의 이론상22 events는 계산값이며 runtime 총량 실측은 아니다. 이전 snapshot과 실제 native/RHI 검증은 보존하며 다른138 asset/Source/Config는 그대로다. 상세 원본/TEMP 구분·검증 범위는 [Art 정본](HEINMACH_CLEAN_PRESENTATION_20261011.md)의 최종 추가 절을 따른다. 필수 잔여 작업은 없다.

<!-- HeinMachCleanPresentation_20261011_FinalBloodEventSeparation -->
## 2026-10-11 — Main DAS/blood 표현 후속 완료

기존 원작 이벤트 창·transform·수명 및 VAT/charge/최종 blood parent를 보존하고 DAS variant1/core6의 sprite 증량·tint와 blood4 physical sprite를 보완했다. actual montage3/event36만 재연결했고, 최종 native18+Brutal5/392 captures/save0/fallback0을 확인했다. 수치는 원작 직접값이 아닌 어시스턴트 임시 표시 튜닝이다. exact 변화14개/혈흔 sibling remap/검수·backup/receipt는 [Art 후속](COMBAT_PRESENTATION_FOLLOWUP_20261011.md)과 Engineering 동명 정본을 따른다. 중복 author로 증량을 재적용하지 않는다.


## 2026-10-12T13:12:55+09:00 — 사망·브루탈·공격/회피/착지 효과 Main 후속

기존 PP_Player_Parry_Success(원본 JustGuard13 emitter의 로컬 alpha 복원), PP_AtkEx_Grapple_01/02와 original world smash_weak surface variants를 재사용했다. 새 particle/material/texture asset0. 원작 출처는 Metadata/Parry_20261012/OriginalEvidence.json, Content/_Art/Effects/Metadata/Extraction_20261006/AssetManifest.json, Saved/ImportReports/PlayerAttackVFX_20261008/CombinedPlaybackWindows.csv 및 기존 Player VFX playback 정본이다. gameplay source field/공격 피해/모션 데이터/오디오는 그대로다.

montage8에 추가된55 window는 공격44(파랑+보라/검붉은 accent), 방향별 회피8, 착지3이다. 기존 trigger/입력 event GUID/field·section/segment 보존을 저작 시 확인하고 SavedAudit02에서55 start/end pair·template·scale·수명을 재조회했다. 루프를 방치하지 않고 notify end에서 deactivate하여 잔여 입자를 drain한다. 기존 Spin 강한 내려찍기2 marker의 dust/snow/grass strong variant는 weak variant로 바꿔 바닥으로 낮게 퍼지게 했고 실제 weapon-tip/walkable normal 기준을 적용했다. 착지 먼지는 벽에 들어간 칼끝의 실패를 피하려고 실제 grounded actor 발밑으로 보정했으며 collider/gameplay 위치는 바꾸지 않았다.

새 수치는 모두 어시스턴트 TEMP 표시값이다: attack blue scale0.35(가벼운 공격)/0.5(강한 공격), accent0.25/0.35, dodge0.25, plunge blue0.5/purple0.4/ground1, Spin ground0.8. Notify Scale3D에서 조정한다. 착지 start는 기존 Land section entry+UE endpoint epsilon0.0001초이고 window0.121175006초는 저장 source damage window 길이를 사용한 표시 adapter이며 새 gameplay duration이 아니다. weapon-tip100cm는 기존 blood source RelativeLocation.Z=100에서 가져온 cm 값이고 원작 floor native writer를 복원했다고 표현하지 않는다. 효과 기호의 파랑/보라/검붉은 인상은 현재 복원 parent·조명에 따른다.

혈흔 TEMP는 Monster Class Defaults: main 기존8/95/150cm half extents, satellite6(technical presentation cap16), radius90–280cm, size factor0.35–0.65, 기존24초 hold+3초 fade 유지다. 전체 방위로 점과 불규칙한 큰 얼룩을 함께 펼친다. shape/RGB 마스크·검붉은 분사·source ash와 dissolve3초는 이전 사진 혈액 구현을 재사용한다. 정상/짝 사망의 source 끝 포즈 수리와 실제6종7장/4방위 검사는 Engineering 최신 절을 따른다.

실제 게임 viewport 캡처와 source/hash/원본 보호는 Metadata/CombatFinishFollowup_20261012/PresentationFinal02·FinalVerification.json, 추가 ground 보정은 PlungeAnchor01/Applied.json에 있다. 대표 실제 화면을 별도 검토하며 editor screenshot/이전 실패를 시각 합격으로 쓰지 않는다. 전체 native shader/pixel parity·Shipping stress를 주장하지 않는다.


## 2026-10-12T18:14:49.705318+09:00 — 내려찍기 바닥 Niagara·alpha Main 완료

사용자 지정 /Game/VFX/03_SlashHit/KZ_Parring_Distort의 원본6 emitter는 그대로 보존했다. /Game/_Art/Effects/Combat/PlayerSlamDistort/NS_Player_Plunge_ParringDistort 복제의 M_SW_distort_Sprite_0/M_SW_distort_Sprite001_1/Hit003_6 renderer만 CustomFacingVector 및 실제 User.KZFloorNormal로 저작했다. shader에 카메라 facing을 남기는 잘못된 수동 binding trial은 native author의 host-map binding3개 true로 대체됐다.

원본 parent/MI2쌍을 새 경로에 복제하고 기존 opacity에 UV radial feather(.8–1)를 곱하며 refraction 가장자리를 중립1로 돌려 사각 경계를 제거했다. 이는 어시스턴트 표시 TEMP이고 원작 직접 수치가 아니다. scalar/vector/texture override는 원본과 동일하다. 원본 source Niagara/머티리얼/텍스처를 수정하지 않았다. 실제 RHI PrivatePIE05/Fall_02 화면에서 부드러운 바닥 원형과 사각 경계 제거를 검수했고, fresh Main saved/RHI가 같은6 package를 검증했다. 경로·SHA·runtime 증거는 Metadata/PlayerSlamDistort_20261012/FinalVerification.json. Fab 사용자 지정 효과와 원작 metadata 재현은 구분하며 원작 pixel/shader 동일성은 주장하지 않는다.


## 2026-10-12T21:06:38.746735+09:00 — ARCH-95 최신 추가 Slash·타격 표현 Main 완료

몬스터의 지정 Slash/Sting 참조는0으로 복구했고 기존 player effect100 객체를 보존한 채 KZ_Slash 별도 child100을 추가했다. Shader/색·source 원래 효과를 제거하거나 대신 재생하지 않는다. reference bones FX_L_Axe_01/02 및 FX_R_Sword_01/02의 geometry를 실제 Weapon_L/R grip에 연결한다. WeaponSlashProbe04의 reference measured offsets와 SM_VFX_SlashRing_01 bounds[-100,-100,-20]..[0,100,20]cm, Meshes[0].Rotation.Yaw180deg에서 span200/centre 보정을 계산했다. 이 숫자는 요청 Fab/current imported asset의 좌표계 변환이며 원작 gameplay 튜닝값이 아니다. shared KZ_Slash/KZ_SwordsMan_Sting asset은 수정하지 않았고 component만 독립 회전·크기 곡선을 중립화한다.

기존 원작 spark adapter를 CPU finite120(40×3)방사형 불꽃으로 재사용했다. TEMP는 life.18–.38s/speed1000–1800cm_s/width2–4cm/length16–30cm 및 blue(.04,.28,3)/purple(1.4,.025,2.4)/red(2,.012,.035) linear HDR와 alpha(0,.95),(.55,.7),(1,0)이다. 실제 수치 조정은 소유 PS의 module/curve에서 한다. 기존 혈액3 emitter와32 root blocks 및 nested data를 보존하며 승인 hit·parry·player received hit에서만 이 burst를 소비한다. cancelled PP/M_Monster_HitFlameFlash 두 asset은 Content에서 제거하고 metadata backup을 보존했다. 추가54 unconditional colour windows는 복원하지 않았다. 기존 ground scatter·dissolve/ash·SlamDistort alpha는 보존한다.

실제 BurstVisual05의120입자/얇은 radial streak 및 중간 contact, natural player original+additional/added-only4 frames, actual monster hit/received-hit 화면을 검수했다. 최초 GPU와 fluid material의 가시성 실패, old raw size lookup cache, camera API 오류는 실패로 보존한다. AdditiveSaved02·ExactBeforeAudit01(220×21 차이0)·FinalVerification이 최신 정본이다. 앞선 replacement author/delivery와 resource 전체 추출/Root/FPS author를 반복하지 않는다.


## 2026-10-13T13:18:40.096195+09:00 — OverFury 추가 Slash 철회·현재 무기 정렬 완료

OverFury의 추가 KZWeaponSlash17쌍만 제거했다. 다른5 montage의 추가33쌍은 같은 /Game/VFX/01_ARPGEssentials/KZ_Slash를 유지한다. 원래1359 effect objects×37 properties와6 montage notify clocks/GUID는 fresh Main 조회에서 그대로다. 원작 source FX를 대신 재생하거나 shared Niagara/mesh/material/texture를 편집하지 않았다.

이번 정렬은 raw mesh만 보던 종전 방식에 실제 emitter pose를 포함한다. SM_VFX_SlashRing_01 radius100cm×initial XYsize2 → effective diameter400cm; particle initial .25turn→90deg + renderer180deg + addon correction90deg=360deg. System User.ScaleLerp=.15의 내부 1±u growth는 component0으로 neutralise하고 actual initial2를 보존한다. addon location0은 이전 bbox centre 보정을 제거한 데이터이며 실제 칼끝 기준 runtime anchor를 사용한다. 숫자는 요청 Fab/current imported asset의 직접값·계산이며 원작 gameplay 튜닝값이 아니다. 정확 field/raw/수식은 Metadata/PlayerSlashAlignment_20261013/NiagaraGeometryEvidence.json을 따른다.

실제 여러 시점/타이밍의 weak/strong/charge/dodge/spin/Fury game captures, true addon-only 검사(Cascade+원래 mesh trail/decal 임시 숨김·복구), 공중 Spin 추가 검수와 실제 GPU endpoint/절삭면을 확인했다. MainRHI01·MainSpinRHI02·최신 병행 module MainRHI04ComposedPreview 및 fresh saved/build 근거는 FinalVerification.json이다. 대표 MainSpinRHI02/Slash_16_Frame036_View0.png. source shader/pixel 완전 일치나 모든 Shipping 프레임 전수 합격을 주장하지 않는다.

<!-- PlayerSlashAlignment_20261013_complete -->

## 2026-10-13 — WeakAttack01 실제 내려베기 방향·전방 확대 Main 완료

사용자 사진에서 지적한 첫 약공격을 원래 효과와 KZ_Slash로 분리 재생했다. KZ_Slash는 회수 중인 Weapon_L을 따르던 첫 start/end2 객체만 Weapon_R의 FX_R_Sword_02/01로 바꿨다. 현재 실제 장착 Imperial_R는 내려베는 쪽이며 current CPU-skinned LOD0 geometry/포즈는 Metadata/WeakAttack01Slash_20261013/EquippedGeometryObservation.json과 CuttingHandEvidence.json에 남겼다. 이름만으로 원작 내부 실행 손을 확인했다고 설명하지 않는다. UV 반전 후보는 철회했고 최종 scale은 모두 양수다.

요청한 더 앞쪽·더 큰 표현은 첫 타격에만 TEMP 전방35cm/XY1.15배다. 원래 PlaneSlash start/end의 RelativeLocation.X 15.265580→50.265580cm, XY scale1→1.15 및 원래 Z.95 유지. 추가 KZ_Slash start/end는 avatar-local RelativeLocation(35,0,0)cm와 Scale3D(1.15,1.15,1)이다. yaw90/effective span400cm·emitter initial90/XY2·renderer180과 기존 source clock0.334464–0.599631초/CustomTimeDilation1.25는 보존했다. 새 숫자는 원작 검증값이 아닌 사용자 요청에 따른 시각 TEMP이며 소유 notify 설정으로 관리한다.

공유 KZ_Slash/두 ring mesh/원래 FP_DAS_PlaneSlash_Enhanced와 OverFury는 SHA 동일하다. mesh/texture/material/alpha 변경0이며 다른 공격·원래 오디오/clock/GUID/HP·ST·Physics를 보존했다. Main fresh saved는 private FinalAuthor01 전체 serialized export와 동일하며 차이는 첫4 객체의 location/scale/near/tip뿐이다. SourceField의 L 표기는 초기 author 이력이며 현행 Near/Tip의 R override가 정본이다.

실제 MainRHI01의 세 시점289장/초중후·18공격·Brutal4·GPU70 및 MainYaw90RHI01의 회전된 actor 재생을 확인했다. 대표 사진은 MainRHI01/Slash_00_Frame004_View1.png, Slash_00_Frame005_View2.png 및 MainYaw90RHI01 동명 사진이다. GPU0.000031cm는 reference tip+35cm 설정의 검수 오차이며 물리 메시 vertex/원작 pixel 완전 일치가 아니다. 현재 가상 marker와 Imperial_R vertex의13.147cm 차이는 측정 경계로 분리한다. shader compile failure0, 필수 잔여0이다. 전체 증거/실패·철회/백업은 Metadata/WeakAttack01Slash_20261013/FinalVerification.json과 ResumeState.json이며 stale private Source/DLL·실패한 exporter/mirror·전체 author를 재사용하지 않는다.

<!-- WeakAttack01Slash_20261013_complete -->

<!-- CombatVFXSequencer_20261013_EditorGuide -->
## 2026-10-13 18:10 KST — 공격 애니메이션과 Niagara 시퀀서 편집

에디터를 재시작한 다음 Tools → Khazan VFX → WeakAttack02 VFX 열기를 실행한다. 열리는 에셋은 /Game/Tools/CombatVFX/LS_DAS_Player_WeakAttack02_VFX다. Player 트랙은 현재 BP_Player의 몸·장비와 DAS_Player_WeakAttack02를 재생한다. VFX | KZWeaponSlash_... 트랙의 잠긴 첫 Transform section은 현재 메인 공격에서 관측해 가져온 출발 궤도다. 아래 Additive section을 선택해 키프레임을 찍고 뷰포트의 W(이동)·E(회전)·R(크기) 도구로 조정한다. NiagaraComponent0 아래 Life Cycle section을 움직여 재생 시작·종료 시점을 정한다.

Content Browser에서 Niagara System 하나를 선택하고 Tools → Khazan VFX → 선택한 Niagara를 현재 시퀀스에 추가로 새 효과를 더할 수 있다. 다른 공격은 공격 AnimSequence 하나를 선택해 선택한 공격 애니메이션 VFX 열기를 사용한다. 둘 이상 몽타주가 참조하면 해당 Montage도 함께 선택한다. WeakAttack02 외의 새 편집 시퀀스는 현행 Notify의 정적 배치를 시작점으로 사용하므로 기존 무기 추적 효과를 바꾸기 전에 궤도와 결과를 확인한다.

편집을 실제 공격에 반영하려면 시퀀서 상단 공격에 적용 또는 Tools 메뉴의 현재 시퀀서를 공격에 적용을 누른다. 이 명령이 시퀀서 평가 결과를 메인 공격 몽타주의 위치·회전·크기 곡선과 Life Cycle에 저장한다. WeakAttack02 기본 시퀀서는 Main에 적용됐으며 검증용 임시 위치·크기 변경은 포함되지 않았다. 시퀀서는 Player 애니메이션과 선택 Niagara를 보여주며 기존 Cascade·데칼 같은 다른 효과는 실제 공격에서 계속 재생된다.

자동 에디터 캡처에서는 Player 애니메이션과 Niagara 선택 기즈모, 컴포넌트 활성화·재생 나이를 확인했으나 Slash 입자 형상을 뚜렷하게 식별하지 못했다. 대화형 에디터에서 Niagara 컴파일 완료 후 Life Cycle 구간을 직접 재생하며 형상이 보이는지 확인하는 검증이 남아 있다. 실제 공격에서는 편집 곡선을 읽고 Niagara를 활성화하는 것까지 fresh PIE로 확인했다.


<!-- CombatVFXSequencer_20261013_VisualResolved -->
## 2026-10-13 18:31 KST — Slash를 보면서 위치 조정 확인

앞 절의 미리보기 형상 미확인 기록은 이후 에디터 전용 시뮬레이션 갱신으로 해결됐다. 시퀀서 재생 화면 EditorAutoVisual18/PlayingPreview.png에서 붉은 Slash를 확인했다. 정지 프레임에서도 EditorScrubVisual19/Before.png와 After.png처럼 Additive Transform을 움직이면 Slash가 그 자리에서 다시 보인다. 시험 이동 50cm는 메인 에셋에 저장되지 않았다. 사용자는 WeakAttack02 VFX 열기 → Life Cycle 안의 프레임 선택 → VFX Additive Transform 키 조정 → 화면 확인 → 공격에 적용 순서로 작업한다. 공유 KZ_Slash와 기존 다른 공격 효과는 그대로 둔다.

<!-- CombatVFXSequencer_20261013_FinalPreviewVerification -->
## 2026-10-13 18:40 KST 최종 정지 프레임 화면 확인

최종 편집 도구로 다시 연 시퀀서에서 붉은 Slash가 보였고, 저장하지 않은 위치 조정에 즉시 따라 움직였다. 화면 증거는 Metadata/CombatVFXSequencer_20261013/EditorScrubFinal20/Before.png 및 After.png다. 시험 이동 50cm는 공격 에셋에 저장되지 않았다. 에디터 재시작 후 Tools → Khazan VFX → WeakAttack02 VFX 열기에서 위치·각도·크기·Life Cycle을 조정하고 화면을 확인한 다음 공격에 적용한다.


## 2026-10-14 — 플레이어 KZ_Slash 전 공격 배치 검수 및 바깥쪽 확대

현재 게임 공격에서 KZ_Slash를 참조하는 다섯 몽타주(Weak/Strong/StrongCharge/DodgeAttack/SpinningAttack)의 추가 효과 33 start/end쌍을 모두 조사했다. 실제 공격 몽타주, 무기 좌·우 tip 이동, 3시점의 초·중·후 프레임을 대조했다. 첫 프레임 좌·우 자동 선택이 차지와 동시 양손 효과에서 잘못 결속되던 구간은 공격별 실제 움직임과 원래 child 배치를 확인해 명시적 무기로 지정했다. 같은 프레임의 두 효과는 각기 해당 무기로 분리했다. WeakAttack01의 기존 오른손 교정은 유지했다.

추가 효과 32쌍의 무기 바깥 거리와 XY 크기를 공격별로 조정했다. 최종 거리는 25–100cm, 평면 크기는 1.12–1.25배다. 이 수치는 **원작 메타데이터 값이 아닌 이번 시각 검수의 TEMP 튜닝값**이며 각 Notify의 `WeaponSlashOutwardOffsetCm`/`Scale3D`에 보관한다. 거리 방향은 매 프레임 캐릭터에서 실제 무기 끝으로 향하는 지면 평면 방향이다. 회전은 여전히 실제 무기의 스윙 접선과 칼날 방향을 따른다. 기존 WeakAttack02의 사용자 편집 가능 Sequencer 곡선 한 쌍은 실제 프레임에서 검토하고 그대로 보존했다. 공유 KZ_Slash/재질/메시는 이번 작업에서 수정하지 않았다.

격리본에서 추가 효과 단독 99장과 원래 효과 합성 99장, 메인에서 공격 재생 288장을 캡처했다. 합성 검수에서는 차지·약공격·회피·스핀의 붉은 Slash가 무기 밖으로 드러나면서 원래 흰색/회색 효과와 함께 재생됐다. 다섯 저장 몽타주를 새 프로세스에서 다시 읽어 추가 33쌍, 원래 효과 객체 882개 내용, Notify 시간·GUID 보존을 확인했다. 전체 배치와 공격별 수치·캡처·저장 해시는 `Metadata/PlayerSlashOuter_20261014/FinalVerification.json`, 대표 비교는 `Candidate3OnlyRHI01/PairSheet_*.jpg`와 `Candidate3ComposedRHI01/PairSheet_*.jpg`다. 원작 게임의 동일 시점 영상과 픽셀/셰이더 완전 일치는 이번 검증이 아니다.


## 2026-10-15 — SpinningAttack의 KZ_Slash 제외 완료

사용자 최신 지시로 Spinning의 여섯 추가 KZ_Slash 쌍을 OverFury 전용 사본6쌍으로 교체하고 Charge streak3/vortex2쌍을 더했다. 원래176 효과/Notify clock·GUID·공격/오디오와 다른 montage는 유지한다. 이전 다섯 montage 바깥 배치 절의 Spinning Niagara 연결만 이 최신 데이터로 대체된다. 원작 Spin window 재사용과 TEMP donor 조합/scale의 구분, Helix2 회색 면 제외와 실제 HeinMach 자연 재생·cleanup·충돌 및 Main DevMap2 suite Success는 HEINMACH_BLUE_SPINNING_20261015.md 및 Metadata/HeinMachLookSpin_20261015/FinalVerification.json을 따른다. 공유 KZ_Slash/OverFury PS는 수정하지 않았다.


HeinMach broad suite의 이후 rear-Brutal fixture 실패는 보존했으며 전체 HeinMach suite 성공으로 기록하지 않는다.

<!-- HeinMachLookSpin_20261015_complete -->
