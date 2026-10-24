"""Exact terminal and full-path GBM with explicit drift and local random streams."""

import math
from numbers import Integral, Real

import numpy as np


def terminal_from_normals(*, spot: float, drift: float, volatility: float,
                          maturity_years: float, normals: np.ndarray) -> np.ndarray:
    """Transform supplied N(0,1) samples using an explicit physical or RN drift.

    No RNG or inference of measure here. Compute in log space; reject terminal
    overflow/underflow rather than silently erase a rare payoff. Workspace is O(B).
    """
    for name, value in (("spot", spot), ("drift", drift), ("volatility", volatility),
                        ("maturity_years", maturity_years)):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise TypeError(f"{name} must be a finite real")
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    if spot <= 0 or volatility < 0 or maturity_years < 0:
        raise ValueError("spot must be positive; volatility and maturity must be nonnegative")
    z = np.asarray(normals, dtype=float)
    if z.ndim != 1 or z.size == 0 or not np.all(np.isfinite(z)):
        raise ValueError("normals must be a nonempty finite one-dimensional array")
    if maturity_years == 0:
        return np.full_like(z, spot)
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            log_terminal = (math.log(spot) + (drift - .5 * volatility * volatility)
                            * maturity_years + volatility * math.sqrt(maturity_years) * z)
            terminal = np.exp(log_terminal)
    except (FloatingPointError, OverflowError) as error:
        raise ValueError("GBM terminal values are outside floating-point range") from error
    if not np.all(np.isfinite(terminal)) or np.any(terminal <= 0):
        raise ValueError("GBM terminal values overflowed or underflowed")
    return terminal


def _real(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a finite real number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


def _positive_integer(name: str, value: int) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Integral):
        raise TypeError(f"{name} must be a positive integer")
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return int(value)


def simulate_paths(*, spot: float, drift: float, volatility: float, times: np.ndarray,
                   n_paths: int, rng: np.random.Generator, batch_size: int = 512) -> np.ndarray:
    """Return exact-transition GBM paths of shape (n_paths, len(times)).

    Drift is supplied explicitly: use mu for physical scenarios or r for pricing
    diagnostics. Times are years, strictly increasing from zero; [0] is allowed.
    Zero sigma/[0] draw no randomness. Batch draws use path-major order, with
    O(N*M) returned storage and O(B*M) extra workspace; no global RNG is used.
    Numerical reproducibility targets a fixed environment and RNG call policy.
    """
    spot = _real("spot", spot)
    drift = _real("drift", drift)
    volatility = _real("volatility", volatility)
    if spot <= 0 or volatility < 0:
        raise ValueError("spot must be positive and volatility nonnegative")
    n_paths = _positive_integer("n_paths", n_paths)
    batch_size = _positive_integer("batch_size", batch_size)
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng must be a numpy.random.Generator")
    if isinstance(times, (list, tuple)) and any(isinstance(t, (bool, np.bool_)) for t in times):
        raise TypeError("times must contain real numbers, not booleans")
    grid = np.asarray(times)
    if grid.dtype.kind not in "iuf":
        raise TypeError("times must contain real numbers, not booleans, strings or complex values")
    grid = np.asarray(grid, dtype=np.float64)
    if grid.ndim != 1 or grid.size == 0 or not np.all(np.isfinite(grid)):
        raise ValueError("times must be a nonempty finite one-dimensional array")
    if grid[0] != 0 or np.any(np.diff(grid) <= 0):
        raise ValueError("times must start at zero and be strictly increasing")
    paths = np.empty((n_paths, len(grid)), dtype=np.float64)
    paths[:, 0] = spot
    if grid.size == 1:
        return paths
    try:
        with np.errstate(over="raise", invalid="raise", under="ignore"):
            if volatility == 0:
                values = np.exp(math.log(spot) + drift * grid[1:]) if drift != 0 else np.full(grid.size - 1, spot)
                if not np.all(np.isfinite(values)) or np.any(values <= 0):
                    raise ValueError("Deterministic GBM path values overflowed or underflowed")
                paths[:, 1:] = values
                return paths
            dt = np.diff(grid)
            location = (drift - .5 * volatility * volatility) * dt
            scale = volatility * np.sqrt(dt)
            for start in range(0, n_paths, batch_size):
                stop = min(start + batch_size, n_paths)
                work = rng.standard_normal((stop - start, len(dt)))
                np.multiply(work, scale, out=work)
                np.add(work, location, out=work)
                np.cumsum(work, axis=1, out=work)
                work += math.log(spot)
                np.exp(work, out=work)
                if not np.all(np.isfinite(work)) or np.any(work <= 0):
                    raise ValueError("GBM path values overflowed or underflowed")
                paths[start:stop, 1:] = work
    except (FloatingPointError, OverflowError) as error:
        raise ValueError("GBM path values are outside floating-point range") from error
    return paths
