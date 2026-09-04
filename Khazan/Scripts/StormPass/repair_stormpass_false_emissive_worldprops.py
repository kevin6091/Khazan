"""Disable false USD-preview emissive on five StormPass world-prop materials.

FModel metadata resolves every target to ``WM_BBQProp_Base`` and the cooked
``M_WorldProp`` parameter cache declares ``EmissiveOn=0``.  The generic USD
conversion nevertheless enabled ``UseEmissiveColorTexture`` because a dormant
``Tex_E`` override existed.  This pass changes only that preview switch; source
textures, material bindings, actors, and transforms stay untouched.
"""

from __future__ import annotations

import hashlib
import json
import os
import traceback

import unreal


PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAP_PATH = "/Game/_Art/Kazan/Environment/StormPass/Maps/L_StormPass_Environment"
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_FalseEmissiveWorldProp_Repair.json",
)
SOURCE_ROOT = os.path.join(
    os.path.expanduser("~"),
    "Desktop",
    "\uce74\uc794",
    "Exports",
    "BBQ",
    "Content",
    "Art",
    "World",
    "World_Material",
    "Prop",
    "Material",
)
MASTER_SOURCE_PATH = os.path.join(
    os.path.expanduser("~"),
    "Desktop",
    "\uce74\uc794",
    "Exports",
    "BBQ",
    "Content",
    "BaseMaterials",
    "WorldProp",
    "WorldPropMaster",
    "M_WorldProp.json",
)
INSTANCE_ROOT = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/OverrideMaterials/"
    "ActorOverrides/Materials"
)
BACKUP_ROOT = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/Backups/"
    "PreFalseEmissiveWorldPropRepair_20260904/Materials"
)
EXPECTED_ACTOR_TOTAL = 14408
MATERIAL_COUNTS = {
    "WM_CTR_Tent_Mid_002": 2,
    "WM_Castle_Ceiling_Base_002_b": 12,
    "WM_Castle_Floor_WMarble_001_01": 4,
    "WM_Castle_Pillar_Gold_001": 16,
    "WM_Castle_Walldeco_Golden_001": 10,
}
EXPECTED_SLOT_TOTAL = sum(MATERIAL_COUNTS.values())
EXPECTED_SOURCE_PARENT = (
    "BBQ/Content/Art/World/World_Material/Prop/Material/Base/WM_BBQProp_Base.0"
)


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def normalized_asset_path(value):
    return value.get_path_name().rsplit(".", 1)[0] if value else None


def material_path(name):
    return INSTANCE_ROOT + "/MI_" + name


