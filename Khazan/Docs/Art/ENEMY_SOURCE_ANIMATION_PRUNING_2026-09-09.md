# 2026-09-09 Enemy 원본 애니메이션 조건부 정리

**원본 전체를 삭제하고 기존 재생용 722개만 남기는 것은 안전하지 않다.** 현재 BP가 원본 시퀀스 5개를 직접 참조하고, 원작 메타데이터에도 Composite를 거치지 않는 Idle·이동·무기 애니메이션 참조가 있다. 사용자의 “인게임에서 사용하지 않는 것이 확실하다면 삭제” 조건에 따라 확인된 중복 원본만 정리했다.

## 적용 결과

| 종류 | 이전 | 현재 | 삭제 |
|---|---:|---:|---:|
| `SourceSequences/A_EN_SRC_*` | 711 | 162 | 549 |
| `PlaybackClips/A_EN_PLAY_*` | 722 | 722 | 0 |
| 최초 임포트의 Idle | 3 | 3 | 0 |
| 전체 AnimSequence | 1,436 | 887 | 549 |

프로젝트 Content에서 290,576,489 bytes(약 277.12 MiB)를 제거했다. 남은 Enemy UE 에셋은 1,222개다. BP 16개·메시·머티리얼·텍스처·Skeleton·카탈로그는 그대로이며, 남긴 에셋 전체의 SHA-256이 작업 전과 같다. 시퀀스의 포즈 키, FPS, 길이, RateScale, root 설정 및 BP 애니메이션 연결을 편집하지 않았다.

## 삭제·보존 근거

삭제한 549개는 다음 조건을 모두 만족한다.

- 현재 프로젝트 Asset Registry의 hard/soft package 및 management 참조가 없다. `Source`/`Config`의 Enemy 원본 경로·이름을 사용하는 코드/설정 검색도 일치 항목이 없다.
- 저장된 원작 메타데이터에서 확인된 소비가 이미 재생용으로 bake한 Composite의 `Properties.AnimationTrack.AnimSegments[*].AnimReference`뿐이다.
- 대응 재생용은 자체 포즈 키를 가진 독립 AnimSequence이며, 삭제 원본을 UE package dependency로 요구하지 않는다. 원본 구간·배속·Dilation을 반영한 기존 bake 결과를 그대로 남겼다.

보존한 원본 162개는 직접 참조 또는 대체 여부 미확인 항목이다. 원작에서 Composite segment 외 직접 참조가 확인된 원본은 100개, 재생용에 대응하지 않는 원본은 124개이며 두 집합은 겹친다. 현재 미사용이라는 사실만으로, 대응 동작이 없는 시퀀스를 향후 재현에도 불필요하다고 단정하지 않았다. 이 집계는 저장된 추출 범위에 대한 분석이며 원작 전체 실행 경로를 관측한 결과가 아니다.

실제 반례는 다음 원작 package와 field에서 확인된다. package prefix는 `BBQ/Content/_Kazan_/Design/Monster/Human/Empire/`다.

| 원작 package | 직접 참조 field | 원본 동작 |
|---|---|---|
| `EmpireSword/Base_Setting/AP_EmpireSword` | `Properties.Idle` | `CA_M_EmpSwd_Stand_F` |
| `EmpireHalberd_E/Base_Setting/AP_EmpireHalberd_E` | `Properties.Idle` | `CA_M_Halberd_Stand_F` |
| `EmpireBow/Base_Setting/WS_EmpireBow_Early_Bow`의 `xxWeaponSlotInfoSkeletalMesh_0` | `Properties.DefaultAnimation` | `EmpireBow/Weapon/CA_M_EmpBow_Stand_F` |

BlendSpace의 `Properties.SampleData[*].Animation`, AnimationProfile의 `AnimMapIDToAsset`, Weapon Notify의 `DefaultWeaponAnimation` 등도 보존 판단에 포함했다. 특히 Composite 내부의 Weapon Notify가 별도 무기 시퀀스를 가리키는 경우, 몸체 포즈를 bake했다고 그 무기 참조까지 대체한 것으로 분류하지 않았다. 동일 basename의 몸체/활 시퀀스는 전체 package path로 구별했다.

최초 임포트 Idle 3개는 이번에 신규 동등성 검증을 하지 않았으므로 보존했다. 이름이 비슷하다는 이유만으로 삭제하지 않았다. 방패병 Idle처럼 동등한 재생용 후보가 있어도 실제 소비를 전환하는 별도 편집은 하지 않았다. 현재 요청 범위는 검증된 미사용 원본 삭제다.

## 검증과 복구

