from pathlib import Path
root = Path(r'C:/Users/user/Desktop/GitProject/Khazan/Khazan')
entries = {
 'Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md': '''

## 2026-10-08 — ARCH-84 피격·SystemGuard·브루탈 접근 계약 (구현 중)

사용자의 직접 구현 요청이다. 기존 Combo 충돌→공통 피해 GE→확정된 결과의 표현 순서를 유지한다. 공격 window의 반응 종류(None/Short/Knockback/Launch)는 공격자 데이터가 지정하고 CharacterDefinition의 종류별 몽타주 pool에서 방향 변형을 랜덤 선택한다. 입사 방향으로 일반 피격 모션을 선택하지 않는다. 공유 ASC 이벤트와 단일 UKZHitReactionAbility만 추가하며 새 combat manager/component/FSM은 만들지 않는다. HP0/몬스터 Stamina0/Dead/Exhausted와 기존 paired Brutal 반응은 일반 피격보다 우선한다. Ability가 취소/완료/실패의 몽타주·제약·공중 movement mode를 정리한다.

SwordShield는 원본 Battle LockOnMove의 SystemGuard180과 attack DamageType notify 구간을 구분한다. 기존 노드에 방어 시간 구간을 추가하며 현재 몽타주 시간으로 소비한다. Passive shield block에는 Active Guard FrontAngle60/GuardStaminaConsumeRate1.8을 임의 혼용하지 않는다. 180을 full cone으로 해석하는 것은 native 소비자 미확인 프로젝트 adapter다. 방패 반응 Hit→End의 재차 피격도 방어하도록 기존 피격 Ability가 자기 shield 실행 여부를 제공한다. 실제 방어는 HP 피해를 막고 공격 window의 사용자 조정 StaminaDamage를 소모하며 소진이면 기존 Exhaustion이 우선한다.

이미 있는 UKZBrutalAttackAbility/UKZExhaustionAbility와 전후 paired montage를 재사용한다. 즉시 TeleportPhysics 정렬을 원본 Grapple Start MoveTo의 .03356 trigger/.433283초 CubicInOut을 참고한 swept 접근으로 바꾼다. 최종 spacing은 기존 live capsule 정책이며 원본350을 최종 간격으로 단정하지 않는다. .01 mesh scale은 actor 정렬에 재적용하지 않는다. 기존 사용자 BrutalHPDamage50 및 lethal Hit2 이후 양쪽 반응 완료를 보존한다. 원본 조사/분류는 Art 별도 문서, 런타임 검증/임시값은 Engineering에 기록한다. 아직 Main 전달/빌드/PIE 완료가 아니다.
''',
 'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md': '''

## 2026-10-08 — CombatReaction 진행·재개

Router→Architecture/Migration/현재 Source와 저장된 metadata를 읽었다. Main을 건드리지 않고 기존 Khazan_MonsterWork_20261006에 최신 Source/Config와 표적 Content를 guarded stage했다. Metadata/CombatReaction_20261008/StageBaseline.json(709행,49복사)이 현재 Main CAS 기준이다. Work 기존 파일은 WorkBefore에 보존했다. 최신 ARCH-83 VFX 및6 Definition의 BrutalHPDamage50을 보존한다. 사용자 editor를 제어하지 않는다.

현재 Work에 CharacterDefinition 반응 pool/종류 enum, native event6개, Combo window 반응 종류·노드 SystemGuardWindows만 추가했다. 단일 HitReactionAbility를 병행 구현 중이고 Art 분류221enemy/24player 및 Shield/Brutal 원본 보고서를 표적 조사했다. 아직 현재 task build/author/PIE/Main 전달을 실행하지 않았다. 재개: 같은 Work 새 native HitAbility→Combo 양방향 피격/Shield→기존Brutal swept 접근→별도 소유 editor에서 InGame player reaction·montage/Definition 데이터 작성→native/저장 재로드 검사→임시editor helper 제외 stock build→StageBaseline/CAS 선택 Main 전달→새 독립 Main검사→완료 기록. 과거 stamina/VFX DLL과 proof를 이번 검사로 재사용하지 않는다.
'''
}
for rel, value in entries.items():
 p = root / rel
 with p.open('a', encoding='utf-8', newline='') as f: f.write(value)
print('Appended ARCH-84/continuity')
