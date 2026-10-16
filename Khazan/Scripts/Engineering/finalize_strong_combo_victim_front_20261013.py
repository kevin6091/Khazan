"""Bind successful Main evidence to the current source and five saved packages."""
from pathlib import Path
from datetime import datetime
import json, hashlib, difflib

root = Path(__file__).resolve().parents[2]
out = root/'Metadata/StrongComboVictimFront_20261013'
read = lambda p: json.loads((out/p).read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
build = read('Build02/Exit.json')
assert build['exit'] == 0 and build['input_unchanged']
current = {str(p.relative_to(root)): sha(p) for p in (root/'Source').rglob('*') if p.is_file()}
assert current == read('Build02/Launch.json')['source_sha256']
checks = []
for name in ['ActualStrong02', 'CollisionRegression02']:
    driver, result, launch = read(name+'/Driver.json'), read(name+'/Exit.json'), read(name+'/Launch.json')
    assert driver['status'] == 'passed' and result['exit'] == 0 and result['input_unchanged']
    assert driver['module_sha256'] == build['module_sha256'] == result['module_sha256']
    assert launch['source_sha256'] == current
    checks.append({'name': name, 'test': driver['test'], 'completion': driver['completion'],
                   'actual_loaded_module': driver['actual_loaded_module']})
runtime = read('ActualStrong02/StrongVictimRuntime.json')
assert runtime['passed'] and len(runtime['actual_strong_cases']) == 12
assert all(r['accepted_hits'] == 2 for r in runtime['actual_strong_cases'])
assert read('Saved01/Verification.json')['passed']
source_files = ['Source/Khazan/Data/KZCharacterDefinitionData.h', 'Source/Khazan/Character/KZCharacter.cpp',
                'Source/Khazan/Ability/KZHitReactionAbility.cpp', 'Source/Khazan/Tests/KZKnockbackPIETest.cpp']
patch = ''
for relative in source_files:
    before = out/'Before'/relative if '/Tests/' not in relative else out/'Before/KZKnockbackPIETest.cpp'
    patch += ''.join(difflib.unified_diff(before.read_text(encoding='utf-8').splitlines(True),
        (root/relative).read_text(encoding='utf-8').splitlines(True), fromfile='before/'+relative, tofile=relative))
(out/'Changes.patch').write_text(patch, encoding='utf-8')
assets = [r['file'] for r in read('Baseline.json') if r['file'].startswith('Content/')]
stamp = datetime.now().astimezone().isoformat()
report = {'schema': 'Khazan.StrongCombo.VictimFront.v1', 'date': stamp, 'status': 'MainAppliedAndVerified',
          'runtime_source_files': source_files[:3], 'dev_file': source_files[3],
          'new_runtime_files': 0, 'new_gameplay_tuning': 0,
          'source_sha256': current, 'asset_sha256': {p: sha(root/p) for p in assets},
          'module': build['module'], 'module_sha256': build['module_sha256'],
          'saved_verification': 'Saved01/Verification.json', 'tests': checks,
          'actual_cases': 12, 'approved_hits': 24,
          'policy': 'StrongAttack01-03: configured humanoids use fixed existing front victim montage; unconfigured bodies retain Knockback; other windows unchanged.',
          'earlier_failed_checks': ['Probe01: composite_sections unavailable in Python, saves0.',
              'ActualStrong01: incorrect DEV None-group count and active-montage assertion during normal blend-out; runtime unchanged for02.',
              'CollisionRegression01: incorrect automation name matched no tests; identity-verified owned process stopped, rerun02 uses exact registered name.'],
          'limitations': ['Owned RHI uses enlarged query capsules/high floor as QA fixtures; no original-game pixel/pose parity claim.'],
          'remaining': []}
assert not (out/'FinalVerification.json').exists()
(out/'FinalVerification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
body = f'''\n\n## {stamp} — ARCH-97 StrongCombo 인간형 VictimFront Main 완료

사용자 요청을 Main에 적용했다. StrongAttack01–03 각2개, 총6개 AttackWindow만 VictimFront로 변경하고 인간형4종(Swordsman/SwordShield/HeavySwordsman/HalberdElite)의 HitReactions.VictimFront에 기존 AM_BrutalVictimFront를 연결했다. 정면 피해자 모션 Damage1→Damage2를 기존 일반 HitReaction Ability/Task로 고정 재생하며 짝 브루탈을 시작하지 않는다. 해당 자기 montage instance의 paired root travel만 억제하고 Knockback/Launch RMS를 만들지 않는다. 설정 없는 Apes/Yetuga는 이전 Knockback pool을 유지한다. 사망·소진·guard 및 피해 승인/dedup/HP·ST/기존 효과는 기존 계약을 따른다.

runtime3파일/기존 DEV1/저장5package 수정이며 새 runtime file/class/태그/manager 및 새 gameplay 수치0이다. enum을 끝에 추가하여 None/Short/Knockback/Launch의 기존 ordinal을 보존했다. Character의 Short event.OptionalObject가 명시한 montage를 Ability가 선택하며, 정상·재피격·취소의 기존 제약/tag/montage cleanup을 재사용했다. 다른 Player window/몬스터 공격·브루탈/Definition의 원래 모든 피격·이동·AI·grant·소진 설정은 fresh Saved01 readback으로 보존 확인했다. 정면 클립에 execution material notify0도 확인해 추가 사망/재질 adapter를 만들지 않았다.

Build02 exit0/input동일, actual RHI ActualStrong02의4종×3타=12case/24승인 적중·어느 target facing에서도 고정 pose·자기 root-disable·RMS 없음·자연 완료/재피격/취소·다른 Short/Knockback pool·거대형 fallback과 기존 PlayerAttackCollision16 회귀가 성공했다. 실제 loaded module SHA는 `{build['module_sha256']}`이며 전체 Source/선택5asset·저장/실행 evidence는 Metadata/StrongComboVictimFront_20261013/FinalVerification.json과 Changes.patch다. Actor 크기/높은 평면은 격리 QA fixture이며 원작 pixel/전체 pose 일치 검증으로 표현하지 않는다.

필수 잔여0이다. Probe01의 Python 미노출 property/ActualStrong01의 DEV None-group·blend-out 기대값 실패는 역사로 보존하고02의 성공으로 대체한다. CollisionRegression01은 등록명을 잘못 입력해 matched test0이며 Launch PID/CommandLine을 확인한 task-owned process만 종료했다. 정확한 등록명으로 실행한02의 성공을 근거로 한다. 제품 runtime은 첫 실제 검사 이후 추가 변경0이며 Build02는 DEV 보완이다. 기존 editor process0에서 시작했고 외부/사용자 editor 제어0이다. 이후 조정은 최신 Main Definition의 VictimFront와 Player StrongCombo의6window만 표적 확인한다. 완료한 author/과거 VFX·Root·retime/private DLL 전달을 재실행하지 않는다.
'''
for document in ['Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md',
                 'Docs/Engineering/COMBAT_REACTION_RUNTIME_20261008.md',
                 'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md']:
    with (root/document).open('a', encoding='utf-8') as f:
        f.write(body)
brief = f'''\n\n## {stamp} — ARCH-97 StrongCombo 정면 반응 Main 검증 완료

StrongCombo 1·2·3타의6window를 인간형4종의 기존 정면 피해자 모션으로 고정했다. 기존 확정 피해/event/HitReaction Ability·Task와 cleanup을 재사용하며 새 runtime class/tag/manager·gameplay 수치0이다. 거대형/다른 공격 반응은 보존했다. Main runtime3/기존 DEV1/asset5, build·fresh saved·actual12case/24hit 및 기존 collision16 회귀 성공. 현행 사용법은 COMBAT_REACTION_RUNTIME_20261008.md 마지막 ARCH-97, exact SHA/실행 evidence는 Metadata/StrongComboVictimFront_20261013/FinalVerification.json이다. 필수 잔여0이며 과거 author/retime/delivery를 재실행하지 않는다.
'''
for document in ['Docs/Engineering/ENGINEERING_PROJECT_STATE.md', 'Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md']:
    assert (root/document).is_file()
    with (root/document).open('a', encoding='utf-8') as f:
        f.write(brief)
print('STRONG_VICTIM_FINALIZED: Main, 12 actual cases, collision regression')
