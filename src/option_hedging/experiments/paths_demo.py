"""Exact GBM path lab: physical scenarios, paired RN checks and reusable paths."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
from time import perf_counter
import tomllib

import matplotlib.pyplot as plt
import numpy as np

from option_hedging import __version__
from option_hedging.analysis.path_plots import make_path_figures
from option_hedging.analysis.path_statistics import summarize_paths, summarize_validation
from option_hedging.simulation.gbm import simulate_paths
from option_hedging.simulation.time_grid import make_time_grid
from option_hedging.experiments.provenance import finalize_manifest


def _integer(name, value, minimum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


def _load(raw):
    config = tomllib.loads(raw.decode("utf-8"))
    if set(config) != {"market", "simulation", "validation"}:
        raise ValueError("Expected exactly [market], [simulation], [validation]")
    market, sim, validation = (config[key] for key in ("market", "simulation", "validation"))
    if set(market) != {"spot", "maturity_years", "risk_free_rate", "physical_drift", "volatility"}:
        raise ValueError("market requires spot, maturity_years, risk_free_rate, physical_drift, volatility")
    for name, value in market.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"market.{name} must be a finite real number")
        if not math.isfinite(value):
            raise ValueError(f"market.{name} must be finite")
    if market["spot"] <= 0 or market["maturity_years"] <= 0 or market["volatility"] < 0:
        raise ValueError("Demo spot/maturity must be positive and volatility nonnegative")
    if set(sim) != {"paths", "steps_per_year", "seed", "batch_size", "preview_paths"}:
        raise ValueError("simulation requires paths, steps_per_year, seed, batch_size, preview_paths")
    for name, minimum in (("paths", 2), ("steps_per_year", 1), ("seed", 0), ("batch_size", 1), ("preview_paths", 1)):
        _integer(f"simulation.{name}", sim[name], minimum)
    if sim["preview_paths"] > sim["paths"]:
        raise ValueError("preview_paths cannot exceed simulation.paths")
    if set(validation) != {"repeats", "paths"}:
        raise ValueError("validation requires repeats and paths")
    for name in ("repeats", "paths"):
        _integer(f"validation.{name}", validation[name], 2)
    return config, market, sim, validation


def _paired_paths(market, times, n_paths, batch_size, key):
    paths, elapsed = {}, {}
    for measure, drift_key in (("physical", "physical_drift"), ("risk_neutral", "risk_free_rate")):
        rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(key)))
        start = perf_counter()
        paths[measure] = simulate_paths(spot=market["spot"], drift=market[drift_key],
                                        volatility=market["volatility"], times=times, n_paths=n_paths,
                                        rng=rng, batch_size=batch_size)
        elapsed[measure] = perf_counter() - start
    return paths, elapsed


def _stats(paths, times, market, measure):
    return summarize_paths(paths, times, spot=market["spot"],
                           drift=market["physical_drift"] if measure == "physical" else market["risk_free_rate"],
                           volatility=market["volatility"], risk_free_rate=market["risk_free_rate"])


def _report(market, sim, validation, summary):
    terminal = summary["terminal_statistics"]
    p, q = terminal["physical"], terminal["risk_neutral"]
    v = summary["validation_summary"]
    return f"""# GBM market paths: the bridge from pricing to hedging

Executed model experiment; no market data or hedge trades are used. The output
is a reusable collection of simulated stock paths, not a forecast or trading P&L.

## Scenario and timing

S0={market['spot']:g}, maturity={market['maturity_years']:g} years,
physical drift mu={market['physical_drift']:.1%}, continuous risk-free rate r={market['risk_free_rate']:.1%},
constant annual volatility={market['volatility']:.1%}, no dividends.
Both measures use the same Brownian shocks. Physical drift is an assumed scenario
parameter, not an estimated expected market return. RN drift r is for pricing checks.

The main sample contains **{sim['paths']:,} paths and {summary['time_points']} time points**
({summary['intervals']} intervals). Grid dates are regular k/{sim['steps_per_year']} years
strictly before expiry, then exact expiry; the final step may be shorter.
The first {sim['preview_paths']} path IDs are shown without selecting attractive outcomes.

## Exact transitions

```text
S_next = S_now * exp((drift - sigma^2/2)*dt + sigma*sqrt(dt)*Z)
Z ~ N(0,1), independent across paths and intervals
```

Log increments are accumulated in batches before exponentiation. This is exact
at the selected grid dates under constant-parameter GBM, without Euler time-step
bias. It does not recover the continuous trajectory between grid dates.
The generator validates irregular times, positivity, finite ranges and explicit
drift, and deterministic limits consume no random samples.

## Main-sample terminal results

