"""Restore HeinMach movement collision and source navigation bounds.

This pass consumes the original ``HeinMach_Chrcollision`` FModel export and
the resolved 9,104-prop root-template audit. It changes only gameplay
collision, navigation bounds, the authored tutorial PlayerStart, and the map's
GameMode override. Existing visual transforms, materials, user exclusions, and
the deliberately omitted opening sequence remain untouched.
"""

from __future__ import annotations

import collections
import importlib.util
import json
import math
import os
import re
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
FMODEL_ROOT = os.path.join(os.path.expanduser("~"), "Desktop", "\uce74\uc794")
SOURCE_COLLISION_JSON = os.path.join(
    FMODEL_ROOT,
    "Exports",
    "BBQ",
    "Content",
    "_Kazan_",
    "Level",
    "HeinMach",
    "HeinMach_Chrcollision.json",
)
ROOT_AUDIT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_RootTemplateCoverage_Audit.json",
)
ROOT_AUDIT_SCRIPT = os.path.join(
    SCRIPT_DIR, "audit_heinmach_root_template_coverage.py"
)
METADATA_ROOT = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Player",
    "Environment",
    "HeinMach",
    "Metadata",
)
EXCLUSION_PATHS = (
    os.path.join(METADATA_ROOT, "HeinMach_UserExclusions.json"),
    os.path.join(METADATA_ROOT, "HeinMach_OptimizationExclusions.json"),
)
MAP_PATH = "/Game/_Art/Player/Environment/HeinMach/Maps/L_HeinMach_Environment"
GAME_MODE_ASSET = "/Game/Bluprints/GameSystem/BP_GameMode"
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_Playability_Restoration.json",
)
ROUTE_COLLISION_MAPPING_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_RouteCollision_SourceMapping.json",
)
AUTOMATION_ROUTE_NAV_COMPATIBILITY_PATH = os.path.join(
    METADATA_ROOT,
    "HeinMach_AutomationRouteNavCompatibility.json",
)

ROUTE_COLLISION_LABEL = "HM_RouteCollision_Source_Chrcollision"
NAV_BOUNDS_LABEL_PREFIX = "HM_NavBounds_Source_"
NAV_MODIFIER_LABEL_PREFIX = "HM_NavModifier_Source_"
NAV_LINK_LABEL_PREFIX = "HM_NavLink_Source_"
AUTOMATION_NAV_LINK_LABEL_PREFIX = "HM_NavLink_AutomationRoute_"
MANAGED_PROP_PREFIX = "HM_Prop_"
TERRAIN_LABEL_PREFIXES = ("HM_Landscape_", "HM_Terrain_")
PLAYER_START_LABEL = "HM_Tutorial_PlayerStart_DualAxeSword"
ROUTE_COLLISION_FOLDER = "HeinMach/Gameplay/RouteCollision"
NAV_BOUNDS_FOLDER = "HeinMach/Gameplay/NavigationBounds"
NAV_MODIFIER_FOLDER = "HeinMach/Gameplay/NavigationModifiers"
NAV_LINKS_FOLDER = "HeinMach/Gameplay/NavigationLinks"

# Reconstruction-only compensation.  The restored Recast edge beside source
# NavLinkProxy6 is 31.4 cm from its exact source endpoint, 1.4 cm beyond the
# original 30 cm snap radius.  Keep the source value in the report and apply a
# local 50 cm radius so this authored traversal survives the mesh conversion.
NAV_LINK_SNAP_RADIUS_OVERRIDES_CM = {828: 50.0}

# Direct source value: HeinMach_Spawn_Main01 / MISSION01_START.  The source Z
# is an anchor/root value, not a valid Unreal Character capsule center in the
# reconstructed static Landscape.
TUTORIAL_SOURCE_LOCATION = (12073.493, 24725.363, 303.5308)
# Runtime Pawn-profile trace against restored LandscapeComponent_61.
TUTORIAL_GROUND_SURFACE_Z = 354.70317567901657
# BP_Player CDO, CollisionCylinder scaled capsule half-height.
TUTORIAL_PLAYER_CAPSULE_HALF_HEIGHT = 88.0
# Temporary spawn-only clearance: the measured surface normal slopes across
# the 34 cm capsule radius, so the center is raised 8 cm above exact contact.
TUTORIAL_SPAWN_CLEARANCE = 8.0
TUTORIAL_START_LOCATION = (
    TUTORIAL_SOURCE_LOCATION[0],
    TUTORIAL_SOURCE_LOCATION[1],
    TUTORIAL_GROUND_SURFACE_Z
    + TUTORIAL_PLAYER_CAPSULE_HALF_HEIGHT
    + TUTORIAL_SPAWN_CLEARANCE,
)
TUTORIAL_START_ROTATION = (0.0, 245.0138, 0.0)

LOCAL_INDEX_RE = re.compile(r"\.(\d+)$")
NUMBERED_COLLISION_TAG_RE = re.compile(
    r"^\d+_Collision(PrimaryType|AdjectiveType|Useless)$"
)
BASE_COLLISION_TAG_RE = re.compile(
    r"^CollisionPrimaryType_(PrimaryType|AdjectiveType|Useless)$"
)


