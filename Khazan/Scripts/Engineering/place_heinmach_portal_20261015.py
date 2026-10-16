"""Guarded authoring: preserve the latest map, add one portal and one feet marker."""
from pathlib import Path
import hashlib, json, os, shutil, unreal as u

root = Path(u.Paths.project_dir()).resolve()
out = Path(os.environ['KZ_PORTAL_OUT'])
out.mkdir(parents=True, exist_ok=True)
map_file = root / 'Content/Maps/L_HeinMach_Environment.umap'
before_sha = hashlib.sha256(map_file.read_bytes()).hexdigest()
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
if not world or world.get_name() != 'L_HeinMach_Environment':
    world = u.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
assert world
subsystem = u.get_editor_subsystem(u.EditorActorSubsystem)
actors = subsystem.get_all_level_actors()
by_label = {a.get_actor_label(): a for a in actors}
gate = by_label['GateCube']
mode = os.environ.get('KZ_PORTAL_PLACE_MODE', 'apply')
if mode in ('correct', 'arena'):
    assert 'HM_Yetuga_EntrancePortal' in by_label and 'HM_Yetuga_ArenaArrival' in by_label
else:
    assert 'HM_Yetuga_EntrancePortal' not in by_label, 'Already placed; use readback, not repeat authoring.'
before = {a.get_actor_label(): dict(cls=a.get_class().get_path_name(), transform=a.get_actor_transform().export_text()) for a in actors}

anchors_file = root / 'Saved/ImportReports/HeinMach_PlayableCameraAnchors.json'
anchors = json.loads(anchors_file.read_text(encoding='utf-8-sig'))
anchor = next(a for a in anchors['all_player_starts'] if a['tag'] == 'Mission01_Boss_Start')
source_boss = None
if mode == 'arena':
    source_file = Path(anchors['source_json'])
    source_rows = json.loads(source_file.read_text(encoding='utf-8-sig'))
    point_index, point_row = next((i, x) for i, x in enumerate(source_rows) if x.get('Name') == 'Yetuga_TargetPoint')
    point_root_index = int(point_row['Properties']['RootComponent']['ObjectPath'].rsplit('.', 1)[1])
    point_raw = source_rows[point_root_index]['Properties']['RelativeLocation']
    spawn_index, spawn_row = next((i, x) for i, x in enumerate(source_rows) if x.get('Name') == 'SA_Yetuga' and x.get('Type') == 'xxSpawnHandler_Character')
    spawn_root_index = int(spawn_row['Properties']['RootComponent']['ObjectPath'].rsplit('.', 1)[1])
    spawn_raw = source_rows[spawn_root_index]['Properties']['RelativeLocation']
    point_location = u.Vector(point_raw['X'], point_raw['Y'], point_raw['Z'])
    spawn_location = u.Vector(spawn_raw['X'], spawn_raw['Y'], spawn_raw['Z'])
    facing = u.MathLibrary.find_look_at_rotation(point_location, spawn_location)
    anchor = dict(actor_name='Yetuga_TargetPoint', root_component_index=point_root_index,
        source_object_index=point_index, tag='grab', world_location_cm=point_location.to_tuple(),
        world_rotation_degrees=dict(pitch=0, yaw=facing.yaw, roll=0),
        policy='TEMP arrival placement using an original arena marker; yaw calculated toward original SA_Yetuga, not an original teleport rule')
    source_boss = dict(actor_name='SA_Yetuga', source_object_index=spawn_index, root_component_index=spawn_root_index,
        world_location_cm=spawn_location.to_tuple(), actor_bp=spawn_row['Properties']['ActorBP_Soft'])
boss = u.Vector(*anchor['world_location_cm'])

def floor_at(p, above=1000):
    # Authoring trace span only; not a runtime gameplay tuning value.
    hit = u.SystemLibrary.line_trace_single_by_profile(world, p + u.Vector(0, 0, above), p - u.Vector(0, 0, 2000),
        'Pawn', True, [gate], u.DrawDebugTrace.NONE, True)
    assert hit, 'No floor collision: author in the warmed full editor, not an uninitialized commandlet world.'
    data = hit.to_dict()
    broken = u.get_default_object(u.GameplayStatics).call_method('BreakHitResult', args=(hit,))
    point, normal = broken[4], broken[6]
    assert data['blocking_hit'] and normal.z > 0.7, str(data)
    return point, dict(point=point.to_tuple(), normal=normal.to_tuple(),
        actor=broken[9].get_path_name() if broken[9] else None,
        component=broken[10].get_path_name() if broken[10] else None, trace_profile='Pawn')

