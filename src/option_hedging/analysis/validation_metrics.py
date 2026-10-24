"""Stress diagnostics retain raw CI failures and distinguish numerical floors."""

from collections import defaultdict
import math

import numpy as np


def _rms(values):
    scale = float(np.max(np.abs(values)))
    return scale * float(np.sqrt(np.mean((values / scale) ** 2))) if scale > 0 else 0.


def summarize_mc(rows, *, uncertainty_floor):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["scenario_id"], row["method"])].append(row)
    metrics = []
    for (scenario_id, method), group in sorted(groups.items()):
        errors = np.array([r["price"] - r["reference"] for r in group])
        ses = np.array([r["standard_error"] for r in group])
        covered = np.array([r["ci_low"] <= r["reference"] <= r["ci_high"] for r in group])
        n = len(group)
        coverage = float(covered.mean())
        z = 1.959963984540054
        center = (coverage + z*z / (2*n)) / (1 + z*z/n)
        half = z * math.sqrt(coverage*(1-coverage)/n + z*z/(4*n*n)) / (1+z*z/n)
        error_scale = float(np.max(np.abs(errors)))
        sd = error_scale * float(np.std(errors/error_scale, ddof=1)) if error_scale > 0 else 0.
        rms_se = _rms(ses)
        zero = int(np.count_nonzero(ses == 0))
        classification = ("zero_observed_variance" if zero == n else "below_diagnostic_floor" if rms_se <= uncertainty_floor
                          else "partly_degenerate" if zero else "regular")
        metrics.append(dict(scenario_id=scenario_id, method=method, repeats=n,
                            reference=group[0]["reference"], bias=float(np.mean(errors)), rmse=_rms(errors),
                            empirical_sd=sd, rms_standard_error=rms_se,
                            sd_to_rms_se=sd/rms_se if rms_se > uncertainty_floor else None,
                            coverage=coverage, coverage_ci_low=max(0., center-half), coverage_ci_high=min(1., center+half),
                            zero_se_repeats=zero,
                            zero_se_nonzero_reference_repeats=sum(r["standard_error"] == 0 and r["reference"] > 0 for r in group),
                            uncovered_above_precision_floor=int(np.count_nonzero(~covered & (np.abs(errors) > uncertainty_floor))),
                            diagnostic_class=classification,
                            total_terminal_evaluations=group[0]["n_paths"]+group[0]["pilot_paths"]))
    return metrics
