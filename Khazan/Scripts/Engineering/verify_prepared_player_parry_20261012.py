"""Final prepared proof; no Main product edits or foreign process control."""
from pathlib import Path
import difflib, json, runpy
MAIN=Path(__file__).resolve().parents[2];META=MAIN/'Metadata/Parry_20261012'
D=runpy.run_path(str(MAIN/'Scripts/Engineering/deliver_player_parry_20261012.py'),run_name='parry_verify')
WORK=D['WORK']
R=json.loads((META/'PreparedVerification.json').read_text(encoding='utf-8'))
build=json.loads((META/'Build08/Launch.json').read_text())
exitrow=json.loads((META/'Build08/Exit.json').read_text());assert exitrow['exit']==0
for rel in D['SOURCE']:
    assert D['sha'](WORK/rel)==build['source'][rel],('Candidate changed since build',rel)
    assert D['sha'](MAIN/rel)==D['BASE'].get(rel),('Main target changed before delivery',rel)
for name in ['PIE03','GuardRegression01','CollisionRegression01']:
    driver=json.loads((META/name/'Driver.json').read_text());assert driver['status']=='passed' and not driver['shader_failures']
    assert json.loads((META/name/'Exit.json').read_text())['exit']==0
assert json.loads((META/'SavedAudit03/SavedAudit.json').read_text())['status']=='passed'
preview=json.loads((META/'AlphaPreview07/EffectRendering.json').read_text())
assert preview['status']=='passed' and len(preview['effects'])==2
assert preview['hidden_fixture_pawns'][0]['class']=='DefaultPawn'
log=(META/'AlphaPreview07/Editor.log').read_text(encoding='utf-8',errors='replace')
assert not any(s in log for s in ['Failed to compile Material','Default Material will be used'])
for image in ['PP_Player_Parry_Success_2.png','PP_Player_Parry_Success_3.png']:
    assert (META/'AlphaPreview07'/image).stat().st_size>200000
patch=[]
for rel in D['SOURCE']:
    old=(META/'Before'/rel).read_text(encoding='utf-8-sig').splitlines(keepends=True) if (META/'Before'/rel).exists() else []
    new=(WORK/rel).read_text(encoding='utf-8-sig').splitlines(keepends=True)
    patch.extend(difflib.unified_diff(old,new,fromfile='Main/'+rel,tofile='ParryWork/'+rel))
(META/'PreparedSource.patch').write_text(''.join(patch),encoding='utf-8')
R['rows']=D['rows']();assert not any(r['conflict'] for r in R['rows'])
R['prepared_verified']=True;R['complete']=False;R['main_delivered']=False
R['build_input_source_matches_candidate']=True
R['visual_review']={'status':'passed_prepared','actual_viewed':['AlphaPreview07/PP_Player_Parry_Success_2.png','PIE03/02_ActualParryMotion.png','PIE03/03_ActualParryEffectTail.png'],
                    'result':'No opaque card/sphere background boundary; elliptic source spark caps and continuous UV/pixel edge fade. Source emitter graph retained, original MI overrides restored. No original pixel parity claim.'}
R['actual_private_module']=json.loads((META/'PIE03/Driver.json').read_text())['actual_module']
R['locks']=[{'path':r['path'],'winerror':r['lock_error']} for r in R['rows'] if r['lock_error']]
assert len(R['locks'])==2
(META/'PreparedVerification.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
(META/'ResumeState.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
section='''\n\n## 2026-10-12 — 패링 최종 준비본 검증 확정 / Main 2개 잠금 유지

최종 Build08/PIE03(15 case 및 6종 Definition)/SavedAudit03/AlphaPreview07는 Exit0·passed다. native 실제 loaded module SHA는 PreparedVerification.json에 있고 현재 준비 Source7은 Build08 input과 동일하다. Gameplay 제품 Source6은 앞서 성공한 GuardRegression01/CollisionRegression01과 같은 코드다. source MI base-property overrides가 복원된 saved reload, DefaultParticle ellipse power2와 .04 UV/1.25px edge 연결을 확인했다. 실제 game viewport의 .13/.24초 효과 및 dark RHI burst를 직접 열어 원판·불투명 card 경계가 없음을 확인했다. Source shader/pixel 완전 일치와 실제 스피커 출력/Shipping/network 검증을 완료한 것은 아니다.

**Main product Source/package 변경0, 적용 완료가 아니다.** 마지막 preflight는 대상 SHA 충돌0·GA_Player_Guard/AM_DAS_Player_Guard의 Windows error32 2개다. 기존 Main editor PID19752가 계속 실행 중이다. 사용자에게 작업 저장 후 종료 상태만 요청했고 에디터를 임의로 종료하거나 잠금 handle을 강제로 닫지 않았다. exact resume는 Metadata/Parry_20261012/ResumeState.json, review diff는 PreparedSource.patch다. 잠금 해제 이후 해당 Source7/asset13만 반영하고 fresh Main build/PIE/audit를 추가한다. 전체 저작/추출과 과거 DLL 복원은 반복하지 않는다.
'''
for rel in ['Docs/Engineering/PARRY_IMPLEMENTATION_20261012.md','Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md','Docs/Art/PLAYER_PARRY_SOURCE_20261012.md','Docs/Art/ART_WORK_CONTINUITY.md']:
    p=MAIN/rel
    assert section.splitlines()[2] not in p.read_text(encoding='utf-8-sig')
    with p.open('a',encoding='utf-8',newline='\n') as f:f.write(section)
print('PARRY_FINAL_PREPARED_PASS Main product changes=0 Locks=2 Source targets=7 Asset targets=13',flush=True)
