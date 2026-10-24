"""Real path artifacts and CLI: reusable data, paired measures and reproducibility."""

import csv
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest


CONFIG = '''[market]
spot = 100.0
maturity_years = 1.0
risk_free_rate = 0.05
physical_drift = 0.08
volatility = 0.2
[simulation]
paths = 200
steps_per_year = 12
seed = 42
batch_size = 32
preview_paths = 5
[validation]
repeats = 4
paths = 100
'''


def run(tmp_path, config=CONFIG, name="out"):
    demo = importlib.import_module("option_hedging.experiments.paths_demo")
    config_path = tmp_path / f"{name}.toml"
    config_path.write_text(config)
    return demo.run_demo(config_path, tmp_path / name)


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def test_demo_saves_reusable_full_paths_and_paired_measure_diagnostics(tmp_path):
    out = run(tmp_path)
    paths = np.load(out / "paths.npy", allow_pickle=False)
    times = np.load(out / "times.npy", allow_pickle=False)
    assert paths.shape == (200, 13)
    np.testing.assert_array_equal(paths[:, 0], np.full(200, 100.))
    assert times[0] == 0 and times[-1] == 1
    assert len(rows(out / "preview_paths.csv")) == 5 * 13
    assert len(rows(out / "time_statistics.csv")) == 2 * 13
    terminal = rows(out / "terminal_results.csv")
    p = np.array([float(r["terminal_spot"]) for r in terminal if r["measure"] == "physical"])
    q = np.array([float(r["terminal_spot"]) for r in terminal if r["measure"] == "risk_neutral"])
    np.testing.assert_array_equal(p, paths[:, -1])
    np.testing.assert_allclose(p / q, np.full(200, math.exp(.03)), rtol=2e-14)
    validation = rows(out / "validation.csv")
    assert len(validation) == 8
    assert len({r["seed_key"] for r in validation}) == 4  # paired measures share each repeat's shocks
    summary = json.loads((out / "summary.json").read_text())
    assert summary["path_matrix_bytes"] == paths.nbytes
    assert summary["terminal_statistics"]["physical"]["mean"] == pytest.approx(p.mean())
    assert summary["terminal_statistics"]["risk_neutral"]["discounted_mean"] == pytest.approx(q.mean() * math.exp(-.05))
    assert summary["terminal_statistics"]["physical"]["log_return_mean"] == pytest.approx(np.log(p / 100).mean())
    assert summary["terminal_statistics"]["physical"]["log_return_variance"] == pytest.approx(np.log(p / 100).var(ddof=1))
    for name in ("paths.png", "diagnostics.png"):
        assert (out / name).stat().st_size > 10000
    assert (out / "RESULTS.md").stat().st_size > 1500


def test_exact_config_and_source_output_hashes(tmp_path):
    out = run(tmp_path)
    assert (out / "input_config.toml").read_text() == CONFIG
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["status"] == "completed"
    assert manifest["config_sha256"] == hashlib.sha256(CONFIG.encode()).hexdigest()
    assert manifest["rng"]["bit_generator"] == "PCG64"
    assert manifest["path_measure"] == "physical"
    for filename, digest in manifest["artifact_sha256"].items():
        assert hashlib.sha256((out / filename).read_bytes()).hexdigest() == digest
    root = Path(__file__).resolve().parents[1] / "src/option_hedging"
    for filename, digest in manifest["source_hashes"].items():
        assert hashlib.sha256((root / filename).read_bytes()).hexdigest() == digest


def test_numeric_artifacts_reproduce_exactly_in_same_environment(tmp_path):
    first = run(tmp_path, name="first")
    second = run(tmp_path, name="second")
    for filename in ("paths.npy", "times.npy", "preview_paths.csv", "terminal_results.csv", "validation.csv", "time_statistics.csv"):
        assert (first / filename).read_bytes() == (second / filename).read_bytes()


@pytest.mark.parametrize("old,new", [
    ("paths = 200", "paths = 1"), ("paths = 200", "paths = true"),
    ("preview_paths = 5", "preview_paths = 201"), ("seed = 42", "seed = -1"),
    ("batch_size = 32", "batch_size = 0"), ("steps_per_year = 12", "steps_per_year = true"),
    ("maturity_years = 1.0", "maturity_years = 0.0"),
    ("physical_drift = 0.08", "physical_drift = nan"),
    ("volatility = 0.2", "volatility = -0.2"),
    ("repeats = 4", "repeats = 1"), ("batch_size = 32", "batch_size = 32\nunknown = 1"),
    ("physical_drift = 0.08", "physical_drift = 1000.0"),
])
def test_invalid_or_unrepresentable_config_leaves_no_output(tmp_path, old, new):
    with pytest.raises((ValueError, TypeError)):
        run(tmp_path, CONFIG.replace(old, new))
    assert not (tmp_path / "out").exists()


def test_zero_volatility_demo_is_finite_and_reports_deterministic_uncertainty(tmp_path):
    out = run(tmp_path, CONFIG.replace("volatility = 0.2", "volatility = 0.0"))
    summary = json.loads((out / "summary.json").read_text())
    assert summary["terminal_statistics"]["physical"]["standard_error"] == 0
    assert np.all(np.isfinite(np.load(out / "paths.npy")))
    assert summary["validation_summary"]["risk_neutral"]["discounted_mean"] == pytest.approx(100.)


def test_existing_output_is_preserved(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "sentinel").write_text("preserve")
    with pytest.raises(FileExistsError):
        run(tmp_path)
    assert list(out.iterdir()) == [out / "sentinel"]


def test_cli_runs_and_refuses_second_run(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(CONFIG)
    cmd = [sys.executable, "-W", "error", "-m", "option_hedging.experiments.paths_demo",
           "--config", str(path), "--output-dir", str(tmp_path / "cli")]
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    first = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    assert (tmp_path / "cli" / "manifest.json").exists()
    second = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert second.returncode != 0
    assert "already exists" in second.stderr
