# 프로젝트 상태

> 모든 작업 시작 전에 `1_PROJECT_STATE.md`, `2_UE5_RULES.md`, `3_ARCHITECTURE.md`를 먼저 확인한다.
> 기존 기록은 덮어쓰거나 삭제하지 않고, 변경 사항을 날짜별 섹션으로 문서 하단에 추가한다.

## 2026-08-31 기준

- [완료] 카잔 캐릭터 파츠(Torso, Shoes, Hair, Arm, Leg, Face 등)를 Leader Pose Component로 `SKM_Khazan` 베이스 메시에 동기화하는 C++/Blueprint 구성을 완료했다.
- [완료] 투명·발광(Ghost) 무기의 머티리얼 구조 분석을 완료했다.
- [진행 대기] FModel에서 추출한 HeinMach 레벨 에셋(Static Mesh, Material, Texture)을 UE Python API로 자동 임포트하고 머티리얼을 매핑해야 한다.
- [범위 제외] 주인공이 맨손으로 비틀거리며 기본 이동만 하는 장면은 HeinMach 레벨 구성 대상에서 제외한다.

## 2026-08-31 작업 반영

- [완료] 프로젝트 로컬 `UnrealPSKPSA` 플러그인을 UE 5.8에 맞게 빌드하고 `.psk`, `.pskx`, `.psa` 임포터를 활성화했다.
- [완료] FModel의 PSK 21개를 `/Game/_Art/Kazan/FModel/PSK`에 임포트했다. 재검증 결과 21개 모두 유효한 Skeletal Mesh와 Skeleton을 가진다.
- [완료] HeinMach 환경 레이어 19개를 UE Python API로 자동 임포트하고 `/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment` 맵을 생성했다.
- [완료] HeinMach 임포트 결과 Static Mesh 22개, Material Instance 22개, Texture 45개를 생성했으며 22개 메시 모두 머티리얼 슬롯 연결을 확인했다.
- [검증] HeinMach 재실행 시 기존 유효 결과를 감지해 중복 임포트 없이 종료한다.
- [범위 제외 유지] 모든 `HeinMach_Cine_*` 레이어와 캐릭터·스폰·사운드·BGM 레이어를 환경 재구성 입력에서 제외했다.

## 2026-08-31 FModel 규칙 문서화

- [완료] 실제 추출물에서 확인한 Khazan 에셋의 네이밍, 원본 패키지 경로, 파일 역할, 메시 분할, 머티리얼 참조 및 UE5 정리 규칙을 `4_FMODEL_ASSET_RULES.md`에 기록했다.
- [유지 규칙] FModel/에셋 작업 전에는 기존 핵심 문서 3개와 `4_FMODEL_ASSET_RULES.md`를 먼저 확인하고, 새 발견은 기존 내용을 덮어쓰지 않은 채 하단에 추가한다.

## 2026-08-31 HeinMach 환경 재구성 확정

