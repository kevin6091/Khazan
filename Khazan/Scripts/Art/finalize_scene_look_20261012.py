"""Record verified Main delivery and append completion to existing Art histories."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib, json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Metadata/SceneLook_20261012'
stamp = datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
def read(name): return json.loads((OUT/name).read_text(encoding='utf-8'))
def write(name,value): (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

plan = read('PreparedDelivery.json')
assert len(plan['files']) == 493
for row in plan['files']: assert sha(ROOT/row['file']) == row['prepared'], row['file']
saved = read('MainSaved01/SavedAudit.json')
assert saved['success'] and not saved['mismatches'] and saved['asset_saves'] == 0
assert read('MainSaved01/Exit.json')['exit'] == 0
shader_errors = []
views = []
for run in ['MainDevAfter01','MainHeinAfter01']:
    capture = read(run+'/Capture.json')
    assert capture['success'] and capture['asset_saves'] == 0
    assert read(run+'/Exit.json')['exit'] == 0
    views += [{'run':run,**v} for v in capture['views']]
    log = (OUT/run/'Editor.log').read_text(encoding='utf-8',errors='replace')
    shader_errors += [line for line in log.splitlines() if 'Failed to compile Material' in line or 'Default Material will be used' in line]
assert not shader_errors
comparison = read('VisualComparison.json')
module = json.loads((ROOT/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))['Modules']['Khazan']
result = {'complete':True,'status':'MainDeliveredAndFreshSavedRHIValidated','utc':stamp,
    'packages':493,'sha256_matches':493,'saved_audit':'MainSaved01/SavedAudit.json','actual_game_views':views,
    'comparisons':comparison,'visual_reviewed':['MainDevAfter01/PlayerFront.png','MainHeinAfter01/Entry.png','MainHeinAfter01/ReferenceStart.png'],
    'shader_compile_errors':shader_errors,'source_changes':0,'config_changes':0,'native_delivery':0,
    'main_manifest_module':module,'main_manifest_module_sha256':sha(ROOT/'Binaries/Win64'/module),
    'protected_actor_poses':10032,'pose_error':0,'original_shader_pixel_parity_verified':False,'shipping_performance_verified':False}
write('FinalVerification.json',result)
write('ResumeState.json',{'complete':True,'status':result['status'],'utc':stamp,'remaining':[],
    'last_verified':'MainSaved01 and MainDevAfter01/MainHeinAfter01; Exit0, selected493 SHA, reviewed game images',
    'final_receipt':'FinalVerification.json','do_not_repeat':'No stage, whole author, reimport, Source/Config/DLL delivery.'})
delivery=read('Delivery.json');delivery['status']=result['status'];delivery['verified_utc']=stamp;write('Delivery.json',delivery)
marker='SceneLook_20261012_MainCompleted'
text=('앞선 Main 잠금 대기 기록을 이 완료 기록으로 대체한다. 사용자 Main 에디터가 종료된 뒤 선택493개 전부의 baseline SHA와 교체 접근을 먼저 확인했고 '
    'Main에 map2/기존 masked MI489/부모2만 전달했다. 사용자 프로세스 강제 종료·저장·reload0, Source/Config/DLL 전달0이다. '
    'MainSaved01 새 프로세스의 saved audit Success/Exit0, 기존 actor pose10032 변화0, 보호 material parameter/base overrides 예상 밖 차이0을 확인했다. '
    'MainDevAfter01(DevMap3뷰)/MainHeinAfter01(HeinMach4뷰)는 실제 D3D12 game viewport를 촬영하고 Exit0/성공/재질 compile failure0이다. '
    '역광 캐릭터·눈/바위/횃불·음영 화면을 직접 검수했으며 실제 Shot1092×573과 요청 창1600×900은 구분한다. '
    '현재493개 파일 SHA가 준비본과 전부 같다. 비교 이미지는 새 Main 촬영으로 갱신했다. '
    'Three small-tree raw emission off는 명시한 TEMP 보정이며 실패한 stock foliage transmission trial은 철회된 상태다. '
    '원작 전용 shader/pixel 전체 일치와 Shipping 성능·전 경로 플레이 검증은 별도이며 완료로 확대하지 않는다. '
    '재개 정본은 Metadata/SceneLook_20261012/FinalVerification.json과 complete ResumeState.json이다. 이미 완료된 전체 저작/추출/재임포트를 반복하지 않는다.')
for name in ['SCENE_LIGHTING_MATERIAL_REFINEMENT_20261012.md','ART_PROJECT_STATE.md','ART_KNOWLEDGE_INDEX.md','ART_WORK_CONTINUITY.md']:
    p=ROOT/'Docs/Art'/name
    if marker not in p.read_text(encoding='utf-8-sig'):
        with p.open('a',encoding='utf-8') as f:f.write('\n\n## '+stamp+' — DevMap·HeinMach Main 반영 및 새 화면 검증 완료\n\n'+text+'\n\n<!-- '+marker+' -->\n')
p=ROOT/'0_DOCUMENT_ROUTER.md'
if marker not in p.read_text(encoding='utf-8-sig'):
    with p.open('a',encoding='utf-8') as f:f.write('\n\n## '+stamp+' — SceneLook Main 완료\n\nArt: Docs/Art/SCENE_LIGHTING_MATERIAL_REFINEMENT_20261012.md → Metadata/SceneLook_20261012/FinalVerification.json. 앞선 잠금 대기를 대체한다. 선택493개 Main SHA 및 새 saved/RHI 화면 검증 완료. Source/Config/DLL 전달0. 전체 author·추출·재임포트를 반복하지 않는다.\n\n<!-- '+marker+' -->\n')
print('SCENE_MAIN_COMPLETED',493,flush=True)
