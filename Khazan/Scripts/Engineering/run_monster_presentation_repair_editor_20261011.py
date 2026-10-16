"""Run and journal a new task-owned hidden editor, with an exact project identity."""
from pathlib import Path
from datetime import datetime, timezone
import json, os, subprocess, sys, time, hashlib
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
WORK=Path('C:/Users/user/Desktop/GitProject/Khazan_GiantFallWork_20261011/Khazan')
name,entry,mode=sys.argv[1:4]
project=MAIN if mode.startswith('main_') else WORK
mode=mode.removeprefix('main_')
out=MAIN/'Metadata/MonsterPresentationRepair_20261011'/name
out.mkdir(exist_ok=False)
if mode!='commandlet':
    plan=json.loads((MAIN/'Saved/ImportReports/MonsterVFX_20261008/PreparedPlaybackPlan.json').read_text(encoding='utf-8-sig'))
    pairs=sorted({(e['asset'],e['family']) for e in plan['events'] if e['category']=='Attack'})
    assert len(pairs)==198
    (out/'AttackCases.tsv').write_text('\n'.join(a+'\t'+f for a,f in pairs)+'\n',encoding='utf-8')
commandlet=mode=='commandlet'
cmd=['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/'+('UnrealEditor-Cmd.exe' if commandlet else 'UnrealEditor.exe'),str(project/'Khazan.uproject'),'-unattended','-nosplash','-nosound','-NoSourceControl','-NoLiveCoding','-NoAutoSave','-EnablePlugins=GameFeatures','-DisablePlugins=RiderLink,ModelContextProtocol,XGEController','-abslog='+str(out/'Editor.log')]
if commandlet:cmd+=['-NullRHI','-run=pythonscript','-script='+str((MAIN/entry).resolve())]
else:
    cmd+=['/Engine/Maps/Entry','-RenderOffscreen','-Windowed','-ResX=1600','-ResY=900','-ForceRes','-ExecCmds=py '+str((MAIN/entry).resolve())]
    if mode=='asset_editor':cmd+=['-NullRHI']
env=dict(os.environ,KZ_MONSTER_REPAIR_OUT=str(out),KZ_MONSTER_REPAIR_MODE=mode,KZ_MONSTER_REPAIR_TEST=os.environ.get('KZ_MONSTER_REPAIR_TEST',''),PYTHONUTF8='1',UE_SKIP_UBT_SDK_SETUP='1')
startup=subprocess.STARTUPINFO();startup.dwFlags|=subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=0
start=time.monotonic();p=subprocess.Popen(cmd,env=env,startupinfo=startup,creationflags=subprocess.CREATE_NO_WINDOW)
proof_source=['Character/KZMonster.h','Character/KZMonster.cpp','UI/KZCombatHUDWidget.h','UI/KZCombatHUDWidget.cpp','Ability/Combo/KZComboActionAbility.cpp','Ability/PlayerAbility/KZBrutalAttackAbility.cpp','Tests/KZCombatUIPIEEditor.cpp','Tests/KZPlayerAttackCollisionPIETest.cpp','Tests/KZMonsterPresentationRepairPIETest.cpp','Khazan.Build.cs']
source_hashes={'Source/Khazan/'+f:hashlib.sha256((project/'Source/Khazan'/f).read_bytes()).hexdigest() for f in proof_source}
(out/'Launch.json').write_text(json.dumps({'pid':p.pid,'command':cmd,'utc':datetime.now(timezone.utc).isoformat(),'source_sha256':source_hashes},indent=2),encoding='utf-8')
print('OWNED_REPAIR_EDITOR',p.pid,flush=True)
try:result=p.wait(timeout=1800)
except subprocess.TimeoutExpired:p.terminate();result=p.wait(timeout=30)
(out/'Exit.json').write_text(json.dumps({'pid':p.pid,'exit':result,'seconds':time.monotonic()-start},indent=2),encoding='utf-8')
print('OWNED_REPAIR_EXIT',result,flush=True);sys.exit(result)
