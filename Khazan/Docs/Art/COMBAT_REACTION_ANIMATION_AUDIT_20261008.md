# Combat Reaction 애니메이션 감사

## 2026-10-08 — 7종 피격·공중·다운·회복 리소스 분류

이번 기록은 Player와 Swordsman, SwordShield(사용자 ShieldMan), HeavySwordsman, HalberdElite, ApesStoneHandElite, Yetuga의 **Art 분류와 제작 계획**이다. Source·에셋·에디터·PIE는 변경하거나 실행하지 않았다. 실제 제작/적용/런타임 검증 여부는 Engineering 기록과 해당 후속 receipt를 따른다.

기계 판독 결과는 `Metadata/CombatReaction_20261008/AnimationClassification.json`이다. 모든 현재 경로, 원작 package/AP field, 직접·Composite 구분, 원작 segment와 현재 bake 길이, 파일 SHA, 지원되지 않는 단계, 기존 브루탈 참조를 기록했다. 경로를 과거 Playback 이름으로 되돌리지 않는다.

### 조사 범위와 근거

- Enemy 정본 `ENEMY_ANIMATION_ORGANIZATION_20261007.md` → `Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv` 813행 → 선택 피격·가드·회복 후보 221개를 사용했다. 선택 현재 파일은 모두 존재한다. 전체 Content 조사는 하지 않았다.
- Apes/Yetuga의 별도 조회표 `Metadata/EnemyBehaviorResearch_20261008/CurrentApesYetugaLibrary.csv` 212행과 저장 원작 AP/Composite 캐시를 사용했다. 인간 AP는 `Content/_Art/Enemies/HeinMach/Metadata/Expansion_20260909/Source/BBQ/Content/_Kazan_/Design/Monster/Human/Empire/<원작 family>/Base_Setting/AP_*.json`의 export 0을 사용했다.
- Player는 `Saved/ImportReports/InGame_Playback_SequenceSnapshot_20261002.json`, `Metadata/InGamePlayback_20261002/PlaybackPlan.json`, 현재 `Shared/Combat/Reactions` 표적 파일 조회와 uasset 내 저장 TimingContract를 사용했다. Art 인덱스의 일부 2026-09-16 manifest 경로는 현재 파일이 없어 그 기록만으로 옵션을 확정하지 않았다.
- 기존 브루탈 24개 피해자 클립의 AP 대응은 `Metadata/MonsterStamina_20261008/AnimationPlan.json`, 실제 InGame 복제·몽타주는 `Authoring.json`과 `MainSavedReload_ConcurrentBuild.json`을 재사용했다. 이번 감사에서 새 저장본을 로드한 것으로 표현하지 않는다.

### 몸별 가능한 최소 계획

아래 이름은 각 family의 현재 `Animations/Damage` 안 시퀀스다. JSON에는 생략하지 않은 절대 `/Game` 경로가 있다. 인간 Art 기본 경로는 `/Game/_Art/Enemies/HeinMach/Humanoids/<Family>/Animations/Damage`, Apes는 `/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Animations/Damage`, Yetuga는 `/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Animations/Damage`다.

