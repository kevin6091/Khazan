from pathlib import Path
import json,os,re,traceback,unreal
out=Path(os.environ['KZ_CLEAN_OUTPUT']);main=Path(os.environ['KZ_CLEAN_MAIN'])
report={'success':False,'saved':0,'particles':[],'materials':[]}
def export(obj):
 t=unreal.AssetExportTask();t.object=obj;t.filename=str(out/(obj.get_name()+'.t3d'));t.exporter=unreal.ObjectExporterT3D();t.automated=True;t.prompt=False
 assert unreal.Exporter.run_asset_export_task(t)
 b=Path(t.filename).read_bytes();return b.decode('utf-16') if b.startswith(b'\xff\xfe') else b.decode('utf-8-sig')
try:
 plan=json.loads((main/'Saved/ImportReports/PlayerAttackVFX_20261008/CombinedPreparedPlaybackPlan.json').read_text(encoding='utf-8-sig'))
 paths=[p for p in plan['native_particle_assets'] if '/DualAxeSword/' in p]
 paths+=['/Game/_Art/Effects/Combat/Blood/PP_Dmg_Blood_Trail','/Game/_Art/Effects/Combat/Blood/PP_Dmg_Blood_Trail_Sub','/Game/_Art/Effects/Combat/Blood/FP_Dmg_Blood_Base','/Game/_Art/Effects/Combat/Blood/FP_BloodSplit_01','/Game/_Art/Effects/Combat/Blood/FP_BloodSplit_02','/Game/_Art/Effects/Combat/Shared/FP_PlaneSlash_Base_001']
 for path in paths:
  obj=unreal.load_asset(path)
  if not obj:continue
  text=export(obj);objects=[]
  for cls,name,ref in re.findall(r'Begin Object Class=/Script/Engine\.(\w+) Name="([^"]+)" ExportPath="[^\x27]*\x27([^\x27]+)\x27"',text):
   if any(word in cls for word in ['Spawn','Event','Rotation','Location','Size','Color','TypeData','Required','LODLevel']):
    mod=unreal.find_object(None,ref);assert mod
    fields={}
    for n in ['BurstList','UnitScalar','Rate','SpawnCount','Events','StartRotation','StartSize','StartLocation','ColorOverLife','StartColor','Material','TypeDataModule','SpawnModule','Modules','bUseLocalSpace','bEmitterDelayUseRange','EmitterDelay','EmitterDuration','ParticleLODLevel']:
     try:
      v=mod.get_editor_property(n);fields[n]=v.export_text() if hasattr(v,'export_text') else str(v)
     except Exception:pass
    objects.append({'name':name,'class':cls,'fields':fields})
  report['particles'].append({'asset':path,'modules':objects})
 for path in ['/Game/_Art/Effects/Shared/Materials/BBQ_Material/Decal/FM_MeshDecal','/Game/_Art/Effects/Shared/Materials/BBQ_Material/PhysicsDecal/PD_Blood_Curve_Normal']:
  obj=unreal.load_asset(path)
  while obj:
   export(obj);row={'asset':obj.get_path_name(),'class':obj.get_class().get_name()}
   if isinstance(obj,unreal.Material):
    row['blend']=str(obj.get_editor_property('blend_mode'));row['custom']=[]
    for node in unreal.MaterialEditingLibrary.get_material_expressions(obj):
     if isinstance(node,unreal.MaterialExpressionCustom):row['custom'].append(node.get_editor_property('code'))
   report['materials'].append(row)
   obj=obj.get_editor_property('parent') if isinstance(obj,unreal.MaterialInstance) else None
 report['success']=True
except Exception:
 report['error']=traceback.format_exc();unreal.log_error(report['error'])
(out/'Effects.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
assert report['success'],report.get('error')