def log(message):
    unreal.log("KHAZAN_HEINMACH_PLAYABILITY: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def load_root_audit_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_heinmach_root_audit", ROOT_AUDIT_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to import HeinMach root-template audit module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def local_index(reference):
    path = reference.get("ObjectPath", "") if isinstance(reference, dict) else ""
    match = LOCAL_INDEX_RE.search(path)
    return int(match.group(1)) if match else None


def source_vector(value, keys, defaults):
    value = value if isinstance(value, dict) else {}
    return [float(value.get(key, default)) for key, default in zip(keys, defaults)]


def local_transform(obj):
    properties = obj.get("Properties", {}) if isinstance(obj, dict) else {}
    location = source_vector(
        properties.get("RelativeLocation"), ("X", "Y", "Z"), (0.0, 0.0, 0.0)
    )
    rotation = source_vector(
        properties.get("RelativeRotation"),
        ("Pitch", "Yaw", "Roll"),
        (0.0, 0.0, 0.0),
    )
    scale = source_vector(
        properties.get("RelativeScale3D"), ("X", "Y", "Z"), (1.0, 1.0, 1.0)
    )
    return unreal.Transform(
        location=unreal.Vector(x=location[0], y=location[1], z=location[2]),
        rotation=unreal.Rotator(
            pitch=rotation[0], yaw=rotation[1], roll=rotation[2]
        ),
        scale=unreal.Vector(x=scale[0], y=scale[1], z=scale[2]),
    )


def resolve_world_transform(objects, index, cache, stack=()):
    if index in cache:
        return cache[index]
    if index is None or index < 0 or index >= len(objects):
        raise RuntimeError("Invalid local source object index: {}".format(index))
    if index in stack:
        raise RuntimeError("Attachment cycle at source object {}".format(index))
    obj = objects[index]
    result = local_transform(obj)
    parent_index = local_index((obj.get("Properties") or {}).get("AttachParent"))
    if parent_index is not None:
        parent = resolve_world_transform(
            objects, parent_index, cache, stack + (index,)
        )
        result = unreal.MathLibrary.compose_transforms(result, parent)
    cache[index] = result
    return result


def managed_prop_label(record):
    return "{}{}_{}_{}".format(
        MANAGED_PROP_PREFIX,
        record.get("source_level", "Unknown"),
        record.get("source_object_index", 0),
        record.get("actor_name", "Actor"),
    )[:220]


def load_root_prop_exclusions():
    labels = set()
    for path in EXCLUSION_PATHS:
        payload = load_json(path)
        for record in payload.get("exclusions", []):
            if (
                record.get("category") == "root_prop"
                and record.get("do_not_restore")
                and record.get("label")
            ):
                labels.add(str(record["label"]))
    return labels


def collision_tag(tags):
    tags = [str(value) for value in (tags or [])]
    for value in tags:
        match = NUMBERED_COLLISION_TAG_RE.match(value)
        if match:
            return match.group(1), value
    for value in tags:
        match = BASE_COLLISION_TAG_RE.match(value)
        if match:
            return match.group(1), value
    return None, None


def source_body_collision_override(record, resolver):
    package = str(record["source_package"])
    objects = resolver.load_package(package)
    actor_index = int(record["source_object_index"])
    if objects is None or not (0 <= actor_index < len(objects)):
        raise RuntimeError(
            "Unable to load source actor {}:{}".format(package, actor_index)
        )
    actor = objects[actor_index]
    root_reference = (actor.get("Properties") or {}).get("RootComponent")
    component, component_package, component_objects, _ = resolver.resolve_ref(
        root_reference, package, objects
    )
    if (
        not isinstance(component, dict)
        or component_package is None
        or component_objects is None
    ):
        raise RuntimeError(
            "Unable to resolve source root component {}:{}".format(
                package, actor_index
            )
        )
    body_instance, _, _, _ = resolver.inherited_property(
        component, component_package, component_objects, "BodyInstance"
    )
    if not isinstance(body_instance, dict):
        return None
    value = body_instance.get("CollisionEnabled")
    return str(value) if value is not None else None


def collision_decision(record, resolver):
    body_override = source_body_collision_override(record, resolver)
    if body_override == "ECollisionEnabled::NoCollision":
        return False, "source_body_no_collision", body_override, None
    if body_override in (
        "ECollisionEnabled::QueryOnly",
        "ECollisionEnabled::QueryAndPhysics",
    ):
        return True, "source_body_query_enabled", body_override, None
    if body_override == "ECollisionEnabled::PhysicsOnly":
        return False, "source_body_physics_only", body_override, None

    category, source_tag = collision_tag(record.get("tags"))
    if category in ("PrimaryType", "AdjectiveType"):
        return True, "source_collision_tag", body_override, source_tag
    if category == "Useless":
        return False, "source_collision_tag", body_override, source_tag

    # The 23 untagged records are visible rock meshes. Their cooked BodySetup
    # was not exported by FModel, so collision is enabled as an explicit
    # temporary fallback to prevent traversal through visible rock mass.
    return True, "temporary_untagged_visible_rock_fallback", body_override, None


def set_folder(actor, folder):
    try:
        actor.set_folder_path(folder)
    except Exception:
        actor.set_editor_property("folder_path", folder)


def set_tags(actor, tags):
    actor.set_editor_property("tags", [unreal.Name(value) for value in tags])


def configure_component_navigation(component, enabled):
    try:
        component.set_can_ever_affect_navigation(bool(enabled))
    except Exception:
        component.set_editor_property("can_ever_affect_navigation", bool(enabled))


def configure_collision_mesh_assets(collision_meshes):
    changed_meshes = []
    already_configured_meshes = []
    trace_flag_changed_meshes = []
    collision_cook_opt_out_cleared_meshes = []
    navigation_data_enabled_meshes = []
    target = unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE

    for mesh_path, mesh in sorted(collision_meshes.items()):
        body_setup = mesh.get_editor_property("body_setup")
        if not body_setup:
            raise RuntimeError("Collision mesh has no BodySetup: " + mesh_path)

        current_trace_flag = body_setup.get_editor_property("collision_trace_flag")
        never_needs_cooked = bool(
            body_setup.get_editor_property("never_needs_cooked_collision_data")
        )
        has_navigation_data = bool(
            mesh.get_editor_property("has_navigation_data")
        )
        changed = (
            current_trace_flag != target
            or never_needs_cooked
            or not has_navigation_data
        )
        if changed:
            mesh.modify()
            body_setup.modify()
            if current_trace_flag != target:
                body_setup.set_editor_property("collision_trace_flag", target)
                trace_flag_changed_meshes.append(mesh_path)
            if never_needs_cooked:
                # FModel/USD-restored meshes were imported without gameplay
                # collision, which left this BodySetup optimization enabled.
                # It must be cleared or Chaos never creates the complex
                # triangle mesh even when the component blocks Pawn.
                body_setup.set_editor_property(
                    "never_needs_cooked_collision_data", False
                )
                collision_cook_opt_out_cleared_meshes.append(mesh_path)
            if not has_navigation_data:
                # StaticMeshComponent navigation relevance is gated by the
                # mesh asset.  The reconstructed USD/FModel assets all had
                # this disabled, so Recast ignored their valid BodySetup
                # collision even though each live component affected nav.
                # set_editor_property sends the StaticMesh edit notification;
                # UStaticMesh then builds NavCollision and broadcasts the
                # change to every component using this asset.
                mesh.set_editor_property("has_navigation_data", True)
                navigation_data_enabled_meshes.append(mesh_path)
            if not unreal.EditorAssetLibrary.save_loaded_asset(
                mesh, only_if_is_dirty=False
            ):
                raise RuntimeError("Failed to save collision mesh: " + mesh_path)
            changed_meshes.append(mesh_path)
        else:
            already_configured_meshes.append(mesh_path)

    return {
        "collision_mesh_count": len(collision_meshes),
        "changed_collision_mesh_count": len(changed_meshes),
        "already_configured_collision_mesh_count": len(
            already_configured_meshes
        ),
        "changed_complex_as_simple_mesh_count": len(trace_flag_changed_meshes),
        "cleared_collision_cook_opt_out_mesh_count": len(
            collision_cook_opt_out_cleared_meshes
        ),
        "enabled_navigation_data_mesh_count": len(
            navigation_data_enabled_meshes
        ),
    }


def restore_prop_collision(actor_subsystem, root_payload):
    records = list(root_payload.get("resolved_root_placements", []))
    if len(records) != 9104:
        raise RuntimeError(
            "Expected 9,104 resolved root props, found {}".format(len(records))
        )

    source_by_label = {managed_prop_label(record): record for record in records}
    if len(source_by_label) != len(records):
        raise RuntimeError("Resolved root prop labels are not unique")

    actors_by_label = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(MANAGED_PROP_PREFIX)
    }
    exclusions = load_root_prop_exclusions()
    expected_active = set(source_by_label) - exclusions
    unexpected = sorted(set(actors_by_label) - set(source_by_label))
    missing = sorted(expected_active - set(actors_by_label))
    excluded_present = sorted(set(actors_by_label) & exclusions)
    if unexpected:
        raise RuntimeError("Unexpected managed prop actor: " + unexpected[0])
    if missing:
        raise RuntimeError(
            "Active managed prop is missing; preserve the new user deletion first: "
            + missing[0]
        )
    if excluded_present:
        raise RuntimeError("Excluded prop was restored unexpectedly: " + excluded_present[0])

    root_module = load_root_audit_module()
    resolver = root_module.PackageResolver(root_module.Path(FMODEL_ROOT))
    decision_counts = collections.Counter()
    source_tag_counts = collections.Counter()
    body_override_counts = collections.Counter()
    collision_meshes = {}
    enabled_actor_count = 0
    disabled_actor_count = 0

    for index, (label, actor) in enumerate(sorted(actors_by_label.items()), start=1):
        record = source_by_label[label]
        enabled, reason, body_override, source_tag = collision_decision(
            record, resolver
        )
        component = actor.get_component_by_class(unreal.StaticMeshComponent)
        if not component:
            raise RuntimeError("Managed prop has no StaticMeshComponent: " + label)
        mesh = component.get_editor_property("static_mesh")
        if not mesh:
            raise RuntimeError("Managed prop has no StaticMesh: " + label)

        actor.set_actor_enable_collision(enabled)
        if enabled:
            component.set_collision_profile_name("BlockAll")
            component.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
            configure_component_navigation(component, True)
            collision_meshes[mesh.get_path_name()] = mesh
            enabled_actor_count += 1
        else:
            component.set_collision_profile_name("NoCollision")
            component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
            configure_component_navigation(component, False)
            disabled_actor_count += 1

        decision_counts[reason] += 1
        source_tag_counts[source_tag or "<none>"] += 1
        body_override_counts[body_override or "<unset>"] += 1
        if index % 1000 == 0:
            log("Configured source collision for {}/{} live props".format(
                index, len(actors_by_label)
            ))

    mesh_collision = configure_collision_mesh_assets(collision_meshes)

    return {
        "source_resolved_prop_count": len(records),
        "active_prop_count": len(actors_by_label),
        "excluded_prop_count": len(exclusions),
        "collision_enabled_actor_count": enabled_actor_count,
        "collision_disabled_actor_count": disabled_actor_count,
        **mesh_collision,
        "decision_counts": dict(sorted(decision_counts.items())),
        "source_tag_counts": dict(sorted(source_tag_counts.items())),
        "body_override_counts": dict(sorted(body_override_counts.items())),
        "temporary_fallback_count": decision_counts[
            "temporary_untagged_visible_rock_fallback"
        ],
    }


