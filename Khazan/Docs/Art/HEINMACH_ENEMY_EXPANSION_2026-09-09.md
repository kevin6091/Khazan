# 2026-09-09 인간형 Enemy 의상·장비·애니메이션 확장

사용자 요청: Sword/Shield 외 인간형 확인, 동일 의상 원인 확인/수정, 얼굴 약 3종으로 제한, 의상과 무기 다양화, 원작 메타데이터에 맞춘 애니메이션 임포트.

## 원본 확인과 의상 선정

기존 `SourceSpawnActors.json`의 HeinMach 스폰 47개를 재사용했다. 인간형은 Sword_Early 12, SwordShield 5, Bow_Early 5, SwordHArmor_Early 1, Halberd_E_Early 1, Sword_Sick_F 7이다. Sick_F는 검병의 부상 상황 변형이며 별도 갑옷 병종으로 세지 않는다. 원본의 도끼 모양 장병기는 Halberd 계열이다. 이 스폰 목록에서 별도 한손 도끼병은 확인되지 않았다.

검병과 방패병은 원본부터 `Empire_Upper001V4/003V4`, `Empire_Lower001V4/003V4`를 공유한다. 이전 추출은 이 두 상의·두 하의에 얼굴 5종까지 곱하여 40개 검병을 만들었으므로 의상보다 얼굴 변형이 과도하게 많았다. 원작 런타임의 색상·체형 RNG 결과까지 복원한 결과는 아니었다.

새 카탈로그는 얼굴 identity 001/002/003을 순환하며, 같은 상·하의에 모든 얼굴을 곱하지 않는다. 마법사의 건강형 Face003은 동일 번호의 얼굴 identity이며, 원본이 허용한 건강형을 사용한다. 얼굴 004/005의 신규 조합은 만들지 않는다. 헬멧형 레시피에 없는 얼굴을 임의로 추가하지 않는다.

| 병종 | 대표 조합 | 원본 의상/장비 근거 |
|---|---:|---|
| Swordsman | 4 | `CD_RD_Human_Adult_M_EmpireWounded_001`: 상의 001V4/003V4 × 하의 001V4/003V4, 검 |
| SwordShield | 4 | `CD_RD_Human_Adult_M_EmpireWoounded_SwordShield_001` (원본 철자): 폐쇄형 헬멧, 같은 군복 상·하의, 검과 방패 |
| Archer | 4 | `CD_RD_Human_Adult_M_EmpireBowWounded_001`: Hair002V4, 상의 001V4/002V4 × 하의 003V4/002V4, 활·화살·화살통 |
| HeavySwordsman | 1 | `CD_RD_Human_Elite_M_Empire_Early001`: Elite 전용 헬멧·상의·하의, `C_I_EmpireElite_Sword001V2` |
| HalberdElite | 1 | HeinMach `CB_EmpireHalberd_E_Early`, `C_M_HalberdV2`, `C_I_Halberd_WeaponV2` |
| Mage | 1 | 별도 지역 `CB_EmpireMagic`: Hair004, Upper004/Lower004 로브, Staff001 |
| MageHard | 1 | 별도 지역 `CB_EmpireMagic_Hard`: Hair503, Upper004V3/Lower004V3, Staff002 |

HeinMach 카탈로그에 마법사의 출현을 주장하지 않는다. 마법사 BP/애니메이션은 `/Game/_Art/Enemies/OtherRegions/Humanoids`에 구분한다. 원본 full package 경로, CB, 레시피, 실제 선택 파츠는 아래 manifest의 각 항목이 정본이다.

## 폴더와 사용 계약

