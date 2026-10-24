"""Cox-Ross-Rubinstein European option pricing by backward induction.

No dividends or early exercise. Runtime is O(steps**2), memory O(steps).
Invalid probabilities are rejected rather than clipped or replaced by another model.
"""

import math
from numbers import Integral
import sys

import numpy as np

from option_hedging.contracts import OptionSpec


def price(spec: OptionSpec, *, steps: int) -> float:
    """Return a CRR premium, handling expiry and deterministic volatility limits.

    Integer step counts (including NumPy integers) must be strictly positive;
    booleans and float-valued counts are rejected, even at expiry. A coarse
    grid may violate -sigma*sqrt(dt) <= r*dt <= sigma*sqrt(dt); increase steps
    when that happens. Representational overflow raises ValueError explicitly.
    """
    if isinstance(steps, bool) or not isinstance(steps, Integral):
        raise TypeError("steps must be a positive integer, not a boolean or float")
    if steps <= 0:
        raise ValueError("steps must be a positive integer")
    steps = int(steps)
    if spec.maturity_years == 0:
        difference = spec.spot - spec.strike
        return max(difference if spec.kind == "call" else -difference, 0.0)
    try:
        return _price_before_expiry(spec, steps)
    except (OverflowError, FloatingPointError) as error:
        raise ValueError("Tree calculation exceeds floating-point range; adjust the grid or inputs") from error


def _price_before_expiry(spec: OptionSpec, steps: int) -> float:
    if spec.volatility == 0:
        exponent = -spec.risk_free_rate * spec.maturity_years
        discounted_k = (spec.strike * math.exp(exponent) if -700 <= exponent <= 700
                        else math.exp(math.log(spec.strike) + exponent))
        if not math.isfinite(discounted_k):
            raise ValueError("Discounted strike exceeds floating-point range")
        difference = spec.spot - discounted_k
        return max(difference if spec.kind == "call" else -difference, 0.0)

    dt = spec.maturity_years / steps
    a = spec.volatility * math.sqrt(dt)
    b = spec.risk_free_rate * dt
    if not math.isfinite(a) or not math.isfinite(b) or a <= 0:
        raise ValueError("Tree time/volatility scale is outside floating-point range")
    if not -a <= b <= a:
        raise ValueError("Invalid risk-neutral probability: grid must satisfy -sigma*sqrt(dt) <= r*dt <= sigma*sqrt(dt); increase steps")
    # Algebraically identical to (exp(b)-exp(-a))/(exp(a)-exp(-a)).
    # Negative expm1 arguments avoid both cancellation at tiny a and exp(2*a) overflow.
    p = math.exp(b - a) * math.expm1(-a - b) / math.expm1(-2 * a)
    if not 0 <= p <= 1 or not math.isfinite(p):
        raise ValueError("Risk-neutral probability is outside [0,1]; use a different grid")
    if (p == 0 and b != -a) or (p == 1 and b != a):
        raise ValueError("Interior risk-neutral probability is outside representable floating-point range; use a different grid")

    offsets = (2 * np.arange(steps + 1, dtype=float) - steps) * a
    log_nodes = math.log(spec.spot) + offsets
    if not np.all(np.isfinite(log_nodes)) or np.max(log_nodes) > math.log(sys.float_info.max):
        raise ValueError("Terminal tree nodes exceed floating-point range; reduce steps or volatility")
    with np.errstate(over="raise", invalid="raise", under="ignore"):
        difference = np.exp(log_nodes) - spec.strike
        # Preserve very small payoffs near the strike instead of subtracting
        # almost identical spot values (important when sigma approaches zero).
        log_ratio = (math.log(spec.spot) - math.log(spec.strike)) + offsets
        near_strike = np.abs(log_ratio) < .5
        difference[near_strike] = spec.strike * np.expm1(log_ratio[near_strike])
        values = np.maximum(difference if spec.kind == "call" else -difference, 0.0)
        discount = math.exp(-b)
        for remaining in range(steps, 0, -1):
            values = discount * ((1 - p) * values[:remaining] + p * values[1:remaining + 1])
    result = float(values[0])
    if not math.isfinite(result):
        raise ValueError("Tree premium exceeds floating-point range")
    return result