def restore_terrain_collision(actor_subsystem):
    terrain_actors = []
    collision_meshes = {}
    for actor in actor_subsystem.get_all_level_actors():
        if not actor or not isinstance(actor, unreal.StaticMeshActor):
            continue
        label = actor.get_actor_label()
        if not label.startswith(TERRAIN_LABEL_PREFIXES):
            continue

        component = actor.static_mesh_component
        mesh = component.get_editor_property("static_mesh")
        if not mesh:
            raise RuntimeError("Terrain actor has no StaticMesh: " + label)
        actor.set_actor_enable_collision(True)
        component.set_collision_profile_name("BlockAll")
        component.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
        configure_component_navigation(component, True)
        collision_meshes[mesh.get_path_name()] = mesh
        terrain_actors.append(label)

    if not terrain_actors:
        raise RuntimeError("No restored HeinMach terrain actors were found")

    mesh_collision = configure_collision_mesh_assets(collision_meshes)
    return {
        "terrain_actor_count": len(terrain_actors),
        **mesh_collision,
    }


def restore_route_walls(actor_subsystem, objects):
    actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    matches = [actor for actor in actors if actor.get_actor_label() == ROUTE_COLLISION_LABEL]
    if len(matches) > 1:
        raise RuntimeError("Duplicate managed route collision actors")
    if matches:
        actor = matches[0]
        if not isinstance(actor, unreal.KZLevelRouteCollisionActor):
            raise RuntimeError("Managed route collision label has the wrong class")
        created = False
    else:
        actor = actor_subsystem.spawn_actor_from_class(
            unreal.KZLevelRouteCollisionActor,
            unreal.Vector(x=0.0, y=0.0, z=0.0),
            unreal.Rotator(pitch=0.0, yaw=0.0, roll=0.0),
        )
        if not actor:
            raise RuntimeError("Failed to spawn KZLevelRouteCollisionActor")
        actor.set_actor_label(ROUTE_COLLISION_LABEL, mark_dirty=True)
        created = True

    actor.set_actor_location(unreal.Vector(x=0.0, y=0.0, z=0.0), False, False)
    actor.set_actor_rotation(
        unreal.Rotator(pitch=0.0, yaw=0.0, roll=0.0), False
    )
    actor.set_actor_scale3d(unreal.Vector(x=1.0, y=1.0, z=1.0))
    set_folder(actor, ROUTE_COLLISION_FOLDER)
    set_tags(
        actor,
        (
            "HeinMachSourceCollision",
            "Source_HeinMach_Chrcollision",
            "BlocksCharacterMovement",
        ),
    )

    actor.clear_boundary_instances()
    transform_cache = {}
    source_wall_count = 0
    degenerate_wall_count = 0
    source_disabled_wall_count = 0
    instance_sources = []
    restored_bounds = {
        "min": [math.inf, math.inf, math.inf],
        "max": [-math.inf, -math.inf, -math.inf],
    }

    for source_index, source_object in enumerate(objects):
        if source_object.get("Type") != "xxWallComponent":
            continue
        source_wall_count += 1
        properties = source_object.get("Properties") or {}
        extent_value = properties.get("BoxExtent") or {}
        extent = [
            float(extent_value.get("X", 0.0)),
            float(extent_value.get("Y", 0.0)),
            float(extent_value.get("Z", 0.0)),
        ]
        if any(value <= 0.01 for value in extent):
            degenerate_wall_count += 1
            continue

        owner_index = local_index(source_object.get("Outer"))
        owner = (
            objects[owner_index]
            if owner_index is not None and 0 <= owner_index < len(objects)
            else {}
        )
        owner_properties = owner.get("Properties") or {}
        wall_collision_enabled = owner_properties.get("bWallCollisionEnabled")
        if wall_collision_enabled is False:
            source_disabled_wall_count += 1
            continue

        world_transform = resolve_world_transform(
            objects, source_index, transform_cache
        )
        center = world_transform.translation
        rotation = world_transform.rotation.rotator()
        result = actor.add_boundary_box(
            center,
            rotation,
            unreal.Vector(x=extent[0], y=extent[1], z=extent[2]),
        )
        if int(result) < 0:
            raise RuntimeError(
                "Failed to add source wall instance {}".format(source_index)
            )
        body_instance = properties.get("BodyInstance") or {}
        instance_sources.append(
            {
                "instance_index": int(result),
                "source_component_index": source_index,
                "source_component_name": source_object.get("Name"),
                "source_owner_index": owner_index,
                "source_owner_type": owner.get("Type"),
                "source_owner_name": owner.get("Name"),
                "source_owner_wall_collision_enabled": wall_collision_enabled,
                "source_component_collision_enabled": body_instance.get(
                    "CollisionEnabled"
                ),
                "world_center_cm": [
                    float(center.x),
                    float(center.y),
                    float(center.z),
                ],
                "world_rotation_degrees": [
                    float(rotation.pitch),
                    float(rotation.yaw),
                    float(rotation.roll),
                ],
                "box_half_extent_cm": extent,
            }
        )
        for axis, center_value in enumerate((center.x, center.y, center.z)):
            restored_bounds["min"][axis] = min(
                restored_bounds["min"][axis], center_value - extent[axis]
            )
            restored_bounds["max"][axis] = max(
                restored_bounds["max"][axis], center_value + extent[axis]
            )

    actor.finalize_boundary_instances()
    restored_count = int(actor.get_boundary_instance_count())
    if (
        source_wall_count != 3206
        or restored_count != 2281
        or source_disabled_wall_count != 1
    ):
        raise RuntimeError(
            "Unexpected wall inventory: source={} restored={} degenerate={} "
            "source_disabled={}".format(
                source_wall_count,
                restored_count,
                degenerate_wall_count,
                source_disabled_wall_count,
            )
        )
    if len(instance_sources) != restored_count:
        raise RuntimeError(
            "Route collision source mapping count mismatch: {} != {}".format(
                len(instance_sources), restored_count
            )
        )
    write_json(
        ROUTE_COLLISION_MAPPING_PATH,
        {
            "status": "mapped",
            "source_collision_json": SOURCE_COLLISION_JSON,
            "managed_actor_label": ROUTE_COLLISION_LABEL,
            "source_wall_component_count": source_wall_count,
            "omitted_degenerate_component_count": degenerate_wall_count,
            "omitted_source_disabled_non_degenerate_count": (
                source_disabled_wall_count
            ),
            "restored_instance_count": restored_count,
            "instances": instance_sources,
        },
    )
    return {
        "actor_label": ROUTE_COLLISION_LABEL,
        "created": created,
        "source_wall_component_count": source_wall_count,
        "restored_non_degenerate_box_count": restored_count,
        "omitted_degenerate_component_count": degenerate_wall_count,
        "omitted_source_disabled_non_degenerate_count": source_disabled_wall_count,
        "source_mapping_report": ROUTE_COLLISION_MAPPING_PATH,
        "source_mapping_record_count": len(instance_sources),
        "world_bounds_cm": restored_bounds,
    }


