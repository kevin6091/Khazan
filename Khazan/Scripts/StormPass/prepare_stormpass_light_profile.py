"""Reconstruct the StormPass JellyFish IES profile from FModel's HDR export.

FModel exports the cooked ``TextureLightProfile`` lookup as a 256x1 Radiance
HDR image rather than the original LM-63 source file.  Unreal's IES importer
normalizes all candela samples by the maximum source value.  To reproduce the
cooked lookup without changing it, this script writes the 256 decoded lookup
values at the exact angles sampled by UE (x * 180 / 256) and appends one
unbaked sentinel sample at 180 degrees with a value of 1.0.  The sentinel keeps
the importer normalization factor at one; UE's 256 generated texels stop at
179.296875 degrees, so it never enters the runtime texture.

This is an asset-only step.  It deliberately refuses to modify the open world
and removes only two unreferenced assets created by earlier import probes in
the dedicated StormPass IES folder.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import traceback

import unreal


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
FMODEL_HDR_PATH = (
    r"C:\Users\user\Desktop\카잔\BBQ\Content\_Kazan_\Art\VFX\VFX_Texture"
    r"\BBQ_Texture\IES\JellyFish.hdr"
)
GENERATED_IES_PATH = os.path.join(
    unreal.Paths.project_saved_dir(),
    "ImportSources",
    "StormPassLightProfile",
    "JellyFish_Reconstructed.ies",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "StormPass_LightProfile_AssetPreparation.json",
)
ASSET_FOLDER = (
    "/Game/_Art/Kazan/Environment/StormPass/Reconstructed/LightAssets/IES"
)
PROFILE_ASSET_PATH = ASSET_FOLDER + "/TLP_JellyFish"
FAILED_PROBE_ASSET_PATHS = (
    ASSET_FOLDER + "/T_JellyFish_Profile",
)
EXPECTED_WIDTH = 256
EXPECTED_HEIGHT = 1
EXPECTED_NONZERO_SAMPLE_COUNT = 128
EXPECTED_MIN = 0.0
EXPECTED_MAX = 0.6640625


def log(message):
    unreal.log("KHAZAN_STORMPASS_LIGHT_PROFILE: " + str(message))


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def world_snapshot():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    world = editor.get_editor_world()
    actors = unreal.get_editor_subsystem(
        unreal.EditorActorSubsystem
    ).get_all_level_actors()
    fog = sorted(
        (actor.get_actor_label(), actor.get_class().get_name())
        for actor in actors
        if actor
        and (
            actor.get_actor_label().startswith("SP_Fog_")
            or "Fog" in actor.get_class().get_name()
        )
    )
    return {
        "world_path": world.get_path_name() if world else None,
        "actor_count": len(actors),
        "fog_actor_count": len(fog),
        "fog_actors": fog,
    }


def read_ascii_line(data, position):
    end = data.find(b"\n", position)
    if end < 0:
        end = len(data)
    line = data[position:end]
    if line.endswith(b"\r"):
        line = line[:-1]
    return line.decode("ascii"), min(end + 1, len(data))


def decode_fmodel_rgbe(path):
    with open(path, "rb") as source:
        data = source.read()
    if not data.startswith(b"#?RADIANCE"):
        raise RuntimeError("JellyFish source is not a Radiance HDR file")

    position = 0
    header = []
    while True:
        line, position = read_ascii_line(data, position)
        if not line:
            break
        header.append(line)
    resolution, position = read_ascii_line(data, position)
    fields = resolution.split()
    if fields != ["-Y", "1", "+X", "256"]:
        raise RuntimeError("Unexpected JellyFish HDR resolution: " + resolution)
    if data[position : position + 2] != b"\x02\x02":
        raise RuntimeError("JellyFish HDR does not use the expected scanline RLE")

    width = (data[position + 2] << 8) | data[position + 3]
    position += 4
    if width != EXPECTED_WIDTH:
        raise RuntimeError("Unexpected JellyFish HDR scanline width")

    channels = []
    for _channel_index in range(4):
        channel = []
        while len(channel) < width:
            if position >= len(data):
                raise RuntimeError("JellyFish HDR scanline ended early")
            code = data[position]
            position += 1
            if code > 128:
                count = code - 128
                if position >= len(data):
                    raise RuntimeError("JellyFish HDR run is missing its value")
                channel.extend([data[position]] * count)
                position += 1
            elif code:
                end = position + code
                channel.extend(data[position:end])
                position = end
            else:
                raise RuntimeError("JellyFish HDR contains a zero-length RLE packet")
        if len(channel) != width:
            raise RuntimeError("JellyFish HDR channel width mismatch")
        channels.append(channel)
    if position != len(data):
        raise RuntimeError("Unexpected bytes follow the JellyFish HDR scanline")
    if channels[0] != channels[1] or channels[0] != channels[2]:
        raise RuntimeError("JellyFish profile is not a grayscale lookup")

    values = []
    for mantissa, exponent in zip(channels[0], channels[3]):
        values.append(
            0.0 if exponent == 0 else math.ldexp(float(mantissa), exponent - 136)
        )
    return {
        "header": header,
        "resolution": resolution,
        "width": width,
        "height": 1,
        "values": values,
    }


def format_float(value):
    if value == 0.0:
        return "0"
    return format(value, ".17g")


def wrapped_values(values, count_per_line=12):
    return [
        " ".join(format_float(value) for value in values[index : index + count_per_line])
        for index in range(0, len(values), count_per_line)
    ]


def build_ies_text(profile_values):
    # UE samples x/256 * 180 for x in [0, 255].  The final 180-degree
    # sentinel affects ComputeMax only and is never sampled into the texture.
    vertical_angles = [index * 180.0 / EXPECTED_WIDTH for index in range(257)]
    candela_values = list(profile_values) + [1.0]
    lines = [
        "IESNA:LM-63-2002",
        "[TEST] Reconstructed from FModel JellyFish TextureLightProfile HDR",
        "[MANUFAC] Khazan StormPass deterministic restoration",
        "TILT=NONE",
        # lamps, lumens/lamp, candela multiplier, vertical count, horizontal
        # count, Type C, meters, dimensions, ballast, future use, watts
        "1 1 1 257 1 1 2 0 0 0 1 1 1",
    ]
    lines.extend(wrapped_values(vertical_angles))
    lines.append("0")
    lines.extend(wrapped_values(candela_values))
    return "\n".join(lines) + "\n"


def write_if_changed(path, content):
    encoded = content.encode("ascii")
    if os.path.isfile(path):
        with open(path, "rb") as source:
            if source.read() == encoded:
                return False
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as output:
        output.write(encoded)
    return True


def color_channels(color):
    return {
        "r": float(color.r),
        "g": float(color.g),
        "b": float(color.b),
        "a": float(color.a),
    }


def profile_state(asset):
    if not asset:
        return None
    minimum, maximum = asset.compute_texture_source_channel_min_max()
    built_size = asset.blueprint_get_built_texture_size()
    return {
        "path": asset.get_path_name(),
        "class": asset.get_class().get_name(),
        # The IES LOD group may report a 32x32 resident resource after reload
        # even though source/build data remains the native 256x256 profile.
        "resident_size_x": int(asset.blueprint_get_size_x()),
        "resident_size_y": int(asset.blueprint_get_size_y()),
        "built_size_x": int(built_size.x),
        "built_size_y": int(built_size.y),
        "brightness": float(asset.get_editor_property("brightness")),
        "texture_multiplier": float(
            asset.get_editor_property("texture_multiplier")
        ),
        "srgb": bool(asset.get_editor_property("srgb")),
        "never_stream": bool(asset.get_editor_property("never_stream")),
        "compression_settings": str(
            asset.get_editor_property("compression_settings")
        ),
        "source_min": color_channels(minimum),
        "source_max": color_channels(maximum),
    }


def state_is_exact(state):
    if not state:
        return False
    return (
        state["class"] == "TextureLightProfile"
        and state["built_size_x"] == 256
        and state["built_size_y"] == 256
        and abs(state["source_min"]["r"] - EXPECTED_MIN) <= 1.0e-7
        and abs(state["source_max"]["r"] - EXPECTED_MAX) <= 1.0e-7
        and abs(state["texture_multiplier"] - 1.0) <= 1.0e-7
        and not state["srgb"]
        and state["never_stream"]
    )


def delete_unreferenced_probe(path):
    if not unreal.EditorAssetLibrary.does_asset_exist(path):
        return {"path": path, "status": "absent", "referencers": []}
    referencers = list(
        unreal.EditorAssetLibrary.find_package_referencers_for_asset(
            path, load_assets_to_confirm=True
        )
    )
    if referencers:
        raise RuntimeError(
            "Refusing to delete referenced StormPass IES probe {}: {}".format(
                path, referencers
            )
        )
    if not unreal.EditorAssetLibrary.delete_asset(path):
        raise RuntimeError("Failed to delete StormPass IES probe: " + path)
    return {"path": path, "status": "deleted", "referencers": []}


def import_profile(ies_path):
    existing = unreal.EditorAssetLibrary.load_asset(PROFILE_ASSET_PATH)
    existing_state = profile_state(existing) if existing else None
    if state_is_exact(existing_state):
        return existing, [], "reused_exact", existing_state
    deletion = None
    if existing:
        deletion = delete_unreferenced_probe(PROFILE_ASSET_PATH)

    if not unreal.EditorAssetLibrary.does_directory_exist(ASSET_FOLDER):
        unreal.EditorAssetLibrary.make_directory(ASSET_FOLDER)
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", ies_path)
    task.set_editor_property("destination_path", ASSET_FOLDER)
    task.set_editor_property("destination_name", "TLP_JellyFish")
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", False)
    task.set_editor_property("save", True)
    # Keep .ies on the synchronous legacy factory.  UE 5.8's Interchange
    # dispatcher asserts in TaskGraph when started from Rider's game-thread
    # Python executor, while UTextureFactory owns the engine's native IES
    # conversion path (FIESConverter) and is safe in this context.
    task.set_editor_property("factory", unreal.TextureFactory())
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported_paths = list(task.get_editor_property("imported_object_paths"))
    asset = unreal.EditorAssetLibrary.load_asset(PROFILE_ASSET_PATH)
    if not asset:
        raise RuntimeError("Unreal did not create the JellyFish light profile")
    return asset, imported_paths, "imported", deletion


def main():
    before = world_snapshot()
    if before["fog_actor_count"] != 0:
        raise RuntimeError("Fog boundary differs before Light asset preparation")

    decoded = decode_fmodel_rgbe(FMODEL_HDR_PATH)
    values = decoded["values"]
    source_min = min(values)
    source_max = max(values)
    nonzero_count = sum(1 for value in values if value != 0.0)
    if (
        decoded["width"] != EXPECTED_WIDTH
        or decoded["height"] != EXPECTED_HEIGHT
        or nonzero_count != EXPECTED_NONZERO_SAMPLE_COUNT
        or abs(source_min - EXPECTED_MIN) > 1.0e-12
        or abs(source_max - EXPECTED_MAX) > 1.0e-12
    ):
        raise RuntimeError("JellyFish FModel profile fingerprint changed")

    generated = build_ies_text(values)
    source_written = write_if_changed(GENERATED_IES_PATH, generated)
    cleanup = [
        delete_unreferenced_probe(path) for path in FAILED_PROBE_ASSET_PATHS
    ]
    profile, imported_paths, import_status, previous_state = import_profile(
        GENERATED_IES_PATH
    )
    state = profile_state(profile)
    if not state_is_exact(state):
        raise RuntimeError(
            "Reconstructed JellyFish TextureLightProfile failed validation: "
            + json.dumps(state, ensure_ascii=False, sort_keys=True)
        )
    if not unreal.EditorAssetLibrary.save_loaded_asset(
        profile, only_if_is_dirty=False
    ):
        raise RuntimeError("Failed to save reconstructed JellyFish profile")

    after = world_snapshot()
    if after != before:
        raise RuntimeError("Editor world changed during Light asset preparation")
    report = {
        "status": "passed",
        "operation": "asset_only_native_ies_profile_reconstruction",
        "map_modified": False,
        "fmodel_hdr_path": FMODEL_HDR_PATH,
        "fmodel_hdr_sha256": sha256_file(FMODEL_HDR_PATH),
        "fmodel_hdr_header": decoded["header"],
        "fmodel_hdr_resolution": decoded["resolution"],
        "source_width": decoded["width"],
        "source_height": decoded["height"],
        "source_sample_count": len(values),
        "source_nonzero_sample_count": nonzero_count,
        "source_min": source_min,
        "source_max": source_max,
        "generated_ies_path": GENERATED_IES_PATH,
        "generated_ies_sha256": sha256_file(GENERATED_IES_PATH),
        "generated_ies_written": source_written,
        "vertical_angle_count": 257,
        "horizontal_angle_count": 1,
        "unbaked_normalization_sentinel": {
            "vertical_angle_degrees": 180.0,
            "candela": 1.0,
        },
        "profile_asset": PROFILE_ASSET_PATH,
        "profile_import_status": import_status,
        "profile_previous_state_or_deletion": previous_state,
        "profile_imported_object_paths": imported_paths,
        "profile_state": state,
        "failed_probe_cleanup": cleanup,
        "fog_policy": "deferred_until_final_pass",
        "world_before": before,
        "world_after": after,
    }
    write_json(REPORT_PATH, report)
    log(
        "RESULT profile={} samples={} nonzero={} range=[{},{}] fog=0 report={}".format(
            state["path"],
            len(values),
            nonzero_count,
            source_min,
            source_max,
            REPORT_PATH,
        )
    )
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
                "fog_policy": "deferred_until_final_pass",
            },
        )
        unreal.log_error("KHAZAN_STORMPASS_LIGHT_PROFILE: " + str(exception))
        raise