- 삭제 전 549개 UE 파일을 `C:/Users/user/Desktop/카잔/EnemyExtracts/AnimationPruning_20260909`에 복사하고 SHA-256을 대조했다. `BackupManifest.json`에 삭제 파일·남긴 파일 및 기존 사용자 작업의 기준 hash가 있다. PSK/PSA/NPY/JSON/raw cooked 원본 자료도 보존한다.
- 삭제 후 별도 commandlet에서 재생용 722개와 남긴 원본 162개를 재로드하고 frame rate의 분자/분모, sample 수, 길이와 RateScale을 기존 manifest와 확인했다. 재생용은 처음/중간/마지막 compressed pose 2,166개가 유효했다. 길이의 최대 차이는 임포트 계약 대비 약 `4.124e-7 s`이며 이번 정리로 재생 속도를 변경한 값이 아니다.
- 남은 1,222개 hash 일치, 누락 Enemy dependency 0, 삭제 원본의 package referencer 0, 저장된 카탈로그의 BP 16개 몸체/Idle/머티리얼/장비 socket 검사를 통과했다. 전투 AI·Notify 실행이나 원작 영상과의 동작 속도 대조를 수행한 것은 아니다.
- 실행 중 에디터의 삭제 검사에서 UE `FAppTime` ensure 및 참조 검사 알고리즘 fallback 경고가 발생했으나 삭제 API와 hash 검사는 완료됐다. 첫 commandlet은 에셋 검사에는 통과했지만 실행 중 에디터와 MCP 포트가 충돌했다. 최종 재검사는 해당 commandlet에만 `-DisablePlugins=ModelContextProtocol`을 적용하며 프로젝트 설정은 변경하지 않는다. 최종 프로세스 결과는 아래 완료 기록과 로그를 기준으로 한다.
- 다른 작업에서 변경된 Router/Animation/Engineering 문서 8개는 audit에 외부 변경으로 기록하고 보존했다. Enemy 외부 파일을 이 스크립트로 수정하거나 과거 hash로 복구하지 않았다.

## 현재 조회·재개 기준

최신 현재 목록은 `Content/_Art/Enemies/HeinMach/Metadata/AnimationPruning_20260909/RetainedAssets.json`이다. 같은 폴더의 `RemovedSources.json`, `RetainedSourceDecisions.json`, `AnimationRetention.csv`, `HeinMachEnemy_AnimationPruning_Metadata_20260909.json`에서 각 원본의 결정·원작 package/field·현재 참조·대응 재생용을 확인한다. 이전 `Cleanup_20260909`와 `Expansion_20260909` 자료는 해당 시점의 기록이다.

파이프라인은 `Scripts/Enemies/plan_enemy_animation_pruning.py` → `prune_enemy_source_animations.py` → `publish_enemy_animation_pruning.py`다. 삭제 작업 재개 시 저장된 plan/backup hash를 확인하며, 새 baseline을 덮어쓰지 않는다. 요청 없이 이전 전체 importer를 실행해 삭제 원본을 재생성하지 않는다. 원본 전체를 없애려면 보존 사유별로 직접 사용 시퀀스와 누락 동작의 재생 계약을 먼저 정해야 한다.

## 2026-09-09 최종 검증 완료

`Saved/Logs/EnemyAnimationPruningFinalAudit_20260909.log`는 **Success, 오류 0개, 기존 Lumen scalability 경고 1개, process exit code 0**으로 정상 종료했다. `HeinMachEnemy_AnimationPruning_Audit_20260909.json`은 passed다. 이전 GUI ensure/첫 commandlet의 포트 충돌과 최종 결과를 구분한다. 최종 commandlet의 임시 플러그인 비활성화는 현재 GUI나 프로젝트 설정에 적용하지 않았다.

커밋 범위는 Enemy 원본 삭제·새 판단 자료·관련 파이프라인/Art 문서다. Player/DAS/C++/프로젝트 설정 및 다른 문서 작업은 포함하지 않는다. main과 origin/main이 같은 상태에서 이번 변경을 stage하며, 전달 commit과 원격 일치 확인은 최종 응답 및 `Saved/ImportReports/HeinMachEnemy_AnimationPruning_GitDelivery_20260909.json`에 기록한다.

## 2026-09-09 main 전달 확인

에셋 정리 커밋 `ec802c8f37cb45ecdab3ee9460495f7f65595ade`를 `origin/main`에 push하고 원격 ref 일치를 확인했다. 삭제 549개와 새 metadata/스크립트/관련 Art 기록만 포함하며 기존 다른 작업은 그대로 남았다. 이 전달 확인은 후속 문서 커밋에 포함한다.
