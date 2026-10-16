# DualAxeSword 전투·혈흔·눈/먼지 이펙트 추출 및 UE 임포트

## 2026-10-06 — 범위와 원본 보존

사용자의 직접 요청으로 DualAxeSword 휘두름·공격 접촉·가드·직전 가드/패링·피격·혈흔과 Player/Monster 발자국·대시·지면 타격의 눈/먼지 효과를 추출했다. 결과 폴더는 프로젝트의 기존 Art 루트에 맞춘 `/Game/_Art/Effects` (`Content/_Art/Effects`)다. 이 작업은 Art 에셋·추출/임포트 스크립트·메타데이터에 한정한다. 게임 Source/BP/애니메이션 Notify/기존 맵을 수정하거나 효과를 gameplay 이벤트에 연결하지 않았다. 라이브 사용자 에디터/PIE를 조작하지 않았다.

기존 Art 지식·FModel export metadata를 출발점으로 관련 package index와 명시적 참조를 따라갔다. 게임 전체 리소스를 추출한 작업이 아니다. 요청 효과 root는 814개: Cascade 751, Niagara 21, decal material/curve 42. 해당 root의 텍스처·재질·메시·함수·커브·vector field 등 시각 의존성을 닫은 집합은 **2,313개 패키지**다. Cascade 안의 하위 emitter/module 객체 수를 별도 에셋 수처럼 합산하지 않는다.

원본 연결 자료는 **733개 패키지**다. DualAxeSword AnimComposite/Montage/Sequence 및 PhysicsData/PhysicalMaterial JSON에서 **4,146개 effect notify**, **3,426개 routing entry**, **16개 physical material 계약**을 기록했다. 이 수량은 각각 원본 export/entry의 수이며 독립적으로 실행할 효과 수가 아니다. 시각 패키지와 binding 패키지는 일부 겹치므로 두 집합을 단순 합산해 고유 원본 수라고 표현하지 않는다.

FModel의 현재 로컬 설정(GameDirectory/AES)을 사용한 기존 `EnemyExtractor.exe`/CUE4Parse 1.2.2.202609 backend로 표적 추출했다. parsing contract는 `GAME_UE4_27`, `DesktopMobile`. 원작의 실제 표시 build/patch 번호는 미확인이다. AES 값은 보고서/로그에 출력하지 않았다.

| 자료 | 경로 | 내용 |
| --- | --- | --- |
| 지속 manifest | `Content/_Art/Effects/Metadata/Extraction_20261006/AssetManifest.json` | 정확한 원본 package/type, JSON 경로·SHA256, native 목적지, root 여부 |
| 시각 원본 JSON | 같은 폴더의 `Source/BBQ/...` | 2,313개 원본 package metadata |
| 연결 원본 JSON | 같은 폴더의 `Bindings/Source/BBQ/...` | 733개 원본 binding package metadata |
| 참조 간선 | `DependencyEdges.json` | export 이름, 정확한 field, target package. Properties 밖 CachedExpressionData도 포함 |
| 애니메이션 효과 | `AnimationEffectNotifies.json` | 원본 Notifies index, LinkValue/Duration/EndLink, notify 객체/타입/필드 |
| 표면/피해 선택 | `EffectRoutingContracts.json`, `PhysicalSurfaceContracts.json` | 원본 entry 전체, 공격/피해/가드/표면 조건 및 참조 |
| 원본 cooked 시각 패키지 | `Saved/Extracted/CombatEffects_20261006/OriginalRaw/BBQ/...` | 2,313개 `.uasset/.uexp/...`, raw export 실패 0 |
| 원본 cooked binding 패키지 | 같은 추출 폴더의 `OriginalBindingRaw/BBQ/...` | 733개, raw export 실패 0 |
| 교환 payload | 같은 추출 폴더의 `Payload/BBQ/...` | texture/StaticMesh 600 package, 변환 export 실패 0, PSKX 모든 export LOD 보존 |
| 재구성 경계 | `SourceOnlyAssets.json`, `Recovery/Cascade/*.json` | native 미생성 원본 및 cooked table에서 유도한 editor distribution의 field별 계약 |

원작 UE4 cooked `.uasset`를 UE5의 Content에 직접 복사하지 않았다. `OriginalRaw`는 Content 밖에 보존하며 UE5 에셋은 엔진 factory로 별도 작성한다. 모든 작성 에셋은 `KZFXSourcePackage`, `KZFXSourceSHA256` metadata tag로 출처를 식별한다.

## 2026-10-06 — 폴더와 원본 사용 계약

| UE 폴더 | 용도 |
| --- | --- |
| `DualAxeSword/Core`, `Flow`, `Yaksha`, `Enchant` | DAS 전용 휘두름·스킬·흐름/야차·속성 효과 |
| `Combat/GuardParry` | Guard/JustGuard/Parry 및 관련 접촉 효과 |
| `Combat/AttackContact`, `Blood`, `HitReaction`, `Shared` | 타격·혈액/혈흔·피격·공통 피드백 |
| `Movement/DeepSnow`, `IceSnow`, `Snow`, `Grass`, `Dust` 아래 `Player/Monsters` | 표면별 발자국/대시/슬래시/스매시/착지 효과 |
| `Movement/Monsters/<원본 이름>` | Yetuga·Apes 등 원본에서 참조한 몬스터 접촉 효과 |
| `Shared/Textures`, `Materials`, `Meshes`, `VectorFields`, `Data` | 재사용 시각 의존성. 가능한 원본 VFX 하위 디렉터리 유지 |
| `Metadata/Extraction_20261006` | 원본 및 복원/검증 보고서 |

