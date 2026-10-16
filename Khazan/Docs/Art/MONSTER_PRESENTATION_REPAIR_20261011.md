# Monster 표현·Combat UI 원본 재검사 — 2026-10-11

사용자 직접 수정 요청은 몬스터6종의 공격 위치/방향 전부 재검사, 바닥 혈흔 데칼 제거, 실제 피격의 다량 검붉은 분사, 사망 후 검은 재/dissolve 소멸, 가슴 socket의 LockOn/B 및 원작에 가까운 HP/Stamina alpha/layout이다. 기존 imported source와 저장 report부터 표적 확인한다. 이전 표본 검증을 이번 전체 품질 합격으로 사용하지 않는다.

출발 자료는 MonsterVFX PreparedPlaybackPlan의 Attack198 asset/1577 occurrence, MonsterVFX 원본 manifest·native resource audit 및 CombatUI SourceWidgets01/SourceResources01/Textures01이다. W_Hp_Monster/W_Stamina CurBar의 Background alpha는0이며 별도 BG가 MI_UI_TriGrad_Overhead_Stamina를 소비한다. 현재 Source의 opaque crimson bar background는 이 원본 계약과 다르다. 수치·원본 field/출처·새 임시 표현은 후속 실제 결과에 분리 기록한다.

현재 단계는 조사/수정 착수이고 Main 새 적용·RHI 품질 검증 전이다. Runtime 책임과 exact resume는 [Engineering continuity](../Engineering/ENGINEERING_WORK_CONTINUITY.md)의 ARCH-88 절 및 Metadata/MonsterPresentationRepair_20261011을 따른다. 기존 raw animation/원작 추출을 전체 다시 생성하지 않는다.

## 2026-10-12 — ARCH-88 실제 Main 적용·수치 출처

Source10/asset59는 MainDelivery/Receipt.json과 Before byte backup으로 Main에 반영했다. 이 절 이전의 착수·실패 기록은 보존한다. 새 gameplay runtime 파일0이며 원본 재추출·raw animation 재임포트·전체 project 복사는 하지 않았다. 동시 사운드 작업24 animation/67 notify의 GUID·시간·전체 field를 AudioCensusMainBefore01와 AudioCensusMainAfter01에서 동일하게 확인했다.

공격 위치·방향은 기존 typed SourceSocket/RelativeLocation/RelativeRotation/Scale3D/attach/absolute rotation/window/resource를 유지한다. 실제 spawn을 현재 pose의 bone-finalize 뒤로 옮겨 이전 프레임의 socket을 사용하던 문제를 수정했다. SavedAudit01(Main)와 MainRuntime01은 Attack198/1577 전부 통과했고 deterministic non-floor1483건의 최대 위치 오차3.46e-13cm/회전 오차4.83e-6도는 원작 typed field에 따른 엔진 변환과의 비교다. 원작 실행 파일/게임 화면과의 오차라고 표현하지 않는다. Halberd CorrectionInfos52의 TM에는 bone 식별자가 없고 현재 bone/time/yaw 후보와 정확히 대응하지 않았다. 이를 Root 보정으로 임의 활성화하지 않았으며 원작 native correction/pixel/frame 일치는 미확인이다.

floor blood는 source xxAnimNotifyState_Decal42개의 Effect를 None으로 하고, shared blood PS16개의 실제 FM_MeshDecal/FS_Blood_box receiver만 제거했다. 다른 slash mesh/물리 파편은 보존했다. 새 FP_Monster_HitBlood는 /Game/_Art/Effects/Combat/Blood/PP_Dmg_Blood_Trail_Sub의 실제 Base_DefaltParticle_Masked sprite를 사용한다. 원래 velocity/gravity/collision/texture는 유지하고 mesh-decal receiver를 제거했다. FP_Monster_DeathAsh는 /Game/_Art/Effects/Monsters/Human/FP_DeathEffect라는 기존 원작 추출 기반 native adapter의 sprite를 재사용한다. 원작 cooked executable을 복원한 신규 shader가 아니다.

