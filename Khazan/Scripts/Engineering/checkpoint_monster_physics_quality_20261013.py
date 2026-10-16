"""Append the actual isolated quality checkpoint, preserving earlier failure history."""
from pathlib import Path
import datetime,json
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'Metadata/MonsterSecondaryPhysics_20261013'
marker='<!-- MonsterSecondaryPhysics_20261013_quality09 -->'
section='''

## 2026-10-13 — 저장 후보의 품질 조정 / 메인 전달 전

현재 PA35 / SK35 / post-process20 / Elite CopyPose1 / 기존 gameplay BP6의97 package는 격리 작업본에만 있다. 초기378개에서 giant의 미분류 facial/muscle controls61개를 animation-driven으로 되돌려 explicit cloth/hair317개다. Main 게임 Source/asset 반영0이다. 기존 skeletal vertex/skeleton/animation/texture/material 재임포트0이다.

enemy reference root35개 모두1을 확인하여 player wrapper100용 world-space 설정 대신 ComponentSpace를 사용했다. thin capsule 관성은 실제 dominant skin support의 uniform box 관성으로 보완하고 player mass-per-length·반경·spring/damping/각도·24/4/4·1/60 solver 값을 유지했다. hair angular projection은 현재 player Torso의0.8을 사용한 기술적 어댑터다. 중검병 분리 head/upper는 내부 anatomy 중복 접촉을 제거하고 full parent17 anatomy를 AddClothCollisionSource로 받는다.

PhysicsPIE04~08에서 검병/방패병/중검병/할버드/Apes5 family는 finite/실제 simulation·반응·body contact 및 기존 cloth45도 QA를 통과한다. PhysicsPIE08 peak는32.426/29.823/중검 upper30.800 head25.621/할버드30.265/Apes39.931도다. Yetuga178.218도는 실패이며 Main 전달 근거로 사용하지 않는다. ProjectionBound01/02와 nonlinear 전체 Stability trial은 품질 실패 기록으로 보존한다. alpha1은 철회하고 current player Hair profile + Torso alpha0.8로 복원했다. Yetuga의 single-bone tuft는 머리→attachment 거리를 hair 길이로 쓰지 않도록 FurSupport01에서 실제 skin AABB 길이를 사용한다(예 Hair14:88.627→52.621cm, mass0.177253→0.105242kg). Yetuga만 nonlinear angular solver 적용 FurSolver01 후 fresh PhysicsPIE09를 검증 중이다. 변경은 원작 직접 수치라고 표현하지 않는다.

NoContactControl01~03은 source/body contact 분리 진단용이며 비활성 접촉 설정을 package에 저장하지 않았다. Source36/variant 및 original shape17/17/16 capsule 근거는 기존 report를 재사용한다. debugger session/agent breakpoint 정리 및 user exceptions 보존 완료다. PrivateBuild13은 foreign UBT writer 공유 실패로 unique -Log로 해결했고 foreign build mutex는 기다렸다. PrivateBuild18의 native Saved 검사 TSubclassOf 타입 오류는 도구 오류이며 PrivateBuild19/20 성공으로 보완했다. 최신 Main Source126개를 다시 intake했고 변경은 기존 modular BeginPlay block 하나다. 별도 editor만 사용한다.

정확한 재개: PhysicsPIE09 Driver/Runtime 실제 결과 확인 → 실패면 Yetuga worst bone·stage·rendered_joint_peak와 Saved 검사에서 실제 scale/inertia/contact geometry를 표적 검토(다른5 family 보존) → flag 없는 saved + 실제6종 PIE/RHI 및 PlayerAttackCollision 회귀 → current Main/source/assets SHA/CAS 검증 → 선택97 package/runtime1/DEV1 전달·Main build/새 loader/PIE 확인 → 완료 기록. full Author/구 metadata export/Player 전체 author/FPS/root/VFX author 재실행 금지. PreparedVerification은 실제 품질 통과 후에만 true로 만든다.

'''+marker+'\n'
for rel in ('Docs/Engineering/MONSTER_SECONDARY_PHYSICS_20261013.md','Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md'):
    p=ROOT/rel
    if marker not in p.read_text(encoding='utf-8-sig'):
        with p.open('a',encoding='utf-8') as f:f.write(section)
(OUT/'ResumeState.json').write_text(json.dumps(dict(status='isolated_yetuga_quality09',main_applied=False,
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),owned_run='PhysicsPIE09',
    remaining=['Yetuga bounded motion','saved/RHI/current gameplay regression','CAS selective Main delivery','Main build and fresh verification'],
    next='Read PhysicsPIE09 Driver/Runtime; preserve other five families and prior failures'),indent=2),encoding='utf-8')
print('QUALITY09 CHECKPOINT APPENDED')
