"""Append the observed grab-warning result without replacing earlier project records."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def append(relative, marker, section):
    target = ROOT / relative
    current = target.read_text(encoding="utf-8")
    if marker in current:
        return
    with target.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("\n\n" + section.strip() + "\n")


append("Docs/Art/GIANT_VFX_REFINEMENT_20261013.md", "Apes·Yetuga 잡기 경고 UI·SFX 원본 복원 (2026-10-14)", r"""
## Apes·Yetuga 잡기 경고 UI·SFX 원본 복원 (2026-10-14)

FModel 원본 증거는 `Metadata/EnemyBehaviorResearch_20261008/YetugaOriginal/AC_Yetuga_CloseGrab_Start{,_Ori}.json`, `AC_Yetuga_RushGrab{,_Slow}.json` 및 `Metadata/EnemyBehaviorResearch_20261008/ApesOriginalEvidence.json`의 `xxHoldingAttackWarning` NotifyState다. 원본 경고 리소스는 `BBQ/Content/_Kazan_/Art/VFX/VFX_Particle/UI/FP_UI_BurstAttact_Grab`(Cascade 9 emitters: mesh 6, sprite 3), 텍스처 `FT_UI_BurstAttack_Font`, `_Blur`, `FT_Splash_Decal_02`, 메시 `FS_BurstA_001~003`이다. `ParticleModuleColorOverLife_12~17.ColorOverLife.Table.Values`의 처음 RGB는 `(5, 2.5, 0)`, 0.25 normalized time의 끝 RGB는 `(0.1, 0, 0)`이고, BG `_11`은 `(0.5, 0.25, 0)`에서 `(0.1, 0.05, 0)`이다. CameraOffset 원본 모듈은 10/50/80/99~102 cm 값을 갖는다. 원본 UI음 후보는 `BBQ/Content/_Kazan_/Sound/Ui/ui_holding_attack`, EventId `1713520362`, `BBQ/Content/WwiseAudio/Media/881646502.wem`이다. 복원 PCM은 48 kHz stereo, 4.360875초다. 독점 `xxHoldingAttackWarning` 네이티브 구현의 직접 particle/audio 참조는 추출 metadata에 없으므로 Notify 이름과 전용 asset·sound 명칭의 대응은 **근거 있는 추론**이지 원본 실행 코드의 직접 확인은 아니다.

원본 Notify와 현행 clip의 재생률/시간축을 대조해 `Metadata/GiantGrabWarning_20261014/WarningPlan.json`에 7개 창을 기록했다. 현행 적용초는 Yetuga CloseGrab Start/Ori `0.426349079~0.601462825`, RushGrab `0.300323580~0.469503228`, RushGrab_Slow `0.431678243~0.627242855`; Apes CloseGrab Start `0.0001~0.264423162`, Start2_Stone `0.000139266~0.468124387`, Start_Stone `0~0.268416542`다. 이는 원본 property 직접값이 아니라 원본 Notify 시점과 현행 재생축의 **계산 적용값**이다. 원본 추출 메타데이터와 계산 근거는 위 `WarningPlan.json` 및 `Scripts/Art/prepare_giant_grab_warning_20261014.py`에 남겼다.

원본 텍스처·PSKX와 9-emitter Cascade 그래프를 Main의 `/Game/_Art/Effects/Combat/GrabWarning/`으로, 디코딩한 원본 media를 `/Game/Audio/Original/Media/SW_UI_HoldingAttack`으로 가져왔다. 원본 cooked shader graph는 확보할 수 없어 세 Material은 마스크·particle alpha와 sharp/blur 텍스처를 사용하는 프로젝트 어댑터다. `FM_BurstAttack_BG`의 2x2 atlas 첫 cell 선택도 어댑터다. 원본 shader/믹싱·DSP/픽셀 일치로 표시하지 않는다. 기존 몬스터 VFX를 제거하거나 대체하지 않고 `UI_Chest`의 별도 GrabWarning 트랙에 추가했다. Apes의 0초 단발 오디오 Notify가 실제 PIE에서 건너뛰어져, 7개 모두 원본 경고 창과 같은 시작의 `KZAnimNotifyState_PlayAudio`로 바꾸고 유한 sound tail을 보존했다.

