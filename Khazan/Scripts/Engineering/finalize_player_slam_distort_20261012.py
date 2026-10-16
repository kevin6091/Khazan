from pathlib import Path
from datetime import datetime
import hashlib,json
P=Path(__file__).resolve().parents[2];O=P/'Metadata/PlayerSlamDistort_20261012'
def read(n):return json.loads((O/n).read_text(encoding='utf-8-sig'))
assert read('MainBuild03/Exit.json')['exit']==0
assert read('MainSaved01/SavedAudit.json')['success']
assert read('MainPIE02/Driver.json')['status']=='passed'
assert read('MainPIE02/Native/Result.json')['passed']
delivery=read('Delivery.json')
for r in delivery['files']:assert hashlib.sha256((P/r['file']).read_bytes()).hexdigest()==r['after'],r['file']
stamp=datetime.now().astimezone().isoformat()
report={'status':'MainDeliveredAndFreshVerified','complete':True,'date':stamp,'files':delivery['files'],
 'current_runtime':'existing shared Niagara schema/execution from concurrent ARCH-95 reused; one factory floor-normal/sort/dilation addition; two invalid FXSystemComponent include lines removed for UE5.8 build compatibility',
 'asset_packages':6,'new_runtime_classes':0,'source_original_niagara_unchanged':True,
 'source_start_seconds':3.741868019104004,'source_end_seconds':3.8630430698394775,
 'floor_normal':'User.KZFloorNormal; three local-space renderers bind to the actual traced surface normal',
 'alpha_TEMP':'Original opacity times normalized radial 1-smoothstep(.8,1,r); refraction returns to neutral1 at edge; original scalar/vector/texture overrides preserved',
 'build':'MainBuild03/Exit.json','saved':'MainSaved01/SavedAudit.json','runtime':'MainPIE02/Driver.json',
 'runtime_checks':'MainPIE02/Native/Result.json','actual_loaded_module':read('MainPIE02/Driver.json')['actual_loaded_module'],
 'module_sha256':read('MainPIE02/Driver.json')['module_sha256'],
 'failed_runs_preserved':['MainBuild01 stale foreign HotReloadState link response','MainBuild02 canceled own queued process before unsafe stock-mode selection','MainPIE01 startup during concurrent Main binaries rebuild'],
 'editor_control':'Existing user/foreign editor save/reload/PIE/terminate0; task-owned processes only',
 'limits':'User-chosen Fab Niagara is not original-game metadata. No original shader/pixel parity or shipping performance claim.'}
(O/'FinalVerification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'ResumeState.json').write_text(json.dumps({'complete':True,'status':report['status'],'final':'FinalVerification.json','remaining_required':[]},indent=2)+'\n',encoding='utf-8')
eng=f'''\n\n## {stamp} — 내려찍기 KZ_Parring_Distort Main 완료\n\n기존 FallAttack의 Start3.741868019104004/End3.8630430698394775 branching 부모 안에 KZExtra_PlungeDistort child 한 쌍을 추가했다. 기존 source ground dust·GUID·section/segment·공격 판정/피해/오디오·RateScale은 보존했다. 최신 Main ARCH-95의 NiagaraTemplate/공통 UFX 실행·종료·module 의존성을 재사용하고 shared factory에 실제 traced floor normal의 User.KZFloorNormal와 sort/dilation 처리만 합쳤다. UObject receipt·끝/취소 cleanup은 기존 ActionAbility 소유다. UE5.8에서는 UFXSystemComponent가 기존 ParticleSystemComponent.h에 선언되므로 없는 별도 include 두 줄을 제거했다. 새 runtime class/file/tag0이다.\n\n선택 전달8행(기존 runtime factory1/DEV1/asset6)과 include 보완2, MainBuild03 exit0, fresh MainSaved01 저장0, MainPIE02 actual input fall→landing의 유효1개·바닥/분리/normal·정지·기존 dust 유지가 통과했다. 실제 loaded current canonical module와 파일 SHA는 Metadata/PlayerSlamDistort_20261012/FinalVerification.json에 있다. 초기 floor rotation90도 trial은 철회했고 최종 RelativeRotation0/Scale1과 normal binding을 사용한다. 사용자/foreign editor 저장·종료·reload0이며 후속 stock build의 current manifest를 보존했다. 필수 잔여0; 전체 author/과거 alias 전달은 반복하지 않는다.\n'''
art=f'''\n\n## {stamp} — 내려찍기 바닥 Niagara·alpha Main 완료\n\n사용자 지정 /Game/VFX/03_SlashHit/KZ_Parring_Distort의 원본6 emitter는 그대로 보존했다. /Game/_Art/Effects/Combat/PlayerSlamDistort/NS_Player_Plunge_ParringDistort 복제의 M_SW_distort_Sprite_0/M_SW_distort_Sprite001_1/Hit003_6 renderer만 CustomFacingVector 및 실제 User.KZFloorNormal로 저작했다. shader에 카메라 facing을 남기는 잘못된 수동 binding trial은 native author의 host-map binding3개 true로 대체됐다.\n\n원본 parent/MI2쌍을 새 경로에 복제하고 기존 opacity에 UV radial feather(.8–1)를 곱하며 refraction 가장자리를 중립1로 돌려 사각 경계를 제거했다. 이는 어시스턴트 표시 TEMP이고 원작 직접 수치가 아니다. scalar/vector/texture override는 원본과 동일하다. 원본 source Niagara/머티리얼/텍스처를 수정하지 않았다. 실제 RHI PrivatePIE05/Fall_02 화면에서 부드러운 바닥 원형과 사각 경계 제거를 검수했고, fresh Main saved/RHI가 같은6 package를 검증했다. 경로·SHA·runtime 증거는 Metadata/PlayerSlamDistort_20261012/FinalVerification.json. Fab 사용자 지정 효과와 원작 metadata 재현은 구분하며 원작 pixel/shader 동일성은 주장하지 않는다.\n'''
for rel in ['Docs/Engineering/ENGINEERING_PROJECT_STATE.md','Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md','Docs/Engineering/PLAYER_ATTACK_VFX_RUNTIME_20261008.md']:
 with(P/rel).open('a',encoding='utf-8') as f:f.write(eng)
for rel in ['Docs/Art/ART_PROJECT_STATE.md','Docs/Art/ART_WORK_CONTINUITY.md','Docs/Art/ART_KNOWLEDGE_INDEX.md','Docs/Art/PLAYER_ATTACK_VFX_PLAYBACK_20261008.md']:
 with(P/rel).open('a',encoding='utf-8') as f:f.write(art)
print('SLAM_DISTORT_MAIN_COMPLETE',stamp)