| 몸 | 짧은 피격 fixture | 큰 반응·다운 회복 후보 | 위로 띄워짐 후보와 제한 |
|---|---|---|---|
| Swordsman | `Damage_Normal_D_F` | F/B 각각 `Damage_Down_F/B` → `Damage_Down_Loop_F/B` → `Damage_Getup_F/B` | AP AirAnimation: F/B Up → Peak → Down → Land → DownLoop → Getup |
| SwordShield | `Damage_Normal_D_F` | F/B 각각 `Damage_Down_F/B` → `Damage_Down_Loop_F/B` → `Damage_Getup_F/B` | AP AirAnimation: F/B Up → Peak → Down → Land → DownLoop → Getup |
| HeavySwordsman | `Damage_Normal_D_F_Composite` | F/B 각각 `Damage_Down_F/B` → `Damage_Down_F/B_Loop` → `Damage_Getup_F/B` | AP DamageOnAirAnimMap 없음. 독립 Up/Peak/Down/Land 클립 없음. Down 재사용은 프로젝트의 별도 표현 계획으로만 취급 |
| HalberdElite | `Damage_Normal_D_F` | F/B 각각 `Damage_Down_F/B` → `Damage_Down_F/B_Loop` → `Damage_Getup_F/B` | AP AirAnimation: F/B Up → Peak → Down → Land → Getup. Landing Step2는 null이므로 원작 AP에 DownLoop가 연결됐다고 주장하지 않음 |
| ApesStoneHandElite | `Damage_Normal_D_F` | 독립 Down/DownLoop/Getup 쌍 없음. NoBlowDamage 대체 참조는 `Damage_Grapple_Atk_02` | NoAirDamage도 같은 피해자 2번 Composite. 인간 Air 단계를 강제하지 않음 |
| Yetuga | `Damage_Normal_D_F` | 독립 Down/DownLoop/Getup 쌍 없음. NoBlowDamage 대체 참조는 `Damage_Grapple_Atk_02` | NoAirDamage도 같은 피해자 2번 Composite. 인간 Air 단계를 강제하지 않음 |
| Player | `CA_P_Kazan_DualAxeSword_Off_DamageNormal_D_F` 등 | `Off_DamageAir_F/B` 전체 클립 → `Off_Down_Loop_F/B` → `Off_Getup_F/B`; 별도 QuickStand F/B/L/R 있음 | 현재는 source 전체 Air F/B만 확인. 독립 수평/수직 단계·구간 경계·AP 연결은 미확인이며 임의 절단하지 않음 |

인간형 Down 계획의 Start→Loop, Loop→Loop, End→None은 **현재 프로젝트에서 제작할 몽타주 링크 제안**이다. 원작 AP의 일반 Down 흐름이나 고정 hold 시간을 직접 확인한 것으로 기록하지 않는다. Up/Peak/Down은 CMC의 실제 상승·정점·하강·착지에 대응하는 후보이며, 모든 단계를 무조건 시간순으로 재생하는 원작 몽타주로 해석하지 않는다. 이번 감사에서는 발사 힘·중력·움직임·정렬 수치를 추가하지 않았다.

Swordsman/SwordShield/Halberd AP에는 AirAnimation과 별개로 BlowAnimation/BounceAnimation 항목이 있지만 확인한 단계 참조는 모두 null이다. 따라서 이름이 Down인 클립을 조립한 수평 launch 표현을 원작의 완성된 BlowAnimation 체인으로 부르지 않는다. **NoAirDamage/NoBlowDamage는 bool 면역 flag가 아니라 대체 애니메이션 참조 필드**다. Apes/Yetuga의 면역 여부 또는 피격 정책 자체를 이 필드명만으로 결정하지 않는다.

Apes AP `FallingAnimList`의 Start/Loop/End는 모두 `AC_M_ApesStoneHand_E_Falling`을 참조한다. 이것은 별도 공중 피격→다운→회복 체인을 제공한다는 뜻이 아니다. Yetuga의 GroggyStr/PartGroggy와 실제 exhaustion에 쓰는 GroggyStand/New를 피격 Air 클립으로 섞지 않는다.

### 방향·변형 선택

원작 AP `DamageDirectionSet`은 DamageWeak/Normal/Strong 및 DamageL/R/D/U를 구분한다. 방향 이름과 약/보통/강도를 하나의 무작위 풀로 합치지 않는다. `BackDamageDirectionSet`은 별도 D/U 반응이며, 앞 방향 네 개와 같은 조건이라고 추정하지 않는다.

Swordsman은 Normal과 Strong의 L/R/D/U 각각에 RandomDamageAnimations 2개가 저장됐다. 다른 다섯 enemy profile에서 확인한 무작위 배열은 Strong/D의 2개다. 해당 수치는 AP 원시 배열 길이이며 선택 가중치·확률은 확인하지 못했다. 기본과 `_2` 변형이 함께 저장됐으므로 기본 클립까지 중복으로 추가한 새 확률 분포를 만들지 않는다. Heavy의 `Damage_Normal_D_F_Original`은 직접 source, `_Composite`는 AP가 참조한 Composite bake다. 이름만 비슷하다는 이유로 교환하지 않는다.

