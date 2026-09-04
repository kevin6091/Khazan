"""Restore the source-authored DualAxeSword tutorial entry anchors.

This Art/Resource pass restores the source PlayerStart and the two tutorial
enemy spawn locations as editor/runtime integration markers.  It deliberately
does not load any HeinMach_Cine_Opening layer, so the unwanted barehanded
staggering sequence remains excluded.  Enemy AI and tutorial UI are gameplay
integration responsibilities and can bind to the stable TargetPoint labels.
"""

from __future__ import annotations

import json
import os
import traceback

import unreal


PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
MAP_PATH = "/Game/_Art/Kazan/Environment/HeinMach/Maps/L_HeinMach_Environment"
LEVEL_DATA_PATH = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "HeinMach",
    "Metadata",
    "HeinMach_LevelData.json",
)
REPORT_PATH = os.path.join(
    PROJECT_ROOT,
    "Saved",
    "ImportReports",
    "HeinMach_DualAxeTutorial_Restoration.json",
)
FOLDER = "HeinMach/Reconstructed/Tutorial_DualAxeSword"
PLAYER_SOURCE_NAME = "MISSION01_START"
PLAYER_LABEL = "HM_Tutorial_PlayerStart_DualAxeSword"
SPAWN_SPECS = (
    {
        "source_name": "SA_EmpireSword_Early3_Item",
        "label": "HM_TutorialSpawn_01_EmpireSword",
        "ai_data": "AI_EmpireSword_Tutorial_Signal_1",
        "sequence": 1,
    },
    {
        "source_name": "SA_Empire_SwordShield_2",
        "label": "HM_TutorialSpawn_02_EmpireSwordShield",
        "ai_data": "AI_Empire_SwordShield_Tutorial_Signal_1",
        "sequence": 2,
    },
)


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as source:
        return json.load(source)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2, sort_keys=True)
        output.write("\n")


def vector(transform):
    value = transform.get("location_cm", {})
    return unreal.Vector(
        x=float(value.get("x", 0.0)),
        y=float(value.get("y", 0.0)),
        z=float(value.get("z", 0.0)),
    )


def rotator(transform):
    value = transform.get("rotation_degrees", {})
    return unreal.Rotator(
        pitch=float(value.get("pitch", 0.0)),
        yaw=float(value.get("yaw", 0.0)),
        roll=float(value.get("roll", 0.0)),
    )


def transform_payload(actor):
    location = actor.get_actor_location()
    rotation = actor.get_actor_rotation()
    return {
        "location_cm": {"x": location.x, "y": location.y, "z": location.z},
        "rotation_degrees": {
            "pitch": rotation.pitch,
            "yaw": rotation.yaw,
            "roll": rotation.roll,
        },
    }


def set_folder(actor):
    try:
        actor.set_folder_path(FOLDER)
    except Exception:
        actor.set_editor_property("folder_path", FOLDER)


def set_tags(actor, values):
    actor.set_editor_property("tags", [unreal.Name(value) for value in values])


def source_record(records, source_name):
    matches = [
        record
        for record in records
        if record.get("source_level") == "HeinMach_Spawn_Main01"
        and record.get("actor_name") == source_name
    ]
    if len(matches) != 1:
        raise RuntimeError(
            "Expected one {} source record, found {}".format(source_name, len(matches))
        )
    return matches[0]


def load_level_if_needed():
    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if not world or not world.get_path_name().startswith(MAP_PATH + "."):
        if not level_subsystem.load_level(MAP_PATH):
            raise RuntimeError("Failed to load HeinMach environment map")
    return level_subsystem


def spawn_or_reuse(actor_subsystem, actors_by_label, actor_class, label, record):
    actor = actors_by_label.get(label)
    created = False
    if actor and not isinstance(actor, actor_class):
        raise RuntimeError("Tutorial label exists with the wrong class: " + label)
    if not actor:
        actor = actor_subsystem.spawn_actor_from_class(
            actor_class, vector(record["transform"]), rotator(record["transform"])
        )
        if not actor:
            raise RuntimeError("Failed to spawn tutorial anchor: " + label)
        actor.set_actor_label(label, mark_dirty=True)
        actors_by_label[label] = actor
        created = True
    actor.set_actor_location(vector(record["transform"]), False, False)
    actor.set_actor_rotation(rotator(record["transform"]), False)
    set_folder(actor)
    return actor, created


