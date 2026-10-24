"""A diagnostic floor must not be asserted to prove roundoff or real inaccuracy."""

import math

import pytest

from option_hedging.analysis.validation_metrics import summarize_mc


def test_small_genuine_uncertainty_is_labeled_below_floor_not_proven_roundoff():
    rows = [dict(scenario_id=0, method="plain", price=p, reference=1e-11,
                 standard_error=1e-12, ci_low=p-2e-12, ci_high=p+2e-12,
                 n_paths=100, pilot_paths=0) for p in (9e-12, 1e-11, 1.1e-11)]
    result = summarize_mc(rows, uncertainty_floor=1e-10)[0]
    assert result["diagnostic_class"] == "below_diagnostic_floor"
    assert result["zero_se_repeats"] == 0
    assert result["rmse"] > 0


@pytest.mark.parametrize("scale", [1., 1e-170, 1e150])
def test_hand_worked_stress_metrics_preserve_failures_and_currency_scaling(scale):
    prices = [0., 2., 4., 4.]
    ses = [0., 1., 2., 0.]
    intervals = [(0., 0.), (0., 4.), (0., 8.), (4., 4.)]
    rows = [dict(scenario_id=0, method="control", price=p*scale, reference=2*scale,
                 standard_error=se*scale, ci_low=ci[0]*scale, ci_high=ci[1]*scale,
                 n_paths=100, pilot_paths=20) for p, se, ci in zip(prices, ses, intervals)]
    result = summarize_mc(rows, uncertainty_floor=.1*scale)[0]
    for name, expected in (("bias", .5), ("rmse", math.sqrt(3)),
                           ("empirical_sd", math.sqrt(11/3)),
                           ("rms_standard_error", math.sqrt(5/4))):
        assert result[name] / scale == pytest.approx(expected)
    assert result["sd_to_rms_se"] == pytest.approx(math.sqrt(44/15))
    assert result["coverage"] == .5
    assert result["coverage_ci_low"] == pytest.approx(.15003898915214947)
    assert result["coverage_ci_high"] == pytest.approx(.8499610108478506)
    assert result["zero_se_repeats"] == 2
    assert result["zero_se_nonzero_reference_repeats"] == 2
    assert result["uncovered_above_precision_floor"] == 2
    assert result["diagnostic_class"] == "partly_degenerate"
    assert result["total_terminal_evaluations"] == 120
