"""Integrate discounted payoff directly; independent of project pricing formulas."""

from dataclasses import dataclass
import math
from numbers import Real

from scipy.integrate import quad

from option_hedging.contracts import OptionSpec


@dataclass(frozen=True)
class PayoffReference:
    price: float
    quad_error_estimate: float
    tail_bound: float
    evaluations: int
    lower_normal_bound: float
    upper_normal_bound: float


def integrate_payoff(spec: OptionSpec, *, normal_cutoff: float = 12.) -> PayoffReference:
    """Bound normal tails and numerically integrate the positive payoff region.

    Call payoff <= discounted stock, whose normal density is tilted by v=sigma
    sqrt(T); put payoff <= discounted strike. These inequalities bound both omitted
    tails. QUADPACK's integration error is an estimate, not a rigorous bound.
    No project pricer, normal-CDF option formula or GBM transform is called.
    """
    if not isinstance(spec, OptionSpec):
        raise TypeError("spec must be OptionSpec")
    if isinstance(normal_cutoff, bool) or not isinstance(normal_cutoff, Real):
        raise TypeError("normal_cutoff must be a finite real")
    if not math.isfinite(normal_cutoff) or normal_cutoff < 4:
        raise ValueError("normal_cutoff must be finite and at least 4")
    if spec.maturity_years == 0:
        value = max(spec.spot - spec.strike if spec.kind == "call" else spec.strike - spec.spot, 0.)
        return PayoffReference(value, 0., 0., 0, 0., 0.)
    try:
        log_k = math.log(spec.strike) - spec.risk_free_rate * spec.maturity_years
        k_pv = spec.strike if spec.risk_free_rate == 0 else math.exp(log_k)
        v = spec.volatility * math.sqrt(spec.maturity_years)
        if not math.isfinite(k_pv) or k_pv <= 0 or not math.isfinite(v):
            raise ValueError("Reference parameters are outside floating-point range")
        if v == 0:
            value = max(spec.spot - k_pv if spec.kind == "call" else k_pv - spec.spot, 0.)
            return PayoffReference(value, 0., 0., 0, 0., 0.)
        lower, upper = -float(normal_cutoff), float(normal_cutoff) + v
        a = (log_k - math.log(spec.spot) + .5 * v * v) / v
        lo, hi = ((max(lower, a), upper) if spec.kind == "call" else (lower, min(upper, a)))
        # Gaussian tail probability via erfc is used only for the truncation bound.
        sf = lambda x: .5 * math.erfc(x / math.sqrt(2))
        tail = (spec.spot * (sf(v - lower) + sf(upper - v)) if spec.kind == "call"
                else k_pv * (sf(-lower) + sf(upper)))

        def integrand(z):
            log_stock = math.log(spec.spot) - .5 * v * v + v * z
            high, low = (log_stock, log_k) if spec.kind == "call" else (log_k, log_stock)
            if high <= low:
                return 0.
            log_payoff = high + math.log(-math.expm1(low - high))
            return math.exp(log_payoff - .5 * z * z - .5 * math.log(2 * math.pi))

        value, error, evaluations = 0., 0., 0
        if lo < hi:
            # Density centers can coincide with the payoff kink to rounding
            # precision. Do not create a nearly zero-width QUADPACK interval.
            # Removing a redundant split leaves the full integration domain intact.
            gap = 64 * max(math.ulp(x) for x in (lo, hi, v, 0.))
            points = [lo]
            for center in sorted({0., v}):
                if center - points[-1] > gap and hi - center > gap:
                    points.append(center)
            points.append(hi)
            for start, stop in zip(points, points[1:]):
                result = quad(integrand, start, stop, epsabs=1e-11, epsrel=1e-11, limit=100, full_output=1)
                if len(result) != 3:
                    raise ValueError(f"Reference quadrature did not converge: {result[3]}")
                piece, estimated_error, info = result
                value += piece
                error += estimated_error
                evaluations += info["neval"]
        if not all(math.isfinite(x) for x in (value, error, tail)):
            raise ValueError("Reference integral is not finite")
        return PayoffReference(value, error, tail, evaluations, lower, upper)
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Reference integral is outside floating-point range") from exc