def nearby_environment_count(actor_subsystem, location, radius):
    radius_squared = float(radius) * float(radius)
    count = 0
    for actor in actor_subsystem.get_all_level_actors():
        if not actor or not actor.get_actor_label().startswith("HM_Prop_"):
            continue
        delta = actor.get_actor_location() - location
        distance_squared = (
            float(delta.x) * float(delta.x)
            + float(delta.y) * float(delta.y)
            + float(delta.z) * float(delta.z)
        )
        if distance_squared <= radius_squared:
            count += 1
    return count


def main():
    data = load_json(LEVEL_DATA_PATH)
    player_record = source_record(
        list(data.get("player_respawn_points", [])), PLAYER_SOURCE_NAME
    )
    monster_records = list(data.get("monster_spawns", []))
    spawn_records = {
        spec["source_name"]: source_record(monster_records, spec["source_name"])
        for spec in SPAWN_SPECS
    }

    level_subsystem = load_level_if_needed()
    actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    before_actors = [actor for actor in actor_subsystem.get_all_level_actors() if actor]
    actors_by_label = {actor.get_actor_label(): actor for actor in before_actors}
    created_labels = []
    reused_labels = []

    player, created = spawn_or_reuse(
        actor_subsystem,
        actors_by_label,
        unreal.PlayerStart,
        PLAYER_LABEL,
        player_record,
    )
    set_tags(
        player,
        (
            "HeinMachTutorial",
            "DualAxeSword",
            "Source_MISSION01_START",
            "BarehandOpeningExcluded",
        ),
    )
    try:
        player.set_editor_property("player_start_tag", unreal.Name("DualAxeSwordTutorial"))
    except Exception:
        pass
    (created_labels if created else reused_labels).append(PLAYER_LABEL)

    spawn_results = []
    for spec in SPAWN_SPECS:
        record = spawn_records[spec["source_name"]]
        actor, created = spawn_or_reuse(
            actor_subsystem,
            actors_by_label,
            unreal.TargetPoint,
            spec["label"],
            record,
        )
        set_tags(
            actor,
            (
                "HeinMachTutorial",
                "DualAxeSword",
                "TutorialEnemySpawn",
                spec["source_name"],
                spec["ai_data"],
            ),
        )
        (created_labels if created else reused_labels).append(spec["label"])
        spawn_results.append(
            {
                **spec,
                "source_object_index": record.get("source_object_index"),
                "transform": transform_payload(actor),
                "nearby_environment_prop_count_2500cm": nearby_environment_count(
                    actor_subsystem, actor.get_actor_location(), 2500.0
                ),
            }
        )

    all_player_starts = [
        actor
        for actor in actor_subsystem.get_all_level_actors()
        if actor and isinstance(actor, unreal.PlayerStart)
    ]
    labels = {actor.get_actor_label() for actor in actor_subsystem.get_all_level_actors() if actor}
    required_labels = {PLAYER_LABEL, *(spec["label"] for spec in SPAWN_SPECS)}
    if not required_labels.issubset(labels):
        raise RuntimeError("Tutorial anchor validation failed")
    if not level_subsystem.save_current_level():
        raise RuntimeError("Failed to save DualAxeSword tutorial anchors")

    report = {
        "status": "restored",
        "map_path": MAP_PATH,
        "source_level": "HeinMach_Spawn_Main01",
        "scene_flow": [
            "barehanded_staggering_opening: excluded",
            "DualAxeSword_attack_tutorial: restored entry and spawn anchors",
            "main_HeinMach_progression: existing continuous environment",
        ],
        "player_start": {
            "label": PLAYER_LABEL,
            "source_name": PLAYER_SOURCE_NAME,
            "source_object_index": player_record.get("source_object_index"),
            "transform": transform_payload(player),
            "nearby_environment_prop_count_2500cm": nearby_environment_count(
                actor_subsystem, player.get_actor_location(), 2500.0
            ),
        },
        "tutorial_spawn_markers": spawn_results,
        "created_labels": created_labels,
        "reused_labels": reused_labels,
        "player_start_count": len(all_player_starts),
        "art_scope_boundary": (
            "The original environment, source PlayerStart, and source enemy locations are "
            "restored. Enemy Blueprint/AI spawning, attack prompts, completion gates, and "
            "forced DualAxeSword loadout remain an Engineering integration task."
        ),
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
