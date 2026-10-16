import datetime, hashlib, json, pathlib
MAIN=pathlib.Path(__file__).resolve().parents[2]; OUT=MAIN/'Metadata/MonsterStamina_20261008'
read=lambda n:json.loads((OUT/n).read_text(encoding='utf-8'))
proof=read('ConcurrentMainRebuild.json'); report=read('MainSavedReload_ConcurrentBuild.json')
assert report['success'] and not report['dirty_content'] and not report['dirty_map']
assert len(report['facing_saved_readback'])==4
assert report['loaded_module']['sha256']==proof['module_sha256']
assert hashlib.sha256((MAIN/'Binaries/Win64'/proof['module']).read_bytes()).hexdigest()==proof['module_sha256']
assert json.loads((MAIN/'Binaries/Win64/UnrealEditor.modules').read_text(encoding='utf-8-sig'))['Modules']['Khazan']==proof['module']
manifest=read('PreparedDeliveryManifest.json')
for row in manifest['rows']:
    assert hashlib.sha256((MAIN/row['relative']).read_bytes()).hexdigest()==row['after'],row['relative']
result=dict(complete=True,utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    source_assets_still_match=True,current_module=report['loaded_module'],new_main_build_not_performed_by_this_task=True,
    user_editor_controlled=False,main_saved_reload_success=True,facing_saved_readback=4,
    original_delivery_proof='FinalVerification.json',current_saved_proof='MainSavedReload_ConcurrentBuild.json')
(OUT/'FinalVerification_CurrentMain.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
marker='<!-- MonsterStaminaConcurrentMainBuildVerified_20261008 -->'
body='\n\n'+marker+'\n## 2026-10-08 17:39 KST — 후속 Main 기본 DLL 빌드 보존·재검증\n\n'
body+='전달 완료 뒤 본 작업이 시작하지 않은 Main native build가 새 canonical DLL과 manifest를 만들었다. 해당 build는 Succeeded이고 선택 모듈은 현재 `UnrealEditor-Khazan.dll`, SHA `3a2b4942da22fdf94cc7cf6581da3b5fb04f63475315c675d66ef6c4782e758d`다. 이전 unique alias 전달·canonical 보존은 당시 사실이며 현재 모듈 선택을 과거 alias로 되돌리지 않았다. 전달105행과 전체 Source/Config가 검증한 현재 구현과 동일한 것을 확인했다.\n\n'
body+='별도 fresh Main commandlet에서 현재 canonical DLL을 실제 로드해 저장 Definition6+Player1/montage20/sequence49/attackBP35/body2 및 NPC4 BS·CMC/AI CDO·dirty0를 다시 확인했고 exit0으로 종료했다. 증거는 Metadata/MonsterStamina_20261008/{ConcurrentMainRebuild,FinalVerification_CurrentMain,MainSavedReload_ConcurrentBuild}.json과 ConcurrentMainBuild.log다. 이 새 DLL에서 native453/회귀5종을 다시 실행한 것은 아니며 동일한 제품 Source의 이전 Work runtime 결과와 새 Main saved readback을 구분한다. 사용자 Main19576은 읽기 inventory로만 확인했으며 제어·PIE·저장·종료하지 않았다. 이제 현재 Main 기본 DLL을 사용하고 과거 전달/authoring helper를 재실행하지 않는다.\n'
for relative in ['0_DOCUMENT_ROUTER.md','Docs/Engineering/ENGINEERING_PROJECT_STATE.md',
    'Docs/Engineering/ENGINEERING_WORK_CONTINUITY.md','Docs/Engineering/MONSTER_STAMINA_EXHAUSTION_20261008.md',
    'Docs/Engineering/MONSTER_FACING_SMOOTHING_20261008.md']:
    path=MAIN/relative; assert marker not in path.read_text(encoding='utf-8')
    with path.open('a',encoding='utf-8',newline='') as stream:stream.write(body)
print(json.dumps(result))
