# 2026-10-06 HeinMach 눈 파임 재현

## 착수 상태

사용자 직접 구현 요청이다. Art와 Engineering에 걸친 작업으로 Router, 최신 Art 상태/파이프라인/HeinMach Reference와 저장 지면 report, Engineering 최소 변경 규칙/Architecture/Migration 최신 절 및 실제 KZCharacter/KZMonster/Action Source를 확인했다. 배경 눈보라와 눈 지면 변형을 구분한다. 기존 HeinMach 룩·9,610 actor pose·PlayerStart와 동시 몬스터 작업을 보존한다.

작업본은 `C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan`이다. Source/Config/Binaries/Plugins/Maps/Rendering은 별도 복사본이며 나머지 Content는 읽기 전용 취급 junction이다. 메인 사용자 editor PID27916 및 타 작업 editor를 조작하지 않는다. source/map/config는 실제 검증 후 최신 hash/dirty/다른 작업 완료 상태를 확인해 선택 병합한다. 현재 본 절은 구현 완료 기록이 아니다.

## 원작 표적 근거

- `Saved/Extracted/HeinMachSnow_20261006/Source/BBQ/Content/...` 원시 JSON, `RootRequests.json`/`ClosureRequests.json`, `Saved/ImportReports/HeinMachSnow_20261006/OriginalSnowContracts.json`의 package/file/SHA/field가 출처다. 기존 원작 terrain weightmap/texture/tiling report를 재사용한다.
- `WLM_HeinMach.ScalarParameterValues`: `SnowHeight=15`, `Displacement Multiplier-DeepSnow=15`, `HeightIntensity-DeepSnow=1`, `Tiling-DeepSnow=4`. `WLM_HeinMach2`: `SnowHeight=25`, `Displacement Multiplier-DeepSnow=15`, `Displacement Multiplier-DeepSnow2=7.5`, `Tiling-DeepSnow=5`, `Tiling-DeepSnow2=2`. 이는 원시 shader 계수다. 실행 식과 원작 shader 단위까지 직접 확인한 값은 아니다.
- source root `BaseMaterials/Terrain/Base_Terrain5.bUsedWithVirtualHeightfieldMesh=true`. `BaseMaterials/VT_SnowField/M_WriteSnow`와 `MI_WriteSnowField_Human`, 사람·무기/아이템 writer가 존재한다. `MI_WriteSnowField_Human.Parent=MI_WriteSnowField_02_Main`, additive/unlit, `Intensity=1`, `MasterOpacity=1`, `DetailIntensity=20`, `NoiseTex=FT_SnowPersonDecal_01`. editor graph가 제거된 metadata에서 원작 writer 실행 식을 복원했다고 하지 않는다.
- `WLI_HeinMach_DeepSnow.LayerName=DeepSnow`, `PhysMaterial=PM_DeepSnow`. 원작의 DeepSnow 레이어와 보통 Snow/Ice 레이어를 이름만으로 같은 깊이로 간주하지 않는다.

## 적용 설계 및 수치 상태

기존 weighted terrain graph를 복제해 원래 D/N/S·레이어 가중치·UV·puddle를 유지하고, 눈 높이·압축·완만한 rim·높이 미분 normal·약한 압축 색/roughness를 추가한다. 원작 VHM의 stock UE5.8 대응은 Nanite 동적 변위다. UV/normal이 끊기는 임의 메시 전체를 일괄 tessellate하지 않고 현재 source landscape component를 별도 복제한다. 실제 scalar 변위/scale·seam·normal과 무파임/파임 상태를 RHI에서 검사한다.

Native 해석: DeepSnow 15cm/DeepSnow2 7.5cm는 원시 15/7.5 계수를 cm 높이로 선택한 **원작 계수 기반 native 설정**이다. 원작 실행의 cm 값 직접 확인과 구분한다. 일반 눈 4cm, rim 2.5cm, 압축 darkening .06/roughness +.08, 발 반경 17×9cm, 발 contact reach12cm, 무기5cm, teleport256cm는 **assistant 임시 튜닝값**이며 원작 검증값이 아니다. field 2048²×2cm=4096cm, tile128, cache256은 기술 예산이다. 원작 snow refill 시간은 미확인이므로 자동 복구 시간을 임의로 적용하지 않는다.

눈은 substrate collision 위로 쌓이고 접촉 시 substrate까지 압축한다. 기존 CMC/route collision/NavMesh를 deform height로 재작성하지 않는다. 기존 지면보다 아래로 파여 발이 공중에 뜨는 구성은 최종 전달하지 않는다. 2D field의 altitude gate와 cache 예산 한계는 실제 QA 및 결과 기록에서 공개한다.

## 기술 조사