# Begin at the user's cube top, below the cave roof; an overhead roof is not the entrance floor.
gate_floor, gate_hit = floor_at(gate.get_actor_location(), gate.get_actor_bounds(False)[1].z)
exit_floor, exit_hit = floor_at(boss, 50 if mode == 'arena' else 1000)
record = dict(before_sha256=before_sha, source_anchor_report=str(anchors_file), source_anchor=anchor,
              gate_transform=gate.get_actor_transform().export_text(), gate_floor=gate_floor.to_tuple(),
              exit_floor=exit_floor.to_tuple(), gate_hit=gate_hit, exit_hit=exit_hit, before_actors=before,
              source_boss=source_boss)

# Audit mode provides collision evidence without saving or requiring the new native class.
if mode == 'trace':
    record['status'] = 'traced_read_only'
    (out / 'Placement.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
else:
    cls = u.load_class(None, '/Script/Khazan.KZBossPortal')
    assert cls
    # TEMP visible/entry size: fits a standing player; preview/readback verify it in this cave.
    portal_center = gate_floor + u.Vector(0, 0, 160)
    portal = by_label['HM_Yetuga_EntrancePortal'] if mode in ('correct', 'arena') else subsystem.spawn_actor_from_class(cls, portal_center, gate.get_actor_rotation())
    assert portal
    portal.set_actor_location(portal_center, False, False)
    portal.set_actor_label('HM_Yetuga_EntrancePortal')
    portal.set_folder_path('Gameplay/YetugaPortal')
    volume = portal.get_editor_property('entry_volume')
    volume.set_box_extent(u.Vector(80, 140, 160), False)
    effect = portal.get_editor_property('portal_effect')
    if mode != 'arena':
        effect.set_asset(u.load_asset('/Game/VFX/06_NiagaraBundle/N_Portal4Boss'))
        effect.set_relative_scale3d(u.Vector(1, 1, 1))
    exit_rotation = u.Rotator(pitch=0, yaw=anchor['world_rotation_degrees']['yaw'], roll=0)
    exit_point = by_label['HM_Yetuga_ArenaArrival'] if mode in ('correct', 'arena') else subsystem.spawn_actor_from_class(u.TargetPoint, exit_floor, exit_rotation)
    exit_point.set_actor_location_and_rotation(exit_floor, exit_rotation, False, False)
    exit_point.set_actor_label('HM_Yetuga_ArenaArrival')
    exit_point.set_folder_path('Gameplay/YetugaPortal')
    portal.set_editor_property('exit_point', exit_point)
    # Keep the user's locator editable, remove its solid grey block from play.
    gate.set_actor_hidden_in_game(True)
    gate.set_actor_enable_collision(False)
    after = {a.get_actor_label(): dict(cls=a.get_class().get_path_name(), transform=a.get_actor_transform().export_text())
             for a in subsystem.get_all_level_actors()}
    corrected_labels = {'HM_Yetuga_EntrancePortal', 'HM_Yetuga_ArenaArrival'} if mode in ('correct', 'arena') else set()
    assert all(after[k] == v for k, v in before.items() if k not in corrected_labels)
    # Abort on a concurrent map write instead of overwriting another task's newest level.
    assert hashlib.sha256(map_file.read_bytes()).hexdigest() == before_sha, 'Concurrent map write; reload and reapply.'
    backup = out / 'Before/L_HeinMach_Environment.umap'
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(map_file, backup)
    assert u.EditorLoadingAndSavingUtils.save_map(world, '/Game/Maps/L_HeinMach_Environment')
    record.update(status='main_map_saved', after_sha256=hashlib.sha256(map_file.read_bytes()).hexdigest(),
                  backup=str(backup), portal=portal.get_path_name(), portal_transform=portal.get_actor_transform().export_text(),
                  exit_point=exit_point.get_path_name(), exit_transform=exit_point.get_actor_transform().export_text(),
                  added_actors=sorted(set(after) - set(before)), actor_count_before=len(before), actor_count_after=len(after),
                  preserved_unrelated_actor_transforms=True,
                  changed_existing_actor_properties=(['HM_Yetuga_ArenaArrival.transform'] if mode == 'arena' else
                      ['GateCube.hidden', 'GateCube.ActorEnableCollision'] +
                      (['HM_Yetuga_EntrancePortal.transform', 'HM_Yetuga_ArenaArrival.rotation'] if mode == 'correct' else [])),
                  temporary_tuning=dict(entry_half_extent_cm=[80, 140, 160], portal_center_above_floor_cm=160,
                                        fade_out_seconds=0.45, black_hold_seconds=0.15, fade_in_seconds=0.6))
    (out / 'Placement.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
print('KZ_PORTAL_PLACEMENT_' + record['status'])