### Player 경로·Guard 성공

현재 Player 반응 24개는 `/Game/_Art/Player/Animation/Weapons/DualAxeSword/Shared/Combat/Reactions` 아래 `Damage` 14개, `Airborne` 2개, `Down` 2개, `Recovery` 6개다. Recovery에는 Getup F/B와 QuickStand F/B/L/R가 있다. 현재 DAS InGame에 Damage 폴더/피격 복제본이 없으므로 gameplay 제작 시 선택한 클립만 InGame으로 복제하고 실제 bone/root/rate 옵션과 이미 보정된 타임라인을 보존해야 한다. 이번 감사는 복제를 실행하지 않았다.

현재 InGame Guard 성공 후보는 정확히 다음 세 경로다.

- `/Game/_Art/Player/Animation/InGame/DAS/Guard/Player_Guard_Suc_F`
- `/Game/_Art/Player/Animation/InGame/DAS/Guard/Player_Guard_Suc_L`
- `/Game/_Art/Player/Animation/InGame/DAS/Guard/Player_Guard_Suc_R`

2026-10-02 saved snapshot에서는 각각 duration 0.3333333432674408초, RateScale 1, EnableRootMotion false, ForceRootLock false, RefPose였다. 이것은 현재 새 UObject 재로드 결과가 아니다. 현재 파일 존재/SHA만 이번에 확인했다. Playback Composite/Common의 Guard_Suc 13개도 정확 경로와 원본 segment를 기록했지만 Normal/Just 및 D/U 후보를 기존 F/L/R 성공과 자동 동등하게 취급하지 않는다. Reflection은 별도 반응으로 분리한다.

### 수치·루트·기존 브루탈 보존

Enemy 후보 옵션/프레임/FPS/길이/RateScale은 CurrentAnimationLibrary의 원시 행을 보존했다. 후보 221개의 현재 파일 존재와 SHA는 확인했으며, 새로운 UObject 옵션 재읽기 또는 raw pose 일치 검사는 하지 않았다. 조회표의 RootMotion=true, ForceRootLock=true, AnimFirstFrame 계약을 source root 트랙 재작성으로 해석하지 않는다.

선택 원본 중 읽을 수 있는 Composite segment는 219개이고 AnimPlayRate=1, LoopingCount=1이었다. 이는 **Composite 내부 segment 소비 횟수**다. DownLoop/Peak 등의 이름이나 제안 몽타주 Loop→Loop와 구분한다. 18클립에서 serialized Dilation 필드를 찾았으며 활성/native 조건을 모두 판독한 것은 아니다. 현재 CompositeBake 길이에 원본 dilation을 다시 곱하지 않는다.

Swordsman/SwordShield/Halberd의 실제 비-null Air 단계에 저장된 StepNBlendTime은 0초다. 정확 AP file/field와 각 값은 JSON에 있다. 이 값은 phase-set 전이 blend이며 새 UAnimMontage BlendIn/BlendOut을 자동으로 0으로 해야 한다는 근거가 아니다. 일반 피격 몽타주의 blend 또는 hold time에 원작 근거를 찾지 못한 경우 author/runtime 소유자가 임시 튜닝값임을 표시해야 한다.

Player `.01`은 기존 mesh/component·삽입 root scale의 공간 계약이다. 재생률이나 source 시간이 아니다. Player 반응 uasset 내 TimingContract는 SourceTimelineReplacement 및 dilation_applied=false를 기록하며, 실제 새 옵션/rate는 저장본 readback 전 미확인으로 남겼다. `.01`을 타이밍에 적용하거나 기존 보정 root를 다시 bake하지 않는다.

