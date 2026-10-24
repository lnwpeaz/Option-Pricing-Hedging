"""Recoverable source bytes for an experiment, in addition to identifying hashes."""

import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import platform
import zipfile


def capture_snapshot(output_dir: Path, *, config_bytes: bytes, entrypoint: str) -> dict:
    """Write a deterministic archive of package source and exact replay inputs.

    Optional checkout material aids review; package/config/runtime pins are always
    included, so a source-only replay does not depend on an installed editable path.
    No generated outputs, secrets, environment directories or Git metadata are read.
    """
    package = Path(__file__).resolve().parents[1]
    project = package.parent.parent
    files = {"src/option_hedging/" + p.relative_to(package).as_posix(): p.read_bytes()
             for p in sorted(package.rglob("*.py"))}
    if (project / "pyproject.toml").is_file():
        for name in ("pyproject.toml", "README.md", "requirements-lock.txt", "requirements-research.txt"):
            path = project / name
            if path.is_file():
                files[name] = path.read_bytes()
        for folder, pattern in (("tests", "*.py"), ("configs", "*.toml")):
            for path in sorted((project / folder).glob(pattern)):
                files[path.relative_to(project).as_posix()] = path.read_bytes()
    files["input_config.toml"] = config_bytes
    pins = {name: version(name) for name in ("numpy", "scipy", "pandas", "matplotlib")}
    try:
        pins["pytest"] = version("pytest")
    except PackageNotFoundError:
        pass  # pytest is optional for running installed demos.
    try:
        pins["QuantLib"] = version("QuantLib")
    except PackageNotFoundError:
        pass  # Optional independent research comparator.
    files["runtime-requirements.txt"] = ("# Recorded versions; platform/Python/build still matter.\n" +
                                         "\n".join(f"{k}=={v}" for k, v in pins.items()) + "\n").encode()
    files["REPLAY.md"] = (
        "# Replay this captured source\n\n"
        "Extract into a new directory. Use the recorded Python/platform and dependencies.\n"
        "A dependency version list is not a portable, hash-verified environment lock.\n\n"
        "```sh\n"
        f"PYTHONPATH=src python -m {entrypoint} --config input_config.toml --output-dir replay-output\n"
        "```\n\nNumerical results target the recorded environment; elapsed times and images may differ.\n"
    ).encode()
    metadata = dict(format_version=1, entrypoint=entrypoint, python=platform.python_version(),
                    platform=platform.platform(), runtime_versions=pins,
                    files={name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())})
    files["SNAPSHOT.json"] = (json.dumps(metadata, indent=2, allow_nan=False) + "\n").encode()
    destination = output_dir / "source_snapshot.zip"
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    return dict(filename=destination.name, sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),
                format_version=1, entrypoint=entrypoint)


def finalize_manifest(output_dir: Path, manifest: dict, *, config_bytes: bytes, entrypoint: str) -> None:
    """Archive sources and write the completed manifest last, after all artifacts."""
    manifest["source_snapshot"] = capture_snapshot(output_dir, config_bytes=config_bytes, entrypoint=entrypoint)
    if manifest.get("status") not in (None, "completed"):
        manifest.setdefault("scope_note", manifest["status"])
    manifest["status"] = "completed"
    manifest["artifact_sha256"] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted(output_dir.iterdir()) if p.is_file() and p.name != "manifest.json"}
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
