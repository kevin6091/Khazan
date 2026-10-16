import datetime, hashlib, json, pathlib, shutil
MAIN = pathlib.Path(__file__).resolve().parents[2]
OUT = MAIN/'Metadata/MonsterStamina_20261008'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
manifest=json.loads((OUT/'PreparedDeliveryManifest.json').read_text(encoding='utf-8'))
expected={r['relative']:r['after'] for r in manifest['rows']}
baseline=json.loads((OUT/'MainSourceBaselineAfterCollision.json').read_text(encoding='utf-8'))
for relative,value in {**baseline,**expected}.items(): assert sha(MAIN/relative)==value,relative
module_file=MAIN/'Binaries/Win64/UnrealEditor.modules'
module=json.loads(module_file.read_text(encoding='utf-8-sig'))['Modules']['Khazan']
assert module=='UnrealEditor-Khazan.dll'
log=pathlib.Path('C:/Users/user/AppData/Local/UnrealBuildTool/Log.txt')
assert 'Result: Succeeded' in log.read_text(encoding='utf-8',errors='replace')
saved_log=OUT/'ConcurrentMainBuild.log'; assert not saved_log.exists(); shutil.copy2(log,saved_log)
result=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),not_our_build=True,user_editor_pid=19576,
    user_editor_controlled=False,all_delivered_rows_match=True,all_source_config_match=True,
    module=module,module_sha256=sha(MAIN/'Binaries/Win64'/module),modules_sha256=sha(module_file),
    prior_canonical_sha256=manifest['main_canonical_dll_before'],build_log=str(saved_log),fresh_readback_pending=True)
(OUT/'ConcurrentMainRebuild.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
