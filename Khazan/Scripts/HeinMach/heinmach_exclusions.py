"""Shared restoration tombstones for the reconstructed HeinMach level."""

from __future__ import annotations

import json
import os


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(SCRIPT_DIR, "..", ".."))
METADATA_ROOT = os.path.join(
    PROJECT_ROOT,
    "Content",
    "_Art",
    "Kazan",
    "Environment",
    "HeinMach",
    "Metadata",
)
EXCLUSION_PATHS = (
    os.path.join(METADATA_ROOT, "HeinMach_UserExclusions.json"),
    os.path.join(METADATA_ROOT, "HeinMach_OptimizationExclusions.json"),
)
MANUAL_OVERRIDE_PATH = os.path.join(METADATA_ROOT, "HeinMach_ManualOverrides.json")


def exclusion_records():
    records = []
    seen = set()
    for path in EXCLUSION_PATHS:
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8-sig") as source:
            payload = json.load(source)
        for record in payload.get("exclusions", []):
            label = str(record.get("label", ""))
            if not label or not record.get("do_not_restore") or label in seen:
                continue
            copy = dict(record)
            copy["metadata_path"] = path
            records.append(copy)
            seen.add(label)
    return records


def exclusion_labels(category=None):
    return {
        record["label"]
        for record in exclusion_records()
        if category is None or record.get("category") == category
    }


def filter_records(records, label_function, category=None):
    excluded = exclusion_labels(category)
    return [record for record in records if label_function(record) not in excluded]


def transform_overrides(category=None):
    if not os.path.isfile(MANUAL_OVERRIDE_PATH):
        return {}
    with open(MANUAL_OVERRIDE_PATH, "r", encoding="utf-8-sig") as source:
        payload = json.load(source)
    result = {}
    for record in payload.get("transform_overrides", []):
        label = str(record.get("label", ""))
        if (
            label
            and record.get("do_not_reset")
            and (category is None or record.get("category") == category)
        ):
            result[label] = record
    return result
