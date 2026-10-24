"""Source recovery is demonstrated by running archived code in a fresh directory."""

import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest


CONFIG = b'''[option]
spot=100.0
strike=100.0
maturity_years=1.0
risk_free_rate=0.05
volatility=0.2
kind="call"
[convergence]
steps=[5,6]
'''


def provenance():
    return importlib.import_module("option_hedging.experiments.provenance")


def test_snapshot_is_deterministic_and_contains_actual_sources_config_and_replay(tmp_path):
    one, two = tmp_path / "one", tmp_path / "two"
    one.mkdir()
    two.mkdir()
    metadata = provenance().capture_snapshot(one, config_bytes=CONFIG, entrypoint="option_hedging.experiments.convergence_demo")
    other = provenance().capture_snapshot(two, config_bytes=CONFIG, entrypoint="option_hedging.experiments.convergence_demo")
    assert metadata == other
    archive = one / metadata["filename"]
    assert archive.read_bytes() == (two / metadata["filename"]).read_bytes()
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == metadata["sha256"]
    with zipfile.ZipFile(archive) as source:
        assert source.read("input_config.toml") == CONFIG
        assert source.read("src/option_hedging/pricing/black_scholes.py") == (
            Path(__file__).resolve().parents[1] / "src/option_hedging/pricing/black_scholes.py").read_bytes()
        assert b"option_hedging.experiments.convergence_demo" in source.read("REPLAY.md")
        data = json.loads(source.read("SNAPSHOT.json"))
        for name, digest in data["files"].items():
            assert hashlib.sha256(source.read(name)).hexdigest() == digest
        assert set(source.namelist()) == set(data["files"]) | {"SNAPSHOT.json"}


def test_new_demo_has_verifiable_artifacts_and_replay_uses_archived_sources(tmp_path):
    module = importlib.import_module("option_hedging.experiments.convergence_demo")
    config = tmp_path / "config.toml"
    config.write_bytes(CONFIG)
    out = module.run_demo(config, tmp_path / "out")
    verifier = importlib.import_module("option_hedging.experiments.verify_run")
    result = verifier.verify_run(out)
    assert result["source_recoverable"] is True
    manifest = json.loads((out / "manifest.json").read_text())
    recovered = tmp_path / "recovered"
    with zipfile.ZipFile(out / manifest["source_snapshot"]["filename"]) as archive:
        archive.extractall(recovered)  # trusted archive created locally by this test
    env = dict(os.environ, PYTHONPATH=str(recovered / "src"))
    command = [sys.executable, "-W", "error", "-m", "option_hedging.experiments.convergence_demo",
               "--config", "input_config.toml", "--output-dir", "replayed"]
    completed = subprocess.run(command, cwd=recovered, env=env, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert (recovered / "replayed/convergence.csv").exists()
    # Prices/errors match; illustrative elapsed times need not.
    import csv
    with (out / "convergence.csv").open() as stream:
        original = list(csv.DictReader(stream))
    with (recovered / "replayed/convergence.csv").open() as stream:
        replay = list(csv.DictReader(stream))
    assert [{k: v for k, v in r.items() if k != "elapsed_seconds"} for r in original] == [
        {k: v for k, v in r.items() if k != "elapsed_seconds"} for r in replay]


@pytest.mark.parametrize("target", ["convergence.csv", "input_config.toml", "source_snapshot.zip"])
def test_verifier_rejects_modified_artifact(tmp_path, target):
    demo = importlib.import_module("option_hedging.experiments.convergence_demo")
    config = tmp_path / "config.toml"
    config.write_bytes(CONFIG)
    out = demo.run_demo(config, tmp_path / "out")
    with (out / target).open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(ValueError, match="hash|integrity"):
        importlib.import_module("option_hedging.experiments.verify_run").verify_run(out)


def test_historical_hash_only_runs_are_reported_as_not_recoverable(tmp_path):
    out = tmp_path / "historical"
    out.mkdir()
    (out / "input_config.toml").write_bytes(CONFIG)
    digest = hashlib.sha256(CONFIG).hexdigest()
    (out / "manifest.json").write_text(json.dumps(dict(config_sha256=digest,
        artifact_sha256={"input_config.toml": digest}, source_hashes={"missing_old_code.py": "old-digest"})))
    result = importlib.import_module("option_hedging.experiments.verify_run").verify_run(out)
    assert result["artifact_integrity"] is True
    assert result["source_recoverable"] is False
