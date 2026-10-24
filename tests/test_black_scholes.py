"""Independent benchmarks, financial identities and meaningful boundary cases."""

from dataclasses import replace
import math

import pytest

from option_hedging.contracts import OptionSpec
from option_hedging.pricing import black_scholes as bs


def option(**changes):
    return OptionSpec(**(dict(spot=100.0, strike=100.0, maturity_years=1.0,
                       risk_free_rate=0.05, volatility=0.20, kind="call") | changes))


@pytest.mark.parametrize("kind,expected", [("call", 10.450583572185565),
                                           ("put", 5.573526022256971)])
def test_standard_no_dividend_benchmark(kind, expected):
    assert bs.price(option(kind=kind)) == pytest.approx(expected, abs=1e-10)


@pytest.mark.parametrize("spot,strike,rate,time,sigma", [
    (80, 110, 0.03, 0.25, 0.40), (150, 90, -0.02, 2.0, 0.15),
    (100, 100, 0, 1, 0.2), (1, 100, 0.05, 1, 0.20),
])
def test_put_call_parity_and_no_arbitrage_bounds(spot, strike, rate, time, sigma):
    spec = option(spot=spot, strike=strike, risk_free_rate=rate,
                  maturity_years=time, volatility=sigma)
    call, put = bs.price(spec), bs.price(replace(spec, kind="put"))
    discounted_strike = strike * math.exp(-rate * time)
    assert call - put == pytest.approx(spot - discounted_strike, abs=1e-12)
    assert max(spot - discounted_strike, 0) - 1e-12 <= call <= spot
    assert max(discounted_strike - spot, 0) - 1e-12 <= put <= discounted_strike


@pytest.mark.parametrize("kind,spot,expected", [
    ("call", 120, 20), ("call", 80, 0), ("put", 120, 0),
    ("put", 80, 20), ("call", 100, 0), ("put", 100, 0),
])
def test_expiry_returns_intrinsic_value(kind, spot, expected):
    assert bs.price(option(kind=kind, spot=spot, maturity_years=0)) == expected


@pytest.mark.parametrize("kind,spot,rate", [
    ("call", 90, 0.05), ("call", 110, -0.02),
    ("put", 90, 0.05), ("put", 110, -0.02),
])
def test_zero_volatility_is_discounted_deterministic_payoff(kind, spot, rate):
    terminal = spot * math.exp(rate)
    payoff = max(terminal - 100, 0) if kind == "call" else max(100 - terminal, 0)
    assert bs.price(option(kind=kind, spot=spot, risk_free_rate=rate,
                           volatility=0)) == pytest.approx(math.exp(-rate) * payoff)


@pytest.mark.parametrize("field,value", [
    ("spot", 0), ("spot", -1), ("strike", 0), ("strike", -1),
    ("maturity_years", -1), ("volatility", -0.2),
    ("spot", float("nan")), ("strike", float("inf")),
    ("maturity_years", float("inf")), ("volatility", float("nan")),
    ("risk_free_rate", float("-inf")), ("kind", "CALL"), ("kind", None),
    ("spot", True), ("volatility", "0.2"), ("risk_free_rate", None),
])
def test_rejects_invalid_contract_inputs(field, value):
    with pytest.raises((ValueError, TypeError)):
        option(**{field: value})


def test_deep_out_of_money_call_retains_small_positive_value():
    # Independent quadrature of discounted terminal payoff under a normal density.
    assert bs.price(option(spot=1)) == pytest.approx(3.37791731128902e-116, rel=1e-9, abs=0)


def test_price_increases_with_volatility():
    for kind in ("call", "put"):
        assert bs.price(option(kind=kind, volatility=0.4)) > bs.price(option(kind=kind))


@pytest.mark.parametrize("kind,expected", [("call", 10), ("put", 0)])
def test_extremely_small_positive_volatility_has_finite_limit(kind, expected):
    assert bs.price(option(kind=kind, spot=110, risk_free_rate=0,
                           volatility=1e-200)) == pytest.approx(expected)


def test_discounted_strike_does_not_overflow_in_intermediate_exponential():
    spec = option(kind="put", spot=1, strike=1e-100, risk_free_rate=-750)
    # Combine exponents independently; exp(750) alone exceeds floating-point range.
    expected = math.exp(math.log(1e-100) + 750) - 1
    assert bs.price(spec) == pytest.approx(expected, rel=1e-13)
