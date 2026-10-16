# 2026-10-07 Enemy 애니메이션 분류·이름·Root Motion

## 대상과 현재 적용 상태

사용자 직접 수정 요청이다. HeinMach Humanoids의 Swordsman, SwordShield, HeavySwordsman, HalberdElite 및 Yetuga, ApesStoneHandElite를 대상으로 한다. Archer는 제외한다. 2026-10-07 이번 절의 결과는 별도 MonsterWork의 실제 저장 결과이며 메인 전달·최종 검증은 하단 완료 절에 따로 기록한다.

| Art 라이브러리 | 시퀀스 수 | 현재 루트 경로 |
|---|---:|---|
| Swordsman | 181 | `/Game/_Art/Enemies/HeinMach/Humanoids/Swordsman/Animations` |
| SwordShield | 91 | `/Game/_Art/Enemies/HeinMach/Humanoids/SwordShield/Animations` |
| HeavySwordsman | 77 | `/Game/_Art/Enemies/HeinMach/Humanoids/HeavySwordsman/Animations` |
| HalberdElite | 115 | `/Game/_Art/Enemies/HeinMach/Humanoids/HalberdElite/Animations` |
| Yetuga | 120 | `/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations` |
| ApesStoneHandElite | 92 | `/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations` |

Art 676개와 기존 gameplay 93개를 합쳐 기존 시퀀스 769개를 정리했다. 새 공격에 필요한 gameplay 복제본 44개를 추가해 현재 검사 대상은 813개다. 기존 gameplay 몽타주 33개도 같은 목적별 폴더로 옮겼고 신규 공격 몽타주 22개를 추가했다. 폴더/이름 변경은 에디터의 Rename API와 참조 갱신으로 수행했다. Skeleton/mesh/texture의 이름과 토폴로지, 캐릭터 스케일은 이 작업의 수정 대상이 아니다.

## 분류와 이름 계약

| 폴더 | Art 시퀀스 수 | 의미 |
|---|---:|---|
| Idle | 85 | 미발견 정지 대기와 대응 End, Talk |
| Locomotion | 145 | 이동·대치 Stand·방향별 Walk/Run·Turn/Stop 등 |
| Attack | 142 | 공격과 해당 준비·반복·타격·회수 단계 |
| Damage | 233 | 피격·넘어짐·잡기 피해자 반응 등 |
| Death | 18 | 사망 |
| Guard | 17 | 독립 가드/방어 반응 |
| Alert | 20 | 발견·전투 준비·경계 |
| Equip | 5 | 무기 착용/수납 |
| Interaction | 5 | 발리스타 등 별도 장치 의존 동작 |
| Recovery | 2 | 독립 회복/일어남 |
| Prop | 3 | 별도 바위 등 소품 애니메이션 |
| Pose | 1 | 기준 포즈 |

접두사 `A_EN_PLAY`, 반복된 `AC/CA/M/EN/Boss`, 캐릭터/병종 이름, 임포트 hash 꼬리를 제거했다. 목적 prefix와 실제 방향·단계·변형은 남긴다. 예: `A_EN_PLAY_AC_EmpireSword_Pierce_Step1` → `Attack/Attack_Pierce_Step1`, Halberd `Basic_Loop_02` → `Idle/Idle_Loop_02`, `LockOnWalk_L` → `Locomotion/Locomotion_LockOnWalk_L`. gameplay 시퀀스는 기존 `/Game/Monsters/<Family>/Animations/InGame/<Category>` 아래에서 같은 이름을 쓴다. 몽타주는 `/Animations/<Category>/Montages`에 있다.

동일 목적 이름의 직접 원본 타임라인과 Composite 파생본은 `_Original`/`_Composite`로 구분한다. 필요한 경우 안정적인 Variant 번호를 더한다. 서로 다른 원본을 같은 이름으로 덮어쓰거나 삭제하지 않는다. `DownUpperSlash`는 Damage가 아니라 Attack, `SprintSwing`도 이동이 아니라 Attack이다. `Pierce_LockOnWalk_B`는 실제 방향 이동 용도다. `FootSword`는 저장 원본 `Moving/PeaceIdle/AC_EmpireSword_UnEquip.json`의 참조를 근거로 Equip에 둔다. DamageGrapple의 피해자 동작 이름에 `Atk`가 있어도 현재 melee 공격 후보로 간주하지 않는다.

## Root Motion 옵션과 소비 계약

모든 대상 시퀀스는 `EnableRootMotion=true`, `ForceRootLock=true`, `RootMotionRootLock=AnimFirstFrame`로 저장했다. Root Motion을 재생할 때 실제 root 변화를 추출하고, 포즈에는 처음 프레임의 root 기준을 사용한다. 원본 bone 키·곡선·RateScale·샘플률·시퀀스 길이를 수정하거나 재임포트하지 않았다.

