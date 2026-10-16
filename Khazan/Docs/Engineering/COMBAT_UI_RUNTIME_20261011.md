# Combat UI 현행 구현 — 2026-10-11

## 책임과 현재 적용

ARCH-87에 따라 실제 Main에 `UKZCombatHUDWidget` h/cpp2개를 추가했다. 기존 local `AKZPlayerController::BeginPlay`가 configured Widget을 생성/AddToPlayerScreen하고 EndPlay에서 RemoveFromParent/참조를 정리한다. 기존 BP_PlayerController는 `/Game/UI/Combat/WBP_CombatHUD`를 사용한다. BP는 Native Widget을 상속하고 Class Defaults에서 원작 크기·위치 및 표시 보간 설정을 조정할 수 있다. 별도 Manager/FSM/ActorComponent와 gameplay 상태 사본은 없다.

Widget의 NativeTick은 game thread에서 현재 Pawn, ASC의 HP/MaxHP/Stamina/MaxStamina, 기존 LockOn/BrutalAbility를 읽는다. WidgetTree/UPROPERTY가 UI를 보유하고 actor는 약한 참조다. 보간값은 presentation에만 존재하며 실제 피해·회복·비용·소진을 변경하지 않는다. player 변경 시 표시를 새 속성값으로 초기화하고, pawn 없음/죽은 대상/actor 파괴와 EndPlay를 처리한다.

현재 BP 몬스터6종의 실제 `Bip001-Head`에 머리 위 게이지 기준을 설정했다. Yetuga만 `bUseBossCombatHUD`와 이름 `예투가`, HalberdElite/Apes만 elite backdrop을 사용한다. BP CharacterDefinition/GAS 초기 수치와 AI/animation/VFX 설정은 유지한다. 새 UI property는 실제 소비가 있는 actor별 presentation 설정이다.

## TargetPoint와 브루탈

LockOnComponent의 읽기 전용 `GetCurrentTarget()`은 IsLockedOn일 때만 현재 actor를 반환한다. UI의 점은 해당 Monster의 **기존 GetLockOnTargetPoint**에서 취하고 UWidgetLayoutLibrary로 local player viewport/DPI를 변환한다. 머리 게이지와 록온 지점을 같은 위치로 임의 대체하지 않는다. 화면 밖/뒤/Visibility blocker는 표시를 숨긴다.

Brutal은 실제 granted spec의 `CanActivateAbility`와 `FindBrutalTarget`을 사용한다. 실행 중 spec에는 B를 표시하지 않는다. 소진·상대 readiness·사망·거리·정면·visibility·GAS 활성화 정책을 재구현한 bool 대신 기존 Ability 판단을 소비한다. 표시 대상과 실제 행동을 일치시키기 위해 FindBrutalTarget은 기존 모든 적격 조건을 통과한 locked actor를 우선하고, 없으면 기존 최근접 적격 actor를 선택한다. 다른 action 취소/비용/피해/paired montage/alignment 수명은 이 작업에서 수정하지 않았다.

록온 상태에서는 같은 대상의 실행 가능 여부에 따라 일반 reticle→원작 Xbox B glyph/브루탈 ring으로 전환한다. 록온이 없어도 실제 Ability가 선택한 실행 가능 대상에 B를 표시한다. 원작 UI의 X 모양 이미지와 Xbox B glyph를 구분한다. 원본 출처/색/위치는 [Art 감사](../Art/COMBAT_UI_SOURCE_AUDIT_20261011.md)를 따른다.

## 표시 보간과 정책

HP/Stamina는 `Clamp(Current/Max,0,1)`이며 Max<=0/비정상 값은0으로 안전하게 표시한다. 첫 관측은 실제 값으로 초기화한다. 이후 `Display += (Target-Display) * (1-exp(-DeltaTime/Seconds))`를 양방향에 동일하게 적용한다. 연속 회복/연타마다 easing 시작을 재설정하지 않아 움직이는 target에서도 표시가 멈추지 않는다. 새 gameplay literal이나 회복 timer를 추가하지 않았다.

`GaugeSmoothingSeconds=.35초`는 **임시 표시 튜닝값**이다. 원작 `InterpolationTimeMultiply=.35`는 native 공식/단위가 미확인이므로 원작 시간이라고 주장하지 않는다. WBP Class Defaults에서 조정한다. 영향은 표시 지연뿐이며 GT ASC 값은 즉시 반영된다. 조정 기준은 양방향 가독성·연속 회복 추종·피해 후 수렴이다. `HeadPadding8cm`/`MonsterDiscoverySeconds.25초`도 원작 native 근거 없는 표시용 임시값이다. 크기/앵커/색/폰트는 Art 감사의 직접 확인값 또는 명시된 계산/adapter다.

