"""Audit FModel JSON and texture sources for inherited HeinMach overrides."""

from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
FMODEL_ROOT = Path.home() / "Desktop" / "\uce74\uc794"
RESTORATION_REPORT = (
    PROJECT_ROOT
    / "Saved"
    / "ImportReports"
    / "HeinMach_InheritedRootProp_Restoration.json"
)
REPORT_PATH = (
    PROJECT_ROOT
    / "Saved"
    / "ImportReports"
    / "HeinMach_InheritedOverrideSource_Audit.json"
)
PACKAGES_OVERRIDE = None


def load_json(path: Path):
    with path.open("r", encoding="utf-8-sig") as source:
        return json.load(source)


def package_source(package: str, extension: str) -> Path | None:
    relative = Path(*package.split("/"))
    # Raw Properties exports live under Exports.  Prefer them over JSON sidecars
    # emitted by the USD converter, whose schema is intentionally different.
    candidates = (
        (FMODEL_ROOT / "Exports" / relative).with_suffix(extension),
        (FMODEL_ROOT / relative).with_suffix(extension),
    )
    return next((path for path in candidates if path.is_file()), None)


def package_from_object_path(object_path: str | None) -> str | None:
    if not object_path:
        return None
    return str(object_path).rsplit(".", 1)[0]


def image_source(package: str) -> Path | None:
    relative = Path(*package.split("/"))
    for root in (FMODEL_ROOT, FMODEL_ROOT / "Exports"):
        base = root / relative
        for extension in (".png", ".hdr", ".exr", ".tga"):
            candidate = base.with_suffix(extension)
            if candidate.is_file():
                return candidate
    return None


def material_record(package: str, json_path: Path) -> dict:
    payload = load_json(json_path)
    if isinstance(payload, list):
        source = next(
            (
                item
                for item in payload
                if isinstance(item, dict)
                and item.get("Type") in {"Material", "MaterialInstanceConstant"}
            ),
            None,
        )
        if source is None:
            raise RuntimeError(f"Material export is missing from: {json_path}")
        properties = source.get("Properties", {})
        texture_values = properties.get("TextureParameterValues", []) or []
        scalar_count = len(properties.get("ScalarParameterValues", []) or [])
        vector_count = len(properties.get("VectorParameterValues", []) or [])
        switch_count = len(
            ((properties.get("StaticParameters") or {}).get("StaticSwitchParameters"))
            or []
        )
        source_type = source.get("Type")
        parent_object_path = (properties.get("Parent") or {}).get("ObjectPath")
    elif isinstance(payload, dict) and isinstance(payload.get("Parameters"), dict):
        parameters = payload["Parameters"]
        properties = parameters.get("Properties", {}) or {}
        texture_values = [
            {
                "ParameterInfo": {"Name": name},
                "ParameterValue": {"ObjectPath": object_path},
            }
            for name, object_path in (payload.get("Textures") or {}).items()
            if object_path
        ]
        scalar_count = len(parameters.get("Scalars", {}) or {})
        vector_count = len(parameters.get("Colors", {}) or {})
        switch_count = len(parameters.get("Switches", {}) or {})
        source_type = "UsdPreviewSurfaceSidecar"
        parent_object_path = None
    else:
        raise RuntimeError(f"Unsupported FModel material payload: {json_path}")

    texture_parameters = []
    for item in texture_values:
        object_path = (item.get("ParameterValue") or {}).get("ObjectPath")
        texture_package = package_from_object_path(object_path)
        texture_image = image_source(texture_package) if texture_package else None
        texture_parameters.append(
            {
                "name": (item.get("ParameterInfo") or {}).get("Name"),
                "object_path": object_path,
                "package": texture_package,
                "image_path": str(texture_image) if texture_image else None,
            }
        )

    return {
        "package": package,
        "name": package.rsplit("/", 1)[-1],
        "type": source_type,
        "json_path": str(json_path),
        "parent_object_path": parent_object_path,
        "texture_parameters": texture_parameters,
        "scalar_parameter_count": scalar_count,
        "vector_parameter_count": vector_count,
        "static_switch_parameter_count": switch_count,
        "base_property_overrides": properties.get("BasePropertyOverrides", {}),
    }


def main() -> None:
    restoration = load_json(RESTORATION_REPORT)
    packages = (
        sorted(PACKAGES_OVERRIDE)
        if PACKAGES_OVERRIDE is not None
        else sorted(
            item["package"]
            for item in restoration.get("placement_result", {}).get(
                "unresolved_override_materials", []
            )
        )
    )

    records = []
    missing_json = []
    parse_errors = []
    for package in packages:
        json_path = package_source(package, ".json")
        if json_path is None:
            missing_json.append(package)
            continue
        try:
            records.append(material_record(package, json_path))
        except Exception as exception:
            parse_errors.append({"package": package, "error": str(exception)})

    texture_packages = {}
    for record in records:
        for parameter in record["texture_parameters"]:
            package = parameter.get("package")
            if package:
                texture_packages.setdefault(package, parameter.get("image_path"))
    missing_images = sorted(
        package for package, path in texture_packages.items() if not path
    )

    report = {
        "status": "audited",
        "source_restoration_report": str(RESTORATION_REPORT),
        "material_package_count": len(packages),
        "parsed_material_count": len(records),
        "missing_json_count": len(missing_json),
        "parse_error_count": len(parse_errors),
        "unique_texture_package_count": len(texture_packages),
        "missing_texture_image_count": len(missing_images),
        "materials_with_texture_overrides": sum(
            bool(record["texture_parameters"]) for record in records
        ),
        "missing_json_packages": missing_json,
        "parse_errors": parse_errors,
        "missing_texture_image_packages": missing_images,
        "records": records,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with REPORT_PATH.open("w", encoding="utf-8", newline="\n") as output:
        json.dump(report, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")
    print(json.dumps({key: value for key, value in report.items() if key.endswith("count")}, indent=2))
    print(f"report={REPORT_PATH}")


if __name__ == "__main__":
    main()
