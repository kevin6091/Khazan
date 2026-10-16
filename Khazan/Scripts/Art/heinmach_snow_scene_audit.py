"""Final saved scene, source poses/fire preservation and supported dressing audit."""
from pathlib import Path
from collections import Counter
import datetime
import hashlib
import json
import unreal
ROOT=Path(unreal.Paths.project_dir()).resolve()
assert ROOT==Path('C:/Users/user/Desktop/GitProject/Khazan_SnowWork_20261006/Khazan')
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
MAIN=Path('C:/Users/user/Desktop/GitProject/Khazan/Khazan')
OUT=MAIN/'Saved/ImportReports/HeinMachSnow_20261006'
W=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
E=unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
before=json.loads((OUT/'Resume20261007/SceneBefore.json').read_text(encoding='utf-8'))
actors={a.get_actor_label():a for a in E.get_all_level_actors()}
def pose(a):
    p=a.get_actor_location();r=a.get_actor_rotation();s=a.get_actor_scale3d()
    return [p.x,p.y,p.z,r.pitch,r.yaw,r.roll,s.x,s.y,s.z]
errors=[]
for label,p in before['poses'].items():
    a=actors.get(label)
    if not a or max(abs(x-y) for x,y in zip(pose(a),p))>1e-6:errors.append(label)
assert not errors,errors[:10]
assert len(actors)==before['actors']+1,(len(actors),before['actors'])
parts=[c for a in actors.values() for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.component_has_tag('HeinMachSnowSurface')]
assert len(parts)==46
assert len([a for a in actors.values() if isinstance(a,unreal.KZSnowDeformation)])==1
mesh_paths=sorted(set(c.static_mesh.get_path_name() for c in parts))
assert len(mesh_paths)==46
for c in parts:
    assert c.static_mesh.get_editor_property('nanite_settings').get_editor_property('max_edge_length_factor')==2.0
    assert c.get_material(0).get_name().startswith('M_HM_Deformable_')
micro=[c for a in actors.values() for c in a.get_components_by_class(unreal.StaticMeshComponent) if c.component_has_tag('HeinMachMicroDressing')]
micro_report=json.loads((OUT/'Resume20261007/MicroDressing.json').read_text(encoding='utf-8'))
baseline_micro=json.loads((OUT/'Resume20261007/MainBaselineMicroDressing.json').read_text(encoding='utf-8'))
expected_labels={r['label'] for r in micro_report['changed']}|{r['label'] for r in baseline_micro['parts']}
assert {c.get_owner().get_actor_label() for c in micro}==expected_labels
visibility={r['label']:r['visibility'] for r in micro_report['changed']}
visibility.update({r['label']:r['visibility'] for r in baseline_micro['parts']})
for c in micro:
    assert c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_PAWN)==unreal.CollisionResponseType.ECR_IGNORE
    assert not c.get_editor_property('bCanEverAffectNavigation')
    actual=str(c.get_collision_response_to_channel(unreal.CollisionChannel.ECC_VISIBILITY))
    assert actual==visibility[c.get_owner().get_actor_label()],(c.get_owner().get_actor_label(),actual,visibility[c.get_owner().get_actor_label()])
fire=[a for a in actors.values() if 'KZHeinMachTutorialFire' in [str(t) for t in a.tags]]
assert len(fire)==258
boundary=next(a for a in actors.values() if isinstance(a,unreal.KZLevelRouteCollisionActor))
assert boundary.get_boundary_instance_count()==2281
classes=Counter(a.get_class().get_name() for a in actors.values())
assert classes['KZNavMeshBoundsBox']==242 and classes['KZNavModifierBox']==26 and classes['NavLinkProxy']==24
# Recover the original authoring binding report from retained metadata and assert its SHA-derived mesh names.
topology=json.loads((OUT/'Topology.json').read_text(encoding='utf-8'))
bindings=[]
for row in topology['terrain']:
    if not row['label'].startswith('HM_Landscape_'):continue
    comp=actors[row['label']].get_component_by_class(unreal.StaticMeshComponent)
    suffix=hashlib.sha256(row['mesh'].encode()).hexdigest()[:10]
    assert comp.static_mesh.get_name()=='SM_HM_Snow_'+suffix
    bindings.append(dict(actor=comp.get_owner().get_path_name(),old_mesh=row['mesh'],new_mesh=comp.static_mesh.get_path_name(),
        group='Landscape1' if '/Landscape1/' in row['mesh'] else 'Landscape2'))
assert len(bindings)==46
(OUT/'Authoring.json').write_text(json.dumps(dict(success=True,terrain_components=bindings,new_meshes=46,
    materials=sorted(set(c.get_material(0).get_path_name() for c in parts)),existing_actor_transforms_changed=0,
    added_actor=next(a.get_path_name() for a in actors.values() if isinstance(a,unreal.KZSnowDeformation)),isolated_project=str(ROOT),
    binding_recovery='Original retained Topology metadata and current saved scene; source-path SHA-derived clone names verified'),indent=2),encoding='utf-8')
report=dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),success=True,actors=len(actors),
    existing_poses_unchanged=len(before['poses']),snow_surfaces=len(parts),snow_materials=2,micro_dressing=len(micro),
    fire_actors=len(fire),route_walls=2281,nav_bounds=242,nav_null_modifiers=26,nav_links=24)
(OUT/'Resume20261007/SceneFinalAudit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('SNOW_SCENE_AUDIT_PASSED',json.dumps(report))
