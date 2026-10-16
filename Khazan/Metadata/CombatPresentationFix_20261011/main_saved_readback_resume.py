"""Fresh Main readback, no game package writes."""
from pathlib import Path
import os,json,hashlib
import unreal
ROOT=Path(unreal.Paths.project_dir()).resolve()
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=Path(os.environ['KZ_CLEAN_OUTPUT'])
os.environ['KZ_PRESENTATION_READ_ONLY']='1'
os.environ['KZ_UI_READ_ONLY']='1'
os.environ['KZ_COMBAT_UI_OUTPUT']=str(OUT)
for script in ['Metadata/CombatPresentationFix_20261011/author_snow40_resume.py','Scripts/Engineering/configure_combat_ui_20261011.py']:
 p=ROOT/script;exec(compile(p.read_text(encoding='utf-8'),str(p),'exec'),dict(__name__='__main__',__file__=str(p)))
authored=json.loads((ROOT/'Metadata/CombatPresentationFix_20261011/VFXAuthorResume03/VFXAuthored.json').read_text())
rows=[]
for path in authored['changed_assets']:
 obj=unreal.load_object(None,path);assert obj,path
 task=unreal.AssetExportTask();task.object=obj;task.exporter=unreal.ObjectExporterT3D();task.filename=str(OUT/(obj.get_name()+'.t3d'));task.automated=True;task.prompt=False
 assert unreal.Exporter.run_asset_export_task(task)
 raw=Path(task.filename).read_bytes();text=raw.decode('utf-16') if raw.startswith(b'\xff\xfe') else raw.decode('utf-8-sig')
 if '/Blood/' in path:assert 'EmitterName="KZ_PhysicalBloodSpray"' in text,path
 rows.append({'asset':path,'class':obj.get_class().get_name(),'export_sha256':hashlib.sha256(raw).hexdigest()})
report={'status':'passed','asset_writes':0,'VFX_assets':rows,'source_events_rebound':authored['rebound_DAS_events'],'UI_readback':'SavedReadback.json','snow_readback':'Snow40.json'}
(OUT/'CombinedSavedReadback.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
unreal.log('MAIN_COMBAT_UI_PRESENTATION_SAVED_READBACK_PASSED')