def restore_navigation_bounds(actor_subsystem, objects):
    actors_by_label = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor
    }
    source_records = []
    transform_cache = {}
    for source_index, source_object in enumerate(objects):
        if source_object.get("Type") != "xxNavMeshBoundsVolume":
            continue
        root_index = local_index(
            (source_object.get("Properties") or {}).get("RootComponent")
        )
        if root_index is None:
            raise RuntimeError(
                "Source NavMeshBoundsVolume has no root: {}".format(source_index)
            )
        transform = resolve_world_transform(objects, root_index, transform_cache)
        label = "{}{}_{}".format(
            NAV_BOUNDS_LABEL_PREFIX,
            source_index,
            source_object.get("Name", "NavMeshBoundsVolume"),
        )[:220]
        source_records.append((label, source_index, source_object, transform))

    if len(source_records) != 242:
        raise RuntimeError(
            "Expected 242 source NavMesh bounds, found {}".format(
                len(source_records)
            )
        )
    expected_labels = {record[0] for record in source_records}
    stale = [
        actor
        for label, actor in actors_by_label.items()
        if label.startswith(NAV_BOUNDS_LABEL_PREFIX) and label not in expected_labels
    ]
    for actor in stale:
        actor_subsystem.destroy_actor(actor)

    created_count = 0
    reused_count = 0
    for label, source_index, source_object, transform in source_records:
        actor = actors_by_label.get(label)
        if actor and not isinstance(actor, unreal.KZNavMeshBoundsBox):
            raise RuntimeError("Managed nav bounds label has the wrong class: " + label)
        if not actor:
            actor = actor_subsystem.spawn_actor_from_class(
                unreal.KZNavMeshBoundsBox,
                transform.translation,
                transform.rotation.rotator(),
            )
            if not actor:
                raise RuntimeError("Failed to spawn nav bounds: " + label)
            actor.set_actor_label(label, mark_dirty=True)
            actors_by_label[label] = actor
            created_count += 1
        else:
            reused_count += 1
        actor.set_actor_location(transform.translation, False, False)
        actor.set_actor_rotation(transform.rotation.rotator(), False)
        actor.set_actor_scale3d(transform.scale3d)
        actor.set_actor_enable_collision(False)
        set_folder(actor, NAV_BOUNDS_FOLDER)
        set_tags(
            actor,
            (
                "HeinMachSourceNavBounds",
                "Source_HeinMach_Chrcollision",
                "SourceIndex_{}".format(source_index),
            ),
        )

    final = [
        actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(NAV_BOUNDS_LABEL_PREFIX)
    ]
    if len(final) != len(source_records):
        raise RuntimeError(
            "Final NavMesh bounds count mismatch: {}".format(len(final))
        )
    return {
        "source_count": len(source_records),
        "created_count": created_count,
        "reused_count": reused_count,
        "removed_stale_count": len(stale),
        "final_count": len(final),
        "source_box_half_extent_cm": 100.0,
        "transform_basis": "source BrushComponent RelativeLocation/Rotation/Scale3D",
    }