기존 `AM_BrutalVictimFront/Back`의 Damage1/2와 Player `AM_DAS_BrutalFront/Back`는 JSON의 실제 saved montage 자료를 재사용했다. Victim2와 no-air/no-blow fallback이 같은 source여도 독립 피격 재생을 잡기/holding 수명과 혼동하지 않는다. 기존 브루탈 몽타주의 옵션/섹션/notify·자동 BlendOut을 이번 분류 때문에 재작성하지 않는다.

### 남은 확인과 재개

Player 원작 AP와 공중/다운 Composite의 현재 캐시·클립 구간이 추가로 확보되면 이 문서 하단과 JSON의 후속 evidence에 연결한다. 그전에는 위 Player full Air→DownLoop→Getup 계획을 원작 확정 체인으로 부르지 않는다. 실제 제작 후 fresh saved readback으로 선택 clone의 옵션/속도/프레임, montage section links/autoBlendOut, 취소·다운 hold·착지 후 Getup을 검증한다. 분류 보고서만으로 build/PIE/원작 시각 일치 완료를 선언하지 않는다.

## 2026-10-08 — 저장 루트 감사·충돌 형상 계산·임시 이동 수치의 후속 근거

이번 절은 앞선 분류의 **후속 Art 근거**다. 원본 트랙을 옮기거나 재임포트하지 않았다. Work 전용 충돌 author 도구는 작성됐지만, 이 절 작성 시점에 해당 도구의 실제 에셋 저장·fresh reload·접촉 PIE 결과는 아직 확인하지 않았다. Main 적용 또는 런타임 완료로 기록하지 않는다.

### 실제 루트 관측과 외부 이동 구분

Root가 별도 소유 Work 에디터에서 실행한 읽기 전용 스킬 감사는 `Metadata/CombatReaction_20261008/InPlaceReactionRootAudit.json`이다. report의 UE 버전은 `5.8.2-56702186+++UE5+Release-5.8`, 생성 시각은 `2026-10-08T20:37:25.635365` local, `read_only=true`, `status=passed`다. 이 절에서는 [unreal-root-motion-repair SKILL.md](C:/Users/user/.codex/skills/unreal-root-motion-repair/SKILL.md)의 실제 bone index 0/parent 없음·트랙 순서·소비 경계 원칙을 적용해 저장 보고서를 해석했다. 별도 에디터/PIE를 실행하지 않았다.

| 검사 시퀀스 | 실제 Skeleton root / 첫 트랙 | 저장 옵션·시간 | 관측 범위 |
|---|---|---|---|
| Player `Shared/Combat/Reactions/Airborne/CA_P_Kazan_DualAxeSword_Off_DamageAir_F` 및 `_B` | `C_P_Kazan`, index0, parent None / `c_p_kazan` | RateScale1, 30/1fps, 40frames/41keys, 1.3333333730697632초, EnableRootMotion=false, ForceRootLock=false, RefPose | 0/20/40프레임의 실제 root와 자식 `Root`는 translation/rotation 변화 0. 0/중간/끝 직전의 engine root extraction도 변화 0 |
| Swordsman `Damage_Air_F_Up` | `Root`, index0, parent None / `root` | RateScale1, 5000/167fps, 5frames/6keys, 0.16699999570846558초, EnableRootMotion=true, ForceRootLock=true, AnimFirstFrame | report sample에서 실제 root 변화·engine extraction은 0. `Bip001` 및 virtual foot bones의 pose 변화는 별개 |

이 결과는 **선택 sample 관측**이며 모든 프레임·모든 반응 클립의 동일성을 보증하지 않는다. Player 두 Air의 실제 root 트랙은 존재하고 먼저 저장돼 있으므로, “dummy root가 앞에 있어 이동을 잃었다”는 진단의 근거가 아니다. Swordsman `Bip001` pose 변화(감사 sample의 최대 위치 차이 약44.822646cm)는 몸의 표현이며 이를 실제 root/capsule 이동으로 옮기는 근거로 사용하지 않는다. 현재 제작 방향은 제자리 피격 포즈를 보존하고 엔진 RootMotionSource가 외부 이동을 담당하는 것이다. 이것은 프로젝트 실행 설계이며 원작 내부 이동 구현을 확인한 결과가 아니다.

