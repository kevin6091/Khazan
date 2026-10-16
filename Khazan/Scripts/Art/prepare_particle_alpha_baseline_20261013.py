"""Main read-only content plus one owned QA background for matched standalone A/B."""
from pathlib import Path
import shutil,subprocess,json
MAIN=Path(__file__).resolve().parents[2];ROOT=MAIN/'Metadata/ParticleAlpha_20261013'
WORK=MAIN.parent.parent/'Khazan_ParticleAlphaBaseline_20261013/Khazan'
assert not WORK.exists();WORK.mkdir(parents=True);(WORK/'Content').mkdir()
for name in ('Config','Binaries'):shutil.copytree(MAIN/name,WORK/name)
shutil.copy2(MAIN/'Khazan.uproject',WORK/'Khazan.uproject')
for name in ('Plugins','Source','Scripts'):
    r=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(WORK/name),str(MAIN/name)],capture_output=True);assert r.returncode==0
for child in (MAIN/'Content').iterdir():
    if child.is_dir():
        r=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(WORK/'Content'/child.name),str(child)],capture_output=True);assert r.returncode==0
    else:shutil.copy2(child,WORK/'Content'/child.name)
qa=WORK/'Content/__ParticleAlphaQA';assert not qa.exists();qa.mkdir()
shutil.copy2(MAIN.parent.parent/'Khazan_ParticleAlphaWork_20261013/Khazan/Content/__ParticleAlphaQA/M_AlphaDiagnosticSavedBg.uasset',qa/'M_AlphaDiagnosticSavedBg.uasset')
(ROOT/'BaselineProject.json').write_text(json.dumps({'work':str(WORK),'main_content_read_only':True,'owned_qa_assets':1},indent=2),encoding='utf-8')
print('BASELINE_PROJECT_READY',WORK)
