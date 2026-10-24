"""CRR checks against hand-worked trees and independent analytic benchmarks."""

from dataclasses import replace
import math

import numpy as np
import pytest

from option_hedging.contracts import OptionSpec
from option_hedging.pricing import binomial
from option_hedging.pricing.black_scholes import price as analytic_price


def spec(**changes):
    return OptionSpec(**(dict(spot=100, strike=100, maturity_years=1,
                             risk_free_rate=.05, volatility=.2, kind="call") | changes))


@pytest.mark.parametrize("steps,time,kind,expected", [
    (1, 1, "call", 40), (1, 1, "put", 20),
    (2, 2, "call", 48), (2, 2, "put", 12),
])
def test_hand_computed_tree_with_discounting(steps, time, kind, expected):
    # dt=1, u=2, d=.5, exp(r*dt)=1.25, p=.5; discount=.8.
    contract = spec(volatility=math.log(2), risk_free_rate=math.log(1.25),
                    maturity_years=time, kind=kind)
    assert binomial.price(contract, steps=steps) == pytest.approx(expected, abs=1e-11)


@pytest.mark.parametrize("kind,benchmark", [("call", 10.450583572185565),
                                           ("put", 5.573526022256971)])
def test_step_grid_approaches_analytic_benchmark(kind, benchmark):
    errors = [abs(binomial.price(spec(kind=kind), steps=n) - benchmark)
              for n in (25, 50, 100, 200, 400, 800)]
    assert errors[-1] < .003
    assert errors[-1] < errors[0] / 10
    # CRR errors may oscillate; do not require monotonic improvement on a mixed grid.


@pytest.mark.parametrize("kind,spot,rate", [
    ("call", 80, .03), ("put", 120, -.02), ("call", 130, -.02), ("put", 70, .03),
])
def test_off_strike_and_negative_rate_convergence(kind, spot, rate):
    contract = spec(kind=kind, spot=spot, risk_free_rate=rate)
    assert binomial.price(contract, steps=1000) == pytest.approx(analytic_price(contract), abs=.01)


@pytest.mark.parametrize("rate", [-.05, 0, .05])
def test_put_call_parity_and_bounds(rate):
    call = spec(risk_free_rate=rate)
    c = binomial.price(call, steps=200)
    p = binomial.price(replace(call, kind="put"), steps=200)
    discounted = 100 * math.exp(-rate)
    assert c - p == pytest.approx(100 - discounted, abs=2e-10)
    assert max(100 - discounted, 0) - 1e-10 <= c <= 100
    assert max(discounted - 100, 0) - 1e-10 <= p <= discounted


@pytest.mark.parametrize("kind,spot,expected", [("call", 120, 20), ("put", 80, 20),
                                              ("call", 80, 0), ("put", 120, 0)])
def test_expiry_intrinsic_value(kind, spot, expected):
    assert binomial.price(spec(kind=kind, spot=spot, maturity_years=0), steps=2) == expected


@pytest.mark.parametrize("kind,rate", [("call", .05), ("put", -.05)])
def test_zero_volatility_has_deterministic_value(kind, rate):
    contract = spec(kind=kind, volatility=0, risk_free_rate=rate)
    difference = 100 - 100 * math.exp(-rate)
    expected = max(difference, 0) if kind == "call" else max(-difference, 0)
    assert binomial.price(contract, steps=10) == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("steps", [0, -1, True, False, 1.5, "100", None])
def test_reject_invalid_step_counts_even_at_expiry(steps):
    with pytest.raises((ValueError, TypeError)):
        binomial.price(spec(maturity_years=0), steps=steps)


def test_accepts_numpy_integer_step_count():
    assert binomial.price(spec(), steps=np.int64(100)) == pytest.approx(
        binomial.price(spec(), steps=100))


@pytest.mark.parametrize("rate", [-1, 1])
def test_invalid_risk_neutral_probability_is_not_clipped(rate):
    with pytest.raises(ValueError, match="probability"):
        binomial.price(spec(risk_free_rate=rate), steps=1)


@pytest.mark.parametrize("rate", [-.2, .2])
def test_probability_endpoints_have_valid_deterministic_tree_value(rate):
    contract = spec(risk_free_rate=rate)
    payoff = max(100 * math.exp(rate) - 100, 0)
    assert binomial.price(contract, steps=1) == pytest.approx(math.exp(-rate) * payoff, abs=1e-11)


def test_tiny_positive_volatility_preserves_valid_probability():
    # exp(a) and exp(-a) both round to 1; expm1 must preserve the .5 probability.
    value = binomial.price(spec(volatility=1e-12, risk_free_rate=0), steps=1)
    assert value == pytest.approx(5e-11, rel=.001, abs=0)


def test_unrepresentable_tree_nodes_raise_instead_of_returning_nan():
    with pytest.raises(ValueError, match="range"):
        binomial.price(spec(volatility=100), steps=100)


def test_interior_probability_underflow_is_rejected_instead_of_erasing_premium():
    # a=700,b=-100 gives log(p)=-800: float p=0, although discounted
    # up-payoff has a representable value near 100. This is not a true p=0 endpoint.
    with pytest.raises(ValueError, match="probability.*range"):
        binomial.price(spec(volatility=700, risk_free_rate=-100), steps=1)


def test_interior_probability_rounding_to_one_is_rejected():
    with pytest.raises(ValueError, match="probability.*range"):
        binomial.price(spec(risk_free_rate=math.nextafter(.2, -math.inf)), steps=1)
