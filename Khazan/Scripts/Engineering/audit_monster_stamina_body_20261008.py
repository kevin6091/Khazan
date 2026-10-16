"""Read-only selected mesh/CDO audit in the explicitly isolated work editor."""
import datetime
import json
import os
from pathlib import Path
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
expected = Path('C:/Users/user/Desktop/GitProject/Khazan_MonsterWork_20261006/Khazan').resolve()
if root != expected:
    raise RuntimeError('Wrong editor project')
report_path = Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan/Metadata/MonsterStamina_20261008/BodyAudit.json')
subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
library = unreal.SubobjectDataBlueprintFunctionLibrary
paths = [
    ('ApesStoneHandElite', '/Game/_Art/Enemies/Shared/Elites/ApesStoneHandElite/Blueprints/BP_EN_ApesStoneHandElite_Early'),
    ('Yetuga', '/Game/_Art/Enemies/HeinMach/Bosses/Yetuga/Blueprints/BP_EN_Boss_Yetuga'),
]
rows = []
for family, path in paths:
    bp = unreal.load_asset(path)
    if not bp:
        raise RuntimeError('Missing visual BP ' + path)
    components = []
    seen = set()
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
        data = library.get_data(handle)
        component = library.get_object_for_blueprint(data, bp)
        if not isinstance(component, unreal.SkeletalMeshComponent):
            continue
        if component.get_path_name() in seen:
            continue
        seen.add(component.get_path_name())
        mesh = component.get_editor_property('skeletal_mesh')
        components.append(dict(
            name=component.get_name(), mesh=mesh.get_path_name() if mesh else None,
            relative_location=str(component.get_editor_property('relative_location')),
            relative_rotation=str(component.get_editor_property('relative_rotation')),
            relative_scale=str(component.get_editor_property('relative_scale3d')),
            materials=[m.get_path_name() if m else None for m in component.get_materials()],
            skeleton=mesh.get_editor_property('skeleton').get_path_name() if mesh else None,
            mesh_bounds=str(mesh.get_bounds()) if mesh else None,
        ))
    if len(components) != 1:
        raise RuntimeError(f'Expected selected one-body visual assembly: {family}: {components}')
    rows.append(dict(family=family, visual_bp=path, components=components))
report = dict(success=True, pid=os.getpid(), project=str(root),
              utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), rows=rows,
              write_assets=False, pie=False)
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('MONSTER_STAMINA_BODY_AUDIT', json.dumps(report, ensure_ascii=False))
for row in rows:
    skeleton = unreal.load_asset(row['components'][0]['skeleton'])
    try:
        print('STAMINA_SKELETON_SLOTS', skeleton.get_path_name(), skeleton.get_editor_property('slot_groups'))
    except Exception as error:
        print('STAMINA_SKELETON_SLOT_API', str(error))
