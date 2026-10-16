from pathlib import Path
from datetime import datetime
import json

MAIN=Path(__file__).resolve().parents[2]
OUT=MAIN/'Metadata/BeastDodge_20261012'
stamp=datetime.now().astimezone().isoformat()
state={'status':'in_progress','timestamp':stamp,'work':str(MAIN.parent.parent/'Khazan_BeastDodgeWork_20261012/Khazan'),'main_product_writes':0,'approved_main_editor_restart':False,'author_removed':True,'stock_build':'FinalWorkBuild02 passed b555e6d8; FinalWorkBuild03 is current-source merge, inspect its Exit/Build.log','verified':['Patterns01 all 47 entries and real sight/alert/combat','NativeBatch01 SourceAudit/PassivePIE/DefensePIE/RecoveryPIE passed','FinalWorkQA01 first four and Guard/CombatPolicy passed'],'remaining':['Remove bad concurrent Particles/FXSystemComponent.h include (class is already in ParticleSystemComponent.h) after current build finishes','Parry test self-starts PIE: batch driver now avoids duplicate start; rerun','PlayerAttack OverFury 18/19 in first regression: rerun precisely and diagnose if repeated','Finish current Main merge/stock build and feedback relative User.Scale_All review','Main editor restart approval is pending; do not close user session without its response','Exact CAS installation, canonical Main build/fresh checks and final Mixed records'],'fidelity_limits':['Original custom BT native abort/RNG/defaults not supplied','Group1 part destruction producer absent','Selected-step float semantics and native movement/physics equivalence unverified','Apes >= threshold/reset/random independence is an explicit project adapter']}
(OUT/'ResumeState.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
text=f'''\n\n## {stamp} — ARCH-94 Apes·Yetuga StateTree / 플레이어 피격·회피 진행 체크포인트

정본 metadata는 `Metadata/BeastDodge_20261012/ResumeState.json`과 NativeBatch01/Patterns01/FinalWorkQA01이다. Main 게임 Source/Content/Config 전달은 아직 0이다. 분리 프로젝트 Khazan_BeastDodgeWork_20261012에서 원본121개 BT 노드·49 gate·46 skill·10 MoveTo·5 LockOnMove를 보존하고, 선택 실패를 원본 failure edge로 돌리는 실행 상태를 별도로 둔다. Yetuga runtime tree173 state/Apes9 state, 기존 PatternAbility/AIController/Definition을 재사용한다. 새로운 runtime 파일/class는0, 개발용 QA 파일3이다.

Patterns01의 Apes19/Yetuga28(원본24+SI/step alias4) 실제 GAS 실행47건 및 실제 Sight→Roar→전투가 통과했다. NativeBatch01의 SourceAudit, 실제7피격 SideMove passive, 실제 근접/장판/투사체 회피11건·8방향 취소/비용 실패·타 기여 보존, 마지막 피격 후 잠금/이동/회피 복구6건이 통과했다. 피격 잠금0.1초는 어시스턴트 TEMP, Dodge 시작0.1초 무적은 사용자 지정이다. 피격 montage blend-out의 Root Motion만 비활성화하여 이동을 방해하지 않게 한다.

FinalWorkQA01에서는 최초4 및 Guard/CombatPolicy 통과, Parry는 기존 native test의 자체 PIE 요청과 driver 요청이 중복되어 World가 교체된 실패(Driver에서 수정), PlayerAttackCollision은 OverFury19 기대/18 관측으로 재검증이 남았다. 기대값을 낮추거나 성공으로 기록하지 않는다. 새 Main Niagara/피격 표현 Source 변경을 Rebase02로 병합했고 Build.cs는 Main의 기존 Niagara 항목을 그대로 채택했다. 현재 병합본의 잘못된 FXSystemComponent.h include가 컴파일 실패했으며 실제 UFXSystemComponent 선언은 기존 ParticleSystemComponent.h에 있다. 이 한 줄을 제거하고 stock rebuild한다. 생성용 author CPP/추가 editor dependencies는 제거했고 원문은 Completion에 보관했다.

회피 효과는 Fab CursedMagic Dash1/Blink1을 재사용하고 새 유한 .18초 WAV를 제작했다. 원본 VFX 파일은 변경0이며 User.Scale_All의 preset 값을 TEMP 배율 .12/.15로 곱해 설정하는 보완본을 최종 화면 검수한다. 원작 전용 SFX/VFX 또는 pixel 일치를 주장하지 않는다.

메인 에디터 재시작 승인을 비동기로 요청했으며 응답 전 종료/강제 종료를 하지 않는다. 응답 후 최신 PID/프로젝트/dirty/PIE를 재확인하고 정상 종료→최신 Source/Data CAS→canonical stock build→fresh Main SourceAudit/피격/회피/AI/회귀→원래 map 재실행 순이다. Main 소스가 계속 변경되면 작은 3-way 병합을 반복하고 사용자 변경을 보존한다. 원작 custom BT의 native RNG/abort/생략 기본값, Group1 부위 파괴 생성자, 원작 물리·이동·selected-step float 의미는 미확인이다. 현재 엔진 실행 및 저장 구조의 검증과 원작 완전 일치를 구분한다.
'''
with (MAIN/'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md').open('a',encoding='utf-8') as stream:stream.write(text)
print(stamp,flush=True)
