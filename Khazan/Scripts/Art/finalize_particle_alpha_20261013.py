"""Verify Main delivery and append Art-only completion/continuity records."""
from pathlib import Path
from datetime import datetime
import hashlib,json,re,statistics
MAIN=Path(__file__).resolve().parents[2];ROOT=MAIN/'Metadata/ParticleAlpha_20261013'
read=lambda p:json.loads((ROOT/p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
delivery=read('Delivery.json');verify=read('MainShaderVerify01/Verification.json');snow=read('MainSnow01/Capture.json')
assert delivery['status']=='installed' and verify['status']=='passed' and snow['status']=='passed'
assert len(verify['masters'])==86 and not verify['errors'] and len(verify['instances'])==16
assert read('MainShaderVerify01/Exit.json')['exit_code']==0 and read('MainSnow01/Exit.json')['exit_code']==0
for row in delivery['files']:assert sha(MAIN/row['relative'])==row['after_sha256'],row['relative']
prepare=read('Preparation.json');audit=read('Audit02/Audit.json')
assert sha(MAIN/'Content/Maps/L_HeinMach_Environment.umap')==prepare['main_map_sha256']
protected_systems=[]
for row in audit['systems']:
    p=MAIN/('Content/'+row['path'].removeprefix('/Game/')+'.uasset')
    if row['sha256'] and sha(p)!=row['sha256']:protected_systems.append(row['path'])
assert not protected_systems,protected_systems
assert 'SpawnCountScale=0.200000' in verify['snow']
before=read('SnowBefore02/Capture.json');after=read('SnowAfter01/Capture.json')
averages={}
for layer in ('Source_Flakes_Fast_Large','Source_Dust'):
    a=statistics.mean(r['counts'][layer] for r in before['samples']);b=statistics.mean(r['counts'][layer] for r in after['samples'])
    averages[layer]={'before_mean':a,'work_after_mean':b,'observed_reduction':1-b/a,'main_counts':[r['counts'][layer] for r in snow['samples']]}
cards_before=read('GameCardsBefore02/Cards.json');cards_after=read('GameCardsAfter02/Cards.json')
assert cards_before['status']==cards_after['status']=='passed'
numeric=lambda values:[float(v) for s in values for v in re.findall(r'(?:x|y|z|pitch|yaw|roll): ([-+\d.]+)',s)]
assert numeric(cards_before['camera'])==numeric(cards_after['camera'])
stamp=datetime.now().astimezone().isoformat()
R={'status':'MainApplied_Saved_RHI_GameValidated','at':stamp,'delivery':delivery,
   'scope':{'current_saved_animations':524,'effect_systems':331,'material_interfaces':281,'direct_renderer_materials':203,'base_materials_compiled':86,'alpha_png_textures':138,'hdr_curve_lookup_textures_not_png_exported':4},
   'changes':{'material_masters':13,'material_instances':16,'snow_effect_type':1,'source_config_map_particle_texture_binary_writes':0,'qa_asset_delivery':0},
   'alpha_repairs':['Untextured DefaultParticle had no spatial alpha: retained Masked blend and added elliptic spatial mask instead of a full square.','Selected16 instances sampled constant A255: use R density from their actual sampled texture, bounded particle Alpha and inward edge feather.','Parent scalar defaults0 retain other instances; original source RGB output, textures, particle modules/geometry/age and event timing preserved.'],
   'temporary_visual_values':{'edge_feather_uv':.03,'minimum_edge_pixels':1.25,'untextured_ellipse_power':2,'source':'Assistant-selected presentation tuning for the requested repair, not original shader values.'},
   'snow':{'before_scale':.25,'after_scale':.20,'spawn_rate_reduction':.20,'source':'User requested fewer particles; assistant-selected modest20% reduction.','source_rates_per_second':[1250,2500],'previous_effective_rates_per_second':[312.5,625],'new_effective_rates_per_second':[250,500],'actual_count_observations':averages,'note':'Three game-frame samples are random/time-dependent active counts, not a claim of exactly20% active particles at every instant.'},
   'evidence':{'usage_audit':'Audit02/Audit.json','material_triage':'MaterialTriage.json','channel_evidence':'TextureChannelAnalysis.json','repair_plan':'RepairPlan.json','main_shader_readback':'MainShaderVerify01/Verification.json','same_camera_card_before':'GameCardsBefore02/Cards_150.png','same_camera_card_after':'GameCardsAfter02/Cards_150.png','game_snow_before':'SnowBefore02/Entry.png','work_snow_after':'SnowAfter01/Entry.png','fresh_main_snow':'MainSnow01/Capture.json'},
   'visual_review':{'card_fixture':'Actual standalone same camera: hard squares/black atlas background removed; masks/texture detail remain. Gradient wave cards retain their intended internal pattern; no broad conversion of meshes/Additive materials.','snow':'Same saved Player camera; source two-layer graph/material/size/velocity/lifetime unchanged. Lower spawn scale and fewer active particles verified.','particle_simulation':'EffectsBefore01/After01 exercised8 PS families;4 had no active particles under default standalone parameters. Positive PartGroggy blood, blade/wood samples reviewed; this is not an8-family exhaustive gameplay visual pass.'},
   'failure_history':['Audit01 protected Notifies getter corrected to AnimationLibrary public API.','Textures01 forced PNG exporter on HDR asserted; Textures02 used native compatible exporter selection,4 HDR lookup sources excluded from PNG inspection.','CardsBefore01 reentrant fixture callback failed; only its verified owned hung process was stopped. Other editors were not controlled.','PIE diagnostic viewport mismatch excluded from final visual evidence; standalone saved QA-map regular Shot used.','AlphaApply01-05 intermediate errors/partial saves retained; final DefaultAlpha01 + saved ShaderVerify01/MainShaderVerify01 supersede them.','First Main os.replace was denied while a separate read-only asset consumer was active; retried only after it exited normally.'],
   'limits':['Current saved usage and86 shader graphs checked; screenshots are representative masks/particle families/HeinMach views, not every combat frame at every camera.','Cooked original shader parity and Shipping/network/full-level performance were not tested.'],
   'protected':{'main_heinmach_map_sha256':prepare['main_map_sha256'],'snow_system_sha256':prepare['main_snow_system_sha256'],'all331_original_system_hashes_preserved':True,'gameplay_source_edited':False},'remaining':[]}
(ROOT/'FinalVerification.json').write_text(json.dumps(R,indent=2,ensure_ascii=False),encoding='utf-8')
text=f'''\n\n## {stamp} — 현재 효과 알파 카드 경계·HeinMach 눈 수 Main 수정 완료\n\n정본은 `Metadata/ParticleAlpha_20261013/FinalVerification.json`이다. 기존 사용 metadata→현재524 animation의 notify/HeinMach96 effect component→331 PS/NS·281 material interface를 확인했다. 전체 Content/원작 추출을 재조사하지 않았다. 직접 renderer 재질203/부모86, 현재 alpha 입력의 실제138 PNG 채널·부모/인스턴스 상속을 확인했다. HDR4 lookup/검정 float는 PNG 강제 변환하지 않았다.\n\n공용 `Shared/Materials/Other/DefaultParticle`은 PC.A만 opacity mask로 사용해 실제 카드가 흰 사각형이었다. 기존 Masked blend를 유지하고 타원 공간 마스크를 연결했다.16 sprite instance는 실제 sampled texture의 A가255 상수인 채 불투명 카드를 그렸다. 해당 instance에만 R density/particle Alpha 선행 clamp/안쪽 feather를 적용한다. 부모 default repair0과 원래 source RGB·particle modules/shape/수명·event/animation·mesh/Additive 정책은 보존한다. 어시스턴트 표시 TEMP는 feather.03UV/최소1.25px/무텍스처 ellipse power2이며 원작 shader 수치가 아니다.\n\n메인 선택30파일=부모13+MI16+기존 NET_HM_WeatherBudget1을 hash/CAS 전달했다. Source/Config/map/PS/NS/texture/바이너리·QA asset 전달0이다. 기존 눈2레이어의 source1250/2500 particles_s는 그대로이고 생성 scale.25→.20(어시스턴트 표시 TEMP)으로 rate312.5/625→250/500, 기존 대비20% 줄었다. 실제3샘플 평균 flakes2119→1862.33/dust532.67→454.67로 감소했다. 이는 random/time-dependent active count이며 매 순간 정확히20%라는 뜻이 아니다. 눈 크기/속도/수명/재질·camera/원본 actor 배치는 바꾸지 않았다.\n\n새 MainShaderVerify01은86 material compile errors0·16 scalar override·snow.20, MainSnow01은 실제 game view/count/저장0으로 통과했다. standalone 동일 camera card17의 검은 사각·solid card 제거 및 texture 양성을 직접 확인했다. actualPS8 중4는 기본 단독 parameter에서 active0이므로 전체8 양성 화면 검증이라고 기록하지 않는다. 실제 PartGroggy blood/짧은 blade·wood 표본과 눈 entry/sky를 검수했으며 모든 전투 frame/camera·Shipping/원작 shader 전체 동일성은 주장하지 않는다.\n\n초기 protected API/강제 HDR PNG/fixture reentrancy/PIE viewport/반환값·부분 저장 실패는 각 run에 보존했다. Windows 접근 제한은 별도 consumer의 정상 종료 후 선택 전달로 해결했으며 foreign editor 종료/저장/reload0이다. task-owned CardsBefore01 hung fixture만 정확 PID/args 확인 후 정리했다. 모든331 source system과 HeinMach map·눈 graph hash가 원본과 일치한다. 후속은 이 보고서/RepairPlan/TextureChannelAnalysis에서 표적 시작하고 prepare/전체 author/과거 CAS를 반복하지 않는다. 필수 잔여0이다.\n'''
marker='<!-- ParticleAlpha_20261013_MainCompleted -->'
for name in ['Docs/Art/ART_PROJECT_STATE.md','Docs/Art/ART_WORK_CONTINUITY.md','Docs/Art/ART_KNOWLEDGE_INDEX.md','Docs/Art/HEINMACH_WEATHER_RESTORATION_2026-10-06.md']:
    p=MAIN/name
    if marker not in p.read_text(encoding='utf-8-sig'):
        with p.open('a',encoding='utf-8') as f:f.write(text+'\n'+marker+'\n')
(ROOT/'ResumeState.json').write_text(json.dumps({'status':'complete','at':stamp,'final_verification':'FinalVerification.json','main_asset_writes':30,'remaining':[],'resume':'Use saved final report and targeted alpha evidence. Do not repeat preparation/graph author/installation. QA assets remain only in owned work/baseline projects.'},indent=2),encoding='utf-8')
print(json.dumps({'status':R['status'],'files':30,'material_compile_errors':0,'protected_systems':331,'main_snow_samples':len(snow['samples'])},indent=2))
