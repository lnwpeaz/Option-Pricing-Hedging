"""A diagnostic figure must retain failed comparisons beyond the target tolerance."""

import matplotlib.pyplot as plt
from option_hedging.analysis.validation_metrics import summarize_mc
from option_hedging.analysis.validation_plots import make_validation_figures


def test_failed_reference_check_remains_visible_in_figure():
    references = [dict(scenario_id=0, absolute_difference=1e-3)]
    trees = [dict(steps=32, status="ok", absolute_error=.01)]
    rows = [dict(scenario_id=0, method=method, price=price, reference=1.,
                 standard_error=.1, ci_low=price-.2, ci_high=price+.2,
                 n_paths=100, pilot_paths=0)
            for method in ("plain", "antithetic", "control") for price in (.95, 1.05)]
    metrics = summarize_mc(rows, uncertainty_floor=1e-10)
    figures = make_validation_figures(references, trees, metrics, tolerance=1e-7,
                                      precision_floor=1e-10)
    try:
        low, high = figures["validation.png"].axes[0].get_ylim()
        assert low <= 1e-3 <= high
    finally:
        for figure in figures.values():
            plt.close(figure)
