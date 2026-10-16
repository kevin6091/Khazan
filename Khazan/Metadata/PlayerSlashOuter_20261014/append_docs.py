"""Append, never replace, this task's dated Art and Engineering records."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]
records = {
    'Docs/Art/PLAYER_ATTACK_VFX_PLAYBACK_20261008.md': '''

## 2026-10-14 — 플레이어 KZ_Slash 전 공격 배치 검수 및 바깥쪽 확대

현재 게임 공격에서 KZ_Slash를 참조하는 다섯 몽타주(Weak/Strong/StrongCharge/DodgeAttack/SpinningAttack)의 추가 효과 33 start/end쌍을 모두 조사했다. 실제 공격 몽타주, 무기 좌·우 tip 이동, 3시점의 초·중·후 프레임을 대조했다. 첫 프레임 좌·우 자동 선택이 차지와 동시 양손 효과에서 잘못 결속되던 구간은 공격별 실제 움직임과 원래 child 배치를 확인해 명시적 무기로 지정했다. 같은 프레임의 두 효과는 각기 해당 무기로 분리했다. WeakAttack01의 기존 오른손 교정은 유지했다.

추가 효과 32쌍의 무기 바깥 거리와 XY 크기를 공격별로 조정했다. 최종 거리는 25–100cm, 평면 크기는 1.12–1.25배다. 이 수치는 **원작 메타데이터 값이 아닌 이번 시각 검수의 TEMP 튜닝값**이며 각 Notify의 `WeaponSlashOutwardOffsetCm`/`Scale3D`에 보관한다. 거리 방향은 매 프레임 캐릭터에서 실제 무기 끝으로 향하는 지면 평면 방향이다. 회전은 여전히 실제 무기의 스윙 접선과 칼날 방향을 따른다. 기존 WeakAttack02의 사용자 편집 가능 Sequencer 곡선 한 쌍은 실제 프레임에서 검토하고 그대로 보존했다. 공유 KZ_Slash/재질/메시는 이번 작업에서 수정하지 않았다.

격리본에서 추가 효과 단독 99장과 원래 효과 합성 99장, 메인에서 공격 재생 288장을 캡처했다. 합성 검수에서는 차지·약공격·회피·스핀의 붉은 Slash가 무기 밖으로 드러나면서 원래 흰색/회색 효과와 함께 재생됐다. 다섯 저장 몽타주를 새 프로세스에서 다시 읽어 추가 33쌍, 원래 효과 객체 882개 내용, Notify 시간·GUID 보존을 확인했다. 전체 배치와 공격별 수치·캡처·저장 해시는 `Metadata/PlayerSlashOuter_20261014/FinalVerification.json`, 대표 비교는 `Candidate3OnlyRHI01/PairSheet_*.jpg`와 `Candidate3ComposedRHI01/PairSheet_*.jpg`다. 원작 게임의 동일 시점 영상과 픽셀/셰이더 완전 일치는 이번 검증이 아니다.
''',
    'Docs/Engineering/COMBAT_PRESENTATION_FOLLOWUP_20261011.md': '''

## 2026-10-14 — ARCH-95 KZ_Slash 무기 바깥 배치 계약 Main 완료

기존 `UKZActionAbility`의 finalized-bone effect receipt에서 실제 장착 무기의 좌·우 선택, tip, 스윙 접선, 절삭면을 계속 계산한다. 추가 효과 Notify에 `WeaponSlashOutwardOffsetCm` 하나를 추가하고 기존 leading mesh endpoint 위치를 구한 뒤 캐릭터→실제 tip의 지면 평면 방향으로 이 거리만 이동한다. 칼날 방향만 따라 밀면 차지 타격 중 칼끝이 몸을 향하는 프레임에서 효과도 몸 안쪽으로 들어오는 문제가 있어 방향을 분리했다. 값 0은 기존 배치를 유지한다. Sequencer 소유 WeakAttack02와 원래 Cascade/Decal, 수명·취소·피해·오디오는 건드리지 않는다. 새 runtime class/component/manager/tag/file은 없다.

다섯 몽타주 33쌍 중 32쌍의 좌·우 무기와 크기·거리만 변경했다. 수치는 25–100cm/XY 1.12–1.25배의 **TEMP 시각 튜닝**이며 원작 값으로 표현하지 않는다. 격리본의 원본 해시 확인·T3D 허용 field diff·백업 후 메인 에셋 5개를 SHA 비교/교체했다. 새 프로세스 저장 재검사는 원래 효과 882개와 Notify 시간·GUID가 동일하고 WeakAttack02 Sequencer 두 객체가 변하지 않았음을 통과했다. Main `KhazanEditor` 빌드 및 실제 D3D12 `Khazan.CombatEffect.PIE`가 성공했고 GPU 입자 끝점 68건의 목표 위치 최대 오차는 0.000042cm다. 실제 로드된 표준 DLL SHA, 작업본의 단독/합성 캡처, Main 288장과 저장 에셋 영수증은 `Metadata/PlayerSlashOuter_20261014/FinalVerification.json`에 결속했다. 이 오차는 현행 무기 marker/추가 효과 계약 검수이지 원작 영상 픽셀 일치나 Shipping 성능 증명이 아니다.
''',
    'Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md': '''

## 2026-10-14 — ARCH-95 플레이어 KZ_Slash 바깥 배치 계약 보완

기존 추가 Slash의 실행 소유자와 정상/취소 cleanup은 Action Ability effect receipt 그대로다. finalized pose에서 선택한 실제 무기의 스윙 접선(X)·절삭면(Y)으로 회전을 만들고 매 프레임 실제 tip에서 캐릭터 바깥쪽으로 `WeaponSlashOutwardOffsetCm`를 적용한다. 이 값은 Notify별 TEMP 시각 데이터이며 기본 0이다. 첫 프레임 추정 선택이 틀리던 공격은 저장 Notify의 좌·우 무기 이름으로 확정했다. 기존 원래 VFX·WeakAttack02의 Sequencer 소유권, ASC 상태·피해 경로는 유지하며 새 실행 상태나 manager는 추가하지 않는다. Main 저장·빌드·실제 PIE 근거는 `Metadata/PlayerSlashOuter_20261014/FinalVerification.json`이다.
''',
    'Docs/Art/ART_WORK_CONTINUITY.md': '''

## 2026-10-14 — Player KZ_Slash 전 공격 바깥 배치 완료 및 원작 시각 비교 잔여

메인 몽타주 5개/33쌍 중 32쌍의 추가 Slash 배치를 수정했고 WeakAttack02의 편집 가능한 Sequencer 한 쌍은 프레임 검토 후 보존했다. 격리본 단독·합성 각 99장과 Main 288장, 원래 효과 882개/시간·GUID 보존의 마지막 근거는 `Metadata/PlayerSlashOuter_20261014/FinalVerification.json`이다. 원작 게임의 동일 시점/카메라 영상과 직접 픽셀 비교는 하지 않았고 25–100cm/1.12–1.25배는 TEMP 값이다. 재개 시 Router→PLAYER_ATTACK_VFX_PLAYBACK 최신 절→FinalVerification의 공격별 tuning/PairSheet와 현재 Main 다섯 SHA를 읽고, 원작 동일 프레임이 있으면 효과 외곽·색감·밀도만 표적 비교한다. 필요한 Notify 값만 바꾼 뒤 기존 효과882/33쌍 저장 재검사와 D3D12 실제 재생을 반복한다.
''',
    'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md': '''

## 2026-10-14 — ARCH-95 Player KZ_Slash 바깥 배치 Main 검증 완료

현행 Action finalized-pose receipt에 Notify별 캐릭터→무기 tip의 지면 평면 바깥 거리만 추가했다. Main 빌드, 별도 백그라운드 메인 D3D12 `Khazan.CombatEffect.PIE`, 실제 GPU endpoint68/최대 오차0.000042cm, 저장 에셋5/원래 효과882/Notify 시간·GUID 검사가 성공했다. 마지막 실제 DLL/asset/source SHA와 백업은 `Metadata/PlayerSlashOuter_20261014/FinalVerification.json`·`MainApply/Receipt.json`이다. 작업 소유 에디터는 모두 종료했다. 후속 시각 조정은 Router→Architecture ARCH-95 최신 절→COMBAT_PRESENTATION_FOLLOWUP 최신 절→현재 Main Source/asset SHA 순으로 시작하고, 임시 숫자를 원작 근거로 격상하지 않는다. 새로운 조정 후 표준 빌드·저장 readback·실제 GPU PIE를 다시 실행한다. 원작 게임 픽셀 동일성 및 Shipping/network 성능은 별도 검증 범위다.
''',
}

for rel, addition in records.items():
    path = root/rel
    existing = path.read_text(encoding='utf-8-sig')
    marker = addition.strip().splitlines()[0]
    assert marker not in existing, (rel,marker)
    with path.open('a',encoding='utf-8',newline='') as file:
        file.write(addition)
    print('APPENDED',rel)
