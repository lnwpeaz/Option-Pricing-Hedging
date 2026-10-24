"""Monte Carlo research lab: repeated accuracy, uncertainty and CPU benchmarks."""

import argparse
from contextlib import redirect_stdout
import csv
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import io
from importlib.metadata import version
import json
import os
from pathlib import Path
import platform
from time import perf_counter
import tomllib

import matplotlib.pyplot as plt
import numpy as np

from option_hedging import __version__
from option_hedging.analysis.mc_metrics import build_summary, summarize_estimates
from option_hedging.analysis.mc_plots import make_figures
from option_hedging.contracts import OptionSpec
from option_hedging.experiments.mc_benchmarks import run_benchmarks
from option_hedging.experiments.provenance import finalize_manifest
from option_hedging.pricing.black_scholes import price as analytic_price
from option_hedging.pricing.monte_carlo import METHODS, price


def _integer(name, value, minimum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def _grid(name, values, minimum, *, even=False):
    if not isinstance(values, list) or len(values) < 2:
        raise ValueError(f"{name} must contain at least two increasing integers")
    for value in values:
        _integer(name, value, minimum)
        if even and value % 2:
            raise ValueError(f"{name} must be even for antithetic pairs")
    if any(a >= b for a, b in zip(values, values[1:])):
        raise ValueError(f"{name} must be strictly increasing")
    return values


def _load_config(raw):
    config = tomllib.loads(raw.decode("utf-8"))
    if set(config) != {"option", "monte_carlo", "benchmark"}:
        raise ValueError("Expected exactly [option], [monte_carlo], [benchmark]")
    options = dict(config["option"])
    dividend = options.pop("dividend_yield", 0.)
    if isinstance(dividend, bool) or not isinstance(dividend, (int, float)) or dividend != 0:
        raise ValueError("Only dividend_yield=0 is supported")
    spec = OptionSpec(**options)
    if spec.maturity_years <= 0 or spec.volatility <= 0:
        raise ValueError("Research demo requires positive maturity and volatility")
    mc = config["monte_carlo"]
    required = {"sample_sizes", "strikes", "methods", "repeats", "seed", "batch_size", "pilot_paths", "bootstrap_repeats"}
    if set(mc) != required:
        raise ValueError(f"monte_carlo keys must be {sorted(required)}")
    _grid("sample_sizes", mc["sample_sizes"], 4, even=True)
    methods = mc["methods"]
    if not isinstance(methods, list) or len(methods) != 3 or set(methods) != set(METHODS):
        raise ValueError(f"methods must contain each of {METHODS} exactly once")
    for key, minimum in (("repeats", 2), ("seed", 0), ("batch_size", 2), ("pilot_paths", 2), ("bootstrap_repeats", 100)):
        _integer(key, mc[key], minimum)
    strikes = mc["strikes"]
    if (not isinstance(strikes, list) or len(strikes) < 2 or any(
        isinstance(x, bool) or not isinstance(x, (float, int)) or not np.isfinite(x) or x <= 0 for x in strikes)):
        raise ValueError("strikes must contain at least two finite positive numbers")
    if any(a >= b for a, b in zip(strikes, strikes[1:])) or spec.strike not in strikes:
        raise ValueError("strikes must increase and include the baseline option strike")
    benchmark = config["benchmark"]
    if set(benchmark) != {"n_paths", "batch_sizes", "repeats", "seed"}:
        raise ValueError("benchmark keys must be n_paths, batch_sizes, repeats, seed")
    _integer("benchmark.n_paths", benchmark["n_paths"], 4)
    _integer("benchmark.repeats", benchmark["repeats"], 3)
    _integer("benchmark.seed", benchmark["seed"], 0)
    _grid("benchmark.batch_sizes", benchmark["batch_sizes"], 2)
    return spec, mc, benchmark, config


def _experiment(spec, mc):
    rows = []
    # Warm up every estimator; these draws are outside the recorded experiment streams.
    for method in METHODS:
        price(spec, n_paths=128, rng=np.random.Generator(np.random.PCG64(0)),
              method=method, batch_size=mc["batch_size"], pilot_paths=mc["pilot_paths"])
    for kind_id, kind in enumerate(("call", "put")):
        for strike_id, strike in enumerate(mc["strikes"]):
            contract = replace(spec, kind=kind, strike=strike)
            reference = analytic_price(contract)
            for n in mc["sample_sizes"]:
                for repeat in range(mc["repeats"]):
                    # Rotate method order so the same method is not always measured first.
                    methods = mc["methods"][repeat % 3:] + mc["methods"][:repeat % 3]
                    for method in methods:
                        key = [1, kind_id, strike_id, n, repeat, METHODS.index(method), mc["seed"]]
                        rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(key)))
                        start = perf_counter()
                        result = price(contract, n_paths=n, rng=rng, method=method,
                                       batch_size=mc["batch_size"], pilot_paths=mc["pilot_paths"])
                        elapsed = perf_counter() - start
                        rows.append(dict(kind=kind, strike=float(strike), reference=reference,
                                         repeat=repeat, **asdict(result),
                                         total_terminal_evaluations=n + result.pilot_paths,
                                         elapsed_seconds=elapsed, seed_key=json.dumps(key)))
    return sorted(rows, key=lambda r: (r["kind"], r["strike"], r["n_paths"], r["method"], r["repeat"]))


