from pathlib import Path
root=Path(__file__).resolve().parents[2]
text='''

## 2026-10-08 — In-place 피격의 실제 이동 경로 추가

별도 Work commandlet에서 Player Air F/B의 true skeleton root C_P_Kazan/index0/track0과 child Root 모두 이동0을 확인했다. 순서/누락/다른 Root의 이동 전사 문제가 아니다. Swordsman Up의 Bip001 이동은 포즈이며 world root로 임의 전사하지 않는다. 근거는 Metadata/CombatReaction_20261008/PlayerSourceRootReadback.json 및 InPlaceReactionRootAudit.json이다. `unreal-root-motion-repair`는 읽기 진단에만 적용했고 root/골격을 재구성하지 않았다.

이런 클립은 플레이 중 실제 날림을 별도로 구동해야 한다. 새 물리 component/helper 대신 HitReaction 실행에 엔진 UAbilityTask_ApplyRootMotionJumpForce의 RootMotionSource를 소유한다. Short/방패/미지원 Giant Short fallback은 이 이동을 만들지 않는다. 지원하는 Knockback은 수평, Launch는 수평+수직 곡선이다. duration은 실제 몽타주의 반응→Land/Getup 시각에서 가져오고 새 gameplay timer 수치를 만들지 않는다. CMC는 anim root motion을 RootMotionSource보다 먼저 적용하므로 자기 force 중에는 AnimInstance IgnoreRootMotion을 소유하고 완료/취소에 이전 mode를 복구한다. 원본 클립 옵션/track/rate는 보존하고 InGame 복제의 root 옵션만 실제 기존 template 정책으로 켠다.

CharacterDefinition HitReactions의 KnockbackDistance250cm, LaunchDistance120cm, LaunchHeight150cm는 어시스턴트가 선택한 임시 튜닝값이다. 원작 absolute 거리/높이로 확인한 수치가 아니다. 캐릭터 종마다 조절할 수 있고 실제 capsule 이동·벽 sweep·착지/기상 완료·과도한 이동 여부로 검증한다. 숫자를 여러 함수에 흩어 넣지 않는다. 일반 Monster Attack Window HP10/Stamina5도 원작 절대 피해량 환산이 미확인인 임시 설정으로 기존 window 데이터에 모아 조절한다. Player 기존 피해값은 임의 변경하지 않으며 승인된 접촉의 애니메이션 반응은 피해0에서도 가능하다. 원작 raw knockback curve/힘·거리 필드와 프로젝트3종 분류는 구분한다. 아직 이 force의 build/PIE 완료가 아니다.
'''
for rel in ['Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md','Docs/Engineering/COMBAT_REACTION_RUNTIME_20261008.md']:
 with (root/rel).open('a',encoding='utf8') as f:f.write(text)
print('Appended motion evidence/temporary tuning')