폴더명은 이번 정리의 분류다. effect 이름만으로 “이것이 패링 성공 때 실행된다”와 같은 조건을 확정하지 않는다. 아래 원본 field와 catalog가 실행 조건의 근거다.

- `.../PhysicsData/PA_Dmg/PP_Damage_Spray`: `ItemList[6].Data`가 `PP_AtkEx_Guard`, 해당 공격 강도 조건이 `NewDefense`. `[7]`은 `PP_AtkEx_JustGuard`/`NewJustGuard`, `[69]`은 동일 effect의 `EnhancedJustGuard` 조건이다. exact property 구조와 추가 attach/detach 설정은 routing catalog의 raw entry를 따른다.
- `.../PhysicsData/PA_Attack/PA_Attack_Slash`: `ItemList`/`NewExtraData`의 `NewParrying` 분기에서 `PP_AtkEx_Parry`를 참조한다. Guard와 Parry를 하나의 새 gameplay 조건으로 합치지 않았다.
- `.../PhysicsData/.../PP_Battle_FX_Composition`: attacker particle, damager spray/bleed, environment/skin decal, damage base 및 trail 계약을 함께 보존한다. 피격 결과의 실행 주체나 원작 runtime 코드까지 확인한 것은 아니다.
- `PA_World_PC_footstep_dash_normal.EffectList`: `Default`는 default dash, `SurfaceType10/4`는 IceSnow dash, `SurfaceType13`은 DeepSnow dash, `SurfaceType8`은 Grass 분기다. `PM_DeepSnow.SurfaceType=SurfaceType13`, `PM_Snow=SurfaceType10`, `PM_Dirt=SurfaceType7`은 원본 physical material의 직접 확인값이다. 표면 번호를 현재 프로젝트의 이름/충돌 설정에 새로 연결하지 않았다.
- `AC_Kazan_DualAxeSword_Com_WeakAtk01` 등의 socket, offset/scale, notify duration, `bOnAttackSuccessed`, `KillOnNotifyEnd`, DilationCurve 및 compiled notify particle info는 원본 JSON에 보존했다. 현재 InGame retime/몽타주에 이 시간을 그대로 이식하지 않았다.

사용할 에셋은 catalog의 원본 참조 → manifest의 native destination 순서로 찾는다. 나중에 gameplay 연결을 요청받으면 실제 현재 Source/BP/애니메이션의 소유자·시간축·소켓·수명/취소 계약을 따로 확인한다.

## 2026-10-06 — native 복원 방법과 한계

native 대상 수량은 **2,028개**다. 최종 저장본의 실제 검증 결과는 아래 날짜별 후속 절과 `FreshSavedAssetAudit.json`을 우선한다.

| 종류 | native 대상 |
| --- | ---: |
| Cascade ParticleSystem | 751 |
| Texture2D / TextureCube | 510 / 2 |
| StaticMesh | 88 |
| Material / MaterialInstanceConstant | 109 / 522 |
| VectorFieldStatic | 17 |
| CurveFloat / CurveLinearColor / CurveLinearColorAtlas | 1 / 9 / 9 |
| MaterialParameterCollection | 4 |
| TextureRenderTarget2D / PhysicalMaterial | 5 / 1 |

**Cascade**: 원본 emitter/LOD/module graph와 직렬화 필드·참조·cooked distribution table을 가져왔다. CPU cooked table이 있어도 UE editor GPU compilation은 `Distribution` UObject를 요구한다. 제거된 editor object는 원본 table에서 native Constant/Uniform/Curve distribution으로 유도했다. source table `TimeBias=b`, `TimeScale=s`, sample index `i`의 입력은 `t_i=b+i/s`. 원본 lookup의 선형 보간과 끝 clamp에 맞춰 `CIM_Linear` key를 작성한다. 벡터 축 lock, random/extreme operation을 유지한다. **80,841개 editor distribution**은 원작 editor keyframe의 직접 복원이 아니라 cooked sample 기반 계산 결과다. CPU table은 함께 보존하며 GPU의 UE5 재컴파일/재샘플링과 shader 구현 차이는 원작 동일성 검증과 구분한다.

원작 전용 클래스는 `xxParticleModuleMeshMaterialOverride → ParticleModuleMeshMaterial` 2개, `xxDtbVectorParticleParameter → DistributionVectorParticleParameter` 1개에 한해 native adapter를 사용했다. 원래 `OverrideName` 같은 전용 runtime 계약은 JSON에 남아 있고 native 클래스에 동일 로직이 있다고 주장하지 않는다. 무기 runtime material 제공·소켓/owner parameter 공급·원작 전용 renderer를 이 작업에서 구현하지 않았다.

**재질**: 원본의 `CachedExpressionData`가 Properties 밖에 있으므로 별도로 읽어 기본 scalar/vector/texture parameter를 가져오고 MI parent/override를 복원했다. native shader graph는 source texture·tint·emissive/opacity·명시적 UV pan/SubUV 계약으로 만든 복원용 graph다. Blood decal의 원본 `MD_DeferredDecal`을 유지한다. source 표현식 연결, distortion/refraction, dissolve, VAT deformation, dynamic material 조합 및 원작 custom rendering의 완전 복원이 아니다. texture compression에 맞는 sampler type은 UE5 `MaterialExpressionUtils::GetSamplerTypeForTexture` 기술 계약을 따른다.

