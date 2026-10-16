"""Append the Main persistence recheck to the two domain records."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
report = json.loads((Path(__file__).parent / "SavedReadback.json").read_text(encoding="utf-8"))
assert report["status"] == "passed" and report["asset_saves"] == 0


def append(relative, section):
    file = ROOT / relative
    marker = section.strip().splitlines()[0]
    if marker in file.read_text(encoding="utf-8"):
        return
    with file.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("\n\n" + section.strip() + "\n")


append("Docs/Art/ART_PROJECT_STATE.md", """
## 2026-10-15 — Apes·Yetuga 잡기 경고 Main 저장본 확인

메인 반영 여부 재확인 요청에 따라 새 UE 에디터 프로세스에서 7개 잡기 애니메이션의 원본 경고 ParticleSystem·SoundWave 연결을 읽었다. 7개 파일 SHA가 2026-10-14 최종 저작본과 모두 같고, 원본 경고 PS의 9 emitter와 4.360875초 SoundWave, UI_Chest/카메라 배치/구간 종료 분리 설정이 유지된다. game asset save 0 및 검사 전후 모든 대상 SHA 동일이다. 따라서 미반영·중단된 임포트/Notify 적용분은 없다. 증거는 `Metadata/GiantGrabWarning_20261015/SavedReadback.json`, 원본·시각 검증·shader 한계는 `GIANT_VFX_REFINEMENT_20261013.md`의 2026-10-14 잡기 경고 절이다. 오늘 새 원본 추출·shader 저작·PIE 화면 검사를 수행한 것으로 읽지 않는다.
""")

append("Docs/Engineering/ENGINEERING_PROJECT_STATE.md", """
## 2026-10-15 — Apes·Yetuga 잡기 경고 Main 반영 유지 확인

현재 Main `KZAnimNotify_CombatEffect.cpp/.h`의 경고 camera-facing 분기가 존재하며, 새 UE 에디터 프로세스에서 7개 애니메이션의 VFX/audio state 설정을 재확인했다. 두 종의 7개 capture node/12개 판정창은 모두 bBeginsCapture=true·bBlockable=false이며 기존 Combo 적중 분기가 일반 가드/패링 호출을 건너뛴다. 병행 GiantCamera의 중복 대상 4개 clip/4개 camera event도 누락 0이다. 검사 asset save 0·전후 SHA 동일, 이전 최종 7개 애니메이션 SHA 일치, 미반영 중단분 0이다. 오늘 근거는 `Metadata/GiantGrabWarning_20261015/SavedReadback.json`과 `MainSavedEditor.log`(exit 0). 이전 Main 빌드와 실제 D3D12 PIE 근거는 `Metadata/GiantGrabWarning_20261014/Build02.log`, `PIE/RuntimeReport.json`이며 오늘 다시 빌드/PIE한 결과와 구분한다. 직접 Guard-held 잡기 통합 사례와 원작 shader/DSP 전체 일치는 기존 미검증 범위를 유지한다.
""")

append("Docs/Art/ART_WORK_CONTINUITY.md", """
## 2026-10-15 — 잡기 경고 적용 중단분 없음 재확인

2026-10-14 잡기 경고 적용은 Main에 완료돼 있으며 2026-10-15 새 프로세스의 7개 saved binding/9 emitter/음향 로드·최종 SHA 검사도 통과했다. `Metadata/GiantGrabWarning_20261015/SavedReadback.json`이 최신 저장 여부 근거다. 원작 shader·동일 프레임 비교 한계는 위 2026-10-14 continuity 그대로이며 미반영된 에셋이나 중단된 저장 작업을 뜻하지 않는다. 전체 author/import/옛 DLL 전달을 다시 실행할 필요가 없다. 이후 실제 외관 수정 요청이 오면 위 원본 비교 절차에서 이어간다.
""")

append("Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md", """
## 2026-10-15 — 잡기 경고 Main 적용 중단분 없음 재확인

7개 경고 애니메이션과 7 capture node/12 창의 방어 불가 설정, 중복 4개 camera Notify를 새 프로세스에서 확인했다. 소스·에셋 재적용 없이 검사가 통과했고 검사 중 game asset save 0이다(`Metadata/GiantGrabWarning_20261015/SavedReadback.json`). 현재 Main 반영을 위해 재개해야 할 저장/전달/빌드 작업은 없다. 위 2026-10-14 Guard-held 별도 통합 사례는 추가 검증의 미확인 범위로 유지한다. 오늘 검사를 새로운 PIE·원작 동일성 검증으로 확대하지 않는다.
""")