- `/Game/_Art/Enemies/HeinMach/Humanoids/<병종>/Blueprints/BP_EN_*`: 배치 가능한 대표 외형.
- 각 병종의 `Meshes` 또는 `Parts`: 통합 몸체 또는 원본 skin 파츠.
- `Animations/SourceSequences/A_EN_SRC_*`: 원본 시퀀스 시간축.
- `Animations/PlaybackClips/A_EN_PLAY_*`: 원본 AnimComposite의 구간·반복·배속과 활성 DilationCurve를 반영한 재생용 시퀀스. **1배로 재생하며 같은 시간 보정을 다시 적용하지 않는다.**
- `Shared/Equipment`, `Shared/Skeletons`, `Shared/Materials/Expansion`, `Shared/Textures`: source package를 키로 공유한다.
- `Archive/FaceVariants_20260908`: 이전의 얼굴 중심 조합 보관. 신규 대표 카탈로그와 구분한다.
- `/Game/_Art/Enemies/HeinMach/Preview/L_HeinMach_EnemyCatalogue`: 대표 16개 외형 비교용 Art 레벨.

BP는 `Actor` 기반의 시각 조합이며 gameplay AI, GAS Ability, 피해·적중·콜리전 동작을 구현한 Enemy Pawn은 아니다. Player C++/ABP/기존 DAS 애니메이션은 이번 수정 대상이 아니다.

중갑병의 파츠는 원본 자체의 bind pose가 다르다. 예를 들어 `C_M_Human_Elite_M_Empire_Lower001V2`의 pelvis translation은 upper/carrier와 다르고, 어깨·muscle bone도 차이가 있다. 하나의 공통 bind pose로 강제로 합치지 않고 각 원본 skin을 유지한다. `EnemyBody`와 `EnemyArmor_Head/Upper/Lower`는 같은 클립·같은 재생 위상을 사용해야 한다. 이후 애니메이션 교체 시 네 컴포넌트를 함께 갱신한다.

다른 14개 의상은 파츠가 공유하는 bind transform의 일치를 확인하고 통합했다. 빈 carrier의 사용하지 않던 cloth bind가 실제 로브와 다른 경우에는 실제 파츠의 일치하는 bind를 채택했다. 최대 공유 bind 위치 차이는 `CombinedMeshManifest.json`에 기록된다. 상위 UV가 없는 파츠의 중립 보충, 원본 morph/LOD와 UE 복원 범위는 이전 추출과 같이 구분한다.

## 시간축과 원본 수치

원본 시퀀스 711개의 `Properties.NumFrames`, `Properties.SequenceLength`로 `(NumFrames - 1) / SequenceLength = 30 fps`를 확인했다. ActorX의 `AnimRate = NumFrames / SequenceLength`와 혼동하지 않는다. 예를 들어 원본 길이 1초에 31 samples이면 간격은 30개다.

원본 `RateScale` override는 이 집합에서 직렬화되지 않았다. UE/CUE의 1.0 기본값으로 기록하며, 원작 파일에서 명시적으로 1.0을 읽었다고 표현하지 않는다. `AnimationTrack.AnimSegments`의 `AnimStartTime`, `AnimEndTime`, `StartPos`, `LoopingCount`, `AnimPlayRate`는 각각 원본값을 보존한다. 음수 배속의 역재생도 원본 구간에 맞게 반영한다.

활성 `DilationCurve`는 `BakedDilationCurveName`, `TimePerFrame`, `DilationSequenceLength`, `DilationAnimPositions[].T_Original/T_Dilation`을 보존한다. `ApplyDilationCurveType=None`이면 적용하지 않는다. 타입 필드가 생략되고 이름 있는 baked table이 존재하면 그 table을 사용하는 복원 조건을 명시한다. 원작 런타임 코드 자체를 확인했다는 의미가 아니다.

예: `_Kazan_/Design/Monster/Human/Empire/Empire_SwordHArmor/Skill/01_SwordSwing_01/AC_EmpireSwordHArmor_SwordSwing_01_Step1`의 원시 `SequenceLength=2.0666666 s`, `DilationCurve.DilationSequenceLength=2.1666298 s`, `TimePerFrame=0.016666668 s`. 보정 클립은 저장된 시간 표의 역함수를 구간 선형 보간하여 원본 pose를 재표본화한다. Quaternion은 같은 회전 반구를 선택하고 정규화한 선형 보간을 사용한다.

