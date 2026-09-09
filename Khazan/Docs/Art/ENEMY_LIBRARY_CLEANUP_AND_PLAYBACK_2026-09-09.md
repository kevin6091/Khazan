# 2026-09-09 Enemy 실사용 외형 정리와 애니메이션 구분

사용자 요청에 따라 대표 외형 16개와 그 의존 리소스를 남기고, 사용하지 않는 원본 파츠·예전 조합을 프로젝트 Content에서 삭제했다. 애니메이션은 사용자가 검증 후 선정할 예정이므로 이번에는 삭제하거나 편집하지 않았다.

## 정리 결과

| 종류 | 이전 | 현재 | 삭제 |
|---|---:|---:|---:|
| 외형 Blueprint | 61 | 16 | 45 |
| SkeletalMesh | 96 | 29 | 67 |
| Skeleton | 10 | 10 | 0 |
| Material / MaterialInstance | 106 | 65 | 41 |
| Texture | 256 | 214 | 42 |
| AnimSequence | 1,436 | 1,436 | 0 |
| 카탈로그 Level | 1 | 1 | 0 |

총 195개 자산, 343,444,687 bytes(약 327.53 MiB)를 Content에서 제거했다. `Archive/FaceVariants_20260908`의 예전 BP 45개/몸체 44개, 통합 몸체가 이미 사용하는 원본 파츠 중 독립 참조가 없는 메시, 관련 미사용 머티리얼·텍스처가 대상이다. Asset Registry의 hard/soft package 참조와 management 참조를 추적했으며, Enemy 밖에서 참조하는 삭제 후보는 없었다.

29개 메시가 29종 캐릭터를 의미하지 않는다. 통합 몸체·중갑 파츠·무기·화살통·애니메이션의 preview mesh와 pose carrier를 포함한다. 대표 외형은 계속 검병 4, 방패병 4, 궁병 4, 중갑 대검병 1, 할버드 1, 다른 지역 마법사 2의 16개다. 숨겨진 pose carrier와 공유 Skeleton은 애니메이션 및 중갑 조립이 사용하므로 유지했다.

복구용 UE 자산 백업은 `C:/Users/user/Desktop/카잔/EnemyExtracts/ProjectCleanup_20260909`에 있다. `BackupManifest.json`의 삭제 후보 195개를 복사 후 SHA256 대조했다. 원작 PSK/PSA/PNG/JSON/raw cooked 보관소는 이전 위치에 유지한다. 프로젝트 Content를 가볍게 정리한 것이며 외부 보관 원본까지 제거한 것은 아니다.

별도 Unreal 프로세스에서 카탈로그를 다시 열고 BP 16개의 몸체·머티리얼·애니메이션·장비 socket을 확인했다. 남긴 자산 1,771개는 시작 hash와 같고, 삭제 자산으로 향하는 Enemy 내부 package 참조는 0개다. 기존 애니메이션 1,436개는 내용까지 동일하다. 작업 시작 시 보호한 기존 코드·플레이어 자산·문서·환경 맵 44개도 변하지 않았다. 최종 commandlet은 오류 0개로 정상 종료했다.

UE 삭제 API가 성공을 반환했지만 `T_EN_T_EV_BlankWhite_01.uasset` 4,899 bytes가 디스크에 남았다. 재실행에서도 같아, UE 종료·미참조·정확한 경로·백업 hash를 확인하고 해당 단일 파일만 정리했다. 이후 별도 프로세스에서 최종 검증을 통과했다.

## 현재 Blueprint에 들어 있는 작업

16개 BP의 부모는 실제 Asset Registry에서 `/Script/Engine.Actor`로 확인했다. 생성기는 Components/SimpleConstructionScript의 조립 정보와 기본 속성을 만들며, 별도 EventGraph나 전투 Construction Script 로직을 작성하지 않았다.

| 구성 | 저장된 작업 | 역할 |
|---|---|---|
| `DefaultSceneRoot` | Actor의 기본 SceneComponent | 배치 원점 |
| `EnemyBody` | 완성 몸체 메시, 머티리얼, 방향과 원본 CB 기반 크기 | 캐릭터의 외형과 포즈 |
| `EnemyWeapon_R` / `EnemyWeapon_L` | 병종별 검·대검·할버드·활·지팡이와 원본 socket | 손의 움직임을 따라가는 장비 |
| `EnemyShield_L` | 방패와 `Weapon_L` 연결 | 방패병 장비 |
| `EnemyQuiver` | 화살통, 원본 `Weapon_R_BackPack` socket·상대 transform | 궁병 장비 |
| `EnemyArmor_Head/Upper/Lower` | 원본 bind pose를 보존한 개별 skin | 중갑병 전용 파츠 |
| 애니메이션 기본값 | `ANIMATION_SINGLE_NODE`, 원본 Battle AP의 Idle, looping/playing, play rate 1 | 배치 시 대기 자세 |
| 출처 태그 | `OriginalPackage`, `AssemblySelection`, `SourceLevel` 등 | CB·레시피·장비·Idle 추적 |

