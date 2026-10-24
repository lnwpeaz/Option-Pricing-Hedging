"""Declared-domain numerical validation with an independent payoff integral."""

import argparse
import csv
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
from itertools import product
import json
import math
from pathlib import Path
import platform
import tomllib

import matplotlib.pyplot as plt
import numpy as np

from option_hedging.analysis.validation_metrics import summarize_mc
from option_hedging.analysis.validation_plots import make_validation_figures
from option_hedging.contracts import OptionSpec
from option_hedging.experiments.provenance import finalize_manifest
from option_hedging.pricing.black_scholes import price as analytic_price
from option_hedging.pricing.binomial import price as tree_price
from option_hedging.pricing.monte_carlo import METHODS, price as mc_price
from option_hedging.validation.payoff_reference import integrate_payoff


def _positive(name, value, *, allow_negative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite real")
    if not math.isfinite(value) or (not allow_negative and value <= 0):
        raise ValueError(f"{name} must be finite" + (" and positive" if not allow_negative else ""))


def _integer(name, value, minimum):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")


def _load(raw):
    config = tomllib.loads(raw.decode())
    if set(config) != {"grid", "monte_carlo", "checks"}:
        raise ValueError("Expected exactly [grid], [monte_carlo], [checks]")
    grid, mc, checks = (config[key] for key in ("grid", "monte_carlo", "checks"))
    if set(grid) != {"spot", "strikes", "maturities", "volatilities", "rates", "tree_steps"}:
        raise ValueError("Unexpected or missing grid keys")
    _positive("spot", grid["spot"])
    for key in ("strikes", "maturities", "volatilities", "rates", "tree_steps"):
        values = grid[key]
        if not isinstance(values, list) or not values:
            raise ValueError(f"{key} must be a nonempty increasing list")
        for value in values:
            if key == "tree_steps":
                _integer(key, value, 1)
            else:
                _positive(key, value, allow_negative=key == "rates")
        if any(a >= b for a, b in zip(values, values[1:])):
            raise ValueError(f"{key} must be strictly increasing")
    if set(mc) != {"paths", "repeats", "pilot_paths", "batch_size", "seed"}:
        raise ValueError("Unexpected or missing monte_carlo keys")
    for name, minimum in (("paths", 4), ("repeats", 2), ("pilot_paths", 2), ("batch_size", 2), ("seed", 0)):
        _integer(name, mc[name], minimum)
    if mc["paths"] % 2:
        raise ValueError("paths must be even for antithetic pairs")
    if set(checks) != {"analytic_absolute_tolerance", "uncertainty_floor"}:
        raise ValueError("Unexpected or missing checks keys")
    for name, value in checks.items():
        _positive(name, value)
    return config, grid, mc, checks


def _calculate(grid, mc):
    references, trees, estimates = [], [], []
    cells = product(grid["maturities"], grid["volatilities"], grid["strikes"], grid["rates"], ("call", "put"))
    for scenario_id, (maturity, volatility, strike, rate, kind) in enumerate(cells):
        spec = OptionSpec(grid["spot"], strike, maturity, rate, volatility, kind)
        identifying = dict(scenario_id=scenario_id, **asdict(spec))
        reference = analytic_price(spec)
        independent = integrate_payoff(spec)
        references.append(dict(**identifying, analytic_price=reference, quadrature_price=independent.price,
                               absolute_difference=abs(reference-independent.price),
                               quad_error_estimate=independent.quad_error_estimate,
                               truncated_tail_bound=independent.tail_bound,
                               quadrature_evaluations=independent.evaluations))
        for steps in grid["tree_steps"]:
            try:
                value = tree_price(spec, steps=steps)
                row = dict(price=value, absolute_error=abs(value-reference), status="ok", reason="")
            except ValueError as error:
                row = dict(price=None, absolute_error=None, status="rejected_grid", reason=str(error))
            trees.append(dict(**identifying, steps=steps, reference=reference, **row))
        for method_id, method in enumerate(METHODS):
            for repeat in range(mc["repeats"]):
                key = [4, scenario_id, repeat, method_id, mc["seed"]]
                rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence(key)))
                estimate = mc_price(spec, n_paths=mc["paths"], rng=rng, method=method,
                                    batch_size=mc["batch_size"], pilot_paths=mc["pilot_paths"])
                estimates.append(dict(**identifying, repeat=repeat, reference=reference,
                                      **asdict(estimate), seed_key=json.dumps(key)))
    return references, trees, estimates


