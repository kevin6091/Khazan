"""Persist the delivered sword policy and the unresolved shield-motion identity."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json

ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Metadata/MonsterAttackFilter_20261012'
stamp=datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
def read(n):return json.loads((OUT/n).read_text(encoding='utf-8'))
def write(n,v):(OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
audit=read('MainSaved01/Report.json');assert audit['success'] and not audit['saved']
assert read('MainSaved01/Exit.json')['exit']==0
delivery=read('Delivery.json');assert len(delivery['files'])==2
for row in delivery['files']:assert sha(ROOT/row['file'])==row['after']
baseline=read('Baseline.json')['files']
for p,h in baseline.items():
    if '/SwordShield/' in p or p.endswith('BP_Monster_SwordShield.uasset'):assert sha(ROOT/p)==h
sword=audit['families']['Swordsman']['after'];shield=audit['families']['SwordShield']['after']
assert len(sword['attacks'])==3 and len(sword['grants'])==12
assert len(shield['attacks'])==3 and len(shield['grants'])==8
result={'status':'SwordsmanMainVerified_ShieldMotionAwaitingIdentification','utc':stamp,
    'swordsman_complete':True,'shield_motion_identity_resolved':False,'files':delivery['files'],
    'excluded':['/Game/Monsters/Swordsman/Abilities/GA_Kick.GA_Kick_C','/Game/Monsters/Swordsman/Abilities/GA_Rush.GA_Rush_C'],
    'kept_attacks':sword['attacks'],'swordsman_initial_grants':12,'shield_attacks':shield['attacks'],
    'shield_initial_grants':8,'shield_bytes_unchanged':True,'fresh_audit':'MainSaved01/Report.json',
    'verified_placed_actors':audit['placed_actors'],'protected_settings_match_original':True,
    'runtime_cpp_changes':0,'config_changes':0,'native_delivery':0,'pie_ran':False,
    'verification_limit':'Saved CDO/definition and placed-actor policy checked. No newly executed gameplay/pose verdict.',
    'pending_question':'Which SwordShield motion was described as a kick: ShieldCrash, SwordCombo, or Swordsman Kick only?'}
write('FinalVerification.json',result)
write('ResumeState.json',{'complete':False,'status':result['status'],'utc':stamp,'swordsman_complete':True,
    'remaining':['Identify the shield motion if the user still wants a shield attack excluded.'],
    'next_steps':['Start from current Main and MainSaved01; do not reimport or delete animation/ability resources.',
        'After the user identifies the shield motion, map it to the current ability/node/montage using the recorded shield attack paths.',
        'Back up the current affected asset(s), change only the selected shield candidate/grant or proven combo edge in the task-owned project.',
        'Fresh-verify saved values, preserve remaining attacks and unrelated definition settings, CAS-deliver selected files, then audit current placed actors.']})
delivery['status']=result['status'];delivery['verified_utc']=stamp;write('Delivery.json',delivery)
marker='MonsterAttackFilter_20261012_SwordsmanMainVerified'
text=('사용자 요청으로 검병 GA_Kick와 GA_Rush를 기존 BP_Monster_Swordsman.AttackAbilities 및 DA_Character_Swordsman.InitialAbilityGrants에서 제외했다. '
    '공격 후보5→3, 초기 grant14→12다. 남은 GA_EmpireSword_Early_Slash/Early_Smash/Pierce 및 Alert/Idle/Exhaustion/HitReaction은 유지한다. '
    '기존 ARCH-77 StateTree 선택→ASC Spec 활성화→ComboAction 실행을 재사용하며 runtime C++/Tag/Config/DLL 변경0이다. '
    '게임 리소스 삭제·montage/animation/collider/VFX/피해 설정 수정0, 새 runtime file/class0이다. '
    '별도 Khazan_AttackFilterWork_20261012에서 두 asset만 저장했고 Main에 exact SHA/CAS로 전달했다. '
    'Prepared02 및 새 MainSaved01 Success/Exit0, AttackAbilities/InitialAbilityGrants와 보호된 AI/Locomotion/HitReactions/MonsterStamina/Unaware/InitialEffects의 원본 보존을 확인했다. '
    'DevMap 배치 검병7개 모두 후보3, 방패병1개 후보3을 fresh load로 확인했다. HeinMach에서 해당 두 BP의 배치 actor는0이다. '
    '이는 saved policy 검증이며 새 PIE 실행·제자리 달리기 체감 검증으로 기록하지 않는다. '
    '방패병은 수정 전후 모두 SwordCombo/Pierce/ShieldCrash 후보3, 초기 grant8이며 Kick 클래스가 없다. '
    '두 방패병 asset의 byte SHA는 원본과 동일하다. 사용 중4개 sequence의 raw 발/골반 포즈41시점은 Probe02에 보관했지만, 수치만으로 사용자가 말한 발차기 동작을 확정하지 않는다. '
    '방패치기인지 검 연속공격인지 사용자에게 동작 식별을 질문한 상태다. 임의로 sword swing이나 ShieldCrash를 제거하지 않았으며 방패 동작 제외는 미완료/식별 대기다. '
    '정본은 Metadata/MonsterAttackFilter_20261012/FinalVerification.json 및 ResumeState.json. 확인 후 current Main의 해당 후보/grant 또는 실제 kick node만 작은 data 변경으로 제외하고 새 saved/배치 actor 검증을 수행한다.')
for name in ['MONSTER_AI_IMPLEMENTATION_20261006.md','ENGINEERING_PROJECT_STATE.md','ENGINEERING_WORK_CONTINUITY.md']:
    p=ROOT/'Docs/Engineering'/name
    if marker not in p.read_text(encoding='utf-8-sig'):
        with p.open('a',encoding='utf-8') as f:f.write('\n\n## '+stamp+' — 검병 발차기·돌진 제외 Main 완료 / 방패병 동작 식별 대기\n\n'+text+'\n\n<!-- '+marker+' -->\n')
print('SWORD_MAIN_VERIFIED_SHIELD_IDENTIFICATION_PENDING',flush=True)
