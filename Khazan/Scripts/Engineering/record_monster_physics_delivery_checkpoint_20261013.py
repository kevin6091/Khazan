"""Record delivered state while the final Main build/loader checks are pending."""
from pathlib import Path
import datetime,json
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Metadata/MonsterSecondaryPhysics_20261013'
assert json.loads((OUT/'DeliveryManifest.json').read_text(encoding='utf-8'))['complete']
marker='<!-- MonsterSecondaryPhysics_20261013_delivered_pending_main -->'
section='''

## 2026-10-13 — Main 선택 전달 완료 / 최종 Main 검증 대기

97 package(PA35/SK35/post-process20/Elite CopyPose1/기존 BP6) + 기존 KZMonster.cpp의 파츠 초기화 block1 + DEV 검증1의99행을 SHA/CAS로 Main에 전달했다. 새 runtime class/component/manager/tag0, private DLL/Build.cs/Config/author source 전달0이다. 최신 Source126 intake와 보호된 Player/Config/기타 Source를 보존했다. MainBuild01을 별도로 실행 중이며 완료 기록은 아직 아니다.

PrivateFinalQA02 fresh saved/RHI의 실제6 family 모두 finite/실제 simulation·반응·접촉/45도 envelope 통과, PlayerAttackCollision 회귀 Success다. 실제 peak: 검병29.073/방패29.836/중검 upper30.802 head25.621/할버드32.513/Apes39.391/Yetuga37.864도. PrivateFinalQA01의 Yetuga cloth49.669도 실패를 보존하고 cloth 관성만 보완했다. 최종317 simulated 설정이며 Yetuga37 single-bone fur +4 cloth는 모두 활성 상태다. 현재 정상 actor 전체 world ragdoll은 off다.

일반19 post-process는 ComponentSpace, Yetuga1은 WorldSpace다. Yetuga의 짧은 털은 source player spring784/damping56/8·8·3도/몸 damping0.1·1.5를 유지하되 hard angular limit·exact solver·실제 dominant skin tip 반경0.5cm 접촉을 적용했다. 원래 고정점에서 겹치는 몸 proxy pair는 분리했고 나머지 몸 접촉은 유지한다. 피부 support uniform-box와 pivot parallel-axis를 합산한 virtual inertia + 어시스턴트 TEMP 배율2를 사용한다. 큰 cloth4에도 기존 관성 TEMP2를 적용했다. 이는 사용자 지정/원작 직접 수치가 아니며 PA의 InertiaTensorScale에 저장된 기술적 안정화다. 원작 metadata50 anatomy capsule만 직접 출처이며 feel은 기존 Player TEMP 재사용이다.

실패한 broad nonlinear/alpha1/soft limit/geometry 후보와 compile/link 도구 오류는 모두 report에 보존했다. FurActual02 실제 body inertia·velocity·PA hard flags를 관측했다. ParticleConstraints count0은 immediate mode에서 등록하지 않는 engine 경로의 값이므로 관절 미생성 증거로 해석하지 않는다. 제약 존재/정확 engine 내부 cause·원작 전체 physics parity와 모든 skin triangle 관통0은 단정하지 않는다.

재개: MainBuild01 Exit/UBT Result 확인 → owned process 목록 확인 → main_commandlet MainSaved01(verify_monster_physics_main_saved_20261013.py, 저장0) → main_rhi MainFinalQA01에서 MonsterSecondaryPhysics.PIE/PlayerAttackCollision.PIE 실제2검사(별도 owned process) → 99SHA/actual module/보호 파일 확인 → 완료 MD/ResumeState 기록. PreparedVerification.json은 실제 PrivateFinalQA02의3검사/6 PNG/원본 Source/99SHA 검증으로 true다. full Author/과거 PA/FPS/root/VFX 재추출·재임포트·private DLL 전달은 반복하지 않는다.

'''+marker+'\n'
for rel in ('Docs/Engineering/MONSTER_SECONDARY_PHYSICS_20261013.md','Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md'):
    p=ROOT/rel
    if marker not in p.read_text(encoding='utf-8-sig'):
        with p.open('a',encoding='utf-8') as f:f.write(section)
(OUT/'ResumeState.json').write_text(json.dumps(dict(status='main_delivered_validation_pending',main_applied=True,
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),owned_build='MainBuild01',
    next='Confirm MainBuild01, run Main saved loader and fresh Main RHI physics/gameplay checks, finalize evidence/documents'),indent=2),encoding='utf-8')
print('DELIVERY CHECKPOINT APPENDED')
