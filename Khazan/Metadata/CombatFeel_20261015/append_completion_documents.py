"""Append domain completion notes; preserve all prior and concurrent records."""
from pathlib import Path
import json

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
report = json.loads((BASE / "FinalVerification.json").read_text(encoding="utf-8"))
assert report["status"] == "complete_main_verified" and not report["remaining"]
module = Path(report["builds"]["current_module"]).name
digest = report["builds"]["current_module_sha256"]
receipt = "`Metadata/CombatFeel_20261015/FinalVerification.json`"
notes = {
"Docs/Engineering/PARRY_IMPLEMENTATION_20261012.md": """
## 2026-10-15 — 현재 패링 VFX 교체와 선형 카메라 힘 적용 완료

사용자 직접 수정 요청으로 이전 ParryImpactEffect/halo, 바닥용 plunge Niagara 연결, ParryScreenDistortion 후처리 volume 생성 경로를 제거했다. 기존 Guard 승인/성공 좌우 모션/스태미너 비용/공격자 알림은 유지한다. `ParryBillboardDistortion`은 `/Game/VFX/03_SlashHit/KZ_Parring_Distort`로 저장했다. XY는 두 actor 중점, Z는 실제 `Bip001-Spine2` 흉부 높이의 평균이며 카메라를 향하게 한다. camera pull 상수와 바닥 normal parameter는 사용하지 않는다. Guard montage의 남은 particle/Niagara Notify 연결은 0이다.

기존 CombatEffect SpawnComponent를 재사용하는 editor Instanced `ParryBrutalEffects`에 현재 BrutalFront의 접촉 효과 `PP_AtkEx_Grapple_01`, `PP_Dmg_Blood_Trail_Sub`, `PP_AtkEx_Grapple_02` 3개를 복사해 승인된 패링에 함께 재생한다. source_notify/source_package/source_field, parameter/scale/원본 duration은 Author02에 기록했다. 원본 duration은 WindowEndTime−WindowStartTime 계산이며 방출 정지 뒤 기존 alpha/lifetime drain을 보존한다. 요청 Niagara native scale1, 방출 종료 .5s/최대 수명2.5s는 TEMP 유한 수명 정책으로 조절 가능하다. 실제 Guard BP와 두 giant BP 총3 package만 이 작업에서 저장했다. 범용 CombatEffect runtime/원래 Brutal particle asset은 교체하지 않았다.

모든 현행 camera shake producer(giant source notify 86창 및 Guard 성공)는 기존 KZCombatCameraModifier의 선형 방향 힘/복원으로 소비한다. 최소 상승 .08s/복원 .16s/최대 반복4Hz는 사용자가 자연스러운 선정값을 허용한 TEMP이다. 원본 amplitude/FOV/scale/거리 attenuation/window는 유지하며, 반복 pulse는 반대 방향으로 되풀이한다. 취소/Notify End/mesh 소멸에서는 마지막 실제 화면 기여(거리 배율 포함)를 저장해 그 위치에서 선형으로 복원한다. 독립 이벤트의 중첩과 유한 cleanup을 유지하며 gameplay RNG를 소비하지 않는다.

FinalRHI01은 실제 D3D12 패링17/17 Success와 위치/모션/tail3장, 정상 가드/취소/자원/소진 회귀를 포함한다. Physics03의 LinearCamera4 및 GiantCamera4는 Success(같은 suite의 당시 AI 실패와 구분). 신규 AI만 후속 수정됐으며 각 실제 로드 DLL hash는 최종 receipt의 runs에 별도로 기록했다. 최신 원작 shader pixel 일치/Shipping 성능을 검증한 것으로 표현하지 않는다. 정본: RECEIPT. Art 외관은 PLAYER_PARRY_SOURCE_20261012.md의 같은 날짜 최신 절.
""",
"Docs/Engineering/APES_YETUGA_FALL_IMPLEMENTATION_20261011.md": """
## 2026-10-15 — 거리 복귀·Armageddon·장거리 잡기·groggy/콤보 연결 Main 완료

멀어져 Idle에 남는 두 실행 원인을 기존 소유자 안에서 수정했다. disabled ChargeTackle SourceGate의 true와 inverted false가 모두 false였던 것을 `bInvert` 반환으로 보완해 source false continuation으로 진행한다. 원작 StateTree와 disabled skill 정책은 유지한다. 또한 baked navmesh 밖에서 accepted abstract path가 Moving만 표시하고 Pawn 입력은 0인 Yetuga 실행을 PursuitProbe03에서 확인했다(Walking/속도470cm/s/MaxAcceleration1800cm/s², IgnoreMoveInput=false, active montage/root 없음). AIController의 task-owned `DirectMoveGoal`을 기존 Locomotion intent→Pawn AddMovementInput→CMC로 소비한다. 유효 nav 투영 성공 시 원래 MoveTo로 복귀하며 권한 상실/task Exit/Unpossess는 기존 StopRequestedMove가 목표/입력을 함께 정리한다. 새로운 gameplay state나 manager는 없다.

Yetuga AISettings의 `RangedPatternSkill=Armageddon`, range800–5000cm, chance.3, cooldown20s를 저장했다. range 입력은 원작 BT058 거리 분기800 및 BT export37 Armageddon maxDistance5000을 활용한다. 원본 상위 HP raw<=65/MinStamina raw>=20/EndCooltime240은 BEHAVIOR_ANALYSIS 및 AuditBefore02에 기록되어 있다. 사용자 요청대로 설정된 원거리 선택에서 HP ceiling만 해제하고 source stamina/angle/장애물/Ability/기존 cooldown owner를 유지한다. **30%/20s는 원작 직접값이 아닌 TEMP 정책**이다. 같은 selection frame의 true/false gate가 하나의 RNG 결과를 공유하며 task Enter에서 다시 뽑지 않는다. Apes에는 존재하지 않는 Armageddon을 추가하지 않았다.

capture-bearing node의 정방향 trace-target 이동만 선택 target의 현재 거리−원본 TargetOffset까지 TargetMax 상한을 확장한다. 원본 이동 시간/curve/미스/회복/다른 공격 이동은 유지하며 임의 고정 장거리 literal을 넣지 않았다. 실제 2000cm 고정 표적에서 Apes Level_DashAtk_New_Step8 1846.74cm, Yetuga RushGrab_Step5 1815.15cm 이동 및 양쪽 held=1을 확인했다. 이동 중인 플레이어의 회피는 원래 공격의 행동이며 자동 포획 보장을 넣지 않았다.

약점 파괴와 groggy에 쓰는16 sequence의 before/after read-only root audit rows가 완전히 동일하다. PartGroggy_Start 두 clip은 enable_root_motion=true, true root `Root` index0 및 정상 track 순서다. 추출523.544cm에 대해 실제 약점 파괴 캡슐 이동 Apes526.802cm/Yetuga526.790cm을 확인했다. Rider에서는 실제 Apes PartGroggy의 MontagesOnly/DisableRootMotionCount0/mesh scale1/root translation scale1/Walking을 확인했다. 올바른 원본 track을 재베이크하거나 과대 배율로 바꾸지 않았다.

두 몬스터의 기존 AM_Exhaustion은 Start→Loop 및 Loop→Loop를 각 runtime montage instance에 연결하고 기존 timer/Brutal/End cleanup을 유지한다. Physics03에서 Start/Loop를 연속 관측(Apes277/Yetuga437 samples), End 후 State.Exhausted 해제를 통과했다. 콤보 Commit/Open section jump에는 기존 ABP Slot inertializer를 사용해 `MinimumTransitionBlendSeconds=.12s` TEMP floor를 적용한다. source0/짧은.1s 전이는 보완하고 더 긴 원본 blend와 clip/Notify 시간은 보존한다.

Build11 standard/Build12 suffix 성공. PursuitFinal 및 최신 표준 Main FinalMain01은 실제 source StateTree의 4500cm 추적/다음 공격, full-HP Armageddon entry, 두 capture 및 BeastDodge.SourceAudit, GiantFall13 회귀 전부 Success, 저장0이다. 원거리 30%는 저장 policy이며 QA에서는 0/1 경계로 선택 경로를 확인한 것이지 통계 실측30%가 아니다. 최신 실행 모듈/모든 원시 실패 기록/수치 출처/현재 SHA는 RECEIPT. 사망 연결은 COMBAT_PRESENTATION_FOLLOWUP_20261011.md의 최신 절.
""",
"Docs/Engineering/COMBAT_PRESENTATION_FOLLOWUP_20261011.md": """
## 2026-10-15 — 6종 치명 브루탈 피해자→사망 관성 연결 완료

기존 paired victim/Hit2 피해/terminal hold/죽음 owner를 유지하고 `AKZMonster::FinishDeathPresentation`에서 원본 death BlendIn과 `FKZMonsterStaminaSettings::DeathTransitionBlendSeconds` 중 큰 시간으로 montage inertialization을 요청한다. 새 .24s 최소값은 원작 직접값이 아닌 TEMP이며 기존 Definition 설정에서 조정한다. 더 긴 원본 blend는 보존한다. 포즈를 즉시 바꾸거나 짝 반응 중간에 사망 몽타주를 실행하지 않는다.

FinalRHI01 실제 Main D3D12에서 Swordsman/SwordShield/HeavySwordsman/HalberdElite/ApesStoneHandElite/Yetuga 6종×정면/후면12 lethal pair가 모두 Success다. 실제 death montage, 완료 terminal pose, capsule/root scale 복원, spacing을 확인하고 pair→death 첫.4s를.08s 간격5장씩 기록했다. transition frame/bone velocity는 진단 자료이며 임의 threshold로 원작 일치를 주장하지 않는다. 최종 근거와 각 run의 실제 DLL hash는 RECEIPT. 기존 dissolve/ash/일반 사망/비치명 groggy 회복과 관련 없는 Source를 일괄 교체하지 않았다.
""",
"Docs/Art/PLAYER_PARRY_SOURCE_20261012.md": """
## 2026-10-15 — 사용자 지정 KZ_Parring_Distort 및 Brutal 접촉 burst Main 완료

최신 사용자 지정 효과는 `/Game/VFX/03_SlashHit/KZ_Parring_Distort`다. 원본 camera-facing Niagara renderer/material을 유지하고 두 캐릭터 사이 흉부 높이에 배치했다. 이전 JustGuard halo/바닥 전용 Niagara/화면 PP 재생 연결은 현재 Guard에서 제거했다. 해당 원본 에셋 자체를 삭제하거나 공유 shader를 이 작업에서 바꾸지 않았다. native scale1은 요청 에셋 원래 크기를 사용한 것이며 방출 종료.5s/최대 수명2.5s는 TEMP 표시 수명이다. runtime source/cleanup은 Engineering PARRY_IMPLEMENTATION 최신 절을 따른다.

현재 BrutalFront의 `PP_AtkEx_Grapple_01`, `PP_Dmg_Blood_Trail_Sub`, `PP_AtkEx_Grapple_02` 접촉 burst 3개를 parameter/scale/원본 window와 함께 재사용한다. source package/field는 Author02/Author.json과 AuditFinal/Audit.json에 있다. 첫 Author01 full9 연결의 손/무기 잔상 레이어에서는 회색 큰 면이 나타나 layer isolation으로 확인했고, 실제 접촉 burst만 남긴 Author02가 최종이다. 이 선택은 source 전체 Brutal 재현 완료를 뜻하지 않으며 실제 Brutal montage/공유 PS는 보존한다. 이전9개 임시 연결 기록은 보존하고 현재 저장 연결3개로 대체한다.

FinalRHI01의 01_ActualParryImpact/02_ActualParryMotion/03_ActualParryEffectTail에서 camera-facing 왜곡 및 같은 접촉 입자를 실제 플레이어 패링 성공 시 확인했다. full9 손 잔상의 회색 slab는 최종 재생에 없다. requested Niagara-only/mesh-only 진단은 원인 분리 자료이고 기능검증 통과로 집계하지 않는다. 실제 기능은 Main D3D12 Parry17 Success이며, 저장 Guard BP 현재 SHA가 Author02와 동일한 새 프로세스 readback을 통과했다. 원작 shader pixel identity를 새로 확보한 결과로 표현하지 않는다. 최종 근거: RECEIPT. 본 작업의 unique package 저장은 Guard+두 monster BP3개이며 새로운 Art particle/shader asset은 없다.
""",
"Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md": """
## 2026-10-15 — ARCH-99/85/92/94 CombatFeel 실행 계약 확정

앞선 같은 날짜 계획의 'chance는 실행 진입' 및 'abstract direct path 추격' 설명은 현재 구현으로 대체한다. Armageddon chance는 source true/inverted-false gate가 같은 selection frame에 공유하는 한 RNG 결과이고 task Enter 재평가는 없다. off-nav abstract path의 실제 입력0이 관측돼 선택된 기존 이동 task의 DirectMoveGoal을 AIController가 기존 intent→Pawn/CMC 입력으로 소비한다. 정상 nav 복귀/Exit/금지/Unpossess cleanup은 StopRequestedMove 한 경로로 정리한다. 목표는 navigation resource이며 ASC gameplay 상태의 사본이 아니다. 공격/피해/자원/죽음 수명과 worker 경계는 유지한다.

Runtime 신설0, 기존 camera/Guard/Pattern/Exhaustion/AI/Monster 소유자와 기존 data field만 보완했다. .12s combo floor는 source0뿐 아니라 더 짧은 source blend에도 적용하며 긴 blend는 보존한다. 실제 적용, 빌드, 각 DLL별 PIE/화면 검수 및 미확인 경계는 RECEIPT와 도메인 현행 문서에 기록했다. 앞선 실패나 계획 기록은 삭제하지 않는다.
""",
"Docs/Engineering/ENGINEERING_PROJECT_STATE.md": """
## 2026-10-15 — CombatFeel 메인 구현·검증 완료

패링 사용자 지정 Niagara/Brutal burst, 모든 현행 선형 camera force/return, Apes/Yetuga 원거리 추적과 장거리 capture, Yetuga 원거리 Armageddon TEMP policy, groggy runtime loop 및 giant 콤보/6종 lethal death inertia를 메인 기존 소유자에 적용했다. unique BP3개/새 runtime 파일·class0. PartGroggy root data는 정상이며16 clip audit 동일 및 실제 캡슐 이동 검증을 통과했다. Build11/12, 표준 메인 MODULE(SHA DIGEST)의 FinalMain01 3 suite Success; 이전 RHI Parry17/Brutal12와 camera/root/groggy suite는 각 module identity를 유지해 별도로 기록한다. 정본: RECEIPT 및 PARRY_IMPLEMENTATION/APES_YETUGA_FALL_IMPLEMENTATION/COMBAT_PRESENTATION_FOLLOWUP 같은 날짜 최신 절. 필수 잔여0.
""",
"Docs/Art/ART_PROJECT_STATE.md": """
## 2026-10-15 — CombatFeel 사용자 지정 패링 연결 완료

메인 Guard의 요청 KZ_Parring_Distort와 기존 Brutal 접촉 burst3개의 저장·fresh readback·실제 D3D12 패링17 검증을 완료했다. full9 임시 잔상 연결은 Author02 접촉3 연결로 대체했고 original Niagara/PS/material/Brutal montage 자체는 보존했다. 현재 외관과 TEMP 수명·shader 미확인 경계는 PLAYER_PARRY_SOURCE_20261012.md의 최신 절. 저장/검증 근거: RECEIPT. 관련 재author 대기나 미전달 에셋 없음.
""",
"Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md": """
## 2026-10-15 — CombatFeel 최종 완료 및 재개 기준

앞선 같은 날짜 진행 중 기록을 완료 상태로 대체한다. Build10 표준 DLL 잠금은 보존했고 타 세션을 종료하지 않았다. 잠금 해소 후 Build11 표준 및 Build12 suffix 성공, 후속 다른 빌드가 표준 manifest로 복귀한 뒤 FinalMain01에서 실제 MODULE SHA DIGEST로 GiantCombatFeel/BeastDodge.SourceAudit/GiantFall 모두 Success, 저장0을 다시 확인했다. PursuitFinal suffix 성공도 원시 기록 그대로 보존한다. 다른 run의 모듈을 현재 모듈 테스트로 재명명하지 않는다.

최종 상태 complete_main_verified/remaining=[]는 RECEIPT다. 패링/카메라/약점 root·groggy/콤보/치명 브루탈 전환, 두 giant 거리 복귀/잡기와 Yetuga source Armageddon 적용 완료다. 작업 소유 editor/commandlet은 정상 종료했고 breakpoint/debug session도 이전 root 진단 후 정리했다. 원작 shader pixel 일치와 moving-target capture 회피 등의 검증 범위는 최종 report limits이며 필수 미반영 작업이 아니다.

다음 관련 요청은 Router→Architecture v2/Migration→관련 현행 문서 최신 날짜 절→FinalVerification의 현재 Source/3 BP SHA 및 AuditFinal에서 시작한다. 완료 author 스크립트/전체 root 재임포트/이전 DLL 복원은 반복하지 않는다. 실제 추가 수정이 생기면 변경한 소유자와 해당 suite만 검증하며 타 세션 변경을 보존한다. write_final_verification.py는 완료된 receipts를 검사할 뿐 게임 파일을 수정하지 않는다.
""",
"Docs/Art/ART_WORK_CONTINUITY.md": """
## 2026-10-15 — CombatFeel 패링 Main 저장·화면 검수 완료

앞선 Author01 full9/FinalRHI 진행 중 기록은 최종 Author02 burst3 및 exact KZ_Parring_Distort 연결로 대체한다. fresh AuditFinal의 Guard CDO/원래 montage 잔여 effect0, 현재 package SHA=Author02, 실제 Parry17/3캡처를 완료했다. source root16 rows도 동일하며 올바른 animation을 재베이크하지 않았다. original/shared VFX asset과 unrelated 세션 변경은 보존한다. 최종 상태와 evidence는 RECEIPT, Art 외관 정본은 PLAYER_PARRY_SOURCE 최신 절이다. 필수 미전달/검증 대기 없음. 재개는 현재 저장 binding/receipt부터 시작하고 이미 완료된 full author/import를 재실행하지 않는다.
"""
}
for relative, text in notes.items():
    text = text.replace("RECEIPT", receipt).replace("MODULE", module).replace("DIGEST", digest)
    path = ROOT / relative
    marker = text.strip().splitlines()[0]
    if marker not in path.read_text(encoding="utf-8-sig"):
        with path.open("a", encoding="utf-8") as stream:
            stream.write("\n" + text + "\n")
print("Completion appended to", len(notes), "domain documents; prior records preserved")
