"""Lognormal geometric reference and discrete arithmetic bounds, q=0."""
import math
from dataclasses import replace
import numpy as np
from scipy.special import log_ndtr, logsumexp
from option_hedging.asian_contracts import AsianOptionSpec
from option_hedging.pricing._asian_statistics import log_ratio,log_mean_exp


def _exp(log_value):
    if not math.isfinite(log_value):
        raise FloatingPointError('unrepresentable log value')
    try:
        result = math.exp(log_value)
    except OverflowError as exc:
        raise FloatingPointError('unrepresentable currency value') from exc
    if result == 0:
        raise FloatingPointError('positive currency value underflow')
    return result


def _difference(log_a, log_b):
    if not math.isfinite(log_a) or not math.isfinite(log_b):
        raise FloatingPointError('unrepresentable log difference')
    if log_b >= log_a:
        raise FloatingPointError('positive difference below numerical precision')
    return _exp(log_a + math.log(-math.expm1(log_b-log_a)))


def geometric_log_moments(spec: AsianOptionSpec):
    t=np.asarray(spec.fixing_times)
    sigma2=spec.volatility*spec.volatility
    a=math.log(spec.spot)+(spec.risk_free_rate-.5*sigma2)*float(t.mean())
    b2=sigma2*float(np.dot(2*(len(t)-np.arange(len(t)))-1,t))/len(t)**2
    if not math.isfinite(a) or not math.isfinite(b2) or (spec.volatility>0 and b2==0):
        raise FloatingPointError('unrepresentable geometric log moments')
    return a,b2


def _average_log(spec, geometric=False):
    t=np.asarray(spec.fixing_times)
    with np.errstate(over='raise',invalid='raise'):
        logs=math.log(spec.spot)+spec.risk_free_rate*t
        result=float(logs.mean() if geometric else logsumexp(logs)-math.log(len(t)))
    if not math.isfinite(result):raise FloatingPointError('unrepresentable average')
    return result


def deterministic_price(spec):
    if spec.volatility != 0:raise ValueError('deterministic_price requires sigma=0')
    if spec.risk_free_rate==0:
        return max(spec.spot-spec.strike,0.) if spec.kind=='call' else max(spec.strike-spec.spot,0.)
    times=np.asarray(spec.fixing_times)
    with np.errstate(over='raise',invalid='raise',under='ignore'):
        growth=spec.risk_free_rate*times
        average_growth=(float(growth.mean()) if spec.averaging=='geometric'
                        else float(log_mean_exp(growth[None,:])[0]))
    money=log_ratio(spec.spot,spec.strike)+average_growth
    if not math.isfinite(money):raise FloatingPointError('unrepresentable deterministic log moneyness')
    if (spec.kind=='call' and money<=0) or (spec.kind=='put' and money>=0):return 0.
    scale=math.log(spec.strike)-spec.risk_free_rate*spec.maturity_years
    if spec.kind=='call':return _exp(scale+money+math.log(-math.expm1(-money)))
    return _exp(scale+math.log(-math.expm1(money)))


def geometric_price(spec):
    if spec.volatility==0:
        return deterministic_price(replace(spec,averaging='geometric'))
    a,b2=geometric_log_moments(spec)
    sd=math.sqrt(b2)
    discount=spec.risk_free_rate*spec.maturity_years
    la=a+.5*b2-discount
    lk=math.log(spec.strike)-discount
    d2=(a-math.log(spec.strike))/sd
    d1=d2+sd
    if la<=lk:
        call=_difference(la+float(log_ndtr(d1)),lk+float(log_ndtr(d2)))
        if spec.kind=='call':return call
        parity=0. if la==lk else _difference(lk,la)
        result=parity+call
    else:
        put=_difference(lk+float(log_ndtr(-d2)),la+float(log_ndtr(-d1)))
        if spec.kind=='put':return put
        result=_difference(la,lk)+put
    if not math.isfinite(result):raise FloatingPointError('unrepresentable geometric price')
    return result


def arithmetic_bounds(spec):
    discount=spec.risk_free_rate*spec.maturity_years
    la=_average_log(spec)-discount
    lk=math.log(spec.strike)-discount
    asset, strike=_exp(la),_exp(lk)
    if spec.kind=='call':return (max(asset-strike,0.),asset)
    return (max(strike-asset,0.),strike)