| 적용 대상·field | 값·단위·조건 | 출처 상태·이유·조정 기준 |
|---|---|---|
| HitBlood Spawn.BurstList Count/CountLow, Rate |192개/명중1회, Time0초, Rate0/초, loop1|TEMP 어시스턴트: 사용자 요청의 다량 분사. 실제 accepted/dedup hit마다1 burst이며 지속 누출을 막음. 화면 밀도와 연타 비용으로 조정|
| HitBlood ColorOverLife/AlphaOverLife |linear RGB(.19,.0025,.008), alpha1|TEMP: 검붉은 피와 명확한 실입자. 원작 색 수치라고 표현하지 않음|
| HitBlood Lifetime/StartSize |1.2초, uniform1.4–3.5cm|TEMP: 분사 후 유한 drain·물리 방울. 바닥 receiver/decal은 생성하지 않음. 근거리 가독성/수명 비용으로 조정|
| DeathAsh Spawn/Required |sprite emitter마다 burst24개+rate12/초, duration3초, loop1; actual body anchors7곳|TEMP: 머리/가슴/골반/손/종아리의 실제 pose에서 재를 분산. 원작 lifetime/alpha/texture는 보존|
| DeathAsh Color/Velocity/Size |linear(.003,.003,.003); world X/Y[-60,60], Z[50,100]cm/초; uniform2–4.5cm|TEMP: 검은 재가 위로 흩어지도록 분산. 화면 밀도·이동 방향·비용으로 조정|
| Monster.DeathDissolveSeconds |3초; HP0인 normal/paired death 완료 뒤 시작|TEMP: 사망 동작은 끝까지 재생하고 corpse가 소멸하는 표시 시간. Monster Class Defaults에서 조정|
| corpse9 masters KZDeathProgress/KZDeathEdgeWidth/KZDeathNoiseTiling |baseline0, edge.08(normalized), UV multiplier6|progress0은 생존 원본 보존. edge/tiling은 TEMP 부드러운 소멸·큰 덩어리 억제. texture /Game/_Art/Effects/Shared/Textures/BBQ_Texture/Noise/FT_Noise_Dissolve와 Linear Grayscale 유지|
| corpse BaseColor char |linear(.002,.002,.002), weight clamp(progress×3)|TEMP 검게 타는 표현. 원본 BaseColor RGB 및 original opacity A를 보존한 graph 확장. 수학적0/1 clamp와 tuning3을 구분|
| UI_Chest socket |Bip001-Spine2, local identity/offset0; skeleton5개를 monster6종이 사용|현행 실제 bone 확인. 뼈 좌표를 그대로 쓰는 부착 설정이며 가슴 임의 world Z offset이 아님|
| EliteFrameSize/opacity |124×22 logical px / .8|크기는 TEMP 사용자 요청의 축소. 원작 W_OverheadGauge180×32/opacity.8에서 크기만 줄임|
| empty Gauge TrackColor |linear(.015,.015,.015)|TEMP: HP와 empty track를 구분하는 검정 계열. alpha는 아래 원작 gradient 값 사용|

원작 UI 출처는 Metadata/CombatUI_20261011/SourceWidgets01/BBQ/Content/_Kazan_/UserInterface/UIWidget/GameHud/StatusGauge/W_Hp_Monster.json의 CurBar.WidgetStyle.BackgroundImage.TintColor.SpecifiedColor.A=0 및 ProgressBar_Recover.WidgetStyle.FillImage.TintColor.SpecifiedColor RGBA(.947307,.061246,.072272,.65098)다. 원작 Recover tint를 프로젝트의 감소 잔상에 재사용했으며 native 원작 보간 동작을 확인한 것은 아니다. Current HP/ST는 ASC 실제 값으로 즉시 갱신한다. .35초 감소 잔상·ST 잔상alpha.35는 프로젝트 TEMP이며 원작 InterpolationTimeMultiply=.35를 초 단위로 복원했다고 설명하지 않는다.

