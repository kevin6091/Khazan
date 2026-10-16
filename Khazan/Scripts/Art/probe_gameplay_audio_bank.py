from pathlib import Path
import json
import subprocess

root=Path(__file__).resolve().parents[2]
task=root/'Saved/Extracted/GameplayAudio_20261011'
out=root/'Saved/ImportReports/GameplayAudio_20261011/BankProbe01'
out.mkdir(exist_ok=False)
sample=task/'RawSample01/BBQ/Content/WwiseAudio'
init=sample/'Init.bnk'
assert init.is_file(),init
bank=sample/'Event/English(US)/Play_PLYR_VO_Dmg.bnk'
assert bank.is_file(),bank
python=Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe')
parser=root/'Saved/ImportReports/GameplayAudio_20261011/Tools/wwiser.pyz'
vgm=Path('C:/Users/user/Downloads/63a7cbccd9fbaae9db45240069a49bd6a3a00b73/Output/.data/vgmstream-cli.exe')
args=[str(python),str(parser),'-d','xml','-dn',str(out/'Banks'),'-g','-go',str(out/'txtp'),
      '-gw',str(sample/'Media/English(US)'),'-gv','1.0','-grf',str(init),str(bank)]
with (out/'wwiser.log').open('w',encoding='utf-8') as f:
    process=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
    assert process.returncode==0,process.returncode
txtps=sorted((out/'txtp').glob('*.txtp'))
print('Generated event variants',len(txtps))
if txtps:
    selected=txtps[0]
    with (out/'Decoder.log').open('w',encoding='utf-8') as f:
        process=subprocess.run([str(vgm),'-o',str(out/'EventSample.wav'),str(selected)],stdout=f,stderr=subprocess.STDOUT)
        assert process.returncode==0,process.returncode
    print('Rendered full original event sample',selected.name)
(out/'Probe.json').write_text(json.dumps({'args':args,'txtps':[str(p) for p in txtps]},indent=2),encoding='utf-8')