`PlayerSourceRootReadback.json`은 Root가 소유한 Work PID24376의 기존 source24개 loaded readback이고 dirty_packages는0개다. 24개 모두 RateScale1이며, QuickStand4는 EnableRootMotion=true/ForceRootLock=true, Normal/Strong10은 EnableRootMotion=false/ForceRootLock=true, 나머지10은 false/false, 전부 RefPose로 읽혔다. 앞 절의 “fresh 옵션 미확인”은 이 **후속 Work source readback 범위**에서 보완됐다. 새 InGame clone의 저장본·Main의 현재 옵션까지 검사했다고 확대하지 않는다. source uasset의 TimingContract `dilation_applied=false`와 `.01` 공간 계약을 재생률에 다시 적용하지 않는다.

### 이동 수치의 소유자와 출처

현재 Work `Data/KZCharacterDefinitionData.h`의 `FKZHitReactionSettings`에는 `KnockbackDistance=250`, `LaunchDistance=120`, `LaunchHeight=150`가 저장된다. 단위는 엔진 RMS가 소비하는 **world cm**이며 CharacterDefinition의 조정 가능한 설정이다. 세 값은 어시스턴트가 선택한 **임시 프로젝트 튜닝값**이고 원작 AP/SD/curve 직접값 또는 사용자 지정값이 아니다. 제자리 반응 포즈에 식별 가능한 수평/수직 이동을 제공하기 위한 값이며, 실제 capsule 이동·착지·회복/취소 cleanup을 별도 native PIE로 확인해 조정해야 한다. 이 기록만으로 그 검증이 통과했다고 표현하지 않는다.

### Monster 공격 Box의 정확 계산과 지원하지 않은 형상

재사용 데이터는 `Metadata/CombatReaction_20261008/MonsterAttackCollisionPlan.json`과 동일 폴더의 `build_monster_collision_plan.py`다. 기존 AuthoringPlan/AttackExpansionPlan으로 현재 **35patterns/55nodes**만 선택했고 원본 Composite68개에서 xxAttack108개를 찾았다. Box100개는 원시 `Size`, `RelativeOffset`, `AbsoluteOffset`, 철자가 그대로인 `RelativeRotatoion`, `PostCleaningAttackInfo.AttackBoxList/Bounds`를 사용했다. `Size`를 half extent로 두고 offset/rotation 조합 네 가지의 box corner union을 원본 Bounds와 비교했다. 100개 모두 최대 오차0.001cm 이내이며 전체 최대 오차는 `0.00008216241923264533cm`다. 이 기준은 **계산 오차 QA**이며 gameplay 튜닝 수치가 아니다.

`LocalCenterPos`는 attachment 원점이므로 relative/absolute offset을 합성한 계산 center를 사용한다. 원본 key1448개에 이 계산을 적용했다. 원본 패턴 재사용을 현재 노드별로 펼치면 작성 계획은 Box113개/key1498개다. 원본 시간은 저장 dilation table/PlaybackEventTimes의 baked 시간으로 변환하고 `segmentStart + bakedTime/segmentRate - nodeSectionStart`로 현재 node-local seconds를 계산한다. 이미 bake된 시퀀스에 dilation을 다시 적용하지 않는다.

Source Bounds 일치는 원본 **형상 합성**의 근거이며 현재 monster capsule 기준 방향·scale·원점의 실제 정렬까지 검증한 결과가 아니다. Work helper는 실제 로드한 gameplay BP CDO mesh-relative location만 `CollisionToActor` translation으로 기록한다. mesh `.01`/yaw 또는 source bone transform을 또 곱하지 않는다. 기존 인간 author는 Art body transform 복사 후 capsule half-height만큼 로컬 Z offset을 적용한다(`MonsterAuthorEditor.cpp:470–473`, 당시 AuthoringPlan HH102/102/123.5/140cm); 이 과거 계획값을 현재 CDO의 새 readback이라고 부르지 않는다. Apes/Yetuga의 별도 BodiesAuthoring receipt는 direct CB mesh Z-240/-265cm와 Apes X-50cm를 기록하지만 이번 인간35 공격 범위에는 두 family의 공격 창을 추가하지 않았다.

