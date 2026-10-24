"""Catch schedule/convention errors and cancellation in independent references."""
from dataclasses import FrozenInstanceError, replace
import math
import numpy as np
import pytest
from option_hedging.asian_contracts import AsianOptionSpec
from option_hedging.pricing.asian_reference import (geometric_log_moments, geometric_price,
    deterministic_price, arithmetic_bounds)
from option_hedging.validation.asian_reference import integrate_geometric, integrate_two_fixing


def spec(**kw):
    return AsianOptionSpec(**dict(dict(spot=100, strike=100, risk_free_rate=.05,
        volatility=.2, kind='call', fixing_times=(.25,.5,1)), **kw))


def test_single_fixing_literal_and_put_call_parity():
    s=spec(fixing_times=(1,))
    assert geometric_price(s)==pytest.approx(10.450583572185565,abs=1e-10)
    assert geometric_price(s)-geometric_price(replace(s,kind='put'))==pytest.approx(100-100*math.exp(-.05))


def test_nonuniform_covariance_and_immutable_normalization():
    s=spec(risk_free_rate=-.02,volatility=.3,fixing_times=[.1,.4,1])
    a,v=geometric_log_moments(s)
    assert a==pytest.approx(math.log(100)+(-.02-.3**2/2)*.5)
    assert v==pytest.approx(.3**2/9*sum(min(x,y) for x in [.1,.4,1] for y in [.1,.4,1]))
    assert s.fixing_times==(.1,.4,1.) and type(s.spot) is float
    with pytest.raises(FrozenInstanceError):s.spot=20


@pytest.mark.parametrize('kind',['call','put'])
@pytest.mark.parametrize('averaging',['arithmetic','geometric'])
def test_deterministic_actual_fixing_average(kind,averaging):
    s=spec(spot=120,strike=125,risk_free_rate=.04,volatility=0,kind=kind,
           fixing_times=(.25,.5),averaging=averaging)
    avg=(120*math.exp(.01)+120*math.exp(.02))/2 if averaging=='arithmetic' else 120*math.exp(.015)
    want=math.exp(-.02)*max((avg-125)*(1 if kind=='call' else -1),0)
    assert deterministic_price(s)==pytest.approx(want,abs=2e-13)
    assert integrate_geometric(s).price==pytest.approx(geometric_price(s))


@pytest.mark.parametrize('kw',[
 {'fixing_times':()}, {'fixing_times':(0,1)}, {'fixing_times':(1,1)},
 {'fixing_times':(.5,.1)}, {'fixing_times':(True,)}, {'fixing_times':('1',)},
 {'fixing_times':(complex(1),)}, {'fixing_times':(float('nan'),)},
 {'spot':0},{'spot':True},{'strike':float('inf')},{'risk_free_rate':'0.05'},
 {'risk_free_rate':float('nan')},{'volatility':-.1},{'kind':'CALL'},{'averaging':'weighted'}])
def test_invalid_contracts_rejected(kw):
    with pytest.raises((ValueError,TypeError)):spec(**kw)


@pytest.mark.parametrize('kind',['call','put'])
@pytest.mark.parametrize('times',[(1,),(.1,.4,1),(.2,.7)])
def test_geometric_formula_against_independent_payoff_integration(kind,times):
    s=spec(kind=kind,fixing_times=times,risk_free_rate=-.03,strike=110)
    ref=integrate_geometric(s)
    assert abs(geometric_price(s)-ref.price)<max(2e-10,4*ref.error_estimate+ref.tail_bound)
    assert ref.evaluations>0 and ref.tail_bound>=0


@pytest.mark.parametrize('kind',['call','put'])
def test_arithmetic_bounds_and_two_fixing_reference(kind):
    s=spec(kind=kind,fixing_times=(.2,1),risk_free_rate=-.02)
    ref=integrate_two_fixing(s)
    lo,hi=arithmetic_bounds(s)
    assert lo<ref.price<hi
    g=geometric_price(s)
    assert ref.price>g if kind=='call' else ref.price<g
    one=spec(kind=kind,fixing_times=(1,))
    with pytest.raises(ValueError):integrate_two_fixing(one)


def test_small_tail_and_currency_scales_are_not_silently_zeroed():
    p=geometric_price(spec(spot=1,strike=100,fixing_times=(1,)))
    assert 0<p<1e-90
    tiny=geometric_price(spec(spot=1e-300,strike=1e-300,fixing_times=(1,)))
    assert tiny==pytest.approx(1.0450583572185565e-301,rel=2e-12,abs=0)
    with pytest.raises(FloatingPointError):geometric_price(spec(spot=1,strike=1e300,fixing_times=(1,)))
    with pytest.raises(FloatingPointError):geometric_price(spec(volatility=1e300))
    with pytest.raises(FloatingPointError):arithmetic_bounds(spec(risk_free_rate=-1000))
    with pytest.raises(ValueError):deterministic_price(spec())


@pytest.mark.parametrize('spot',[100.,1e16])
@pytest.mark.parametrize('kind',['call','put'])
@pytest.mark.parametrize('averaging',['arithmetic','geometric'])
def test_deterministic_nextafter_strike_preserves_positive_payoff(spot,kind,averaging):
    strike=math.nextafter(spot,math.inf if kind=='put' else 0.)
    s=spec(spot=spot,strike=strike,risk_free_rate=0,volatility=0,kind=kind,averaging=averaging)
    want=abs(strike-spot)
    assert deterministic_price(s)==pytest.approx(want,rel=1e-14,abs=0)


@pytest.mark.parametrize('averaging',['arithmetic','geometric'])
def test_deterministic_small_positive_drift_is_not_rounded_to_zero(averaging):
    s=spec(spot=100,strike=100,risk_free_rate=1e-17,volatility=0,fixing_times=(.25,1),averaging=averaging)
    want=100*math.exp(-1e-17)*(.5*(math.expm1(.25e-17)+math.expm1(1e-17)) if averaging=='arithmetic' else math.expm1(.625e-17))
    assert deterministic_price(s)==pytest.approx(want,rel=1e-13,abs=0)