def _summary(references, trees, metrics, checks):
    per_method = {}
    for method in METHODS:
        rows = [r for r in metrics if r["method"] == method]
        regular = [r for r in rows if r["diagnostic_class"] == "regular"]
        per_method[method] = dict(cells=len(rows), regular_cells=len(regular),
            regular_median_coverage=float(np.median([r["coverage"] for r in regular])) if regular else None,
            zero_se_cells=sum(r["zero_se_repeats"] > 0 for r in rows),
            zero_se_repeats=sum(r["zero_se_repeats"] for r in rows),
            below_floor_cells=sum(r["diagnostic_class"] == "below_diagnostic_floor" for r in rows),
            zero_se_nonzero_reference_repeats=sum(r["zero_se_nonzero_reference_repeats"] for r in rows),
            uncovered_above_precision_floor=sum(r["uncovered_above_precision_floor"] for r in rows))
    return dict(scenario_count=len(references), analytic_absolute_tolerance=checks["analytic_absolute_tolerance"],
                max_analytic_quadrature_difference=max(r["absolute_difference"] for r in references),
                max_quadrature_error_estimate=max(r["quad_error_estimate"] for r in references),
                max_tail_bound=max(r["truncated_tail_bound"] for r in references),
                analytic_checks_passed=all(r["absolute_difference"] <= checks["analytic_absolute_tolerance"] for r in references),
                tree_rejected_grid_count=sum(r["status"] != "ok" for r in trees),
                mc_zero_se_cells=sum(r["zero_se_repeats"] > 0 for r in metrics),
                uncertainty_floor=checks["uncertainty_floor"], methods=per_method)


def _report(grid, mc, checks, summary):
    table = "\n".join(f"| {method} | {row['regular_cells']} | {row['zero_se_cells']} | "
                       f"{row['zero_se_repeats']} | {row['below_floor_cells']} | "
                       f"{row['uncovered_above_precision_floor']} |" for method, row in summary["methods"].items())
    return f"""# Numerical validation across a predeclared parameter domain

This extends the baseline evidence. It checks prices/uncertainty under the same
European, constant-volatility, no-dividend model; it is not historical market
validation, a novel pricing model, or evidence of hedge effectiveness.

## Fixed design and independent reference

- Spot={grid['spot']:g}; strikes={grid['strikes']}; maturities={grid['maturities']} years.
- Volatilities={grid['volatilities']}; continuous rates={grid['rates']}; both call/put.
- Total option scenarios: **{summary['scenario_count']}**; CRR steps={grid['tree_steps']}.
- Three MC estimators, {mc['paths']:,} production paths and {mc['repeats']} independent repeats per cell.
- Control uses {mc['pilot_paths']} additional independent pilot paths per estimate.
- Every scenario/repeat is retained, including zero sample variance and CI failures.

The reference numerically integrates discounted payoff against the standard normal
density without calling the project analytic/CRR/MC/GBM implementation. Finite
integration limits are L=-12, U=12+sigma*sqrt(T), split at the payoff kink and density
centers. For a call, payoff <= discounted stock; for a put, payoff <= discounted
strike. Normal-tail probabilities therefore bound the omitted payoff tails.

QUADPACK's absolute integration error is an **estimate**, distinct from the analytic
truncation bound. It is not a proof of exact floating-point arithmetic. Very small
premiums below that error budget are not relatively resolved by this check.

Predeclared absolute analytic tolerance: **{checks['analytic_absolute_tolerance']:g} premium units**.
Maximum analytic/integral difference: **{summary['max_analytic_quadrature_difference']:.6g}**.
Largest quadrature error estimate: {summary['max_quadrature_error_estimate']:.6g};
largest truncated-tail bound: {summary['max_tail_bound']:.6g}.
All analytic comparisons within tolerance: **{summary['analytic_checks_passed']}**.
Tree rejected-grid rows retained: {summary['tree_rejected_grid_count']}.
CRR errors can oscillate; boxplots do not imply every scenario improves monotonically.
The reference-error figure uses a linear axis below 1e-12 and log scaling above it.
The CRR figure places errors <= {checks['uncertainty_floor']:g} at that display floor;
exact and tiny errors remain unchanged in the CSV.

## Monte Carlo limitations are measured

MC estimates are compared with the analytic reference after the independent
absolute-price check. Normal 95% CIs are approximate. Wilson intervals quantify
finite-repeat uncertainty in observed coverage; with only {mc['repeats']} repeats,
individual coverage differences are noisy. There is no multiple-testing claim that
one method is statistically best over all regimes.

| Method | Regular cells | Cells with any zero SE | Zero-SE runs | Cells below diagnostic floor | Uncovered runs with error above floor |
|---|---:|---:|---:|---:|---:|
{table}

The absolute uncertainty floor is predeclared at {checks['uncertainty_floor']:g} premium units.
Cells with RMS standard error at or below this floor are excluded from the regular
SE-calibration comparison. This can reflect genuinely small sampling uncertainty;
it does not prove roundoff. The floor never edits prices, raw CIs or coverage. Zero sample variance can mean a rare payoff was not
observed. A nearly linear payoff with a stock control may also have residual
uncertainty near floating-point precision. Both can make raw normal-CI coverage
misleading for different reasons. Cells with partial degeneracy are recorded
separately. Check mc_metrics.csv and join scenario_id to reference_checks.csv.

Reported coverage failures with tiny monetary errors are not claims of economically
large risk. Lower SE is not automatically more trustworthy. These observations
motivate caution before Monte Carlo uncertainty is used in future hedge analysis.
The existing analytic Greeks remain the planned hedge policy; this audit does not
introduce noisy MC hedge decisions.

## Reproduction and provenance

```sh
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.validation_demo \\
  --config configs/validation.toml --output-dir reports/runs/my-validation
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.verify_run reports/runs/my-validation
```

Raw data are reference_checks.csv, tree_checks.csv, mc_estimates.csv and mc_metrics.csv.
Numerical outputs use explicit PCG64 SeedSequence keys [4,scenario_id,repeat,method_id,seed].
source_snapshot.zip preserves actual source, input configuration, dependency versions
and REPLAY.md. Integrity verification checks saved bytes; numerical replay requires
the recorded Python/platform/library environment. Timings and figure bytes are not
replay acceptance criteria. Old hash-only examples remain historical and are not
retroactively described as containing recoverable source.

## Remaining substantive research

Complete the self-financing hedge ledger, validate accounting manually, and run
paired frequency/cost/volatility-misspecification experiments with uncertainty.
Those results answer the original research question. Adding more models or a UI
before that would not close the central evidence gap.

Primary implementation reference: [SciPy quad](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad.html).
"""


