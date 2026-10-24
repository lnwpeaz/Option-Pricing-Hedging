"""Independent numerical integration with an explicit omitted-tail bound."""

import importlib
from dataclasses import replace

import pytest

from option_hedging.contracts import OptionSpec


BASE = OptionSpec(100, 100, 1, .05, .2, "call")


def reference(spec=BASE, **kwargs):
    return importlib.import_module("option_hedging.validation.payoff_reference").integrate_payoff(spec, **kwargs)


@pytest.mark.parametrize("kind,want", [("call", 10.450583572185565), ("put", 5.573526022256971)])
def test_independent_baseline_and_reported_numerical_uncertainty(kind, want):
    result = reference(replace(BASE, kind=kind))
    assert result.price == pytest.approx(want, abs=2e-10)
    assert result.quad_error_estimate >= 0
    assert 0 < result.tail_bound < 1e-28
    assert result.evaluations > 0


def test_coarse_truncation_error_is_bounded_and_tightening_reduces_tail_bound():
    rough = reference(normal_cutoff=4.)
    fine = reference(normal_cutoff=12.)
    assert abs(rough.price - 10.450583572185565) <= rough.tail_bound + rough.quad_error_estimate + 1e-12
    assert fine.tail_bound < rough.tail_bound


@pytest.mark.parametrize("kwargs,want", [({"maturity_years": 0, "spot": 110}, 10.),
                                         ({"volatility": 0}, 4.877057549928594)])
def test_deterministic_limits(kwargs, want):
    result = reference(replace(BASE, **kwargs))
    assert result.price == pytest.approx(want)
    assert result.tail_bound == result.quad_error_estimate == result.evaluations == 0


def test_reference_does_not_depend_on_project_pricers_or_gbm(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Independent reference called production pricing/simulation")
    for module, name in (("pricing.black_scholes", "price"), ("pricing.binomial", "price"),
                          ("pricing.monte_carlo", "price"), ("simulation.gbm", "terminal_from_normals")):
        monkeypatch.setattr(importlib.import_module("option_hedging." + module), name, forbidden)
    assert reference().price == pytest.approx(10.450583572185565, abs=2e-10)


@pytest.mark.parametrize("cutoff,error", [(True, TypeError), (3., ValueError), (float("inf"), ValueError)])
def test_invalid_quadrature_domain(cutoff, error):
    with pytest.raises(error):
        reference(normal_cutoff=cutoff)


@pytest.mark.parametrize("maturity", [1., 3.])
def test_nearly_coincident_kink_and_density_center_do_not_break_integration(maturity):
    import math
    call = reference(replace(BASE, maturity_years=maturity, risk_free_rate=-.02))
    put = reference(replace(BASE, maturity_years=maturity, risk_free_rate=-.02, kind="put"))
    assert call.price > 0
    assert put.price-call.price == pytest.approx(100 * math.expm1(.02 * maturity), abs=3e-10)