재생 클립 722개 중 143개는 시간 보정에 의해 길이가 달라진다. 보정 출력은 원본 table의 시간 간격 또는 참조 시퀀스 sample rate를 기준으로 sample 수를 정하고, **정확한 목표 길이에 맞춘 유리수 frame rate**를 사용한다. 이 출력 rate는 원본 파일의 직접 기록값과 구분되는 계산값이다. 프레임 간 보간은 baked sample 해상도 범위의 근사이며 원본 런타임 전 과정과 완전 동일하다고 주장하지 않는다.

원본 root-motion flag는 원본 시퀀스에 보존한다. 재생 클립의 enable flag는 참조 시퀀스 중 root motion이 있는 경우 활성화한다. 이는 UE `FAnimTrack::HasRootMotion`의 기술적 동작을 따른 파생 설정이며, 원작 CMC/AI 이동 정책을 새로 확정하는 설정이 아니다.

엔진 5.8은 데이터 모델 rate와 압축용 `PlatformTargetFrameRate`를 구분한다. commandlet에서 해당 자산을 생성하는 동안만 `AnimationSettings.DefaultFrameRate`를 목표값으로 설정하고 두 rate를 함께 초기화한 후 즉시 되돌린다. change notification은 `NEVER`이며 프로젝트 Config에 저장하지 않는다. 기존 자산의 rate 변경으로 인한 resampling/압축 오차를 피한다.

절대 시간 기반 notify 4,863개의 원본/보정 시작·종료 시간은 `PlaybackEventTimes.json`에 보존한다. BBQ 전용 notify의 실행 로직을 가짜 UE notify로 대체하지 않는다. 원본 이벤트 class/속성은 Source JSON에 남긴다. Actor time dilation, AI 상태의 추가 배속, hit-stop은 별도 gameplay 계약이며 이 Art bake의 검증 범위 밖이다.

## 보존 자료와 한계

- 원본/선택/변환 정본: `Saved/Extracted/HeinMachEnemiesV2`.
- 프로젝트 메타데이터: `Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909`.
- 외부 원본 보관: `C:/Users/user/Desktop/카잔/EnemyExtracts/HumanoidExpansion_20260909`.
- cooked package 2,144개, source/derived 파일 9,219개와 SHA256을 보존했다. AES key나 FModel 설정 파일은 복사하지 않는다.
- 원본에 없는 `SI_EmpireSwordShield_SwordSwing_Turn_R` 참조 1개는 `SourceClosure.missing`에 기록했다.
- projectile/VFX timeline 26개, 선택한 외형이 사용하지 않는 elite shield 장비 timeline 1개, 원본 길이 0인 검색종료 clip 1개는 metadata만 보존한다. 임의 길이나 잘못된 skeleton을 배정하지 않는다.
- Cooked BBQ cartoon shader의 그래프는 제거되어 있으므로 UE DefaultLit 표시용 재구성을 사용한다. 원본 master/MI parent, scalar/vector/texture parameter, 색상·체형 프리셋 JSON과 raw cooked data는 보존하지만 원작 shader topology·RNG 색상 결과를 완전히 복구했다고 주장하지 않는다.
- 원본 LOD/morph/physics/cloth 정보와 raw/ActorX 파일은 보존한다. 현재 프로젝트 PSK importer가 원작 cloth simulation, morph/LOD chain을 자동 복원한 것으로 기록하지 않는다.

## 검증 상태

라이브 에디터에서 대량 shader graph 생성 중 메모리가 급증하여, 미저장 기존 변경이 없는 baseline과 백업을 확인한 뒤 에디터를 종료하고 NullRHI commandlet으로 재개했다. 새 라이브러리 생성과 cooked archive 감사는 통과했다. 애니메이션·BP·카탈로그·실제 RHI 및 보호 파일의 최종 검증 결과는 완료 후 아래에 추가한다.

## 2026-09-09 최종 임포트 및 검증 결과