**텍스처**: PNG/HDR 일반 payload 외에 PF_FloatRGBA Texture2D **15개**는 원본 inline bulk의 RGBA half bits를 EXR로 보존했다. 재조립한 RGBA SHA256을 original payload와 비교했다. PF_FloatRGBA cubemap **1개**는 6 faces의 half bits/원본 순서를 DDS에 보존해 tiny HDR decoder 실패와 alpha 손실을 피했다. 다른 cube는 FModel HDR 교환 payload로 임포트했다. `PrecisionTextureExtraction.json`, `PrecisionCubeExtraction.json`의 원본·offset·크기·hash를 따른다.

**Vector field**: 17개 모두 원본 inline FFloat16Color RGB와 dimensions/bounds를 FGA XYZ로 변환했다. alpha=0 확인, 순서·부호·배율 변경 없음. `VectorFieldExtraction.json` 참조.

**Curve/MPC**: 원본 curve key/tangent를 native 커브에 옮겼다. CurveLinearColor 고정 배열은 임시 unsaved T3D actor에서 가져온 curve UObject만 duplicate하여 작성했다. scratch map/actor는 저장하지 않았다. atlas/MPC 참조와 원본 파라미터도 보존했다.

**StaticMesh**: ActorX importer의 `None` material-token 오류를 피하기 위해 import staging의 MATT0000 이름만 바꿨다. 정점/면/UV bytes를 이 회피에서 변경하지 않았다. native 재질 및 원본 material slot 이름을 이후 복원했다. native geometry는 export LOD0, 원본 다른 LOD PSKX는 payload에 보존한다. 원작 VAT shader 없는 메시의 deformation이나 최종 original tangent/shading 동일성까지 완료한 것으로 보지 않는다.

**Render target**: 원본 크기/format/clear color/address/mip 설정을 가진 native buffer asset 5개를 만들었다. 원작 runtime writer와 플레이 중 생성되는 buffer 내용은 미구현이다. asset 생성과 그 시스템의 복원은 다르다.

**source-only**: NiagaraSystem **21개**, MaterialFunction **264개**의 raw/JSON을 모두 보존했다. 함수 264개는 export가 MaterialFunction root 하나씩이며 expression graph export가 없다. Niagara도 원작 editor graph/GPU HLSL source가 없고 UE4 compiled VM/schema를 UE5에 그대로 이식할 수 없다. 빈 native 에셋을 만들어 임포트 완료로 표시하지 않았다. Niagara 목록에는 `FP_BloodSplit_*`, `FP_Dmg_Blood_Base*`, DAS dissolve/buff/afterimage 등이 포함되므로 **요청 효과 전부의 재생 복원을 완료한 상태가 아니다.**

## 2026-10-06 — 검사 중 발견한 문제와 재개 기준

- 별도 UE process에서 `FP_BloodBleed_001` 저장본 로드가 null access violation을 일으켰다. Rider native dump session의 paused frame에서 `rcx=0`, `[rcx+0x10]` 접근 실패를 확인했다. 엔진 PDB가 없어 해당 frame에서 원본 변수 이름/소스 라인을 직접 검사하지 못했다. 원본의 null Distribution 및 UE5 `ParticleModules_Color.cpp` GPU CompileModule 경로를 대조해 위 editor distribution 복원을 적용했고 Blood의 새 process reload가 성공했다. dump session은 종료했고 사용자 breakpoints를 변경하지 않았다. 사용한 skill: [debugging-code SKILL.md](C:/Users/user/AppData/Local/JetBrains/Rider2026.2/aia/agents/views/codex/.agents/skills/debugging-code/SKILL.md).
- 앞서 이 작업이 생성한 Cascade 49개만 source metadata의 소유권을 byte 검사한 뒤 SHA256 backup을 만들고 재작성했다. `Saved/ArtBackups/CombatEffects_20261006/Cascade_before_editor_distribution_repair/BackupManifest.json`. 다른 기존/사용자 에셋을 삭제하거나 복구용 old byte를 현행 파일에 덮지 않는다.
- typed visual reference closure로 원본 월드 ice material과 그 의존성을 추가했다. RequiredModule의 material 참조 6개/3 particle을 복구했다. `Import_rebind.json`; 최초 `Import_particles.json`의 reference_not_loaded 6개는 이 후속 결과와 구분한다.
- direct SETNOPEC FName의 따옴표 포함 문제를 Source field와 비교하여 수정했다. nested struct의 delimited FName과 direct FName 표현을 구분한다. `Import_names.json`. runtime parameter/emitter 이름을 source와 다시 검사한다.
- 실제 RHI 검사에서 TC_Alpha texture의 LinearColor sampler 오류를 찾아 해당 source 소유의 2 material/3 node를 Alpha sampler로 교정했다. `Import_samplers.json`. 단순 process exit 0만으로 shader/렌더 검사 성공을 판단하지 않는다.
- 자동 HDR cubemap 오분류는 child process의 TextureImporter 설정과 정확한 EXR로, tiny RGBA16F cube는 exact DDS로 처리했다. 다른 세션 Build.bat lock을 기다리는 import는 child 환경의 `UE_SKIP_UBT_SDK_SETUP=1`로 SDK discovery만 건너뛰었다. 현재 프로젝트 Config나 사용자 build를 바꾸지 않았다. shader QA는 child process에서 XGEController를 disable하여 로컬 worker를 사용한다.

