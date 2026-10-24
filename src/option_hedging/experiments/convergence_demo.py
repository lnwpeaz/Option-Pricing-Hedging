"""Compare CRR step grids against analytic European call and put prices.

Consumes [option] and [convergence]. Results describe numerical approximation,
not hedge performance. Single-run elapsed times are illustrative, not benchmarks.
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
from time import perf_counter
import tomllib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from option_hedging import __version__
from option_hedging.contracts import OptionSpec
from option_hedging.pricing.binomial import price as tree_price
from option_hedging.pricing.black_scholes import price as analytic_price
from option_hedging.experiments.provenance import finalize_manifest


def run_demo(config_path: Path, output_dir: Path) -> Path:
    """Write a fresh convergence run; validate and calculate before creating output."""
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    raw = config_path.read_bytes()
    config = tomllib.loads(raw.decode("utf-8"))
    options = dict(config["option"])
    q = options.pop("dividend_yield", 0.0)
    if isinstance(q, bool) or not isinstance(q, (int, float)) or q != 0:
        raise ValueError("Only dividend_yield=0 is supported")
    spec = OptionSpec(**options)
    grid = config.get("convergence", {}).get("steps")
    if (not isinstance(grid, list) or len(grid) < 2
            or any(isinstance(n, bool) or not isinstance(n, int) or n <= 0 for n in grid)):
        raise ValueError("convergence.steps must be a list of at least two positive integers")
    if any(a >= b for a, b in zip(grid, grid[1:])):
        raise ValueError("convergence.steps must be strictly increasing with no duplicates")

    rows = []
    for kind in ("call", "put"):
        contract = replace(spec, kind=kind)
        reference = analytic_price(contract)
        for steps in grid:
            start = perf_counter()
            estimate = tree_price(contract, steps=steps)
            elapsed = perf_counter() - start
            rows.append(dict(kind=kind, steps=steps, tree_price=estimate,
                             analytic_price=reference, signed_error=estimate - reference,
                             absolute_error=abs(estimate - reference), elapsed_seconds=elapsed))
    summary = {
        "largest_grid_steps": grid[-1],
        "results": {kind: next(row for row in reversed(rows) if row["kind"] == kind)
                    for kind in ("call", "put")},
        "interpretation": "CRR error may oscillate across step counts; no monotonic convergence claim",
        "timing_note": "One observation per grid/kind; timings vary and are not a performance benchmark",
    }
    source_root = Path(__file__).resolve().parents[1]
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "experiment": "crr_convergence_demo",
        "effective_option": asdict(spec), "effective_steps": grid,
        "assumptions": {"exercise": "European", "dividend_yield": 0,
                        "rate": "continuous", "method": "CRR backward induction"},
        "config_scope": "[option] and [convergence]; [pricing].tree_steps and hedge/simulation sections are not executed",
        "config_sha256": hashlib.sha256(raw).hexdigest(),
        "source_hashes": {str(p.relative_to(source_root)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in sorted(source_root.rglob("*.py"))},
        "versions": {"python": platform.python_version(), "option_hedging": __version__,
                     **{name: version(name) for name in ("numpy", "scipy", "matplotlib")}},
    }
    output_dir.mkdir(parents=True, exist_ok=False)
    with (output_dir / "convergence.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for filename, data in (("summary.json", summary),):
        (output_dir / filename).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    (output_dir / "input_config.toml").write_bytes(raw)

    fig, axes = plt.subplots(2, 2, figsize=(12, 8), layout="constrained")
    for column, kind in enumerate(("call", "put")):
        subset = [row for row in rows if row["kind"] == kind]
        color = f"C{column}"
        ax = axes[0, column]
        ax.plot(grid, [row["tree_price"] for row in subset], "o-", color=color, label="CRR")
        ax.axhline(subset[0]["analytic_price"], color="0.3", ls="--", label="Black-Scholes")
        ax.set(xscale="log", xlabel="Tree steps", ylabel="Option premium", title=f"{kind.title()} price")
        ax.legend()
        error = np.array([row["absolute_error"] for row in subset])
        positive = error > 0
        if np.any(positive):
            axes[1, 0].loglog(np.array(grid)[positive], error[positive],
                              "o-" if column == 0 else "x--", color=color, label=kind)
        axes[1, 1].loglog(grid, [max(row["elapsed_seconds"], 1e-12) for row in subset],
                          "o-", color=color, label=kind)
    axes[1, 0].set(title="Absolute pricing error (may oscillate)", xlabel="Tree steps", ylabel="Absolute error")
    if axes[1, 0].lines:
        axes[1, 0].legend()
    else:
        axes[1, 0].text(.5, .5, "All errors are zero at recorded precision", ha="center", transform=axes[1, 0].transAxes)
    axes[1, 1].set(title="Elapsed time (single measurements)", xlabel="Tree steps", ylabel="Seconds")
    axes[1, 1].legend()
    for ax in axes.flat:
        ax.grid(alpha=.25)
    fig.suptitle(f"CRR Convergence | S={spec.spot:g}, K={spec.strike:g}, T={spec.maturity_years:g}, "
                 f"r={spec.risk_free_rate:.1%}, sigma={spec.volatility:.1%}", fontsize=14)
    try:
        fig.savefig(output_dir / "convergence.png", dpi=160)
    finally:
        plt.close(fig)
    finalize_manifest(output_dir, manifest, config_bytes=raw,
                      entrypoint="option_hedging.experiments.convergence_demo")
    return output_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/baseline.toml"))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    destination = args.output_dir or Path("reports/runs") / datetime.now(timezone.utc).strftime("convergence-%Y%m%dT%H%M%S%fZ")
    try:
        result = run_demo(args.config, destination)
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as error:
        parser.error(str(error))
    print(f"CRR convergence demo saved to {result.resolve()}")


if __name__ == "__main__":
    main()