검병·할버드·마법사 등은 몸체+장비 2개, 방패병·궁병은 3개, 중갑병은 몸체 carrier+갑옷 파츠 3개+대검의 5개 SkeletalMeshComponent로 구성된다. 활과 지팡이에는 원본 WeaponSlot이 지정한 장비용 기본 애니메이션도 연결했다.

중갑병은 네 몸체/갑옷 컴포넌트에 같은 Idle이 지정돼 있다. 이후 다른 동작을 연결할 때 같은 클립·재생 시점을 함께 갱신해야 한다. 전투 중 클립 변경과 위상 동기화를 자동 처리하는 별도 기능은 아직 없다.

현재 BP는 외형을 확인하고 가져다 쓸 수 있는 조립 Actor다. CharacterMovement, AIController/BehaviorTree, ASC/GAS Ability, 공격·피격 판정, 콤보, 이동 AnimGraph는 구현하지 않았다. 생성된 메시 컴포넌트의 collision은 `NoCollision`이다. `KhazanAnimInstance.cpp`나 Player ABP를 복사한 결과도 아니다.

## 30 fps 원본과 재생용 시퀀스가 다른 이유

원작에는 **AnimSequence에 저장된 포즈**와 **그 포즈를 사용하는 AnimComposite의 재생 규칙**이 따로 있다. FModel에서 시퀀스를 30 fps로 가져오면 포즈와 원본 시퀀스 시간축은 복원되지만, 상위 Composite가 정한 구간·배속·반복·시간 변환까지 자동 적용되지는 않는다.

| 구분 | `A_EN_SRC_*` | `A_EN_PLAY_*` |
|---|---|---|
| 원본 기준 | 원작 AnimSequence | 원작 AnimComposite 및 활성 DilationCurve |
| 구간 | 원본 시퀀스 전체 | `AnimStartTime`–`AnimEndTime`의 지정 구간 |
| 순서/반복 | 원본 키 순서 | `StartPos`, 여러 segment, `LoopingCount` 반영 |
| 배속 | 시퀀스의 시간축 | `AnimPlayRate` 반영; 음수는 역재생 |
| 시간대별 속도 | 시퀀스 자체의 키 시간 | `T_Original`–`T_Dilation` 표를 이용해 다시 표본화 |
| FPS | metadata의 `(NumFrames-1)/SequenceLength`, 이 집합은 30 | 참조 시퀀스 또는 Dilation `TimePerFrame`을 기준으로, 목표 종료 시간에 맞춘 유리수 rate |
| 사용 | 원본 비교·추후 재편집의 기준 | 위 규칙을 이미 반영한 결과를 1배로 재생 |

FPS는 저장한 sample의 시간 간격이다. 재생용 FPS가 약 60이라고 해서 동작을 두 배 빠르게 만든 것은 아니다. 같은 동작 길이에 더 많은 포즈를 찍으면 부드럽게 표본화하면서 길이는 유지된다. 실제 속도 차이는 구간의 길이·배속·시간 변환에서 나온다. 종료 시간을 정확히 맞추기 위해 재생용 FPS는 항상 정수 30/60이 되지 않는다.

원본 711개 시퀀스의 `RateScale` override는 직렬화돼 있지 않았다. 1.0은 UE/CUE 기본값이며 원작 파일에 명시된 override로 표현하지 않는다. 원본/재생용 모두 임포트 시 1배로 두었으며, 재생용에 같은 Composite 배속이나 Dilation을 다시 곱하면 중복 적용된다.

### 실제 metadata 사례

- 궁병 피격: `BBQ/Content/_Kazan_/Design/Monster/Human/Empire/EmpireBow/Moving/Reaction/AC_EmpireBow_DamageNormal_D_B`. 원본 `Properties.SequenceLength=0.7 s`, `DilationCurve.DilationSequenceLength=1.0132997 s`. 재생용은 원본 포즈를 해당 시간 표에 따라 약 1.0133초 동안 재생한다. 단순히 30 fps 원본을 그대로 틀었을 때와 다른 길이다.
- 마법사 역재생: `BBQ/Content/_Kazan_/Design/Monster/Human/Empire/EmpireMagic/Skill/03_FireRandom/AC_EmpireMagic_FireRandom_Loop_Back`. `AnimationTrack.AnimSegments[0]`의 `AnimStartTime=0`, `AnimEndTime=1.2 s`, `AnimPlayRate=-1.2`, `LoopingCount=1`. 1.2초 구간을 역방향으로 1.2배 재생하므로 구간 결과는 1.0초다. 이 계산값과 별개로 serialized Dilation 끝은 `0.99999964 s`다.
- 궁병 동작 연결: `BBQ/Content/_Kazan_/Design/Monster/Human/Empire/EmpireBow/Skill/00_DestroyObject/AC_EmpireBow_DestroyObject_End`. segment 0은 `CA_M_EmpBow_BasicShoot_End`의 0–0.8666667초, segment 1은 `StartPos=0.8666667 s`에서 `CA_M_EmpBow_Stand_F`의 0–0.1초다. 연결 후 `SequenceLength=0.9666667 s`, 활성 Dilation 결과는 `1.3533326 s`다. 한 원본 시퀀스만 임포트해서는 이 연결 결과가 생기지 않는다.