normal/elite는 onscreen/clear view에 머리 위 HP/Stamina를 표시한다. Yetuga는 첫 visible candidate 또는 locked boss를 선택하고 생존/표시 감소가 끝날 때까지 top HUD로 유지한다. native arena/VM 조건은 metadata에 없어 이 선택·유지 정책은 프로젝트 adapter다. HP0에서 위젯을 즉시 제거하지 않고 lethal 표시 감소를 마친 후 사라지게 한다. 원작 native 조건 전체 일치/복수 보스 운영/네트워크·Shipping 검증은 완료 범위와 구분한다.

## 검증 기록

Build02/03/04/05/06은 stock Editor target 성공이다. 초기 Build01은 UWidget::Slot을 가리는 지역 변수로 실패해 작은 이름 변경으로 해결했고, 미초기화 경고도 수정했다. 최신 build/source/module receipt를 최종 보고서와 결속한다.

ConfigureEditor03에서6 BP head/boss 설정과15texture/native fallback Controller를 확인했다. 뒤 보완에서16texture/font/WBP_CombatHUD/BP_PlayerController 연결을 저장했고 `SavedReadback01`의 새 Main commandlet exit0/read-only 검사를 통과했다. ConfigureEditor04의 마지막 보고용 ParentClass protected 접근은 실패했으나 저장한 제품은 fresh readback으로 확인했다. 보호된 부모 property를 읽는 대신 실제 Native PIE Cast/tick으로 상속을 확인한다.

Main 실제 RHI PIE01은 초기 UI/ASC 보간/TargetPoint/B/granted Ability 실행·취소/소멸 검사를 통과했다. PIE02는 새 WBP/폰트/배경/피해·회복/lethal/Max0까지 수행했으며 마지막 UnPossess 단계에서 fixture가 Pawn의 null Controller를 재조회하여 실패했다. UI의 local Controller 소유 수명은 유지됐다. fixture가 원래 Controller 약한 참조를 유지하도록 수정하고 Build06 후 PIE03에서 전체를 다시 검증한다. Python은 별도 프로세스 lifecycle만 담당하고 gameplay/입력은 native fixture다. 다른 에디터 제어·저장·PIE는 하지 않았다.

## Main 통합 범위

이전에 완료된 MonsterVFX/GiantCombatFall/PlayerAttackVFXPolish/HeinMachCleanPresentation은 Main 전달 receipt가 존재한다. `BackgroundMainAudit01.json`에 기록하고 과거 worktree 전체를 복사하지 않았다. 현재 이어지는 별도 `CombatPresentationFix_20261011`의 native/Art 후속은 아직 verified delivery 전이다. Source delta와 현재 Main을 `BackgroundSourceDelta01.json`으로 비교했다. 최신 검증 완료 시 함수별 작은 병합으로 ARCH-87의 LockOn getter/FindBrutalTarget 우선 정책, Monster UI 설정, UMG/Slate module과 새 BP 설정을 보존해야 한다. 실패한 이전 NativeAfter01/02를 완성 작업으로 재전달하지 않는다.
## 2026-10-11 — 최종 Main UI 완료 / shader 검사 보강

UI는 [FinalVerification](../../Metadata/CombatUI_20261011/FinalVerification.json)의 `MainDeliveredAndFreshVerified` 상태다. 최종 실제 Main 실행은 `PIEEditor05_FinalShader`이며 stock MainBuild02 DLL, native 전체 기능 검사 Success, material compile failure/fallback0, Exit0이다. 원작 이미지16·FontFace1·UI material2·WBP와 BP7을 포함한 Content27/Source10의 현재 SHA를 결속했다. 표시 설정은 `/Game/UI/Combat/WBP_CombatHUD` Class Defaults에서 조정한다.

PIE03/04의 기능 검사는 성공했으나 Shader fallback 검사가 부족했다. 후속 VFX 검사에서 BrutalRing의 Custom RGBA→ComponentMask 두 입력이 연결되지 않은 것을 발견했다. UE의 default input pin 이름은 빈 문자열이며 `Input`이라는 이름의 이전 호출은 연결하지 못했다. 기존 노드의 두 연결만 보완하고 원본 기반 radii/color 및 analytic 식을 유지했다. RingRepair01은 저장 후 Unreal Array 보고 직렬화에서 실패했으므로 RingRepair02의 성공 기록과 새 RHI PIE05를 최종 근거로 사용한다. 검사 driver도 material fallback을 실패로 판정하도록 보강했다. 현재 링과 B glyph의 실제 표시를 확인했다.