def restore_navigation_modifiers(actor_subsystem, objects):
    actors_by_label = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor
    }
    source_records = []
    transform_cache = {}
    for source_index, source_object in enumerate(objects):
        if source_object.get("Type") != "NavModifierVolume":
            continue
        properties = source_object.get("Properties") or {}
        root_index = local_index(properties.get("RootComponent"))
        if root_index is None:
            raise RuntimeError(
                "Source NavModifierVolume has no root: {}".format(source_index)
            )
        root = objects[root_index]
        root_properties = root.get("Properties") or {}
        body_setup_index = local_index(root_properties.get("BrushBodySetup"))
        if body_setup_index is None:
            raise RuntimeError(
                "Source NavModifierVolume has no BrushBodySetup: {}".format(
                    source_index
                )
            )
        body_setup = objects[body_setup_index]
        convex_elems = (
            ((body_setup.get("Properties") or {}).get("AggGeom") or {}).get(
                "ConvexElems"
            )
            or []
        )
        if len(convex_elems) != 1:
            raise RuntimeError(
                "Expected one source NavModifier convex box at {}".format(
                    source_index
                )
            )
        elem_box = convex_elems[0].get("ElemBox") or {}
        box_min = elem_box.get("Min") or {}
        box_max = elem_box.get("Max") or {}
        expected_min = (-100.0, -100.0, -100.0)
        expected_max = (100.0, 100.0, 100.0)
        actual_min = tuple(float(box_min.get(axis, 0.0)) for axis in "XYZ")
        actual_max = tuple(float(box_max.get(axis, 0.0)) for axis in "XYZ")
        if actual_min != expected_min or actual_max != expected_max:
            raise RuntimeError(
                "Unexpected source NavModifier box at {}: {} -> {}".format(
                    source_index, actual_min, actual_max
                )
            )

        transform = resolve_world_transform(objects, root_index, transform_cache)
        label = "{}{}_{}".format(
            NAV_MODIFIER_LABEL_PREFIX,
            source_index,
            source_object.get("Name", "NavModifierVolume"),
        )[:220]
        source_records.append((label, source_index, source_object, transform))

    if len(source_records) != 26:
        raise RuntimeError(
            "Expected 26 source NavModifier volumes, found {}".format(
                len(source_records)
            )
        )
    expected_labels = {record[0] for record in source_records}
    stale = [
        actor
        for label, actor in actors_by_label.items()
        if label.startswith(NAV_MODIFIER_LABEL_PREFIX)
        and label not in expected_labels
    ]
    for actor in stale:
        actor_subsystem.destroy_actor(actor)

    created_count = 0
    reused_count = 0
    for label, source_index, source_object, transform in source_records:
        actor = actors_by_label.get(label)
        if actor and not isinstance(actor, unreal.KZNavModifierBox):
            raise RuntimeError(
                "Managed nav modifier label has the wrong class: " + label
            )
        if not actor:
            actor = actor_subsystem.spawn_actor_from_class(
                unreal.KZNavModifierBox,
                transform.translation,
                transform.rotation.rotator(),
            )
            if not actor:
                raise RuntimeError("Failed to spawn nav modifier: " + label)
            actor.set_actor_label(label, mark_dirty=True)
            actors_by_label[label] = actor
            created_count += 1
        else:
            reused_count += 1
        actor.set_actor_location(transform.translation, False, False)
        actor.set_actor_rotation(transform.rotation.rotator(), False)
        actor.set_actor_scale3d(transform.scale3d)
        actor.set_actor_enable_collision(True)
        set_folder(actor, NAV_MODIFIER_FOLDER)
        set_tags(
            actor,
            (
                "HeinMachSourceNavModifier",
                "Source_HeinMach_Chrcollision",
                "SourceIndex_{}".format(source_index),
                "NavArea_Null",
            ),
        )

    final = [
        actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor
        and actor.get_actor_label().startswith(NAV_MODIFIER_LABEL_PREFIX)
    ]
    if len(final) != len(source_records):
        raise RuntimeError(
            "Final NavModifier count mismatch: {}".format(len(final))
        )
    return {
        "source_count": len(source_records),
        "created_count": created_count,
        "reused_count": reused_count,
        "removed_stale_count": len(stale),
        "final_count": len(final),
        "source_box_half_extent_cm": 100.0,
        "area_class": "/Script/NavigationSystem.NavArea_Null",
        "transform_basis": "source BrushComponent RelativeLocation/Rotation/Scale3D",
    }


