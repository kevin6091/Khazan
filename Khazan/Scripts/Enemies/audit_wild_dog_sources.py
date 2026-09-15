"""Verify preserved mesh binds/weights, variant sharing and protected user files."""
from __future__ import annotations
import hashlib
import pathlib
import struct
import build_wild_dog_import_manifest as source


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = source.read(source.ROOT / "ImportManifest.json")
    result = []
    for row in manifest["meshes"]:
        original = source.actorx_chunks(pathlib.Path(row["original_source_file"]))
        derived = source.actorx_chunks(pathlib.Path(row["source_file"]))
        def chunk(chunks, name):
            return next(c for c in chunks if c[0].startswith(name))
        def bones(chunks):
            c = chunk(chunks, b"REFSKELT")
            records = [c[4][i*c[2]:(i+1)*c[2]] for i in range(c[3])]
            return records, [source.bone_name(r) for r in records]
        old_records, old_names = bones(original)
        new_records, new_names = bones(derived)
        for index, name in enumerate(old_names):
            new_record = new_records[new_names.index(name)]
            if old_records[index][76:] != new_record[76:]:
                raise RuntimeError("Original mesh bind changed: " + name)
            old_parent = struct.unpack_from("<i", old_records[index], 72)[0]
            new_parent = struct.unpack_from("<i", new_record, 72)[0]
            if (old_names[old_parent] if old_parent >= 0 else None) != (new_names[new_parent] if new_parent >= 0 else None):
                raise RuntimeError("Parent relationship changed: " + name)
        old_weights, new_weights = chunk(original, b"RAWWEIGHTS"), chunk(derived, b"RAWWEIGHTS")
        if old_weights[2:4] != new_weights[2:4]:
            raise RuntimeError("Weight record count changed")
        for index in range(old_weights[3]):
            left = struct.unpack_from("<fii", old_weights[4], index*12)
            right = struct.unpack_from("<fii", new_weights[4], index*12)
            if left[:2] != right[:2] or old_names[left[2]] != new_names[right[2]]:
                raise RuntimeError("Vertex/weight/bone association changed")
        unchanged = []
        if len(original) != len(derived):
            raise RuntimeError("ActorX chunk count changed")
        for left, right in zip(original, derived):
            if not left[0].startswith((b"REFSKELT", b"RAWWEIGHTS")):
                if left != right:
                    raise RuntimeError("Source geometry/UV/color/material chunk changed")
                unchanged.append(left[0].split(b"\0")[0].decode())
        # Compare both original variant exports, including every LOD0 chunk.
        for alias in row["source_mesh_aliases"]:
            path = next(source.ROOT / "Assets" / (alias+ext) for ext in [".psk", ".pskx"]
                        if (source.ROOT / "Assets" / (alias+ext)).is_file())
            other = source.actorx_chunks(path)
            geometry = lambda chunks: [c for c in chunks if not c[0].startswith(b"MATT0000")]
            if geometry(original) != geometry(other):
                raise RuntimeError("Shared variant mesh payload differs: " + alias)
        result.append({"source": row["source_package"], "mesh_binds_preserved": len(old_names),
                       "weights_checked": old_weights[3], "unchanged_chunks": unchanged,
                       "added_bones": len(new_names)-len(old_names), "source_mesh_aliases": row["source_mesh_aliases"],
                       "derived_sha256": sha256(pathlib.Path(row["source_file"]))})
    audit = {"status": "passed", "meshes": result}
    source.write(source.ROOT / "MeshDerivationAudit.json", audit)
    source.write(source.PROJECT_META / "MeshDerivationAudit.json", audit)

    baseline = source.read(source.ROOT / "WorkspaceBaseline.json")
    git_root = pathlib.Path(baseline["git_root"])
    initial_user = {p:h for p,h in baseline["dirty_file_sha256"].items() if "Scripts/Enemies/prepare_wild_dog_sources.py" not in p}
    changed_user = [p for p,h in initial_user.items() if not (git_root/p).is_file() or sha256(git_root/p) != h]
    changed_protected = [p for p,h in baseline["source_config_sha256"].items()
                         if not (source.PROJECT/p).is_file() or sha256(source.PROJECT/p) != h]
    preservation = {"status": "passed" if not changed_user and not changed_protected else "external_changes_observed",
                    "initial_user_files": len(initial_user), "changed_initial_user_files": changed_user,
                    "source_config_files": len(baseline["source_config_sha256"]), "changed_source_config": changed_protected}
    source.write(source.PROJECT / "Saved/ImportReports/WildDog_WorkspacePreservation_20260915.json", preservation)
    print("WILD_DOG_SOURCE_AUDIT_PASSED", len(result), "mesh;", preservation, flush=True)


if __name__ == "__main__":
    main()
