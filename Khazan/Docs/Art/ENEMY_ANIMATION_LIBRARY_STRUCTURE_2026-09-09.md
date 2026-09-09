# 2026-09-09 Enemy 재생 애니메이션 구조 통합

남은 Enemy AnimSequence를 실제 사용 관점에서 하나의 재생 라이브러리로 통합했다. 최종 884개는 모두 `A_EN_PLAY_*` 이름을 사용하며, 각 병종의 `Animations/Playback` 폴더 한 곳에 있다. `SourceSequences`, `PlaybackClips`, 예전 단수형 `Animation` 폴더에는 AnimSequence나 redirector가 남아 있지 않다.

## 최종 구조

```text
/Game/_Art/Enemies
├─ HeinMach/Humanoids
│  ├─ Archer/Animations/Playback             169
│  ├─ HalberdElite/Animations/Playback       115
│  ├─ HeavySwordsman/Animations/Playback      77
│  ├─ Shared/Animations/Playback                9
│  ├─ SwordShield/Animations/Playback          91
│  └─ Swordsman/Animations/Playback           181
└─ OtherRegions/Humanoids
   ├─ EliteShield/Animations/Playback         130
   └─ Mage/Animations/Playback                112
```

`SharedSourceReferences`의 애니메이션은 `Shared`, `EliteShield_SourceReferences`의 애니메이션은 `EliteShield`로 옮겼다. 메시나 Skeleton 등 애니메이션이 아닌 자료의 기존 위치는 이번 요청으로 바꾸지 않았다.

## 네이밍과 의미

모든 이름의 공통 접두사는 `A_EN_PLAY_`다. 뒤의 원작 asset basename은 유지했다.

| 이름 형태 | 수량 | 실제 의미 |
|---|---:|---|
| `A_EN_PLAY_AC_*` 중심 | 722 | 원작 AnimComposite의 segment·배속·Dilation을 포즈에 bake한 재생 시퀀스 |
| `A_EN_PLAY_CA_*` 중심 | 162 | 원작 AP·BlendSpace·WeaponSlot·Notify 등이 AnimSequence를 직접 쓰므로 원본 시간축을 그대로 재생하는 시퀀스 |

`AC`와 `CA`는 원작 asset basename 일부이며 새 접두사 분류값이 아니다. 동일 basename이 서로 다른 원작 package에 존재하는 경우 기존 8자리 구분 suffix를 유지한다. 모든 자산의 Content Browser 역할은 `EnemyArtRole=PlaybackSequence`로 통일했다.

원본 유래 차이는 파일명이나 폴더 분리 대신 다음 metadata로 보존한다.

- `PlaybackDerivation=CompositeBake` 또는 `DirectOriginalTimeline`
- `PreviousEnemyArtRole=PlaybackClip` 또는 `SourceSequence`
- `OriginalPackage`: 원작의 전체 package path
- `CanonicalAnimationStructureVersion=20260909_PlaybackUnifiedV1`
- `CanonicalPlaybackPath`: 현재 재생 자산 경로
- 기존 `TimingContract`와 source metadata 경로

`DirectOriginalTimeline`도 프로젝트에서는 재생용이다. 다만 원작 Composite 변환을 거친 것처럼 기록하지 않는다. 이 구분 덕분에 나중에 동작을 교체하거나 원작 시간을 재검증할 때 어떤 규칙으로 만들어졌는지 추적할 수 있다.

## 중복 Idle 3개 정리

이전 초기 임포트의 다음 세 Idle은 현재 직접 재생 시퀀스와 같은 원작 package, Skeleton, 30 fps, 길이, sample 수, RateScale 및 root 설정이었다.

- `A_EN_Sword_Idle`
- `A_EN_SwordShield_Idle`
- `A_EN_HalberdElite_Idle`

