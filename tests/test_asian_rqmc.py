"""Scramble-level reconstruction, endpoints, pairing and no false IID errors."""
from dataclasses import replace
import math
import numpy as np
import pytest
from scipy.special import ndtri
from scipy.stats import qmc,t
from option_hedging.asian_contracts import AsianOptionSpec
from option_hedging.pricing.asian_monte_carlo import price
from option_hedging.pricing.asian_reference import geometric_price
from option_hedging.pricing.asian_samples import target_payoffs
from option_hedging.pricing.asian_rqmc import normals_from_uniforms

S=AsianOptionSpec(100,100,.05,.2,'call',(.2,.6,1.))


@pytest.mark.parametrize('method,construction',[('sobol','increments'),('sobol_bridge','bridge')])
def test_reconstruct_scrambles_pairing_and_parent_rng(method,construction):
    parent=np.random.default_rng(61)
    entropies=parent.integers(0,2**32,size=(16,4),dtype=np.uint32)
    means=[]
    for entropy in entropies:
        child=np.random.Generator(np.random.PCG64(np.random.SeedSequence(entropy)))
        u=qmc.Sobol(d=3,scramble=True,bits=52,rng=child).random_base2(4)
        means.append(100*target_payoffs(S,ndtri(u),construction=construction).mean())
    rng=np.random.default_rng(61)
    r=price(S,n_paths=256,method=method,scrambles=16,rng=rng,batch_size=6)
    np.testing.assert_allclose(r.scramble_prices,means,atol=2e-13,rtol=0)
    se=np.std(means,ddof=1)/4
    assert r.price==pytest.approx(np.mean(means),abs=1e-13)
    assert r.standard_error==pytest.approx(se,abs=1e-13)
    assert r.ci_high-r.price==pytest.approx(t.ppf(.975,15)*se,abs=1e-13)
    assert (r.production_paths,r.independent_samples,r.scrambles,r.normal_coordinates,r.payoff_evaluations)==(256,16,16,768,256)
    assert r.pilot_paths==r.control_payoff_evaluations==0
    assert repr(rng.bit_generator.state)==repr(parent.bit_generator.state)
    assert isinstance(r.scramble_prices,tuple)


@pytest.mark.parametrize('u',[[[0.]],[[1.]],[[float('nan')]],[[float('inf')]],[[True]],[[1j]]])
def test_invalid_uniforms_and_endpoints_are_never_clipped(u):
    with pytest.raises((ValueError,TypeError)):normals_from_uniforms(u)


def test_finite_normal_transform_preserves_tails():
    u=np.array([[2**-52,.5,1-2**-52]])
    np.testing.assert_array_equal(normals_from_uniforms(u),ndtri(u))


@pytest.mark.parametrize('kw',[{'scrambles':1},{'scrambles':True},{'n_paths':65},
 {'n_paths':96},{'n_paths':256,'bits':3},{'bits':True},{'bits':0},{'bits':53}])
def test_invalid_rules_even_in_deterministic_limit(kw):
    args=dict(n_paths=64,scrambles=4,bits=52);args.update(kw)
    with pytest.raises((TypeError,ValueError)):
        price(replace(S,volatility=0),method='sobol',rng=np.random.default_rng(1),**args)


@pytest.mark.parametrize('method',['sobol','sobol_bridge'])
def test_deterministic_and_zero_observed_variance_are_distinct(method):
    rng=np.random.default_rng(5);state=repr(rng.bit_generator.state)
    exact=price(replace(S,volatility=0),n_paths=64,method=method,rng=rng,scrambles=4)
    assert exact.status=='deterministic' and exact.scramble_prices==() and exact.normal_coordinates==0
    assert repr(rng.bit_generator.state)==state
    rare=price(replace(S,strike=1e20),n_paths=64,method=method,rng=rng,scrambles=4)
    assert rare.status=='sampled' and rare.standard_error==0
    assert 'zero_observed_variance' in rare.diagnostics and len(rare.scramble_prices)==4


@pytest.mark.parametrize('method',['sobol','sobol_bridge'])
@pytest.mark.parametrize('times',[(1.,),(.07,.2,.6,1.)])
def test_independent_macro_repeats_against_geometric_truth(method,times):
    s=replace(S,fixing_times=times,averaging='geometric')
    values=[];ses=[]
    for seed in range(16):
        r=price(s,n_paths=1024,method=method,rng=np.random.default_rng(501+seed),scrambles=8)
        values.append(r.price);ses.append(r.standard_error)
    errors=np.array(values)-geometric_price(s)
    assert abs(errors.mean())<.03
    assert np.sqrt(np.mean(errors**2))<.1
    assert np.all(np.asarray(ses)>0)


def test_qmc_batch_policy_and_global_rng_state():
    before=np.random.get_state()
    a=price(S,n_paths=256,method='sobol_bridge',rng=np.random.default_rng(9),batch_size=2)
    b=price(S,n_paths=256,method='sobol_bridge',rng=np.random.default_rng(9),batch_size=128)
    assert a.price==pytest.approx(b.price,abs=2e-13)
    assert a.standard_error==pytest.approx(b.standard_error,abs=2e-13)
    assert all(np.array_equal(x,y) for x,y in zip(before,np.random.get_state()))
