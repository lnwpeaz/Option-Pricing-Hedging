"""Numerical/statistical contracts; no single-seed 'truth must be inside CI' test."""

from dataclasses import replace
import math

import numpy as np
import pytest

from option_hedging.contracts import OptionSpec
from option_hedging.pricing import monte_carlo as mc
from option_hedging.simulation import gbm


BASE = OptionSpec(100, 100, 1, .05, .2, "call")


def estimate(spec=BASE, **kwargs):
    args = dict(n_paths=2000, rng=np.random.Generator(np.random.PCG64(17)))
    args.update(kwargs)
    return mc.price(spec, **args)


def test_terminal_transform_has_explicit_drift_and_exact_limit():
    values = gbm.terminal_from_normals(spot=100, drift=.08, volatility=.2,
                                     maturity_years=1, normals=np.array([-1., 0., 1.]))
    np.testing.assert_allclose(values, [86.93582353988059, 106.18365465453596, 129.69300866657718])
    deterministic = gbm.terminal_from_normals(spot=100, drift=.08, volatility=0,
                                            maturity_years=1, normals=np.array([-2., 2.]))
    np.testing.assert_allclose(deterministic, [108.32870676749586] * 2)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_plain_discounted_payoffs_and_unbiased_sample_standard_error(kind):
    # Losing discounting, using physical drift, or ddof=0 breaks this comparison.
    rng = np.random.Generator(np.random.PCG64(17))
    z = rng.standard_normal(12)
    terminal = 100 * np.exp(.03 + .2 * z)
    payoff = np.maximum(terminal - 100 if kind == "call" else 100 - terminal, 0)
    observations = math.exp(-.05) * payoff
    result = estimate(replace(BASE, kind=kind), n_paths=12, batch_size=5)
    assert result.price == pytest.approx(observations.mean(), rel=2e-14)
    assert result.standard_error == pytest.approx(observations.std(ddof=1) / math.sqrt(12))
    assert result.ci_low == pytest.approx(result.price - 1.959963984540054 * result.standard_error)
    assert result.ci_high == pytest.approx(result.price + 1.959963984540054 * result.standard_error)
    assert result.n_paths == result.independent_samples == 12
    assert result.pilot_paths == 0


def test_antithetic_uncertainty_uses_pair_averages():
    z = np.random.Generator(np.random.PCG64(17)).standard_normal(6)
    plus = np.maximum(100 * np.exp(.03 + .2 * z) - 100, 0)
    minus = np.maximum(100 * np.exp(.03 - .2 * z) - 100, 0)
    pairs = math.exp(-.05) * (plus + minus) / 2
    result = estimate(n_paths=12, method="antithetic", batch_size=5)
    assert result.price == pytest.approx(pairs.mean(), rel=2e-14)
    assert result.standard_error == pytest.approx(pairs.std(ddof=1) / math.sqrt(6))
    assert result.n_paths == 12
    assert result.independent_samples == 6


def test_control_beta_uses_separate_pilot_and_prices_only_production():
    z = np.random.Generator(np.random.PCG64(17)).standard_normal(20)
    stock = 100 * np.exp(-.02 + .2 * z)
    payoff = np.maximum(stock - 100 * math.exp(-.05), 0)
    beta = np.cov(payoff[:8], stock[:8], ddof=1)[0, 1] / np.var(stock[:8], ddof=1)
    corrected = payoff[8:] - beta * (stock[8:] - 100)
    result = estimate(n_paths=12, method="control", pilot_paths=8, batch_size=5)
    assert result.control_beta == pytest.approx(beta)
    assert result.price == pytest.approx(corrected.mean(), rel=2e-14)
    assert result.standard_error == pytest.approx(corrected.std(ddof=1) / math.sqrt(12))
    assert result.pilot_paths == 8
    assert result.independent_samples == result.n_paths == 12


@pytest.mark.parametrize("method", ["plain", "antithetic", "control"])
@pytest.mark.parametrize("kwargs,want", [({"maturity_years": 0, "spot": 110}, 10),
                                         ({"volatility": 0}, 4.877057549928594)])
def test_deterministic_limits_consume_no_rng(method, kwargs, want):
    rng = np.random.default_rng(17)
    state = rng.bit_generator.state
    result = estimate(replace(BASE, **kwargs), rng=rng, method=method)
    assert result.price == pytest.approx(want)
    assert result.standard_error == 0
    assert result.ci_low == result.ci_high == result.price
    assert result.pilot_paths == 0
    assert rng.bit_generator.state == state


@pytest.mark.parametrize("method", ["plain", "antithetic", "control"])
def test_seed_reproducibility_and_batch_invariance_in_recorded_environment(method):
    first = estimate(method=method, batch_size=100)
    assert first == estimate(method=method, batch_size=100)
    other = estimate(method=method, batch_size=77)
    assert other.price == pytest.approx(first.price, abs=2e-12)
    assert other.standard_error == pytest.approx(first.standard_error, abs=2e-12)