- [완료/이전 진행 대기 대체] FModel 원본 참조를 기준으로 Static Mesh 183개, Material Instance 334개, Texture 955개를 CorrectedSourceAssets에 분리 임포트했다. USD asset sharing 및 material-slot merging은 사용하지 않았다.
- [완료] 일반 환경 prop 2,665개를 원본 transform과 mesh reference로 배치했다. 재시작 후 감사에서 누락 0, transform 불일치 0, mesh 불일치 0, TwoSided 불일치 0을 확인했다.
- [완료] 잘못 생성된 기존 범용 액터 777개를 제거하고 원본 지형 액터 2개는 보존했다.
- [완료] PointInstancer foliage를 HISM 113배치, 19 prototype, 12,495 instance로 복원했다. 재시작 후 인스턴스 월드 transform digest, mesh, material 불일치가 모두 0이다.
- [완료] root-only 추출에서 빠진 비루트 렌더 메시 15개를 원본 상대 transform으로 복원했다. 구성은 table 9개, carriage 파손 파츠 5개, bridge 파츠 1개다.
- [완료] 비시네마틱 fog sheet 50개를 원본 transform과 translucency sort priority로 복원했다. FModel USD에 원본 커스텀 셰이더가 없으므로 컴파일 검증된 one-sided translucent preview material v3를 사용한다.
- [완료] 지형 2개의 placeholder display-color material을 추출된 snow texture 기반의 가역적 terrain preview material v1로 교체했다. 메시, UV, 원본 transform은 변경하지 않았다.
- [완료] 원본 조명 89개와 확인용 환경 액터 4개를 포함한 최종 맵 2,938개 액터를 정상 종료·재실행 후 통합 감사했다. 분류 누락 0, 중복 label 0, WorldGrid material 0이며 모든 검사가 통과했다.
- [검증] 원본 메시 190개의 winding audit 결과 positive triangle 1,986,738, negative 6,597, near-zero 2, 오류 0이다. 전체가 뒤집힌 메시는 없으며, negative determinant 배치 341개는 원본 mirror transform이므로 blanket reverse culling을 적용하지 않는다.
- [제약] LandscapeComponent geometry 57개는 확인했지만 FModel 추출물에 원본 WLM/weightmap/layer graph가 없다. 현재 snow terrain material은 시각 확인용 근사치이며 원본 지형 셰이더의 완전 복원으로 간주하지 않는다.
- [제약] fog의 동적 material parameter와 texture reference는 보존했지만 원본 custom parent shader graph는 추출되지 않았다. 현재 fog material도 안전한 preview 근사치다.
- [범위 제외 유지] 모든 HeinMach_Cine_* 및 주인공 맨손 비틀거림·기본 이동 전용 장면은 임포트, 배치, 검증 대상에서 제외한다.
- [작업 연속성] 앞으로 모든 작업은 1_PROJECT_STATE.md부터 5_WORK_CONTINUITY.md까지 먼저 읽는다. 작업이 중단될 가능성이 있으면 종료 전에 5_WORK_CONTINUITY.md에 완료 상태, 검증 결과, 남은 작업과 정확한 재개 절차를 기록한다.

## 2026-08-31 완성 Level 및 조사 지식화

- [확정] Maps 폴더의 완성본은 /Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment 하나다. Before*, LightingOnly, FoliageImportSandbox는 백업 또는 staging이며 완성본이 아니다.
- [완료] 기존 FModel/HeinMach 전수조사 범위, 수량, metadata와 report 경로, superseded 결과, 재조사 조건을 6_SURVEY_KNOWLEDGE_BASE.md에 정리했다.
- [유지 규칙] 앞으로 필요한 정보는 프로젝트 문서 1–6, Content Metadata, Saved/ImportReports 순서로 찾고, 기존 결과가 없거나 source snapshot이 바뀐 경우에만 전수조사한다.
- [유지 규칙] 불가피한 전수조사 후에는 조사 범위, source snapshot, script, 결과 수량, 오류, 상세 JSON 경로, 기존 조사 대체 관계와 재조사 조건을 6_SURVEY_KNOWLEDGE_BASE.md 하단에 추가한다.

## 2026-08-31 DevMap PIE 크래시 진단

- [진단 완료] 기본 `/Game/Maps/DevMap`의 PIE 시작 직후 발생하는 Assert는 `UKhazanAssetManager::LoadedAssetData == nullptr` 상태에서 `AKhazanPlayerController::SetupInputComponent()`가 입력 데이터를 요청해 발생한다.
- [근본 원인] `BP_GameInstance`는 `UKhazanGameInstance` 기반이지만 `DefaultEngine.ini`에 `GameInstanceClass`가 없어 `UKhazanGameInstance::Init()`과 AssetManager 프리로드가 실행되지 않는다.
- [수정 대기] 즉시 복구안은 `GameInstanceClass=/Game/Bluprints/BP_GameInstance.BP_GameInstance_C` 설정이다. 구조적 후속안은 프리로드를 `UKhazanAssetManager::StartInitialLoading()`으로 이동하는 것이다.
- [문서화] 재현 시그니처, 증거, 후속 위험, 수정 후 검증 절차는 `7_RUNTIME_CRASH_DIAGNOSTICS.md`에 기록했다.
- [유지 규칙] 이후 런타임 크래시는 프로젝트 문서 1–7과 최신 동일 시그니처부터 확인하고, 기존 기록으로 설명되지 않을 때만 조사 범위를 넓힌다.
