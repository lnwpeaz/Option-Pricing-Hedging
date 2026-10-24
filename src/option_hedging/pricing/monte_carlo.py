"""Exact-terminal risk-neutral Monte Carlo, with bounded-memory uncertainty.

Plain, antithetic pair means, and an independent-pilot stock control variate.
O(n_paths + pilot_paths) time and O(batch_size) workspace. No analytic option
formula is used. RNG is supplied and advanced only by this call's own samples.
"""

import math
from numbers import Integral
from typing import Literal

import numpy as np

from option_hedging.contracts import OptionSpec, PriceEstimate
from option_hedging.simulation.gbm import terminal_from_normals


METHODS = ("plain", "antithetic", "control")
Z_95 = 1.959963984540054


def _integer(name: str, value: int, minimum: int) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return int(value)


class _Moments:
    """Merge batch-centered moments (avoid E[X^2]-E[X]^2 cancellation)."""

    def __init__(self):
        self.n = 0
        self.mean = 0.0
        self.m2 = 0.0

    def update(self, values: np.ndarray) -> None:
        n = values.size
        mean = float(np.mean(values))
        centered = values - mean
        m2 = float(np.dot(centered, centered))
        if m2 == 0 and np.any(centered != 0):
            raise ValueError("Sample centered moments underflowed")
        total = self.n + n
        delta = mean - self.mean
        merge_m2 = delta * delta * (self.n / total) * n
        if self.n and delta != 0 and merge_m2 == 0:
            raise ValueError("Between-batch sample moments underflowed")
        self.m2 += m2 + merge_m2
        self.mean += delta * (n / total)
        self.n = total
        if not math.isfinite(self.mean) or not math.isfinite(self.m2):
            raise ValueError("Sample moments are outside floating-point range")


def _discounted_samples(spec: OptionSpec, z: np.ndarray, discount: float):
    """Discounted payoff/stock in units of initial spot, for stable moments."""
    terminal = terminal_from_normals(spot=spec.spot, drift=spec.risk_free_rate,
                                    volatility=spec.volatility,
                                    maturity_years=spec.maturity_years, normals=z)
    payoff = np.maximum(terminal - spec.strike if spec.kind == "call"
                        else spec.strike - terminal, 0.0)
    with np.errstate(over="raise", invalid="raise", under="ignore"):
        y = (discount * payoff) / spec.spot
        x = (discount * terminal) / spec.spot
    if np.any((payoff > 0) & (y == 0)) or np.any(x <= 0):
        raise ValueError("Discounted samples or normalized values underflowed")
    return y, x


def _fit_control(spec: OptionSpec, rng: np.random.Generator, n: int,
                 batch_size: int, discount: float) -> float:
    # Merge covariance on pilot batches; production samples are drawn afterwards.
    count, mx, my, sxx, sxy = 0, 0.0, 0.0, 0.0, 0.0
    for start in range(0, n, batch_size):
        size = min(batch_size, n - start)
        y, x = _discounted_samples(spec, rng.standard_normal(size), discount)
        bx, by = float(np.mean(x)), float(np.mean(y))
        dx, dy = bx - mx, by - my
        weight = (count / (count + size)) * size
        xc, yc = x - bx, y - by
        batch_sxx = float(np.dot(xc, xc))
        if batch_sxx == 0 and np.any(xc != 0):
            raise ValueError("Pilot centered moments underflowed")
        merge_sxx, merge_sxy = dx * dx * weight, dx * dy * weight
        if count and dx != 0 and merge_sxx == 0:
            raise ValueError("Between-batch pilot moments underflowed")
        if count and dx != 0 and dy != 0 and merge_sxy == 0:
            raise ValueError("Between-batch pilot covariance underflowed")
        products = xc * yc
        if np.any((xc != 0) & (yc != 0) & (products == 0)):
            raise ValueError("Pilot covariance underflowed")
        sxx += batch_sxx + merge_sxx
        sxy += float(np.sum(products)) + merge_sxy
        mx += dx * (size / (count + size))
        my += dy * (size / (count + size))
        count += size
    if not all(math.isfinite(v) for v in (sxx, sxy, mx, my)):
        raise ValueError("Pilot moments are outside floating-point range")
    beta = sxy / sxx if sxx > 0 else 0.0
    if not math.isfinite(beta):
        raise ValueError("Control coefficient is outside floating-point range")
    return beta


