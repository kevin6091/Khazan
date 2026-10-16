"""Read only: the actual authored GateCube, boss and candidate portal assets."""
from pathlib import Path
import json, os, unreal as u

out = Path(os.environ['KZ_PORTAL_OUT'])
out.mkdir(parents=True, exist_ok=True)
world = u.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
assert world
actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
rows = []
for actor in actors:
    label = actor.get_actor_label()
    if not (any(s in label.lower() for s in ['gatecube', 'yetuga', 'playerstart', 'boss_start'])
            or isinstance(actor, u.TargetPoint) or 'Monster' in actor.get_class().get_name()):
        continue
    center, extent = actor.get_actor_bounds(False)
    row = dict(label=label, path=actor.get_path_name(), cls=actor.get_class().get_path_name(),
               transform=actor.get_actor_transform().export_text(),
               location=list(actor.get_actor_location().to_tuple()),
               bounds_center=list(center.to_tuple()), bounds_extent=list(extent.to_tuple()),
               hidden=actor.get_editor_property('hidden'), components=[])
    for c in actor.get_components_by_class(u.PrimitiveComponent):
        cr = dict(name=c.get_name(), cls=c.get_class().get_name(),
                  collision=str(c.get_collision_enabled()), profile=str(c.get_collision_profile_name()),
                  transform=c.get_world_transform().export_text())
        if isinstance(c, u.StaticMeshComponent):
            mesh = c.get_editor_property('static_mesh')
            cr['mesh'] = mesh.get_path_name() if mesh else None
        row['components'].append(cr)
    rows.append(row)
for name in ['N_Portal1Boss', 'N_Portal3Boss', 'N_Portal4Boss', 'N_Portal5Boss']:
    asset = u.load_asset('/Game/VFX/06_NiagaraBundle/' + name)
    if not asset:
        continue
    task = u.AssetExportTask()
    task.object = asset
    task.filename = str(out / (name + '.t3d'))
    task.exporter = u.ObjectExporterT3D()
    task.automated = True
    task.prompt = False
    u.Exporter.run_asset_export_task(task)
report = dict(map=world.get_path_name(), actor_count=len(actors), actors=rows, asset_saves=0,
              dirty_content=[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()],
              dirty_maps=[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
(out / 'Audit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('KZ_PORTAL_READ_ONLY_AUDIT_COMPLETE')