이 작업에서 따로 만든 것은 시간 규칙을 포즈 키에 적용한 **AnimSequence bake**다. 원작 AI 상태, Actor time dilation, Ability 배속, hit-stop까지 구현한 것은 아니다. 원작 전용 Notify의 실행도 별도이며, 4,863개 원본/변환 이벤트 시간은 `PlaybackEventTimes.json`에 보존했다.

## 모든 재생용 복사본이 필요한가

아니다. 최초 확장에서는 Composite 이름별 대응과 원본 비교를 위해 폭넓게 생성했다. 이번에 722개를 실제 metadata와 변환 데이터로 분류했다.

| 분류 | 수량 | 확인 결과 |
|---|---:|---|
| 시간축 변경 | 271 | 구간 자르기·배속·반복·연결·Dilation 중 하나 이상 적용 |
| 원본과 시간축 동일 | 451 | 한 원본의 전체 구간, 1배, 1회이며 유효 시간 변환 없음 |

451개 중 440개는 sample 수까지 같고, 모든 저장 sample/bone의 비교에서 최대 위치 성분 차이 약 `4.51e-15 cm`, quaternion 성분 차이 `1.1920928955078125e-7`, scale 차이 0이었다. 나머지 11개는 시간축은 같지만 표본 수가 달라져 있어 단순 byte 중복으로 분류하지 않는다. 이 비교는 변환 입력 데이터 비교이며 UE 압축 전/후 검증은 기존 `AnimationImportAudit`와 구분한다.

변경 이유의 중복 집계는 trim 172, Dilation 144, 여러 segment 8, segment offset 8, 반복 3, 배속 8이다. 한 클립에 이유가 여러 개 있을 수 있어 합산해 총수로 쓰지 않는다. 분류는 serialized 시간의 `1e-5 s` 허용오차를 사용했다. 이전 보고서의 “길이가 바뀐 143개”는 `1e-4 s` 기준의 길이 비교라 현재 이유 집계와 기준이 다르다.

후속 정리에서는 `PlaybackComparison.csv`의 `EquivalentSourceTimeline`을 우선 검토하면 된다. 원본 또는 재생용 중 사용할 이름을 정하고 실제 소비 참조를 옮긴 다음 중복을 제거한다. `ChangedTimeline`은 원작 동작을 재현하는 데 필요한 변환일 수 있으므로 이름만 보고 원본/복사본 중 하나를 일괄 삭제하지 않는다. 이번에는 기존 Idle 3개+원본 711개+재생용 722개를 모두 유지했다.

## 현재 자료와 재개 위치

- 현재 프로젝트 에셋 목록: `Content/_Art/Enemies/HeinMach/Metadata/Cleanup_20260909/RetainedAssets.json`.
- 삭제 목록·백업 hash: 같은 폴더의 `RemovedAssets.json`; 외부 백업 `ProjectCleanup_20260909/BackupManifest.json`.
- BP 실제 컴포넌트: 같은 폴더 `BlueprintComponents.json`.
- 애니메이션 비교: 같은 폴더 `PlaybackComparison.csv`, `HeinMachEnemy_PlaybackComparison_20260909.json`.
- 최종 확인: `HeinMachEnemy_CleanupAudit_20260909.json`. 이전 import manifest/report는 추출 당시의 역사 자료이며 삭제된 자산까지 포함한다.
- 외형 확인: `/Game/_Art/Enemies/HeinMach/Preview/L_HeinMach_EnemyCatalogue`.

복원 요청이 없는 한 이전의 전체 import/assembly builder를 재실행해 삭제한 원본을 다시 생성하지 않는다. 이번 작업은 Enemy 에셋·스크립트·관련 Art 문서를 main에 커밋하는 범위이며, 기존 Player/C++/프로젝트 설정 변경은 별도 작업으로 유지한다.

## 2026-09-09 Git 전달 확인

- 에셋 및 파이프라인 커밋: `65119aa65dcf6f7d20b756715695111b946f2ee9`, `art: add curated humanoid enemies and metadata-timed animations`.
- `origin/main` push 성공, LFS 객체 39개(110 MB) 업로드 완료. 원격 `refs/heads/main`의 commit 일치까지 확인했다.
- 기존 Player/C++/설정 변경 및 다른 DAS 문서 작업은 커밋에 포함하지 않았다. 공용 Art 문서는 Enemy 섹션만 stage했다. 이 전달 확인은 별도 문서 커밋으로 기록한다.