def transform_signature(actors):
    rows = []
    for actor in sorted(actors, key=lambda value: value.get_actor_label()):
        location = actor.get_actor_location()
        rotation = actor.get_actor_rotation().quaternion()
        scale = actor.get_actor_scale3d()
        values = [float(rotation.x), float(rotation.y), float(rotation.z), float(rotation.w)]
        length = sum(value * value for value in values) ** 0.5
        if length <= 1.0e-12:
            raise RuntimeError("Zero actor quaternion: " + actor.get_actor_label())
        values = [value / length for value in values]
        for value in values:
            if abs(value) > 1.0e-12:
                if value < 0.0:
                    values = [-item for item in values]
                break
        rows.append(
            "{}|{}|{:.6f},{:.6f},{:.6f}|{:.9f},{:.9f},{:.9f},{:.9f}|"
            "{:.9f},{:.9f},{:.9f}".format(
                actor.get_actor_label(),
                actor.get_class().get_name(),
                location.x,
                location.y,
                location.z,
                *values,
                scale.x,
                scale.y,
                scale.z,
            )
        )
    payload = "\n".join(rows).encode("utf-8")
    return {
        "count": len(rows),
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def source_record(name):
    exports = load_json(os.path.join(SOURCE_ROOT, name + ".json"))
    material = next(
        (
            row
            for row in exports
            if row.get("Type") == "MaterialInstanceConstant"
            and row.get("Name") == name
        ),
        None,
    )
    if not material:
        raise RuntimeError("Missing FModel source material: " + name)
    properties = material.get("Properties") or {}
    parent = ((properties.get("Parent") or {}).get("ObjectPath"))
    if parent != EXPECTED_SOURCE_PARENT:
        raise RuntimeError(name + " source parent changed: " + str(parent))
    scalar_values = {
        row.get("ParameterInfo", {}).get("Name"): float(row.get("ParameterValue", 0.0))
        for row in properties.get("ScalarParameterValues", [])
        if row.get("ParameterInfo", {}).get("Name")
    }
    if scalar_values.get("EmissiveOn", 0.0) != 0.0:
        raise RuntimeError(name + " explicitly enables source emissive")
    return {
        "source_json": os.path.join(SOURCE_ROOT, name + ".json"),
        "parent": parent,
        "emissive_on_override": scalar_values.get("EmissiveOn"),
        "covering_emissive_flow_uv_scale": scalar_values.get(
            "CoveringEmissiveFlowUVScale"
        ),
    }


def master_emissive_defaults():
    exports = load_json(MASTER_SOURCE_PATH)
    material = next(
        row for row in exports if row.get("Type") == "Material" and row.get("Name") == "M_WorldProp"
    )
    parameters = material["Properties"]["CachedExpressionData"]["Parameters"]
    infos = parameters["RuntimeEntries"]["ParameterInfos"]
    values = parameters["ScalarValues"]
    defaults = {
        info.get("Name"): float(values[index])
        for index, info in enumerate(infos)
        if info.get("Name") in {"EmissiveOn", "EmissiveAmount", "BaseEmissiveAmount"}
    }
    expected = {
        "EmissiveOn": 0.0,
        "EmissiveAmount": 1.0,
        "BaseEmissiveAmount": 1.0,
    }
    if defaults != expected:
        raise RuntimeError("M_WorldProp emissive defaults changed: " + str(defaults))
    return defaults


def slot_inventory(actor_subsystem):
    expected = {material_path(name): name for name in MATERIAL_COUNTS}
    counts = {name: 0 for name in MATERIAL_COUNTS}
    for actor in actor_subsystem.get_all_level_actors():
        if not actor:
            continue
        for component in actor.get_components_by_class(unreal.StaticMeshComponent):
            for slot in range(int(component.get_num_materials())):
                material = component.get_material(slot)
                name = expected.get(normalized_asset_path(material))
                if name:
                    counts[name] += 1
    return {"counts": counts, "total": sum(counts.values())}


def backup_materials(materials):
    if not unreal.EditorAssetLibrary.does_directory_exist(BACKUP_ROOT):
        unreal.EditorAssetLibrary.make_directory(BACKUP_ROOT)
    rows = []
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    for name, material in materials.items():
        backup_name = "MI_" + name + "_PreFalseEmissiveWorldPropRepair"
        backup_path = BACKUP_ROOT + "/" + backup_name
        created = False
        if not unreal.EditorAssetLibrary.does_asset_exist(backup_path):
            backup = asset_tools.duplicate_asset(
                backup_name, BACKUP_ROOT, material
            )
            if not backup:
                raise RuntimeError("Failed to back up " + name)
            unreal.EditorAssetLibrary.save_loaded_asset(backup, only_if_is_dirty=False)
            created = True
        rows.append(
            {"source": material.get_path_name(), "backup": backup_path, "created": created}
        )
    return rows


def emissive_override(material):
    direct = None
    for row in material.get_editor_property("scalar_parameter_values"):
        info = row.get_editor_property("parameter_info")
        if str(info.get_editor_property("name")) == "UseEmissiveColorTexture":
            direct = float(row.get_editor_property("parameter_value"))
            break
    effective = float(
        unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(
            material, "UseEmissiveColorTexture"
        )
    )
    return {"direct": direct, "effective": effective}


def set_false_emissive_off(material):
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
        material, "UseEmissiveColorTexture", 0.0
    )
    unreal.MaterialEditingLibrary.update_material_instance(material)
    current = emissive_override(material)
    if current["direct"] == 0.0 and current["effective"] == 0.0:
        return

    values = list(material.get_editor_property("scalar_parameter_values"))
    found = False
    for value in values:
        info = value.get_editor_property("parameter_info")
        if str(info.get_editor_property("name")) == "UseEmissiveColorTexture":
            value.set_editor_property("parameter_value", 0.0)
            found = True
    if not found:
        raise RuntimeError(
            material.get_name() + " has no UseEmissiveColorTexture override"
        )
    material.set_editor_property("scalar_parameter_values", values)
    unreal.MaterialEditingLibrary.update_material_instance(material)
    current = emissive_override(material)
    if current["direct"] != 0.0 or current["effective"] != 0.0:
        raise RuntimeError("False emissive readback failed: " + material.get_name())