원작 MI_UI_TriGrad_Overhead_Stamina의 직접 원시 값은 Metadata/CombatUI_20261011/SourceResources01/BBQ/Content/_Kazan_/UserInterface/UITexture/Material/Simple_Gradient/Instance/MI_UI_TriGrad_Overhead_Stamina.json의 ScalarParameterValues.MidColorRange=.8, VectorParameterValues.GradientColor1/2/3.A=.35/.2/.1이다. M_UI_GaugeBackground의 Mid/A1/A2/A3로 옮겼다. gradient 보간 식/UV 방향은 native stripped graph를 복원하지 못한 명시적 adapter다. CurBar Background는 NoDraw이며 별도 empty track가 alpha를 소유한다. 기존 B A-only/feather1.25 material은 SHA c4d6ff… 그대로 보존했다.

MainUI02는 실제 HalberdElite를 선택해 정상 록온·피해/회복 즉시 반응·B 가슴 부착·실제 CanActivate/paired input·lethal0·Max0·UnPossess/RePossess를 통과했다. 02_DamagedGauges/03_ActualLockOn/04_BrutalAvailable_B를 직접 검사했다. 다른 몬스터가 시야를 가렸던 MainUI01은 검사 전용 배치를 수정했으며 제품의 occlusion 규칙을 약화하지 않았다. 최종 전수 공격 화면은 MainRuntime02에서 원본/런타임 동명 파일이 덮어써지지 않도록 case index를 붙이고 posed pelvis/head 중심으로 카메라를 맞춰 확인 중이다. 완료 receipt/검증 종료는 아래 후속 절에 추가한다.

## 2026-10-12 01:01 KST — Main 표시 수정·검증 종료

FinalVerification.json status는 MainDeliveredAndFreshVerified다. 실제 Main Source10/asset59와 최종 해시·백업·각 실제 loaded DLL을 결속했다. MainRuntime02의198/1577 및6종 normal/paired death/live blood/live ash/MID progress/Destroy, actual accepted-hit13 case, HalberdElite actual UI2가 Success/fallback0/Exit0이다. attack PNG192개/contact sheet8장, blood/ash/late death18장, UI02 damage/normal ring/B 화면을 직접 검사했다.6 component 없는 clip도 native/saved 검사에 포함했다. 원본/런타임 동명 파일 덮어쓰기와 raw root-travel QA 카메라는 검사 코드에서만 보완했다.

최신 MainSavedAudit02 save0은 혈흔 producer42의 Effect None, source geometry198/1577, chest6/skeleton5, corpse master9/P0/tiling6/Linear Grayscale/UI gradient를 확인했다. 동시 사운드24 animation의67 audio Notify는 후속 작업으로 GUID가 재생성됐지만 MainAfter02의 나머지 event field·timing·playback·sound/stop 값은 동일하다. 최신 파일을 보존했고 우리의 바닥 혈흔 제거/사망·UI 계약도 유지했다. 모든 관련 TEMP 숫자는 바로 위 표의 출처 상태를 유지한다.

이번 요청의 구현·Main 검증 필수 잔여는 없다. 재개 근거는 이 정본 마지막 절/Engineering ARCH-88 완료 절/FinalVerification.json이며 완료된 전체 author/import/private copy/alias 복원을 반복하지 않는다. source shader/native correction52의 완전 복원 및 원작 pixel/frame parity·Shipping 성능은 미확인으로 구분한다.


## 2026-10-12 — 첨부 사진 기준 혈액·바닥 혈흔 후속 착수

최신 사용자 요청은 큰 검붉은 분사와 넓고 불규칙한 바닥 혈흔이며 이전 바닥 혈흔 제거 지시를 이 후속 표현에 한해 대체한다. 첨부는 Metadata/MonsterBloodReference_20261012/Reference.png로 byte 보존한다. 관찰: 작은 점만 아니라 뭉친 혈액/찢어진 sheet/주변 방울, 지면의 긴 번짐·가느다란 가지·불규칙한 빈 경계가 함께 보인다. 원본 FT_Decal_Blood_* packed texture 및 현재 blood resources를 표적 조사하고 공용 원본/기존 사망·UI를 일괄 덮어쓰지 않는다. burst/크기/지속 시간은 screenshot에서 원작 숫자를 직접 확인할 수 없으므로 명시한 TEMP asset/default 설정으로 조정한다. 구현/검증 결과는 하단에 추가한다.