- [Epic: Working with Nanite-Enabled Content](https://dev.epicgames.com/documentation/unreal-engine/working-with-naniteenabled-content): programmable displacement, normal 별도 필요, object-space magnitude, crack/bounds/성능 제약.
- [Epic: Runtime Virtual Texturing](https://dev.epicgames.com/documentation/en-us/unreal-engine/runtime-virtual-texturing-in-unreal-engine): 대규모 지형 GPU cache의 원리. 원작의 VHM/RVT 참조와 UE5 대응을 구분한다.
- [Epic: Using Nanite with Landscapes](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-nanite-with-landscapes-in-unreal-engine): native landscape와 Nanite build 갱신. 현재 프로젝트는 landscape를 추출한 StaticMesh이므로 stock Landscape 절차를 그대로 적용하지 않는다.
- [공개 공식 15분 gameplay/IGN 배포](https://www.youtube.com/watch?v=F0I4aETElC0): HeinMach 원작 이동·전투 visual 참조. 같은 카메라/버전의 pixel 동일성 검증 완료 자료는 아니다.

## 현재 검증과 재개

`Topology.json`: current scene 9,610 actors, Snow/weighted material 관련 component49, 기존 static landscape의 Nanite=false. null-RHI vertex stat0은 실제 topology 부재 판정으로 쓰지 않는다. `StageSetup.json`이 source/config/선택 Content 시작 SHA 기준이다.

처음 staging Plugins를 junction으로 둔 빌드는 플러그인 DLL write lock에서 실패했다. task-owned UBT만 중단하고 정확한 junction 자체를 제거해 private Plugins copy로 수정했다. 메인 DLL의 파일 잠금은 해제하거나 재로드하지 않았다. 캐시/Intermediate는 제품 Source/Content 변경과 구분한다. 이후 private cold build를 진행 중이다.

남은 절차: cold build → hidden real-RHI authoring/displacement input readback/Nanite mesh build → 새 saved reload → 실제 Player·Monster 이동·Dodge/무기 접촉/공중·ice 억제·tile boundary/반복·cleanup/성능 → 무파임·파임 재질 화면 검수 → 동시 작업 완료/메인 hash·dirty 확인 및 선택 병합/cold build → 메인 reload → 기존 노션 양식으로 실제 결과 작성. 최신 결과는 하단 날짜별 완료/실패 절로 추가한다.

## 2026-10-06 — 격리 저장·셰이더와 접촉 QA 체크포인트

- 격리 authoring 성공: source landscape component 46개를 별도 Nanite mesh로 복제, 기존 weighted graph 2개에 변위/normal/압축 PBR을 추가하고 `HM_SnowDeformation` Actor를 배치했다. `Authoring.json`/`AuthoringPoseDelta.json`: 기존 actor pose 차이0. 아직 메인 전달/PIE 완료가 아니다.
- 두 material 실제 DX12 `ShaderStats.json`: errors0, pixel instructions524/549, Nanite·tessellation=true. 최초 VectorParameter 기본 RGB 출력으로 Transform.w가 범위를 벗어난 오류는 RGBA 연결로 수정했다. MP_Displacement Python enum 미노출은 native editor input helper와 T3D readback으로 해결했다. Nanite 사용 flag는 mesh 할당 후 해당 2material만 다시 저장했다.
- 첫 검증 지점 `(12100,13500)`은 원본 DeepSnow weight255지만 실제 complex Visibility hit가 `StaticMeshActor_3711`의 `SM_WP_CTR_Rock_Collision_004`, Z124.491/normal.Z.987/tag0이었다. 눈 위 바위가 가리는 지점을 사용한 QA fixture 오류다. 바위를 deform surface로 바꾸거나 collision/route 설정을 바꾸지 않았다. `BlockingSurface.json` 및 saved verify 로그를 근거로 노출된 눈만 선택하는 QA fixture를 수정 중이다.
- `debugging-code`를 적용해 격리 PID21560 LLDB attach를 시도했으나 source breakpoint58에 executable code 없음, manual pause stack `<알 수 없음>`으로 심볼 해석이 불가능했다. 이 blocker를 밝힌 뒤 native test hit 값과 isolated asset readback으로 fallback했다. 자기 breakpoint1개 제거/자기 attach session STOP, user breakpoint 상태는 변경하지 않았다. 디버거로 root cause를 직접 확인했다고 하지 않는다.
- 컴파일/author/API 실패를 완료로 해석하지 않는다. 현재 ColdBuild_ExposedSurfaceQA 이후 own verify mailbox → Khazan.Snow.PIE가 다음 단계다. original source shader/HLSL 미확보, contact foot radius·압축 색/roughness 등의 임시 상태는 유지한다. 자동 refill 없음, bounded world tile cache는 기술 제한이다.


## 2026-10-07 — HeinMach 눈 변형 메인 반영·최종 검증 완료

메인 `/Game/Maps/L_HeinMach_Environment`에 눈 변형을 선택 반영했다. 원래 weighted terrain의 텍스처·레이어·UV를 보존한 전용 Nanite 지면 46개와 머테리얼 2개, `HM_SnowDeformation` Actor 1개다. 총 9,869 actors이며 기존 9,868 actor의 transform/PlayerStart와 화로 작업 258 actors를 보존했다. 48 asset/맵의 전달·최종 SHA는 `Saved/ImportReports/HeinMachSnow_20261006/Delivery20261007.json`, 최신 검증은 `FinalVerification20261007.json`이다.

파임은 실제 높이 변위, 압축 field의 미분 normal, 압축 색·roughness로 표현한다. quintic 타원 brush와 완만한 rim, max 누적으로 둥근 경계와 압축 한계를 둔다. 발/발끝, 몸통·팔다리, 실제 부착 장비와 합쳐진 원작 장비 메시의 접촉을 소비한다. 원래 눈/얼음/바위 가중치를 유지하며 공중 무기는 눈에 기록하지 않는다. Nanite와 physics substrate의 약 8cm 오차는 전용 메시 precision12/MaxEdgeLengthFactor2.0 및 recook로 교정했다. 이는 엔진 기술 설정이며 원작 수치가 아니다.

원작 출처는 `OriginalSnowContracts.json`의 package/file/SHA/field와 원시 `Saved/Extracted/HeinMachSnow_20261006/Source`다. WLM_HeinMach의 SnowHeight15/DeepSnow Displacement15, WLM_HeinMach2의 SnowHeight25/DeepSnow15/DeepSnow2 7.5는 원작 shader 계수다. 이 작업의 15cm/7.5cm는 계수를 높이로 해석한 native 설정이며 원작 실행 cm 직접 확인이 아니다. 일반 눈4cm, rim2.5cm, 압축 darkening.06/roughness+.08, 발17×9cm/reach12cm, 몸22×18cm/reach24cm, 무기5cm, height gate32cm/normal.Z.5/teleport256cm는 어시스턴트 임시값이다. 둥근 윤곽, 얕은 접촉, 바닥 관통 방지 및 중첩 층 오염 억제를 위해 선정했고 Actor 조정 속성/전용 material에 집중했다. 원작 writer 실행 식/동일 프레임 비교는 미확보다.

최종 실제 메인 DX12 PIE `Khazan.Snow.PIE` Success: 2026-10-07 04:22:07 UTC, PID27452. 깊이 capture785.0→799.5, 실제 파임14.5cm, compressed render/기존 collision 차이<1cm. 실제 Player run447.37cm/압축485샘플, Dodge383.41cm/5샘플, toe contact85프레임/압축1.0. 4 Monster family 이동·몸 접촉·원본 장비 접촉, 공중 negative, 반복 압축/창 이동 cache/EndPlay 복구 통과. 몸·무기 격리 pose는 실제 gameplay 넘어짐/공격 montage의 전체 재생을 검사한 것과 구분한다. 화면은 `Saved/SnowQA/{Snow_Untouched,Snow_Compressed,Snow_Player_Run_Dodge,Snow_Weapon_Contact,Snow_Monster_Torso}.png`; 무파임/파임 이미지 직접 검수 및 SceneDepth 값 검증 완료다. 원작과 픽셀 동일 완료로 표현하지 않는다.

최종 편집 대상은 `/Game/Maps`의 플레이 맵이다. 별도 `_Art/.../Maps` 보관 맵과 GameDefaultMap은 이 작업에서 교체하지 않았다. 후속 조정은 현재 메인 맵의 46 surface/Actor/2 material만 수정하며 초기 authoring/full map 복원을 반복하지 않는다. 원작 shader와 동일 카메라 연속 프레임을 확보하면 압축 재질·rim·높이 해석을 그 근거로 조정한다. runtime/충돌·경로·성능 계약은 `../Engineering/HEINMACH_SNOW_IMPLEMENTATION_20261006.md` 마지막 절에 분리했다.


## 2026-10-07 — 넓은 발 눌림·무기 크레이터 후속 반영 완료

사용자 최신 요청의 방향은 정확한 신발 크기/위치를 복제하기보다 넓고 부드러운 눈 눌림, 무기는 운석 구멍 같은 큰 파임이다. 기존 원작 동일성 목표에서 이번 brush 크기만 사용자 룩 변경 요청을 우선했다. `/Game/Maps/L_HeinMach_Environment`의 HM_SnowDeformation을 조정했다. 발 반경17×9→40×32cm(기본 파임 지름80×64cm, 타원 면적 약8.37배), 무기 반경5→100cm(기본 지름2m, 원형 면적400배)다. 완만한 rim은 파임 경계 바깥까지 이어진다. 확대된 quintic 타원/원형 brush가 인접 발자국을 넓게 연결해 선명한 개별 신발 윤곽을 줄인다. 무기 이동 경로는 넓은 원형 눌림을 겹쳐 표현한다.

위 치수와 발 접촉 허용높이20cm/무기24cm는 요청한 방향을 위해 **어시스턴트가 선정한 임시 native tuning**이며 원작 메타데이터 직접값 또는 사용자가 숫자를 지정한 값이 아니다. 기존 깊이/압축 색·roughness/부드러운 rim의 material을 재사용했다. 기존 snow coefficient의 native15/7.5cm 해석 및 일반4cm는 유지했다. 원작 shader/pixel 동일 검증으로 표현하지 않는다.

private saved reload와 실제 main saved reload에4설정 값 일치, actor9,869/기존 source poses9,868/snow46/micro dressing65/fire258/merged weapon profile4를 검사했다. 기존 small-stone Pawn/nav 완화, Sky/PP/날리는 눈·횃불 배치와 사용자 PlayerParts/Monster 변경은 보존했다. 새 texture/material/mesh asset은0이며 기존 Actor 설정과 runtime writer만 보완했다.

실제 private Khazan.Snow.PIE Success06:15:07 UTC, main Success06:28:20 UTC/PID28460. main run411.51cm/압축2,267샘플, Dodge437.76cm/1,221샘플, 실제 Imperial_R 장비 ground1,023샘플. 날 접촉 위치에서(60,50)cm 떨어진 지점의 압축>0.1도 통과해 넓은 크레이터를 검사했다. 공중 무기 억제/4 Monster 이동·몸 접촉·합쳐진 장비/깊이14.5cm/render-collision<1cm/반복·창 이동 이력·EndPlay 복구는 통과했다. 몸/장비 pose fixture는 gameplay 넘어짐/공격 전체 montage 검증과 구분한다.

첫 자료 `Saved/ImportReports/HeinMachSnow_20261006/BroadBrush20261007/{Baseline,SavedSettings,StagePIEPassed,Delivery,MainVerification20261007,FinalVerification}.json`, 실제 main 사진은 MainPreview의 PNG5다. Before/StagePreview도 보존했다. Before 사진 이후 PlayerParts/무기 등 독립 변경이 있어 이미지 차이 전체를 눈의 변화만으로 해석하지 않는다. 메인 mapSHAb9802151fccf3fd5d4c21073506014f7cba8d5d532be703d06b12c47d1b76b00. 새 native property를 포함한 별도 모듈이므로 실행 중인 user editor에는 저장 후 재시작이 필요하다. 사용자 DevMap/콤보 정의의 미저장 content1은 보존했다. 이후 크기는 같은 Actor의 FootRadiusCm/WeaponRadiusCm와 contact height 설정에서 조정한다. runtime 비용/수명은 Engineering 정본의 같은 후속 절에 분리한다.


## 2026-10-07 — 두꺼운 눈층·깊은 무기 크레이터 메인 반영 완료

사용자 직접 요청으로 기존 snow graph를 활용한 material 복사본2개와 현재 HeinMach map의 설정을 선택 변경했다. DeepSnow15→60cm, DeepSnow2 7.5→36cm, 기타 snow4→18cm, rim2.5→12cm는 어시스턴트 임시 튜닝값이다. 원작 scalar의 shader 단위/최종 world displacement가 미확인이므로 이 높이를 원작 검증값으로 표현하지 않는다. 원본 metadata 경로·직접 scalar의 출처는 앞선 OriginalSnowContracts 절을 유지한다. 새 값의 출처는 이번 사용자 룩 요청에 맞춘 assistant 선택이다. 현재 조정 위치는 M_HM_Deformable_Landscape1_Deep20261007/2_Deep20261007의 SnowHeightCm_<layer>/SnowRimHeightCm_Temporary이며 source D/N/S/기존 weight/표면 배치는 유지한다.

발은 FootCompression.7로 부분 압축하고 무기/몸은1로 바닥까지 압축한다. max accumulation으로 반복 접촉이 물리 바닥 아래를 파지 않는다. 깊은 layer의 이론 발42cm/무기60cm, rim 상한12cm이며 레이어 weight 때문에 위치별 실제 깊이는 달라진다. native displacement normalization75cm/magnitude.75/center0와 기존 terrain scale100을 함께 설정해 60+12cm를 bound 안에 넣었다. HeinMach 무기 contact reach84cm는 최대 snow60+기존 substrate tolerance24로 계산한 보수적 임시값이다. 발 radius40×32/무기 radius100cm와 foot reach20cm를 유지한다. 실제 GPU snow top collision이 아니며 얇은 layer에서도 공통 최대 reach를 사용한다.

깊은 벽에서 2cm bilinear field의 미분이 각지게 보이는 것을 normal-only ±2texel 중앙차분(현재 ±4cm)으로 완화했다. 새로운 CPU texel/mesh/texture allocation은 없으며 수정 pixel에서 field4회 추가 sample, untouched pixel에서는 기존 source normal/weight height derivative를 사용한다. material RHI compile errors0, pixel instructions600/624/vertex148. Nanite mesh46의 precision/fallback/collision은 이번 변경0.

Fresh main PID15340 native actual contact PIE Success: GPU 발40.500cm/크레이터58.000cm, 바닥 render-vs-collision<1cm, 반복/이동창 이력/실제 Player run·Dodge/4 Monster 발·몸·합쳐진 무기/공중 억제/EndPlay passed. QA 좌표의 혼합 layer 때문에 첫 pure60cm 가정2항목 실패는 InitialMixedWeightQAFailure.log에 보존하고 실제 깊이×.7 비율 검사로 정정했다. 저장 scene9869/기존 poses9868/fire258/snow46/micro65와 source weapon profile4를 main readback 검사했다. native fixture는 모든 실제 공격 montage·knockdown 연출 검증이나 원작 pixel parity를 의미하지 않는다.

첫 main 전달은 loaded material의 Windows file lock으로 Source3/map까지만 반영되고 material 단계가 실패했다. 잘못 이어 실행한 read-only verifier17840은 init assertion으로 진행하지 못해 normal close가 불가능했으며 해당 own process만 종료했다. user19684와 다른 작업 process는 조작하지 않았다. live RESETLOADERS/강제 package 해제 없이 private editor16088에서 Deep20261007 복사본2를 만들고46 surface 참조를 바꿨다. 이전 material2의 main SHA는 baseline 그대로다. 초기 전달/검증 실패는 IncompleteDeliveryStartupFailure.log/PreAliasSavedSettings.json에 남겼다. 새 main entry는 init exception에서도 own editor를 정상 종료하도록 보완했다.

자료 정본은 Saved/ImportReports/HeinMachSnow_20261006/DeepSnow20261007/{Baseline,SavedSettings,StagePIEPassed,Delivery,FinalVerification}.json, StagePIE/MainPIE.log, MainPreview의 PNG6 및 RuntimeGeometry.json이다. 메인 Source3/map/new material2 선택 전달, 새 alias UnrealEditor-KhazanSnowDeep20261007.dll; 일반 DLL은 전달 시 최신 hash 2f27c046480aeb7c328b79cd3268dc6c8fc07659ed4b4fb4d8773d296183773e 그대로 보존했다. 사용자 에디터의 save/reload/PIE/camera/close를 실행하지 않았다. 새 native property는 기존 실행 중 에디터에 반영되지 않아 사용자가 작업을 저장하고 재시작해야 한다. 현재 값이 과하면 위 scalar/FootCompression/WeaponContactHeightCm에서 조정하고 같은 fixture와 실제 플레이 화면을 다시 검사한다.


<!-- HeinMachSnow_Contact55_20261007_preview_verified_pending -->
## 2026-10-07 21:11 KST ? Contact55 Main Preview ?? ????? HeinMach ?? ??

Main Source3/? Contact55 material2/Preview map/UnrealEditor-KhazanSnowContact55QA_20261007.dll? ?? ????. ?? native PIE ?? ?? /Game/Maps/L_HeinMach_Environment_Contact55_20261007, fresh background Main PID24660, 12:08:02 UTC Khazan.Snow.PIE Success?. GPU ?? ?34.000cm/??50.000cm?? ?? canonical /Game/Maps/L_HeinMach_Environment? ?? ???? ???. ??? Main PID3528? HeinMach/dirty0/PIE???? ??? ???? ?? file lock? ????. ??? save/reload/PIE/camera/close? ???? ???. FinalVerification? success=false/preview_verified=true/canonical_map_pending=true? ??? Preview ??? ????.

?? ??55cm??35cm???50cm? ?? ???? ?? ??? ???. ?? DeepSnow2 36cm/?? ?18cm/rim12cm? ?? assistant ?????. ? ??5~8cm ??? ??1.4rim ??? ??? ?? ?? semiaxes8?5cm, brush?8/1.4?5/1.4cm, vertical substrate reach8cm? ????. field R[0,1]? reference55cm? ?? ?? ???? foot35/55?weapon50/55?body1??. min(weightedSnowHeight,55*R)? ?? ???? substrate?? ????. ?? D/N/S?source layer weight/UV?mesh/collision? ???? ?? metadata ????? pixel parity ???? ???? ???.

?? ? GPU ??? ?? mesh LOD0 ??? ?? ??? barycentric ??? smooth normal ???? camera? ????128?128 ???/?? foot SceneDepth? pixel? ?? ???? ????. ?? Nanite ?? ?? ???? ??? vertical Z ??? ?? centre ray? ????. ?? tiny-foot0cm ??? first Main Preview2492 Halberd torso ??? ????. case15?? ?? pelvis ?? ?? bPauseAnims=true? test pose? ????? product body ?? ??? ??. ?? case17 merged weapon? ?? pause? ????. ?? Preview??? partial depth/residual?isolated foot ?? ? ???repeat/cache/fullclear?actual Player run/Dodge/4Monster ????gear/????/EndPlay? ????. ?? foot8cm ?? ? ?? airborne negative??? ?? ??/????GPU/shipping ??? ?????.

??? Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007/FinalVerification.json/Delivery.json/PendingApplyStatus.json? MainPIE.log/MainPreview?. ?? ?? ??? Preview ??? Source/? ?? ???? ?? canonical ?? ??? ???. ?? baseline SHA 700a26ed9fb41db7da54c1ca2fe248efc768be029ba89b577fb7ff9901a84cba? ???? authored canonical SHA c2796c4a0ec5540c22bcdb367ad7e7b8da7bff4a5aacb9a5c29bfdc19de4808c? Content ? PendingCanonical/L_HeinMach_Environment.umap? ????. 12:08:54 UTC ??? hidden worker2256? wait_apply? ???3528 ??? ????. ?? ? baseline SHA? ?? ?? ??? pending blob? atomic ???? hash/receipt? ????. ??? map? ???? ???BlockedCanonicalChanged, ?? lock? WaitingForCanonicalUnlock??. ?? ? ?? appender? ???? Preview PIE? canonical SHA ??? ?? ????. ?? canonical? ? Main PIE? ?? ??.

<!-- HeinMachSnow_Contact55_20261007_preview_verified_pending_utf8 -->
## 2026-10-07 21:13 KST — Contact55 Preview 검증 성공·원본 적용 대기 (UTF-8 보완)

바로 앞 pending 기록의 문자열 인코딩이 손실돼 이 절에 동일 상태를 올바른 UTF-8로 보완한다. 앞선 기록은 보존한다.
Main Source3/새 Contact55 material2/Preview 맵 /Game/Maps/L_HeinMach_Environment_Contact55_20261007/QA alias UnrealEditor-KhazanSnowContact55QA_20261007.dll은 선택 반영됐다. 새 background Main PID24660의 실제 Khazan.Snow.PIE는12:08:02 UTC Success다. GPU 실측 발34cm/무기50cm다. 원본 /Game/Maps/L_HeinMach_Environment는 아직 미적용이며 사용자 Main PID3528이 HeinMach/dirty0/PIE없음 상태로 원본을 로드하고 있어 잠금이 유지된다. 사용자 save/reload/PIE/camera/close는 수행하지 않았다. FinalVerification은 success=false/preview_verified=true/canonical_map_pending=true로 Preview 성공과 원본 적용 완료를 분리한다.
최대 눈55cm·발35cm·무기50cm는 사용자가 직접 지정했다. DeepSnow2 36cm/기타 눈18cm/rim12cm는 앞선 assistant 임시값을 유지했다. 발 주변5~8cm 요청에 맞춰 기존1.4rim을 포함한 명목 타원 semiaxes8×5cm를 선택했고 brush는8/1.4×5/1.4cm다. 발 trace reach8cm는 접촉 오인을 줄이되 타이트한0을 피하는 native 선택이다. field R[0,1] reference55cm, foot35/55·weapon50/55·body1과 min(weightedSnowHeight,55*R)로 얕은 눈에서는 substrate까지만 파인다. 기존 D/N/S·source layer weight/UV·mesh/collision을 보존하며 이 값을 원작 검증값으로 표현하지 않는다.

GPU probe는 실제 LOD0 삼각형 정점 법선을 barycentric 보간한 smooth normal 방향으로 카메라를 정렬하고128×128 baseline/isolated foot SceneDepth의 동일 pixel 차이 최대값을 측정했다. 경사면 수직 Z 깊이나 단일 중앙 ray와 구분한다. tiny foot0cm 및 첫 Preview2492 Halberd torso 실패는 보존했다. test case15에서 pelvis 배치 전에 bPauseAnims=true로 pose를 고정했고 제품 body 코드는 동일하다. 기존 merged weapon case17도 같은 pause를 쓴다. 최종 Preview는 partial depth/residual·foot 범위밖0·repeat/cache/fullclear·실제 Player run/Dodge/4Monster gait/body/gear/공중무기/EndPlay가 통과했다. actual foot8cm 바로 위 고립 airborne negative·모든 실제 공격/넘어짐·원작 pixel parity·GPU/shipping 성능은 미검증이다.

자료는 Saved/ImportReports/HeinMachSnow_20261006/Contact55_20261007의 FinalVerification.json/Delivery.json/PendingApplyStatus.json와 MainPIE.log/MainPreview다. 원본 canonical SHA700a26ed9fb41db7da54c1ca2fe248efc768be029ba89b577fb7ff9901a84cba는 그대로다. 후보 SHA c2796c4a0ec5540c22bcdb367ad7e7b8da7bff4a5aacb9a5c29bfdc19de4808c는 Content 밖 PendingCanonical/L_HeinMach_Environment.umap에 보존한다. hidden worker2256은12:08:54 UTC wait_apply로 시작해 사용자3528 종료를 기다린다. 종료 후 baseline SHA가 같을 때만 atomic 적용하며 변경된 사용자 map은 보존·BlockedCanonicalChanged, 다른 lock은 WaitingForCanonicalUnlock이다. 적용 후 hash/receipt/finalize/완료 appender를 확인한다. 현재는 Preview 성공·원본 적용 대기이며 원본 canonical 새 Main PIE 증거는 없다.


<!-- HeinMachSnow_AttackContact_20261008_complete -->

## 2026-10-08 10:52 KST — Contact55 기본 HeinMach 반영·새 접촉 검증 완료

이전 Preview 성공·canonical 대기를 이번 새 전달로 완료했다. 기본 /Game/Maps/L_HeinMach_Environment는 현재 Contact55 material2와 최대55cm/발35cm/무기50cm·rim 포함 발 반경축8×5cm를 사용한다. material2의 바이너리·D/N/S·source weight/UV·mesh/collision·9868 source poses/fire258/snow46/micro65는 보존했고 맵의 기존 Snow owner에 contact profile2(4.56MiB payload)를 저장했다. 원작 직접 높이로 간주하지 않으며 사용자55/35/50 및 기존 임시36/18/rim12 구분을 유지한다. resource 재추출/새 머테리얼/texture/mesh 작성0.

무기는 기존 실제 Attack Ability 실행 중 지역 눈 표면에 닿을 때만 넓은 crater를 만들며 이동은 작은 발 파임이다. 세부 native 소유/계산/임시 접촉6cm·검증은 Docs/Engineering/HEINMACH_SNOW_IMPLEMENTATION_20261006.md의 이번 절을 따른다. fresh canonical MainPID652 native PIE Success01:45:35 UTC; 새 모듈/저장 profile2/기존 scene/settings 확인과 GPU 발34cm·무기50cm, partial/residual/range/cache/EndPlay 검증을 완료했다. 실제 활성 Player/4NPC Attack pose를 평가 후 고정한 접촉 fixture이며 모든 자연 montage 궤적·원작 pixel parity·GPU/shipping 최악 성능은 미검증이다.

정본 Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008/{Delivery,FinalVerification,MainVerification,SurfaceProfiles,SurfaceProfileProof}.json 및 MainVerify.log/StagePIE.log. canonical SHA57d8319ea0f3b623c3a4a5de052fd3abd5ef38d898f0b0e440108879dd771ea7, 선택 alias UnrealEditor-KhazanSnowWeaponContact20261008.dll. 이전 worker2256을 중지·archive했고 이전 PendingApplyStatus는 SupersededByAttackContact20261008, canonical_pending=false다. 옛 Delivery/Preview FinalVerification/PendingCanonical은 과거 증거로 보존하며 재적용하지 않는다. 사용자 에디터 save/reload/PIE/close는 실행하지 않았다. 마지막 UE 연결/프로세스는 없었고 다음 새 에디터에서 기본 맵을 확인한다.



<!-- HeinMachSnow_AttackContact_20261008_normal_rebuild_verified -->
## 2026-10-08 11:01 KST — 후속 일반 Main DLL 빌드도 새 접촉 검증 완료

전달 뒤01:49:41 UTC Main 프로젝트 native build가 새로 실행돼 normal DLL과 manifest가 갱신됐다. 이 빌드는 본 작업이 시작한 것이 아니며 되돌리지 않았다. 최신 전체 Main Source가 본 작업의 검증된 NativeBuildProof와 byte 일치하고 canonical/Source3/기존 보호 asset·Config도 동일함을 확인했다. 현재 manifest는 `UnrealEditor-Khazan.dll`, SHA `4ca0cc527b9d94c6812246befd974e5ce268ec5ece23207add6394d369cde354`다. 앞 절의 alias 선택·원래 DLL 보존은 당시 전달 사실이며 현재 선택 모듈 정본은 이 절이다. 이전 성공 Delivery/FinalVerification을 수정하지 않았다.

새 hidden MainPID19372에서 실제 normal DLL 경로·저장 canonical profile2/55cm·작은 발 범위/scene9,869를 재검증했고01:58:40 UTC `Khazan.Snow.PIE` Success 및 정상 종료했다. Player Run142/Dodge236 표본 maximum35/55, Player/4NPC active 공격 지면 양성/공중·비공격·취소 음성과 기존 GPU 발34/무기50cm/cache/EndPlay 회귀가 통과했다. 자료는 `Saved/ImportReports/HeinMachSnow_20261006/AttackContact_20261008/NormalMainRebuild_20261008`의 snapshot Delivery(not_a_delivery), MainColdBuild.log, MainVerification/Exit, MainVerify.log다. 이번 Snow 수정·canonical 반영은 완료이고 old worker/preview pending을 재개하지 않는다. 기존 모듈 변경 및 source 보존 절차·원작/mip/normal/자연 fast sweep/GPU/shipping 미검증 범위는 유지한다.

같은 Development Editor/frozen attack scope의 normal DLL SnowTick은 active929 평균0.507301/P95 1.033800/max4.364200ms, `Profile(20261008_105739).csv`다. 이전 .420499ms와 조건이 다른 별도 관측이며 개선율로 비교하지 않는다. 사용자 에디터를 저장/종료/재시작하거나 예전 alias로 manifest를 되돌리지 않았다. 새 에디터에서 기본 HeinMach를 확인한다.
## 2026-10-11 — Main 눈40cm 및 표현 후속

최신 Main은 DeepSnow40cm, 다른18/36cm layer 유지, foot35/40=.875, weapon cap1, profile2로 적용됐다. actor9861/PP0/전체 pose를 보존했고 실제 GPU40cm/Snow contact 전체 검사 및 동일 카메라 RHI를 완료했다. padding15cm/조명은 명시된 해석·임시값이며 원작 직접 metadata로 바꾸어 기록하지 않는다. exact 적용·출처·backup/receipt는 [Art 후속 정본](COMBAT_PRESENTATION_FOLLOWUP_20261011.md)이다.

## 2026-10-16 — 현행 눈 재질·배치 설명과 과거 수량 구분

현재 구현 설명 요청에 따라 저장 report/authoring script와 현행 파일 hash를 읽기 전용으로 대조했다. 에셋 저장·재임포트·재추출·새 RHI/PIE는 하지 않았으며 문서 하단만 추가한다. runtime 책임과 상세 수식은 Engineering `HEINMACH_SNOW_IMPLEMENTATION_20261006.md`의 같은 날짜 절에 분리했다.

현재 두 재질은 `/Game/_Art/Player/Environment/Rendering/HeinMachSnow/Materials/M_HM_Deformable_Landscape1_Contact55_20261007` 및 `M_HM_Deformable_Landscape2_Contact55_20261007`이다. 두 uasset SHA는 `Metadata/CombatPresentationFix_20261011/MainResume/FinalVerification.json`의 최종값과 동일하다. 이름의 Contact55는 과거 이름이며 현재 DeepSnow/DepthReference는40cm다. `MainSavedResume01/Snow40.json`과 `SnowBake/SurfaceProfiles.json`이 높이/레이어/profile 근거다. DeepSnow2=36cm, 다른 snow layer=18cm, non-snow=0, rim coefficient=12cm이다. 40/35는 기존 사용자 요청,36/18/12 및 압축 darkening.06/roughness+.08은 기존 어시스턴트 임시 표현값이다. layer 가중치 때문에 지역 높이가 모두40cm인 것은 아니며 rim이 더해진 표면을40cm hard cap으로 설명하지 않는다.

10월16일 RoutePrune의 `FinalVerification.json` 및 `MainSaved01/Inventory.json`과 현재 map SHA가 일치한다. 이 최신 inventory에는 Snow owner1(`KZSnowDeformation_0`, label `HM_SnowDeformation`) 및 전용 Snow mesh를 참조하는 component38/고유 mesh38가 있다. 두 Contact55 material을 사용한다. 최초 도입46 surface/9869 actor 및10월11일9861 actor는 당시 검증 수량이며 최신 정리맵의 배치 수로 재사용하지 않는다. 이번 inventory schema에는 component tag/모든 actor UPROPERTY가 없으므로 그 필드를 fresh 재검사했다고 확대하지 않는다.

재질은 원본 weighted terrain의 D/N/S·UV·weight·puddle 경로를 보존하고 Nanite Displacement/파임 normal/PBR을 덧붙인 native 구현이다. 현행 FIELD_CODE는 `Scripts/Art/heinmach_snow_contact55.py:25`, normal은 해당 script의 기존 deep normal 보정, 40cm 변경은 `Metadata/CombatPresentationFix_20261011/author_snow40_resume.py`로 추적한다. 최초 `heinmach_snow_author.py`의15cm·18cm normalization을 현행 파라미터로 읽지 않는다. 현재 식은 지역높이 H에서 `min(H,DepthReference*R)*valid`를 빼고 `RimHeight*G*valid*SnowMask`를 더한다. normal은 원래 tangent normal을 world로 변환한 뒤 높이 변화 미분을 합성하며 field±2texel(현재±4cm) 중앙차분을 사용한다. 75cm normalization/magnitude.75/center0와 actor scale100은 기존 bound 계약이며 runtime 충돌지형의 높이 수정과 다르다.

CPU contact profile은 기존 weight PNG의 `(높이분자, non-puddle weight합, snow weight합)`을 보존해 보간 후 나눈다. Landscape1=253×316, Landscape2=505×631의 float3 payload 합4,783,236bytes는 현재 SnowBake manifest의 계산값이다. shader의 weight/UV/height/reference/rim을 바꾸면 profile도 함께 갱신해야 하며 원작 shader를 회수한 자료로 표현하지 않는다. 원작 VHM/WriteSnow 관련 근거는 기존 OriginalSnowContracts package/file/field를 재사용한다.

실제 과거 GPU40cm/고립 발34cm 및 접촉 회귀는10월11일 receipt의 관측값이다. 이번 턴에는 source/재질 동일 SHA와 최신 map 저장 증거만 확인했다. 설명 완료, 게임 파일 변경0, 신규 build/PIE0이며 원작 pixel/native 동일성과 전체 Shipping 비용 검증은 별도다.