def restore_navigation_links(actor_subsystem, objects):
    actors_by_label = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor
    }
    direction_map = {
        "ENavLinkDirection::BothWays": unreal.NavLinkDirection.BOTH_WAYS,
        "ENavLinkDirection::LeftToRight": unreal.NavLinkDirection.LEFT_TO_RIGHT,
        "ENavLinkDirection::RightToLeft": unreal.NavLinkDirection.RIGHT_TO_LEFT,
    }
    source_records = []
    transform_cache = {}

    for source_index, source_object in enumerate(objects):
        if source_object.get("Type") not in ("NavLinkProxy", "xxNavLinkProxy"):
            continue
        properties = source_object.get("Properties") or {}
        point_links = properties.get("PointLinks") or []
        if len(point_links) != 1:
            raise RuntimeError(
                "Expected one point link on source proxy {}: found {}".format(
                    source_index, len(point_links)
                )
            )
        root_index = local_index(properties.get("RootComponent"))
        if root_index is None:
            raise RuntimeError(
                "Source NavLinkProxy has no root: {}".format(source_index)
            )
        transform = resolve_world_transform(objects, root_index, transform_cache)
        link = point_links[0]
        left = source_vector(link.get("Left"), ("X", "Y", "Z"), (0.0, 0.0, 0.0))
        right = source_vector(
            link.get("Right"), ("X", "Y", "Z"), (0.0, 0.0, 0.0)
        )
        source_direction = str(
            link.get("Direction", "ENavLinkDirection::BothWays")
        )
        if source_direction not in direction_map:
            raise RuntimeError(
                "Unsupported source nav-link direction: " + source_direction
            )
        label = "{}{}_{}".format(
            NAV_LINK_LABEL_PREFIX,
            source_index,
            source_object.get("Name", "NavLinkProxy"),
        )[:220]
        source_records.append(
            {
                "label": label,
                "source_index": source_index,
                "source_type": source_object.get("Type"),
                "source_name": source_object.get("Name"),
                "transform": transform,
                "left": left,
                "right": right,
                "source_direction": source_direction,
                "direction": direction_map[source_direction],
                "left_project_height": float(link.get("LeftProjectHeight", 0.0)),
                "max_fall_down_length": float(
                    link.get("MaxFallDownLength", 1000.0)
                ),
                "source_snap_radius": float(link.get("SnapRadius", 30.0)),
                "applied_snap_radius": float(
                    NAV_LINK_SNAP_RADIUS_OVERRIDES_CM.get(
                        source_index, link.get("SnapRadius", 30.0)
                    )
                ),
                "snap_height": float(link.get("SnapHeight", 50.0)),
                "use_snap_height": bool(link.get("bUseSnapHeight", False)),
                "snap_to_cheapest_area": bool(
                    link.get("bSnapToCheapestArea", True)
                ),
            }
        )

    if len(source_records) != 14:
        raise RuntimeError(
            "Expected 14 source NavLinkProxy actors, found {}".format(
                len(source_records)
            )
        )

    expected_labels = {record["label"] for record in source_records}
    stale = [
        actor
        for label, actor in actors_by_label.items()
        if label.startswith(NAV_LINK_LABEL_PREFIX) and label not in expected_labels
    ]
    for actor in stale:
        actor_subsystem.destroy_actor(actor)

    created_count = 0
    reused_count = 0
    report_links = []
    for record in source_records:
        label = record["label"]
        transform = record["transform"]
        actor = actors_by_label.get(label)
        if actor and not isinstance(actor, unreal.NavLinkProxy):
            raise RuntimeError("Managed nav-link label has the wrong class: " + label)
        if not actor:
            actor = actor_subsystem.spawn_actor_from_class(
                unreal.NavLinkProxy,
                transform.translation,
                transform.rotation.rotator(),
            )
            if not actor:
                raise RuntimeError("Failed to spawn source nav link: " + label)
            actor.set_actor_label(label, mark_dirty=True)
            actors_by_label[label] = actor
            created_count += 1
        else:
            reused_count += 1

        actor.set_actor_location(transform.translation, False, False)
        actor.set_actor_rotation(transform.rotation.rotator(), False)
        actor.set_actor_scale3d(transform.scale3d)
        actor.set_actor_enable_collision(False)

        link = unreal.NavigationLink()
        link.set_editor_property(
            "left",
            unreal.Vector(
                x=record["left"][0],
                y=record["left"][1],
                z=record["left"][2],
            ),
        )
        link.set_editor_property(
            "right",
            unreal.Vector(
                x=record["right"][0],
                y=record["right"][1],
                z=record["right"][2],
            ),
        )
        link.set_editor_property("direction", record["direction"])
        link.set_editor_property(
            "left_project_height", record["left_project_height"]
        )
        link.set_editor_property(
            "max_fall_down_length", record["max_fall_down_length"]
        )
        link.set_editor_property("snap_radius", record["applied_snap_radius"])
        link.set_editor_property("snap_height", record["snap_height"])
        link.set_editor_property("use_snap_height", record["use_snap_height"])
        link.set_editor_property(
            "snap_to_cheapest_area", record["snap_to_cheapest_area"]
        )
        actor.set_editor_property("point_links", [link])
        actor.set_editor_property("smart_link_is_relevant", False)
        set_folder(actor, NAV_LINKS_FOLDER)
        set_tags(
            actor,
            (
                "HeinMachSourceNavLink",
                "Source_HeinMach_Chrcollision",
                "SourceIndex_{}".format(record["source_index"]),
            ),
        )
        report_links.append(
            {
                "label": label,
                "source_index": record["source_index"],
                "source_type": record["source_type"],
                "source_name": record["source_name"],
                "actor_location_cm": [
                    float(transform.translation.x),
                    float(transform.translation.y),
                    float(transform.translation.z),
                ],
                "actor_rotation_degrees": [
                    float(transform.rotation.rotator().pitch),
                    float(transform.rotation.rotator().yaw),
                    float(transform.rotation.rotator().roll),
                ],
                "local_left_cm": record["left"],
                "local_right_cm": record["right"],
                "direction": record["source_direction"],
                "source_snap_radius_cm": record["source_snap_radius"],
                "applied_snap_radius_cm": record["applied_snap_radius"],
                "snap_radius_override_reason": (
                    "restored Recast edge is 31.4 cm from the exact source endpoint"
                    if record["source_index"] in NAV_LINK_SNAP_RADIUS_OVERRIDES_CM
                    else None
                ),
            }
        )

    final = [
        actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label().startswith(NAV_LINK_LABEL_PREFIX)
    ]
    if len(final) != len(source_records):
        raise RuntimeError(
            "Final source NavLinkProxy count mismatch: {}".format(len(final))
        )
    return {
        "source_count": len(source_records),
        "created_count": created_count,
        "reused_count": reused_count,
        "removed_stale_count": len(stale),
        "final_count": len(final),
        "transform_basis": "source PositionComponent transform plus local PointLinks",
        "links": report_links,
    }