## 2026-10-12T04:22:44+09:00 — 사진 혈액 후속 Main 완료 / 원작 근거·TEMP 정본

사진의 검붉은 큰 덩어리·찢어진 액체막·미세 방울과 넓은 불규칙 바닥 혈흔을 Main의 FP_Monster_HitBloodReference로 구현했다. 기존 FP_Monster_HitBlood의 byte는 그대로 보존했다. 유효 신규 package는 Ref PS, M_Monster_HitBloodFluid/FT_Monster_HitBloodFluid, M_Monster_HitBloodGround/FT_Monster_HitBloodGroundMask의5개다. 초기 Sheet/SheetMask2개는 MainSaved04 무참조 확인·SHA 보호 뒤 RetiredTrials로 옮겼다. 사망 ash/dissolve·UI·audio·원본 texture·map·lighting을 덮어쓰지 않았다.

원작 resource 출처는 Content/_Art/Effects/Metadata/Extraction_20261006/AssetManifest.json의 PP_Dmg_Blood_Trail_Sub, FT_Subuv_Fluid_001, FT_Decal_Blood_A_003 행이다. 각각 Saved/Extracted/CombatEffects_20261006/Source/BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/Physics/PP_Damage/PP_Dmg_Blood_Trail_Sub.json, VFX_Texture/SubUV/FT_Subuv_Fluid_001.json, VFX_Texture/BBQ_Texture/Decal/FT_Decal_Blood_A_003.json을 근거로 한다(마지막2는 위 Art/VFX prefix 상대 경로). source Texture Properties.SRGB=false와 native packed RGB는 own copy에 적용했다. ground 원본은1024×2048/RGB3 혈흔 모양이며 alpha 전체를 마스크로 쓰면 사각형이 된다. fluid의1024×1024 export는4×4=16 frame으로 관찰·계산했다. solid green background와 opaque A를 제외한 max(R,B)를 opacity에 사용한다. 이는 새 adapter이며 stripped 원작 shader를 복원했다고 표현하지 않는다.

| 현행 설정/field | 값·단위·조건 | 출처·이유·조정 기준 |
|---|---|---|
| PS droplet Burst/Size/Lifetime |384개, uniform .8–2.2cm,1.2초|TEMP 사진의 다량 미세 분사/유한 drain. 실제 연타 밀도·비용으로 조정. original gravity/collision/cylinder/size-by-speed 재사용|
| PS sheet / chunk Burst/Size/Lifetime |8개/55–100cm/.65초,24개/12–26cm/1초|TEMP 큰 액체막과 덩어리를 분리. sprite3층의 Required/Spawn/LOD/Modules를 독립 복사하고 alpha curve를 소유. 폐기된 Author03의 공유 module 오류를 완료로 읽지 않음|
| PS local velocity fan |droplet min(60,-220,80) max(400,220,450); sheet/chunk min(60,-130,80) max(220,130,260), cm/초|TEMP 표면 바깥 축의 분사·상향/측면 확산. 근거리 가독성과 궤적으로 조정|
| sheet/chunk start location |min(-12,-22,-10), max(12,22,25)cm|TEMP 좁은 발생 부피에서 큰 sheet가 겹쳐 튀도록 함. 장방형 배경 없이 분사해야 함|
| ColorOverLife / AlphaOverLife |linear(.12,.001,.003); normalized age (0,1),(.6,1),(1,0)|TEMP 방울 색과 마지막40% fade. 원작 timing이라고 표현하지 않음|
| Required/Spawn/draw |Rate0, BurstTime0, loop1, delay0, draw limit false, dynamic bounds|유한 accepted-hit1회 burst 계약. 원본 max_draw_count 존재와 원본 cap enabled 여부를 혼동하지 않음. SetupSoloing 이후 save/readback으로3 enabled 확인|
| Fluid UV/mask |floor(saturate(age)×15),4×4 atlas; max(R,B), power .45/density2.5|grid/15는 export 기반 계산(16-1), power/density는 TEMP 두꺼운 액체. G/A를 배경 alpha로 쓰지 않음|
| Fluid BloodColor / shading |linear(.12,.004,.009), EyeAdaptationInverse full conversion, per-pixel lerp(.3,1.8, B×.75+R×.25), Unlit translucent|모든 숫자는 TEMP 사진 비교. 가까운 횃불의 강한 붉은/흰 정반사와 sheet 과노출을 억제하고 검붉은 색·내부 농도 변화 유지. 조명은 그대로다. 예전 rough .14→.28/spec .1/metal .25 노드는 보존하나 현행 Unlit에서 비활성; MetalPower .25 원작 raw를 실제 Metallic 복원으로 주장하지 않음|
| Ground BloodColor/mask |linear(.012,.00025,.00075), power .4/density6, RGB channel uniqueID%3|색/power/density는 TEMP 검붉은 번짐과 실루엣.3은 원본 RGB 마스크 수. gameplay RNG를 소비하지 않는다. roughness/metallic 출력 미연결로 opaque plate 억제|
| Monster projector / trace |half extents(8,95,150)cm,600cm downward trace|TEMP 사진 대비 약190×300cm 번짐과 얇은 지면 투영. 지면 밖/벽/공중 생성은 reject; Snow 높이·rim은 기존 owner 값으로 계산하여 추가|
| Ground hold/fade |24초 유지+3초 fade; DecalLifetimeOpacity|TEMP 전투 중 바닥 혈흔 유지·유한 비용. victim 사망 뒤 유지하고 engine component timer가 destroy|

