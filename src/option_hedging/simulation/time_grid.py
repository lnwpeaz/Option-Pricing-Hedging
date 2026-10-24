"""Regular annual trading grid with exact expiry and a possible shorter last step."""

import math
from numbers import Integral, Real

import numpy as np


def make_time_grid(*, maturity_years: float, steps_per_year: int = 252) -> np.ndarray:
    """Return 0, regular k/frequency dates < T, and exact T (years).

    This is a model grid, not a holiday-aware trading calendar. Zero maturity
    returns [0]. The final interval is shorter when T is not a regular date.
    """
    if isinstance(maturity_years, bool) or not isinstance(maturity_years, Real):
        raise TypeError("maturity_years must be a finite real number")
    if not math.isfinite(maturity_years) or maturity_years < 0:
        raise ValueError("maturity_years must be finite and nonnegative")
    if isinstance(steps_per_year, (bool, np.bool_)) or not isinstance(steps_per_year, Integral):
        raise TypeError("steps_per_year must be a positive integer")
    if steps_per_year < 1:
        raise ValueError("steps_per_year must be positive")
    maturity = float(maturity_years)
    if maturity == 0:
        return np.array([0.])
    count = maturity * steps_per_year
    if not math.isfinite(count):
        raise ValueError("Requested time grid is outside floating-point range")
    regular = np.arange(math.floor(count) + 1, dtype=np.float64) / steps_per_year
    regular = regular[regular < maturity]
    result = np.append(regular, maturity)
    if result[0] != 0 or np.any(np.diff(result) <= 0):
        raise ValueError("Requested time grid cannot be represented distinctly")
    return result
