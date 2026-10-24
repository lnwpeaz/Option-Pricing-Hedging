"""Predeclared multi-regime audit keeps every result, including degenerate CIs."""

import csv
import importlib
import json
from pathlib import Path

import pytest


CONFIG = '''[grid]
spot=100.0
strikes=[100.0,120.0]
maturities=[0.01,1.0]
volatilities=[0.1,0.8]
rates=[-0.02,0.05]
tree_steps=[16,32]
[monte_carlo]
paths=256
repeats=4
pilot_paths=64
batch_size=128
seed=991
[checks]
analytic_absolute_tolerance=1e-7
uncertainty_floor=1e-10
'''


def run(tmp_path, config=CONFIG, name="out"):
    path = tmp_path / (name + ".toml")
    path.write_text(config)
    return importlib.import_module("option_hedging.experiments.validation_demo").run_demo(path, tmp_path / name)


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def test_all_grid_cells_and_reference_tree_mc_evidence_are_retained(tmp_path):
    out = run(tmp_path)
    assert len(rows(out / "reference_checks.csv")) == 32
    assert len(rows(out / "tree_checks.csv")) == 64
    raw = rows(out / "mc_estimates.csv")
    metrics = rows(out / "mc_metrics.csv")
    assert len(raw) == 32 * 3 * 4
    assert len(metrics) == 32 * 3
    assert all(float(r["absolute_difference"]) < 1e-7 for r in rows(out / "reference_checks.csv"))
    assert any(int(r["zero_se_repeats"]) > 0 for r in metrics)
    assert any(r["diagnostic_class"] != "regular" for r in metrics)
    for row in metrics:
        assert 0 <= float(row["coverage_ci_low"]) <= float(row["coverage"]) <= float(row["coverage_ci_high"]) <= 1
    summary = json.loads((out / "summary.json").read_text())
    assert summary["scenario_count"] == 32
    assert summary["analytic_checks_passed"] is True
    assert summary["mc_zero_se_cells"] > 0
    assert importlib.import_module("option_hedging.experiments.verify_run").verify_run(out)["source_recoverable"]
    for name in ("validation.png", "calibration.png"):
        assert (out / name).stat().st_size > 10000


def test_numerical_outputs_reproduce(tmp_path):
    one, two = run(tmp_path, name="one"), run(tmp_path, name="two")
    for name in ("reference_checks.csv", "tree_checks.csv", "mc_estimates.csv", "mc_metrics.csv"):
        assert (one / name).read_bytes() == (two / name).read_bytes()


@pytest.mark.parametrize("old,new", [
    ("paths=256", "paths=255"), ("repeats=4", "repeats=true"),
    ("rates=[-0.02,0.05]", "rates=[0.05,0.05]"),
    ("volatilities=[0.1,0.8]", "volatilities=[-0.1,0.8]"),
    ("tree_steps=[16,32]", "tree_steps=[0,32]"),
    ("seed=991", "seed=-1"), ("uncertainty_floor=1e-10", "uncertainty_floor=0.0"),
])
def test_invalid_predeclared_grid_does_not_create_output(tmp_path, old, new):
    with pytest.raises((ValueError, TypeError)):
        run(tmp_path, CONFIG.replace(old, new))
    assert not (tmp_path / "out").exists()


def test_existing_output_is_preserved(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "sentinel").write_text("keep")
    with pytest.raises(FileExistsError):
        run(tmp_path)
    assert list(out.iterdir()) == [out / "sentinel"]
