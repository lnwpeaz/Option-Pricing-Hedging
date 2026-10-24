"""Sensitivities verified against independent constants and finite differences."""

from dataclasses import replace
import pytest

from option_hedging.pricing import black_scholes as bs
from test_black_scholes import option


@pytest.mark.parametrize("kind,delta", [("call", 0.6368306511756191),
                                        ("put", -0.3631693488243809)])
def test_benchmark_greeks_and_vega_units(kind, delta):
    g = bs.greeks(option(kind=kind))
    assert g.delta == pytest.approx(delta, abs=1e-12)
    assert g.gamma == pytest.approx(0.018762017345846895, abs=1e-12)
    assert g.vega == pytest.approx(37.52403469169379, abs=1e-10)


@pytest.mark.parametrize("kind,spot,rate", [
    ("call", 80, .05), ("put", 120, .05),
    ("call", 100, -.02), ("put", 100, -.02),
])
def test_greeks_match_central_finite_differences(kind, spot, rate):
    spec = option(kind=kind, spot=spot, risk_free_rate=rate)
    g = bs.greeks(spec)
    h = .01
    up, mid, down = (bs.price(replace(spec, spot=spot + h)), bs.price(spec),
                     bs.price(replace(spec, spot=spot - h)))
    assert g.delta == pytest.approx((up - down) / (2 * h), rel=1e-6, abs=1e-8)
    assert g.gamma == pytest.approx((up - 2 * mid + down) / h**2, rel=1e-5)
    v = 1e-5
    fd = (bs.price(replace(spec, volatility=spec.volatility + v))
          - bs.price(replace(spec, volatility=spec.volatility - v))) / (2 * v)
    assert g.vega == pytest.approx(fd, rel=1e-7)


@pytest.mark.parametrize("kind,spot,delta", [
    ("call", 120, 1), ("call", 80, 0), ("put", 120, 0), ("put", 80, -1),
])
@pytest.mark.parametrize("boundary", ["expiry", "zero_volatility"])
def test_smooth_boundary_greeks(kind, spot, delta, boundary):
    spec = option(kind=kind, spot=spot, maturity_years=0 if boundary == "expiry" else 1,
                  volatility=0 if boundary == "zero_volatility" else .2,
                  risk_free_rate=0)
    g = bs.greeks(spec)
    assert (g.delta, g.gamma, g.vega) == (delta, 0, 0)


@pytest.mark.parametrize("time,sigma", [(0, .2), (1, 0), (0, 0)])
def test_kink_greeks_are_explicitly_undefined(time, sigma):
    with pytest.raises(ValueError, match="kink"):
        bs.greeks(option(maturity_years=time, volatility=sigma, risk_free_rate=0))


def test_tiny_positive_volatility_does_not_overflow_greek_density():
    g = bs.greeks(option(spot=110, risk_free_rate=0, volatility=1e-200))
    assert (g.delta, g.gamma, g.vega) == (1, 0, 0)


def test_greeks_support_representable_discounting_at_extreme_negative_rate():
    g = bs.greeks(option(kind="put", spot=1, strike=1e-100, risk_free_rate=-750))
    assert (g.delta, g.gamma, g.vega) == (-1, 0, 0)