def _csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_demo(config_path: Path, output_dir: Path) -> Path:
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    raw = config_path.read_bytes()
    config, grid, mc, checks = _load(raw)
    references, trees, estimates = _calculate(grid, mc)
    metrics = summarize_mc(estimates, uncertainty_floor=checks["uncertainty_floor"])
    summary = _summary(references, trees, metrics, checks)
    report = _report(grid, mc, checks, summary)
    serialized_summary = json.dumps(summary, indent=2, allow_nan=False) + "\n"
    figures = make_validation_figures(references, trees, metrics, tolerance=checks["analytic_absolute_tolerance"],
                                      precision_floor=checks["uncertainty_floor"])
    try:
        output_dir.mkdir(parents=True, exist_ok=False)
        for filename, data in (("reference_checks.csv", references), ("tree_checks.csv", trees),
                               ("mc_estimates.csv", estimates), ("mc_metrics.csv", metrics)):
            _csv(output_dir / filename, data)
        (output_dir / "summary.json").write_text(serialized_summary, encoding="utf-8")
        (output_dir / "effective_config.json").write_text(json.dumps(config, indent=2, allow_nan=False)+"\n", encoding="utf-8")
        (output_dir / "input_config.toml").write_bytes(raw)
        (output_dir / "RESULTS.md").write_text(report, encoding="utf-8")
        for filename, figure in figures.items():
            figure.savefig(output_dir / filename, dpi=160)
        source = Path(__file__).resolve().parents[1]
        manifest = dict(experiment="declared_domain_validation", created_utc=datetime.now(timezone.utc).isoformat(),
                        config_sha256=hashlib.sha256(raw).hexdigest(),
                        rng=dict(bit_generator="PCG64", seed_key="[4, scenario_id, repeat, method_id, seed]",
                                 method_ids={m: i for i, m in enumerate(METHODS)}),
                        source_hashes={str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in sorted(source.rglob("*.py"))},
                        versions={"python": platform.python_version(), **{p: version(p) for p in ("numpy", "scipy", "matplotlib")}},
                        environment=dict(platform=platform.platform(), machine=platform.machine()))
        finalize_manifest(output_dir, manifest, config_bytes=raw, entrypoint="option_hedging.experiments.validation_demo")
    finally:
        for figure in figures.values():
            plt.close(figure)
    return output_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/validation.toml"))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output = args.output_dir or Path("reports/runs") / datetime.now(timezone.utc).strftime("validation-%Y%m%dT%H%M%S%fZ")
    try:
        result = run_demo(args.config, output)
    except (ValueError, TypeError, OSError, KeyError, OverflowError) as error:
        parser.error(str(error))
    print(f"Declared-domain validation saved to {result.resolve()}")
    summary = json.loads((result / "summary.json").read_text())
    if not summary["analytic_checks_passed"]:
        parser.exit(1, "Analytic/reference checks exceeded the predeclared tolerance; inspect saved evidence.\n")


if __name__ == "__main__":
    main()
