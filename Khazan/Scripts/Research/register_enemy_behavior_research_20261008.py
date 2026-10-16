"""Append scoped research pointers without replacing existing domain history."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MARKER = '<!-- ApesYetugaBehaviorResearch_20261008 -->'

entries = {
    '0_DOCUMENT_ROUTER.md': '''
## 2026-10-08 — Apes 엘리트·Yetuga 보스 원작 패턴 분석 조회점

패턴/공격/회복 요청은 Art+Engineering이다. [원본·공개자료 감사](Docs/Art/APES_YETUGA_PATTERN_SOURCE_AUDIT_20261008.md)와 [행동 분석](Docs/Engineering/APES_YETUGA_BEHAVIOR_ANALYSIS_20261008.md) 최신 보완 절→Metadata/EnemyBehaviorResearch_20261008의 표적 report→필요한 package/export 순으로 읽는다. 원작 cooked AI/SI/SB/CS/AP·공개 전투 표적프레임·공식5→8초 exhaustion을 대조했다. 분석 완료이며 신규 몬스터AI/게임코드/asset 적용·build·PIE 완료가 아니다. ARCH-79의4NPC와 Yetuga/Apes library 상태는 유지한다.

Apes Early/Standard 일반군·피격passive가 다르고 Yetuga는 custom BT다. step/시각동작/notify/attack group/실제적중을 구분한다. BT HP raw65/60/50(bCompareRate=false)을퍼센트로바꾸지않는다. 현재asset212개이름은 CurrentApesYetugaLibrary.csv를조회하고 oldPlayback경로를재사용하지않는다. 동명이름 DamageParry는 Index.local_path/full package로구분한다. 전체추출/retime/rename을반복하지않는다.
''',
    'Docs/Art/ART_KNOWLEDGE_INDEX.md': '''
## 2026-10-08 — Apes·Yetuga 패턴의 재사용 근거

첫 자료는 [APES_YETUGA_PATTERN_SOURCE_AUDIT_20261008.md](APES_YETUGA_PATTERN_SOURCE_AUDIT_20261008.md) 최신 절이다. Metadata/EnemyBehaviorResearch_20261008의 ApesOriginalAnalysis/Evidence/ResolvedBranches, YetugaOriginal/AIContractSummary/SkillStepsBranches/SkillAvailability/YetugaOriginalSkillAnalysis, root YetugaOriginalDefenseRecovery, PublicApes/PublicYetuga 및 ResearchVerification를 재사용한다. 원본 package/export-index/field/raw/hash, 현재212개source mapping, 공개clip정확URL/시각/hash를 보존했다.

Yetuga exhaustion GroggyStand/New, 직가 GroggyStr, 등 PartGroggy는 별도포즈다. NormalAtk01의동작4와group5를구분한다. DamageParry의 Moving/Reaction 및 Armageddon 동명이인사본은 Index.local_path로찾는다. 기존SourceMetadataZIP/게임asset은변경하지않았고 추가library재추출/retime/rootrepair는없다. gameplay 해석·native미확인은 Engineering 분석에 분리했다.
''',
    'Docs/Art/ART_PROJECT_STATE.md': '''
## 2026-10-08 — Apes·Yetuga 패턴 원본/공개 자료 분석 완료

APES_YETUGA_PATTERN_SOURCE_AUDIT_20261008.md 및 Metadata/EnemyBehaviorResearch_20261008을 따른다. 기존원본hash·공개전투표적프레임·공식patch·현행212asset경로를대조했다. original/cache/public/시간검증/report를새research영역에저장하고 도메인문서에분리기록했다. 게임에셋·원본ZIP·Root Motion옵션·재생률·Skeleton/scale은수정하지않았다. 분석완료와새AI구현/원작런타임일치검증을구분한다. 미관련Snow/렌더링/physics작업의완료·대기상태를이번연구로변경하지않는다.
''',
    'Docs/Engineering/ENGINEERING_PROJECT_STATE.md': '''
## 2026-10-08 — Apes·Yetuga 행동/공격 원작 분석 완료

APES_YETUGA_BEHAVIOR_ANALYSIS_20261008.md 최신보완절을따른다. Apes Early/Standard 가중군·피격횡이동/후퇴·연계, Yetuga custom121node/40CanUseSkill·거리/후방·조건부연속공격/두잡기/얼음/브레스·방어/부위파괴/고갈을원본과공개프레임으로대조했다. BT HPraw65/60/50단위·native event/취소·Rate/group reset·실제Brutal창은미확인이다. 공식고갈5→8초와CS term8이일치하지만 회복SI6.4와동일parameter가아니다.

이번패턴연구의게임Source/BP/asset수정·build·PIE는0회다. 기존ARCH-79의4NPC구현/StateTree/ComboAction·사용자변경을유지했다. Yetuga/Apes는library만있으며신규AI를적용했다고기록하지않는다. source/공개증거검증은ResearchVerification.json, 최초동명이름cache실패와정확package분리도보존했다. 직접구현후속은별도사용자요청과기존최소구조기준으로진행한다.
''',
    'Docs/Art/ART_WORK_CONTINUITY.md': '''
## 2026-10-08 — Apes·Yetuga 연구 완료·후속 재개 절차

본 패턴자료분석은완료다. Art정본 APES_YETUGA_PATTERN_SOURCE_AUDIT_20261008.md→Engineering분석→Metadata/EnemyBehaviorResearch_20261008/{ResearchVerification,CurrentApesYetugaLibrary,ApesOriginalResolvedBranches,YetugaOriginalDefenseRecovery} 및 YetugaOriginal/표적SkillAnalysis·Public manifest를읽는다. 원본237사본/59Apes기초hash·공개27Yetuga/20Apesmanifest·현재212asset의정적검증을완료했다. flat DamageParry충돌은PackageCopies/Index.local_path로해결했고실패기록은보존했다.

추가필요자료는Apes HeinMachEarly2 level498–501, YetugaIntro호출, native단위/default/event/group/취소소비다. 해당원본만표적조회한다. 이미완료한추출/전체library/retime/rename/rootmotion설정을반복하지않는다. 사용자요청은분석이므로이번연구에서게임Source/BP/assets/에디터/PIE를수정하지않았다. 이절은기존Snow대기등다른작업의재개기록을대체하지않는다.
''',
    'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md': '''
## 2026-10-08 — Apes·Yetuga 연구 완료·미확인 계약 후속

분석정본은 APES_YETUGA_BEHAVIOR_ANALYSIS_20261008.md의스킬/방어최종보완절이다. 마지막검증은ResearchVerification.json 및Skill75/Defense40개원본SHA·참조검증이다. Source/BP/assets/build/PIE적용은없다. 기록된미확인은실패한구현이아니라 native소비자료/통제실험이없는범위다.

재개:(1)Router→Architecture최신/현재Migration→본정본과저장Art/report를읽는다.(2)요청이추가분석인지직접구현인지구분한다.(3)native의HPraw65/60/50·ratio/default·고갈timer/Brutal·Rate/조건결합·AttackSuccess/OnAttack·group reset·실행중중단을표적확인한다.(4)추가영상은버전/난이도/HP/기력/거리/각도/방어결과를고정한다.(5)구현시기존StateTree/Definition/ComboAction에서필요부분만확장하며무조건콤보/단일Phase2bool/새manager를선행생성하지않는다. 기존4NPC·사용자변경·다른continuity작업을보존한다.
'''
}

for relative, body in entries.items():
    path = ROOT / relative
    prior = path.read_bytes()
    if MARKER.encode('utf-8') in prior:
        continue
    with path.open('ab') as stream:
        stream.write(('\n\n' + MARKER + '\n' + body.lstrip()).encode('utf-8'))
    assert path.read_bytes().startswith(prior)
    print('Appended:', relative)
