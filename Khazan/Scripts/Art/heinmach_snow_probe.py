"""Read-only topology/material evidence in the isolated snow workspace."""
from pathlib import Path
import json
import unreal

ROOT=Path(unreal.Paths.project_dir()).resolve()
assert ROOT == Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
OUT=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Saved/ImportReports/HeinMachSnow_20261006')
LIB=unreal.MaterialEditingLibrary
world=unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
rows=[]; materials={}
actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
for actor in actors:
    for comp in actor.get_components_by_class(unreal.StaticMeshComponent):
        mats=[comp.get_material(i) for i in range(comp.get_num_materials())]
        if not any(m and ('SourceWeighted' in m.get_name() or 'Snow' in m.get_name()) for m in mats):
            continue
        mesh=comp.static_mesh
        row={'actor':actor.get_path_name(),'label':actor.get_actor_label(),
          'mesh':mesh.get_path_name() if mesh else None,'materials':[m.get_path_name() if m else None for m in mats],
          'transform':str(comp.get_world_transform()),'collision_profile':str(comp.get_collision_profile_name())}
        if mesh:
            row['nanite']=str(mesh.get_editor_property('nanite_settings'))
            row['vertices']=unreal.EditorStaticMeshLibrary.get_number_verts(mesh,0)
        rows.append(row)
        for mat in mats:
            if not mat or mat.get_path_name() in materials: continue
            base=mat
            while isinstance(base,unreal.MaterialInstanceConstant):base=base.get_editor_property('parent')
            nodes=LIB.get_material_expressions(base)
            materials[mat.get_path_name()]={'base':base.get_path_name(),'nodes':[{
              'name':n.get_name(),'class':n.get_class().get_name(),
              'code':n.get_editor_property('code') if isinstance(n,unreal.MaterialExpressionCustom) else ''} for n in nodes]}
            task=unreal.AssetExportTask(); task.object=base;task.exporter=unreal.ObjectExporterT3D()
            task.filename=str(OUT/(base.get_name()+'.t3d'));task.automated=True;task.prompt=False
            unreal.Exporter.run_asset_export_task(task)
report={'actors':len(actors),'terrain':rows,'materials':materials,
  'material_properties':[str(x) for x in dir(unreal.MaterialProperty) if 'DISP' in x or 'WORLD' in x],
  'mesh_subsystem_api':[x for x in dir(unreal.StaticMeshEditorSubsystem) if 'nanite' in x or 'lod' in x]}
(OUT/'Topology.json').write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
print('SNOW_TOPOLOGY_COMPLETE',len(rows))
