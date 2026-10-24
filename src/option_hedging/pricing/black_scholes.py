"""Black-Scholes prices and Greeks for European options without dividends."""

import math

from scipy.special import log_ndtr, ndtr

from option_hedging.contracts import Greeks, OptionSpec


def _discounted_strike(spec: OptionSpec) -> float:
    """Combine exponents before exp so a representable final value stays finite."""
    exponent = -spec.risk_free_rate * spec.maturity_years
    # Preserve exact K at r*T=0 and normal-range accuracy at deterministic kinks.
    if -700 <= exponent <= 700:
        return spec.strike * math.exp(exponent)
    return math.exp(math.log(spec.strike) + exponent)


def _terms(spec: OptionSpec) -> tuple[float, float, float]:
    """Return discounted strike and d1/d2; caller handles deterministic limits."""
    discounted_strike = _discounted_strike(spec)
    stddev = spec.volatility * math.sqrt(spec.maturity_years)
    log_moneyness = math.log(spec.spot) - math.log(spec.strike)
    d1 = (log_moneyness + spec.risk_free_rate * spec.maturity_years) / stddev + stddev / 2
    return discounted_strike, d1, d1 - stddev


def _positive_difference(log_a: float, log_b: float) -> float:
    """Compute a-b in the tails without subtracting two almost equal prices."""
    if log_a == -math.inf:
        return 0.0
    return math.exp(log_a) * (-math.expm1(min(log_b - log_a, 0.0)))


def price(spec: OptionSpec) -> float:
    """Return the modeled premium, handling expiry and zero volatility exactly.

    Price the out-of-the-money leg in log-CDF space, then recover the other
    leg using put-call parity. This preserves small tail values and avoids
    unnecessary cancellation in in-the-money prices.
    """
    s, k, t, r, sigma = (spec.spot, spec.strike, spec.maturity_years,
                          spec.risk_free_rate, spec.volatility)
    if t == 0:
        return max(s - k, 0.0) if spec.kind == "call" else max(k - s, 0.0)
    discounted_strike = _discounted_strike(spec)
    if sigma == 0:
        return (max(s - discounted_strike, 0.0) if spec.kind == "call"
                else max(discounted_strike - s, 0.0))
    discounted_strike, d1, d2 = _terms(spec)
    if discounted_strike == 0:
        return s if spec.kind == "call" else 0.0
    if s <= discounted_strike:
        call = _positive_difference(math.log(s) + float(log_ndtr(d1)),
                                    math.log(discounted_strike) + float(log_ndtr(d2)))
        return call if spec.kind == "call" else (discounted_strike - s) + call
    put = _positive_difference(math.log(discounted_strike) + float(log_ndtr(-d2)),
                               math.log(s) + float(log_ndtr(-d1)))
    return put if spec.kind == "put" else (s - discounted_strike) + put


def greeks(spec: OptionSpec) -> Greeks:
    """Return sensitivities; vega/100 is the change per volatility percentage point.

    At expiry or zero volatility, return piecewise limiting sensitivities
    away from the payoff/forward kink. At the kink the tuple is undefined,
    so raise ValueError rather than silently choose a delta convention.
    """
    s, t, sigma = spec.spot, spec.maturity_years, spec.volatility
    if t == 0 or sigma == 0:
        boundary = spec.strike if t == 0 else _discounted_strike(spec)
        if s == boundary:
            raise ValueError("Greeks are undefined at the deterministic payoff kink")
        delta = float(s > boundary) - float(spec.kind == "put")
        return Greeks(delta=delta, gamma=0.0, vega=0.0)
    _, d1, _ = _terms(spec)
    # Multiplication may saturate to -inf, whose exponential is correctly zero.
    # Python's d1**2 instead raises for large finite d1.
    density = math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi)
    delta = float(ndtr(d1)) if spec.kind == "call" else -float(ndtr(-d1))
    return Greeks(delta=delta,
                  gamma=density / (s * sigma * math.sqrt(t)),
                  vega=s * density * math.sqrt(t))