현재 4종 NPC ABP의 `RootMotionFromMontagesOnly`는 유지한다. 공격 및 대기/발견 End 등 실제 몽타주에서 root delta를 CMC가 소비한다. Navigation 보행/추격은 기존 CMC 구동과 방향별 포즈·Foot Placement를 유지한다. 모든 시퀀스의 옵션 활성화는 보행까지 `RootMotionFromEverything`으로 구동하는 별도 구현과 같지 않다. Yetuga/Apes의 AI 구현을 이번 에셋 정리 완료로 해석하지 않는다. root가 정지한 클립은 옵션을 켜도 이동량이 생기지 않는다.

`unreal-root-motion-repair` 절차로 before hash/복제 probe/실제 skeleton root 및 첫 트랙/참조 scale/추출을 검사했다. 기존 769개는 Root 765개, Weapon_R 1개, B_Rock 3개다. 모두 skeleton index 0과 첫 트랙이 일치한다. pelvis/Bip001이 움직이는 in-place 포즈를 dummy-root 문제로 판단해 root에 옮기지 않았다. 루트 트랙 재작성 및 Skeleton topology/Actor scale 보정은 없다. 대표 scale 검사와 전부의 index/track 검사를 구분한다.

## 메타데이터와 검증 근거

원본 export CSV는 역사적 원본/파생 경로를 보존한다. 현행 경로는 `Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv`를 사용한다. 이 표는 current/legacy/original package, timeline derivation, frame/FPS/seconds/RateScale/root/options를 연결한다. `RenamePlan.json`, `MontageRenameApplied.json`, `Preflight.json`, `SavedAnimationAudit.json` 및 immutable `BeforeManifest.json`/`Before`가 대응 관계와 byte backup의 근거다.

모든 raw pose key와 float/transform curve, authored sync marker, 재생률/프레임 및 선택 메타데이터를 native 검사한다. 압축 root 샘플은 엔진 codec/리샘플링 정밀도가 있으므로 원본 raw key의 동일성 검사와 분리한다. 최초 .001cm tolerance는 실제 최대 .0060654cm 차이에 실패했다. 최종 .01cm 및 normalized quaternion 1e-4rad는 기술 QA 허용 오차이며 gameplay 튜닝값/원작 수치가 아니다. 실패 로그를 보존한다. 최종 native 성공 여부는 완료 절을 따른다.

AssetTools 참조 갱신의 catalogue 처리 지연과 debugger engine 심볼 부재는 continuity/실패 로그에 기록했다. 최종 남은 Yetuga rock redirector는 fresh registry refs 0 확인 뒤 정확한 2개 package 명령으로 제거했다. 첫 명령의 이미 없는 옛 경로 에러와 두 번째 0-error 성공을 구분한다. 검사한 fresh 저장 상태에 남은 옛 패키지는 없다.

런타임 공격/재추격의 소유자·조건·임시 수치는 [Engineering 정본](../Engineering/MONSTER_ATTACK_ROOT_MOTION_20261007.md)에 기록한다.


## 2026-10-07 18:43 KST — Enemy 정리·공격·Root Motion Main 완료

실제 Main 반영 완료다. Archer 제외 HeinMach Humanoids4종 및 Yetuga/ApesStoneHandElite의 Art676, 기존 gameplay93을 purpose12폴더와 의미 이름으로 정리했다. 신규 gameplay44를 더해 현재813시퀀스, 기존 montage33과 신규22를 더해55montage다. Idle/Locomotion/Attack/Damage/Death/Guard/Alert/Equip/Interaction/Recovery/Prop/Pose이며 방향·단계·변형은 보존한다. A_EN_PLAY/중복 AC·CA·M·EN·Boss·캐릭터 접두사와 hash tail을 제거했다. 겹치는 direct source/Composite는 Original/Composite로 구분한다. CurrentAnimationLibrary.csv가 current→legacy→original source/frame/FPS/length/RateScale/root/options의 조회표다. 과거 export CSV는 historical 원본이며 수정하지 않았다.

813개 EnableRootMotion=true/ForceRootLock=true/AnimFirstFrame을 저장·fresh Main readback했다. 4NPC의 기존 RootMotionFromMontagesOnly로 공격/End 몽타주 root delta를 CMC가 소비한다. Nav 보행은 기존 CMC/velocity pose/Foot Placement를 유지하며 RootMotionFromEverything 보행 구현이라고 부르지 않는다. Yetuga/Apes는 library/options 정리이지 신규 AI 구현이 아니다. index0/first track audit769의 Root765/Weapon_R1/B_Rock3을 유지했다. raw pose19M/곡선·재생률 비교와 compressed extraction tolerance를 구분한다. source pose/root 트랙·Skeleton topology/scale/Player .01·재생속도/재임포트 수정은 없다.

Rename참조 갱신 후 옛802 packages는 fresh registry/commandlet 및 Main hash 확인으로 실제 제거됐다. source assets의 imported actor/catalogue 참조도 갱신했다. 실패 fixup와 QA 로그를 지우지 않았다. Archer177개 hash는 전달 전후 동일하다. Main stock build·813 saved reload/dirty0를 완료했다. 자산별 분류·이름·원본 출처는 ENEMY_ANIMATION_ORGANIZATION_20261007.md 및 Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv를 따른다.