ARCH-86 후속 병합 후에도 록온 적격 대상 우선 선택, 실제 B 실행 조건, 원작 폰트/배경, ASC 양방향 보간, lethal 감소·소멸, Max0 및 UnPossess/RePossess가 전체 재검사를 통과했다. 원작 cooked shader/VM/native 보간식의 완전 복원·pixel/frame parity·멀티플레이/Shipping 성능은 여전히 검증 범위 밖이며 구현 adapter/임시 수치를 원작 직접 확인값으로 바꾸어 기록하지 않는다.

## 2026-10-12 — ARCH-88 가슴 표식·즉시 게이지 반응 적용

이후 현재 UI 계약은 실제 UI_Chest socket(Bip001-Spine2, local identity)을 매 프레임 projection하는 LockOn/B, actual ASC 비율의 즉시 foreground, 감소 때만 보관하는 HP/ST damage trail이다. 과거 TargetPoint 표시/양방향 .35초 foreground 보간 설명은 이 범위에서 대체한다. gameplay LockOn camera/targeting의 기존 TargetPoint와 Ability 적격 조건은 유지했다. GaugeSmoothingSeconds=.35초는 이제 감소 잔상만의 TEMP 설정이며 회복은 즉시 반영한다.

CurBar BackgroundImage는 원작 alpha0에 맞게 NoDraw로 하고 원작 gradient alpha를 별도의 M_UI_GaugeBackground에서 표시한다. dark track(.015,.015,.015), ST trail alpha.35, EliteFrameSize124×22는 어시스턴트 TEMP로 구분한다. 원작 Recover tint/gradient Mid·alpha/source package는 Docs/Art/MONSTER_PRESENTATION_REPAIR_20261011.md 마지막 수치 절을 따른다. 기존 B ring A-only/feather 및 radius/색은 보존했다.

MainUI02 실제 RHI Success/fallback0/Exit0에서 HalberdElite의 damage/recovery, chest projection/visible normal ring/eligible B·실제 Ability, lethal0·Max0·UnPossess/RePossess를 확인했다. 02/03/04 PNG를 직접 검사했다. MainUI01은 다른 saved NPC가 표식 시야를 가려 UI만 screenshot에서 보이지 않을 수 있었으며 own test subjects를 분리하는 QA 배치만 보완했다. 제품 occlusion 테스트·target eligibility를 약화하지 않았다. 현재 code는 UI Widget h/cpp/Monster socket 최소 수정이며 새 UI runtime class0이다.

## 2026-10-14 — Combat HUD 해상도별 가독성 조정

사용자가 현재 UI가 저해상도로 보인다고 지적했다. 기존 원작 HUD 텍스처는 HP 1440×28, 스태미너 1440×12, 록온 168×168, B 64×64이고 UI compression/NoMipmaps/NeverStream 상태다(원본·임포트 출처는 `Docs/Art/COMBAT_UI_SOURCE_AUDIT_20261011.md`). `WBP_CombatHUD`의 Player 360×8, Monster 100×6, Boss 720×10, LockOn 60×60, B 38×38 logical px 설정은 저장본에서 원작 레이아웃 값과 일치했다. 흐릿해 보이는 주된 원인은 UE 기본 `UIScaleCurve`가 작은 PIE 뷰포트에서 이 크기를 크게 축소하는 것이었다.

실제 제품 변경은 `Config/DefaultEngine.ini`의 `[/Script/Engine.UserInterfaceSettings]`에 `UIScaleRule=ShortestSide`와 임시 표시 곡선 `480px→0.8, 720→1.0, 1080→1.3, 2160→2.6, 8640→10.4`를 추가한 것뿐이다. 이는 **어시스턴트 선정 TEMP UI 가독성 값**이며 원작 metadata 수치가 아니다. 화면 짧은 변을 기준으로 900px에서는 1.15(엔진 기본 약 .833), 1080px에서는 1.3배가 된다. 계산상 1080p 물리 높이는 Player HP 약10.4px, Monster HP 약7.8px, Boss HP 약13px, B 약49px이다. 작은 약450px PIE 화면에서는 최소 .8배를 사용하고 Boss 프레임 폭은 약787px이므로 기존 약1090px 게임 뷰포트에 들어온다. 수치 기준은 판독성과 화면 내 배치를 함께 확보하는 것이며 원작 동일 배율을 주장하지 않는다.