def price(spec: OptionSpec, *, n_paths: int, rng: np.random.Generator,
          method: Literal["plain", "antithetic", "control"] = "plain",
          batch_size: int = 65536, pilot_paths: int = 1024) -> PriceEstimate:
    """Estimate European premium; CI uses independent observations, not raw paths.

    Antithetic requires an even n_paths >= 4; pair averages determine its SE.
    Control fits beta on pilot_paths extra samples, then freezes it for production.
    Adjusted prices and CIs can cross theoretical bounds and are never clipped.
    Deterministic cases consume no RNG. Input settings are validated even then.
    """
    if not isinstance(spec, OptionSpec):
        raise TypeError("spec must be an OptionSpec")
    n_paths = _integer("n_paths", n_paths, 2)
    batch_size = _integer("batch_size", batch_size, 2)
    pilot_paths = _integer("pilot_paths", pilot_paths, 2)
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a numpy.random.Generator")
    if method not in METHODS:
        raise ValueError(f"method must be one of {METHODS}")
    if method == "antithetic" and (n_paths < 4 or n_paths % 2):
        raise ValueError("Antithetic n_paths must be even and at least 4")
    units = n_paths // 2 if method == "antithetic" else n_paths
    if spec.maturity_years == 0:
        value = max(spec.spot - spec.strike if spec.kind == "call"
                    else spec.strike - spec.spot, 0.0)
        return PriceEstimate(value, 0.0, value, value, n_paths, units, 0, method)
    try:
        discount = math.exp(-spec.risk_free_rate * spec.maturity_years)
        if not math.isfinite(discount) or discount <= 0:
            raise ValueError("Discount factor is outside floating-point range")
        if spec.volatility == 0:
            strike_pv = math.exp(math.log(spec.strike)
                                 - spec.risk_free_rate * spec.maturity_years)
            if not math.isfinite(strike_pv) or strike_pv <= 0:
                raise ValueError("Discounted strike is outside floating-point range")
            value = max(spec.spot - strike_pv if spec.kind == "call"
                        else strike_pv - spec.spot, 0.0)
            return PriceEstimate(value, 0.0, value, value, n_paths, units, 0, method)

        beta = _fit_control(spec, rng, pilot_paths, batch_size, discount) if method == "control" else 0.0
        moments = _Moments()
        unit_batch = max(1, batch_size // 2) if method == "antithetic" else batch_size
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            for start in range(0, units, unit_batch):
                z = rng.standard_normal(min(unit_batch, units - start))
                y, stock = _discounted_samples(spec, z, discount)
                if method == "antithetic":
                    opposite, _ = _discounted_samples(spec, -z, discount)
                    observations = .5 * y + .5 * opposite
                elif method == "control":
                    observations = y - beta * (stock - 1.0)
                else:
                    observations = y
                moments.update(observations)
        normalized_se = math.sqrt(moments.m2) / math.sqrt(moments.n - 1) / math.sqrt(moments.n)
        mean = moments.mean * spec.spot
        se = normalized_se * spec.spot
        if (normalized_se > 0 and se == 0) or (moments.mean != 0 and mean == 0):
            raise ValueError("Estimate or uncertainty underflowed")
        low, high = mean - Z_95 * se, mean + Z_95 * se
        if not all(math.isfinite(v) for v in (mean, se, low, high)):
            raise ValueError("Estimate uncertainty is outside floating-point range")
        return PriceEstimate(mean, se, low, high, n_paths, units,
                             pilot_paths if method == "control" else 0, method, beta)
    except (OverflowError, FloatingPointError) as error:
        raise ValueError("Monte Carlo arithmetic is outside floating-point range") from error
