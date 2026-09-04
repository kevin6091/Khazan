"""Inspect USD-created material instances for source-identifying metadata."""

import json
import os

import unreal


REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_UE_Material_Metadata_Probe.json",
)

CANDIDATES = [
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/CorrectedSourceAssets/HeinMach_StaticMeshLibrary_Corrected/Materials/MI_WM_MCN_House_Base_54.MI_WM_MCN_House_Base_54",
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/CorrectedSourceAssets/HeinMach_StaticMeshLibrary_Corrected/Materials/MI_WM_WOD_Ground_Stone_4.MI_WM_WOD_Ground_Stone_4",
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/CorrectedSourceAssets/HeinMach_StaticMeshLibrary_Corrected/Materials/MI_WM_WOD_Ground_VertexPainter_4.MI_WM_WOD_Ground_VertexPainter_4",
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/CorrectedSourceAssets/HeinMach_StaticMeshLibrary_Corrected/Materials/MI_WM_COM_Mushroom_Small_0.MI_WM_COM_Mushroom_Small_0",
]


def serializable(value):
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [serializable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): serializable(item) for key, item in value.items()}
    if hasattr(value, "get_path_name"):
        return value.get_path_name()
    return str(value)


def call_if_available(target, name, *args):
    function = getattr(target, name, None)
    if function is None:
        return {"available": False}
    try:
        value = function(*args)
        if not isinstance(value, (str, bytes, dict, list, tuple)):
            try:
                value = list(value)
            except Exception:
                pass
        return {"available": True, "value": serializable(value)}
    except Exception as exception:
        return {"available": True, "error": str(exception)}


def main():
    library = unreal.MaterialEditingLibrary
    records = []
    for asset_path in CANDIDATES:
        material = unreal.EditorAssetLibrary.load_asset(asset_path)
        record = {
            "asset": asset_path,
            "loaded": bool(material),
            "metadata": serializable(
                unreal.EditorAssetLibrary.get_metadata_tag_values(material)
                if material
                else {}
            ),
        }
        if material:
            texture_names = call_if_available(library, "get_texture_parameter_names", material)
            scalar_names = call_if_available(library, "get_scalar_parameter_names", material)
            vector_names = call_if_available(library, "get_vector_parameter_names", material)
            for result in (texture_names, scalar_names, vector_names):
                if result.get("available") and "value" in result:
                    try:
                        result["value"] = list(result["value"])
                    except Exception:
                        pass
            record["texture_parameter_names"] = texture_names
            record["scalar_parameter_names"] = scalar_names
            record["vector_parameter_names"] = vector_names

            texture_values = {}
            for name in texture_names.get("value", []) if isinstance(texture_names, dict) else []:
                texture_values[str(name)] = call_if_available(
                    library,
                    "get_material_instance_texture_parameter_value",
                    material,
                    name,
                )
            record["texture_values"] = texture_values
            record["parent"] = serializable(material.get_editor_property("parent"))
            record["base_property_overrides"] = str(
                material.get_editor_property("base_property_overrides")
            )
        records.append(record)

    payload = {
        "material_editing_library_methods": sorted(
            name for name in dir(library) if "parameter" in name.lower()
        ),
        "records": records,
    }
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
    unreal.log("KHAZAN_HEINMACH_MATERIAL_PROBE: RESULT report=" + REPORT_PATH)


if __name__ == "__main__":
    main()
