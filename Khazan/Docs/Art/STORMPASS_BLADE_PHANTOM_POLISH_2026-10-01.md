# 2026-10-01 StormPass Blade Phantom 보스 환경 폴리싱

## 실제 적용 범위

사용자의 두 보스 장소 폴리싱·조사·마킹 요청에 따라 `/Game/_Art/Player/Environment/StormPass/Maps/L_StormPass_Environment`를 수정하고 저장했다. 기존 메시를 삭제하거나 이동하지 않았다. 기존 PlayerStart, HeinMach, Player 메시·Skeleton·애니메이션, 게임 C++는 수정 대상이 아니다. 보스 전투/자동 페이즈 전환 구현과 아래 환경 작업을 구분한다.

수정 전 map과 운영 metadata는 `Saved/ArtBackups/StormPass_BladePhantom_PrePolish_20261001`에 보존했다. 새 렌더 에셋은 `Content/_Art/Player/Environment/StormPass/Reconstructed/BladePhantomPolish`에 모았으며, 공유하는 기존 재질 대신 페이즈 전용 인스턴스를 사용했다.

## 두 페이즈 장소와 원작 위치 근거

| 구분 | 원작 서브레벨/장소 | 확인 방법 |
| --- | --- | --- |
| 1페이즈 | `StormPass_Boss_Phase_1` — 성채 내부 홀, 왕좌·계단·기둥·붉은 수면 | 해당 source prop 배치와 원작 WEP Phase1 |
| 2페이즈 | `StormPass_Boss_Phase_2` — 눈 덮인 숲·바위·목책·landscape와 붉은 수면 | 다른 source prop/landscape 배치, WEP Phase2, 보스 spawn의 레벨 의존성 |

두 환경은 **같은 보스 좌표 영역에 겹쳐 배치된, 배타적으로 표시할 원작 서브레벨 변형**이다. 서로 다른 곳에 보이도록 임의의 먼 좌표로 옮기지 않았다. 큰 PostProcess volume의 중심을 2페이즈 spawn으로 취급하지 않는다.

| editor-only 표식 | source JSON / export index / field | 원본 월드 위치 `(X,Y,Z)` cm | 조건 |
| --- | --- | --- | --- |
| `SP_BP_Phase1_ArenaReference_TargetPoint_Boss` | `StormPass_Spawn_Main01.json`, 833, root `RelativeLocation` | `(162650, 51600, 695)` | 공통 보스 참조점; 새 gameplay spawn으로 확정한 값이 아님 |
| `SP_BP_Phase1_PlayerEntry_Mission02_Start_BossZone` | 위 JSON, 1464, root `RelativeLocation/Rotation` | `(162240, 51600, 296.66724)`, Yaw `-10°` | 원작 BossZone 진입 앵커 |
| `SP_BP_Phase2_ArenaReference_TargetPoint_Boss` | 위 공통 참조점 | `(162650, 51600, 695)` | 같은 좌표 영역에서 2페이즈 환경을 선택해 확인 |
| `SP_BP_Phase2_BossSpawn_SA_BladePhantom` | 위 JSON, 1519, root transform / `DependentLevelPath` | `(163796.5, 51485.645, 222)`, Yaw `175°` | `DependentLevelPath=/Game/_Kazan_/Level/StormPass/StormPass_Boss_Phase_2`; `bHalfHeightAdjusted=true`, `SpawnIDX=468`, `TIDX=293006`, `bSpawnAtBeginPlay=false` |
| `SP_BP_CinemaReference_BossStart_C_M_BladePhantom_5` | `StormPass_Cinema_Boss_Start.json`, 해당 actor의 root transform | `(57170.38, 14660.25, 6435.748)` | 컷씬 staging 참조; 실제 전투 spawn과 구분 |

정확한 export index, 회전, source JSON SHA-256은 `Metadata/BladePhantom_ArenaPolish_20261001/OriginalAnchors.json` 및 `ArenaMarkers.json`에 있다. 같은 이름을 가진 다른 지역 에셋의 값을 사용하지 않았다.

Outliner 위치는 `StormPass/01_BladePhantom/Phase1`, `Phase2`, `CinemaReference`다. `SourceMarkers`와 `ReviewCameras`에서 찾는다. 검수 카메라 2개는 진입 앵커에 **임시 검수 높이 300 cm**를 더한 위치이며 FOV **80°**다. gameplay 카메라·리스폰 설정값이 아니다. 마커 5개와 카메라 2개는 editor-only로 저장했다.

## 조사 결과와 수정