재개는 Router → Art 상태/이 문서 → manifest/catalog/최신 reports 순서다. Python은 `C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe`, helper는 `Scripts/Art/run_combat_effects_background.py`다. 이미 완료한 전체 추출/임포트 단계를 반복하지 말고 실패한 필드/에셋만 확인한다. 검사 명령은 `... run_combat_effects_background.py audit`, `compile --render`, `preview --render`. 검수에는 task-owned hidden process만 사용한다. `DEBUG RESETLOADERS`, live reload/Save All/사용자 PIE 종료를 재사용하지 않는다.

Source-only Niagara의 후속 복원에는 원작 editor graph/HLSL 또는 동등한 editable source가 필요하다. 그것을 확보할 수 없다면 원본 compiled metadata·원작 화면/동작을 근거로 effects를 별도 native Niagara로 재제작하고 차이를 검증하는 후속 작업으로 진행한다. 이번 raw/JSON을 UE5 Content에 옮겨 이름만 같은 새 system을 만들지 않는다.

## 2026-10-06 — 최종 저장본·재생 검사와 미복원 범위

**요청 범위의 원본 추출·보존 및 지원하는 native 에셋 작성/검증을 마쳤다. 원작 효과 전부의 동일한 재생 복원은 미완료다.** `DeliveryVerification.json` passed가 이 작업의 마지막 디스크 검증이다. 과거 진행 체크포인트의 2,175개 의존성/13개 float texture 및 material stage 대기 상태는 현재 2,313개/15개 및 아래 결과로 대체한다.

- native `.uasset` **2,028개**, 예상 목록 외 파일 0. Cascade 751개, emitter 4,518개, LOD 5,608개. 모든 에셋을 새 process에서 로드하고 class·출처·원본 emitter/LOD/module 수·required material·FName·mesh material/slot 참조를 대조했다. Material 109개 기본 scalar/vector/texture와 MI 522개 parent 및 scalar/vector/texture override 배열을 원본과 대조했다. 마지막 2,028개 파일 SHA256이 audit와 동일하다.
- raw 시각 패키지 **2,313개/5,070파일**, raw binding **733개/1,466파일**, 교환 payload **600개/601파일** 모두 존재·비어 있지 않음·export 실패 0. 지속 source JSON 2,313개와 source manifest의 SHA256 일치. 원본 cooked 파일은 계속 Content 밖에 있다.
- native raw distribution table **80,874개**의 활성 entry count/stride/value 배열 범위와 source shape를 검사했다. source shape 차이 0. `EntryCount=0`인 비활성 table은 엔진 `Empty()`가 남긴 value allocation과 구분한다. `PP_Dmg_Water_Blood`의 GPU `EmitterInfo` 5필드는 Python protected getter로 읽을 수 없었으며 이 내부 compiled field까지 검증했다고 주장하지 않는다. 일반 원본 module distribution 검사와 실제 GPU 대표 재생을 구분한다.
- 색상 커브 9개의 원본 key **117개**를 native `get_unadjusted_linear_color_value()`로 평가해 해당 채널의 source 값을 비교했다. editor key/tangent는 source T3D로 이관했지만 모든 중간 시간의 곡선/원작 화면까지 전수 검증한 것은 아니다.
- `ShaderVerification.json`: 실제 RHI에서 master material **109개 모두 compile errors 0**, pixel/vertex instruction 양수. 셰이더 컴파일 통과는 제거된 원작 표현식 그래프의 복원 증명이 아니다.
- `RepresentativeEffectRendering.json`: 별도 hidden process의 unsaved blank PIE에서 **9개 대표 효과를 재생·캡처**, process exit 0/marker passed. Guard, JustGuard, Parry, `FP_BloodBleed_001`, DAS FatalbloodEX slash, PC DeepSnow normal footstep/dash/Smash, Monster L DeepSnow dash다. **45 PNG**는 `Saved/ImportReports/CombatEffects_20261006/Preview`에 있다. 마지막 Guard/JustGuard 근접 frame 2의 황금 섬광/밝은 궤적과 Parry·blood·DAS slash·눈 입자 이미지를 실제 열어 확인했다. 751개 모두의 전체 수명·충돌·소켓·원작 동일성 검사를 한 것은 아니다.

검수 카메라 거리(guard 계열 150cm, 나머지 fit 300–800cm), 1280×720, 노출 1, 30FPS cap, 캡처 frame 1/2/4/8/16은 **검수용 기술 설정**이다. 원작 gameplay 카메라·속도·전이·효과 수치로 사용하지 않는다. 최초 먼 카메라의 검은 Guard 캡처를 원작 효과가 없다는 근거로 사용하지 않는다. 해당 camera만 가까이 옮긴 마지막 이미지에서 가시성을 확인했고 에셋 크기나 원본 수치를 키우지 않았다. 이미지는 독립 SceneCapture 검수이며 실제 플레이어 전투 화면/원작 비교 사진이 아니다.

### 후속 수정의 실제 내용

가드 runtime에서 `93 into an array of size 93` assertion이 발생했다. 새 process의 native readback에서 `ColorScaleOverLife` table이 source 32×3=96개인데 93개였고, `AlphaScaleOverLife`도 source 128개 대신 127개였음을 확인했다. 소스 마지막 작은 값의 `e-05` 표기 다음 원소들이 잘렸다. 로컬 UE5.8 `CoreUObject/Private/UObject/PropertyNumeric.cpp`의 `FNumericProperty::ImportText_Internal`은 float 문자열 포인터를 숫자/부호/소수점/f까지만 전진시키며 exponent를 전진시키지 않는다. `PropertyArray.cpp`는 잘린 import에서 배열을 부분 변경한 채 반환할 수 있다.

