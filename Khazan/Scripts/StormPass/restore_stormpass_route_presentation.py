"""Non-destructive StormPass phase visibility and source route access.

No source actor is deleted or moved. Native editor layers persist the review
selection; inactive alternatives are also hidden/noncolliding in game. This is
an environment review mode, not an implementation of gameplay streaming.
"""
import hashlib
import json
import os
import runpy

import unreal

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '../..'))
META = os.path.join(ROOT, 'Content/_Art/Kazan/Environment/StormPass/Metadata')
STATE = os.path.join(META, 'StormPass_PhaseVisibilityBaseline_20260907.json')
MAP = '/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment'
VARIANTS = ('boss_phase_1', 'boss_phase_2', 'boss_phase_clear')


def read(path):
    with open(path, encoding='utf-8-sig') as f:
        return json.load(f)


def write(path, data):
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def actors():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP + '.'):
        raise RuntimeError('StormPass must be open')
    return list(unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors())


def phase(actor):
    label = actor.get_actor_label()
    if label.startswith('SP_Landscape_Boss_'):
        return 'boss_phase_2'
    for value in VARIANTS:
        if '_stormpass_' + value + '_' in label.lower():
            return value
    return None


def capture_phase_baseline():
    if os.path.isfile(STATE):
        return read(STATE)
    records = []
    for actor in actors():
        variant = phase(actor)
        if not variant:
            continue
        components = []
        for c in actor.get_components_by_class(unreal.SceneComponent):
            value = {'name': c.get_name(), 'visible': bool(c.get_editor_property('visible'))}
            if isinstance(c, unreal.PrimitiveComponent):
                value['collision'] = str(c.get_collision_enabled()).split('.')[1].split(':')[0]
            components.append(value)
        records.append({'label': actor.get_actor_label(), 'variant': variant,
                        'hidden_in_game': bool(actor.get_editor_property('hidden')),
                        'post_process_enabled': bool(actor.get_editor_property('enabled')) if isinstance(actor, unreal.PostProcessVolume) else None,
                        'components': components})
    result = {'boundary': 'Preserve source actors/transforms; editor review state only, not runtime streaming logic.',
              'actors': records}
    write(STATE, result)
    return result


def set_variant(variant='traversal', save=False):
    if variant not in ('traversal',) + VARIANTS:
        raise ValueError('Unknown review variant')
    baseline = capture_phase_baseline()
    by_label = {a.get_actor_label(): a for a in actors()}
    layers = unreal.get_editor_subsystem(unreal.LayersSubsystem)
    groups = {v: [] for v in VARIANTS}
    for row in baseline['actors']:
        actor = by_label[row['label']]
        active = row['variant'] == variant
        groups[row['variant']].append(actor)
        actor.set_actor_hidden_in_game(row['hidden_in_game'] if active else True)
        # Discard earlier transient diagnostic flags; the named editor layer
        # below is the authoritative persistent visibility mechanism.
        actor.set_is_temporarily_hidden_in_editor(False)
        if row['post_process_enabled'] is not None:
            actor.set_editor_property('enabled', row['post_process_enabled'] if active else False)
        components = {c.get_name(): c for c in actor.get_components_by_class(unreal.SceneComponent)}
        for saved in row['components']:
            c = components[saved['name']]
            c.set_visibility(saved['visible'] if active else False, False)
            if 'collision' in saved:
                c.set_collision_enabled(getattr(unreal.CollisionEnabled, saved['collision']) if active else unreal.CollisionEnabled.NO_COLLISION)
    for value, members in groups.items():
        name = 'SP_SourceVariant_' + value
        if not layers.get_layer(name):
            layers.create_layer(name)
        layers.add_actors_to_layer(members, name)
        layers.set_layer_visibility(name, value == variant)
    result = {'active_variant': variant, 'counts': {k: len(v) for k, v in groups.items()},
              'retained_actors': sum(len(v) for v in groups.values()), 'deleted_actors': 0}
    write(os.path.join(META, 'StormPass_CurrentReviewVariant.json'), result)
    if save and not unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level():
        raise RuntimeError('Map save failed')
    print(json.dumps(result))
    return result


