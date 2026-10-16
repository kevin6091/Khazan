# Fab VFX 로컬 대조 및 프로젝트 반입

## 2026-10-12 — 요청 범위와 확인한 자료

이번 요청은 Art / Resource다. Router → Art 상태·파이프라인 규칙 → 기존 지식 인덱스 순으로 확인했다. 원작과 다른 고품질 VFX를 사용한다는 사용자 방침에 따라 `C:/Users/user/Desktop/VFX`의 로컬 Unreal Content를 지정한 Fab 상품과 대조하고 현재 Khazan 프로젝트에 반입한다. 공격·Ability·Notify·Cue 연결이나 기존 이펙트 교체는 이번 범위에 없다. 게임 C++/BP 로직 및 프로젝트 Config를 변경하지 않는다. 새 runtime 파일/class/component는 0개다.

기존 저장 report에는 이번 공급 폴더의 상품 대응표가 없어서 해당 폴더만 최초 조사했다. 결과는 `Metadata/FabVFX_20261012/LocalInventory.json`, `SourcePackageIndex.json`, `ListingMap.json`에 재사용 가능하게 저장했다. 전체 원작/FModel·프로젝트 Content를 다시 조사하지 않았다.

| 요청 상품 | 로컬 원본 | 현재 반입 상태 |
| --- | --- | --- |
| [Action-RPG Essentials VFX Pack V2.0](https://www.fab.com/listings/8bebe1ca-0d93-4495-8bed-c07851d92fe1) | 공급 폴더에서 대응 팩 미확인 | 미반입, 별도 다운로드 경로 필요 |
| [Dynamic Impact and Collision Effects Pack](https://www.fab.com/listings/d9a83197-8153-42cb-9dff-fca43c413b5d) | 공급 폴더에서 대응 팩 미확인 | 미반입, 별도 다운로드 경로 필요 |
| [Slash and Hit VFX](https://www.fab.com/listings/9d886fdb-8011-49e7-a10d-0d8897fe9dc2) | 공급 폴더에서 대응 팩 미확인 | 미반입, 별도 다운로드 경로 필요 |
| [4번째 링크, 상품명 미확인](https://www.fab.com/listings/de3c9ae3-ebfb-4702-8cc2-1c7c2608c0f4) | 상품 자체 조회 실패로 로컬 대응을 판정할 수 없음 | 미반입, 상품명/정상 URL 필요 |
| [Cursed Magic Niagara](https://www.fab.com/listings/83d31880-441c-424e-8d22-71d778cf2905) | `Unreal8/CursedMagicNiagara/Content/Cursed_Magic` | `/Game/Cursed_Magic`, 시스템 58개 |
| [Niagara VFX Bundle](https://www.fab.com/listings/ebcdf5fb-077c-46ac-be75-1393a7c699b6) | `Unreal8/Unreal8_Assets/Content/NiagaraVFXBundle` | `/Game/NiagaraVFXBundle`, 시스템 609개 |
| [ARPGVFXPack03](https://www.fab.com/listings/4ea54c1a-a334-4115-89ea-957aa6d3d4b0) | `Unreal8/Unreal8_Assets/Content/ARPGVFXPack03` | `/Game/ARPGVFXPack03`, 시스템 15개 |

로컬 원본 경로는 모두 위 VFX 공급 루트 기준 상대 경로다. 두 대응 원본 프로젝트의 `EngineAssociation`은 5.4이고 대상 설치 엔진은 `Engine/Build/Build.version`의 5.8.2다. Fab 현행 상품 버전과 로컬 다운로드 버전이 완전히 같다고 주장하지 않는다. Bundle의 Fab 표기 609개와 로컬 registry의 NiagaraSystem 609개는 일치한다. 나머지 상품 대응은 상품명·원본 프로젝트·폴더 및 실제 에셋 계층을 사용했다.

4번째 상품은 웹 조회가 실패했고 공개 페이지/API 요청도 HTTP 403이었다. computer-use 스킬을 참고한 브라우저 연결 시도 역시 사용 가능한 브라우저가 없었다. `FlaresEffect` 또는 다른 로컬 상품이라고 추측하지 않는다. 로컬 Epic Launcher Fab 캐시에서도 요청한 7개 ID에 해당하는 다운로드 경로를 찾지 못했다. 인증·구매·다운로드·타인의 앱 제어는 수행하지 않았다.

## 2026-10-12 — 실제 반입과 native 검증

원본 `/Game` 상대 경로를 유지해 hard/soft reference를 보존했다. 선택 팩 자체 3,188 package, Cursed 데모의 World Partition 외부 actor/object 110 package, 실제 참조를 추적해 공급 폴더에서 가져온 공용 Mannequin 59 package를 합쳐 3,357개를 반입했다. 총 크기는 5,017,846,876 byte다. 기존 대상 파일 충돌·덮어쓰기 0개다. 원본/대상 SHA-256은 Delivery와 최종 검증에 보존한다. 엔진 로드·컴파일 중 에셋을 재저장하지 않아 공급된 native package bytes를 유지한다.

공용 package는 `Content/Characters/Mannequins`에 있고 외부 actor/object는 `Content/__ExternalActors__/Cursed_Magic`, `Content/__ExternalObjects__/Cursed_Magic`에 있다. 참조를 깨뜨리는 임의 폴더 이동/이름 변경을 하지 않았다. 다른 공급 팩·AdvancedGlass·FlaresEffect·환경·전체 사운드 번들을 이 요청에 함께 반입하지 않았다.

`StageDependencies08/DependencyAudit.json`은 3,357/3,357 registry 등록과 모든 `/Game` hard package 의존성의 존재를 확인했다. `MainLoad02/AssetLoadAudit.json` 및 `Exit.json`은 현재 Khazan 프로젝트에서 public asset 3,247개 실제 로드, 외부 package 110개 등록, NiagaraSystem 682개, Material 376개/MI 1,120개, World 28개를 확인했고 load error 0·process exit 0이다. 머티리얼 수 376에는 공용 Mannequin material 1개가 포함된다.

초기 `StageDependencies01`은 이 UE 버전에 없는 `AssetData.get_soft_object_path()` 호출 때문에 실패했다. registry의 실제 package/asset 이름으로 object path를 구성해 수정했고 실패 report를 보존했다. 초기 `MainLoad01`은 에셋 로드 자체는 성공했지만 검사 프로세스가 GameFeatures를 켜지 않아 현재 AssetManager의 GameFeatureData 시작 ensure로 exit 1이었다. 검사 프로세스에만 `-EnablePlugins=GameFeatures`를 적용한 MainLoad02가 exit 0이다. 프로젝트 plugin/Config를 수정한 것은 아니다.

아래 5개 soft path는 공급된 원본에도 파일이 없다. 원본의 데모 Pose/Control Rig/Skeleton 미리보기 참조이며 원본값을 임의 대체하지 않았다. 전체 경로와 작성 에셋은 `StageDependencies08/DependencyAudit.json` 및 `FinalVerification.json`에 있다.

- `/Game/Characters/Heroes/Mannequin/Meshes/SKM_Manny`
- `/Game/Characters/Heroes/Mannequin/Meshes/SKM_Quinn`
- `/Game/Characters/Mannequins/Meshes/SKM_Quinn`
- `/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple`
- `/Game/Mannequin/Character/Mesh/SK_Mannequin_Female`

Cursed 데모에는 원본 legacy input의 Jump/Move/Look/Turn mapping 부재 경고와 복사된 RigVM private-memory import 경고가 있다. 데모 입력을 Khazan Config에 넣거나 데모 character를 게임 캐릭터로 적용하지 않았다. 에셋 로드 성공과 데모 플레이 가능 검증을 구분한다. 이 경고는 Niagara VFX의 로드 실패로 관측되지 않았으며 데모 실행의 완전 정상도 주장하지 않는다.

## 2026-10-12 — 마지막 확인과 남은 범위

반입 3팩의 Material 375개에 대해 별도 숨김 Main 실제 RHI 프로세스로 `MaterialEditingLibrary.recompile_material()`을 실행 중이다. 최신 결과는 `Metadata/FabVFX_20261012/MainShaders01/ShaderAudit.json` 및 `Exit.json`을 기준으로 읽는다. 이 절 작성 당시에는 진행 중이며 shader 완료/최종 원본·대상 SHA 확인은 하단 후속 절과 `FinalVerification.json`으로 확정한다.

7개 전체 완료가 아니다. 미확인 3팩의 로컬 경로와 4번째 상품명/정상 링크가 필요하다. async 질문으로 누락된 3팩의 경로를 요청했다. 자료가 추가되면 기존 `LocalInventory.json`/`SourcePackageIndex.json`을 재사용해 새 원본만 대조하고 새 package만 preflight/이관/검증한다. 완료한 3팩을 다시 반입하거나 기존 package를 덮어쓰지 않는다. 정확 재개 기록은 Art continuity 및 `Metadata/FabVFX_20261012/ResumeState.json`이다.

VFX별 실제 화면·입자 수명/소켓/사용자 파라미터·combat event 연결, 게임 통합 및 Shipping 성능은 별도 작업이다. 팩의 재생률/수명/크기/색/입자 수와 기존 gameplay 수치를 이번에 튜닝하지 않았다. 원작 일치 검증으로 기록하지 않는다.


## 2026-10-12T10:52:19.737884+09:00 — 확인된 3팩 최종 검증 완료 / 7개 전체 미완료

MainShaders01은 실제 D3D12/SM6·NVIDIA GeForce RTX 3060 Ti에서 팩 Material375개 전부 compile error0·pixel instruction 양수375/375·process exit0으로 완료했다. MainLoad02의 native public3247/external110/Niagara682/load error0/exit0과 함께 Scripts/Art/verify_fab_vfx_import_20261012.py가 원본 및 Main3357 파일의 SHA-256 동일성을 확인했고 Exit0으로 종료했다. 원본/대상 byte 변경0·기존 파일 덮어쓰기0·Source/Config/uproject 쓰기0·asset save0이며 보호 snapshot에서 동시 변경 관측도0이다. 최종 증거는 Metadata/FabVFX_20261012/FinalVerification.json과 ResumeState.json이다. 앞 절의 shader 진행 상태는 이 완료 결과로 대체한다.

확인된 3팩의 반입 검증은 완료됐다. 7개 전체 완료로 확대하지 않는다. 미확인 3팩의 별도 로컬 경로와 4번째 링크 상품명/정상 URL이 여전히 필요하다. 실제 화면/particle simulation/게임 연결/Shipping 성능 및 데모 입력·RigVM 경고 해결은 이번 완료 범위가 아니다. 공급 폴더의 구매 목록 PDF에 대한 GUID/URL 표적 검색에서도 4번째 상품을 식별할 정보를 확인하지 못했으며 전체 PDF 내용 확인으로 표현하지 않는다. 임시 검증 staging 삭제는 자동 검토가 policy block으로 거부해 실행되지 않았고 Saved/ArtStaging/FabVFX_20261012를 보존했다. Source/현재 Content/검증 report는 유지됐다.


## 2026-10-12T12:09:54.562710+09:00 — Fab7 후속: Assets 프로젝트의 4팩 확인·얕은 폴더 정리 준비

최신 사용자 요청은 4번째 상품을 Roar Spell VFX로 확정하고 VFX/Assets의 나머지4팩 반입 및 전체7팩의 얕은 폴더 정리를 직접 승인했다. 앞선 원본경로 유지/7개 미확인 기록 중 미래 작업 방침을 이 요청으로 대체한다. 현재 Source C:/Users/user/Desktop/VFX/Assets/Content에서 ARPGEssentials299/DynamicCollisionVFX136/SlashFX163/Roar_Spell_VFX14, 새 package612를 확인했다. Niagara는52/16/35/1=104, 기존682와 합계786이다. 공급 프로젝트 EngineAssociation5.4, 대상5.8.2이며 게임 Source/Config/asset gameplay hookup 변경 권한으로 확대하지 않는다.

정리 계획은 /Game/VFX/01_ARPGEssentials,02_DynamicImpact,03_SlashHit,04_RoarSpell,05_CursedMagic,06_NiagaraBundle,07_ARPG03과 실제 공용 의존성 _Shared다. NiagaraSystem은 각 pack root에 바로 두고 지원 에셋은 Materials/Textures/Meshes/Blueprints/Modules/Curves/Demo 한 단계에 모은다. visible folder depth는 Content 아래 최대3이다. duplicate basename552개에만 원래 효과군 또는 full-source-key hash 접미사를 붙여 이름 충돌을 막는다. World Partition 외부 패키지는 엔진이 관리한다.

기존 Main3357 bytes/SHA는 불변 Before 백업, 신규4팩과 기존3팩을 합친 InputManifest3969개/6,435,516,913byte가 임시 project Saved/ArtStaging/FabVFX_Complete_20261012에 있다. MainOwnership02는 outside referencers0/dirty0/Exit0이다. Main editor가 당시 PIE Play였지만 제어·종료하지 않았고 이후 사용자 editor 종료/connection 없음은 inventory로 확인됐다. 현재 Main Content 구조는 아직 바꾸지 않았다.

PilotRename의7개 대표(WorldPartition map 포함) 이동과 기본 value 비교는 passed였으나 기존 Cursed demo RigVM private import LoadErrors로 Exit1이었다. staging demo-only ControlRig9를 recompile_vm/compile_blueprint/save하여 graph model/node counts를 유지했고 RigRefresh01은 passed/Exit0이다. 전체 StageRename01 own PID28520/launcher session79726이 진행 중이다. 이후 일부 demo ABP AnimGraph 중복/material function editor-only 경고를 새 프로세스에서 확인할 필요가 있다. VFX 상태·로직·원본 수치를 새 튜닝으로 변경하지 않았다.

정확 재개: 먼저 Completion/StageRename01/{Launch,Exit}.json과 StageRename.json 및 Editor.log를 읽고 현재PID/args를 대조한다. 실행 중이면 중복 rename하지 않는다. 종료 후 성공 대상은 RenamePlan/새 object existence로 재실행을 건너뛴다. StageRename은 모든 public3859개를 이동해야 한다. 그 뒤 Scripts/Art/run_fab_vfx_fixup_20261012.py로 staging-only redirector fixup, audit_fab_vfx_organized_20261012.py로 fresh class/기본 value/old refs/missing hard refs 검사, 필요한 demo cache 보완과 실제RHI material 검증을 수행한다. 문제를 해결한 준비본만 Main에 전달하며 GameSource/Config/기존 map은 저장하지 않는다. Main publish·old path retire·fresh Main 검사·현재 metadata/docs는 아직 남아 있다.

재사용 evidence는 Metadata/FabVFX_20261012/Completion의 InputManifest/ListingMap/FolderMap/RenamePlan/LayoutSummary/PropertiesBefore/InputRegistry/MainOwnership/PilotRename/RigRefresh01 및 각 process receipt다. Input01 neutral GameFeatures rule 오류와 MainOwnership01의 없는 is_asset_loaded API 실패는 보존하고 Input02/Ownership02 성공이 대체한다. 원본4팩 재조사/기존3팩 broad reimport/옛 native DLL/다른 Source 전달을 반복하지 않는다.


## 2026-10-12T12:49:08.300308+09:00 — Fab7 얕은 구조 native 검증 통과 / 같은 renderer RHI 검사 중

대형 AssetTools batch의3859개 새 destination은 모두 저장됐으나 final call 이후 isolated PID28520 committed memory가68GB까지 늘어났고 source/Main 변경 없이 own process만 종료했다. 원본 및 Before는 유지했다. neutral staging과 Before의 작업용 복사본에 NTFS compression을 적용해 logical bytes를 보존했고 OS가 paging을 회수한 뒤 디스크 공간도 회복됐다. 새 native audit는25개마다 GC해 memory를 제한했다. StageAudit01 public3859/value7943/error0/hard missing0은 데모맵의 old GameMode reference1 때문에 failed였고, same class/new path를 맵에 다시 저장한 MapRef01 후 StageAudit02는 passed/Exit0/oldrefs0/redirectors0이다. 초기 batch에 나온 demo AnimGraph/material function LoadErrors는 이 fresh load에서는0이었다. 원본 preview soft path5의53 referencer는 별도 유지한다.

현재 current Main RendererSettings/Windows RHI section만 staging Config에 복사한 뒤 StageShaders02 own PID7932/launcher11114가 Material419 real D3D12/SM6 no-save compile을 진행한다. neutral renderer로 시작한 StageShaders01은 작업별 renderer 일치를 위해 own process만 종료했고 초기 receipt를 보존했다. Main Config/Source/기존 map은 변경0, native 검사로 준비본 class/field 보존을 확인했으며 Main publish는 아직 전이다.

정확 재개는 Completion/ResumeState.json이다. 먼저 StageShaders02/Launch·Exit와 StageShaders.json을 읽고 running이면 중복 launch하지 않는다. passed/Exit0 뒤 publish_fab_vfx_organized_20261012.py로 verified stage files를 동일 volume의 Main 새VFX namespace에 move하고 기존3팩3357 파일을 Retired archive로 move한다. source/target 절대경계 및 SHA가 각각 preflight되며 source/Main conflict가 있으면 반영하지 않는다. 이후 fresh MainAudit01/audit_fab_vfx_organized_20261012.py→verify_fab_vfx_completion_20261012.py→Art 정본/state/knowledge/continuity 최종 추가 순이다. 이미 이동한3859 asset의 일괄 rename/전체 original import를 반복하지 않는다.


## 2026-10-12T13:26:59.800787+09:00 — Fab VFX 7팩 반입·얕은 폴더 정리 완료

사용자 후속 지시대로 미반입 4팩을 `C:/Users/user/Desktop/VFX/Assets/Content`에서 확인하고 기존 3팩과 합쳐 Main에 반입·정리했다. 신규 원본은 `ARPGEssentials` 299 / `DynamicCollisionVFX` 136 / `SlashFX` 163 / `Roar_Spell_VFX` 14 package, NiagaraSystem은 52 / 16 / 35 / 1이다. 네 번째 Fab ID `de3c9ae3-ebfb-4702-8cc2-1c7c2608c0f4`의 상품명은 사용자 정정과 로컬 폴더 대조에 따른 **Roar Spell VFX**로 확정했다. 앞선 4팩 미확인·미반입 및 publish/shader 대기 기록은 이 완료 범위에서 대체한다. 이전 기록과 실패 증거는 삭제하지 않았다.

| 상품 | 현재 Unreal 경로 | NiagaraSystem |
| --- | --- | --- |
| Action-RPG Essentials VFX Pack V2.0 | `/Game/VFX/01_ARPGEssentials` | 52 |
| Dynamic Impact and Collision Effects Pack | `/Game/VFX/02_DynamicImpact` | 16 |
| Slash and Hit VFX | `/Game/VFX/03_SlashHit` | 35 |
| Roar Spell VFX | `/Game/VFX/04_RoarSpell` | 1 |
| Cursed Magic Niagara | `/Game/VFX/05_CursedMagic` | 58 |
| Niagara VFX Bundle | `/Game/VFX/06_NiagaraBundle` | 609 |
| ARPGVFXPack03 | `/Game/VFX/07_ARPG03` | 15 |

각 팩의 NiagaraSystem은 pack root 바로 아래에 있다. 지원 에셋은 `Materials`, `Textures`, `Meshes`, `Blueprints`, `Modules`, `Curves`, `Demo` 한 단계로 모았다. 실제 참조된 공통 Mannequin 지원 에셋 59개는 `/Game/VFX/_Shared`에 있다. 보이는 폴더 깊이는 Content 아래 최대 3단계다. 같은 pack 내 basename 충돌 552개에만 기존 효과군 접미사 또는 필요한 source-key hash를 붙였다. 원본→새 object path 정본은 `Completion/RenamePlan.json`이며 디렉터리 이름만 바꾸어 참조를 깨뜨린 방식이 아니다. World Partition 숨김 패키지의 해시 디렉터리는 엔진 관리 영역이다.

Main 최종 파일은 **3,969개 / 5,132,230,561 byte**다. public asset 3,859개와 Cursed 데모의 외부 actor 103 / object 7개를 포함한다. `MainAudit02`는 public 3,859개의 실제 load/class, 설정 비교 7,943건, old reference 0 / missing hard reference 0 / redirector 0 / load error 0을 확인하고 Exit 0으로 종료했다. 총 NiagaraSystem 786, World 33, Material 419, MaterialInstanceConstant 1,246이다. Niagara fixed bounds/warmup, Material blend/양면/shading/clip, Texture sRGB/compression/LOD, AnimSequence timing/root 설정은 기록된 공급 에셋 값과 같다. 원작 게임 수치나 새 gameplay 튜닝으로 표현하지 않는다.

`StageShaders02`는 Main의 RendererSettings 및 Windows RHI 설정을 복사한 격리 프로젝트에서 실제 D3D12/SM6로 Material 419개를 no-save 재컴파일했다. compile error 0, 양수 shader instruction 통계 419/419, Exit 0이다. 최종 verifier는 해당 renderer 두 section의 현재 Main 일치 및 이 검증 이후 Material bytes 변경 0도 확인했다. 전체 particle 화면/시뮬레이션, gameplay 연결, 원작 일치 및 Shipping 성능까지 검증했다는 의미는 아니다.

일반 AssetTools 이동에서 Cursed 데모의 unloaded 외부 actor가 빠진 것을 마지막 점검에서 확인하고, 원본 맵과 외부 package를 작업용 staging에 복원한 뒤 [Epic WorldPartitionRenameDuplicateBuilder](https://dev.epicgames.com/documentation/ko-kr/unreal-engine/world-partition-builder-commandlet-reference)의 duplicate mode로 보완했다. `WPBuilder02`는 Exit 0이다. `WPStageAudit05`와 Main 최종 WP 감사는 외부 actor 103 / object 7의 등록·새 참조·파일 존재 및 원본/이동 맵의 actor 103개 실제 load를 확인했다. 위치·회전·scale·실제 actor class·Niagara 선택은 정확히 같다. 저장 시 엔진이 갱신한 editor descriptor bounds 35건과 Blueprint class 경로 해석 51건은 `WPDescriptorDifferences.json` 및 `MainWPDemoAudit.json`에 분리했다. 이를 공급 원본과 동일한 raw descriptor bytes라고 표현하지 않는다. 원본/이동 맵 load에서 동일 GUID·값의 transient WorldDataLayers 사본이 관측됐지만 디스크 actor package·descriptor는 103개로 중복 없이 대응한다.

Main 전달된 3,969개는 최종 publish receipt의 SHA와 일치한다. 처음 반입했던 3팩 3,357개의 bytes는 `Completion/Before` 및 `Completion/Retired/Content`에 보존했고 retired SHA를 재확인했다. 보완 전 task-owned 맵/외부 package 9개는 `WPBeforeMain`에 별도 보존했다. 삭제한 것은 retired 파일이 있던 **이미 빈 디렉터리만**이다. 공급 원본 VFX, 기존 gameplay 에셋/맵, Source, Config, uproject를 이 작업이 수정하지 않았다. snapshot 대비 Source 10개의 동시 외부 변경이 관측되어 FinalVerification에 분리 기록했으며 이전 Source를 복원하거나 전달하지 않았다. `KZGameplayTags.cpp` 및 Ability/Cue/Notify 연결 변경은 0이다.

앞선 bulk rename의 committed memory 68GB 문제는 작업용 프로세스만 종료하고 저장된 목적지에서 재개했다. 최종 검사는 25개마다 GC하여 완료했다. demo-only ControlRig 9개의 generated RigVM cache는 graph model/node 수를 유지하며 재컴파일했고 fresh Main load에는 오류가 없다. 공급 원본에도 없는 editor preview mesh soft path 5개(53 referencer)와 데모 legacy input 경고는 그대로 별도 기록한다. 새로운 hard dependency 누락이나 Niagara 반입 실패로 기록하지 않는다.

현재 정본은 `Metadata/FabVFX_20261012/Completion/FinalVerification.json`, `ResumeState.json`, `LibraryOverview.md`다. 이전 `Metadata/FabVFX_20261012/FinalVerification.json`은 최초 3팩 원본 경로 반입의 역사 증거다. 다시 전체 inventory/반입/rename/RHI compile을 시작하지 않는다. 후속 선택은 `Completion/ListingMap.json` → `LibraryOverview.md`/`RenamePlan.json` → 필요한 효과만 확인한다. 요청된 반입·정리의 남은 필수 작업은 0이다.


## 2026-10-12T13:28:50.418609+09:00 — Fab7 현재 열린 Main 에디터 표시 확인

RiderLink의 현재 Main PID16504에서 read-only registry 조회로 7팩 root의 NiagaraSystem 52/16/35/1/58/609/15 및 public asset 3859를 확인했다. 강제 rescan/asset save/map save/맵 전환/PIE 제어는 0이다. 현재 열린 에디터에서도 `/Game/VFX` 라이브러리를 바로 조회할 수 있다. 증거는 `Metadata/FabVFX_20261012/Completion/LiveEditorAvailability.json`이다. 7팩 반입·정리는 complete/남은 필수 작업0을 유지한다.
