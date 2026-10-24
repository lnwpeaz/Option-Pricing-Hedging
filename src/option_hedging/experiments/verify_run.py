"""Verify saved bytes and source recovery without executing archived code."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


def _safe_name(name):
    if not isinstance(name, str) or not name or "\\" in name:
        raise ValueError("Invalid relative artifact name")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != name:
        raise ValueError("Unsafe relative artifact name")
    return name


def verify_run(output_dir: Path) -> dict:
    """Check hashes relative to the manifest; not authenticity or cross-build replay."""
    manifest = json.loads((output_dir / "manifest.json").read_text())
    config = (output_dir / "input_config.toml").read_bytes()
    if hashlib.sha256(config).hexdigest() != manifest["config_sha256"]:
        raise ValueError("Input config hash integrity failure")
    artifacts = manifest.get("artifact_sha256")
    if artifacts is not None:
        for name, digest in artifacts.items():
            path = output_dir / _safe_name(name)
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != digest:
                raise ValueError(f"Artifact hash integrity failure: {name}")
    snapshot = manifest.get("source_snapshot")
    result = dict(config_integrity=True, artifact_integrity=True if artifacts is not None else None,
                  artifact_count=len(artifacts or {}), source_recoverable=False,
                  note="Historical hash-only run: exact old source is not recoverable from this record alone")
    if snapshot is None:
        return result
    name = _safe_name(snapshot["filename"])
    archive_path = output_dir / name
    if hashlib.sha256(archive_path.read_bytes()).hexdigest() != snapshot["sha256"]:
        raise ValueError("Source snapshot hash integrity failure")
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate archived names")
        for filename in names:
            _safe_name(filename)
        metadata = json.loads(archive.read("SNAPSHOT.json"))
        if metadata.get("format_version") != 1:
            raise ValueError("Unsupported snapshot format")
        expected = metadata["files"]
        if set(names) != set(expected) | {"SNAPSHOT.json"}:
            raise ValueError("Source snapshot entry integrity failure")
        for filename, digest in expected.items():
            if hashlib.sha256(archive.read(filename)).hexdigest() != digest:
                raise ValueError(f"Archived source hash integrity failure: {filename}")
        if archive.read("input_config.toml") != config:
            raise ValueError("Archived input config integrity failure")
        for filename, digest in manifest["source_hashes"].items():
            archive_name = "src/option_hedging/" + _safe_name(filename)
            if expected.get(archive_name) != digest:
                raise ValueError(f"Manifest/archive source hash mismatch: {filename}")
    result.update(source_recoverable=True, note="Archived source/config bytes verified; execution and environment must be checked separately")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    try:
        result = verify_run(args.run_dir)
    except (OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