초기 Main PIE는 경고 PSC 8~9개 active particle과 양 종의 원본 음향 로그를 보였지만, UI가 몸체에 묻혀 화면에서 보이지 않았다. 원본 PS의 단독 실제 게임 렌더 `Metadata/GiantGrabWarning_20261014/ParticlePreview/Frame_93.png`는 검은 붓획과 금빛 섬광을 보여 재질 전체 실패가 아님을 분리했다. `KZAnimNotify_CombatEffect`의 명시적 UI용 옵션은 `UI_Chest` 위치에서 실제 mesh world AABB 앞면을 카메라 방향으로 계산해 배치·회전한다. 새 gameplay 수치 literal은 없으며 이 화면 배치는 원본 네이티브 구현이 확인되지 않은 **기술 어댑터**다. Notify 창 종료 뒤 `OnNotifyEndDeattach`로 잔여 입자를 분리한다. 마지막 Main RHI `Metadata/GiantGrabWarning_20261014/PIE/RuntimeReport.json`은 `Khazan.GiantFall.PIE` 성공, 경고 재생 5회, Apes/Yetuga active particle 및 `SW_UI_HoldingAttack` 로그 양성이다. `PIE/Yetuga_0.png`, `Apes_2.png`와 후속 캡처에서 두 몬스터 앞의 붓획/금빛 플래시와 사각 텍스처 경계가 드러나지 않는 것을 눈으로 확인했다. `SavedReadback.json`은 7개 asset의 UI·음향 state·분리 설정과 이전 단발 음향 0개를 새 에디터에서 재확인했다. 원작 실게임 같은 프레임과의 나란한 픽셀·청감 비교는 아직 수행하지 않았다.
""")

append("Docs/Engineering/APES_YETUGA_FALL_IMPLEMENTATION_20261011.md", "잡기 방어 불가와 원본 경고 연결 (2026-10-14)", r"""
## 잡기 방어 불가와 원본 경고 연결 (2026-10-14)

Main의 Apes `Dodge_A_Step8/12`, `Level_DashAtk_New_Step8/12`, Yetuga `CloseGrab_Step1`, `RushGrab_Step3/5` 저장 판정창은 모두 `bBeginsCapture=true`, `bBlockable=false`다(`Metadata/GiantGrabs_20261013/FreshReadback.json`). `KZComboActionAbility.cpp` 적중 경로는 먼저 `TryDodgeHit(..., Window.bBeginsCapture)`를 호출하며, 그 다음 `Window.bBlockable && ... TryGuardHit(...)`에서만 일반 방어·Perfect Guard/Parry를 실행한다. `KZAbilitySystemComponent.cpp::TryDodgeHit`는 capture의 `bDodgeOnly`가 true일 때 활성 회피 Ability의 `TryAvoidHit` 성공만 허용한다. 따라서 현재 데이터와 실행 분기상 두 종 잡기는 가드·패링할 수 없고 성공한 회피만 무효화한다. 기존 태그/Ability 수명은 변경하지 않았다.

원본 `xxHoldingAttackWarning`에 대응한 전용 Cascade·SoundWave를 기존 `KZAnimNotifyState_MonsterVisual` + `KZAnimNotify_CombatEffect`, `KZAnimNotifyState_PlayAudio` 경로로 7개 AnimSequence에 추가했다. `KZAnimNotify_CombatEffect`에는 기본 false인 `bFaceCameraOutsideMeshBounds` 한 설정만 추가했다. 켜진 이 UI effect는 기존 `UI_Chest` 소켓을 쓰되 카메라 방향의 mesh world AABB 앞면으로 원점을 옮기고 화면을 향하게 한다. 위치는 현재 mesh bounds의 투영으로 계산하며 수치 튜닝 상수를 새로 두지 않았다. 일반 전투 effect는 이 경로를 사용하지 않는다. 경고 state가 끝나면 기존 `OnNotifyEndDeattach`를 사용해 유한 Cascade tail을 소켓에서 분리한다. 추가 manager/component/상태 복제는 없다.