수치 출처는 사용자 결정이 아닌 어시스턴트의 사진 비교 TEMP이며 원작 package 숫자와 구분한다. 원작처럼 보이는지는 조명·camera·motion에 영향을 받는다. saved probe의 size_sample0는 난수 sample이므로 min/max 증거로 쓰지 않고 private author의 uniform 범위와 package SHA를 같이 기록했다.

최종 MainSaved11 save0/CDO6/gamma/sampler/Unlit+Emissive, MainSnowVisual11 강제 QA warm 없는 실제6종24혈액/12소멸·surface direction/ground lifetime와 MainActualHits04 실제13 collision이 통과했다.24개를 contact sheet와 첫 프레임/giant/대표 원본 크기 화면으로 검토했다. QA shadow pool256은 own process만의 memory 설정이며 제품 config를 수정하지 않았다. 기존 Snow 변형의 움푹 파인 지면도 보존한다. exact pixel/frame·stripped shader native 복원·Shipping 성능 검증은 별도다. Source4/package5/loaded DLL/SHA/대표 화면·검증과 재개는 Metadata/MonsterBloodReference_20261012/FinalVerification.json, ResumeState03.json이다. 초기 pending checkpoint/실패 화면을 최신 상태로 사용하거나 전체 author/delivery를 다시 실행하지 않는다.


최종 추가 보정: MainSnowVisual09는 Unlit만으로 야외 노출에서 검정 덩어리로 묻히고 깊은 Snowpit의 옆면에 혈흔이 늘어져 보여 최종 시각 통과로 사용하지 않았다. SurfaceFinish02는 Fluid BloodColor를 사진 기반 TEMP linear(.12,.004,.009)로 바꾸고 UE EyeAdaptationInverse를 Emissive 앞에 연결했다. full conversion의 기본 Alpha1은 엔진 값이지 원작 gameplay 또는 새 튜닝 수치가 아니다. 노출 역변환으로 가까운 횃불/밝은 눈에서 검붉은색과 atlas 내부 농도 변화가 함께 유지된다. Ground는 rendered-depth WorldPosition의 ddx/ddy 외적 normal과 producer가 기록한 기존 CMC WalkableFloorZ로 수직 옆면을 제외한다. 새 slope 임계값과 Snow geometry 수정은 없다.