`text()`를 유한 float의 **일반 소수 표기**로 바꾸었다. 숫자를 튜닝/반올림해서 바꾼 것이 아니라 같은 source JSON 값을 전달하는 형식의 수정이다. source 기준 337 ParticleSystem의 **750필드**, source table에서 유도한 editor distribution의 **640필드**를 다시 가져왔다. 고정 배열 색상 커브 9개와 atlas 참조도 재검사했다. `GuardDistributionReadback.json` 마지막 invalid 0 및 전체 table audit/대표 PIE 통과가 수정 결과다. Rider native dump는 throw 지점과 assertion을 확인하는 데 사용했으나 엔진 PDB가 없어 원인 frame의 명명된 변수/소스 라인을 debugger로 직접 확인하지 못했다. task-owned dump session은 종료했고 사용자 breakpoint/editor는 조작하지 않았다.

`Import_numeric.json`의 failed는 curve duplicate가 기존 경로를 unattended로 덮지 못한 **중간 단계 상태**다. 그 이전 particle/MI/mesh 저장 결과는 유지됐고, `Import_numericdata.json` completed에서 task-owned curve만 byte backup·참조 소유권 확인 후 재작성했다. scratch subobject에 강한 Python 참조를 유지해 GC에 사라지지 않게 했다. native 삭제 API가 원래 파일을 남긴 경우에도 backup과 byte가 같은 정확한 task 경로만 제거했다. 현재 모든 curve/atlas를 포함한 fresh audit가 통과했으므로 이 과거 실패를 현재 누락으로 해석하지 않는다.

초기 이름 충돌 정리 때 남아 있던 `External/BASE_Black`, `BASE_Disolve`, `BASE_SAPE` 3 texture 경로는 source별 최종 hash-suffix 목적지로 MI를 재연결한 뒤 정리했다. 기존 referencer가 있었을 때는 정리를 중단했고, 마지막에는 referencer 0·metadata 소유권·replacement·byte backup SHA256을 확인했다. `ObsoleteTextureCleanup.json` passed/3개 파일 부재, 현재 2,028개 예상 native만 존재한다. backup은 `Saved/ArtBackups/CombatEffects_20261006/BeforeDecimalRepair` 및 `ObsoleteTextureNames`. `GuardEffectiveMaterialParameters.json`에는 Guard 관련 MI 4개의 실제 effective parameter readback도 있다.

### 확정된 한계와 정확한 재개

**Niagara 21개와 MaterialFunction 264개는 원본 raw/JSON 추출 완료, native 편집/재생 복원 미완료**다. BloodSplit/Dmg_Blood_Base와 DAS dissolve/buff/afterimage가 이 목록에 있다. source-only raw를 UE5 Content에 복사하거나 이름만 같은 빈 에셋을 만들지 않았다. shader는 계속 source texture/parameter를 사용하는 recovery graph이며 distortion/refraction/dissolve/VAT와 원작 전용 renderer·3개 custom class의 runtime 특수 동작을 완전히 이식한 것이 아니다. 원작 runtime buffer writer, owner/socket parameter와 gameplay/surface routing 실행도 추가하지 않았다.

다음 작업은 Router → Art 최신 상태 → 이 마지막 절 → `DeliveryVerification`, `AssetManifest`, `SourceOnlyAssets`, 해당 binding catalog 순서로 시작한다. 완료한 전체 추출/임포트나 `numericdata`를 반복하지 않는다. native 목적지는 manifest에서 찾는다. 원작 Niagara/editor shader source를 확보할 수 있으면 21개/264개 중 실제 사용할 대상만 이어서 복원한다. 확보가 불가능하면 원작 metadata와 해당 효과의 원작 화면/동작을 근거로 좁은 범위의 native 재제작 및 차이 검증을 별도 진행한다. gameplay 연결은 현재 Source/BP/소켓/시간축·취소 수명 계약을 확인하는 별도 요청이다.

후속 수정 전 현재 대상 파일의 사용자 변경/새 SHA를 확인하고 새로운 backup을 만든다. 예전 byte backup이나 source metadata tag가 있다는 이유만으로 이후 사용자 편집을 덮지 않는다. 검사 runner는 `audit`, `compile --render`, `preview --render`; 결과 marker/report를 함께 읽는다. 이 작업의 Unreal 검사 process와 Rider dump session은 종료됐다. live reload/`DEBUG RESETLOADERS`/Save All/사용자 PIE 제어를 하지 않았다.


## 2026-10-08 ? ?? DAS ?? ?? ????source shader ?? ?? ??

?? ??? Player Data26 node/7 montage/32 sequence? ??24 original AC? `MappedOriginalEffectWindows.json`?? ??? direct/None-status/HeinMach-compatible surface ??66?? ???. ?? native ?? ?? Cascade?? ??0??. ? ?? Niagara? ? ?? ?? ?? ??? ???? ???. ?? Main effects2,028? SHA? ?? fresh audit? ?? ???? native2028? ?? ????????? ???. ?? ???/?? ???? `Saved/ImportReports/PlayerAttackVFX_20261008/ResourceAudit/CurrentAttackResourceSubset.json`, source table/shape/adapter ? ??? `ResourceAudit.json`? ???. Weak ? ?? ComStrong ??? ?? PA_StatusAttack_DualAxeSword None route? ?? FP_PlaneSlash_Base_001??. ?? Base_Strong ??? raw/JSON? ?? ????? ?? node?? ???? ?? native trial? ??? ???.