- Root prop 1,862, child prop 515, 기존 source light 24, fog sheet 7, foliage component 7 / instance 3,218, landscape component 16을 저장 metadata와 필요한 raw source에 대조했다. 메시 존재·종류와 전체 attachment chain을 합성한 transform에서 오류가 없었다. 기존 source 배치를 재이동하거나 재생성하지 않았다.
- Source USD의 렌더 바인딩을 이용해 mesh layout 119개, 렌더 재질 슬롯 3,143개를 확인했다. source slot과 UE slot의 순서를 동일하다고 가정하지 않고 texture 대응으로 매핑했다. 오류 0이다. 물 actor 2개는 mesh의 `WorldGridMaterial` placeholder 대신 원작 WaterBody의 런타임 재질 바인딩을 기존 native water metadata에 따라 확인했다. WorldGrid로 되돌리지 않았다.
- 보스에서 쓰는 native surface MI 188개(Phase1 134 / Phase2 54)를 복제하고 source WEP의 global metallic/roughness/specular 값을 적용했다. 기존 source control과 텍스처·알파 정책을 유지했다. StaticMesh 렌더 재질 203개의 최종 감사에서 누락·fallback·채널 오류 0이다.
- 나무 MI 4개는 일반 USD 감사가 **사용되지 않는 옛 selector vector**를 보고 경고했다. 실제 `M_SP_SourceTreeFoliage_V2` 그래프는 roughness=G, AO=R, metallic=별도의 0 scalar로 정상 연결돼 있었다. 실제 그래프를 검증하도록 감사기를 보완했으며 나무를 잘못 재수정하지 않았다.
- 보스에서도 바깥 지역 sky/cloud가 남아 있던 연결을 수정했다. 원작 WEP가 지정한 Phase1 `SkyColor_DeepGray`, Phase2 `SkyColor_DeepNight`를 표적 추출해 기존 native sky parent에 반영했다. 두 페이즈의 cloud layer 원작 preset은 `CloudIntensity=0`, `CloudAmount=-1`이므로 보스에서는 cloud 메시를 숨긴다. 바깥 검수 모드에서는 이전 GloomyDay와 cloud를 복원한다.
- 표시 변형 전환 시 sun·sky·sky material·cloud·fog를 함께 전환하도록 기존 `restore_stormpass_route_presentation.py`에 연결했다. `StormPass_Light`에 있어 기존 이름 판별에서 빠졌던 BossClear PostProcess가 보스 전투 모드에 영향을 주지 않도록 enabled 조건도 분리했다.
- 이전 root-only 복원에서 빠진 component 138개를 attachment/template 상속까지 조사했다. 깃발 14개, 활성 하위 point light 28개, fire/화염벽 표현 47개를 source 위치에 추가했다. 원작 PSK 깃발의 native bounds 오차는 최대 `0.000004296875 cm`로 float 오차 범위다. D/N/S는 원작 `WM_COM_Flag_Base_001_WW`와 같은 텍스처이며 source Proxy=None 슬롯은 보이지 않는 재질로 처리했다.
- 불꽃은 Phase1 Cascade 28곳과 Phase2 Niagara fire 3곳 / fire wall 16곳이다. 원본 텍스처를 사용한 native animated material billboard로 보완했다. 작은 불/큰 불은 각각 원본 core StartSize `(23,35,0)` / `(120,110,0)`과 실제 `Fire_core_size`를 사용한다. 작은 불 atlas grid는 source material B_30의 `SubUV_U=12, SubUV_V=6`, 큰 불은 B_31의 `8,8`이다. 정확한 JSON·export index·field·texture는 `CascadeCoreSources.json`에 기록했다.
- UE 5.8 `MaterialBillboardComponent.cpp`의 world-size 렌더 경로에서는 transform scale이 그대로 sprite 크기가 되지 않는다. source scale을 크기에 명시적으로 반영했다. FireWall은 source local Y를 길이, Z를 높이로 대응시키는 **native 축 해석**이며 원작 Niagara 실행 코드를 복원했다고 표현하지 않는다.
- 마지막 재질 작업으로 기존 Phase2 fog plane 7개의 재질을 복제하고 source WEP `FogSheetColor=(1,0.25,0,0.75)`를 연결했다. 기존 native emissive × RGB, opacity × A의 명시적 bridge이며 원작 MPC shader graph의 완전한 포팅은 아니다. plane 위치·크기를 바꾸거나 fog geometry를 재생성하지 않았다.

## 수치 출처와 native 재현 범위

원본 WEP는 `C:/Users/user/Desktop/카잔/Exports/BBQ/Content/Art/ArtRendering/AR_PostProcess/WEP/WEP_StormPass_Boss_Phase1.json` / `...Phase2.json`이다. 저장 profile의 source JSON SHA-256은 각각 `B339CDCF4F97CEADDE910232A7FD305093B5B3EB0F825B4335EEC9E5EFD9F52D`, `938E452DFF4EFC374EC9C06160B3D2E62F99F4C1F5D6AA1E733537ECD714E458`이다. Sky와 추가 FX의 표적 추출은 기존 EnemyExtractor / CUE4Parse의 UE4.27 해석 경로를 사용했다. raw cooked UE4 package를 UE5 Content에 넣지 않았다.

| source component / field | Phase1 원시 값 | Phase2 원시 값 | 적용 조건 |
| --- | --- | --- | --- |
| `xxEnvironmentMaterialComponent.ScalarValues`: GlobalMetallic / GlobalRoughness / GlobalSpecular | `0.5 / 0.5 / 0.25` | `0.4 / 0.4 / 0.2` | 해당 페이즈의 native surface MI; 무차원 재질 계수 |
| directional light `RelativeRotation` (Pitch,Yaw,Roll) | `(-58.43113,115.03608,599.90796)°` | `(-38.00232,-359.83856,132.28406)°` | 원본 회전; UE 정규화된 회전과 quaternion으로 검증 |
| directional light `LightColor` RGB bytes | `(214,179,138)` | `(199,172,219)` | 원본 FColor |
| sky light `Intensity`, `LightColor` | `1.25`, `(255,189,88)` | `1.25`, `(155,212,223)` | 원본 native sky 계수/색 |
| fog `FogDensity`, `FogHeightFalloff` | `1`, `1.5` | `1.5`, `1` | 원작 custom renderer의 원시 계수; 아래 native 변환과 구분 |
| fog `CameraFollowOffset.Z` | `-2500 cm` | `-2000 cm` | 원작 camera-follow offset; 이 작업에서는 진입 앵커를 기준으로 static editor proxy 사용 |
| fog `VolumetricFogDistance` | `7500 cm` | `5000 cm` | 해당 페이즈 native fog view distance |