@pytest.mark.parametrize("kwargs,error", [
    ({"n_paths": True}, TypeError), ({"n_paths": 2.0}, TypeError),
    ({"n_paths": 1}, ValueError), ({"n_paths": -2}, ValueError),
    ({"method": "antithetic", "n_paths": 3}, ValueError),
    ({"method": "antithetic", "n_paths": 5}, ValueError),
    ({"method": "magic"}, ValueError), ({"rng": 42}, TypeError),
    ({"batch_size": True}, TypeError), ({"batch_size": 1}, ValueError),
    ({"pilot_paths": True}, TypeError), ({"pilot_paths": 1}, ValueError),
])
def test_invalid_parameters_are_rejected(kwargs, error):
    with pytest.raises(error):
        estimate(**kwargs)


@pytest.mark.parametrize("overrides", [{"risk_free_rate": 1000}, {"volatility": 1000}])
def test_unrepresentable_samples_raise_instead_of_silent_zero_or_inf(overrides):
    with pytest.raises(ValueError):
        estimate(replace(BASE, **overrides))


def test_global_numpy_random_state_is_untouched():
    np.random.seed(123)
    before = np.random.get_state()
    estimate(method="control")
    after = np.random.get_state()
    np.testing.assert_array_equal(before[1], after[1])
    assert before[2:] == after[2:]


def test_repeated_seed_accuracy_se_calibration_and_variance_reduction():
    # Broad tolerances assess an ensemble; no requirement that every CI covers truth.
    truth = 10.450583572185565
    results = {method: [estimate(method=method, n_paths=4000,
                               rng=np.random.default_rng(np.random.SeedSequence([j, 901])))
                        for j in range(96)] for method in ("plain", "antithetic", "control")}
    rmse = {}
    for method, values in results.items():
        errors = np.array([v.price - truth for v in values])
        se = np.array([v.standard_error for v in values])
        rmse[method] = np.sqrt(np.mean(errors ** 2))
        assert abs(errors.mean()) < 4 * errors.std(ddof=1) / math.sqrt(96)
        assert .65 < errors.std(ddof=1) / se.mean() < 1.4
        assert .84 < np.mean(np.abs(errors) <= 1.959963984540054 * se) <= 1
    assert rmse["antithetic"] < .85 * rmse["plain"]
    assert rmse["control"] < .65 * rmse["plain"]


def test_error_shrinks_with_sqrt_sample_count_over_independent_repeats():
    truth = 10.450583572185565
    rmses = []
    for n in (1000, 16000):
        errors = [estimate(n_paths=n, rng=np.random.default_rng(np.random.SeedSequence([n, j, 810]))).price - truth
                  for j in range(64)]
        rmses.append(np.sqrt(np.mean(np.square(errors))))
    assert 2.5 < rmses[0] / rmses[1] < 6


def test_negative_rates_and_put_call_parity_in_expectation():
    spec = replace(BASE, risk_free_rate=-.02)
    call = estimate(spec, n_paths=100000, method="control")
    put = estimate(replace(spec, kind="put"), n_paths=100000, method="control")
    assert call.price - put.price == pytest.approx(100 - 100 * math.exp(.02), abs=2e-12)


@pytest.mark.parametrize("kind", ["call", "put"])
def test_expiry_at_the_money_is_exactly_zero(kind):
    result = estimate(replace(BASE, kind=kind, maturity_years=0))
    assert result.price == 0.0


@pytest.mark.parametrize("kwargs,error", [
    ({"spot": 0}, ValueError), ({"drift": float("nan")}, ValueError),
    ({"volatility": -.1}, ValueError), ({"maturity_years": -1}, ValueError),
    ({"spot": True}, TypeError), ({"normals": np.array([float("inf")])}, ValueError),
    ({"normals": np.array([[0.]])}, ValueError), ({"normals": np.array([])}, ValueError),
])
def test_terminal_transform_rejects_invalid_inputs(kwargs, error):
    args = dict(spot=100, drift=.05, volatility=.2, maturity_years=1, normals=np.array([0.]))
    args.update(kwargs)
    with pytest.raises(error):
        gbm.terminal_from_normals(**args)


@pytest.mark.parametrize("method", ["plain", "antithetic", "control"])
@pytest.mark.parametrize("scale", [1e-170, 1e150])
def test_price_and_uncertainty_scale_with_notional_without_moment_underflow(method, scale):
    # A silent square overflow/underflow would leave representable SE wrong or zero.
    base = estimate(method=method)
    scaled = estimate(replace(BASE, spot=BASE.spot * scale, strike=BASE.strike * scale), method=method)
    assert scaled.price / scale == pytest.approx(base.price, rel=2e-11)
    assert scaled.standard_error / scale == pytest.approx(base.standard_error, rel=2e-11)
    assert scaled.control_beta == pytest.approx(base.control_beta, abs=2e-11)


def test_discounting_before_normalization_preserves_large_finite_payoff():
    # Extreme rate changes scale by 1e304: normalizing the undiscounted payoff first erases it.
    spec = OptionSpec(1e300, 1e-100, 1, -700, 20, "put")
    result = estimate(spec)
    assert result.price == pytest.approx(1.3783112189796238e203, rel=2e-11)
    assert result.standard_error == pytest.approx(7.593901060564171e201, rel=2e-11)


def test_between_batch_moment_underflow_is_explicit_even_for_singleton_pairs():
    spec = OptionSpec(100, 1e-10, 1, 700, 38, "put")
    with pytest.raises(ValueError, match="underflow"):
        estimate(spec, method="antithetic", batch_size=2)