Cooked material/function graph? ??? ?? ??? ???? ??? ? ??. ?? native recovery? ParticleModuleParameterDynamic? source four-channel curves? ????? master shader?? DynamicParameter expression? ?? ???? ?? ?? ????. T_blade_test/Base_Dynamic_RGB/FM_meshoffset_A/FM_fluid_A/FM_blood_trail source DP4 ????? scalar/vector/texture/default ? source alpha255/RGB density PNG? ?? ????. Mask/dissolve/UV/distortion/tint? ? ??? source parameter ??? ?? **native ??**?? source stripped topology? ?? ??? ???.

Private AttackVFXWork?? master5?? ? graph? ???? RHI compile errors0/?? instructions? ????. Main native2028 ??? ??0, private ????5/?? native??0. `Saved/ImportReports/PlayerAttackVFX_20261008/ShaderRecovery_1497b20e61004bd3a1c00cc69b34f9e7/PostAuthorScope.json`? source SHA/?? native SHA/??/HLSL/compile stats? ????. Before ?? Cascade6?30 PNG? ????? ?? Slate callback?? ????/? map? ??? ? ????? RecursionError? process AV(exit3)? ? After? ??0??. ?? renderer ?? ??? ???? ???. Helper? IN_TICK guard? ????? ?? fresh After-only ??? native ability/weapon/level ?? ??? ?? ???. Main ??? editor/Source/asset ??? ???.

Decal50 ?? ????? missing MI2? Base_Decal_BottomCrack parent1, Texture3? ?? ????. ?? metadata/raw/decodedPNG? supplemental6 manifest? `ResourceAudit/DecalDependencyExtraction`? ?? ?? extraction manifest? ???? ???. Blood000/Linear000 PNG? ?? ??? ?? ?? RGB ???? 2?2 UV4frame ??? ??? PF_DXT1 alpha? opaque?. Random_Ch_Value0..3? RGB ?? ???3=maxRGB fallback? native ???? ????. Curve registry0 FadeOut/1 SlowIn/2 FastInSlowOut/3 Fast? exact original FloatCurve keyTime/interpolation/tangents/weighted-none/SHA? `DecalGPUPlan.json`? ????. Lifetime2/3/5/9/11?? source key domain0..3?? stretch?? `age*TimeScale/LifeSpan*lastKeyTime`? ?? caller ??? native ???? curve ? ??? ????? ???. GPU HLSL/author/floor QA helper? ???? ? ? ??? decal native author ?????.


## 2026-10-08 — DAS shader After 검사·Decal private author 체크포인트

직전 2026-10-08 감사 절은 문서 기록 과정의 인코딩 문제로 일부 한국어가 `?`로 저장됐다. 기존 기록은 보존하며 아래에 범위와 실제 결과를 다시 기록한다. CurrentAssets의 26 node/7 montage/32 sequence와 원작 24 AC의 실제 effect windows에서 선정한 native subset 66개는 모두 기존 Cascade이며 누락은 0이다. Weak와 현재 ComStrong은 같은 `FP_PlaneSlash_Base_001`을 사용한다. 인접 Base_Strong 후보는 raw/JSON만 보존했고 새 native trial은 만들지 않았다. 원작 cooked material/function의 editor expression graph는 제거되어 있으며, 추가 raw 추출로 그 연결을 확인했다고 주장하지 않는다.

실제 private 변경은 particle master 5개(`T_blade_test`, `Base_Dynamic_RGB`, `FM_meshoffset_A`, `FM_fluid_A`, `FM_blood_trail`)의 source DynamicParameter 채널·texture RGB mask·opacity/dissolve/UV/tint 연결과, Decal master 및 최소 의존성이다. 원작 parameter/default/MI override와 source DP field/curve는 근거가 있지만 graph 연결은 native 재구성이다. MaterialFunction/VAT dynamic-remeshing 및 원작 refraction/normal/scene-depth topology는 아직 복원하지 않았다.

Private After-only RHI PID16480은 normal exit0, 30PNG 저장, 검사 중 asset save0이었다. `ShaderRecovery_67a33441c953431ab20ffbfc6e2f6a00`에 receipt/log/PNG/tools를 보존한다. OverFury slash frame16의 붉은 면이 frame24에서는 찢어진 가는 혈흔 형상으로 바뀌어 DP dissolve 반응을 확인했다. 전체 수명 종료와 원작 화면 일치는 검증하지 않았다. BloodTrail은 frame16/24에서 active1/2지만 조명 없는 blank world PNG는 검게 남아 있어 렌더 완료로 판단하지 않는다. 밝은 바닥/DirectionalLight를 사용하는 후속 QA helper에 같은 blood ribbon 검사를 추가했다. Frame 번호는 Slate callback 순번이며 원작 시각의 절대 시간으로 환산하지 않는다.

Private Decal author PID17636은 normal exit0, receipt `passed_private_author`다. 기존 `Base_Blood_Decal` 1개를 변경하고 native 의존성 6개(new Crack master, MI2, Texture3)를 작성했다. 두 master의 compile errors는 0이지만 decal instruction counter0은 렌더 증거가 아니다. Source RGB packed mask와 Random_Ch_Value0..3을 R/G/B/maxRGB로 연속 선택하는 연결을 사용한다. 채널3=maxRGB는 DXT1 opaque A로 네모가 생기는 것을 피하는 native fallback이며 원작 graph 직접 확인값이 아니다. Source CurveFloat 4개의 raw key/time/interpolation/tangent를 GPU Hermite/linear/constant 계산에 보존했고, `age*TimeScale/LifeSpan*lastKeyTime`의 수명 정규화는 source life2/3/5/9/11초와 curve domain0..3초 관계에서 선택한 native 해석이다. 기존 consumer는 KZDecalCurveIndex=-1로 새 curve를 우회한다. 원작 모든 UV/noise/static topology가 재현됐다고 주장하지 않는다.