Cylinder5개는 `BakingAttackDirections`만 있고 대응 PostCleaning Box geometry가 없다. Shape 미직렬화3개 중 Push2개에는 원점0의 Box keys만 있고 Bounds가 없다. AttackDirections의 CenterPosition을 충돌 center로 대체하거나 cylinder 높이를 추정하지 않았다. 따라서 **8개 unique/11개 현재 사용 occurrence는 자동 작성 제외**이며 plan 및 author receipt의 skipped 목록으로 남긴다. Kick Action, SwordSting Step1/Step2, GuardCounterRecovery Action의 선택 Composite에는 지원되는 xxAttack Box가 없으므로 임의 공격 박스를 만들지 않았다.

### 공격량·반응 분류·작성 상태

Monster HP10/Stamina5와 Blockable=true는 Root가 승인한 **프로젝트 임시 설정**이며 원작 절대 피해량·원작 불가드 flag는 미확인이다. 설정은 기존 충돌 Window에 모아 저장하도록 계획했다. Player는 현재18nodes/60windows의 실제 피해량·geometry·timing을 보존하며 예전 AuthorReport의 HP10/Stamina5를 다시 적용하지 않는다.

Player 반응 mapping 계획은 Short34/Knockback23/Launch3다. SD 관계45개는 명시된 DamageInfoIndex, 15개는 candidate SI index0 추론이므로 각각 표시했다. DamageStrong→Knockback은 프로젝트 세 분류 해석이며 원작 full knockdown 확인이 아니다. Launch3개는 ChargeAttack03의 explicit SD3개에 있는 upward height/force 또는 BounceDatas를 사용한 프로젝트 선택이다. UseCurve의 height/force만으로 원작 공중 상태 전이를 확정하지 않는다.

Work의 `CombatReactionCollisionAuthorEditor.cpp`는 EditorContext `Khazan.Combat.ReactionCollisionAuthor`, exact Work path/noPIE guard이며 기존 ComboDefinition36개(몬스터35+Player1)만 대상으로 한다. 기존 몽타주·시퀀스·BP·registry·draw 옵션은 변경 대상이 아니다. 실제 저장/재읽기 및 geometry 접촉 QA의 다음 근거는 Work `Saved/MonsterAI/CombatReactionCollisionAuthor.json`과 후속 native test receipt다. 이번 절 작성 시점에는 그 성공을 확인하지 않았다.

## 2026-10-08 — Player 피해량 기록 정정

현재 `/Game/Data/ComboCommand/DA_Player_Combo_Definition`의 18개 공격 노드·60개 window는 이미 저장된 `HPDamage=10`, `StaminaDamage=5`를 보존한다. 구조체 기본값0을 실제 Player 에셋 값으로 설명한 초기 기록은 정정한다. “예전 10/5를 다시 적용하지 않는다”는 앞 절은 기존 window의 실제 10/5를 복사·보존한다는 의미이며, 피해0을 뜻하지 않는다. 기존 fresh Main PID2512 readback 및 CombatReaction 전 Main/Work SHA와 최종 collision author/fresh Work readback이 이를 확인했다. 정확한 출처·SHA·수치의 미확인 원작/사용자 선택 상태는 [Engineering 정정 기록](../Engineering/COMBAT_REACTION_RUNTIME_20261008.md)에 남겼다.

이번 정정은 문서만 변경한다. Player 반응 분류와 geometry/timing, 시퀀스 raw/root/rate 및 몽타주 구성에는 새 변경이 없다. 피해0 접촉을 지원하는 Ability 정책과 실제 저장 피해량10/5는 별개의 사실이다.


<!-- CombatReactionMainComplete_20261010 -->
## 2026-10-10 — 분류·파생 몽타주 Main 저장본 검증 완료