요청한 의상·장비 중심의 대표 외형 16개를 저장했다. 검병 4, 검·방패병 4, 궁병 4, 중갑 대검병 1, 할버드 정예병 1, 별도 지역의 마법사 2개다. 얼굴은 001/002/003을 의상에 순환 배정했으며 얼굴마다 동일 의상을 중복 생성하지 않았다. 검·방패병의 상하의 공유는 원본 recipe와 일치한다. 추가 궁병 의상, 중갑, 두 종류의 로브로 외형 구성을 넓혔다.

장비는 검·방패·활/화살·대검·할버드·서로 다른 지팡이 2개이며 화살통도 원본 socket에 연결했다. 별도의 한손 도끼 일반병은 확인한 HeinMach spawn 목록에 없다. 도끼 모양 장병기는 HalberdElite로 구분한다. 무기를 임의로 다른 병종에 섞은 원작에 없는 조합은 만들지 않았다.

| 검증 | 실제 결과 | 보고서 |
|---|---|---|
| 외형·라이브러리 | 대표 BP 16, 통합 몸체 14, 원본/재사용 메시 36, 텍스처 256, 머티리얼 69 | `HeinMachEnemyV2_Library.json`, `HeinMachEnemyV2_Assemblies.json` |
| 애니메이션 | SourceSequence 711 + PlaybackClip 722 = 1,433개 저장 | `HeinMachEnemyV2_AnimationImportAudit.json` |
| 시간 오차 | 원본/계산 목표 길이와 UE 저장 길이의 최대 차이 `4.123535148892188e-7 s` | 위 보고서 `maximum_duration_error_seconds` |
| 포즈 오차 | 첫·중간·마지막 sample의 모든 bone을 RAW/COMPRESSED로 대조. 위치 `0.0001068115234375 cm`, quaternion 성분 `0.0007085800170898438`, scale `1.3113021850585938e-6` 이하 | 위 보고서 `maximum_pose_errors`, 20개 batch report |
| 실제 RHI | 머티리얼 69개 shader 통계, 텍스처 256개 sRGB, 저장된 BP 16개 construction·장비 부착 검증 통과 | `HeinMachEnemyV2_RenderAudit.json` |
| 최종 조립 방향 | 16개 모두 수직 방향 및 head/pelvis 높이 확인, 라이브 화면에서 서 있는 외형 확인 | `HeinMachEnemyV2_OrientationAudit.json` |
| 보존 | 백업 669개 hash 일치. 기존 Enemy 579개 무변경, 89개 Archive 이동, 기존 카탈로그 맵 1개 갱신 | `HeinMachEnemyV2_PreservationAudit.json` |

보고서는 `Saved/ImportReports`와 `Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/Reports`에 있다. 통합 결과는 `HeinMachEnemyV2_FinalAudit.json`이다. batch는 보고서 통과와 프로세스 정상 종료를 모두 확인했다. 애니메이션의 모든 프레임을 원작 게임 화면과 비교하거나 전투 PIE 속도를 검증한 결과는 아니다. Actor/Ability의 추가 배속·hit-stop은 앞서 적은 별도 경계다.

최종 화면 검수에서 `unreal.Rotator(0,-90,0)`가 UE 5.8 Python에서 pitch=-90으로 해석되는 오류를 발견했다. 새 BP 16개와 장비·카탈로그 조명은 `pitch=`, `yaw=`, `roll=`을 명시하도록 수정했다. 캐릭터의 수평 방향만 바꾸는 `pitch=0, yaw=-90, roll=0`을 적용했으며 애니메이션 키는 변경하지 않았다. 초기 화면의 누운 외형은 애니메이션 압축이나 FPS 문제와 구분된다. 최종 유효 화면은 `Saved/Screenshots/WindowsEditor/RiderMCP/20260909-023700_viewport.png`다. 후속 카메라 근접 캡처는 Slate에서 실패했으며 다른 캡처 API로 전환하지 않았다.

동일 basename `BASE_Normal`을 가진 `_Common/CommonTexture`와 `Art/Character/CHA_Material/Texture/Base`의 원본 package identity도 분리했다. 두 원본 PNG는 같지만 기존 텍스처는 백업과 byte 단위로 동일하게 복원하고 새 원본 package에는 별도 asset을 배정했다. `HeinMachEnemyV2_TextureIdentity.json`에 기록했다.

