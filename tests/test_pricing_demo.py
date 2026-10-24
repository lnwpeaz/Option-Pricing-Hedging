"""Run the actual CLI, inspect artifacts, and protect previous research outputs."""

import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

CONFIG = Path(__file__).resolve().parents[1] / "configs" / "baseline.toml"


def cli(config, output):
    return subprocess.run(
        [sys.executable, "-m", "option_hedging.experiments.pricing_demo",
         "--config", str(config), "--output-dir", str(output)],
        capture_output=True, text=True, check=False,
        env=os.environ | {"PYTHONPATH": str(CONFIG.parents[1] / "src")},
    )


def test_cli_generates_real_prices_figures_and_reproducibility_metadata(tmp_path):
    output = tmp_path / "demo"
    result = cli(CONFIG, output)
    assert result.returncode == 0, result.stderr
    with (output / "baseline.csv").open() as stream:
        rows = list(csv.DictReader(stream))
    values = {row["kind"]: row for row in rows}
    assert abs(float(values["call"]["price"]) - 10.450583572185565) < 1e-10
    assert abs(float(values["put"]["price"]) - 5.573526022256971) < 1e-10
    assert float(values["call"]["vega_per_percentage_point"]) > 0.37
    assert (output / "pricing_and_greeks.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    with (output / "spot_sensitivity.csv").open() as stream:
        curve = list(csv.DictReader(stream))
    assert len(curve) > 10
    assert float(curve[-1]["call_price"]) > float(curve[0]["call_price"])
    assert float(curve[-1]["put_price"]) < float(curve[0]["put_price"])
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["config_sha256"] == hashlib.sha256(CONFIG.read_bytes()).hexdigest()
    assert manifest["source_hashes"]
    assert manifest["versions"]["scipy"]
    assert manifest["assumptions"]["dividend_yield"] == 0
    assert manifest["effective_option"]["spot"] == 100

    # Refusing a rerun prevents quietly rewriting previously inspected output.
    before = (output / "baseline.csv").read_bytes()
    repeated = cli(CONFIG, output)
    assert repeated.returncode != 0
    assert (output / "baseline.csv").read_bytes() == before


def test_demo_rejects_unsupported_dividends_before_writing_output(tmp_path):
    config = tmp_path / "invalid.toml"
    config.write_text(CONFIG.read_text().replace("dividend_yield = 0.0", "dividend_yield = 0.03"))
    output = tmp_path / "bad-run"
    result = cli(config, output)
    assert result.returncode != 0
    assert "dividend" in result.stderr.lower()
    assert not output.exists()
