"""Audit FModel USDA mesh winding against authored vertex normals.

The script is independent from Unreal Python. It reads only the static-mesh
packages referenced by the HeinMach placement manifest and emits a compact
report that can be compared with the UE import audit.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FMODEL_ROOT = Path.home() / "Desktop" / "카잔"
MANIFEST_PATH = (
    PROJECT_ROOT
    / "Content"
    / "_Art"
    / "Kazan"
    / "Environment"
    / "HeinMach"
    / "Metadata"
    / "HeinMach_RenderableStaticMeshPlacements.json"
)
REPORT_PATH = (
    PROJECT_ROOT
    / "Saved"
    / "ImportReports"
    / "HeinMach_FModel_MeshOrientation_Audit.json"
)

ARRAY_RE_TEMPLATE = r"{declaration}\s*=\s*\[(.*?)\](?:\s*\(|\s*\n)"
TRIPLE_RE = re.compile(
    r"\(\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*\)"
)
INT_RE = re.compile(r"-?\d+")


def extract_array(text: str, declaration: str) -> str | None:
    match = re.search(
        ARRAY_RE_TEMPLATE.format(declaration=re.escape(declaration)),
        text,
        flags=re.DOTALL,
    )
    return match.group(1) if match else None


def triples(value: str | None) -> list[tuple[float, float, float]]:
    if not value:
        return []
    return [tuple(float(part) for part in match.groups()) for match in TRIPLE_RE.finditer(value)]


def integers(value: str | None) -> list[int]:
    return [int(item) for item in INT_RE.findall(value or "")]


def subtract(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def normalized(value):
    length = math.sqrt(dot(value, value))
    if length <= 1.0e-12:
        return None
    return (value[0] / length, value[1] / length, value[2] / length)


def audit_mesh(package: str) -> dict:
    source_path = FMODEL_ROOT.joinpath(*package.split("/")).with_suffix(".usda")
    text = source_path.read_text(encoding="utf-8", errors="replace")
    points = triples(extract_array(text, "point3f[] points"))
    normals = triples(extract_array(text, "normal3f[] normals"))
    counts = integers(extract_array(text, "int[] faceVertexCounts"))
    indices = integers(extract_array(text, "int[] faceVertexIndices"))

    offset = 0
    dot_positive = 0
    dot_negative = 0
    dot_near_zero = 0
    signed_volume = 0.0
    triangle_count = 0
    invalid_faces = 0

    for count in counts:
        face = indices[offset : offset + count]
        offset += count
        if count < 3 or any(index < 0 or index >= len(points) for index in face):
            invalid_faces += 1
            continue
        for corner in range(1, count - 1):
            vertex_indices = (face[0], face[corner], face[corner + 1])
            p0, p1, p2 = (points[index] for index in vertex_indices)
            face_normal = normalized(cross(subtract(p1, p0), subtract(p2, p0)))
            if face_normal is None:
                continue
            triangle_count += 1
            signed_volume += dot(p0, cross(p1, p2)) / 6.0

            if len(normals) == len(points):
                authored = normalized(
                    tuple(
                        sum(normals[index][axis] for index in vertex_indices) / 3.0
                        for axis in range(3)
                    )
                )
                if authored is not None:
                    agreement = dot(face_normal, authored)
                    if agreement > 1.0e-4:
                        dot_positive += 1
                    elif agreement < -1.0e-4:
                        dot_negative += 1
                    else:
                        dot_near_zero += 1

    orientation_match = re.search(r"uniform\s+token\s+orientation\s*=\s*\"([^\"]+)\"", text)
    return {
        "package": package,
        "source_path": str(source_path),
        "authored_orientation": orientation_match.group(1) if orientation_match else "rightHanded (USD default)",
        "point_count": len(points),
        "normal_count": len(normals),
        "face_count": len(counts),
        "triangle_count": triangle_count,
        "invalid_face_count": invalid_faces,
        "normal_winding_agreement": {
            "positive": dot_positive,
            "negative": dot_negative,
            "near_zero": dot_near_zero,
        },
        "signed_volume": signed_volume,
    }


def main() -> None:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))
    packages = sorted(
        {
            str(item["static_mesh_package"])
            for item in payload.get("placements", [])
            if item.get("static_mesh_package")
        }
    )
    records = []
    errors = []
    for package in packages:
        try:
            records.append(audit_mesh(package))
        except Exception as exception:
            errors.append({"package": package, "error": f"{type(exception).__name__}: {exception}"})

    report = {
        "status": "audited" if not errors else "partial",
        "mesh_count": len(packages),
        "audited_mesh_count": len(records),
        "error_count": len(errors),
        "normal_winding_totals": {
            key: sum(record["normal_winding_agreement"][key] for record in records)
            for key in ("positive", "negative", "near_zero")
        },
        "meshes_with_more_negative_than_positive": sum(
            record["normal_winding_agreement"]["negative"]
            > record["normal_winding_agreement"]["positive"]
            for record in records
        ),
        "meshes_with_negative_signed_volume": sum(record["signed_volume"] < 0.0 for record in records),
        "errors": errors,
        "meshes": records,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {key: value for key, value in report.items() if key not in {"meshes", "errors"}},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
