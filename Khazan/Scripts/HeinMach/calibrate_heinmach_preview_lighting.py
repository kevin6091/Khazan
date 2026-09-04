"""Calibrate the reversible HeinMach preview lighting for visual inspection.

The old preview sun used intensity 4 lux and relied on histogram exposure near
-8 EV, which clipped Lumen/real-time SkyLight data and exaggerated the malformed
USD materials.  This keeps the existing light direction and locks a stable,
inspection-oriented exposure.  Fog actors and Fog materials are not modified.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
BACKUP_MAP_PATH = (
    "/Game/_Art/Kazan/Environment/HeinMach/Maps/"
    "L_HeinMach_Environment_PreMaterialLightingFix"
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_PreviewLighting_Calibration.json",
)
FOG_LABEL_PREFIX = "HM_FogSheet_"
SOURCE_LIGHT_LABEL_PREFIX = "HM_SourceLight_"
ROUTE_FILL_LABEL_PREFIX = "HM_PreviewRouteFill_"
SUN_INTENSITY_LUX = 20000.0
LOCKED_EXPOSURE_EV100 = 4.0
ROUTE_FILL_FOLDER = "HeinMach/Reconstructed/PreviewLighting/RouteFill"
RECONSTRUCT_SCRIPT = os.path.join(
    SCRIPT_DIR, "reconstruct_heinmach_environment.py"
)
ROUTE_FILL_SPECS = (
    {
        "tag": "Tomb_01",
        "location": (12175.4369937, 16251.5777747, 983.55811),
        "intensity_lumens": 12000.0,
        "attenuation_radius_cm": 3000.0,
        "color_linear": (0.88, 0.91, 1.0),
    },
    {
        "tag": "Tomb_02",
        "location": (28098.0115482, 8071.4278110, -488.84407),
        "intensity_lumens": 12000.0,
        "attenuation_radius_cm": 3000.0,
        "color_linear": (0.55, 0.65, 1.0),
    },
    {
        "tag": "Tomb_03",
        "location": (22895.1630317, -2689.8031882, 97.37791),
        "intensity_lumens": 12000.0,
        "attenuation_radius_cm": 3000.0,
        "color_linear": (1.0, 0.78, 0.66),
    },
)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def actor_transform_record(actor):
    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    scale = actor.get_actor_scale3d()
    return {
        "label": actor.get_actor_label(),
        "location": [location.x, location.y, location.z],
        "rotation": [rotation.pitch, rotation.yaw, rotation.roll],
        "scale": [scale.x, scale.y, scale.z],
    }


def fog_signature(actors):
    records = sorted(
        (
            actor_transform_record(actor)
            for actor in actors
            if actor.get_actor_label().startswith(FOG_LABEL_PREFIX)
        ),
        key=lambda item: item["label"],
    )
    encoded = json.dumps(records, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return {"count": len(records), "sha256": hashlib.sha256(encoded).hexdigest()}


def load_reconstruct_module():
    spec = importlib.util.spec_from_file_location(
        "khazan_heinmach_source_light_helpers", RECONSTRUCT_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load source-light reconstruction helpers")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reset_source_lights(actors):
    """Undo exploratory light edits and reapply the cached FModel light data."""
    reconstruct = load_reconstruct_module()
    level_data = reconstruct.load_json(reconstruct.LEVEL_DATA_PATH)
    records = [
        record
        for record in level_data.get("lights", [])
        if record.get("source_level") == reconstruct.SOURCE_LIGHT_LEVEL
        and record.get("actor_type") in ("xxPointLight", "xxSpotLight")
    ]
    by_label = {
        actor.get_actor_label(): actor
        for actor in actors
        if actor.get_actor_label().startswith(SOURCE_LIGHT_LABEL_PREFIX)
    }
    if len(records) != 89 or len(by_label) != 89:
        raise RuntimeError("Expected the 89 cached/source light actors")
    failures = []
    reset = []
    for record in records:
        label = SOURCE_LIGHT_LABEL_PREFIX + str(record.get("actor_name", "Unknown"))
        actor = by_label.get(label)
        if not actor:
            raise RuntimeError("Source light actor is missing: " + label)
        component_class = (
            unreal.SpotLightComponent
            if record.get("actor_type") == "xxSpotLight"
            else unreal.PointLightComponent
        )
        component = actor.get_component_by_class(component_class)
        if not component:
            raise RuntimeError("Source light component is missing: " + label)
        lumens = reconstruct.apply_source_light(
            component,
            reconstruct.source_light_component_data(record),
            failures,
        )
        reset.append(
            {
                "label": label,
                "intensity_lumens": lumens,
                "attenuation_radius_cm": float(
                    component.get_editor_property("attenuation_radius")
                ),
            }
        )
    if failures:
        raise RuntimeError("Source-light reset property failures: {}".format(len(failures)))
    return reset


def set_actor_folder(actor, path):
    try:
        actor.set_folder_path(path)
    except Exception:
        actor.set_editor_property("folder_path", path)


def create_route_fill_lights(actor_subsystem, actors):
    existing = {
        actor.get_actor_label(): actor
        for actor in actors
        if actor.get_actor_label().startswith(ROUTE_FILL_LABEL_PREFIX)
    }
    expected = {ROUTE_FILL_LABEL_PREFIX + spec["tag"] for spec in ROUTE_FILL_SPECS}
    unexpected = sorted(set(existing) - expected)
    if unexpected:
        raise RuntimeError("Unexpected managed route-fill light: " + unexpected[0])

    results = []
    for spec in ROUTE_FILL_SPECS:
        label = ROUTE_FILL_LABEL_PREFIX + spec["tag"]
        actor = existing.get(label)
        created = actor is None
        if created:
            actor = actor_subsystem.spawn_actor_from_class(
                unreal.PointLight,
                unreal.Vector(*spec["location"]),
                unreal.Rotator(),
            )
            if not actor:
                raise RuntimeError("Failed to create route-fill light: " + label)
            actor.set_actor_label(label, mark_dirty=True)
        actor.set_actor_location(unreal.Vector(*spec["location"]), False, False)
        set_actor_folder(actor, ROUTE_FILL_FOLDER)
        component = actor.get_component_by_class(unreal.PointLightComponent)
        component.set_editor_property("mobility", unreal.ComponentMobility.MOVABLE)
        component.set_editor_property("intensity", spec["intensity_lumens"])
        component.set_editor_property(
            "attenuation_radius", spec["attenuation_radius_cm"]
        )
        component.set_editor_property("cast_shadows", False)
        component.set_editor_property("use_inverse_squared_falloff", True)
        color = spec["color_linear"]
        component.set_light_color(
            unreal.LinearColor(color[0], color[1], color[2], 1.0), False
        )
        results.append({"label": label, "created": created, **spec})
    return results


def main():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach environment map")

    backup_created = False
    if not unreal.EditorAssetLibrary.does_asset_exist(BACKUP_MAP_PATH):
        if not unreal.EditorAssetLibrary.duplicate_asset(MAP_PATH, BACKUP_MAP_PATH):
            raise RuntimeError("Failed to create preview-lighting backup map")
        unreal.EditorAssetLibrary.save_asset(
            BACKUP_MAP_PATH, only_if_is_dirty=False
        )
        backup_created = True

    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = list(actor_subsystem.get_all_level_actors())
    fog_before = fog_signature(actors)
    if fog_before["count"] != 50:
        raise RuntimeError("Fog boundary count changed")

    sun = next((actor for actor in actors if actor.get_actor_label() == "HM_PreviewSun"), None)
    post = next(
        (actor for actor in actors if actor.get_actor_label() == "HM_PreviewPostProcess"),
        None,
    )
    if not sun or not post:
        raise RuntimeError("Preview lighting actors are missing")

    source_light_reset = reset_source_lights(actors)
    route_fill_lights = create_route_fill_lights(actor_subsystem, actors)

    sun_component = sun.get_component_by_class(unreal.DirectionalLightComponent)
    if not sun_component:
        raise RuntimeError("Preview sun component is missing")
    old_sun_intensity = float(sun_component.get_editor_property("intensity"))
    sun_component.set_editor_property("intensity", SUN_INTENSITY_LUX)

    settings = post.get_editor_property("settings")
    old_exposure = {
        "min": float(settings.get_editor_property("auto_exposure_min_brightness")),
        "max": float(settings.get_editor_property("auto_exposure_max_brightness")),
        "bias": float(settings.get_editor_property("auto_exposure_bias")),
    }
    settings.set_editor_property("override_auto_exposure_min_brightness", True)
    settings.set_editor_property("override_auto_exposure_max_brightness", True)
    settings.set_editor_property("override_auto_exposure_bias", True)
    settings.set_editor_property(
        "auto_exposure_min_brightness", LOCKED_EXPOSURE_EV100
    )
    settings.set_editor_property(
        "auto_exposure_max_brightness", LOCKED_EXPOSURE_EV100
    )
    settings.set_editor_property("auto_exposure_bias", 0.0)
    post.set_editor_property("settings", settings)

    fog_after = fog_signature(actors)
    if fog_after != fog_before:
        raise RuntimeError("Fog transform signature changed during lighting calibration")
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save HeinMach environment map")

    payload = {
        "status": "calibrated",
        "map_path": MAP_PATH,
        "backup_map_path": BACKUP_MAP_PATH,
        "backup_created": backup_created,
        "sun": {
            "old_intensity": old_sun_intensity,
            "new_intensity_lux": SUN_INTENSITY_LUX,
            "rotation_preserved": True,
        },
        "exposure": {
            "old": old_exposure,
            "locked_ev100": LOCKED_EXPOSURE_EV100,
            "bias": 0.0,
        },
        "source_lights": {
            "reset_from_cached_fmodel_metadata_count": len(source_light_reset),
            "policy": "Source positions, colors, radii and intensities remain the reconstruction values; exploratory scaling was reset.",
        },
        "route_fill_lights": {
            "count": len(route_fill_lights),
            "policy": "Movable, shadowless inspection lights at the three enclosed Tomb checkpoints; original source lights remain unchanged.",
            "lights": route_fill_lights,
        },
        "fog_boundary": {
            "policy": "Fog actors and Fog materials were not modified",
            "signature_before": fog_before,
            "signature_after": fog_after,
        },
    }
    write_json(REPORT_PATH, payload)
    print(json.dumps({"report": REPORT_PATH, "status": "calibrated"}))
    return payload


if __name__ == "__main__":
    main()
