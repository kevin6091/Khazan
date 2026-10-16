"""Clear only GateCube's mesh; a second fresh process verifies the saved map."""
from pathlib import Path
import datetime, hashlib, json, os, shutil, traceback
import unreal as u

root = Path(u.Paths.project_dir()).resolve()
out = Path(os.environ['KZ_GATE_VIS_OUT'])
out.mkdir(parents=True, exist_ok=True)
map_name = '/Game/Maps/L_HeinMach_Environment'
map_file = root / 'Content/Maps/L_HeinMach_Environment.umap'


def sha():
    return hashlib.sha256(map_file.read_bytes()).hexdigest()


def contract(actors):
    by_name = {a.get_name(): a for a in actors}
    gate = by_name['StaticMeshActor_3219']
    assert gate.get_actor_label() == 'GateCube'
    mesh = gate.get_component_by_class(u.StaticMeshComponent)
    portal = by_name['KZBossPortal_0']
    target = portal.get_editor_property('exit_point')
    assert target.get_actor_label() == 'HM_Yetuga_ArenaArrival'
    effect = portal.get_editor_property('portal_effect')
    volume = portal.get_editor_property('entry_volume')
    asset = mesh.get_editor_property('static_mesh')
    return gate, mesh, dict(
        actor_count=len(actors), gate_path=gate.get_path_name(),
        gate_transform=gate.get_actor_transform().export_text(),
        mesh=asset.get_path_name() if asset else None,
        hidden_in_game=gate.get_editor_property('hidden'),
        gate_collision=gate.get_actor_enable_collision(),
        portal_path=portal.get_path_name(),
        portal_transform=portal.get_actor_transform().export_text(),
        effect=effect.get_asset().get_path_name(),
        effect_transform=effect.get_relative_transform().export_text(),
        exit_path=target.get_path_name(),
        exit_transform=target.get_actor_transform().export_text(),
        entry_extent=list(volume.get_unscaled_box_extent().to_tuple()),
        entry_collision=str(volume.get_collision_enabled()),
        fade_seconds={k: portal.get_editor_property(k) for k in
                      ('fade_out_seconds', 'black_hold_seconds', 'fade_in_seconds')})


try:
    mode = os.environ['KZ_GATE_VIS_MODE']
    before_sha = sha()
    world = u.EditorLoadingAndSavingUtils.load_map(map_name)
    assert world and world.get_path_name() == map_name + '.L_HeinMach_Environment'
    actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    gate, mesh, before = contract(actors)
    saves = 0
    if mode == 'hide' and before['mesh'] is not None:
        assert before['mesh'] == '/Engine/BasicShapes/Cube.Cube', before['mesh']
        assert before['hidden_in_game'] and not before['gate_collision']
        assert sha() == before_sha, 'Concurrent map save before change; retry from fresh disk.'
        shutil.copy2(map_file, out / 'Before.umap')
        with u.ScopedEditorTransaction('Remove GateCube placeholder mesh'):
            gate.modify()
            mesh.modify()
            assert mesh.set_static_mesh(None)
        assert mesh.get_editor_property('static_mesh') is None
        assert sha() == before_sha, 'Concurrent map save before save; do not overwrite.'
        assert u.EditorLoadingAndSavingUtils.save_map(world, map_name)
        saves = 1
    gate, mesh, after = contract(actors)
    assert after['mesh'] is None
    assert after['hidden_in_game'] and not after['gate_collision']
    assert {k:v for k,v in before.items() if k != 'mesh'} == {
        k:v for k,v in after.items() if k != 'mesh'}
    if mode == 'readback':
        assert sha() == before_sha
        expected = json.loads((out.parent / 'GateCubeVisibility01/Result.json').read_text(encoding='utf-8'))
        mismatches = {k:dict(saved=expected['after'].get(k), readback=v)
                      for k,v in after.items() if v != expected['after'].get(k)}
        assert not mismatches, 'Target contract changed after save: ' + repr(mismatches)
        assert sha() == expected['map_after_sha256'], 'Map changed after save; audit latest revision.'
    report = dict(status='passed', mode=mode, utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        pid=os.getpid(), map=map_name, map_saves=saves, map_before_sha256=before_sha,
        map_after_sha256=sha(), before=before, after=after,
        dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
        dirty_content=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
    (out / 'Result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('KZ_GATE_CUBE_VISIBILITY_PASSED ' + mode)
except Exception:
    (out / 'Failure.json').write_text(json.dumps(dict(error=traceback.format_exc()), indent=2), encoding='utf-8')
    raise