def _results_text(spec, mc, benchmark, summary):
    table = []
    for row in summary["baseline_results"]:
        gain = f"{row['mse_gain']:.2f}" if row["mse_gain"] is not None else "n/a"
        table.append(f"| {row['kind']} | {row['method']} | {row['bias']:.6f} | {row['rmse']:.6f} | "
                     f"{row['mean_standard_error']:.6f} | {row['coverage']:.1%} | "
                     f"{gain} | {row['median_seconds'] * 1000:.3f} |")
    slopes = "\n".join(f"- {r['kind']} / {r['method']}: {r['log_rmse_slope']:.3f}" for r in summary["rmse_slopes"]
                       if r["log_rmse_slope"] is not None)
    batch_table = "\n".join(f"| {r['batch_size']:,} | {r['median_seconds'] * 1000:.3f} | "
                            f"{r['traced_peak_bytes'] / 2**20:.3f} |" for r in summary["batch_benchmark"])
    return f"""# Monte Carlo pricing: accuracy, uncertainty and computational efficiency

This is an executed model-based numerical experiment, not trading performance.
European options without dividends; S={spec.spot:g}, baseline K={spec.strike:g},
T={spec.maturity_years:g} years, r={spec.risk_free_rate:.1%}, sigma={spec.volatility:.1%}.
Prices use exact terminal GBM under risk-neutral drift r. Black-Scholes is used
only as the experiment's analytic reference, separate from the MC estimator.

## Experiment design

- Production sample sizes: {mc['sample_sizes']}.
- Strikes: {mc['strikes']}; both call and put; all three methods; {mc['repeats']} independent repeats per cell.
- Control beta uses {mc['pilot_paths']} additional independent pilot paths per run.
- Antithetic N counts terminal evaluations; N/2 independent pair averages determine SE.
- PCG64 with SeedSequence identifiers; every raw seed key is in estimates.csv.
- RMSE percentile intervals use {mc['bootstrap_repeats']} bootstrap resamples of independent repeats.
- Coverage intervals are 95% Wilson intervals for the proportion of runs whose normal CI contains truth.

## Baseline strike, largest sample size: N={summary['largest_n_paths']:,}

| Kind | Method | Bias | RMSE | Mean SE | CI coverage | MSE gain vs plain | Median ms |
|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(table)}

MSE gain compares equal production N. Control uses extra pilot work: consult
work_normalized_gain and time_efficiency_gain in metrics.csv before judging cost.
Reported gains are empirical ratios with finite-repeat uncertainty, not guaranteed
speedups. Lower time*RMSE^2 is a useful local efficiency diagnostic; it is not an
equal-wall-clock experiment or a universal performance ranking.

Log-log empirical RMSE slopes across the sample grid (the MC asymptotic reference is -0.5):

{slopes}

The baseline is one payoff regime. robustness.png and the full metrics.csv retain
all strike/kind scenarios; benefits can change when a payoff becomes rare or nearly linear.
Raw signed errors, CI endpoints and fitted beta values are retained in estimates.csv.

## Computer Engineering measurements

Kernel-only benchmark: {benchmark['n_paths']:,} identical pre-generated normals,
{benchmark['repeats']} timed repetitions after warm-up, alternating scalar/vector order.
Median scalar/vector speedup on this run: **{summary['kernel_speedup']:.2f}x**.
Both kernels compute discounted payoff means. RNG generation and sample uncertainty
are excluded from both; vectorized array allocation and validation are included.
This is not the speedup of a complete MC price, and the Python scalar baseline
is educational rather than a tuned compiled competitor.

Complete plain-MC batching benchmark includes RNG, payoff, validation and sample
statistics; Generator construction is excluded from every timed call. Batch order
alternates. Allocation is measured in a separate untimed pass with tracemalloc.

| Batch size | Median complete price ms | Peak traced MiB |
|---:|---:|---:|
{batch_table}

Time complexity is O(N + pilot paths); peak numerical workspace is O(batch size).
Exact terminal sampling avoids building N x 253 path matrices for European prices.
The allocation figures are observed Python/NumPy traced allocations, not RSS or a
guaranteed byte budget. BLAS/threading, CPU caches, scheduling, thermals, sample size
and tracing overhead affect measurements. No GPU or multicore implementation was measured.

## Statistical and numerical limits

Normal confidence intervals are approximate. A single interval need not contain
truth. Finite-repeat coverage itself is uncertain. Zero observed variance can mean
no rare payoffs were sampled; it does not establish an exact price. zero_se_repeats
is recorded explicitly. Pilot-fitted control estimates and intervals are not clipped
to theoretical option bounds. Overflow, terminal underflow and unrepresentable
moments raise explicit errors; arbitrary extreme floating-point inputs are not supported.

## Reproduction and artifacts

From the project root, choose a new output folder:

```sh
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.monte_carlo_demo \\
  --config configs/monte_carlo.toml --output-dir reports/runs/my-monte-carlo
```

For this exact run use the saved input_config.toml. manifest.json records source,
config and output SHA-256 hashes, versions, platform and RNG derivation. Same inputs
and recorded environment reproduce numerical estimates; timings and figure bytes
are not guaranteed across environments. NumPy does not promise identical samples
across every build or different RNG call shapes. This run does not simulate hedging.
"""


