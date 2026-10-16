"""Append domain records only after PIE, delivery, build and Main reload pass."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import collections
import json
import re

ROOT = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT = ROOT / 'Metadata/EnemyAnimationOrganization_20261007'
ready = json.loads((OUT / 'MainReadyAudit.json').read_text(encoding='utf-8'))
delivery = json.loads((OUT / 'DeliveredManifest.json').read_text(encoding='utf-8'))
saved = json.loads((OUT / 'SavedAnimationAudit.json').read_text(encoding='utf-8'))
assert ready['success'] and ready['game_world'] is None and not ready['dirty_content'] and not ready['dirty_maps']
assert delivery['status'] == 'DeliveredHashVerified'
checks = {
    'SourceAudit_FinalSuccess.log': 'Khazan.Monster.SourceAnimationAudit',
    'AttackPatternsPIE_FinalSuccess.log': 'Khazan.Monster.AttackPatternsPIE',
    'CombatPolicyPIE_Success.log': 'Khazan.Monster.CombatPolicyPIE',
    'WaitingPIE_Success.log': 'Khazan.Monster.WaitingPIE',
    'HealPIE_Success.log': 'Khazan.Heal.PIE',
    'GuardPIE_Success.log': 'Khazan.Guard.PIE',
}
for name, test in checks.items():
    text = (OUT / name).read_text(encoding='utf-8', errors='replace')
    lines = [line for line in text.splitlines() if 'Test Completed.' in line and 'Path={' + test + '}' in line]
    assert lines and 'Result={Success}' in lines[-1], (name, lines[-1:] )
build_bytes = (OUT / 'ColdBuild_Main.log').read_bytes()
build_text = build_bytes.decode('utf-16' if build_bytes.startswith(b'\xff\xfe') else 'utf-8', errors='replace')
assert 'Result: Succeeded' in build_text
patterns = re.findall(r'Pattern completed BP_Monster_(\w+)_C_\d+ index=(\d+) sections=(\d+) rootTravelCm=([\d.]+) expectedRootTravel=(\d+)',
                      (OUT / 'AttackPatternsPIE_FinalSuccess.log').read_text(encoding='utf-8', errors='replace'))
counts = collections.Counter(p[0] for p in patterns)
assert counts == {'Swordsman': 5, 'SwordShield': 3, 'HeavySwordsman': 7, 'HalberdElite': 20}, counts
assert all(float(p[3]) > 1.0 for p in patterns if p[4] == '1')
assert len(saved['sequences']) == len(ready['sequences']) == 813
now = datetime.now(timezone(timedelta(hours=9))).strftime('%Y-%m-%d %H:%M KST')
title = '\n\n## ' + now + ' — Enemy 정리·공격·Root Motion Main 완료\n\n'
engineering = f'''ARCH-79 실제 완료다. 기존 StateTree/AISettings/CharacterDefinition grants/ComboAction/ComboDefinition/Montage를 재사용했다. runtime 새 파일·class·component·manager는0, 실제 gameplay Source는 KZMonster.h와 KZMonsterStateTreeNodes.cpp 두 파일이며 기존 development KZMonsterAIPIETest.cpp를 보완했다. Player/ASC/ComboAction 실행 코드를 재작성하지 않았다.

공격은13→35(Swordsman5, SwordShield3, Heavy7, Halberd20)이며 해당4종 Attack68클립을 모두 연결했다. finite 준비/loop/타격/회복은 같은 Action 안에서 필수 순서를 유지하고 실제 combo만 기존 held X/InputEnd로 잇는다. 신규 combo6개의 끝 경계 InputEnd 실패는 montage data에서 마지막 sample 이전으로 보완했다. 정확한 시간식과 원작 SB/file/field는 MONSTER_ATTACK_ROOT_MOTION_20261007.md 및 AttackExpansionPlan.json/AllSavedSkillAudit.json을 따른다. 원작 hit/guard 조건 producer나 피해/피격을 새로 구현한 것은 아니다.

현재 공격 선택에는 독립 RNG probability가 없고 거리/각도/cooldown gate를 쓴다. 기존 임시 interval2..4초를1.1로 나눠1.8181818..3.6363636초로, combo continuation .75→.85(+10percentage points)로 설정했다. 전체 공격 빈도의 정확한10%를 보장하는 통계 수치가 아니다. ChaseReactionSeconds .4초는 assistant 임시 tuning이며4BP AISettings에 저장했다. 선택 Standoff/Attack을 끝낸 뒤 Chase에 진입하고 기존 task TimeRemaining을 Enter에서 설정/Tick에서 감소시켜 nav 요청을 잠시 보류한다. 첫 Chase에도 적용한다. 타깃 유지/기존 cleanup을 보존한다.

stock SourceAnimationAudit813/18,958,755 raw transforms·곡선/선택 metadata 동일 Success; compressed root QA .01cm/normalized angular1e-4rad는 기술 허용 오차다. raw tolerance1e-6와 구분하며 실제 최대 압축 positional 차이.0060654cm였다. AttackPatternsPIE 최종35개/모든 section/actual root travel/HP 불변·취소 cleanup·네 종 실제 rechase Success. CombatPolicyPIE 네 종 선택 행동 완료/시야 밖 target 유지/.4초 nav hold/후속 물리 추격 Success, Waiting/Heal/Guard PIE Success. 최초 full Monster.PIE의32 방향보행/contact sample min11·median0cm/s는 통과했으며 montage notify만 보완한 뒤 중복 walk 검사는 반복하지 않았다. retreat fixture는 Root lunge로700cm를 따라잡는 문제와 nav 밖5000cm 배치 문제를 각각 보존하고, 최종8후보 projection+complete path 및 Chase 진입 이후 physical advance로 검사했다.

Main 선택 전달은 파일{len(delivery['files'])}개(기존69/신규경로912), 이름 변경 옛 파일{len(delivery['deleted'])}개를 정확한 path/hash guard 뒤 제거했다. backup Before와 실패 로그를 보존한다. 미관련 Source/Config{delivery['unrelated_source_config_verified']} 및 Archer{delivery['protected_archer']}개 hash를 보존했다. Main stock cold build Succeeded, fresh Main PID{ready['pid']} /DevMap/4BP·ABP UP_TO_DATE/813 options·35 grants·68 clips/저장값 재확인/PIE없음/dirty0이다. 자동 Main PIE는 실행하지 않았다. Main에 사용자 직접 Play용 DevMap이 열려 있다. 최종 manifest와 증거는 Metadata/EnemyAnimationOrganization_20261007/FinalVerification.json, DeliveredManifest.json, MainReadyAudit.json을 따른다.

Main 최초 read-only 검사에서 DevAI_ label 접두사에 Navigation volume까지 포함해 actor수5로 실패했다. 4 BP/ABP·813 options 검사는 이미 통과한 상태였고, exact4family actor label로 QA 식을 고친 뒤 같은 fresh editor에서 전체 read-only 검사를 다시 통과했다. 실패 JSON/MainReload log를 보존했고 이 과정에서 게임 코드·map·asset save/PIE는 수행하지 않았다. raw tolerance의 정확한 값은1e-6이며 이전 Art 본문의 최초 .001cm 언급은 엄격한 compressed probe와 혼동한 설명이다. 최종 compressed .01cm와 raw 검사를 구분한다.
'''
art = f'''실제 Main 반영 완료다. Archer 제외 HeinMach Humanoids4종 및 Yetuga/ApesStoneHandElite의 Art676, 기존 gameplay93을 purpose12폴더와 의미 이름으로 정리했다. 신규 gameplay44를 더해 현재813시퀀스, 기존 montage33과 신규22를 더해55montage다. Idle/Locomotion/Attack/Damage/Death/Guard/Alert/Equip/Interaction/Recovery/Prop/Pose이며 방향·단계·변형은 보존한다. A_EN_PLAY/중복 AC·CA·M·EN·Boss·캐릭터 접두사와 hash tail을 제거했다. 겹치는 direct source/Composite는 Original/Composite로 구분한다. CurrentAnimationLibrary.csv가 current→legacy→original source/frame/FPS/length/RateScale/root/options의 조회표다. 과거 export CSV는 historical 원본이며 수정하지 않았다.

813개 EnableRootMotion=true/ForceRootLock=true/AnimFirstFrame을 저장·fresh Main readback했다. 4NPC의 기존 RootMotionFromMontagesOnly로 공격/End 몽타주 root delta를 CMC가 소비한다. Nav 보행은 기존 CMC/velocity pose/Foot Placement를 유지하며 RootMotionFromEverything 보행 구현이라고 부르지 않는다. Yetuga/Apes는 library/options 정리이지 신규 AI 구현이 아니다. index0/first track audit769의 Root765/Weapon_R1/B_Rock3을 유지했다. raw pose19M/곡선·재생률 비교와 compressed extraction tolerance를 구분한다. source pose/root 트랙·Skeleton topology/scale/Player .01·재생속도/재임포트 수정은 없다.

Rename참조 갱신 후 옛802 packages는 fresh registry/commandlet 및 Main hash 확인으로 실제 제거됐다. source assets의 imported actor/catalogue 참조도 갱신했다. 실패 fixup와 QA 로그를 지우지 않았다. Archer{delivery['protected_archer']}개 hash는 전달 전후 동일하다. Main stock build·813 saved reload/dirty0를 완료했다. 자산별 분류·이름·원본 출처는 ENEMY_ANIMATION_ORGANIZATION_20261007.md 및 Metadata/EnemyAnimationOrganization_20261007/CurrentAnimationLibrary.csv를 따른다.
'''
continuity = f'''완료이며 pending helper/추가 에셋 전달이 없다. 최종 Main PID{ready['pid']}은 DevMap/PIE없음/dirty0/4BP·ABP UP_TO_DATE다. owned MonsterWork editor는 preview ScreenPercentage87/MotionBlur3와 원래 foreground throttle을 복구하고 정상 종료했다. 초기 실패 로그는 보존한다. 후속은 Router→Architecture ARCH-79 완료→Migration→MONSTER_ATTACK_ROOT_MOTION_20261007.md/Art ENEMY_ANIMATION_ORGANIZATION_20261007.md→CurrentAnimationLibrary.csv 및 실제 Source 순서다. rename/authoring/fixup/copy setup을 재실행하지 않는다. 직접 확인은 열린 Main DevMap에서 Play하고 감지→End→approach/좌우 대치→다양한 공격→거리 이탈 때 기존 행동 완료+.4초 후 재추격을 본다. 원작 AI 확률/모든 지형·연속 포즈/물리 pad/적 피격·네트워크는 미검증 후속이다.
'''
notes = {
    'Docs/Engineering/MONSTER_ATTACK_ROOT_MOTION_20261007.md': engineering + '\n' + continuity,
    'Docs/Engineering/ENGINEERING_PROJECT_STATE.md': engineering,
    'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md': engineering + '\n' + continuity,
    'Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md': 'ARCH-79 Main 완료.\n\n' + engineering,
    'Docs/Engineering/CHARACTER_TAG_ABILITY_MIGRATION.md': engineering,
    'Docs/Engineering/MONSTER_UNAWARE_LOCOMOTION_20261007.md': '아래 후속은 몬스터의 이전 RM=false/RefPose 계약과 imported animation 경로를 충돌 범위에서 대체한다.\n\n' + engineering,
    'Docs/Art/ENEMY_ANIMATION_ORGANIZATION_20261007.md': art,
    'Docs/Art/ART_PROJECT_STATE.md': art,
    'Docs/Art/ART_WORK_CONTINUITY.md': art + '\n' + continuity,
    'Docs/Art/ART_KNOWLEDGE_INDEX.md': 'Enemy 현행 animation 경로는 [ENEMY_ANIMATION_ORGANIZATION_20261007.md](ENEMY_ANIMATION_ORGANIZATION_20261007.md)와 CurrentAnimationLibrary.csv를 먼저 읽는다. 옛 Playback/AM/가져온 접두사 경로는 역사적 export이며 현재 이름으로 가정하지 않는다.\n\n' + art,
    'Docs/Animation/LOCOMOTION_CURRENT_IMPLEMENTATION.md': '몽타주 root 소비 후속: 모든 해당 Monster 시퀀스 RM=true/ForceRootLock=true/AnimFirstFrame으로 이전 Enemy RM=false/RefPose만 대체됐다. ABP MontagesOnly 유지, Nav CMC/방향 pose/Foot Placement/Player .01·기존 Linked Layer/Start 제외/Stop/Turn 정책은 유지했다. 공격·재추격 값과 실제 검증은 [Engineering 정본](../Engineering/MONSTER_ATTACK_ROOT_MOTION_20261007.md) 최신 Main 완료 절을 따른다. 새 montage55 참조로 이름을 갱신했고 raw/RateScale/FPS를 재작성하지 않았다.\n',
    '0_DOCUMENT_ROUTER.md': 'Art 애니메이션 정리 요청은 [Enemy Art 정본](Docs/Art/ENEMY_ANIMATION_ORGANIZATION_20261007.md)→CurrentAnimationLibrary.csv, 몬스터 동작은 Architecture ARCH-79 완료→Migration→[공격·Root Motion·재추격 정본](Docs/Engineering/MONSTER_ATTACK_ROOT_MOTION_20261007.md)을 읽는다. Archer 제외6종/813시퀀스·12분류/35공격은 Main 반영·stock build·PIE와 saved reload 완료다. Nav 보행은 CMC, 몽타주는 root 소비다. 기존 imported path/RootMotion=false 기록을 현재 정책으로 재사용하거나 author setup을 반복하지 않는다.\n',
}
for relative, note in notes.items():
    with (ROOT / relative).open('a', encoding='utf-8') as stream:
        stream.write(title + note)
report = dict(status='Complete', utc=datetime.now(timezone.utc).isoformat(), main_pid=ready['pid'],
              sequences=813, art_sequences=676, current_gameplay_sequences=137, montages=55,
              attack_patterns=dict(counts), attack_clips=68, root_motion_mode='RootMotionFromMontagesOnly',
              navigation='Existing CMC/velocity pose/Foot Placement', runtime_files_added=0,
              gameplay_source_files=2, development_test_files=1, delivered_files=len(delivery['files']),
              deleted_old_packages=len(delivery['deleted']), protected_archer=delivery['protected_archer'],
              checks=checks, documentation=list(notes), original_aidata_confirmed=False,
              new_damage_or_hit_processing=False, automatic_main_pie=False)
(OUT / 'FinalVerification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
