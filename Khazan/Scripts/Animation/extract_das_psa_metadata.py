"""Extract authoritative frame metadata from the original DualAxeSword PSA files.

The FBX files imported into this project contain a padded 249-frame take.  The
original PSA files still carry the intended frame count and sample rate for each
named animation.  This script reads only the PSA chunk headers and ANIMINFO
records; it never changes project content.

Run from a normal Python 3 interpreter.  The default source path matches the
local FModel export used by this project, but both paths can be overridden.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PSA_ROOT = Path(
    r"C:\Users\user\Desktop\카잔\BBQ\Content\_Kazan_\Art\Character\CHA_Model\PC\Kazan\Animation\DualAxeSword"
)
DEFAULT_REPORT = (
    PROJECT_ROOT / "Saved" / "ImportReports" / "Khazan_DAS_PSA_SourceMetadata.json"
)

CHUNK_HEADER = struct.Struct("<20siii")
ANIM_INFO = struct.Struct("<64s64s4i3f3i")


def _text(raw: bytes) -> str:
    raw = raw.split(b"\0", 1)[0]
    for encoding in ("utf-8", "cp949", "latin-1"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("latin-1", errors="replace")


def _chunk_id(raw: bytes) -> str:
    return _text(raw).strip()


def _parse_anim_info(record: bytes) -> dict:
    (
        name,
        group,
        total_bones,
        root_include,
        key_compression_style,
        key_quotum,
        key_reduction,
        track_time,
        anim_rate,
        start_bone,
        first_raw_frame,
        num_raw_frames,
    ) = ANIM_INFO.unpack(record[: ANIM_INFO.size])

    return {
        "name": _text(name),
        "group": _text(group),
        "total_bones": total_bones,
        "root_include": root_include,
        "key_compression_style": key_compression_style,
        "key_quotum": key_quotum,
        "key_reduction": key_reduction,
        "track_time": track_time,
        "anim_rate": anim_rate,
        "start_bone": start_bone,
        "first_raw_frame": first_raw_frame,
        "num_raw_frames": num_raw_frames,
        # Unreal's PSA importer calls SetNumberOfFrames(NumRawFrames - 1).
        "unreal_final_frame": max(num_raw_frames - 1, 1),
        "duration_seconds": (
            (num_raw_frames - 1) / anim_rate if anim_rate > 0.0 else None
        ),
    }


def parse_psa(path: Path, root: Path) -> dict:
    with path.open("rb") as handle:
        first = handle.read(CHUNK_HEADER.size)
        if len(first) != CHUNK_HEADER.size:
            raise ValueError("file is shorter than one PSA chunk header")

        first_id, _, _, _ = CHUNK_HEADER.unpack(first)
        if _chunk_id(first_id) != "ANIMHEAD":
            raise ValueError(f"unexpected PSA header {_chunk_id(first_id)!r}")

        anim_infos: list[dict] = []
        chunks: list[dict] = []

        while True:
            raw_header = handle.read(CHUNK_HEADER.size)
            if not raw_header:
                break
            if len(raw_header) != CHUNK_HEADER.size:
                raise ValueError("truncated PSA chunk header")

            raw_id, type_flag, data_size, data_count = CHUNK_HEADER.unpack(raw_header)
            chunk_id = _chunk_id(raw_id)
            if data_size < 0 or data_count < 0:
                raise ValueError(f"invalid chunk dimensions for {chunk_id}")

            payload_size = data_size * data_count
            payload = handle.read(payload_size)
            if len(payload) != payload_size:
                raise ValueError(f"truncated PSA chunk payload for {chunk_id}")

            chunks.append(
                {
                    "id": chunk_id,
                    "type_flag": type_flag,
                    "data_size": data_size,
                    "data_count": data_count,
                }
            )

            if chunk_id != "ANIMINFO":
                continue
            if data_size < ANIM_INFO.size:
                raise ValueError(
                    f"ANIMINFO record is {data_size} bytes; expected at least {ANIM_INFO.size}"
                )
            for index in range(data_count):
                offset = index * data_size
                anim_infos.append(_parse_anim_info(payload[offset : offset + data_size]))

    if not anim_infos:
        raise ValueError("PSA has no ANIMINFO record")

    return {
        "file_name": path.name,
        "base_name": path.stem,
        "relative_path": path.relative_to(root).as_posix(),
        "file_size": path.stat().st_size,
        "animations": anim_infos,
        "chunks": chunks,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--psa-root", type=Path, default=DEFAULT_PSA_ROOT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    psa_root = args.psa_root.resolve()
    report_path = args.report.resolve()
    if not psa_root.is_dir():
        raise SystemExit(f"PSA source directory does not exist: {psa_root}")

    rows: list[dict] = []
    failures: list[dict] = []
    for path in sorted(psa_root.rglob("*.psa"), key=lambda item: item.name.lower()):
        try:
            rows.append(parse_psa(path, psa_root))
        except Exception as exc:  # Keep a complete inventory even if one file is damaged.
            failures.append(
                {
                    "relative_path": path.relative_to(psa_root).as_posix(),
                    "error": str(exc),
                }
            )

    by_base_name: dict[str, list[dict]] = {}
    for row in rows:
        by_base_name.setdefault(row["base_name"], []).append(row)

    report = {
        "schema": 1,
        "psa_root": str(psa_root),
        "psa_file_count": len(rows),
        "parse_failure_count": len(failures),
        "duplicate_base_names": sorted(
            name for name, matches in by_base_name.items() if len(matches) > 1
        ),
        "files": rows,
        "failures": failures,
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(
        json.dumps(
            {
                "report": str(report_path),
                "psa_file_count": len(rows),
                "parse_failure_count": len(failures),
                "duplicate_base_name_count": len(report["duplicate_base_names"]),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