별도 소유한 1600×900 D3D12 PIE의 동일 `Khazan.CombatUI.PIE` 실행은 변경 전 `Metadata/UIQuality_20261014/BaselinePIE02`, 변경 후 `ImprovedPIE01` 모두 Success, material compile fallback0이었다. 실제 04_BrutalAvailable_B PNG의 붉은 영역 측정에서 Boss HP 표시가 491×8→687×11px, B 원형이 28×28→40×40px로 늘었고 두 화면을 직접 검수해 잘림·사각형 알파 경계가 없음을 확인했다. 플레이어/일반 적/보스 자원, 가슴 록온, B 전환, 공격 실행/취소, 치명/소유권 수명 검사도 기존 native fixture에서 통과했다. 텍스처·폰트·머터리얼·WBP·게임 C++ 수정0이므로 새 빌드는 필요하지 않았고, 기존 실행 중인 에디터는 프로젝트 Config를 다시 읽도록 정상 재시작해야 한다. 720p/1080p/4K 개별 실제 캡처와 원작 pixel parity는 이번 검증 범위가 아니다.

## 2026-10-15 — HP0 즉시 LockOn 해제·Yetuga 잡기 재잠금 실제 적용/PIE 완료

기존 LockOnComponent가 잠근 대상 ASC의 HP delegate를 소유한다. HP<=0 callback 안에서 현재 타깃·자기 이동 constraint·delegate를 즉시 해제하며 검색/시작/유지에서도 HP>0 및 Dead 아님을 검사한다. 삭제/종료는 기존 StopLockOn/EndPlay 경로로 정리한다. 다른 대상의 이전 HP callback이 새 잠금을 풀지 않도록 같은 해제 경로에서 구독을 제거한다. UI는 기존 GetCurrentTarget 관측을 유지한다.

MonsterPatternAbility의 성공한 BeginCapture에서 CharacterDefinitionAssetName이 Yetuga인 경우 잡힌 local Player의 잠금을 해제한다. 성공 전 miss/실패에는 재잠금 예약을 만들지 않는다. 기존 CaptureEffect/attachment cleanup 완료 후 같은 Controller가 같은 Pawn을 계속 소유하고 Player/Yetuga가 살아 있을 때 StartLockOn으로 잡았던 Yetuga를 직접 다시 잠근다. 카메라에서 다른 몬스터를 재검색하지 않는다. 정상 종료와 살아 있는 상태에서의 강제 취소는 동일 cleanup, Yetuga HP0/소멸 또는 플레이어 HP0/소멸/소유권 해제는 재잠금 거절이다. 잡힌 동안 monster attachment가 있으면 신규 잠금이 거절되어 수동 Toggle로 다시 잠기지 않는다. gameplay HP/Dead/Ability 실행 원본과 애니메이션 자산은 변경하지 않았다.

새 runtime 파일/class0, 기존 runtime5 및 Config1/DEV2만 수정했다. EditorBuild01~03 Succeeded. 실제 RHI CombatUI.PIE(PIE01)에서 진동2배 설정 로드/HP0 동기해제/tick종료/죽은 대상 거절/old delegate 해제를 통과했다. GiantFall.PIE(PIE02_Giant) 14패턴과 기존 낙하/점프 공격 흐름에서 Yetuga CloseGrab/RushGrab 성공·held 중 잠금 금지·완료/취소 재잠금·captor HP0 시 재잠금 금지가 통과했다. PIE01의 lethal fixture가 사망 montage까지 HasRootMotionSources로 판정한 실패는 DEV 검사를 자기 OriginalPatternMoveTo receipt에 한정해 수정했고 실패 로그를 보존했다. 최종 소스diff/각 DLL·실행 근거는 Metadata/LockOnRumble_20261015/{Changes.patch,ChangedFiles.json,PIE01,PIE02_Giant}. 새로운 패키징은 진행 중이며 패드 실물 체감/원작 일치 검증은 하지 않았다.


### 2026-10-15 — LockOn 후속 HeinMach Shipping 완료

앞선 실제 PIE 완료에 이어 Package06_LockOnRumble Shipping compile/cook8590/0error/UATexit0, 최종 container의 HeinMach 단일 map·ForceFeedbackScale2·Epic 설정과90초 offscreen 시작을 확인했다. 배포는 C:/Users/user/Desktop/Khazan_Release_20261015/Windows 전체 폴더다. 정확 source/module/package hash와 각 검증 한계는 Metadata/LockOnRumble_20261015/FinalVerification.json. 필수 잔여0이다.

<!-- LockOnRumble_20261015_complete -->