## 2026-10-12T11:04:18+09:00 — 사용 애니메이션 Root88 / VFX basis·scale Main 완료
현재 사용395개/body392+prop3에 대해 Root 옵션/track을 확인하고 native first/mid/end1176포즈를 검사했다. Animation88의 first-frame 누적 origin을 RefPose lock으로 정렬했다. Root raw channels, 전체 model·notify392 SHA, 모든 timing/Root enable/force/normalized scale 및 original resources는 보존됐다. exact imports 기준 수치는 RootLockPlan.json의 first-root/skeleton reference 필드이며 신규 원작 튜닝값이 아니다. actor 좌표의 root-stripped source collision에 live body scale을 한 번 반영, socket 없는FX는actor orientation+mesh origin/offset·size body scale 적용. VFX198/1577 및 death6는 delivered Source와 동일한 private RHI Success이고 Main current canonical/freshRoot·HP30·Player16·saved 원본 유지가 Success다. active correction-curve rows0 / 원작 native·pixel parity·전체두레벨·network는 완료 검증으로 표현하지 않는다. Metadata/MonsterRootCollisionRepair_20261012/FinalVerification.json 및 ResumeState03.json, MainBefore/RootAssetsBefore 백업을 따른다.


## 2026-10-12T19:30:36.993088+09:00 — 전체 정수 FPS·몽타주 표시 증폭 수정 Main 완료

원인: UE5.8 UAnimMontage::UpdateCommonTargetFrameRate가 호환되지 않는 source sampling rates를 만날 때 CommonTargetFrameRate를 무효화하고 UAnimCompositeBase의100000/1fps precision fallback을 사용한다. 원본 전체 inventory2674/158에서 fractional461/fallback36이었다. import의 (frames−1)/exact source or dilation duration으로 생성된 rational FPS가 근거이며 재생 자체가100000배 빨라진 것으로 혼동하지 않는다.

461 sequence를 nominal30/60Hz로 변환하고 frame-index bone keys3854855개를 그대로 보존했다. raw duration=Dnew=N/Fint, alpha=Dnew/Dold, RateScale_new=RateScale_old×alpha로 실제 seconds를 유지한다. notify/marker local seconds·embedded visual scalar/vector curve X와 slope/weighted tangent·montage source trim 좌표를 함께 변환했다. 원본 TimingContract/metadata는 보존하고 IntegerFPSRepair tag를 덧붙였다.45 의존 montage의 표시 sampling은 모두 정수다. montage DataModel 자체를 강제 정수 grid로 바꾸는 trial은 reload 시 실제 length를 반올림하여 철회했고, 원래 precision model clock은 보존했다.

fresh Main의 모든2674 sequence/158 montage에서 fractional sequence0/fallback0; MainSaved01은 실제 montage length 차이0·raw key/notify 일치를 확인했다. concurrent Main Niagara attack VFX88개는 최신 저장본에서 다시 보정하고 원본 pose hash/신규 notify를 보존했다. 현재 Enemy 조회는 Metadata/AnimationTimingKnockback_20261012/CurrentAnimationLibrary_IntegerFPS.csv(813행/270수정)와 전체 Plan/FinalVerification을 사용한다. 예전 CSV는 변환 전 역사값이다. original game metadata numbers와 clock 계산/knockback TEMP 표현은 구분한다. FPS 수정 과정에서 skeleton/root tracks/material/HP·ST/공격 geometry·world clock을 재저작하지 않았다.


## 2026-10-15 ? PartGroggy Loop?End4? ?? ?? Main ??

Yetuga? ApesStoneHandElite? ?? ??170 sequence? ??? Damage_PartGroggy_Loop/End ? ?? clip? RootMotionRootLock? ANIM_FIRST_FRAME?REF_POSE? ????. ??? ?? /Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Damage ? /Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Damage ???. EnableRootMotion/ForceRootLock? ?? ?? ?? ????. imported RAW ? Root ??(-2.670138359,-522.141235352,0)? skeleton reference Root(0,0,0)? ?522.148cm? ?? pose? ?? ?????, ?? ?? reference lock?? ????. actor/mesh scale ???? Root ????? ?? ???.

?? RAW frame?bone? pose hash/???????notify?4? ?? ??, native ?? DataModel/Notify SHA?170? ?? ??, ???166? ?? hash? ????. skeleton hierarchy/?? ??/???rational FPS?curve?attribute/Marker/VFX?audio ??? ????. FModel ?? ???/????/??? ???0??. ?? ?? ??? metadata/?? pose ???? ??? ?? gameplay ???? ???? ???.

?? duplicate/fresh native probe ? Main? ????, fresh RootPose170/510??? weak-part/???D3D12 Start/Loop/End6??? ????. ??4?? ?? locked root offset?522.148?0cm?. 8? HitAdditive? ???? ?? overlay?? ?? root off? ????. ?? Source/???8? ??? ??? Engineering MONSTER_ATTACK_ROOT_MOTION_20261007.md ?? ?? ??. ?? ? ???SHA?backup: `Metadata/GiantRootUsage_20261015/FinalVerification.json`. ?? probe1?? ???? ??4?? ????.