임시값은 `PolishPolicy.json`과 `MissingRenderPolicy.json`에 모았다. 어시스턴트 선택값이며 사용자 지정/원작 확정값으로 간주하지 않는다.

| 임시/이전 adapter 설정 | 현재 native 값과 이유 | 검증/조정 기준 |
| --- | --- | --- |
| Phase1 exposure bias | `3 EV`; 이전 native `1 EV`에서 어두운 바닥/기둥을 읽을 수 있도록 조정 | 원작 BBQ ambient response와 UE native shading 차이; 렌더에서 바닥·계단과 밝은 광원 부분을 함께 비교 |
| fog density / height falloff adapter | 기존 계수 `×0.01 / ×0.1` 유지. 결과 Phase1 `0.01 / 0.15`, Phase2 `0.015 / 0.1` | 원작 renderer의 단위 변환은 미확인. 기하를 가리는지, 바닥과 목책이 보이는지 검수 |
| 새 하위 light 28개 | 명시된 nonzero intensity는 native candela `×10`, 미직렬화 활성 light는 `30 cd`; 미확인 색은 native white | 이전 root-light용 `×750`을 그대로 쓰면 보스 홀이 포화됨을 렌더에서 확인. `×1`은 해당 홀에서 너무 어두워 중간 배율 선택. 광도 단위와 custom C++ 기본값 미확인 |
| 새 light의 누락 radius / shadow | 임시 radius `1000 cm`; 추가 fill shadow는 off | source radius가 직렬화돼 있으면 그 값을 사용. 중복 local shadow 비용을 줄이는 native 선택이며 원작 shadow 설정 확정이 아님 |
| directional light intensity | 이전 native bridge의 `10 lux` 유지 | 원작 sun Intensity의 직접 확인값이 아니며 이번에 원작값으로 재명명하지 않음 |
| Niagara native sprite 크기 | 기본 전체 크기 `120×160 cm`에 source scale 반영 | source sprite size/VM graph 미확인; geometry 경계를 침범하거나 지나치게 작게 보이는지 검수 |
| native FX timing | Cascade 임시 `30 frames/s`. Niagara A/B는 source shader `Speed=35/30`을 native frames/s로 해석 | source shader Speed 단위·수식은 미확인. 원작 particle lifetime/spawn 프로그램과 동일하다고 주장하지 않음 |
| native FX opacity / emissive gain | `0.5 / 1`; A grid `8×8`은 임시, B grid `8×4`는 source `SubUVTexRC` | packed source texture의 직접 사용과 효과 합성/색 프로그램의 근사 구현을 구분 |
| native flag wave | 진폭 `9 cm`, 주파수 `0.25 Hz` | source FlagWave_Big의 `Height_Light=60`, `Speed_Light=0.25`만으로 shader 단위/식을 확정할 수 없어 작은 native wave 선택; 과한 변형 여부 검수 |

원작의 Niagara/Cascade VM, cloth physics, BBQ shading, wind/film-pass를 완전히 재현한 작업은 아니다. source intensity 0인 light placeholder 40개는 의도대로 추가하지 않았다. source water-spline Niagara 9개는 custom spline DI를 포팅하지 않았으며 기존 native water surface·foam 표현을 유지했다. FX 색은 Phase1 source `xxPointLight10`의 RGB bytes `(76,219,255)` / 255, Phase2 source WEP FogSheetColor RGB를 사용한 native palette 해석이다. 원작 FX 색 curve 프로그램의 복원으로 기록하지 않는다.

## 저장·재로드 검증

UE 5.8.2 라이브 에디터에서 적용 후 저장하고, 실제 World 교체가 발생하는 map 재로드를 수행했다. Phase1과 Phase2를 각각 저장/재로드해 검사했다.

- 원본 arena render actor 누락 0, 원본 transform/mesh 오류 0; foliage 3,218 instance 일치.
- surface MI 188 / StaticMesh 재질 203, render slot 3,143, 추가 source render actor 89, phase visibility/collision baseline actor 3,220, 마커/카메라 7의 검사 실패 0.
- sky/sun/fog 값과 fog-sheet 연결도 재로드 후 유지됐다. 초기 전체 actor 14,426 → 최종 14,522이며 추가 96개는 source render 89 + editor-only 마커/카메라 7이다. 임시 capture actor는 최종 저장 전에 제거했다.
- UE가 PostLoad 때 다시 만드는 editor-only `BillboardComponent` 아이콘의 임시 visibility는 gameplay 렌더 계약에서 제외한다. 추가 FX의 `MaterialBillboardComponent`는 제외하지 않고 검사한다.
- 기존 PlayerStart는 현재 `(30357.803,60165.047,2183.912) cm` 상태를 유지하며 setter를 호출하지 않았다. 게임 소스와 HeinMach 보호 파일의 hash는 동일하다. 작업 중 Engineering 문서 4개에서 외부 변경을 감지했으나 Art 작업에서 작성하지 않았으며 그 변경을 보존했다. 검증 과정에서 생긴 기존 helper `.pyc` 변경은 원래 상태로 돌렸다.
- Python 구문 및 UE 내 데이터 계약/시각 렌더 검수다. 새 boss gameplay, 자동 level transition, 보스 공격/AI, Player 이동/충돌의 PIE 검증을 완료했다고 기록하지 않는다.

재사용할 자료는 `Content/_Art/Player/Environment/StormPass/Metadata/BladePhantom_ArenaPolish_20261001`의 `GeometryReloaded`, `MaterialsReloaded`, `MaterialSlotsReloaded`, `MissingRenderReloaded`, `VariantPhase1Reloaded`, `VariantPhase2Reloaded`, `EnvironmentPhase1Reloaded`, `EnvironmentPhase2Reloaded`, `ReloadVerification` JSON이다. 검수 이미지는 `Saved/ArtReviews/BladePhantom_20261001/Phase1_Reloaded_Final.png`, `Phase2_Reloaded_Final.png`와 wide/close 렌더다. Lumen은 전환 직후 한 capture보다 후속 안정된 capture도 함께 확인했다.

