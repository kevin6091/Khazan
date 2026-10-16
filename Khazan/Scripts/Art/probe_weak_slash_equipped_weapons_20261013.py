from pathlib import Path
import os,json,unreal as u
out=Path(os.environ['KZ_MONSTER_PHYSICS_OUT']);rows=[]
for side in ['L','R']:
 a=u.load_asset('/Game/_Art/Player/Item/Imperial/DualAxeSword_Imperial_'+side);assert a
 task=u.AssetExportTask();task.object=a;task.filename=str(out/('Weapon_'+side+'.fbx'));task.exporter=u.SkeletalMeshExporterFBX();task.automated=True;task.prompt=False;task.options=u.FbxExportOption();task.options.set_editor_property('bASCII',True);task.options.set_editor_property('LevelOfDetail',False);task.options.set_editor_property('BakeMaterialInputs',u.FbxMaterialBakeMode.DISABLED);assert u.Exporter.run_asset_export_task(task)
 rows.append({'mesh':a.get_path_name(),'file':task.filename})
(out/'Probe.json').write_text(json.dumps(rows,indent=2));print('EQUIPPED_WEAPONS_GEOMETRY_EXPORTED')