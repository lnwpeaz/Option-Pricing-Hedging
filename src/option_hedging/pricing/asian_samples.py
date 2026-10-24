"""Pure discounted A/G payoff vectors in S0 units, without retaining paths.

Logs relative to spot preserve tiny currency scales. Positive results that cannot
be represented are diagnosed instead of silently becoming zero or infinity.
"""
import math
import numpy as np
from option_hedging.pricing._asian_statistics import log_ratio,log_mean_exp
from option_hedging.simulation.brownian_bridge import brownian_from_normals


def _payoff(log_average, log_strike, discount, kind):
    if kind=='call':large,small=log_average,np.full_like(log_average,log_strike)
    else:large,small=np.full_like(log_average,log_strike),log_average
    positive=large>small;out=np.zeros_like(large)
    if np.any(positive):
        with np.errstate(over='raise',invalid='raise',divide='raise',under='ignore'):
            log_value=large[positive]-discount+np.log(-np.expm1(small[positive]-large[positive]))
            out[positive]=np.exp(log_value)
        if np.any(out[positive]==0) or not np.all(np.isfinite(out)):
            raise FloatingPointError('unrepresentable positive normalized payoff')
    return out


def discounted_payoffs(spec, normals, *, construction='increments'):
    w=brownian_from_normals(normals,spec.fixing_times,construction=construction)
    t=np.asarray(spec.fixing_times)
    with np.errstate(over='raise',invalid='raise',under='ignore'):
        logs=(spec.risk_free_rate-.5*spec.volatility*spec.volatility)*t+spec.volatility*w
        log_a=log_mean_exp(logs)
        log_g=logs.mean(axis=1)
    if not np.all(np.isfinite(log_a)) or not np.all(np.isfinite(log_g)):
        raise FloatingPointError('unrepresentable log averages')
    log_k=log_ratio(spec.strike,spec.spot)
    discount=spec.risk_free_rate*spec.maturity_years
    return (_payoff(log_a,log_k,discount,spec.kind),
            _payoff(log_g,log_k,discount,spec.kind))


def target_payoffs(spec, normals, *, construction='increments'):
    """Compute only the requested payoff, avoiding unused control evaluations."""
    w=brownian_from_normals(normals,spec.fixing_times,construction=construction)
    t=np.asarray(spec.fixing_times)
    with np.errstate(over='raise',invalid='raise',under='ignore'):
        logs=(spec.risk_free_rate-.5*spec.volatility*spec.volatility)*t+spec.volatility*w
        log_avg=(log_mean_exp(logs) if spec.averaging=='arithmetic'
                 else logs.mean(axis=1))
    if not np.all(np.isfinite(log_avg)):raise FloatingPointError('unrepresentable log average')
    return _payoff(log_avg,log_ratio(spec.strike,spec.spot),
                   spec.risk_free_rate*spec.maturity_years,spec.kind)