`ResourceAudit/ArtCandidateManifest.json`에 private 후보12개(기존변경6/새에셋6)의 Main-before/private-after SHA와 source 경로를 기록했다. Main 기존 native effects2,028개를 다시 hash한 결과 변경0이며 새로운6개도 Main에는 없다. Main 사용자 에디터/Source/Effects asset을 저장하거나 수정하지 않았다. 추가 process는 모두 종료했다. native build 성공 신호 뒤 `Scripts/Art/run_player_attack_vfx_decals.py --qa`를 private Work에서 실행하여 floor18PNG+lit blood3PNG의 mask 외곽·수명·mirror를 확인한다. actual ability/weapon/HeinMach placement는 별도의 native runtime QA이며 아직 이 standalone 검사로 확인하지 않았다.


<!-- PlayerAttackVFX_20261008_context_opacity_private_checkpoint -->
## 2026-10-08 — 실제 OverFury 불투명 면·먼지 네모 후속 private 수정

초기 standalone 검사는 원작 일치나 실제 공격 화면의 최종 통과가 아니었다. Root의 실제 native 공격18 node 검사가 실행·적중 조건을 통과한 뒤, `RuntimePIE/121_AM_DAS_Player_OverFury_OverFury.png`의 몽타주 약1.01초 화면에서 큰 검은 곡면과 불투명 먼지 네모를 발견했다. 따라서 이전 Art 후보12의 `passed_private_art_QA`는 제한된 floor/standalone 범위의 과거 기록이며 최종 전달 근거로 사용하지 않는다.

Source masked child와 translucent parent의 서로 다른 출력 계약을 native graph에서 확인했다. `FM_meshoffset_A`, `FM_fluid_A`, `FM_World_Fluid_A`에는 이미 존재하는 opacity density를 `OpacityMask`에도 연결했다. 앞의 두 master의 masked 경로는 scene depth를 읽는 translucent 전용 `DepthFade` 앞의 동일 density를 사용하며, 원래 translucent fade는 유지했다. Parent/child blend와 clip, source numeric parameter는 변경하지 않았다. 첫 Cmd PID29888은 세 파일을 저장한 뒤 WorldSubUV atlas 개수 guard에서 exit1이었으며, 저장된 세 파일과 실패 이력을 보존했다.

`FM_World_SubUV_color_A`, `FM_SubUV_color_A`의 native opacity dependency에는 `Tex_Opa`만 있었고 실제 grayscale 연기 모양인 `Tex_SubUV`는 빠져 있었다. Source texture payload의 alpha는255로 일정하고 RGB는 변한다. 기존 opacity/particle alpha/source strength를 유지한 채 atlas R density를 곱하고, 실제 `Tex_SubUV`에 연결된 기존 atlas Custom의 Age 입력을 원작 Cascade DynamicParameter0 `SubUV_frame`로 바꿨다. Source master grid default6×6과 현재 child override9×9/8×8은 변경하지 않았다. 정확한 cooked graph와 프레임 간 보간 topology는 미확보이며, 이 연결은 원작 직접 graph 복원값이 아닌 native 재구성이다. WorldSubUV에는 atlas Custom이 두 개 있어 단일 node 개수 가정은 틀렸고 실제 texture 연결로 대상을 찾았다. 두 번째 guard 실패 PID14780은 저장0이며, 수정한 author PID22508/token76b73dd839a642c68364b3f87a54aa00은 exit0으로 세 target 저장을 완료했다.

같은 run에서 `Base_Particle`의 실제 native opacity texture 출력은 이미 R임을 확인했다. importer 코드에서 A를 예상한 것은 실제 native 상태와 달랐다. 따라서 이 parent의 alpha 교체를 새 실제 bug 원인이라고 주장하지 않는다. 추가 저장은 alternate Mask pin뿐이고 현재 `FM_Particle_Zero` source child는 Translucent다. 이 불필요 후보의 guarded restore와 최종15/16 범위는 Root와 조정 중이다.

`ResourceAudit/ContextShaderAuthorSummary.json`에 저장된6 target의 before/after SHA, source package/JSON SHA, native graph 관측, author process와 log를 보존한다. 각 target recompile/save에서 오류는 없었고 log의 material/shader compile 실패0이지만, 그 사실만으로 실제 child render가 통과했다고 판단하지 않는다. `ArtCandidateManifest.json`은 현재 후보16(기존10/신규6)의 hash 일치와 Main Effects2,028개 변경0을 확인한 `waiting_actual_overfury_visual_QA` 상태다. 모든 own editor는 종료했으며 Main Source/Effects/사용자 editor에는 수정·저장·reload를 하지 않았다. 다음 단계는 Root의 fresh native 실제 공격 RHI에서 OverFury 약1.01초와 먼지 field의 투명 외곽을 직접 확인한 뒤 guarded 최종 후보를 확정하는 것이다.


<!-- PlayerAttackVFX_20261008_context_scope15 -->
## 2026-10-08 — 불필요 Base_Particle 변경 제외·최종 Art 후보15 대기

