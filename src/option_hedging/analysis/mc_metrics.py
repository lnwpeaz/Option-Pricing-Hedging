"""Repeated-experiment diagnostics; distinguish sampling error from compute cost."""

from collections import defaultdict
import math

import numpy as np

from option_hedging.pricing.monte_carlo import METHODS, Z_95


def _ratio(numerator, denominator):
    return float(numerator / denominator) if denominator > 0 else None


def summarize_estimates(rows: list[dict], *, seed: int, bootstrap_repeats: int) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[(row["kind"], row["strike"], row["n_paths"], row["method"])].append(row)
    summaries = []
    for group_id, (key, group) in enumerate(sorted(groups.items())):
        kind, strike, n_paths, method = key
        errors = np.array([r["price"] - r["reference"] for r in group])
        se = np.array([r["standard_error"] for r in group])
        r = len(group)
        covered = sum(row["ci_low"] <= row["reference"] <= row["ci_high"] for row in group)
        coverage = covered / r
        z2 = Z_95 ** 2
        center = (coverage + z2 / (2 * r)) / (1 + z2 / r)
        half = Z_95 * math.sqrt(coverage * (1 - coverage) / r + z2 / (4 * r * r)) / (1 + z2 / r)
        rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([20, group_id, seed])))
        bootstrap = np.sqrt(np.mean(errors[rng.integers(0, r, size=(bootstrap_repeats, r))] ** 2, axis=1))
        lo, hi = np.quantile(bootstrap, [.025, .975])
        sd = float(np.std(errors, ddof=1))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        median_seconds = float(np.median([row["elapsed_seconds"] for row in group]))
        summaries.append(dict(kind=kind, strike=strike, n_paths=n_paths, method=method,
                              repeats=r, reference=group[0]["reference"], bias=float(errors.mean()),
                              bias_standard_error=sd / math.sqrt(r), empirical_sd=sd,
                              rmse=rmse, rmse_ci_low=float(lo), rmse_ci_high=float(hi),
                              mean_standard_error=float(se.mean()),
                              rms_standard_error=float(np.sqrt(np.mean(se ** 2))),
                              coverage=coverage, coverage_ci_low=max(0., center - half),
                              coverage_ci_high=min(1., center + half),
                              zero_se_repeats=int(np.count_nonzero(se == 0)),
                              median_seconds=median_seconds,
                              independent_samples=group[0]["independent_samples"],
                              total_terminal_evaluations=group[0]["total_terminal_evaluations"],
                              time_rmse_squared=median_seconds * rmse ** 2))
    plain = {(s["kind"], s["strike"], s["n_paths"]): s for s in summaries if s["method"] == "plain"}
    for row in summaries:
        base = plain[(row["kind"], row["strike"], row["n_paths"])]
        row["mse_gain"] = _ratio(base["rmse"] ** 2, row["rmse"] ** 2)
        row["work_normalized_gain"] = _ratio(base["rmse"] ** 2 * base["total_terminal_evaluations"],
                                             row["rmse"] ** 2 * row["total_terminal_evaluations"])
        row["time_efficiency_gain"] = _ratio(base["time_rmse_squared"], row["time_rmse_squared"])
    return summaries


def build_summary(metrics, kernels, batches, *, base_strike):
    largest = max(r["n_paths"] for r in metrics)
    selected = [r for r in metrics if r["strike"] == base_strike and r["n_paths"] == largest]
    slopes = []
    for kind in ("call", "put"):
        for method in METHODS:
            subset = [r for r in metrics if r["kind"] == kind and r["method"] == method
                      and r["strike"] == base_strike and r["rmse"] > 0]
            slope = float(np.polyfit(np.log([r["n_paths"] for r in subset]),
                                    np.log([r["rmse"] for r in subset]), 1)[0]) if len(subset) > 1 else None
            slopes.append(dict(kind=kind, method=method, log_rmse_slope=slope))
    medians = {name: float(np.median([r["elapsed_seconds"] for r in kernels if r["implementation"] == name]))
               for name in ("scalar", "vectorized")}
    batch_summary = [dict(batch_size=b, median_seconds=float(np.median([
        r["elapsed_seconds"] for r in batches if r["batch_size"] == b])),
        traced_peak_bytes=next(r["traced_peak_bytes"] for r in batches if r["batch_size"] == b))
        for b in sorted({r["batch_size"] for r in batches})]
    return dict(largest_n_paths=largest, baseline_results=selected, rmse_slopes=slopes,
                kernel_median_seconds=medians,
                kernel_speedup=_ratio(medians["scalar"], medians["vectorized"]),
                batch_benchmark=batch_summary,
                notes=["Pilot costs included in estimator timings and work counts.",
                       "Equal production paths is not exactly equal work for control.",
                       "Coverage and bootstrap RMSE intervals have finite-repeat uncertainty.",
                       "Normal CIs are approximate; zero observed variance is not proof of accuracy.",
                       "Kernel speedup excludes RNG and SE; it is not end-to-end speedup.",
                       "Allocation peaks are tracemalloc observations, not RSS.",
                       "Timing-dependent outputs vary; numerical output targets the recorded environment."])
