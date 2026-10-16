"""Seal the user-requested live Main launch without rewriting earlier test history."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import json,hashlib
root=Path(__file__).resolve().parents[2];out=root/'Metadata/MonsterBloodReference_20261012';liveout=out/'MainEditorIntegration'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not (liveout/'Result.json').exists()
original=read(out/'FinalVerification.json')
for row in original['source']+original['assets']:assert sha(root/row['path'])==row['after_sha256'],row['path']
build=read(out/'MainEditorBuild01/Exit.json');assert build['exit']==0 and build['input_unchanged']
sources={str(p.relative_to(root)):sha(p) for p in (root/'Source/Khazan').rglob('*') if p.suffix in ['.h','.cpp','.cs']}
assert sources==read(out/'MainEditorBuild01/Input.json')['source_sha256'],'Concurrent source change requires fresh verification.'
collision=read(out/'MainEditorCollision01/Driver.json');assert collision['status']=='passed' and not collision['material_compile_failures']
assert read(out/'MainEditorCollision01/Exit.json')['exit']==0
assert read(out/'MainEditorCollision01/Launch.json')['source_sha256']==sources
log=(out/'MainEditorCollision01/Editor.log').read_text(encoding='utf-8',errors='replace')
assert log.count('PlayerAttackCollision case=')==13
live=read(liveout/'LiveEditor.json');loaded=read(liveout/'LoadedModule.json')
assert live['status']=='passed' and len(live['families'])==6 and live['pid']==loaded['pid']
assert not live['dirty_content_packages'] and not live['dirty_map_packages']
assert loaded['actual_loaded'] and sha(Path(loaded['module']))==loaded['sha256']
manifest=read(root/'Binaries/Win64/UnrealEditor.modules');assert manifest['Modules']['Khazan']==Path(loaded['module']).name
stamp=datetime.now(timezone.utc);kst=stamp.astimezone(timezone(timedelta(hours=9))).isoformat(timespec='seconds')
result={'utc':stamp.isoformat(),'status':'main_editor_applied_and_ready','complete':True,'project':str(root),'main_editor':live,'loaded_module':loaded,'source_matches_verified_integration_build':True,'source_sha256':sources,'build':build,'actual_collision_proof':collision,'actual_collision_cases':13,'original_blood_packages_and_source_preserved':True,'runtime_content_edits_this_turn':0,'header_timestamp_refresh':read(liveout/'UHTHeaderTimestampRefresh.json'),'launch':'Existing Rider Khazan Run configuration; user editor was already closed. No forced shutdown or native schema hot reload.','supersedes':'Earlier normal-editor-restart requirement only; original visual/native proof remains historical.','notes':['The IDE selected and loaded the current canonical DLL. The tested suffix module and live canonical module share the verified current Source; different DLL SHA values are recorded separately.','Editor/viewport screenshot APIs failed due to inactive Slate capture; confirmation is actual PID/project/world/module and six CDO values, not a claimed screenshot.','Main remains open, DevMap loaded, asset_saves0, dirty content/map0.']}
(liveout/'Result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
resume={'utc':stamp.isoformat(),'status':'complete_main_editor_applied','supersedes_restart_requirement':'ResumeState03.json','main_project_applied':True,'main_editor_applied':True,'main_editor_pid':live['pid'],'module':loaded['module'],'sha256':loaded['sha256'],'proof':'MainEditorIntegration/Result.json','remaining_required_implementation':[],'normal_editor_restart_needed':False,'next':['Use the current Main editor. Do not restore an older alias or rerun completed broad author/delivery scripts.','For a later modification, check current Source/manifest and preserve sound/parry changes.']}
(out/'ResumeState04.json').write_text(json.dumps(resume,ensure_ascii=False,indent=2),encoding='utf-8')
text=f'''

## {kst} — 사진 혈액 작업의 실제 메인 에디터 적용 완료

후속 사용자 요청으로 기존 Rider Khazan Run configuration에서 Main editor PID{live['pid']}를 열었다. 이전 사용자 PID19752는 작업 시작 때 이미 종료돼 있었고 강제 종료/기존 세션 저장/ResetLoaders/hot reload는 하지 않았다. 실제 연결된 editor의 project_dir은 Main, world는 {live['map']}, 실제 로드 DLL은 {Path(loaded['module']).name}, SHA256={loaded['sha256']}다. 몬스터6 CDO가 FP_Monster_HitBloodReference/M_Monster_HitBloodGround와 UI_Chest를 읽는 것을 해당 프로세스 안에서 확인했다. dirty content0/map0, asset save0이다.

다른 작업의 Guard/ASC·패링 Source 반영 뒤 UHT generated header가 Guard UCLASS15/GENERATED_BODY18과 달리 이전13/16으로 남아 합본 빌드가 실패한 상태였다. Source 내용 변경 없이 Guard/ASC header의 timestamp만 갱신하여 UHT를 재실행했다. MainEditorBuild01(2026101255)은 exit0/input동일이며 생성 macro도15/18로 일치했다. 이후 다른 작업의 성공한 current1290 선택을 보존했고 그 DLL에서 actual PlayerAttackCollision13을 fresh Main으로 다시 통과했다. Rider 실행은 현재 canonical DLL을 선택·로드했다. 서로 다른 DLL SHA를 같은 바이너리로 표현하지 않고 동일한 current 전체 Source hash와 각 실제 loaded module을 별도로 기록했다. 혈액 Source4/package5는 앞선 FinalVerification와 동일하다.

이 절은 이전 혈액 완료 기록의 '사용자 Main 미재시작/정상 재시작 필요'만 대체한다. 새 runtime 파일/제품 코드 편집0, 기존 사운드·패링 내용의 롤백0이다. GUI/viewport screenshot API는 inactive Slate 때문에 실패했으므로 화면을 직접 검토했다고 기록하지 않는다. 실제 PID/project/world/native loaded module/CDO로 적용 확인을 완료했고 Main editor는 열어 둔다. 정확한 증거는 Metadata/MonsterBloodReference_20261012/MainEditorIntegration/Result.json, 최신 재개 상태는 ResumeState04.json이다. 앞선 실제 시각 검증24혈액/12소멸·수치/한계는 기존 FinalVerification.json과 Art 정본 최신 절을 유지한다.
'''
for p in ['Docs/Engineering/ENGINEERING_PROJECT_STATE.md','Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md']:
    with (root/p).open('a',encoding='utf-8') as f:f.write(text)
for p in ['Docs/Art/ART_PROJECT_STATE.md','Docs/Art/ART_WORK_CONTINUITY.md']:
    with (root/p).open('a',encoding='utf-8') as f:f.write(f'\n\n## {kst} — 혈액 작업 메인 에디터 적용 완료\n\n앞선 사진 혈액 Source/package는 그대로 유지됐고 후속 사용자 요청으로 실제 Main editor PID{live["pid"]}/DevMap/현 canonical DLL/몬스터6 CDO를 확인했다. 새 Art authoring/asset save0이며 정상 재시작 필요는 해소됐다. Source·UHT timestamp 보완/합본 build·actual hit13과 정확한 적용 증거는 Engineering continuity의 같은 날짜 절, Metadata/MonsterBloodReference_20261012/MainEditorIntegration/Result.json·ResumeState04.json을 따른다.\n')
print('MAIN_EDITOR_APPLIED',live['pid'],loaded['module'])
