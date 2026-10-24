"""Contracts for discrete equal-weight Asian options; annual times, q=0."""
from dataclasses import dataclass
import math
from numbers import Real


def finite_real(value, name):
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f'{name} must be a finite real number')
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f'{name} must be finite')
    return value


def validate_times(times):
    if isinstance(times, (str, bytes)):
        raise TypeError('fixing_times must be a sequence of real times')
    times = tuple(finite_real(t, 'fixing time') for t in times)
    if not times or times[0] <= 0 or any(b <= a for a,b in zip(times,times[1:])):
        raise ValueError('fixings must satisfy 0 < t1 < ... < tm')
    return times


@dataclass(frozen=True)
class AsianOptionSpec:
    spot: float
    strike: float
    risk_free_rate: float
    volatility: float
    kind: str
    fixing_times: tuple[float, ...]
    averaging: str = 'arithmetic'

    def __post_init__(self):
        for name in ('spot','strike','risk_free_rate','volatility'):
            object.__setattr__(self, name, finite_real(getattr(self,name),name))
        if self.spot <= 0 or self.strike <= 0 or self.volatility < 0:
            raise ValueError('spot/strike must be positive and volatility nonnegative')
        if self.kind not in ('call','put') or self.averaging not in ('arithmetic','geometric'):
            raise ValueError('unsupported kind or averaging convention')
        object.__setattr__(self,'fixing_times',validate_times(self.fixing_times))

    @property
    def maturity_years(self):
        return self.fixing_times[-1]


@dataclass(frozen=True)
class AsianEstimate:
    """Unclipped approximate 95% interval and actual estimator work.

    QMC independent units are scramble prices. Zero observed variance does not
    imply an exact price: only status='deterministic' carries that meaning.
    """
    price: float
    standard_error: float
    ci_low: float
    ci_high: float
    method: str
    status: str
    requested_paths: int
    production_paths: int
    independent_samples: int
    pilot_paths: int
    normal_coordinates: int
    payoff_evaluations: int
    control_payoff_evaluations: int
    scrambles: int
    pilot_beta: float | None = None
    scramble_prices: tuple[float, ...] = ()
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self):
        for name in ('price','standard_error','ci_low','ci_high'):
            object.__setattr__(self,name,finite_real(getattr(self,name),name))
        if self.pilot_beta is not None:
            object.__setattr__(self,'pilot_beta',finite_real(self.pilot_beta,'pilot_beta'))
        object.__setattr__(self,'scramble_prices',tuple(finite_real(x,'scramble price') for x in self.scramble_prices))
        object.__setattr__(self,'diagnostics',tuple(self.diagnostics))