## 에디터에서 두 장소 확인

최종 저장 모드는 1페이즈다. 단순히 두 folder를 동시에 표시하면 겹치므로 기존 변형 전환 도구를 사용한다. Unreal Output Log의 입력 모드를 **Python**으로 선택해 아래를 실행한다.

```python
import unreal, runpy
from pathlib import Path
p = Path(unreal.Paths.project_dir())
h = runpy.run_path(str(p / 'Scripts/StormPass/polish_blade_phantom_arenas.py'))
h['view']('boss_phase_1')  # 또는 boss_phase_2
```

`SP_BP_Phase1_ReviewCamera` / `SP_BP_Phase2_ReviewCamera` 또는 SourceMarkers를 선택해 위치를 확인한다. 표시 모드를 저장하려면 `h['save_polish']()`를 실행한다. 바깥 진행 경로는 `h['view']('traversal')`이다. 이 함수는 editor review 선택이며 gameplay에서 체력/Ability로 페이즈를 자동 전환하는 기능이 아니다.

후속 재검수는 `finish_blade_phantom_arena_polish.py`의 `audit_slots`, `audit_extras`, `audit_variant`, `audit_environment`와 본체 `audit_geometry/audit_materials`를 사용한다. 오래된 전체 복원/route-anchor 도구를 재실행해 PlayerStart나 사용자 변경을 되돌리지 않는다.

## 2026-10-01 추가 확인 — 같은 좌표와 다른 전투 환경의 구분

사용자의 “두 페이즈 위치가 같은데 원작은 달라 보인다”는 확인 요청으로 원본 streaming entry, 두 물 actor의 root 배치, 전환 컷씬 metadata와 라이브 마커를 읽기 전용으로 재확인했다. **원본에 직렬화된 두 레벨의 배치 좌표 영역은 겹치지만, 1페이즈 성채 홀과 2페이즈 숲/landscape는 서로 다른 전투 환경이다.** 앞선 “같은 위치”라는 표현을 동일한 지형·장소가 유지된다는 뜻으로 읽지 않는다.

- `StormPass_All.json` export `105` / `116`은 각각 `StormPass_Boss_Phase_2` / `StormPass_Boss_Phase_1`의 `LevelStreamingDynamic`이다. 두 entry에 `LevelTransform`은 직렬화돼 있지 않다. 이 사실은 저장 배치에 별도 이동 offset이 확인되지 않는다는 근거이며, 모든 원작 runtime offset/teleport의 부재를 증명하지는 않는다.
- Phase1 `xxWaterBodyCustomActor_1` export `2379`, root `80`의 `RelativeLocation=(161151,51448,118) cm`, `RelativeScale3D=(15,10,1)`; Phase2 `xxWaterBodyCustomActor1` export `2538`, root `233`은 `(163006.2,51876.9,118) cm`, `(9,8.25,1)`이다. 두 root에는 `AttachParent`가 없으며 기존 Unreal transform 합성 helper로 위치를 재확인했다. 물 actor 원점은 플레이어 spawn이나 arena 중심으로 확정한 값이 아니다.
- `SP_BP_Phase1_ArenaReference_TargetPoint_Boss`와 Phase2의 동명 참조 마커는 **원본 공통 TargetPoint 하나를 두 폴더에 표시한 것**이다. 독립적으로 확인된 두 페이즈 시작점을 뜻하지 않는다. 두 ReviewCamera도 같은 진입 앵커 기반 비교 시점을 사용한다. 라이브 카메라 위치가 모두 `(162240,51600,596.66724) cm`인 것을 확인했다. 카메라를 선택하거나 pilot하는 행위에는 표시 변형 전환 기능이 없다.
- 환경을 비교하려면 위 절의 `view('boss_phase_1')` / `view('boss_phase_2')`를 실행한다. 이때 서로 다른 메시·지형과 해당 페이즈의 조명이 선택된다. 위 두 카메라 중 하나를 선택하는 것만으로는 환경이 바뀌지 않는다. 기존 두 검수 PNG 역시 같은 비교 시점에서 성채 홀과 숲이 다르게 렌더된 결과다.
- 원본 전환 master `/Game/_Kazan_/Art/Cinematic/M_Sequencer/StormPass/BP01/MC_StormPass_BP01_Master`와 시작 master `.../BS/MC_StormPass_BS_Master`만 표적 추출했다. BP01의 binding은 `StormPass_Cinema_Phase`를 참조한다. 현재 JSON 추출에는 Blueprint Function bytecode가 없으므로 정확한 level 표시 전환 호출 순서·플레이어 이동·원작 native 실행 구조까지 확인했다고 표현하지 않는다. 현재 프로젝트의 자동 gameplay 페이즈 전환도 구현 완료가 아니다.

재사용 근거는 `Metadata/BladePhantom_ArenaPolish_20261001/PhaseCoordinateClarification.json`이다. 정확한 export/property, 원본 JSON hash, 새 master metadata 경로/hash와 확인 한계를 기록했다. 이번 추가 확인에서는 map, 마커, 메시, PlayerStart, 게임 소스와 에셋을 수정하거나 저장하지 않았다.

## 2026-10-01 Phase1 밝기·흰빛 재검토 및 수정 완료