세 쌍의 모든 프레임·모든 bone을 RAW와 COMPRESSED로 비교했다. 위치와 scale 성분 차이는 0, quaternion 성분의 최대 차이는 약 `2.292e-5`였다. 이는 같은 원본을 두 번 임포트한 압축 수치 차이며 기존 임포트 검증 허용치보다 작다. 세 Idle은 현재 참조도 0이므로 중복으로 삭제하고, `A_EN_PLAY_CA_*` 직접 재생 시퀀스를 남겼다.

삭제 전 애니메이션 887개와 참조 BP 16개를 `C:/Users/user/Desktop/카잔/EnemyExtracts/AnimationStructure_20260909`에 복사하고 SHA-256을 확인했다. 이 백업과 Git 이전 commit으로 복구할 수 있다.

## 참조와 데이터 검증

UE의 asset rename을 사용해 884개를 이동했고, BP 16개의 몸체·활·지팡이 Idle 참조도 새 package path로 함께 저장했다. BP의 메시, 컴포넌트 수, 재생률, loop, collision, 회전 및 scale은 이전 기록과 같다. 카탈로그 Level에서 16개 Actor의 모든 지정 애니메이션이 현재 884개 안에 있음을 확인했다. `KhazanAnimInstance.cpp`, Player ABP, 캐릭터 코드와 프로젝트 설정은 수정하지 않았다.

별도 Unreal commandlet에서 다음을 확인했다.

- AnimSequence 884개, `A_EN_PLAY_*` 884개, `Animations/Playback` 884개
- old package와 ObjectRedirector 0개, 누락 Enemy dependency 0개
- 저장 FPS의 분자/분모, sample/frame 수, 길이, RateScale, root 설정과 Skeleton이 이동 전 계약과 일치
- 길이 변화 0초
- 모든 시퀀스의 처음·중간·마지막 포즈를 RAW/COMPRESSED로 총 5,298회 평가
- 원본 변환 배열 대비 최대 성분 오차: 위치 `0.000106812 cm`, quaternion `0.000686944`, scale `0.0000013113`
- 변경 대상 밖 Enemy 파일 319개 SHA-256 동일, 보호한 외부 작업 변경 0개
- 최종 commandlet `Success - 0 error(s)`, process exit code 0

포즈 오차는 기존 임포트 압축 검증 범위이며 이번 이동으로 새로 보정한 수치가 아니다. 전투 AI, Notify 실행, Montage/Ability 연결이나 원작 영상 비교는 이 파일 구조 작업의 검증 범위가 아니다.

## 현재 조회 기준

최신 현재 목록과 경로 대응은 `Content/_Art/Enemies/HeinMach/Metadata/AnimationStructure_20260909`에 발행한다. `CurrentAssets.json`이 전체 1,219개 Enemy UE 자산의 현재 경로와 SHA-256을, `AnimationLibrary.csv`가 884개 재생 시퀀스의 병종·유래·원작 package·FPS·길이를 기록한다. `RenameMap.json`, `LegacyIdleDuplicates.json`, `BlueprintComponents.json`으로 이동과 BP 참조를 추적한다.

이전 `Expansion_20260909`, `Cleanup_20260909`, `AnimationPruning_20260909`의 destination 경로는 각 작업 당시의 이력이다. 현재 경로가 필요한 코드·BP·후속 도구는 최신 구조 metadata를 사용한다. 전체 importer를 다시 실행해 `SourceSequences`와 `PlaybackClips` 폴더를 되살리지 않는다.

## 2026-09-09 main 전달 확인

통합 에셋·경로 metadata·파이프라인·관련 Art 문서를 `6fd77bcc281e549f82bdb4204593b181faa02d83` (`art: unify enemy playback animation library`)로 main에 커밋하고 `origin/main`의 동일 hash를 확인했다. 기존 Player/DAS/C++/프로젝트 설정과 다른 작업 문서는 포함하지 않았다. 이 전달 기록은 후속 문서 커밋에 포함한다.