def restore_automation_route_navigation_links(actor_subsystem):
    payload = load_json(AUTOMATION_ROUTE_NAV_COMPATIBILITY_PATH)
    records = payload.get("links", [])
    policy = payload.get("policy", {})
    if len(records) != 10:
        raise RuntimeError(
            "Expected 10 automation-route compatibility links, found {}".format(
                len(records)
            )
        )

    actors_by_label = {
        actor.get_actor_label(): actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor
    }
    expected_labels = {
        "{}{}_{}_{}".format(
            AUTOMATION_NAV_LINK_LABEL_PREFIX,
            int(record["source_action_index"]),
            int(record["source_segment"][0]),
            int(record["source_segment"][1]),
        )
        for record in records
    }
    stale = [
        actor
        for label, actor in actors_by_label.items()
        if label.startswith(AUTOMATION_NAV_LINK_LABEL_PREFIX)
        and label not in expected_labels
    ]
    for actor in stale:
        actor_subsystem.destroy_actor(actor)

    snap_radius = float(policy.get("snap_radius_cm", 50.0))
    max_fall_down_length = float(
        policy.get("max_fall_down_length_cm", 0.0)
    )
    created_count = 0
    reused_count = 0
    report_links = []
    for record in records:
        action_index = int(record["source_action_index"])
        from_index = int(record["source_segment"][0])
        to_index = int(record["source_segment"][1])
        label = "{}{}_{}_{}".format(
            AUTOMATION_NAV_LINK_LABEL_PREFIX,
            action_index,
            from_index,
            to_index,
        )
        start_values = record["restored_nav_from_cm"]
        end_values = record["restored_nav_to_cm"]
        start = unreal.Vector(
            x=float(start_values[0]),
            y=float(start_values[1]),
            z=float(start_values[2]),
        )
        end = unreal.Vector(
            x=float(end_values[0]),
            y=float(end_values[1]),
            z=float(end_values[2]),
        )
        actor = actors_by_label.get(label)
        if actor and not isinstance(actor, unreal.NavLinkProxy):
            raise RuntimeError(
                "Managed automation-route nav-link label has the wrong class: "
                + label
            )
        if not actor:
            actor = actor_subsystem.spawn_actor_from_class(
                unreal.NavLinkProxy,
                start,
                unreal.Rotator(),
            )
            if not actor:
                raise RuntimeError(
                    "Failed to spawn automation-route navigation link: " + label
                )
            actor.set_actor_label(label, mark_dirty=True)
            actors_by_label[label] = actor
            created_count += 1
        else:
            reused_count += 1

        actor.set_actor_location(start, False, False)
        actor.set_actor_rotation(unreal.Rotator(), False)
        actor.set_actor_scale3d(unreal.Vector(x=1.0, y=1.0, z=1.0))
        actor.set_actor_enable_collision(False)

        link = unreal.NavigationLink()
        link.set_editor_property("left", unreal.Vector())
        link.set_editor_property(
            "right",
            unreal.Vector(
                x=float(end.x - start.x),
                y=float(end.y - start.y),
                z=float(end.z - start.z),
            ),
        )
        link.set_editor_property(
            "direction", unreal.NavLinkDirection.LEFT_TO_RIGHT
        )
        link.set_editor_property("left_project_height", 0.0)
        link.set_editor_property("max_fall_down_length", max_fall_down_length)
        link.set_editor_property("snap_radius", snap_radius)
        actor.set_editor_property("point_links", [link])
        actor.set_editor_property("smart_link_is_relevant", False)
        set_folder(actor, NAV_LINKS_FOLDER)
        set_tags(
            actor,
            (
                "HeinMachAutomationRouteNavCompatibility",
                "SourceAction_{}".format(action_index),
                "SourceSegment_{}_{}".format(from_index, to_index),
            ),
        )
        report_links.append(
            {
                "label": label,
                "source_action_index": action_index,
                "source_action_name": record.get("source_action_name"),
                "source_segment": [from_index, to_index],
                "source_from_cm": record["source_from_cm"],
                "source_to_cm": record["source_to_cm"],
                "restored_nav_from_cm": start_values,
                "restored_nav_to_cm": end_values,
                "classification": record.get("classification"),
                "direction": "ENavLinkDirection::LeftToRight",
                "snap_radius_cm": snap_radius,
                "max_fall_down_length_cm": max_fall_down_length,
            }
        )

    final = [
        actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor
        and actor.get_actor_label().startswith(
            AUTOMATION_NAV_LINK_LABEL_PREFIX
        )
    ]
    if len(final) != len(records):
        raise RuntimeError(
            "Final automation-route navigation-link count mismatch: {}".format(
                len(final)
            )
        )
    return {
        "source_metadata": AUTOMATION_ROUTE_NAV_COMPATIBILITY_PATH,
        "source_count": len(records),
        "created_count": created_count,
        "reused_count": reused_count,
        "removed_stale_count": len(stale),
        "final_count": len(final),
        "links": report_links,
    }


