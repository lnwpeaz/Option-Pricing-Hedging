"""Catch S0-in-average, discount, normalization and tail-payoff errors."""
from dataclasses import replace
import math
import numpy as np
import pytest
from option_hedging.asian_contracts import AsianOptionSpec
from option_hedging.pricing.asian_samples import discounted_payoffs


def test_hand_worked_zero_normal_paths_and_single_fixing():
    s=AsianOptionSpec(100,95,.05,.2,'call',(.25,1.))
    a,g=discounted_payoffs(s,np.zeros((1,2)))
    prices=[100*math.exp(.03*.25),100*math.exp(.03)]
    assert a[0]==pytest.approx(math.exp(-.05)*(sum(prices)/2-95)/100)
    assert g[0]==pytest.approx(math.exp(-.05)*(math.sqrt(prices[0]*prices[1])-95)/100)
    one=replace(s,fixing_times=(1.,))
    a,g=discounted_payoffs(one,np.array([[0.],[1.],[-1.]]))
    np.testing.assert_allclose(a,g,atol=1e-15)


@pytest.mark.parametrize('kind',['call','put'])
@pytest.mark.parametrize('construction',['increments','bridge'])
def test_arithmetic_geometric_ordering(kind,construction):
    s=AsianOptionSpec(100,100,-.02,.3,kind,(.05,.2,1.))
    z=np.random.default_rng(84).standard_normal((1000,3)); before=z.copy()
    a,g=discounted_payoffs(s,z,construction=construction)
    assert np.all(a>=g-1e-14) if kind=='call' else np.all(a<=g+1e-14)
    np.testing.assert_array_equal(z,before)


def test_deterministic_and_tiny_positive_currency_scale():
    s=AsianOptionSpec(1e-300,9e-301,.04,0,'call',(.25,.5))
    a,g=discounted_payoffs(s,np.array([[100.,-100.],[0.,0.]]))
    assert a[0]==pytest.approx(math.exp(-.02)*((math.exp(.01)+math.exp(.02))/2-.9),rel=2e-12)
    assert a[0]==a[1] and g[0]==g[1]


def test_unrepresentable_payoffs_fail_explicitly():
    s=AsianOptionSpec(100,100,0,1000,'put',(1.,))
    # Put is finite even when the underlying is too small to exponentiate.
    a,g=discounted_payoffs(s,np.zeros((1,1)))
    np.testing.assert_allclose(a,[1.]);np.testing.assert_allclose(g,[1.])
    huge=replace(s,kind='call',volatility=1.)
    with pytest.raises(FloatingPointError):discounted_payoffs(huge,np.array([[1000.]]))
    tiny=replace(s,kind='call',volatility=.2,risk_free_rate=1000.)
    with pytest.raises(FloatingPointError):discounted_payoffs(tiny,np.array([[-4994.9]]))


def test_near_strike_kernel_does_not_erase_representable_put():
    from option_hedging.pricing.asian_samples import target_payoffs
    k=math.nextafter(100.,math.inf)
    s=AsianOptionSpec(100,k,0,0,'put',(.25,1.))
    a,g=discounted_payoffs(s,np.zeros((1,2)))
    want=(k-100)/100
    assert a[0]==pytest.approx(want,rel=1e-14,abs=0)
    assert g[0]==pytest.approx(want,rel=1e-14,abs=0)
    assert target_payoffs(s,np.zeros((1,2)))[0]==pytest.approx(want,rel=1e-14,abs=0)


def test_tiny_arithmetic_log_average_retains_positive_call():
    s=AsianOptionSpec(100,100,.5e-34,1e-17,'call',(.25,1.))
    z=np.ones((1,2));w=np.array([.5,.5+math.sqrt(.75)])
    want=math.exp(-.5e-34)*float(np.expm1(1e-17*w).mean())
    a,g=discounted_payoffs(s,z)
    assert a[0]==pytest.approx(want,rel=1e-13,abs=0)
    assert g[0]>0


def test_tiny_symmetric_logs_retain_second_order_arithmetic_payoff():
    sigma=1e-18
    s=AsianOptionSpec(100,100,.5*sigma*sigma,sigma,'call',(.25,1.))
    z=np.array([[2.,-2/math.sqrt(.75)]])
    a,_=discounted_payoffs(s,z)
    want=math.exp(-.5*sigma*sigma)*2*math.sinh(sigma/2)**2
    assert a[0]==pytest.approx(want,rel=1e-13,abs=0)