| Measure | Sample mean | Theoretical mean | Sample SD | SE of mean |
|---|---:|---:|---:|---:|
| Physical | {p['mean']:.6f} | {p['theoretical_mean']:.6f} | {p['standard_deviation']:.6f} | {p['standard_error']:.6f} |
| Risk-neutral | {q['mean']:.6f} | {q['theoretical_mean']:.6f} | {q['standard_deviation']:.6f} | {q['standard_error']:.6f} |

Under physical GBM, E[S_T]=S0*exp(mu*T). Under RN GBM,
E[exp(-r*T)*S_T]=S0. Main-sample discounted RN mean:
**{q['discounted_mean']:.6f}**, with sample SE **{q['discounted_standard_error']:.6f}**,
against theoretical {market['spot']:.6f}. A finite sample need not match exactly.

## Independent-repeat diagnostics

All {validation['repeats']} repeats are retained; each contains {validation['paths']:,} paths
per measure. The two measures share shocks within a repeat; different repeat IDs
have separate SeedSequence streams. The paired measures are not independent extra evidence.

| Measure | Ensemble terminal mean | Theory | Approx. 95% interval for ensemble mean |
|---|---:|---:|---:|
| Physical | {v['physical']['mean']:.6f} | {v['physical']['theoretical_mean']:.6f} | [{v['physical']['mean_ci_low']:.6f}, {v['physical']['mean_ci_high']:.6f}] |
| Risk-neutral | {v['risk_neutral']['mean']:.6f} | {v['risk_neutral']['theoretical_mean']:.6f} | [{v['risk_neutral']['mean_ci_low']:.6f}, {v['risk_neutral']['mean_ci_high']:.6f}] |

RN ensemble discounted mean={v['risk_neutral']['discounted_mean']:.6f}; approximate 95% interval
[{v['risk_neutral']['discounted_ci_low']:.6f}, {v['risk_neutral']['discounted_ci_high']:.6f}].
These intervals use variation across independent repeats. Individual intervals
and time-point mean bands are approximate and are not simultaneous confidence bands.
The 5th–95th percentile fan in paths.png describes dispersion across paths,
not uncertainty in the mean and not a calibrated forecast interval for real prices.

Terminal log-return diagnostics across the independent repeats:

| Measure | Mean log return | Theory | Mean sample log-return variance | Theory |
|---|---:|---:|---:|---:|
| Physical | {v['physical']['log_return_mean']:.6f} | {v['physical']['theoretical_log_return_mean']:.6f} | {v['physical']['log_return_variance']:.6f} | {v['physical']['theoretical_log_return_variance']:.6f} |
| Risk-neutral | {v['risk_neutral']['log_return_mean']:.6f} | {v['risk_neutral']['theoretical_log_return_mean']:.6f} | {v['risk_neutral']['log_return_variance']:.6f} | {v['risk_neutral']['theoretical_log_return_variance']:.6f} |

The theoretical log-return mean is (drift-sigma^2/2)*T and variance is sigma^2*T.
Their ensemble standard errors and every repeat's values are retained in summary.json
and validation.csv. Common shocks make the log-return variances of paired measures
the same up to floating-point rounding; they are not two independent confirmations.

## Computer Engineering and saved data

The physical matrix has shape ({sim['paths']}, {summary['time_points']}), dtype float64,
and data size **{summary['path_matrix_bytes'] / 2**20:.3f} MiB** (excluding its NPY header).
The demo also holds the RN matrix for paired diagnostics. Work is O(N*M); returned
matrix storage is O(N*M), and one reusable float shock buffer is O(batch_size*M).
At configured batch_size={sim['batch_size']}, that buffer uses up to
{summary['batch_float_buffer_bytes'] / 2**20:.3f} MiB. This is not total process RSS.
Single-call simulation times in summary.json are illustrative, not a performance benchmark.

paths.npy contains physical paths; times.npy contains their exact grid. Load them
with allow_pickle=False. They provide the same path IDs for future hedge-frequency
and transaction-cost comparisons. preview_paths.csv preserves the first fixed IDs;
terminal_results.csv preserves paired final prices; time_statistics.csv and
validation.csv retain uncertainty and all repeat IDs.

## Reproduction

```sh
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.paths_demo \\
  --config configs/gbm_paths.toml --output-dir reports/runs/my-gbm-paths
```

For the exact run use saved input_config.toml. Output folders must be new.
manifest.json records PCG64 seed construction, config, versions, platform, source
and artifact hashes. Fixed inputs/environment reproduce numerical outputs; times
and PNG bytes need not be stable across environments. RNG call shapes and library
versions are part of the reproducibility scope.

## Next step and limits