def _write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_demo(config_path: Path, output_dir: Path) -> Path:
    """Validate and compute before creating a fresh output directory."""
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    raw = config_path.read_bytes()
    spec, mc, benchmark, config = _load_config(raw)
    rows = _experiment(spec, mc)
    metrics = summarize_estimates(rows, seed=mc["seed"], bootstrap_repeats=mc["bootstrap_repeats"])
    kernels, batches = run_benchmarks(spec, **benchmark)
    summary = build_summary(metrics, kernels, batches, base_strike=spec.strike)
    report = _results_text(spec, mc, benchmark, summary)
    figures = make_figures(metrics, rows, kernels, batches, spec, summary)
    try:
        output_dir.mkdir(parents=True, exist_ok=False)
        for name, data in (("estimates.csv", rows), ("metrics.csv", metrics),
                           ("kernel_benchmark.csv", kernels), ("batch_benchmark.csv", batches)):
            _write_csv(output_dir / name, data)
        for filename, data in (("effective_config.json", config), ("summary.json", summary)):
            (output_dir / filename).write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        (output_dir / "input_config.toml").write_bytes(raw)
        (output_dir / "RESULTS.md").write_text(report, encoding="utf-8")
        for name, fig in figures.items():
            fig.savefig(output_dir / name, dpi=160)
        runtime_info = io.StringIO()
        try:
            build_config = np.show_config(mode="dicts")
        except TypeError:  # NumPy 1.24/1.25 predates the mode argument.
            with redirect_stdout(runtime_info):
                np.show_config()
        else:
            runtime_info.write(json.dumps(build_config, indent=2, default=str))
        (output_dir / "numpy_config.txt").write_text(runtime_info.getvalue(), encoding="utf-8")
        source = Path(__file__).resolve().parents[1]
        manifest = dict(status="completed", experiment="monte_carlo_research_lab",
                        created_utc=datetime.now(timezone.utc).isoformat(),
                        config_sha256=hashlib.sha256(raw).hexdigest(),
                        effective_option=asdict(spec),
                        rng=dict(bit_generator="PCG64", seed_sequence="[1, kind_id, strike_id, N, repeat, method_id, seed]",
                                 kind_ids={"call": 0, "put": 1}, method_ids={m: i for i, m in enumerate(METHODS)},
                                 strike_ids="zero-based index in effective_config.monte_carlo.strikes",
                                 pilot="pilot draws precede disjoint production draws within each control stream",
                                 bootstrap="[20, sorted_metric_group_id, seed]",
                                 benchmark="normals: [9, seed]; batches: [10, repeat, seed]; warmup/allocation: seed"),
                        source_hashes={str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in sorted(source.rglob("*.py"))},
                        versions={"python": platform.python_version(), "option_hedging": __version__,
                                  **{name: version(name) for name in ("numpy", "scipy", "matplotlib")}},
                        environment=dict(platform=platform.platform(), machine=platform.machine(), processor=platform.processor(),
                                         logical_cpu_count=os.cpu_count(),
                                         thread_environment={name: os.environ.get(name) for name in (
                                             "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                                             "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS")},
                                         numpy_build="numpy_config.txt"),
                        artifact_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                         for p in sorted(output_dir.iterdir()) if p.is_file()})
        finalize_manifest(output_dir, manifest, config_bytes=raw,
                          entrypoint="option_hedging.experiments.monte_carlo_demo")
    finally:
        for figure in figures.values():
            plt.close(figure)
    return output_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/monte_carlo.toml"))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    destination = args.output_dir or Path("reports/runs") / datetime.now(timezone.utc).strftime("mc-%Y%m%dT%H%M%S%fZ")
    try:
        result = run_demo(args.config, destination)
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RuntimeError) as error:
        parser.error(str(error))
    print(f"Monte Carlo research lab saved to {result.resolve()}")


if __name__ == "__main__":
    main()
