"""Portal-only copies: preserve shared originals, compensate physical scene exposure."""
from pathlib import Path
import hashlib, json, os, shutil, unreal as u

root = Path(u.Paths.project_dir()).resolve()
out = Path(os.environ['KZ_PORTAL_OUT'])
out.mkdir(parents=True, exist_ok=True)
folder = '/Game/VFX/Portal/YetugaEntrance'
lib = u.MaterialEditingLibrary
originals = {}
copies = {}
materials = []

def disk(asset):
    return root / ('Content/' + asset.get_path_name().split('.')[0][6:] + '.uasset')

def remember(asset):
    path = asset.get_path_name()
    originals[path] = hashlib.sha256(disk(asset).read_bytes()).hexdigest()

def duplicate_material(source):
    key = source.get_path_name()
    if key in copies:
        return copies[key]
    remember(source)
    target = folder + '/Materials/' + source.get_name()
    copy = u.load_asset(target) if u.EditorAssetLibrary.does_asset_exist(target) else u.EditorAssetLibrary.duplicate_asset(key, target)
    assert copy, target
    copies[key] = copy
    row = dict(source=key, copy=copy.get_path_name())
    if isinstance(source, u.MaterialInstanceConstant):
        parent = duplicate_material(source.get_editor_property('parent'))
        lib.set_material_instance_parent(copy, parent)
        row['parent'] = parent.get_path_name()
    else:
        assert isinstance(source, u.Material)
        nodes = list(lib.get_material_expressions(copy))
        count = sum(isinstance(n, u.MaterialExpressionEyeAdaptationInverse) for n in nodes)
        row['exposure_inverse_before'] = count
        if not count:
            emission = lib.get_material_property_input_node(copy, u.MaterialProperty.MP_EMISSIVE_COLOR)
            assert emission, key
            output = lib.get_material_property_input_node_output_name(copy, u.MaterialProperty.MP_EMISSIVE_COLOR)
            inverse = lib.create_material_expression(copy, u.MaterialExpressionEyeAdaptationInverse)
            one = lib.create_material_expression(copy, u.MaterialExpressionConstant)
            one.set_editor_property('r', 1.0)  # Full engine exposure compensation; not a gameplay tuning value.
            inputs = list(lib.get_material_expression_input_names(inverse))
            assert lib.connect_material_expressions(emission, output, inverse, next(x for x in inputs if 'Light' in x))
            assert lib.connect_material_expressions(one, '', inverse, next(x for x in inputs if 'Alpha' in x))
            assert lib.connect_material_property(inverse, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
        errors = list(lib.recompile_material(copy))
        assert not errors, (key, errors)
        row['compile_errors'] = errors
    assert u.EditorAssetLibrary.save_loaded_asset(copy, only_if_is_dirty=False)
    row['sha256'] = hashlib.sha256(disk(copy).read_bytes()).hexdigest()
    materials.append(row)
    return copy

source = u.load_asset('/Game/VFX/06_NiagaraBundle/N_Portal4Boss')
remember(source)
target = folder + '/NS_YetugaEntrance'
system = u.load_asset(target) if u.EditorAssetLibrary.does_asset_exist(target) else u.EditorAssetLibrary.duplicate_asset(source.get_path_name(), target)
assert system
renderers = []
for emitter in ['FloatingParticles_0', 'LightParticles_6', 'PortalParticles2_9', 'PortalParticles_3', 'Vortex_2']:
    renderer = u.load_object(None, system.get_path_name() + ':' + emitter + '.NiagaraSpriteRendererProperties_0')
    source_renderer = u.load_object(None, source.get_path_name() + ':' + emitter + '.NiagaraSpriteRendererProperties_0')
    assert renderer and source_renderer, emitter
    material = duplicate_material(source_renderer.get_editor_property('material'))
    renderer.set_editor_property('material', material)
    renderers.append(dict(renderer=renderer.get_path_name(), material=material.get_path_name()))
renderer = u.load_object(None, system.get_path_name() + ':PortalGate_0.NiagaraMeshRendererProperties_0')
source_renderer = u.load_object(None, source.get_path_name() + ':PortalGate_0.NiagaraMeshRendererProperties_0')
overrides = list(source_renderer.get_editor_property('OverrideMaterials'))
assert len(overrides) == 1
overrides[0].set_editor_property('ExplicitMat', duplicate_material(overrides[0].get_editor_property('ExplicitMat')))
renderer.set_editor_property('OverrideMaterials', overrides)
renderers.append(dict(renderer=renderer.get_path_name(), material=overrides[0].get_editor_property('ExplicitMat').get_path_name()))
assert u.EditorAssetLibrary.save_loaded_asset(system, only_if_is_dirty=False)

world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
assert world.get_name() == 'L_HeinMach_Environment'
map_file = root / 'Content/Maps/L_HeinMach_Environment.umap'
before_sha = hashlib.sha256(map_file.read_bytes()).hexdigest()
actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
portal = next(a for a in actors if a.get_actor_label() == 'HM_Yetuga_EntrancePortal')
effect = portal.get_editor_property('portal_effect')
effect.set_asset(system)
# The package's core plane lies in XZ; rotate its normal from local Y to the gate's local X.
effect.set_relative_rotation(u.Rotator(pitch=0, yaw=90, roll=0), False, False)
effect.set_relative_scale3d(u.Vector(1, 1, 1))
assert hashlib.sha256(map_file.read_bytes()).hexdigest() == before_sha, 'Concurrent map write; reload and reapply.'
backup = out / 'Before/L_HeinMach_Environment.umap'
backup.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(map_file, backup)
assert u.EditorLoadingAndSavingUtils.save_map(world, '/Game/Maps/L_HeinMach_Environment')
for key, expected in originals.items():
    assert hashlib.sha256(disk(u.load_asset(key)).read_bytes()).hexdigest() == expected, key
report = dict(status='main_portal_look_saved', shared_originals_sha256=originals,
    shared_originals_preserved=True, materials=materials, renderers=renderers,
    system=system.get_path_name(), system_sha256=hashlib.sha256(disk(system).read_bytes()).hexdigest(),
    map_before_sha256=before_sha, map_after_sha256=hashlib.sha256(map_file.read_bytes()).hexdigest(),
    niagara_relative_transform=effect.get_relative_transform().export_text(),
    policy='Engine EyeAdaptationInverse Alpha1 only; original colour, alpha, blend, simulation and particle distribution retained.')
(out / 'PortalLook.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('KZ_PORTAL_LOOK_MAIN_SAVED')
