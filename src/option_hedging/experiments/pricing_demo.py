"""Run milestone 1: analytic prices, sensitivities, and reproducible figures.

This module is a learning demonstration, not the future hedge experiment runner.
Only the [option] section of the configuration is used and validated here.
"""

import argparse
import csv
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import tomllib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from option_hedging import __version__
from option_hedging.contracts import OptionSpec
from option_hedging.pricing.black_scholes import greeks, price
from option_hedging.experiments.provenance import finalize_manifest


def run_demo(config_path: Path, output_dir: Path) -> Path:
    """Create a new output directory; existing output is never overwritten."""
    raw_config = config_path.read_bytes()
    options = dict(tomllib.loads(raw_config.decode("utf-8"))["option"])
    q = options.pop("dividend_yield", 0.0)
    if isinstance(q, bool) or not isinstance(q, (int, float)) or q != 0:
        raise ValueError("Only dividend_yield=0 is supported")
    spec = OptionSpec(**options)
    if spec.maturity_years == 0 or spec.volatility == 0:
        raise ValueError("The sensitivity demo requires positive maturity and volatility")
    rows = []
    for kind in ("call", "put"):
        current = replace(spec, kind=kind)
        g = greeks(current)
        rows.append({"kind": kind, "price": price(current), **asdict(g),
                     "vega_per_percentage_point": g.vega / 100})

    spots = np.linspace(spec.spot * .5, spec.spot * 1.5, 101)
    curve = []
    for s in spots:
        call = replace(spec, spot=float(s), kind="call")
        put = replace(call, kind="put")
        g = greeks(call)
        curve.append({"spot": float(s), "call_price": price(call), "put_price": price(put),
                      "call_delta": g.delta, "put_delta": greeks(put).delta,
                      "gamma": g.gamma, "vega_per_percentage_point": g.vega / 100})
    sigmas = np.linspace(.01, max(.6, spec.volatility * 1.5), 101)
    vol_curve = [{"volatility": float(v),
                  "call_price": price(replace(spec, kind="call", volatility=float(v))),
                  "put_price": price(replace(spec, kind="put", volatility=float(v)))}
                 for v in sigmas]

    source_root = Path(__file__).resolve().parents[1]
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": "analytic_pricing_demo",
        "status": "Model-based analytic sensitivities; no hedge or market-data results",
        "effective_option": asdict(spec),
        "assumptions": {"dividend_yield": 0, "exercise": "European", "rate": "continuous"},
        "config_sha256": hashlib.sha256(raw_config).hexdigest(),
        "config_scope": "Only [option] is consumed; other sections are not executed",
        "source_hashes": {str(p.relative_to(source_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(source_root.rglob("*.py"))},
        "versions": {"python": platform.python_version(), "option_hedging": __version__,
                     **{p: version(p) for p in ("numpy", "scipy", "matplotlib")}},
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    for filename, data in (("baseline.csv", rows), ("spot_sensitivity.csv", curve),
                           ("volatility_sensitivity.csv", vol_curve)):
        with (output_dir / filename).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    # Preserve actual input bytes, even though this demo consumes only [option].
    (output_dir / "input_config.toml").write_bytes(raw_config)

    fig, axes = plt.subplots(2, 3, figsize=(14, 8), layout="constrained")
    panels = [
        (axes[0, 0], spots, curve, ["call_price", "put_price"], "Option premium", "Spot"),
        (axes[0, 1], spots, curve, ["call_delta", "put_delta"], "Delta", "Spot"),
        (axes[0, 2], spots, curve, ["gamma"], "Gamma", "Spot"),
        (axes[1, 0], spots, curve, ["vega_per_percentage_point"], "Vega per 1 percentage point", "Spot"),
        (axes[1, 1], sigmas, vol_curve, ["call_price", "put_price"], "Volatility sensitivity", "Annual volatility"),
    ]
    for ax, x, data, keys, title, xlabel in panels:
        for key in keys:
            ax.plot(x, [row[key] for row in data], label=key.replace("_", " "))
        ax.set(title=title, xlabel=xlabel)
        ax.grid(alpha=.25)
        if len(keys) > 1:
            ax.legend()
    axes[1, 2].axis("off")
    note = (f"European options, no dividends\nS={spec.spot:g}, K={spec.strike:g}, T={spec.maturity_years:g} years\n"
            f"r={spec.risk_free_rate:.1%}, sigma={spec.volatility:.1%}\n\n"
            f"Call: {rows[0]['price']:.6f}\nPut: {rows[1]['price']:.6f}\n\n"
            "Analytic model sensitivities\nNo market data or hedge results")
    axes[1, 2].text(.04, .95, note, va="top", fontsize=12, linespacing=1.6)
    fig.suptitle("Black-Scholes Pricing & Greeks | Milestone 1", fontsize=17)
    try:
        fig.savefig(output_dir / "pricing_and_greeks.png", dpi=160)
    finally:
        plt.close(fig)
    finalize_manifest(output_dir, manifest, config_bytes=raw_config,
                      entrypoint="option_hedging.experiments.pricing_demo")
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/baseline.toml"))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    destination = args.output_dir or Path("reports/runs") / datetime.now(timezone.utc).strftime("pricing-%Y%m%dT%H%M%S%fZ")
    try:
        result = run_demo(args.config, destination)
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
        parser.error(str(error))
    print(f"Pricing demo saved to {result.resolve()}")


if __name__ == "__main__":
    main()
