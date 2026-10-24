"""Run the real experiment and CLI; compare numeric artifacts, not wall times."""

import csv
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from option_hedging.contracts import OptionSpec


CONFIG = '''[option]
spot = 100.0
strike = 100.0
maturity_years = 1.0
risk_free_rate = 0.05
volatility = 0.2
kind = "call"
dividend_yield = 0.0
[monte_carlo]
sample_sizes = [128, 512]
strikes = [80.0, 100.0, 120.0]
methods = ["plain", "antithetic", "control"]
repeats = 4
seed = 431
batch_size = 128
pilot_paths = 64
bootstrap_repeats = 100
[benchmark]
n_paths = 512
batch_sizes = [32, 128]
repeats = 3
seed = 471
'''


def run(tmp_path, config=CONFIG, name="out"):
    demo = importlib.import_module("option_hedging.experiments.monte_carlo_demo")
    path = tmp_path / f"{name}.toml"
    path.write_text(config)
    return demo.run_demo(path, tmp_path / name)


def read_rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def test_real_run_outputs_complete_grid_and_auditable_artifacts(tmp_path):
    out = run(tmp_path)
    assert (out / "input_config.toml").read_text() == CONFIG
    estimates = read_rows(out / "estimates.csv")
    metrics = read_rows(out / "metrics.csv")
    assert len(estimates) == 2 * 3 * 3 * 2 * 4
    assert len(metrics) == 2 * 3 * 3 * 2
    for row in estimates:
        n = int(row["n_paths"])
        assert int(row["independent_samples"]) == (n // 2 if row["method"] == "antithetic" else n)
        assert int(row["total_terminal_evaluations"]) == n + (64 if row["method"] == "control" else 0)
    for row in metrics:
        assert 0 <= float(row["coverage_ci_low"]) <= float(row["coverage"]) <= float(row["coverage_ci_high"]) <= 1
        assert float(row["rmse"]) >= 0
        assert float(row["rmse_ci_low"]) <= float(row["rmse_ci_high"])
    manifest = json.loads((out / "manifest.json").read_text())
    assert manifest["rng"]["bit_generator"] == "PCG64"
    assert manifest["config_sha256"] == hashlib.sha256(CONFIG.encode()).hexdigest()
    for filename, digest in manifest["artifact_sha256"].items():
        assert hashlib.sha256((out / filename).read_bytes()).hexdigest() == digest
    for name in ("accuracy.png", "calibration.png", "engineering.png", "robustness.png"):
        assert (out / name).stat().st_size > 10000
    assert (out / "RESULTS.md").stat().st_size > 1500


def test_numeric_reproducibility_ignores_timings(tmp_path):
    one, two = run(tmp_path, name="one"), run(tmp_path, name="two")
    for name in ("estimates.csv", "metrics.csv"):
        a, b = read_rows(one / name), read_rows(two / name)
        excluded = {"elapsed_seconds", "median_seconds", "time_rmse_squared", "time_efficiency_gain"}
        assert [{k: v for k, v in row.items() if k not in excluded} for row in a] == [
            {k: v for k, v in row.items() if k not in excluded} for row in b]


@pytest.mark.parametrize("old,new", [
    ("repeats = 4", "repeats = true"),
    ("repeats = 4", "repeats = 1"),
    ("sample_sizes = [128, 512]", "sample_sizes = [128, 127]"),
    ("sample_sizes = [128, 512]", "sample_sizes = [127, 512]"),
    ('["plain", "antithetic", "control"]', '["plain", "magic"]'),
    ("batch_sizes = [32, 128]", "batch_sizes = [32, true]"),
    ("dividend_yield = 0.0", "dividend_yield = 0.01"),
    ("seed = 431", "seed = -1"),
    ("strikes = [80.0, 100.0, 120.0]", "strikes = [80.0, 120.0]"),
    ("maturity_years = 1.0", "maturity_years = 0.0"),
])
def test_invalid_configs_leave_no_output(tmp_path, old, new):
    with pytest.raises((ValueError, TypeError)):
        run(tmp_path, CONFIG.replace(old, new))
    assert not (tmp_path / "out").exists()


def test_existing_output_refused_without_modification(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "sentinel").write_text("preserve")
    with pytest.raises(FileExistsError):
        run(tmp_path)
    assert list(out.iterdir()) == [out / "sentinel"]


def test_cli_executes_and_rejects_second_run(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text(CONFIG)
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    cmd = [sys.executable, "-m", "option_hedging.experiments.monte_carlo_demo",
           "--config", str(config), "--output-dir", str(tmp_path / "cli")]
    first = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    assert (tmp_path / "cli" / "metrics.csv").exists()
    second = subprocess.run(cmd, env=env, capture_output=True, text=True)
    assert second.returncode != 0
    assert "already exists" in second.stderr


@pytest.mark.parametrize("kind", ["call", "put"])
def test_scalar_and_vector_kernels_agree_on_identical_samples(kind):
    module = importlib.import_module("option_hedging.experiments.mc_benchmarks")
    spec = OptionSpec(100, 100, 1, .05, .2, kind)
    z = np.array([-3., -1., 0., 1., 3.])
    # Direct formula below is independent of either production kernel.
    terminal = 100 * np.exp(.03 + .2 * z)
    expected = np.exp(-.05) * np.maximum(terminal - 100 if kind == "call" else 100 - terminal, 0)
    assert module.scalar_payoff_mean(spec, z) == pytest.approx(float(expected.mean()), abs=2e-12)
    assert module.vector_payoff_mean(spec, z) == pytest.approx(float(expected.mean()), abs=2e-12)


def test_zero_sample_variance_does_not_claim_perfect_accuracy(tmp_path):
    # Extremely OTM contracts produce zero observed payoffs; report that limitation.
    cfg = CONFIG.replace("strikes = [80.0, 100.0, 120.0]", "strikes = [100.0, 10000.0]")
    out = run(tmp_path, cfg)
    rows = read_rows(out / "metrics.csv")
    row = next(r for r in rows if r["kind"] == "call" and r["strike"] == "10000.0")
    assert int(row["zero_se_repeats"]) == 4
    assert "zero observed variance" in (out / "RESULTS.md").read_text().lower()


@pytest.mark.filterwarnings("error")
def test_zero_rmse_at_baseline_still_produces_complete_report(tmp_path):
    cfg = CONFIG.replace("strike = 100.0", "strike = 1000000.0").replace(
        "strikes = [80.0, 100.0, 120.0]", "strikes = [100.0, 1000000.0]")
    out = run(tmp_path, cfg)
    assert json.loads((out / "manifest.json").read_text())["status"] == "completed"
    assert "n/a" in (out / "RESULTS.md").read_text()
