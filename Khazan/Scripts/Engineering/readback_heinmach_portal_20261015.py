"""Fresh-process saved contract check. No map or asset saves."""
from pathlib import Path
import hashlib, json, math, os, unreal as u

root = Path(u.Paths.project_dir()).resolve()
out = Path(os.environ['KZ_PORTAL_OUT'])
out.mkdir(parents=True, exist_ok=True)
map_file = root / 'Content/Maps/L_HeinMach_Environment.umap'
before_sha = hashlib.sha256(map_file.read_bytes()).hexdigest()
world = u.EditorLoadingAndSavingUtils.load_map('/Game/Maps/L_HeinMach_Environment')
assert world
actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
by_label = {a.get_actor_label(): a for a in actors}
portal = by_label['HM_Yetuga_EntrancePortal']
exit_point = by_label['HM_Yetuga_ArenaArrival']
gate = by_label['GateCube']
assert isinstance(portal, u.KZBossPortal)
assert portal.get_editor_property('exit_point') == exit_point
assert gate.get_editor_property('hidden') and not gate.get_actor_enable_collision()
placement_root = root / 'Metadata/HeinMachPortal_20261015'
initial = json.loads((placement_root / 'Placement04/Placement.json').read_text(encoding='utf-8'))
final = json.loads((placement_root / 'Placement06/Placement.json').read_text(encoding='utf-8'))
changed = [label for label, row in initial['before_actors'].items()
           if label not in by_label or by_label[label].get_actor_transform().export_text() != row['transform']
           or by_label[label].get_class().get_path_name() != row['cls']]
# A later concurrent Main save moved PlayerStart. Preserve that revision, not the old snapshot.
assert not (set(changed) - {'PlayerStart'}), changed
assert all(by_label[label].get_class().get_path_name() == initial['before_actors'][label]['cls'] for label in changed)
concurrent_changes = {label: dict(before=initial['before_actors'][label],
    after=dict(cls=by_label[label].get_class().get_path_name(), transform=by_label[label].get_actor_transform().export_text()))
    for label in changed}
anchor = final['source_anchor']
assert math.dist(exit_point.get_actor_location().to_tuple(), final['exit_floor']) < 0.0001
assert abs(exit_point.get_actor_rotation().yaw - anchor['world_rotation_degrees']['yaw']) < 0.0001
assert abs(exit_point.get_actor_rotation().pitch) < 0.0001 and abs(exit_point.get_actor_rotation().roll) < 0.0001
volume = portal.get_editor_property('entry_volume')
effect = portal.get_editor_property('portal_effect')
assert volume.get_unscaled_box_extent().to_tuple() == (80.0, 140.0, 160.0)
assert volume.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN) == u.CollisionResponseType.ECR_OVERLAP
assert effect.get_asset().get_path_name() == '/Game/VFX/Portal/YetugaEntrance/NS_YetugaEntrance.NS_YetugaEntrance'
assert abs(effect.get_editor_property('relative_rotation').yaw - 90) < 0.0001
assert math.dist(portal.get_actor_location().to_tuple(), (19550, 4270, final['gate_floor'][2] + 160)) < 0.0001
after_sha = hashlib.sha256(map_file.read_bytes()).hexdigest()
assert before_sha == after_sha
source = Path(json.loads((root / 'Saved/ImportReports/HeinMach_PlayableCameraAnchors.json').read_text(encoding='utf-8-sig'))['source_json'])
source_exports = json.loads(source.read_text(encoding='utf-8-sig'))
look = json.loads((placement_root / 'PortalLook03/PortalLook.json').read_text(encoding='utf-8'))
material_contracts = []
for original, expected in look['shared_originals_sha256'].items():
    path = root / ('Content/' + original.split('.')[0][6:] + '.uasset')
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, original
for row in look['materials']:
    original, copy = u.load_asset(row['source']), u.load_asset(row['copy'])
    if isinstance(copy, u.Material):
        nodes = u.MaterialEditingLibrary.get_material_expressions(copy)
        assert sum(isinstance(n, u.MaterialExpressionEyeAdaptationInverse) for n in nodes) == 1
        fields = ['BlendMode', 'TwoSided', 'OpacityMaskClipValue', 'MaterialDomain', 'ShadingModel']
        assert all(copy.get_editor_property(k) == original.get_editor_property(k) for k in fields)
        opacity = u.MaterialEditingLibrary.get_material_property_input_node(copy, u.MaterialProperty.MP_OPACITY)
        original_opacity = u.MaterialEditingLibrary.get_material_property_input_node(original, u.MaterialProperty.MP_OPACITY)
        assert (opacity.get_name() if opacity else None) == (original_opacity.get_name() if original_opacity else None)
    else:
        for field in ['ScalarParameterValues', 'VectorParameterValues', 'TextureParameterValues']:
            assert [x.export_text() for x in copy.get_editor_property(field)] == [x.export_text() for x in original.get_editor_property(field)]
    material_contracts.append(dict(original=row['source'], copy=row['copy'], alpha_blend_parameters_preserved=True))
report = dict(status='passed', asset_saves=0, map=world.get_path_name(), map_sha256=after_sha,
    actor_count=len(actors), preserved_original_actors=len(initial['before_actors'])-len(changed),
    original_actors_at_placement=len(initial['before_actors']), unrelated_transform_changes=changed,
    concurrent_post_placement_changes=concurrent_changes,
    added_actors=sorted(set(by_label) - set(initial['before_actors'])),
    portal_transform=portal.get_actor_transform().export_text(), exit_transform=exit_point.get_actor_transform().export_text(),
    entry_extent_cm=volume.get_unscaled_box_extent().to_tuple(),
    niagara=effect.get_asset().get_path_name(), niagara_relative_transform=effect.get_relative_transform().export_text(),
    fade_seconds={name: portal.get_editor_property(name) for name in ['fade_out_seconds', 'black_hold_seconds', 'fade_in_seconds']},
    source_json=str(source), source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    source_exports=[source_exports[anchor['root_component_index']], source_exports[anchor['source_object_index']]],
    source_boss=final['source_boss'],
    shared_originals_preserved=True, material_contracts=material_contracts,
    dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
    dirty_content=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()])
(out / 'Readback.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('KZ_PORTAL_FRESH_SAVED_READBACK_PASSED')
