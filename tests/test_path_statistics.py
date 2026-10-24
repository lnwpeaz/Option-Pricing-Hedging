"""Hand-worked statistics remain meaningful across currency scales."""

import numpy as np
import pytest

from option_hedging.analysis.path_statistics import summarize_paths, summarize_validation


@pytest.mark.parametrize("scale", [1., 1e-170, 1e150])
def test_cross_sectional_sample_se_and_quantiles_preserve_scale(scale):
    paths = np.array([[1., 1.], [1., 2.], [1., 3.]]) * scale
    rows = summarize_paths(paths, np.array([0., 1.]), spot=scale, drift=0., volatility=.2, risk_free_rate=0.)
    assert rows[0]["standard_error"] == 0
    assert rows[1]["mean"] / scale == pytest.approx(2.)
    assert rows[1]["standard_deviation"] / scale == pytest.approx(1.)
    assert rows[1]["standard_error"] / scale == pytest.approx(1 / np.sqrt(3))
    assert rows[1]["q05"] / scale == pytest.approx(1.1)
    assert rows[1]["q95"] / scale == pytest.approx(2.9)


@pytest.mark.parametrize("scale", [1., 1e-170, 1e150])
def test_repeat_uncertainty_counts_independent_repeats_and_preserves_scale(scale):
    rows = [dict(measure=measure, n_paths=10, mean=value * scale, discounted_mean=value * scale,
                 standard_error=.5 * scale, theoretical_mean=2 * scale,
                 log_return_mean=(value - 2) * .1, log_return_variance=.04,
                 theoretical_log_return_mean=0., theoretical_log_return_variance=.04)
            for measure in ("physical", "risk_neutral") for value in (1., 2., 3.)]
    result = summarize_validation(rows)
    for measure in ("physical", "risk_neutral"):
        summary = result[measure]
        assert summary["repeats"] == 3
        assert summary["mean"] / scale == pytest.approx(2)
        assert summary["ensemble_standard_error"] / scale == pytest.approx(1 / np.sqrt(3))
        assert summary["rms_reported_standard_error"] / scale == pytest.approx(.5)
