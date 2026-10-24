"""Cross-sectional GBM statistics and independent-repeat mean diagnostics."""

import math

import numpy as np


Z_95 = 1.959963984540054


def _moments(values):
    """Scaled, centered reductions avoid squaring tiny/large currency amounts."""
    scale = np.max(np.abs(values), axis=0)
    safe_scale = np.where(scale > 0, scale, 1.)
    relative = values / safe_scale
    anchor = relative[0].copy()
    relative -= anchor
    unit_mean = anchor + np.mean(relative, axis=0)
    unit_std = np.std(relative, axis=0, ddof=1)
    mean, std = unit_mean * safe_scale, unit_std * safe_scale
    se = (unit_std / math.sqrt(len(values))) * safe_scale
    if np.any((unit_std > 0) & ((std == 0) | (se == 0))):
        raise ValueError("Sample uncertainty underflowed")
    if not all(np.all(np.isfinite(v)) for v in (mean, std, se)):
        raise ValueError("Sample moments are outside floating-point range")
    return mean, std, se


def summarize_paths(paths, times, *, spot, drift, volatility, risk_free_rate):
    """Rows distinguish path-dispersion quantiles from uncertainty in the mean.

    Center on one observation before reduction: identical deterministic paths
    then have exactly zero sample SD even if their value is not a binary fraction.
    """
    try:
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            means, stds, ses = _moments(paths)
            log_means, log_stds, _ = _moments(np.log(paths) - math.log(spot))
            quantiles = np.quantile(paths, [.05, .5, .95], axis=0)
            theory_mean = np.exp(math.log(spot) + drift * times)
            theory_median = np.exp(math.log(spot) + (drift - .5 * volatility ** 2) * times)
            theory_std = theory_mean * np.sqrt(np.expm1(volatility ** 2 * times))
            discount = np.exp(-risk_free_rate * times)
            if np.any(discount <= 0):
                raise ValueError("Diagnostic discount factor underflowed")
            rows = [dict(time_years=float(t), n_paths=paths.shape[0], mean=float(means[j]),
                         standard_deviation=float(stds[j]), standard_error=float(ses[j]),
                         mean_ci_low=float(means[j] - Z_95 * ses[j]),
                         mean_ci_high=float(means[j] + Z_95 * ses[j]),
                         q05=float(quantiles[0, j]), median=float(quantiles[1, j]), q95=float(quantiles[2, j]),
                         theoretical_mean=float(theory_mean[j]), theoretical_median=float(theory_median[j]),
                         theoretical_std=float(theory_std[j]),
                         log_return_mean=float(log_means[j]), log_return_variance=float(log_stds[j] ** 2),
                         theoretical_log_return_mean=float((drift - .5 * volatility ** 2) * t),
                         theoretical_log_return_variance=float(volatility ** 2 * t),
                         discounted_mean=float(discount[j] * means[j]),
                         discounted_standard_error=float(discount[j] * ses[j])) for j, t in enumerate(times)]
    except (FloatingPointError, OverflowError) as error:
        raise ValueError("Path diagnostics are outside floating-point range") from error
    if not all(math.isfinite(v) for row in rows for v in row.values()):
        raise ValueError("Path diagnostics are not finite")
    return rows


def summarize_validation(rows):
    """An ensemble CI uses independent repeats, not the paired measures as extra data."""
    result = {}
    for measure in ("physical", "risk_neutral"):
        subset = [r for r in rows if r["measure"] == measure]
        values = np.array([r["mean"] for r in subset])
        discounted = np.array([r["discounted_mean"] for r in subset])
        mean, sd, se = (float(v) for v in _moments(values))
        dmean, _, dse = (float(v) for v in _moments(discounted))
        errors = np.array([r["standard_error"] for r in subset])
        error_scale = float(errors.max())
        rms_error = error_scale * float(np.sqrt(np.mean((errors / error_scale) ** 2))) if error_scale > 0 else 0.
        log_mean, _, log_mean_se = (float(v) for v in _moments(np.array([r["log_return_mean"] for r in subset])))
        log_variance, _, log_variance_se = (float(v) for v in _moments(np.array([r["log_return_variance"] for r in subset])))
        result[measure] = dict(repeats=len(subset), paths_per_repeat=subset[0]["n_paths"], mean=mean,
                               theoretical_mean=subset[0]["theoretical_mean"],
                               empirical_sd_of_means=sd, ensemble_standard_error=se,
                               mean_ci_low=mean - Z_95 * se, mean_ci_high=mean + Z_95 * se,
                               rms_reported_standard_error=rms_error,
                               log_return_mean=log_mean, log_return_mean_ensemble_se=log_mean_se,
                               theoretical_log_return_mean=subset[0]["theoretical_log_return_mean"],
                               log_return_variance=log_variance, log_return_variance_ensemble_se=log_variance_se,
                               theoretical_log_return_variance=subset[0]["theoretical_log_return_variance"],
                               discounted_mean=dmean, discounted_ensemble_standard_error=dse,
                               discounted_ci_low=dmean - Z_95 * dse, discounted_ci_high=dmean + Z_95 * dse)
    return result
