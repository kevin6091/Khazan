"""Probe UE MeshDescription winding for native and imported static meshes."""

import json
import os
import traceback

import unreal


SOURCE_ASSET_ROOT = (
    "/Game/_Art/Kazan/Environment/HeinMach/Reconstructed/SourceAssets"
)
REPORT_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportReports",
    "HeinMach_UE_MeshOrientation_Probe.json",
)


def write_report(payload):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def vector_tuple(value):
    return float(value.x), float(value.y), float(value.z)


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def signed_volume(mesh):
    dynamic_mesh = unreal.DynamicMesh()
    copy_result = unreal.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(
        mesh,
        dynamic_mesh,
        unreal.GeometryScriptCopyMeshFromAssetOptions(),
        unreal.GeometryScriptMeshReadLOD(),
    )
    if isinstance(copy_result, tuple) and copy_result:
        dynamic_mesh = copy_result[0]
    elif isinstance(copy_result, unreal.DynamicMesh):
        dynamic_mesh = copy_result
    if not dynamic_mesh:
        raise RuntimeError("Geometry Script did not return a DynamicMesh")
    triangle_count = int(dynamic_mesh.get_triangle_count())
    volume = 0.0
    sampled = 0
    for index in range(triangle_count):
        result = unreal.GeometryScript_MeshQueries.get_triangle_positions(
            dynamic_mesh, index
        )
        positions = [
            value
            for value in (result if isinstance(result, tuple) else ())
            if hasattr(value, "x") and hasattr(value, "y") and hasattr(value, "z")
        ]
        if len(positions) != 3:
            continue
        p0, p1, p2 = (vector_tuple(position) for position in positions)
        volume += dot(p0, cross(p1, p2)) / 6.0
        sampled += 1
    return {
        "triangle_count": triangle_count,
        "sampled_triangle_count": sampled,
        "signed_volume": volume,
    }


def main():
    mesh_folder = SOURCE_ASSET_ROOT + "/HeinMach_StaticMeshLibrary/StaticMeshes/"
    candidates = [
        "/Engine/BasicShapes/Cube.Cube",
        mesh_folder + "SM_WP_SKL_Rock_Big_003.SM_WP_SKL_Rock_Big_003",
        mesh_folder + "SM_WP_WOD_Cave_Base_005.SM_WP_WOD_Cave_Base_005",
        mesh_folder + "SM_WP_COM_Mushroom_Small_005.SM_WP_COM_Mushroom_Small_005",
        mesh_folder + "SM_WP_BANTU_House_Base_001.SM_WP_BANTU_House_Base_001",
        mesh_folder + "SM_WP_BANTU_Pillar_Stone_001.SM_WP_BANTU_Pillar_Stone_001",
    ]

    records = []
    for asset_path in candidates:
        mesh = unreal.EditorAssetLibrary.load_asset(asset_path)
        record = {"asset": asset_path}
        try:
            record.update(signed_volume(mesh))
            record["status"] = "audited"
        except Exception as exception:
            record["status"] = "failed"
            record["error"] = str(exception)
            record["traceback"] = traceback.format_exc()
            try:
                record["geometry_asset_utils_available"] = hasattr(
                    unreal, "GeometryScript_AssetUtils"
                )
                record["geometry_mesh_queries_available"] = hasattr(
                    unreal, "GeometryScript_MeshQueries"
                )
                record["mesh_loaded"] = bool(mesh)
            except Exception as probe_exception:
                record["probe_error"] = str(probe_exception)
        records.append(record)

    report = {"status": "probed", "records": records}
    write_report(report)
    unreal.log(
        "KHAZAN_HEINMACH_ORIENTATION_PROBE: RESULT records={} failures={} report={}".format(
            len(records),
            sum(record["status"] == "failed" for record in records),
            REPORT_PATH,
        )
    )


if __name__ == "__main__":
    main()
