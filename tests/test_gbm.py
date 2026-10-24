"""Exact path transitions and explicit random-stream/time-grid contracts."""

import importlib
import math

import numpy as np
import pytest

from option_hedging.simulation import gbm


def make_grid(**kwargs):
    return importlib.import_module("option_hedging.simulation.time_grid").make_time_grid(**kwargs)


def simulate(**kwargs):
    args = dict(spot=100., drift=.08, volatility=.2, times=np.array([0., .1, .4, 1.]),
                n_paths=8, rng=np.random.Generator(np.random.PCG64(42)), batch_size=3)
    args.update(kwargs)
    return gbm.simulate_paths(**args)


def test_nonuniform_steps_match_independent_increment_calculation():
    z = np.random.Generator(np.random.PCG64(42)).standard_normal((8, 3))
    expected = np.full((8, 4), 100.)
    for j, dt in enumerate((.1, .3, .6)):
        expected[:, j + 1] = expected[:, j] * np.exp(.06 * dt + .2 * math.sqrt(dt) * z[:, j])
    np.testing.assert_allclose(simulate(), expected, rtol=2e-14)


def test_shape_exact_start_finite_positivity_and_no_time_mutation():
    times = np.array([0., .03, .7, 1.])
    before = times.copy()
    values = simulate(times=times, n_paths=101)
    assert values.shape == (101, 4)
    assert values.dtype == np.float64
    np.testing.assert_array_equal(values[:, 0], np.full(101, 100.))
    assert np.all(np.isfinite(values)) and np.all(values > 0)
    np.testing.assert_array_equal(times, before)


@pytest.mark.parametrize("kwargs", [{"volatility": 0}, {"times": np.array([0.])}])
def test_deterministic_cases_consume_no_random_state(kwargs):
    rng = np.random.default_rng(42)
    state = rng.bit_generator.state
    values = simulate(rng=rng, **kwargs)
    times = kwargs.get("times", np.array([0., .1, .4, 1.]))
    np.testing.assert_allclose(values, np.broadcast_to(100 * np.exp(.08 * times), values.shape))
    np.testing.assert_array_equal(values[:, 0], np.full(8, 100.))
    assert rng.bit_generator.state == state


def test_identical_shocks_pair_explicit_physical_and_risk_neutral_drifts():
    physical = simulate(drift=.08)
    risk_neutral = simulate(drift=.05)
    ratio = np.broadcast_to(np.exp(.03 * np.array([0., .1, .4, 1.])), physical.shape)
    np.testing.assert_allclose(physical / risk_neutral, ratio, rtol=2e-14)


def test_reproducibility_batching_and_path_prefix():
    baseline = simulate(n_paths=37, batch_size=5)
    np.testing.assert_array_equal(baseline, simulate(n_paths=37, batch_size=5))
    np.testing.assert_allclose(baseline, simulate(n_paths=37, batch_size=11), rtol=2e-14)
    np.testing.assert_allclose(baseline[:8], simulate(n_paths=8, batch_size=3), rtol=2e-14)


def test_local_generator_does_not_change_global_numpy_state():
    np.random.seed(431)
    state = np.random.get_state()
    simulate()
    current = np.random.get_state()
    np.testing.assert_array_equal(state[1], current[1])
    assert state[2:] == current[2:]


@pytest.mark.parametrize("kwargs,error", [
    ({"spot": 0}, ValueError), ({"spot": True}, TypeError), ({"drift": float("nan")}, ValueError),
    ({"volatility": -.1}, ValueError), ({"volatility": "0.2"}, TypeError),
    ({"times": []}, ValueError), ({"times": [1., 2.]}, ValueError),
    ({"times": [0., 0.]}, ValueError), ({"times": [0., .4, .2]}, ValueError),
    ({"times": [0., float("inf")]}, ValueError), ({"times": [[0., 1.]]}, ValueError),
    ({"times": [False, True]}, TypeError), ({"times": ["0", "1"]}, TypeError),
    ({"times": [0., True]}, TypeError),
    ({"times": [0., 1j]}, TypeError), ({"n_paths": 0}, ValueError),
    ({"n_paths": True}, TypeError), ({"n_paths": 2.0}, TypeError),
    ({"batch_size": 0}, ValueError), ({"batch_size": True}, TypeError), ({"rng": 42}, TypeError),
])
def test_invalid_inputs_fail_even_in_zero_volatility_limit(kwargs, error):
    with pytest.raises(error):
        simulate(**({"volatility": 0} | kwargs))


@pytest.mark.parametrize("kwargs", [{"drift": 1000}, {"drift": -1000}, {"volatility": 1000}])
def test_unrepresentable_paths_raise_without_silent_zero_or_infinity(kwargs):
    with pytest.raises(ValueError):
        simulate(**kwargs)


@pytest.mark.parametrize("drift", [.08, .05, -.02])
def test_repeated_independent_terminal_and_log_return_moments(drift):
    means, log_means, log_variances = [], [], []
    for repeat in range(32):
        paths = simulate(drift=drift, n_paths=3000,
                         rng=np.random.default_rng(np.random.SeedSequence([3, repeat, 401])))
        terminal = paths[:, -1]
        logs = np.log(terminal / 100)
        means.append(terminal.mean())
        log_means.append(logs.mean())
        log_variances.append(logs.var(ddof=1))
    for samples, truth in ((means, 100 * math.exp(drift)), (log_means, drift - .02),
                           (log_variances, .04)):
        ensemble_se = np.std(samples, ddof=1) / math.sqrt(32)
        assert abs(np.mean(samples) - truth) < 4.5 * ensemble_se


def test_irregular_increment_variance_and_independence():
    paths = simulate(n_paths=60000)
    increments = np.diff(np.log(paths), axis=1)
    dt = np.array([.1, .3, .6])
    standardized = (increments - .06 * dt) / (.2 * np.sqrt(dt))
    np.testing.assert_allclose(standardized.var(axis=0, ddof=1), np.ones(3), atol=.025)
    covariance = np.cov(standardized, rowvar=False)
    np.testing.assert_allclose(covariance - np.diag(np.diag(covariance)), np.zeros((3, 3)), atol=.025)


@pytest.mark.parametrize("maturity,frequency,expected", [
    (1., 4, [0., .25, .5, .75, 1.]), (.6, 4, [0., .25, .5, .6]),
    (.1, 4, [0., .1]), (0., 252, [0.]),
])
def test_time_grid_keeps_regular_dates_and_exact_expiry(maturity, frequency, expected):
    result = make_grid(maturity_years=maturity, steps_per_year=frequency)
    np.testing.assert_array_equal(result, expected)
    assert result[-1] == maturity


def test_time_grid_handles_expiry_adjacent_to_regular_date():
    for expiry in (np.nextafter(.5, 0), .5, np.nextafter(.5, 1)):
        result = make_grid(maturity_years=expiry, steps_per_year=4)
        assert result[-1] == expiry
        assert np.all(np.diff(result) > 0)
        assert np.all(result[:-1] < expiry)


@pytest.mark.parametrize("kwargs,error", [
    ({"maturity_years": -1}, ValueError), ({"maturity_years": float("inf")}, ValueError),
    ({"maturity_years": True}, TypeError), ({"steps_per_year": True}, TypeError),
    ({"steps_per_year": 2.0}, TypeError), ({"steps_per_year": 0}, ValueError),
])
def test_time_grid_invalid_inputs(kwargs, error):
    with pytest.raises(error):
        make_grid(**({"maturity_years": 1., "steps_per_year": 252} | kwargs))