def main(apply_changes=False):
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    if not level_subsystem.load_level(MAP_PATH):
        raise RuntimeError("Failed to load StormPass")
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors_before = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    signature_before = transform_signature(actors_before)
    if signature_before["count"] != EXPECTED_ACTOR_TOTAL:
        raise RuntimeError("Unexpected StormPass actor count")

    defaults = master_emissive_defaults()
    sources = {name: source_record(name) for name in MATERIAL_COUNTS}
    materials = {}
    before = {}
    for name in MATERIAL_COUNTS:
        material = unreal.EditorAssetLibrary.load_asset(material_path(name))
        if not isinstance(material, unreal.MaterialInstanceConstant):
            raise RuntimeError("Missing reconstructed material: " + name)
        materials[name] = material
        before[name] = emissive_override(material)

    slots_before = slot_inventory(actor_subsystem)
    if slots_before["counts"] != MATERIAL_COUNTS or slots_before["total"] != EXPECTED_SLOT_TOTAL:
        raise RuntimeError("World-prop slot inventory changed")

    backups = []
    if apply_changes:
        backups = backup_materials(materials)
        for name, material in materials.items():
            set_false_emissive_off(material)
            unreal.EditorAssetLibrary.set_metadata_tag(
                material,
                "KhazanFalseEmissiveRepair",
                "M_WorldProp EmissiveOn=0; dormant Tex_E retained",
            )
            unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)

    after = {name: emissive_override(material) for name, material in materials.items()}
    remaining = [
        name
        for name, values in after.items()
        if values["direct"] != 0.0 or values["effective"] != 0.0
    ]
    slots_after = slot_inventory(actor_subsystem)
    actors_after = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    signature_after = transform_signature(actors_after)
    if slots_after != slots_before:
        raise RuntimeError("Material bindings changed during false-emissive repair")
    if signature_after != signature_before:
        raise RuntimeError("Actor transforms changed during false-emissive repair")
    if apply_changes and remaining:
        raise RuntimeError("False emissive remains: " + ", ".join(remaining))

    report = {
        "status": "repaired" if apply_changes else "audited",
        "map_path": MAP_PATH,
        "decision": (
            "Five WM_BBQProp_Base children inherit M_WorldProp EmissiveOn=0. "
            "Only the erroneous USD-preview UseEmissiveColorTexture switch was disabled."
        ),
        "master_source_json": MASTER_SOURCE_PATH,
        "master_emissive_defaults": defaults,
        "source_records": sources,
        "counts": {
            "material": len(MATERIAL_COUNTS),
            "affected_slot": slots_before["total"],
            "actor": signature_before["count"],
        },
        "slot_inventory": slots_before,
        "emissive_before": before,
        "emissive_after": after,
        "candidate_materials": remaining if not apply_changes else [],
        "backups": backups,
        "transform_before": signature_before,
        "transform_after": signature_after,
        "validation_failures": remaining if apply_changes else [],
    }
    write_json(REPORT_PATH, report)
    print(
        "KHAZAN_STORMPASS_FALSE_EMISSIVE: status={} materials={} slots={} actors={} transform_sha={}".format(
            report["status"],
            report["counts"]["material"],
            report["counts"]["affected_slot"],
            report["counts"]["actor"],
            signature_after["sha256"],
        )
    )
    return report


if __name__ == "__main__":
    try:
        main(False)
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