`KhazanAnimInstance.cpp`, Player ABP, 기존 DAS 시퀀스와 두 환경 맵은 시작 hash와 동일하다. 보호 파일 39개 중 33개가 그대로이며, 나머지 6개는 작업 중 외부에서 변경된 Animation/Engineering 문서다. 해당 문서는 이 Art 작업에서 편집하거나 되돌리지 않았다. 프로젝트 Config 4개도 시작 hash와 같다.

### 열어서 사용하는 순서

1. `/Game/_Art/Enemies/HeinMach/Preview/L_HeinMach_EnemyCatalogue`를 연다. 현재 에디터도 이 맵을 열어 둔 상태다.
2. `Humanoids/<병종>/Blueprints/BP_EN_*`를 배치한다. 마법사는 `OtherRegions/Humanoids`에 있다. 배치 BP는 외형 조립 Actor이며 전투 Pawn 구현과 구분한다.
3. 재생 동작을 고를 때 `Animations/PlaybackClips/A_EN_PLAY_*`와 `AnimationIndex.csv`의 OriginalPackage를 먼저 확인한다. 해당 클립은 구간 배속과 활성 DilationCurve를 반영했으므로 1배 재생한다. `SourceSequences/A_EN_SRC_*`는 가공 전 원본 시퀀스 시간축이다.
4. 중갑병의 애니메이션을 바꾸면 `EnemyBody`와 `EnemyArmor_Head/Upper/Lower`를 같은 클립·시간으로 갱신한다. 서로 다른 원본 bind pose를 유지하기 위한 조립 계약이다.
5. 원본 CB·recipe·장비·재생 시간은 `AssemblyCatalog.json`, `ImportManifest.json`, `AnimationImportManifest.json`, `PlaybackEventTimes.json`으로 추적한다. 간단한 조회는 `EnemyCatalogue.csv`, `AnimationIndex.csv`를 사용한다.

기존 얼굴 중심 BP 45개와 메시 44개는 `Archive/FaceVariants_20260908`에 보관했고, 이동된 89개를 다시 연 에디터에서 로드했다. 앞선 진행 기록의 “redirector 유지”는 디스크 저장 결과까지 확인한 표현이 아니었다. 최종 디스크에는 이전 경로의 redirector가 없으므로 과거 메타데이터의 경로는 `LegacyAssetMoves.json`으로 변환한다. 기존 원본 파일의 백업도 보존한다.

최종 manifest·CSV·보고서·파이프라인 스크립트·이 사용 문서를 외부 archive에도 동기화했다. `SHA256.json`은 보존한 source/derived 파일, `DeliverySHA256.json`은 최종 전달 자료의 hash 목록이다. 원작 전용 shader, 색상/체형 RNG, morph·LOD·cloth·physics, 전투 이벤트의 미복원 범위는 위 한계를 유지한다.

## 2026-09-09 후속 사용자 요청: 실사용 외형만 유지

이 문서의 확장 완료 이후 사용자가 불필요한 원본 캐릭터 제거를 요청했다. Archive의 예전 BP/몸체와 미사용 파츠·머티리얼·텍스처 총 195개를 Content에서 삭제하고 대표 BP 16개를 유지했다. 기존 Archive 경로는 더 이상 존재 목록이 아니다. 이전 원본/파생 manifest는 추출 당시의 기록으로 보존한다.

현재 inventory, BP 설명, 재생용 722개 중 시간축 변경 271개/동일 451개 분류, 삭제·검증 결과는 [ENEMY_LIBRARY_CLEANUP_AND_PLAYBACK_2026-09-09.md](ENEMY_LIBRARY_CLEANUP_AND_PLAYBACK_2026-09-09.md)와 `Metadata/Cleanup_20260909`를 우선한다. 애니메이션 1,436개는 이번 정리에서 삭제하거나 편집하지 않았다.