def configure_tutorial_start(actor_subsystem):
    matches = [
        actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and actor.get_actor_label() == PLAYER_START_LABEL
    ]
    if len(matches) != 1 or not isinstance(matches[0], unreal.PlayerStart):
        raise RuntimeError(
            "Expected exactly one source tutorial PlayerStart: " + PLAYER_START_LABEL
        )
    actor = matches[0]
    location = unreal.Vector(
        x=TUTORIAL_START_LOCATION[0],
        y=TUTORIAL_START_LOCATION[1],
        z=TUTORIAL_START_LOCATION[2],
    )
    rotation = unreal.Rotator(
        pitch=TUTORIAL_START_ROTATION[0],
        yaw=TUTORIAL_START_ROTATION[1],
        roll=TUTORIAL_START_ROTATION[2],
    )
    actor.set_actor_location(location, False, False)
    actor.set_actor_rotation(rotation, False)
    try:
        actor.set_editor_property(
            "player_start_tag", unreal.Name("DualAxeSwordTutorial")
        )
    except Exception:
        pass
    actual_location = actor.get_actor_location()
    actual_rotation = actor.get_actor_rotation()
    return {
        "label": PLAYER_START_LABEL,
        "source_level": "HeinMach_Spawn_Main01",
        "source_name": "MISSION01_START",
        "source_location_cm": list(TUTORIAL_SOURCE_LOCATION),
        "restored_ground_surface_z_cm": TUTORIAL_GROUND_SURFACE_Z,
        "player_capsule_half_height_cm": TUTORIAL_PLAYER_CAPSULE_HALF_HEIGHT,
        "temporary_spawn_clearance_cm": TUTORIAL_SPAWN_CLEARANCE,
        "placement_basis": (
            "source XY + restored Pawn-profile ground Z + BP_Player capsule "
            "half-height + temporary slope clearance"
        ),
        "location_cm": [
            float(actual_location.x),
            float(actual_location.y),
            float(actual_location.z),
        ],
        "rotation_degrees": [
            float(actual_rotation.pitch),
            float(actual_rotation.yaw),
            float(actual_rotation.roll),
        ],
    }


def configure_game_mode(world):
    game_mode_class = unreal.EditorAssetLibrary.load_blueprint_class(GAME_MODE_ASSET)
    if not game_mode_class:
        raise RuntimeError("Unable to load map GameMode class: " + GAME_MODE_ASSET)
    world_settings = world.get_world_settings()
    world_settings.modify()
    world_settings.set_editor_property("default_game_mode", game_mode_class)
    return game_mode_class.get_path_name()


def main():
    for required_path in (
        SOURCE_COLLISION_JSON,
        ROOT_AUDIT_PATH,
        ROOT_AUDIT_SCRIPT,
        AUTOMATION_ROUTE_NAV_COMPATIBILITY_PATH,
        *EXCLUSION_PATHS,
    ):
        if not os.path.isfile(required_path):
            raise RuntimeError("Required playability input is missing: " + required_path)

    objects = load_json(SOURCE_COLLISION_JSON)
    root_payload = load_json(ROOT_AUDIT_PATH)
    if root_payload.get("status") != "audited":
        raise RuntimeError("Root-template report is not in audited state")

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Unable to load HeinMach map: " + MAP_PATH)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        raise RuntimeError("HeinMach editor world is not active")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

    tutorial_start = configure_tutorial_start(actor_subsystem)
    game_mode_class = configure_game_mode(world)
    route_collision = restore_route_walls(actor_subsystem, objects)
    navigation_bounds = restore_navigation_bounds(actor_subsystem, objects)
    navigation_modifiers = restore_navigation_modifiers(actor_subsystem, objects)
    navigation_links = restore_navigation_links(actor_subsystem, objects)
    automation_route_navigation_links = (
        restore_automation_route_navigation_links(actor_subsystem)
    )
    terrain_collision = restore_terrain_collision(actor_subsystem)
    prop_collision = restore_prop_collision(actor_subsystem, root_payload)

    try:
        unreal.SystemLibrary.execute_console_command(world, "RebuildNavigation")
        navigation_rebuild_requested = True
    except Exception as exception:
        log("Navigation rebuild command was unavailable: {}".format(exception))
        navigation_rebuild_requested = False

    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save playable HeinMach map")

    report = {
        "status": "restored",
        "map_path": MAP_PATH,
        "source_collision_json": SOURCE_COLLISION_JSON,
        "source_root_audit": ROOT_AUDIT_PATH,
        "tutorial_start": tutorial_start,
        "game_mode_class": game_mode_class,
        "route_collision": route_collision,
        "navigation_bounds": navigation_bounds,
        "navigation_modifiers": navigation_modifiers,
        "navigation_links": navigation_links,
        "automation_route_navigation_links": automation_route_navigation_links,
        "terrain_collision": terrain_collision,
        "prop_collision": prop_collision,
        "navigation_rebuild_requested": navigation_rebuild_requested,
        "map_saved": True,
    }
    write_json(REPORT_PATH, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == "__main__":
    try:
        main()
    except Exception as exception:
        write_json(
            REPORT_PATH,
            {
                "status": "failed",
                "error": str(exception),
                "traceback": traceback.format_exc(),
            },
        )
        raise