이번 source/pose 정리의 Main 전달과 재로드가 완료됐다. 기존 Authoring_Final의97개와 CollisionAuthoring_Final의36 Definition의 공유3개를 제외한 합집합130개를 전달했다. source245 및 Player InGame 복제24의 실제 raw key/time/value/default와 재생률/root 계약을 fresh Work29152/Main16544에서 읽기 검증했다. 양쪽 각각654,552검사/실패0/필수 미지원0/dirty0, unique montage63/계획65·trimmed Loop16·Definition7·Guard3/window9·collision36/Monster113window/1498key·Player60window를 확인했다. 정확 증거는 [MainSavedReload](../../Metadata/CombatReaction_20261008/MainSavedReload.json), [WorkSavedReload](../../Metadata/CombatReaction_20261008/WorkSavedReload.json), [FinalVerification](../../Metadata/CombatReaction_20261008/FinalVerification.json)다.

다운 Loop16의0.3초 crop은 source 원본 길이·raw/rate를 바꾸지 않는 어시스턴트 임시 prone hold다. Player `.01` 공간 배율은 재생 시간이나 world displacement에 다시 적용하지 않았다. source root는 읽기 감사만 했고 child Root/Bip001 전사·재임포트·root track 수리는 하지 않았다. QuickStand4 후보는 InGame 정리만 했고 chain에 아직 연결하지 않았다.

Heavy matching Air가 없어 Short fallback, Apes/Yetuga는 원본 NoAir/NoBlow의 Damage_Grapple_Atk_02 전용 참조를 사용한다. 이를 면역 bool 또는 human air/down full chain으로 해석하지 않는다. Box source 합성100개/오차 최대0.0000821624cm는 원본 기반 계산 결과이고 Monster113 occurrence/1498key 저장과 실제3 collision contact는 별도 실행 근거다. unsupported11 occurrence는 추정 shape를 만들지 않고 제외했다. Player 기존18노드/60window HP10/Stamina5·geometry/time를 보존하고 반응 kind만 추가했다. Monster HP10/Stamina5·Blockable=true와 네 날림 window의 임시 선택은 원작 absolute 수치/면역 플래그가 아니다.

RHI32피격/15브루탈/3충돌와7PNG는 같은 production source의 Work에서 실제 수행했고 종료 후 임시 helpers를 제외한 stock DLL은 fresh Work/Main 저장 검증을 통과했다. 제한된 캡처/런타임 성공을 원작 전체 pixel/contact 동등성으로 확대하지 않는다. 원본 source 조사·Player retime·author/delivery를 반복하지 않는다. 조정·취소 책임은 [Engineering runtime 정본](../Engineering/COMBAT_REACTION_RUNTIME_20261008.md)의 최신 완료 절을 읽는다.


## 2026-10-12T19:30:36.993088+09:00 — 전체 정수 FPS·몽타주 표시 증폭 수정 Main 완료

원인: UE5.8 UAnimMontage::UpdateCommonTargetFrameRate가 호환되지 않는 source sampling rates를 만날 때 CommonTargetFrameRate를 무효화하고 UAnimCompositeBase의100000/1fps precision fallback을 사용한다. 원본 전체 inventory2674/158에서 fractional461/fallback36이었다. import의 (frames−1)/exact source or dilation duration으로 생성된 rational FPS가 근거이며 재생 자체가100000배 빨라진 것으로 혼동하지 않는다.

461 sequence를 nominal30/60Hz로 변환하고 frame-index bone keys3854855개를 그대로 보존했다. raw duration=Dnew=N/Fint, alpha=Dnew/Dold, RateScale_new=RateScale_old×alpha로 실제 seconds를 유지한다. notify/marker local seconds·embedded visual scalar/vector curve X와 slope/weighted tangent·montage source trim 좌표를 함께 변환했다. 원본 TimingContract/metadata는 보존하고 IntegerFPSRepair tag를 덧붙였다.45 의존 montage의 표시 sampling은 모두 정수다. montage DataModel 자체를 강제 정수 grid로 바꾸는 trial은 reload 시 실제 length를 반올림하여 철회했고, 원래 precision model clock은 보존했다.