The next module is a self-financing short-call hedge ledger: opening premium,
stock trades, cash interest, transaction costs and terminal settlement. No hedge
effectiveness has been measured here. GBM excludes jumps, stochastic volatility,
liquidity constraints and changing spreads; its assumptions are explicit inputs.
"""


def _write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_demo(config_path: Path, output_dir: Path) -> Path:
    """Compute and validate before writing reusable paths into a new folder."""
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    raw = config_path.read_bytes()
    config, market, sim, validation_config = _load(raw)
    times = make_time_grid(maturity_years=market["maturity_years"], steps_per_year=sim["steps_per_year"])
    key = [3, 0, sim["seed"]]
    main, elapsed = _paired_paths(market, times, sim["paths"], sim["batch_size"], key)
    time_rows, terminal_stats, terminal_rows = [], {}, []
    for measure in ("physical", "risk_neutral"):
        stats = _stats(main[measure], times, market, measure)
        time_rows.extend(dict(measure=measure, **row) for row in stats)
        terminal_stats[measure] = stats[-1]
        terminal_rows.extend(dict(measure=measure, path_id=i, terminal_spot=float(value))
                             for i, value in enumerate(main[measure][:, -1]))
    validation = []
    for repeat in range(validation_config["repeats"]):
        repeat_key = [3, 1, repeat, sim["seed"]]
        pair, _ = _paired_paths(market, times, validation_config["paths"], sim["batch_size"], repeat_key)
        for measure in ("physical", "risk_neutral"):
            stat = _stats(pair[measure][:, -1:], times[-1:], market, measure)[0]
            validation.append(dict(measure=measure, repeat=repeat, seed_key=json.dumps(repeat_key), **stat))
    summary = dict(time_points=len(times), intervals=len(times) - 1,
                   path_matrix_bytes=main["physical"].nbytes,
                   paired_matrix_bytes=sum(p.nbytes for p in main.values()),
                   batch_float_buffer_bytes=min(sim["batch_size"], sim["paths"]) * (len(times) - 1) * 8,
                   simulation_seconds=elapsed, terminal_statistics=terminal_stats,
                   validation_summary=summarize_validation(validation))
    report = _report(market, sim, validation_config, summary)
    # Reject nonfinite statistics before creating an output directory.
    summary_json = json.dumps(summary, indent=2, allow_nan=False) + "\n"
    figures = make_path_figures(main["physical"], main["risk_neutral"], times, time_rows, validation,
                                market=market, preview_paths=sim["preview_paths"])
    try:
        output_dir.mkdir(parents=True, exist_ok=False)
        np.save(output_dir / "paths.npy", main["physical"], allow_pickle=False)
        np.save(output_dir / "times.npy", times, allow_pickle=False)
        preview = [dict(path_id=i, time_index=j, time_years=float(t), spot=float(main["physical"][i, j]))
                   for i in range(sim["preview_paths"]) for j, t in enumerate(times)]
        for filename, data in (("preview_paths.csv", preview), ("time_statistics.csv", time_rows),
                               ("terminal_results.csv", terminal_rows), ("validation.csv", validation)):
            _write_csv(output_dir / filename, data)
        (output_dir / "input_config.toml").write_bytes(raw)
        (output_dir / "effective_config.json").write_text(json.dumps(config, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        (output_dir / "summary.json").write_text(summary_json, encoding="utf-8")
        (output_dir / "RESULTS.md").write_text(report, encoding="utf-8")
        for name, figure in figures.items():
            figure.savefig(output_dir / name, dpi=160)
        source = Path(__file__).resolve().parents[1]
        manifest = dict(status="completed", experiment="exact_gbm_paths", path_measure="physical",
                        created_utc=datetime.now(timezone.utc).isoformat(),
                        config_sha256=hashlib.sha256(raw).hexdigest(),
                        rng=dict(bit_generator="PCG64", main_seed_key=key,
                                 validation_seed_key="[3, 1, repeat_id, simulation.seed]",
                                 paired_measures="Same key reinitializes local generators for identical Brownian shocks",
                                 layout="Path-major, consecutive standard_normal((batch_paths, intervals)) calls"),
                        path_array=dict(filename="paths.npy", dtype="float64", shape=list(main["physical"].shape),
                                        times="times.npy", preview_ids=list(range(sim["preview_paths"]))),
                        versions={"python": platform.python_version(), "option_hedging": __version__,
                                  **{name: version(name) for name in ("numpy", "matplotlib")}},
                        environment=dict(platform=platform.platform(), machine=platform.machine()),
                        source_hashes={str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in sorted(source.rglob("*.py"))},
                        artifact_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                         for p in sorted(output_dir.iterdir()) if p.is_file()})
        finalize_manifest(output_dir, manifest, config_bytes=raw,
                          entrypoint="option_hedging.experiments.paths_demo")
    finally:
        for figure in figures.values():
            plt.close(figure)
    return output_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/gbm_paths.toml"))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    destination = args.output_dir or Path("reports/runs") / datetime.now(timezone.utc).strftime("paths-%Y%m%dT%H%M%S%fZ")
    try:
        result = run_demo(args.config, destination)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, MemoryError) as error:
        parser.error(str(error))
    print(f"GBM path lab saved to {result.resolve()}")


if __name__ == "__main__":
    main()
