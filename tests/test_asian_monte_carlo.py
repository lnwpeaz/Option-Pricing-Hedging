"""Independent reconstruction catches wrong units, reused pilots and counters."""
from dataclasses import replace
import math
import numpy as np
import pytest
from option_hedging.asian_contracts import AsianOptionSpec
from option_hedging.pricing.asian_samples import discounted_payoffs, target_payoffs
from option_hedging.pricing.asian_reference import geometric_price, deterministic_price
from option_hedging.pricing.asian_monte_carlo import price
from option_hedging.pricing._asian_statistics import ScaledMoments

S=AsianOptionSpec(100,100,.05,.2,'call',(.25,.5,1.))


def test_plain_independent_observations_and_singleton_batch_tail():
    z=np.random.default_rng(17).standard_normal((65,3));y,_=discounted_payoffs(S,z)
    r=price(S,n_paths=65,rng=np.random.default_rng(17),batch_size=16)
    assert r.price==pytest.approx(100*y.mean(),abs=1e-12)
    assert r.standard_error==pytest.approx(100*y.std(ddof=1)/math.sqrt(65),abs=1e-12)
    assert r.ci_low==pytest.approx(r.price-1.959963984540054*r.standard_error)
    assert (r.production_paths,r.independent_samples,r.normal_coordinates,r.payoff_evaluations)==(65,65,195,65)
    assert r.control_payoff_evaluations==r.pilot_paths==0 and r.pilot_beta is None


def test_antithetic_se_on_pairs_and_actual_new_normal_count():
    z=np.random.default_rng(22).standard_normal((32,3))
    y,_=discounted_payoffs(S,z);opp,_=discounted_payoffs(S,-z);pairs=(y+opp)/2
    r=price(S,n_paths=64,method='antithetic',rng=np.random.default_rng(22),batch_size=14)
    assert r.price==pytest.approx(100*pairs.mean(),abs=1e-12)
    assert r.standard_error==pytest.approx(100*pairs.std(ddof=1)/math.sqrt(32),abs=1e-12)
    assert (r.independent_samples,r.production_paths,r.normal_coordinates,r.payoff_evaluations)==(32,64,96,64)


def test_control_uses_extra_pilot_then_disjoint_production_and_frozen_beta():
    rng=np.random.default_rng(97)
    py,px=discounted_payoffs(S,rng.standard_normal((33,3)))
    beta=np.cov(py,px,ddof=1)[0,1]/np.var(px,ddof=1)
    y,x=discounted_payoffs(S,rng.standard_normal((65,3)))
    values=y-beta*(x-geometric_price(S)/100)
    r=price(S,n_paths=65,method='control',rng=np.random.default_rng(97),batch_size=16,pilot_paths=33)
    assert r.pilot_beta==pytest.approx(beta,abs=2e-14)
    assert r.price==pytest.approx(100*values.mean(),abs=1e-12)
    assert r.standard_error==pytest.approx(100*values.std(ddof=1)/math.sqrt(65),abs=1e-12)
    assert (r.production_paths,r.pilot_paths,r.normal_coordinates,r.payoff_evaluations,r.control_payoff_evaluations)==(65,33,294,98,98)


@pytest.mark.parametrize('method',['plain','antithetic','control'])
def test_deterministic_is_distinct_no_rng_no_actual_work(method):
    s=replace(S,volatility=0);rng=np.random.default_rng(7);state=repr(rng.bit_generator.state)
    r=price(s,n_paths=16,rng=rng,method=method)
    assert r.price==deterministic_price(s) and r.ci_low==r.ci_high==r.price
    assert r.status=='deterministic' and r.requested_paths==16 and not r.diagnostics
    assert all(getattr(r,k)==0 for k in ['production_paths','independent_samples','pilot_paths','normal_coordinates','payoff_evaluations','control_payoff_evaluations','scrambles'])
    assert repr(rng.bit_generator.state)==state


def test_rare_zero_sample_is_not_exact_and_global_rng_unchanged():
    state=np.random.get_state()
    r=price(replace(S,strike=1e10),n_paths=16,rng=np.random.default_rng(9))
    assert r.status=='sampled' and r.standard_error==0 and 'zero_observed_variance' in r.diagnostics
    after=np.random.get_state()
    assert all(np.array_equal(a,b) for a,b in zip(state,after))


def test_geometric_target_and_fixed_seed_reproducibility():
    s=replace(S,averaging='geometric');z=np.random.default_rng(48).standard_normal((64,3))
    _,g=discounted_payoffs(s,z)
    np.testing.assert_array_equal(target_payoffs(s,z),g)
    r=price(s,n_paths=64,rng=np.random.default_rng(48))
    assert r.price==pytest.approx(g.mean()*100)
    assert r==price(s,n_paths=64,rng=np.random.default_rng(48))
    with pytest.raises(ValueError):price(s,n_paths=64,rng=np.random.default_rng(48),method='control')


@pytest.mark.parametrize('kw',[{'n_paths':True},{'n_paths':1},{'batch_size':1},{'pilot_paths':False},
 {'pilot_paths':1},{'scrambles':True},{'bits':53},{'rng':None},{'method':'other'},
 {'method':'antithetic','n_paths':5}])
def test_invalid_settings_even_deterministic(kw):
    args=dict(n_paths=16,rng=np.random.default_rng(1));args.update(kw)
    with pytest.raises((ValueError,TypeError)):price(replace(S,volatility=0),**args)


def test_scaled_moments_avoid_square_overflow_and_false_zero():
    m=ScaledMoments();m.update(np.array([1e200,2e200]));m.update(np.array([3e200]))
    assert m.mean_value==pytest.approx(2e200)
    assert m.standard_error==pytest.approx(1e200/math.sqrt(3))
    tiny=ScaledMoments();tiny.update(np.array([1e-200,2e-200,3e-200]))
    assert tiny.standard_error==pytest.approx(1e-200/math.sqrt(3),rel=1e-14,abs=0)
    with pytest.raises(FloatingPointError):m.update(np.array([float('inf')]))


def test_tiny_currency_estimates_preserved_and_output_range_rejected():
    tiny=replace(S,spot=1e-300,strike=1e-300)
    r=price(tiny,n_paths=64,rng=np.random.default_rng(5))
    normal=price(S,n_paths=64,rng=np.random.default_rng(5))
    assert r.price==pytest.approx(normal.price*1e-302,rel=1e-12,abs=0)
    assert r.standard_error>0
    with pytest.raises(FloatingPointError):price(replace(S,spot=1e308,strike=1e308,risk_free_rate=-1000,kind="put"),n_paths=64,rng=np.random.default_rng(5))