사용자가 이전 폴리싱의 성채가 너무 밝고 하얗다고 지적했다. 위 첫 작업의 `3 EV` 및 root/child light의 candela 변환은 이번 Phase1 수정으로 대체한다. 과거 검증 기록과 백업은 보존한다. 게임 C++ 및 캐릭터 기능을 수정하는 요청으로 해석하지 않았다.

### 원작 화면과 원인

직접 확보하고 시각 비교한 원작 전투 화면은 [신아일보](https://www.shinailbo.co.kr/news/articleView.html?idxno=2025547), [Deltia](https://deltiasgaming.com/how-to-defeat-the-blade-phantom-in-the-first-berserker-khazan/), [Sportskeeda](https://www.sportskeeda.com/esports/the-first-berserker-khazan-how-obtain-soul-eater-set)의 Phase1 성채 이미지다. 저장본은 `Saved/ArtReviews/BladePhantom_LightingReview_20261001/Original_Phase1_*`다. 어두운 적갈색 성채, 작은 따뜻한 불빛, 상부의 약한 차가운 빛과 붉은 안개가 공통 참조다. 서로 다른 카메라/전투 순간의 스크린샷이며 원작 광도·노출의 수치 측정 자료로 사용하지 않는다. YouTube 영상을 실제 재생해 검수했다는 의미도 아니다.

- `Phase1LightReviewBefore.json`: root light 13개가 원본 Intensity `2.5/3`에 임시 배율 `750`을 곱한 `1875/2250 cd`였다. 이전 importer의 lumens 설명과 실제 `CANDELAS` 설정이 달랐다. 원본 xx light의 광도 단위와 inverse-square 기본값은 확정하지 못했다.
- 추가 child light 28개는 흰색 보조광이었다. 기존 adapter는 명시된 source intensity에 `10`을 곱하거나, 값이 없으면 `30 cd`를 사용했다. 노출만 낮추면 성채 전체가 어두워지고 밝은 국소 영역은 남았다.
- 실제 에디터 CVar `r.VolumetricFog=0`으로 원본 WEP의 붉은 안개 발광이 렌더에 빠졌다. 로컬 UE 5.8 `Engine/Config/BaseScalability.ini`의 `ShadowQuality@0/1`은 이를 끄고 `ShadowQuality@2` 이상은 켠다. Effects 품질과 혼동하지 않는다.
- Phase1 fire shader는 원본 주황 atlas의 RGB를 단색 mask로 바꾸고 별개 파란 light 색으로 칠한 근사였다. 실제 core emitter 색과 atlas RGB의 연결을 복원했다.

### 원본 직접 값 및 native 보정의 구분

원본 WEP는 `StormPass_EnvironmentProfile.json:profiles.boss_phase_1`에 저장된 `WEP_StormPass_Boss_Phase1`이며 SHA-256은 `B339CDCF4F97CEADDE910232A7FD305093B5B3EB0F825B4335EEC9E5EFD9F52D`다. source light는 `StormPass_SourceLights.json`의 해당 레벨 export `938–950`, child는 `MissingRenderPlan.json`의 `inherited.Intensity`와 출처 package/export를 사용한다.

| 항목 | 적용값과 계산 | 출처 상태·목적 |
|---|---|---|
| Phase1 노출 | `3 → 2.25 EV` | 임시 native 튜닝. 흰 광역 과노출 감소, 성채의 형태 판독 유지 |
| root light 13개 | `source Intensity × 0.05` → `0.125/0.15`, `UNITLESS`, inverse square off | 원본 단위 변환 미확인. 사진 비교에 따른 임시 배율. source falloff exponent `1`, RGB·위치·radius·IES는 보존 |
| 추가 child light 28개 | 명시값 `25/7.5 × 0.08` → `2/0.6`; 미직렬화 22개는 `2`, `UNITLESS`, falloff `1`, inverse square off | 임시 fill adapter. 흰 번짐 감소. 명시값 6개의 source field와 없는 22개를 구분 |
| child light 색 | FColor `(255,189,88,255)` | 원본 WEP SkyLight.LightColor를 재사용한 native 따뜻한 fill 팔레트. 원작 횃불 LightColor의 직접 확인값은 아님 |
| sky intensity | source `1.25 × 0.48 = 0.6` | source 입력에서 계산하되 `0.48`은 임시 튜닝. 과한 차가운 반사 감소. source sky 색은 보존 |
| bloom | source `7.5 → native 0.5` | 원본 custom film-pass 미포팅을 보정하는 임시값 |
| shadow/highlight gain | source `0 / 1.5 → native 1 / 1` (RGB) | 낮아진 노출에서 검게 잘리는 그림자와 밝은 면의 증폭을 완화하는 임시값 |
| mid/high/shadow saturation | source `1.25 / 2.5 / 0.25 → native 1 / 1 / 1` | 미포팅 film shader에 대한 임시 중립화. global `ColorSaturation=(0.275,0.275,0.275,1)`은 원본 직접 값으로 적용 |
| SceneColorTint | native linear RGBA `(1,0.65,0.75,1)` | 임시 적갈색 보정. source 직접값 `(0.669939,0.751674,0.895833,1)`과 구분 |
| FilmSlope | `1`, 원본 override flag 적용 | 원본 `default_properties.Settings.FilmSlope`, `bOverride_FilmSlope` 직접 값. 이전 native 기본값을 원본으로 취급하지 않음 |
| height/volumetric fog | 기존 source density `1 × 0.01 = 0.01`, falloff `1.5 × 0.1 = 0.15` 유지; native emissive `(0.229167,0.071522,0)` 유지 | density/falloff 배율은 기존 임시 adapter. emissive는 source 직접 값. `r.VolumetricFog 1`로 빠진 렌더 기능 활성화 |

모든 새 임시값은 `PolishPolicy.json:temporary_native_adapter.phase1_light_review`에 모았다. `polish_blade_phantom_arenas.py:apply_phase_environment`의 Phase1 분기가 재사용한다. 각 임시값의 조정 기준은 원작 비교 화면처럼 어두운 성채의 면이 읽히고 넓은 흰/금색 번짐이 줄며 국소 불빛과 안개가 남는 것이다. native Shader와 원작 BBQ/film-pass의 수치 일치를 주장하지 않는다. 기존 surface MI의 원본 GlobalMetallic/Roughness/Specular, directional intensity의 이전 adapter, fog 단위 배율과 geometry는 변경하지 않았다.

불꽃의 원본 근거는 `CascadeCoreColorSources.json`이다. Small `FP_LVL_WBP_LightObj_001_fire_small`의 emitter `188`/LOD `46`/`ParticleModuleColor` export `87`, Medium `FP_LVL_WBP_LightObj_001_FIRE_medium`의 emitter `210`/LOD `79`/color export `102`에서 `Properties.StartColor.MinValueVec/MaxValueVec=(0.964706,1,0)`을 확인했다. source SHA는 각각 `4335d17856f0c9581245cff9de0082ad0fd92ae93ab6da99840e3249b076dce5`, `154968bf7bde084658d2e4eeb205ad74dc66a9e70e94ec657a289f879dbd4fd1`이다. native Emissive는 원본 `FT_Torchfire_02_red`/`FT_Torchfire_8x8_03_red` atlas RGB × 이 core StartColor × 기존 gain이다. 색 sampler, parent 2개, MI 2개, texture 2개만 저장했다. source texture JSON은 sRGB를 명시하지 않으므로 native `sRGB=true`/Default compression은 색 해석 선택으로 기록한다. compression 변경이 sRGB를 재설정하는 것을 readback 검사에서 발견해 compression 이후 sRGB를 적용하고 저장했다. full Cascade/material program의 복원은 아니다.

### 저장·재로드와 전환 검증

- Phase1→Phase2→Phase1 전환을 실행했다. 두 환경 및 3,220개 actor의 visibility/collision/마커 검증 실패 0. Phase2 point light 11개와 Phase2 PP 설정이 전환 전후 동일했다. source SkyLight intensity `1.25`가 Phase2에서 복원되고 Phase1으로 돌아오면 임시 `0.6`이 유지된다.
- Phase1 맵 저장 후 실제 World 교체 재로드를 실행했다. actor `14,522`, 임시 capture 없음, dirty map 없음. Phase1 local light 41개의 저장값과 PP 노출/bloom/FilmSlope, PlayerStart pose가 유지됐다. 관련 없는 사용자의 Dodge asset은 save-all 대상에 넣지 않았다.
- 재로드 후 geometry root `1,862`, child `515`, fog `7`, light `24`, foliage `7`/instance `3,218`, landscape `16`의 source 대응 실패 0. 추가 render 89개와 visibility/environment 검사도 실패 0. 배치 삭제·이동 또는 PlayerStart setter는 실행하지 않았다.
- 보고서: `Phase1LightReviewBefore/After`, `Phase1FireColorCorrection`, `CascadeCoreColorSources`, `LightReview_Phase2Regression`, `LightReview_ReloadVerification`, `LightReview_*Reloaded.json`. 최종 시각 검수: `Saved/ArtReviews/BladePhantom_20261001/Phase1_LightReview_Delivery.png`. source 원본/스크린샷/새 임시값을 구분하는 상세 source manifest도 같은 report 폴더에 보존한다.
- 작업 중 null material input 재귀 검사에서 에디터 충돌이 있었다. 연결되지 않은 pin의 `None`을 native MaterialEditingLibrary로 넘기지 않는 보호로 수정 검사를 완료했다. 재현 절차에서 null input을 그대로 재귀하지 않는다. 최종 적용 이후 저장·재로드/계약 검사가 통과했으며 C++ 빌드나 boss/캐릭터 PIE 완료를 주장하지 않는다.

`view('boss_phase_1')`는 Phase1 조명 정책과 함께 현재 editor session의 `r.VolumetricFog 1`을 켠다. project/scalability INI는 수정하지 않았다. 에디터를 새로 시작해 검수할 때는 위 전환 명령을 다시 실행하거나 Shadows 품질을 High 이상으로 설정한다. 이 session의 fog 활성화는 다른 표시 변형의 fog 렌더에도 적용될 수 있으나 Phase2 asset 값은 이번 수정 대상으로 변경하지 않았다. 환경 자동 전환/보스 gameplay는 계속 미구현이다.

이번 조명 전 백업은 `Saved/ArtBackups/StormPass_Phase1_LightReview_20261001`이며 검수 중 저장된 맵은 그 안의 `EditorSavedDuringReview`에 별도로 남았다. 사용자 변경을 전체 맵 백업으로 되돌리지 않는다.

## 2026-10-02 사용자 요청 — Phase1 옆에 Phase2 전장 분리 배치 완료

사용자가 두 전장을 나란히 두고 각각 마킹하는 편집 구성을 요청했다. 현재 작업 맵은 사용자가 이동한 `/Game/Maps/L_StormPass_Environment` (`Content/Maps/L_StormPass_Environment.umap`)이다. 이전 `_Art/.../Maps`의 작은 umap은 현행 맵으로 향하는 redirector이며 복원하거나 다시 이동하지 않았다. 위의 원본 동일 좌표/상호 배타 변형 설명은 source 사실로 보존한다. **현재 편집 배치는 그 방식 대신 Phase1과 Phase2를 물리적으로 분리해 동시에 표시한다.** 원작의 자동 전환이나 실제 원작 레벨 offset을 새로 확인한 결과는 아니다.

### 실제 변경과 사용 방법

- Phase1 성채와 사용자 PlayerStart는 유지했다. 기존 Phase2의 terrain·props·foliage·fog sheets·local lights·FX·참조 마커·카메라 등 1,120 actor를 world X `+20,390 cm` 평행 이동했다. Y/Z, 회전, scale 및 각 actor의 내부 상대 배치는 유지했다. Phase2 PP는 이동에 더해 foreground bounds를 포함하도록 기존 bounded brush 크기를 변경했다.
- 기존 주 마커 두 개를 `StormPass/01_BladePhantom/ArenaMarkers` 폴더에 모았다. Outliner에서 `ArenaReference`를 검색하면 아래 두 개를 찾을 수 있다. 선택 후 `F`로 해당 장소에 초점을 맞춘다. 기존 별도 Entry/BossSpawn/Cinema 참조와 ReviewCamera는 보존했다.

| 페이즈 | 주 마커 label | 현재 world 위치 (cm) |
|---|---|---|
| Phase1 성채 | `SP_BP_Phase1_ArenaReference_TargetPoint_Boss` | `(162650, 51600, 695)` |
| Phase2 숲/혈수 전장 | `SP_BP_Phase2_ArenaReference_TargetPoint_Boss` | `(183040, 51600, 695)` |

두 마커는 editor-only arena 참조점이다. 높이 `695 cm`는 원본 공통 TargetPoint의 Z이며 실제 바닥 높이/Player respawn capsule 위치로 확정한 값이 아니다. 기존 SourceMarkers의 진입/보스 spawn 표식과 구분한다. gameplay respawn·teleport·boss Ability는 연결하지 않았다.

기존 Output Log Python 명령은 계속 사용할 수 있다. 이제 `view('boss_phase_1')` / `view('boss_phase_2')`는 **두 전장을 함께 둔 채 해당 검수 카메라로 이동하고 마커를 선택한다.** route presentation의 `set_variant`도 분리 layout이 있으면 같은 경로를 사용한다. 과거처럼 한 전장을 숨기거나 shared 환경을 다른 페이즈로 교체하지 않는다.

```python
import unreal, runpy
from pathlib import Path
h = runpy.run_path(str(Path(unreal.Paths.project_dir()) / 'Scripts/StormPass/polish_blade_phantom_arenas.py'))
h['view']('boss_phase_2')  # Phase1은 boss_phase_1
```

### 이동 수치와 재질/조명 계약

자료는 `Content/_Art/Player/Environment/StormPass/Metadata/BladePhantom_SideBySide_20261002`에 저장했다. 배치 간격은 원작 값이 아닌 이번 편집용 계산/임시 설정이다.

| 분류 | 파일·field·원시 값 / 계산 | 단위·조건 |
|---|---|---|
| 현재 native 관측 | `ForegroundBoundsBefore.json:bounds[1].max[0]=168871.5353357`, `bounds[2].min[0]=151400`; `BoundsBefore.json` Phase1 bounded PP의 maxX `169790` | cm, 현재 복원 맵 world bbox. 먼 `_Background_` 산과 fog plane/editor icon은 배치용 foreground bounds에서 제외하되 scene에서 삭제하지 않음 |
| 임시 편집 간격 | `Layout.json:clearance_cm=2000`; helper `separate_arenas`의 한 곳에서 관리 | cm. 전장·bounded PP 사이 간섭을 줄이기 위해 어시스턴트가 고른 20 m 여유이며 원작 근거 미확인. 검증은 foreground/PP X 간격 및 blend 영역 비중첩 |
| 위 관측 기반 계산 | `dx=max(168871.5353357,169790)+2000-151400=20390`; `dy=dz=0` | cm, +X 평행 이동만 수행. source Phase2 streaming offset 확인값이 아님 |
| 원본 직접 값 | `StormPass_LandscapeComponents.json:levels[source_level=StormPass_Boss_Phase_2].components[*].root_transform`, source root export `154`: location `(138800,25800,100)`, scale `(100,100,5)` | cm/무차원. 원본 Landscape RootComponent |
| 원본 입력 기반 계산 | 분리 terrain material RootXY `(138800+20390,25800)=(159190,25800)` | cm. native shader `(WorldXY-RootXY)/RootScale`에서 geometry와 origin을 같은 양만큼 옮겨 weight UV 유지 |
| 원본 참조점 / 계산점 | `OriginalAnchors.json`, `StormPass_Spawn_Main01.json` export `833` TargetPoint_Boss, root `755`, `(162650,51600,695)`; Phase2는 이 값 + `(20390,0,0)` | cm. 원본 공통 arena reference와 이번 authoring 참조 위치의 구분 |

Phase2 landscape parent를 `.../Reconstructed/BladePhantomPolish/Landscape/M_SP_BP_Phase2Landscape_Separated`로 복제했다. fixed world-origin Constant2Vector 한 개를 변경하고 기존 landscape 16 component에 할당했다. 기존 `M_SP_Landscape_Boss`는 수정하지 않았다. foliage 7 batch/3,218 instance의 local transforms와 원본 재질 슬롯은 유지됐다.

양쪽 PP를 bounded/enabled 상태로 유지한다. Phase1 PP maxX `169790`, Phase2 PP minX `171790`으로 간격 `2000 cm`이며 기존 각 BlendRadius `100 cm`의 합보다 크다. source local light/FX의 값은 변경하지 않고 Phase2 render/light component의 lighting channel을 1로 분리했다. 기존 sun을 복제한 `SP_BP_Phase2_Sun`은 source WEP Phase2 `RelativeRotation`, FColor `(199,172,219,255)`, SpecularScale `0.025`를 적용하고 channel 1만 사용한다. Intensity `10 lux`는 이전 native adapter에서 유지한 값이며 원작 직렬화 Intensity 직접 확인값이 아니다. 두 번째 sun의 screen-space light shaft는 끈 native 선택이다.

**sky·height fog·간접 GI는 기존 Phase1 전역 환경을 공유한다.** 별도 원작 sky/fog 실행을 공간별로 완전히 분리한 renderer 구현은 아니며 Pawn lighting channel도 바꾸지 않았다. Phase1의 이전 밝기 수정 및 local light/PP 정책은 보존한다. 이 배치 작업을 원작 Phase2 렌더의 완전 일치로 표현하지 않는다.

### 전장 중심 충돌 바닥 보완

기존 중심 참조점의 complex Visibility trace 4개는 모두 미검출이었다(`GroundTracesApplied.json`). 원본 gameplay collision metadata가 검증된 것으로 간주하지 않고, 두 전장 혈수 core에 보이지 않는 native 지원 바닥을 각각 추가했다. 기존 actor/StaticMesh collision mode를 일괄 교체하지 않았다.

- 대상: `SP_BP_Phase1_CollisionFloor`, `SP_BP_Phase2_CollisionFloor`; 폴더 `StormPass/01_BladePhantom/Collision`.
- Engine `/Engine/BasicShapes/Cube`의 실제 bounds `(100,100,100) cm`를 읽어 크기를 계산했다. render visibility/cast shadow는 false, HiddenInGame true, `BlockAll`, `QueryAndPhysics`, Pawn channel `ECR_BLOCK`이다. editor-only가 아니므로 게임 충돌 지원 actor로 저장된다.
- 높이 출처는 현재 native 바닥 `SP_Prop_StormPass_Boss_Phase_1_896_HISM_WP_Base_Floor_001_500X500_a5`의 bbox: min `(162428.58,51315.004,69.00001)`, max `(162928.58,51815.004,89.00001) cm`. 원본 지형 collision 직렬화값과 구분한다. Phase1 주 마커 XY를 포함하는 타일 하나를 골랐으며 높은 진입/계단 타일은 배제했다.
- 계산: topZ `89.00001`, 두께 `maxZ-minZ=20`, centerZ `79.00001 cm`; XY는 보존된 water actor bbox 사용. Phase1 `SP_ChildProp_StormPass_Boss_Phase_1_02379_00076`은 `15000×10000 cm`, Phase2 `SP_ChildProp_StormPass_Boss_Phase_2_02538_00179`는 `9000×8250 cm`. scale은 이 크기를 engine cube bounds로 나눈 값이다.
- Phase1 flat floor 높이를 Phase2 blood-water core에도 적용한 것은 **이번 authoring의 명시적 근사/가정**이다. 원작 Phase2 collision 높이 직접 확인값은 아니다. 표식의 캡슐 배치 테스트에서 바닥 지지/시각 정합을 추가 확인하여 조정할 수 있다. 전체 외벽·진행 길·NavMesh·AI 이동 복원을 의미하지 않는다.

### 최종 검증과 보존

분리 layout 저장/World 교체 재로드 후 source geometry·추가 render·variant·environment 감사 실패 0이었다. root render 1,862, child 515, source light 24, fog sheet 7, foliage 7/3,218, landscape 16, 추가 render 89 및 기존 visibility/collision baseline 3,220을 확인했다. 기존 pose 13,402개 유지, 이동 pose 1,119개 일치, PP 한 개는 별도 크기 변경 검사 통과. 원본 actor 삭제 0.

지원 바닥 추가 후 다시 저장하고 실제 World를 교체해 재로드했다. 최종 actor `14522 → 14525`는 sun 1개와 지원 바닥 2개 추가다. 두 마커 위치, 양쪽 PP enabled/geometry 표시, landscape 16 material 할당, PlayerStart pose 보존 및 2 floor BlockAll 계약이 유지됐다. 중심/진입/보스 표식 4곳에서 단순/복합 Visibility trace 8/8 모두 해당 지원 바닥 Z `89.00001 cm`, normal +Z에 적중했다. 마지막 dirty map/content는 모두 없었다. **에디터 충돌 검사이며 실제 Character/AI PIE·pathfinding 완료로 기록하지 않는다.**

`LayoutAppliedAudit`, `SideBySide_*Applied/Reloaded`, `ReloadVerification`은 분리만 적용한 단계의 보고서다. 최종 지원 바닥까지 포함한 결과는 `GroundSupportApplied/Reloaded`와 `ReloadVerificationWithCollision`이다. 기존 Art 스크립트 3개의 Python syntax도 통과했다. 단일 Rider viewport screenshot은 `FSlateApplication::TakeScreenshot failed for viewport`로 저장되지 않았으므로 새 overview 이미지 검수 완료를 주장하지 않는다. 시점 계산만 `OverviewCamera.json`에 기록했다.

백업 `Saved/ArtBackups/StormPass_SideBySide_20261002`와 `BackupManifest.json`은 이번 배치 전 맵/metadata/도구를 보존한다. 게임 C++/Blueprint/전투 기능, HeinMach, 사용자 PlayerStart/삭제 메시를 이 작업에서 수정하지 않았다. 게임 빌드는 실행하지 않았다. source/native 자료와 최종 파일 hash는 `SideBySideSourceManifest.json`에 기록한다. 이전 map 백업을 통째로 덮어 사용자 변경을 되돌리지 않는다.
