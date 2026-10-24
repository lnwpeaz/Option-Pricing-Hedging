"""Exercise the real CRR experiment and its artifact/configuration contract."""

import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def cli(config, output):
    return subprocess.run(
        [sys.executable, "-m", "option_hedging.experiments.convergence_demo",
         "--config", str(config), "--output-dir", str(output)],
        capture_output=True, text=True, check=False,
        env=os.environ | {"PYTHONPATH": str(ROOT / "src")},
    )


def config_file(tmp_path, grid="[25, 50, 1000]"):
    # Baseline fixture supplies the full option section without depending on
    # the repository's chosen production convergence grid.
    text = (ROOT / "configs/baseline.toml").read_text().split("[convergence]")[0]
    file = tmp_path / "experiment.toml"
    file.write_text(text + "\n[convergence]\nsteps = " + grid + "\n")
    return file


def test_cli_records_prices_error_timings_and_reproduction_metadata(tmp_path):
    config = config_file(tmp_path)
    output = tmp_path / "convergence"
    result = cli(config, output)
    assert result.returncode == 0, result.stderr
    with (output / "convergence.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 6
    for kind in ("call", "put"):
        subset = [row for row in rows if row["kind"] == kind]
        assert [int(row["steps"]) for row in subset] == [25, 50, 1000]
        assert float(subset[-1]["absolute_error"]) < .003
        assert float(subset[-1]["absolute_error"]) < float(subset[0]["absolute_error"])
        for row in subset:
            assert float(row["elapsed_seconds"]) >= 0
            assert float(row["signed_error"]) == pytest.approx(
                float(row["tree_price"]) - float(row["analytic_price"]))
    assert (output / "convergence.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["config_sha256"] == hashlib.sha256(config.read_bytes()).hexdigest()
    assert manifest["effective_steps"] == [25, 50, 1000]
    assert manifest["source_hashes"]["pricing/binomial.py"]
    assert (output / "input_config.toml").read_bytes() == config.read_bytes()
    summary = json.loads((output / "summary.json").read_text())
    assert summary["largest_grid_steps"] == 1000
    assert summary["results"]["call"]["absolute_error"] < .003

    old = (output / "convergence.csv").read_bytes()
    assert cli(config, output).returncode != 0
    assert (output / "convergence.csv").read_bytes() == old


@pytest.mark.parametrize("grid", ["[0, 10]", "[True, 10]", "[10, 10]", "[20, 10]",
                                  "[10.0, 20]", "[10]", '"10,20"'])
def test_invalid_grid_is_rejected_without_creating_output(tmp_path, grid):
    # TOML booleans are lowercase; retain readable parameter names above.
    config = config_file(tmp_path, grid.replace("True", "true"))
    output = tmp_path / "bad"
    result = cli(config, output)
    assert result.returncode != 0
    assert "steps" in result.stderr.lower()
    assert not output.exists()


def test_dividends_are_rejected_without_creating_output(tmp_path):
    config = config_file(tmp_path)
    config.write_text(config.read_text().replace("dividend_yield = 0.0", "dividend_yield = 0.02"))
    output = tmp_path / "bad"
    result = cli(config, output)
    assert result.returncode != 0
    assert "dividend" in result.stderr.lower()
    assert not output.exists()


def test_invalid_probability_reports_failure_before_writing_output(tmp_path):
    config = config_file(tmp_path, "[1, 2]")
    config.write_text(config.read_text().replace("risk_free_rate = 0.05", "risk_free_rate = 1.0"))
    output = tmp_path / "bad"
    result = cli(config, output)
    assert result.returncode != 0
    assert "probability" in result.stderr.lower()
    assert not output.exists()