Main `Build02.log`의 UE5.8 KhazanEditor 빌드 성공, `CameraFacingAuthorReport.json`의 7개 저장·비소유 Notify 보존, `SavedReadback.json`의 새 프로세스 7개 재확인을 마쳤다. 중간에 병행된 GiantCamera 작업은 같은 Yetuga clip 4개에 camera state를 추가했고 `Metadata/GiantCamera_20261014/OverlapMergeFinal.json`의 병합 성공을 확인한 뒤 본 경고 설정을 다시 저장했다. 마지막 `Metadata/GiantGrabWarning_20261014/PIE/RuntimeReport.json`은 Main D3D12 `Khazan.GiantFall.PIE` 성공, 실제 Apes/Yetuga GrabWarning 발생 각 양성, 원본 음향 5회 및 active particle 양성이다. 경고 UI는 최종 PNG에서 눈으로 확인했다. 이 fixture는 기존 실제 잡기·취소·착지 경로를 검증하지만, 두 종의 잡기를 실제 Guard 입력을 계속 누른 채 맞는 별도 통합 사례나 원작 픽셀 동일성까지 주장하지 않는다. 방어 불가 결론의 직접 근거는 저장된 공격창과 위 short-circuit 실행 분기다.
""")

append("Docs/Art/ART_WORK_CONTINUITY.md", "잡기 경고 원본 비교 잔여 (2026-10-14)", r"""
## 잡기 경고 원본 비교 잔여 (2026-10-14)

Main의 Apes·Yetuga 잡기 경고 PS/SFX와 7개 Notify 적용, 빌드, 새 프로세스 저장 재검사, Main D3D12 PIE는 통과했다. 마지막 근거는 `Metadata/GiantGrabWarning_20261014/{AssetImportReport.json,WarningPlan.json,CameraFacingAuthorReport.json,SavedReadback.json,PIE/RuntimeReport.json}`과 `PIE` PNG다. FModel cooked shader graph와 `xxHoldingAttackWarning` 독점 실행 구현은 확보되지 않아 원작 화면의 픽셀·시간별 알파·Wwise 믹스 일치는 미확인이다. 특히 Apes가 몸을 낮추는 긴 경고 창에서는 `UI_Chest`를 따라가는 파티클이 낮게 보이는 프레임이 있다. 원작 같은 프레임의 영상이 있으면 이 잔여를 비교해야 한다.

재개 순서: `0_DOCUMENT_ROUTER.md` → `Docs/Art/GIANT_VFX_REFINEMENT_20261013.md`의 이번 절 → `WarningPlan.json`/원본 `TelegraphMetadata`·`VisualMetadata` → 최종 `PIE/RuntimeReport.json`과 PNG를 읽는다. 원작 grab UI 영상의 동일 공격·카메라 시점과 직접 대조해 위치/알파/수명 차이만 기록하고, 필요한 경우 기존 Material 어댑터 또는 7개 Notify 설정만 표적 수정한다. 수정 뒤 `verify_giant_grab_warning_saved_20261014.py`와 `giant_grab_warning_pie_20261014.py`를 재실행해 7개 저장 및 양 종 화면·음향을 확인하고 Art 문서 하단에 실제 결과를 추가한다. 원본 9-emitter 그래프를 무근거로 일괄 재임포트하지 않는다.
""")

append("Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md", "Apes·Yetuga 잡기 경고 통합 검증 잔여 (2026-10-14)", r"""
## Apes·Yetuga 잡기 경고 통합 검증 잔여 (2026-10-14)

저장 공격창의 `bBlockable=false`와 `KZComboActionAbility` short-circuit상 가드/패링이 호출되지 않는 것은 확인했다. 마지막 Main UE 빌드 `Metadata/GiantGrabWarning_20261014/Build02.log`, 7개 Notify 저장 재검사 `SavedReadback.json`, D3D12 전투 fixture `PIE/RuntimeReport.json` 모두 성공이다. 특정 잡기 창에 대해 실제 Guard 입력을 지속하는 플레이어의 HP·스태미너/Parry callback을 계측한 별도 PIE 사례는 아직 없다. 원본 네이티브 UI 내부 배치도 직접 확인되지 않았다.

재개 순서: `0_DOCUMENT_ROUTER.md` → `Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md` → `CHARACTER_TAG_ABILITY_MIGRATION.md`의 현행 단계 → `APES_YETUGA_FALL_IMPLEMENTATION_20261011.md` 이번 절 → `KZComboActionAbility.cpp:1344`·`KZAbilitySystemComponent.cpp:16`과 `FreshReadback.json`을 확인한다. 필요 시 기존 GiantFall/Parry fixture에 Guard held + Apes/Yetuga grab 실제 접촉 한 사례씩만 추가해 HP 감소, Guard/Parry 반응 미발생, 회피 성공 예외를 검증한다. 같은 Yetuga clip을 바꾸는 GiantCamera `OverlapMergeFinal.json`과 본 `SavedReadback.json`의 양쪽 Notify가 유지되는지도 새 프로세스에서 확인한다. 수정 후 Main 빌드와 대상 PIE를 다시 돌리고 Engineering 문서 하단에 실제 결과를 추가한다.
""")
