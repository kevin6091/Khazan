"""Append task findings as UTF-8; bind the prepared delivery to saved evidence."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, runpy
MAIN=Path(__file__).resolve().parents[2];META=MAIN/'Metadata/Parry_20261012'
D=runpy.run_path(str(MAIN/'Scripts/Engineering/deliver_player_parry_20261012.py'),run_name='parry_receipt')
WORK=D['WORK']
def append(rel,section):
    p=MAIN/rel
    assert p.exists(),p
    marker=section.splitlines()[0]
    if marker not in p.read_text(encoding='utf-8-sig'):
        with p.open('a',encoding='utf-8',newline='\n') as f:f.write('\n\n'+section+'\n')
    print('PARRY_DOC',rel,flush=True)

eng='''## 2026-10-12 — ARCH-90 패링 준비본: 실제 검증 / Main 잠금

기존 Guard/ASC/Combo/MonsterSkillObject 6 runtime 파일의 작은 확장으로 시작 후 0.146초 전방 blockable 적중을 패링한다. 원작 raw 0.292초를 현재 GuardStart inverse_map으로 계산했으며 비용 배율 0.5와 effect detach 0.06초는 직접 source 값이다. 기존 몬스터 Definition의 사용자 결정 ParryStaminaDamage와 Pattern Parried/고갈 정책을 재사용한다. 새 runtime class/file/태그/GE/Manager는 0개이며 새 DEV test 1개다. Source·책임·cleanup·값 구분·에디터 설정·검증은 [PARRY_IMPLEMENTATION_20261012.md](PARRY_IMPLEMENTATION_20261012.md)에 기록했다.

task-owned ParryWork의 실제 melee/field 15개 상황과 6종 몬스터, 고갈/좌측 response/비용/동일 HitGroup/독립 연타/Release/Cancel/UnPossess를 확인했다. 기존 Guard와 PlayerAttackCollision도 성공했다. 기존 5개 재생 segment·notify는 fresh reload로 동일하며 Montage refresh의 Suc_R 파생 cache 차이는 따로 기록했다. 원작 normal Guard의 JustGuard 설정을 그대로 복원한 것이 아니라 사용자 요청에 따른 시작 창 adapter다.

**Main 구현 반영은 미완료다.** GA_Player_Guard와 AM_DAS_Player_Guard가 기존 Main editor PID19752의 Windows 공유 잠금(error32)으로 대기한다. 대상 SHA 충돌0이며 Source·package를 부분 복사하지 않았다. 사용자/foreign editor 종료·제어0, private DLL/과거 manifest 복원0이다. 현재 잠금과 candidate SHA는 Metadata/Parry_20261012/DeliveryPreflight.json, 준비본 검증과 정확한 재개는 PreparedVerification.json/ResumeState.json을 따른다.
'''
for name in ['ENGINEERING_PROJECT_STATE.md','ENGINEERING_WORK_CONTINUITY.md','CHARACTER_GAMEPLAY_ARCHITECTURE.md','CHARACTER_TAG_ABILITY_MIGRATION.md','GUARD_IMPLEMENTATION_20261002.md']:
    append('Docs/Engineering/'+name,eng)
art='''## 2026-10-12 — Player Parry 준비본과 alpha 검사 정정

원작 Just_L/R composite의 반대 이름 raw sequence 참조, DilationAnimPositions 31개를 사용한 22/60초 bake, PP_Damage_Spray.NewJustGuard→PP_AtkEx_JustGuard의 13 emitter, 기존 원작 성공 cue를 연결했다. 새 motion2/particle1/master3/MI5=11개와 기존 Guard GA/Montage2개가 준비본이다. 정확한 package/SHA·수치·현재 검증 범위는 [PLAYER_PARRY_SOURCE_20261012.md](PLAYER_PARRY_SOURCE_20261012.md)에 기록했다. 공유 원본·Audio Notify·다른 작업은 저장하지 않았다.

최초 어두운 effect preview의 검은 원판은 shader 결함이라는 가설과 달리 검사 전용 빈 GameModeBase 맵에 생성된 **DefaultPawn_0의 구형 메시**였다. AlphaPreview06의 hidden_fixture_pawns에 origin(0,0,0)을 기록했고 이 Pawn만 숨긴 실제 RHI 캡처에서 원판이 사라졌다. AlphaPreview01–05 및 Isolate03은 그 fixture가 가려 외관 합격 근거로 사용하지 않는다. 보호된 LOD property를 직접 변경하려던 Isolate01/02는 API 실패로 끝났으며 task-owned process만 정리했다.

불필요한 local5 MI의 Additive 통일과 black-emissive gate는 AlphaFinalize02에서 철회했다. 모든 MI의 원본 base-property overrides를 복원했으며 particle의 13 emitter를 모두 유지했다. local3 parent의 continuous opacity와 0.04 UV / 최소1.25px edge feather만 유지한다. untextured DefaultParticle spark는 elliptic alpha와 ParrySparkSoftnessPower=2로 모서리·끝을 부드럽게 했다. 이 세 수치는 원작이 아닌 어시스턴트 임시 표현 값이다. root shader/source pixel parity·Shipping 성능은 미확인이다. 최종 preview/saved readback 결과는 PreparedVerification과 하단 후속 기록을 따른다.

**Main 에셋 반영은 잠금으로 대기한다.** 다른 에디터/채팅은 제어하지 않았다. 재추출/전체 author를 반복하지 않고 DeliveryPreflight/ResumeState의 대상만 SHA 확인 후 복사하고 fresh Main saved/RHI를 검증한다.
'''
for name in ['ART_PROJECT_STATE.md','ART_KNOWLEDGE_INDEX.md','ART_WORK_CONTINUITY.md','PLAYER_PARRY_SOURCE_20261012.md']:
    append('Docs/Art/'+name,art)

receipts={}
for name,report in [('Build08','Exit.json'),('PIE02','Driver.json'),('GuardRegression01','Driver.json'),('CollisionRegression01','Driver.json'),('SavedAudit03','SavedAudit.json'),('AlphaPreview07','EffectRendering.json'),('PIE03','Driver.json')]:
    p=META/name/report
    if p.exists():receipts[name]={'report':str(p.relative_to(MAIN)),'sha256':D['sha'](p),'status':json.loads(p.read_text()).get('status'), 'exit':json.loads(p.read_text()).get('exit')}
rows=D['rows']()
R={'utc':datetime.now(timezone.utc).isoformat(),'status':'prepared_main_locked','complete':False,'main_delivered':False,
   'main':str(MAIN),'work':str(WORK),'runtime_files_changed':6,'runtime_new_classes_files':0,'dev_test_new_files':1,
   'existing_assets':2,'new_assets':11,'rows':rows,'receipts':receipts,
   'unverified':['Fresh Main build/PIE/saved audit after lock release','Original shader/pixel/impact-point exact parity','Shipping/network behavior/performance'],
   'next':['Save and close existing Main editor to release two package locks','Run deliver_player_parry_20261012.py preflight; preserve/merge any concurrent Main changes','Run deliver_player_parry_20261012.py deliver; copy no private DLL/config/plugins','Run parry_task_20261012.py main_build MainBuild01 using an unused suffix/current Main source','Run fresh main_rhi MainPIE01 parry_pie_driver_20261012.py and main_commandlet MainSavedAudit01 audit_player_parry_20261012.py','Run existing Guard/PlayerAttackCollision regression in fresh Main process; bind actual source/assets/module and append completion'],
   'do_not_repeat':['stage','Full author/extraction/import','Old/private DLL or module manifest restoration']}
R['locks']=[{'path':r['path'],'winerror':r['lock_error']} for r in rows if r['lock_error']]
R['conflicts']=[r['path'] for r in rows if r['conflict']]
notify='Source/Khazan/Animation/Notifies/KZAnimNotify_PlayAudio.cpp'
R['attached_audio_notify_unchanged']=D['sha'](MAIN/notify)==D['BASE'][notify]
assert R['attached_audio_notify_unchanged']
(META/'PreparedVerification.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
(META/'ResumeState.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('PARRY_PREPARED_RECEIPT',len(rows),len(receipts),len(R['locks']),len(R['conflicts']),flush=True)
