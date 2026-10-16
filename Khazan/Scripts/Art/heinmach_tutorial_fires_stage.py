"""Task-specific isolated background workspace; only Maps/new fire assets mutable."""
import sys
from pathlib import Path
import json
import shutil
import subprocess
import os
import time
import heinmach_reference_stage as stage

stage.STAGE = stage.ROOT / 'Saved/ArtStaging/HeinMachTutorialFires_20261006'
stage.OUT = stage.ROOT / 'Saved/ImportReports/HeinMachTutorialFires_20261006'
stage.MUTABLE = ('Maps', '_Art/Player/Environment/HeinMach/Reconstructed/TutorialFires',
                 '_Art/Player/Environment/HeinMach/Metadata/TutorialFires_20261006')

def run(kind):
    main = '--main' in sys.argv
    assert not main or kind in ('audit','capture'), 'Main project read-only verification'
    project=stage.ROOT if main else stage.STAGE
    if not main:
        shutil.copytree(stage.ROOT/'Scripts/Art',project/'Scripts/Art',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
        relative=Path('Content/_Art/Player/Environment/HeinMach/Metadata/TutorialFires_20261006')
        for name in ('AssetManifest.json','Components.json','DynamicFixtures.json','DestructibleFireSpawners.json','FireActorCandidates.json'):
            if (stage.ROOT/relative/name).is_file():shutil.copy2(stage.ROOT/relative/name,project/relative/name)
    render=kind in ('compile','capture','playback_probe','performance')
    game=kind in ('capture','playback_probe','performance')
    script=project/'Scripts/Art'/('heinmach_tutorial_fires_'+kind+'.py')
    assert script.is_file(),script
    log=stage.OUT/(('main_' if main else '')+kind+'.log')
    args=[str(stage.ENGINE/('UnrealEditor.exe' if render else 'UnrealEditor-Cmd.exe')),str(project/'Khazan.uproject'),
          '-unattended','-nosound','-nosplash','-NoSourceControl','-DisablePlugins=RiderLink,ModelContextProtocol,XGEController',
          '-EnablePlugins=GameFeatures,CascadeToNiagaraConverter','-abslog='+str(log),'-ini:Editor:[TextureImporter]:LoadHdrAsLongLatCubemap=0']
    if render:
        args += ['/Game/Maps/L_HeinMach_Environment','-RenderOffscreen','-windowed','-ResX=1280','-ResY=720','-ExecCmds=py '+str(script)]
        if game: args += ['-game','-EnablePlugins=GameFeatures,PythonScriptPlugin,CascadeToNiagaraConverter']
    else: args += ['-nullrhi','-run=pythonscript','-script='+str(script)]
    startup=subprocess.STARTUPINFO();startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW;startup.wShowWindow=subprocess.SW_HIDE
    env=dict(os.environ);env['UE_SKIP_UBT_SDK_SETUP']='1'
    start=time.monotonic()
    with log.with_suffix('.stdout.txt').open('w',encoding='utf-8') as out:
        p=subprocess.run(args,stdout=out,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,startupinfo=startup,env=env)
    content=log.read_text(encoding='utf-8',errors='replace')
    passed=p.returncode==0 and 'KZ_HM_FIRES_'+kind.upper()+'_PASSED' in content
    if render and 'Default Material will be used in game' in content: passed=False
    report={'kind':kind,'project':str(project),'exit_code':p.returncode,'passed':passed,'elapsed_seconds':time.monotonic()-start,'hidden':True,'log':str(log)}
    (stage.OUT/(('main_' if main else '')+kind+'_Process.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)
    raise SystemExit(0 if passed else 1)

if __name__ == '__main__':
    stage.setup() if sys.argv[1]=='setup' else run(sys.argv[1])