엔진 기술 근거는 설치 UE5.8 Engine/Source/Runtime/Engine/Public/Materials/MaterialExpressionEyeAdaptationInverse.h, Private/Materials/MaterialExpressions.cpp의 기본 LightValue/Alpha1, Private/Materials/HLSLMaterialTranslator.cpp의 EyeAdaptationInverse, Engine/Shaders/Private/DeferredDecal.usf의 scene-depth에서 만든 AbsoluteWorldPosition이다. [Epic EyeAdaptationInverse API](https://dev.epicgames.com/documentation/unreal-engine/API/Runtime/Engine/Materials/UMaterialExpressionEyeAdaptation-?application_version=5.5)는 기능 참조이며 원작 수치의 출처가 아니다. MainSnowVisual10은 잘못 지정한 QA 맵 경로로 중단했고 실제 저장된 /Game/Maps/L_HeinMach_Environment에서 수행한11만 최종 증거로 쓴다. 기존 Snowpit과 source RGB 혈흔의 서로 다른 silhouette은 보존한다.


## 2026-10-12T11:04:18+09:00 — 사용 애니메이션 Root88 / VFX basis·scale Main 완료
현재 사용395개/body392+prop3에 대해 Root 옵션/track을 확인하고 native first/mid/end1176포즈를 검사했다. Animation88의 first-frame 누적 origin을 RefPose lock으로 정렬했다. Root raw channels, 전체 model·notify392 SHA, 모든 timing/Root enable/force/normalized scale 및 original resources는 보존됐다. exact imports 기준 수치는 RootLockPlan.json의 first-root/skeleton reference 필드이며 신규 원작 튜닝값이 아니다. actor 좌표의 root-stripped source collision에 live body scale을 한 번 반영, socket 없는FX는actor orientation+mesh origin/offset·size body scale 적용. VFX198/1577 및 death6는 delivered Source와 동일한 private RHI Success이고 Main current canonical/freshRoot·HP30·Player16·saved 원본 유지가 Success다. active correction-curve rows0 / 원작 native·pixel parity·전체두레벨·network는 완료 검증으로 표현하지 않는다. Metadata/MonsterRootCollisionRepair_20261012/FinalVerification.json 및 ResumeState03.json, MainBefore/RootAssetsBefore 백업을 따른다.


## 2026-10-12T13:12:55+09:00 — 사망·브루탈·공격/회피/착지 효과 Main 후속

기존 PP_Player_Parry_Success(원본 JustGuard13 emitter의 로컬 alpha 복원), PP_AtkEx_Grapple_01/02와 original world smash_weak surface variants를 재사용했다. 새 particle/material/texture asset0. 원작 출처는 Metadata/Parry_20261012/OriginalEvidence.json, Content/_Art/Effects/Metadata/Extraction_20261006/AssetManifest.json, Saved/ImportReports/PlayerAttackVFX_20261008/CombinedPlaybackWindows.csv 및 기존 Player VFX playback 정본이다. gameplay source field/공격 피해/모션 데이터/오디오는 그대로다.

montage8에 추가된55 window는 공격44(파랑+보라/검붉은 accent), 방향별 회피8, 착지3이다. 기존 trigger/입력 event GUID/field·section/segment 보존을 저작 시 확인하고 SavedAudit02에서55 start/end pair·template·scale·수명을 재조회했다. 루프를 방치하지 않고 notify end에서 deactivate하여 잔여 입자를 drain한다. 기존 Spin 강한 내려찍기2 marker의 dust/snow/grass strong variant는 weak variant로 바꿔 바닥으로 낮게 퍼지게 했고 실제 weapon-tip/walkable normal 기준을 적용했다. 착지 먼지는 벽에 들어간 칼끝의 실패를 피하려고 실제 grounded actor 발밑으로 보정했으며 collider/gameplay 위치는 바꾸지 않았다.

새 수치는 모두 어시스턴트 TEMP 표시값이다: attack blue scale0.35(가벼운 공격)/0.5(강한 공격), accent0.25/0.35, dodge0.25, plunge blue0.5/purple0.4/ground1, Spin ground0.8. Notify Scale3D에서 조정한다. 착지 start는 기존 Land section entry+UE endpoint epsilon0.0001초이고 window0.121175006초는 저장 source damage window 길이를 사용한 표시 adapter이며 새 gameplay duration이 아니다. weapon-tip100cm는 기존 blood source RelativeLocation.Z=100에서 가져온 cm 값이고 원작 floor native writer를 복원했다고 표현하지 않는다. 효과 기호의 파랑/보라/검붉은 인상은 현재 복원 parent·조명에 따른다.

혈흔 TEMP는 Monster Class Defaults: main 기존8/95/150cm half extents, satellite6(technical presentation cap16), radius90–280cm, size factor0.35–0.65, 기존24초 hold+3초 fade 유지다. 전체 방위로 점과 불규칙한 큰 얼룩을 함께 펼친다. shape/RGB 마스크·검붉은 분사·source ash와 dissolve3초는 이전 사진 혈액 구현을 재사용한다. 정상/짝 사망의 source 끝 포즈 수리와 실제6종7장/4방위 검사는 Engineering 최신 절을 따른다.

실제 게임 viewport 캡처와 source/hash/원본 보호는 Metadata/CombatFinishFollowup_20261012/PresentationFinal02·FinalVerification.json, 추가 ground 보정은 PlungeAnchor01/Applied.json에 있다. 대표 실제 화면을 별도 검토하며 editor screenshot/이전 실패를 시각 합격으로 쓰지 않는다. 전체 native shader/pixel parity·Shipping stress를 주장하지 않는다.


## 2026-10-12T21:06:38.746735+09:00 — ARCH-95 최신 추가 Slash·타격 표현 Main 완료

몬스터의 지정 Slash/Sting 참조는0으로 복구했고 기존 player effect100 객체를 보존한 채 KZ_Slash 별도 child100을 추가했다. Shader/색·source 원래 효과를 제거하거나 대신 재생하지 않는다. reference bones FX_L_Axe_01/02 및 FX_R_Sword_01/02의 geometry를 실제 Weapon_L/R grip에 연결한다. WeaponSlashProbe04의 reference measured offsets와 SM_VFX_SlashRing_01 bounds[-100,-100,-20]..[0,100,20]cm, Meshes[0].Rotation.Yaw180deg에서 span200/centre 보정을 계산했다. 이 숫자는 요청 Fab/current imported asset의 좌표계 변환이며 원작 gameplay 튜닝값이 아니다. shared KZ_Slash/KZ_SwordsMan_Sting asset은 수정하지 않았고 component만 독립 회전·크기 곡선을 중립화한다.

기존 원작 spark adapter를 CPU finite120(40×3)방사형 불꽃으로 재사용했다. TEMP는 life.18–.38s/speed1000–1800cm_s/width2–4cm/length16–30cm 및 blue(.04,.28,3)/purple(1.4,.025,2.4)/red(2,.012,.035) linear HDR와 alpha(0,.95),(.55,.7),(1,0)이다. 실제 수치 조정은 소유 PS의 module/curve에서 한다. 기존 혈액3 emitter와32 root blocks 및 nested data를 보존하며 승인 hit·parry·player received hit에서만 이 burst를 소비한다. cancelled PP/M_Monster_HitFlameFlash 두 asset은 Content에서 제거하고 metadata backup을 보존했다. 추가54 unconditional colour windows는 복원하지 않았다. 기존 ground scatter·dissolve/ash·SlamDistort alpha는 보존한다.

실제 BurstVisual05의120입자/얇은 radial streak 및 중간 contact, natural player original+additional/added-only4 frames, actual monster hit/received-hit 화면을 검수했다. 최초 GPU와 fluid material의 가시성 실패, old raw size lookup cache, camera API 오류는 실패로 보존한다. AdditiveSaved02·ExactBeforeAudit01(220×21 차이0)·FinalVerification이 최신 정본이다. 앞선 replacement author/delivery와 resource 전체 추출/Root/FPS author를 반복하지 않는다.

## 2026-10-15 — 사망 시 큰 흰 바닥 원판: 재질 복원 오류 8개 제거

SavedAudit.json의 사망 에셋 18개에는 현재 바닥 데칼 9개가 남아 있었다. 이 중 8개는 Shared/Materials/MonsterHuman/FMI_Decal_Deferred_D_02 또는 MI_Decal_Deferred_D_00다. 전자의 parent FM_Decal_Deferred_D와 후자의 M_New_Decal_Deferred_D에서 BaseColor와 EmissiveColor가 같은 MaterialExpressionComponentMask_0 RGB로 연결되어 있고 ShadingModel=MSM_Unlit이다. 흰 mask RGB가 발광으로 표시되어 큰 흰 원판으로 보인다. 원작 cooked shader topology와 동일성이 확인된 재질이 아니다. 원작에 흰 원판 연출이 있다는 근거로 취급하지 않는다.

Metadata/MonsterDeathWhiteDisc_20261015/Base_01_FM_Decal_Deferred_D.t3d의 MaterialEditorOnlyData.BaseColor/EmissiveColor(91~92행), Base_02_M_New_Decal_Deferred_D.t3d의 동일 field(95~96행)가 현행 graph 근거다. SavedAudit/IsolationRHI01은 현행 Yetuga projector DecalSize=(50,800,800)cm, Apes=(50,350,350)cm, Heavy와 일부 검병=(50,150,150)cm, 검병 뒤쪽 Wraith=(50,250,250)cm를 확인했다. 이 숫자는 현재 저장 에셋/런타임 값이며 원작 shader 재현 검증값이나 새 튜닝값으로 승격하지 않는다.

IsolationRHI01은 같은 정지 프레임에서 해당 DecalComponent 하나만 숨긴 Before/After 9쌍이다. 00=Yetuga, 01~02=Heavy, 04~07=검병 변형, 08=Apes의 흰 원판이 그 비교에서 사라진다. 03의 PD_Dirt_SuperRound_MonsterCurve_7b611d5a는 Emissive constant0의 정상 흙 자국이며 보존한다. Main 사망 시퀀스 8개에서 문제 Effect.DecalMaterial만 None으로 저장했고 공유 재질 자체나 다른 공격/패링 경로를 전역 수정하지 않았다. 전체 변경 EventId/패키지는 Engineering MONSTER_VFX_RUNTIME_20261008.md 같은 날짜 표와 Authoring.json에 있다.

수정 전 package Backup/Content와 Before/Edited/After 전체 T3D를 보존했다. Authoring.json은 포인터 이외 모든 export/Notify/애니메이션 데이터 보존을 확인했다. 혈흔, 검은 DeathAsh, dissolve, 사망 모션은 유지 대상이다. AfterRHI01의 fresh main 재생 18개와 기존 혈흔/사망 6종 회귀는 진행 중이며 완료 결과를 뒤에 추가한다. 새 시각 수치·재질·runtime 구조는 추가하지 않았다.

## 2026-10-15 — 사망 흰 원판 제거 Main 시각 검증 완료

위 진행 중 기록의 사망 데칼 수정은 완료했다. AfterRHI01의 새 main D3D12 재생 18개는 Success이며 문제 흰 데칼 생성0, 정상 dirt mark1은 유지됐다. Yetuga의 원판 재생 시점 이후 화면, Heavy/검병 Wraith/Apes 화면에서 원판 소실을 확인했다. 수정 전후 18개 모두 다른 파티클 peak component 수가 동일하다. PresentationRHI01은 6종의 정상 blood·바닥 혈흔·검은 ash·dissolve와 사망 완료를 기존 native quick regression으로 통과했다. Blood_HeavySwordsman_03/DeathAsh_HeavySwordsman에는 바닥 혈흔과 쓰러진 사체가 유지된다. shader compile/fallback 실패0, 게임 코드/공유 material 수정0, 원작 재현용 임시 수치 추가0이다.

검증 시각은 DevMap task-owned D3D12 PIE로 제한하고 원작 cooked shader 동일성 검증과 구분한다. 최종 에셋 SHA·8 EventId·전후 component 수·6종 live 혈흔/ash·실제 DLL은 Metadata/MonsterDeathWhiteDisc_20261015/FinalVerification.json에 있다. Main에 저장 완료했으며 해당 요청의 남은 작업은 없다. 후속 같은 현상은 이 report와 해당 EventId 자료부터 표적 확인하고 공유 shader 전역 교체나 18개 사망 재author를 먼저 하지 않는다.
