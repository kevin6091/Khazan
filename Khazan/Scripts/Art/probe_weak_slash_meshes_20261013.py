from pathlib import Path
import os,json,unreal as u
out=Path(os.environ['KZ_MONSTER_PHYSICS_OUT']);rows=[]
for i in [1,2]:
 mesh=u.load_asset('/Game/VFX/01_ARPGEssentials/Meshes/SM_VFX_SlashRing_0'+str(i));b=mesh.get_bounding_box();rows.append({'mesh':mesh.get_path_name(),'min':[b.min.x,b.min.y,b.min.z],'max':[b.max.x,b.max.y,b.max.z]})
 for kind in ['StaticMeshExporterOBJ']:
  if hasattr(u,kind):
   t=u.AssetExportTask();t.object=mesh;t.filename=str(out/('Mesh'+str(i)+'.obj'));t.exporter=getattr(u,kind)();t.automated=True;t.prompt=False;u.Exporter.run_asset_export_task(t)
 mat=u.load_asset('/Game/VFX/01_ARPGEssentials/Materials/M_VFX_ARPG_Slash_0'+str(i));t=u.AssetExportTask();t.object=mat;t.filename=str(out/('Material'+str(i)+'.t3d'));t.exporter=u.ObjectExporterT3D();t.automated=True;t.prompt=False;u.Exporter.run_asset_export_task(t)
(out/'MeshBounds.json').write_text(json.dumps(rows,indent=2));print('MESH_PROBE_PASSED')