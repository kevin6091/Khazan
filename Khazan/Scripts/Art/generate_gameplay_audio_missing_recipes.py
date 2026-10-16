from pathlib import Path
import json
import subprocess
from prepare_gameplay_audio_scope import OUT,EXTRACT

folder=OUT/'BankRecipes09';folder.mkdir(exist_ok=False)
source=EXTRACT/'Raw03/BBQ/Content/WwiseAudio'
args=['C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe',
      str(OUT/'Tools/wwiser.pyz'),'-r','-nl',str(OUT/'Tools/wwnames.txt'),'-g','-go',str(folder/'txtp'),
      '-gw',str(source/'Media'),'-gv','100%','-gl','3721600213','-gra','-grf','-gwd','-gd',
      '-gp','[kz_apc_switch=kz]','[vo_kz_switch=kz]',
      '-gf','2492340343','4132611353','3667955469','4163716935',
      '--',str(source/'**/*.bnk')]
with (folder/'wwiser.log').open('w',encoding='utf-8') as log:
    code=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT).returncode
files=list((folder/'txtp').glob('*.txtp'))
(folder/'Generation.json').write_text(json.dumps({'args':args,'exit_code':code,'count':len(files)},indent=2),encoding='utf-8')
print('MISSING RECIPES',code,len(files),[p.name for p in files[:10]],flush=True)