Root 결정에 따라 private `Base_Particle` 한 파일만 guarded restore했다. 현재 after SHA `3a361b8a7bcfed84f0785a38a1e898cae7196f87e89983476d22f5cf83431b98`, 보존 backup SHA 및 Main 원본 SHA `1f96ac08825d7eea1342a4a44b8e74789808724e7497984e24b132bd2d7cdf9f`를 확인하고 backup의 정확한 bytes를 복구했다. 실제 native opacity는 이미 R였고, 현재 Translucent consumer에 쓰이지 않는 추가 Mask 출력만 제거한 것이다. 다른 private asset이나 Main 파일은 복구·수정하지 않았다.

`ResourceAudit/BaseParticleUnusedMaskRestore.json`에 단일 복구 증거, `ArtCandidateManifest_Context16BeforeBaseRestore.json`에 직전16 후보를 보존했다. 현재 `ArtCandidateManifest.json`은 실제 필요한15개(기존9/신규6)이며 private expected SHA 모두 일치, Main Effects2,028개 변경0이다. 과거 targeted6 save proof는 보존하고 실제 retained target5와 복구 사실을 구분한다. 상태는 `waiting_actual_overfury_visual_QA`로 유지하며 다음 단계는 Root가 fresh native RHI 실제 OverFury 약1.01초와 smoke field 투명 외곽을 확인하는 것이다. 이 checkpoint는 Main 전달·최종 원작 시각 일치 완료를 뜻하지 않는다.


<!-- PlayerAttackVFX_20261008_atlas_uv_child_RHI -->
## 2026-10-08 — WorldSubUV 체크무늬 fallback 원인·저장 자식9 SM6 재검증

새 실제 OverFury 화면의 큰 회색 체크무늬는 성공한 parent compile/save의 증거와 양립하지 않는 실제 Art 실패다. `RuntimePIE/PrivatePIE.log`의 master `FM_World_SubUV_color_A` 및 Masked child `FMI_World_SubUV_color_A_01`은 PCD3D_SM6에서 Custom input1(UV) 누락으로 컴파일에 실패해 Default Material을 사용했다. 다른 distinct material compile/fallback 실패는 해당 로그에 없었다. 실패 log/Driver/121·123 PNG를 `ResourceAudit/AtlasUVFailureEvidence`에 SHA와 함께 별도 보존했다.

실제 native readback에서 현재 `Tex_SubUV`에 연결된 Custom_0의 UV만 null이었고 Age는 현재 source DP0, Columns/Rows는 기존 scalar nodes에 연결돼 있었다. 동일 master의 다른 atlas Custom_1은 모든 입력이 유효했다. 기존 TextureCoordinate_1의 출력을 Custom_0.UV에 연결하는 한 입력만 복구했다. 파라미터/texture/MI override/geometry/scale/DP curves/atlas 수식·숫자는 변경하지 않았다. 새 private SHA는 `93814b114851baa1cd508b76ebdbade1589e12be23ccd62ab1435e8eb3b6c1d2`다. Context15 범위와 원본 Base_Particle 복구 상태는 유지한다.

첫 UV 검사 PID15592는 RHI 통계를 엄격히 요구했지만 commandlet이 `-AllowCommandletRendering` 없이 실행되어 statistics가 모두0이었다. guard가 저장 전에 중단했으므로 save0이며 이를 컴파일 성공으로 기록하지 않는다. 과거 commandlet의 `recompile_material` errors0만으로 실제 child permutation이 정상이라고 한정하지 않는 이유다. Engine `MaterialEditingLibrary.cpp`의 RecompileMaterial은 현재 resource가 없으면 빈 errors를 반환하고, GetStatistics는 실제 resource에 대해 SubmitCompileJobs/FinishCompilation을 수행한다.

명시적 `-AllowCommandletRendering`을 추가한 private Cmd PID31884/tokenb10d2a6752c24fd19c6af3b41978641c은 28.468초/exit0으로 한 master만 저장했다. 실제 SM6 master PS178/VS344, Masked child01 PS108/VS153, 나머지 referenced child8개 PS178/VS344 instruction을 강제 컴파일 후 확인했다. Source child01은 FT_leaf_01(그리드5×1, alpha255/RGB변화), Masked/TwoSided/Unlit·clip.05이며 Grass source particle13개에서 FS_Leaf_01 TypeDataMesh와 bOverrideMaterial=true로 Required MI를 사용한다. Source smoke child07/03의 grid9×9와 다른 source override는 보존했다. Author log의 수정 전 load 실패는 그대로 남겨 실패 이력을 숨기지 않았다.

새 저장 상태를 별도 read-only RHI PID27776/token38bc8af4d646420cb7d7a7f3581ae514에서 다시 로드했다. 9.797초/exit0, package save0, master와 referenced child9의 positive PS/VS instruction, Failed-to-compile/Default-Material/ShaderCompiler-error log line0을 확인했다. Main `AtlasUVFix_b10...` 및 `AtlasUVFreshVerify_38bc...`에 전체 receipt/log/tools를 보존했다. Child9 바이너리와 Main Effects2,028개 SHA는 모두 불변이다. 후보15(기존9/신규6) manifest는 새 WorldSubUV SHA를 반영했고 `waiting_actual_overfury_visual_QA`를 유지한다. 모든 own editor는 정상 종료했으며 Root의 다음 native build를 막지 않는다. 최종 다음 절차는 Root의 새 Source/Brutal montage author 뒤 실제 공격8 montage RHI에서 fallback log0 및 OverFury 약1.01초 화면을 직접 확인하는 것이다. 이 isolated compile 검사를 실제 공격 시각 통과나 원작 pixel parity로 승격하지 않는다.