fresh Main의 모든2674 sequence/158 montage에서 fractional sequence0/fallback0; MainSaved01은 실제 montage length 차이0·raw key/notify 일치를 확인했다. concurrent Main Niagara attack VFX88개는 최신 저장본에서 다시 보정하고 원본 pose hash/신규 notify를 보존했다. 현재 Enemy 조회는 Metadata/AnimationTimingKnockback_20261012/CurrentAnimationLibrary_IntegerFPS.csv(813행/270수정)와 전체 Plan/FinalVerification을 사용한다. 예전 CSV는 변환 전 역사값이다. original game metadata numbers와 clock 계산/knockback TEMP 표현은 구분한다. FPS 수정 과정에서 skeleton/root tracks/material/HP·ST/공격 geometry·world clock을 재저작하지 않았다.

## 2026-10-13 — Apes/Yetuga 가산 피격 Art 검증 완료, Main 파일 교체 대기

원본 `AB_ApesStoneHand_E` / `AB_Yetuga` CDO에 `xxAnimGraphNode_AdditiveBlend`, BlendTime=[0.1,0.1] seconds/Linear가 직접 확인됐다. 정확한 zip entry/export/field/hash는 `Metadata/GiantHitOverlay_20261013/OriginalConditions.json`이다. 원본 Normal L/R/D/U sequence에는 명시 additive field가 없으며 current imported clip은 full-pose다. 원작 custom node 실행 알고리즘은 미확인이다.

독립 Work에서 원본 full-pose8를 보존하고 game-facing sequence8와 montage8를 `/Game/Monsters/{ApesStoneHandElite|Yetuga}/Animations/Reaction/Additive`에 만들었다. 자체 첫 프레임을 기준으로 LocalSpace additive delta를 계산하고 root motion/추가 notify를 제거했다. 이는 프로젝트 표현 adapter이며 원작의 additive base pose를 직접 추출했다고 표현하지 않는다. frame count/FPS/length/rate는 current source를 그대로 유지했다. 0.1 s/Linear는 원작 custom node enter/exit blend 값을 engine montage blend에 적용한 원작 기반 adapter다. Slot group 추가 외 bone/ref pose/physics source는 편집하지 않았다.

Author01 저장 readback 8개, original sequence/montage16 hash 보존, RHI 피격 화면 및 실제 backbone pose 차이, 2026-10-13 CPU02 native 25조건을 확인했다. 정확한 source/개별길이/FPS/모듈/화면은 Author01/Authoring.json, CPU02/Native.json, PIE02/Family0_Case0_Flinch.png 및 Family1_Case2_Flinch.png를 따른다. Blueprint/runtime 구성과 특수 그로기 trigger 해석은 Engineering의 GIANT_NONINTERRUPTING_HIT_20261013.md에 별도 기록한다.

Main source 적용/compile은 Engineering 범위다. Art 파일 22개 중 새 clip/montage16 + 기존 Skeleton2/ABP2/Definition2의 Main 저장 교체는 기존 Main editor 파일 잠금으로 아직 수행되지 않았다. 원본의 기존 기록/수치는 덮어쓰지 않았다. 완전한 원작 native 그래프 일치나 부위 내구도 피해 환산 검증으로 확대하지 않는다.

## 2026-10-13 — Apes/Yetuga additive 반응 Art 에셋 Main 반영 완료

Main editor 종료 후 별도 Work에서 authoring readback한 새 sequence/montage 16개와 기존 Skeleton/ABP/Definition 6개를 Main에 반영했다. 저장된 Main 22개 에셋의 hash가 `DeliveryPlan.json`의 Work 검증본과 일치하고, 원본 full-pose sequence/montage 16개 hash는 유지된다. fresh Main PIE 25/25에서 두 거인의 네 방향 합성 포즈 및 일반 몬스터 기존 반응 회귀를 확인했다. Main 검증·이미지와 정확한 hash는 `Metadata/GiantHitOverlay_20261013/FinalVerification.json`을 따른다. 원작 custom additive node와 동일한 포즈 연산을 확인했다는 뜻은 아니다.
