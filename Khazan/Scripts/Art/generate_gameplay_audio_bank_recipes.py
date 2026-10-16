"""Decode bank hierarchy recipes without normalization or added fade/tail cuts."""
from pathlib import Path
import json
import subprocess
import sys
from prepare_gameplay_audio_scope import ROOT, OUT, EXTRACT, read

folder = OUT/(sys.argv[1] if len(sys.argv)>1 else 'BankRecipes01')
folder.mkdir(exist_ok=False)
source = EXTRACT/(sys.argv[2] if len(sys.argv)>2 else 'Raw01')/'BBQ/Content/WwiseAudio'
python = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe')
args = [str(python), str(OUT/'Tools/wwiser.pyz'), '-r', '-d', 'xml', '-dn', str(folder/'Banks'),
        '-nl', str(OUT/'Tools/wwnames.txt'), '-g', '-go', str(folder/'txtp'), '-gw', str(source/'Media'),
        '-gv', '100%', '-gl', '3721600213', '-gra', '-grf', '-gwd', '-gd', str(source/'**/*.bnk')]
with (folder/'wwiser.log').open('w',encoding='utf-8') as stream:
    code = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT).returncode
files = list((folder/'txtp').glob('*.txtp'))
(folder/'Generation.json').write_text(json.dumps({'args':args,'exit_code':code,'txtp_count':len(files)},indent=2),encoding='utf-8')
print('BANK RECIPES',code,len(files),flush=True)
assert code==0
