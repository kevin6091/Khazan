"""Read exact FModel Landscape triangles under the source camera anchors.

This is an offline diagnostic, not a collision/navmesh or gameplay simulation.
It distinguishes real terrain above an anchor from misleading distant backdrop
bounds. Negative source USD Y is converted back to Unreal before sampling.
"""

import ast
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
METADATA = ROOT / "Content/_Art/Kazan/Environment/StormPass/Metadata"


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def mesh_arrays(path):
    points, indices = None, None
    with open(path, encoding="utf-8-sig") as stream:
        for line in stream:
            line = line.strip()
            if line.startswith("point3f[] points ="):
                points = ast.literal_eval(line.split("=", 1)[1].strip())
            elif line.startswith("int[] faceVertexIndices ="):
                indices = ast.literal_eval(line.split("=", 1)[1].strip())
            if points is not None and indices is not None:
                break
    if not points or not indices:
        raise RuntimeError("Missing source mesh arrays: " + path)
    return [(x, -y, z) for x, y, z in points], indices


def surface_at(points, indices, x, y):
    for i in range(0, len(indices), 3):
        a, b, c = (points[n] for n in indices[i:i + 3])
        if x < min(a[0], b[0], c[0]) or x > max(a[0], b[0], c[0]):
            continue
        if y < min(a[1], b[1], c[1]) or y > max(a[1], b[1], c[1]):
            continue
        den = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(den) < 1e-10:
            continue
        u = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / den
        v = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / den
        w = 1 - u - v
        if min(u, v, w) >= -1e-6:
            return u * a[2] + v * b[2] + w * c[2]
    return None


def main():
    anchors = read(METADATA / "StormPass_PlayableCameraAnchors.json")["anchors"]
    landscape = read(METADATA / "StormPass_LandscapeComponents.json")
    cache, rows = {}, []
    for anchor in anchors:
        x, y, z = anchor["location_cm"]
        surfaces = []
        for level in landscape["levels"]:
            t = level["root_transform"]
            p, s = t["location_cm"], t["scale"]
            lx, ly = (x - p["x"]) / s["x"], (y - p["y"]) / s["y"]
            for component in level["components"]:
                base, q = component["section_base"], component["component_size_quads"]
                if not (base["x"] <= lx <= base["x"] + q and base["y"] <= ly <= base["y"] + q):
                    continue
                source = component["source_usd"]
                if source not in cache:
                    cache[source] = mesh_arrays(source)
                height = surface_at(*cache[source], lx, ly)
                if height is not None:
                    world_z = p["z"] + height * s["z"]
                    surfaces.append({"source_level": level["source_level"], "component": component["component_name"],
                                     "surface_z_cm": world_z, "anchor_height_above_landscape_cm": z - world_z,
                                     "landscape_above_anchor": world_z > z + 1})
        rows.append({"anchor": anchor["source_name"], "location_cm": anchor["location_cm"], "landscape_samples": surfaces})
    payload = {"stage": "source_landscape_geometry", "source_triangle_files_sampled": len(cache), "anchors": rows,
               "limitation": "Authored walkways and cave floors can be separate static meshes. A Landscape height is not the playable ground by itself."}
    target = ROOT / "Saved/ImportReports/StormPass_RouteLandscapeGeometry_20260907.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in rows:
        print(row["anchor"], [(s["component"], round(s["anchor_height_above_landscape_cm"], 2)) for s in row["landscape_samples"]])
    return payload


if __name__ == "__main__":
    main()