def restore_route_anchors():
    data = read(os.path.join(META, 'StormPass_PlayableCameraAnchors.json'))
    by_label = {a.get_actor_label(): a for a in actors()}
    subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    start = next(a for a in data['anchors'] if a['source_name'] == data['default_start'])
    existing = [a for a in by_label.values() if isinstance(a, unreal.PlayerStart)]
    label = 'SP_PlayerStart_Mission02_Start'
    if existing and (len(existing) != 1 or existing[0].get_actor_label() != label):
        raise RuntimeError('Unmanaged PlayerStart found; refusing to change it')
    actor = by_label.get(label) or subsystem.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(*start['location_cm']))
    actor.set_actor_label(label)
    actor.set_actor_location(unreal.Vector(*start['location_cm']), False, False)
    actor.set_actor_rotation(unreal.Rotator(*start['rotation_degrees']), False)
    actor.set_folder_path('StormPass/00_PlayRoute/PlayerStart')
    records = [{'label': label, 'source_name': start['source_name']}]
    names = [start['source_name']] + ['TS_%03d' % i for i in range(1, 6)] + ['Mission02_Start_Boss', 'Mission02_Start_BossZone']
    # Also expose the source's interior entrance anchors without spawning
    # additional players or implementing checkpoints.
    names += [a['source_name'] for a in data['anchors'] if 'xxPlayerStart' in a['source_name']]
    for index, name in enumerate(dict.fromkeys(names)):
        source = next(a for a in data['anchors'] if a['source_name'] == name)
        label = 'SP_ReviewCamera_%02d_%s' % (index, name)
        camera = by_label.get(label) or subsystem.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(*source['review_camera_location_cm']))
        camera.set_actor_label(label)
        camera.set_actor_location(unreal.Vector(*source['review_camera_location_cm']), False, False)
        pitch, yaw, roll = source['rotation_degrees']
        camera.set_actor_rotation(unreal.Rotator(-5, yaw, roll), False)
        camera.set_editor_property('is_editor_only_actor', True)
        camera.set_folder_path('StormPass/00_PlayRoute/ReviewCameras')
        camera.get_component_by_class(unreal.CameraComponent).set_editor_property('field_of_view', 90)
        records.append({'label': label, 'source_name': name, 'editor_only': True})
    write(os.path.join(META, 'StormPass_RouteAccessActors.json'), {'actors': records, 'gameplay_implementation': False})
    print(json.dumps({'player_starts': 1, 'review_cameras': len(records) - 1}))


def repair_cart_sections():
    helper = runpy.run_path(os.path.join(ROOT, 'Scripts/StormPass/repair_stormpass_surface_rendering.py'))
    source = os.path.join(ROOT, 'Saved/Extracted/StormPass/AdditionalMetadata_20260907/BBQ/Content/Art/World/World_Model/Prop/Machine/WP_BANTU_Cart_Wood_002.json')
    raw = next(r for r in read(source) if r.get('Type') == 'StaticMesh')
    source_indices = [s['MaterialIndex'] for s in raw['RenderData']['LODs'][0]['Sections']]
    if source_indices != [0, 1, 2, 3, 5, 4]:
        raise RuntimeError('Cart source section layout changed')
    root = '/Game/_Art/Kazan/Environment/StormPass/Reconstructed/SourceAssets/StormPass_StaticMeshLibrary/'
    mesh = unreal.load_asset(root + 'StaticMeshes/SM_WP_BANTU_Cart_Wood_002')
    if mesh.get_num_sections(0) != 6:
        raise RuntimeError('Cart imported section count changed')
    helper['fixer'].backup_asset(mesh.get_path_name())
    names = ['MI_WM_MCN_House_Base_0', 'MI_WM_MCN_House_Base_006', 'MI_WM_MCN_House_Base_002',
             'MI_WM_MCN_House_Base_002', 'MI_WM_MCN_Weapon_Wood', 'MI_WM_MCN_House_Base_005']
    materials = [unreal.load_asset(root + 'Materials/' + n) for n in names]
    if not all(materials):
        raise RuntimeError('Exact imported cart materials missing')
    slots = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    for index, material in enumerate(materials):
        if slots.get_lod_material_slot(mesh, 0, index) != index:
            raise RuntimeError('Cart section-to-slot layout changed')
        mesh.set_material(index, material)
    touched = []
    for a in actors():
        for c in a.get_components_by_class(unreal.StaticMeshComponent):
            if c.get_editor_property('static_mesh') == mesh:
                for i, material in enumerate(materials):
                    c.set_material(i, material)
                touched.append(a.get_actor_label())
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError('Cart mesh save failed')
    report = {'source_package': raw.get('Package'), 'source_sha256': hashlib.sha256(open(source, 'rb').read()).hexdigest(),
              'source_section_material_indices': source_indices, 'corrected_imported_materials': [m.get_path_name() for m in materials],
              'actors': touched, 'reason': 'USD deduplicated source material index 3, shifting section bindings and leaving one DisplayColor fallback.'}
    write(os.path.join(META, 'StormPass_CartSectionCorrection_20260907.json'), report)
    print(json.dumps({'cart_actors': len(touched), 'corrected_slots': [3, 4, 5]}))
