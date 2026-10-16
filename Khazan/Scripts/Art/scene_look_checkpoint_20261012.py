"""Append an exact resumable Art checkpoint, preserving shared document histories."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'Metadata/SceneLook_20261012'
stamp=datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
plan=json.loads((OUT/'PreparedDelivery.json').read_text())
write=lambda n,v:(OUT/n).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
write('PreparedVerification.json',{'status':'PreparedAndVerifiedAwaitingMainMapUnlock','utc':stamp,
    'selected_packages':len(plan['files']),'prepared_saved':'PreparedSaved02/SavedAudit.json',
    'real_game_viewport':['DevAfter02/Capture.json','HeinAfter04/Capture.json'],
    'visual_comparisons':['DevMap_BeforeAfter.jpg','HeinMach_BeforeAfter.jpg'],
    'main_delivery':'DeliveryBlocked.json','main_content_writes':0,
    'original_actor_poses_preserved':10032,'original_material_parameters_preserved_except_TEMP_emission_three':True,
    'runtime_source_changes':0,'config_changes':0,'native_delivery':0,
    'original_shader_pixel_parity_verified':False,'shipping_performance_verified':False})
write('ResumeState.json',{'complete':False,'status':'AwaitingMainMapUnlock','utc':stamp,'main_editor_pid_at_preflight':16504,
    'reason':'Windows error32: Content/Maps/DevMap.umap rejects replacement while Main editor holds it',
    'product_writes_to_main':0,'prepared_packages':493,'source_config_module_delivery':0,
    'last_verified':'PreparedSaved02, DevAfter02, HeinAfter04; all Exit0/Success and images reviewed',
    'next_steps':[
        'After Main editor save/close, inspect current Main file hashes against PreparedDelivery.json. No reauthor/reimport.',
        'Run bundled UE python Scripts/Art/scene_look_deliver_20261012.py install.',
        'If Main files changed, preserve them and rebase only lighting/PP field changes onto a new isolated current snapshot.',
        'Run scene_look_task_20261012.py main_author MainSaved01 HeinMach Scripts/Art/scene_look_saved_audit_20261012.py.',
        'Run main_rhi MainDevAfter01 DevMap, then main_rhi MainHeinAfter01 HeinMach sequentially.',
        'Review actual Main images; confirm493 SHA/exit/shader errors and native loaded path; rerun comparisons script.',
        'Write FinalVerification/complete ResumeState and append completion to Art doc/state/index/continuity/router.']})
marker='SceneLook_20261012_PreparedAwaitingMainUnlock'
locator='[SCENE_LIGHTING_MATERIAL_REFINEMENT_20261012.md](SCENE_LIGHTING_MATERIAL_REFINEMENT_20261012.md)'
common=('DevMap/HeinMach 조정본493(map2/기존 masked MI489/새 parent2), PP 각1·toon/custom blendable0, '
    '기존 actor pose10032 변화0와 scalar/vector/texture/base overrides의 예상 밖 변경0을 확인했다. '
    'small-tree3 raw RGB emission off만 TEMP 예외다. source stock foliage transmission 시험은 white leaf로 철회했고 '
    '최종 기존 DefaultLit/기존 two-sided/clip을 유지한다. DevAfter02/HeinAfter04 실제 D3D12 game viewport 검수·Exit0와 '
    'PreparedSaved02/PreparedDelivery가 준비본 정본이다. Source/Config/DLL 전달0, 원작 전용 shader/pixel·Shipping 검증은 별도다. '
    'Main editor PID16504/DevMap의 dirty0을 read-only 확인했지만 Win32 error32 map lock으로 Main content writes0에서 중단했다. '
    '사용자에게 저장 후 editor 종료를 요청했고 editor 종료/reload/save 제어0이다. 잠금 해제 뒤 install→새 MainSaved01→'
    'MainDevAfter01/MainHeinAfter01→selected493 SHA/화면→FinalVerification/완료기록 순으로 재개한다. '
    'Main이 baseline과 달라졌으면 최신 사용자 변경을 보존해 field만 이관한다. 전체 추출/재임포트/Source·과거 DLL 전달을 반복하지 않는다. '
    'exact resume는 Metadata/SceneLook_20261012/ResumeState.json, 비교는 DevMap_BeforeAfter.jpg/HeinMach_BeforeAfter.jpg다.')
for name in ['ART_PROJECT_STATE.md','ART_KNOWLEDGE_INDEX.md','ART_WORK_CONTINUITY.md']:
    p=ROOT/'Docs/Art'/name
    if marker not in p.read_text(encoding='utf-8-sig'):
        with p.open('a',encoding='utf-8') as f:f.write('\n\n## '+stamp+' — DevMap·HeinMach 룩 준비본 / Main 잠금 대기\n\n'+locator+'를 첫 조회한다. '+common+'\n\n<!-- '+marker+' -->\n')
p=ROOT/'0_DOCUMENT_ROUTER.md'
if marker not in p.read_text(encoding='utf-8-sig'):
    with p.open('a',encoding='utf-8') as f:f.write('\n\n## '+stamp+' — DevMap·HeinMach 조명/재질 조정본 준비\n\nArt: Docs/Art/SCENE_LIGHTING_MATERIAL_REFINEMENT_20261012.md → Metadata/SceneLook_20261012/{PreparedVerification,ResumeState,PreparedDelivery,DeliveryBlocked}.json. 준비본493 검증 완료, Main Win32error32/DevMap.umap lock으로 쓰기0. 잠금 해제 후 선택 전달과 새 Main saved/RHI 검증만 재개한다. 전체 author/추출/과거 Source·DLL 전달은 반복하지 않는다.\n\n<!-- '+marker+' -->\n')
print('CHECKPOINT',stamp,flush=True)
