from pathlib import Path
from datetime import datetime,timezone,timedelta
import json
root=Path(__file__).resolve().parents[2];out=root/'Metadata/MonsterRootCollisionRepair_20261012'
stamp=datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
state={'date':stamp,'status':'private_repair_runtime_validation','main_applied':False,'usage_audit':'MainUsageAudit02/Usage.json','root_audit':'MainUsageAudit02/RootAudit.json','basis_audit':'MainBasis03/Basis.json','movement_source_audit':'MainMoves01/Moves.json','scope':{'families':6,'used_sequences':395,'definitions':57,'nodes':220,'attack_windows':405},'root_option_failures':0,'root_track_failures':0,'stage':'Stage.json','baseline':'Baseline.json','private_project':'C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan','private_runtime_files':['Ability/Combo/KZComboActionAbility.cpp','Animation/Notifies/KZAnimNotify_CombatEffect.cpp','Character/KZMonster.h','Character/KZMonster.cpp'],'private_dev_files':['Tests/KZPlayerAttackCollisionPIETest.cpp'],'latest_build':'FixBuild01/Exit.json','running':'FixedLateHit01 own PID30156/session14864','failed_or_historical':['MainUsageAudit01 CDO definition unresolved before BeginPlay; exact existing tagged DA paths used in02.','MainBasis01 invalid Transform constructor;02 collected339 pose rows then unsupported montage composite_sections;03 complete.','BaselineLateHit01 demonstrates paused-boundary HP7; normal late/OverFury also failed before fixture clock fix. World-time stimuli cannot be treated as montage-clock proof. Fixed test now logs actual clock.'],'remaining':['Read FixedLateHit01 result. Keep all16 actual cases, including existing Spin7/OverFury19 and late approaches.','Prove and repair vertical PatternMoves consuming original800/2000cm offsets while CMC stays Walking, if actual fixture confirms.','Build and run all-six actual root/geometry/end/cancel and current-pose VFX tests. Update existing VFX QA expected actor-basis/body-scale.','Fresh saved audit must preserve395 root options/tracks/data, source damage/window/group/time/sound and current assets.','CAS selected runtime/DEV changes onto latest Main, build fresh Main, run actual tests, reload Main after preserving dirty work. Do not restore old private DLL or broad author scripts.']}
(out/'ResumeState01.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
eng=f'''

## {stamp} — ARCH-91 몬스터 Root/공격 판정/이펙트 후속 검사 중

사용자의 직접 수정 요청이다. 최신 Main의 6종 실제 소비자를 재조회했다: 시퀀스395/Definition57/Node220/window405/montage126. MainUsageAudit02/RootAudit는 asset save0/dirty0이며 모두 EnableRootMotion/ForceRootLock=true, true skeleton root index0/track0 정상이다. pelvis 등의 child 움직임184개를 root 이관 근거로 사용하지 않는다. 아직 런타임의 모든 root 이동이 정상이라고 주장하지 않는다.

기존 ComboAction·엔진 timer/shape·GAS dedup/피해·Monster/Notify의 표시 수명을 재사용한다. private에서 닫힌 끝 경계의 재검사와 마지막 window 이후 callback 예약을 차단하고, 기존 actor 축/locked-root baked collision 좌표에 현행 mesh relative scale을 한 번 반영했다. Source339 pose 비교는 actor 축의 root-stripped anchor가 원본 baked anchor와 맞으며 mesh yaw/root travel을 다시 더하면 오차가 커짐을 확인했다. 새 gameplay 수치를 넣지 않고 실제 body transform을 사용한다. VFX는 Monster의 socket 없는 actor 기준/실제 몸 크기와 source-correction의 같은 프레임 final bone을 사용하도록 기존 owner를 보완했다. 새 runtime file/class/manager0이다. LatestSourceTime은 GT notify clock→GT bone-finalize의 실제 지연 소비값이며 End/취소/EndPlay의 기존 delegate cleanup을 사용한다. Player/audio/UI/혈액·사망 값은 보존한다.

현재 Main Source/asset 수정0이다. Main을 idle GiantFallWork에 한 번 snapshot했고 baseline native late hit fixture를 보존했다. BaselineLateHit01의 paused-boundary HP7과 world-clock 기반 normal/OverFury 실패를 구분한다. QA를 실제 montage clock 기준으로 보완한 FixBuild01은 성공·input동일이고 FixedLateHit01이 실행 중이다. giant PatternMoves54의800/2000cm vertical curves와 Walking 소비의 실제 확인, six-family runtime/FX/저장 보존/CAS Main 전달·fresh build/실제 테스트가 남는다. 현재 상태/실패/정확한 다음 절차는 Metadata/MonsterRootCollisionRepair_20261012/ResumeState01.json을 따른다. 완료된 old stage/author/delivery를 반복하거나 private DLL을 Main에 전달하지 않는다.
'''
for rel in ['Docs/Engineering/CHARACTER_GAMEPLAY_ARCHITECTURE.md','Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md']:
    with (root/rel).open('a',encoding='utf-8') as f:f.write(eng)
art=f'''

## {stamp} — 몬스터 실제 사용 Root/좌표 후속 검사 중

현재 실제 소비자 시퀀스395는 Root 옵션과 true-root/첫 track 모두 정상, save0/dirty0이다. 기존 CurrentAnimationLibrary와 cached collision/VFX plan을 재사용해 Source339 bone samples와 baked attachment origin을 비교했다. 원본 좌표는 actor 축/root-stripped이며 실제 render mesh1.2/1.3 크기가 기존 collision mapping에서 누락됐다. socket 없는 VFX의 actor 기준과 current final pose 보정은 runtime에 한해 private에서 진행 중이다. Root/골격/키/notify/원본 texture·particle 값과 package를 재저작하지 않았다. 현재 Main 적용 완료가 아니며 숫자/원본 출처는 Metadata/MonsterRootCollisionRepair_20261012/MainBasis03/Basis.json 및 MainUsageAudit02/RootAudit.json, 진행/재개는 Engineering continuity와 ResumeState01.json을 따른다.
'''
with (root/'Docs/Art/ART_WORK_CONTINUITY.md').open('a',encoding='utf-8') as f:f.write(art)
print('CONTACT_CHECKPOINT',stamp)
