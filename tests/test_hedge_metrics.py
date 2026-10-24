"""Hand metrics and paired uncertainty distinguish precision from market validity."""
import importlib
import math

import numpy as np
import pytest


def module():
    return importlib.import_module('option_hedging.analysis.metrics')


def case(scenario_id,pnl,shift=0.):
    n=len(pnl)
    return dict(scenario_id=scenario_id,strategy='delta_hedged',hedge_volatility=.2,
                rebalance_every_steps=1,one_way_cost_bps=0.,premium_shift=shift,
                initial_premium=10.,reference_premium=10.,terminal_pnl=np.array(pnl),
                nominal_costs=np.zeros(n),financed_costs=np.zeros(n),turnover=np.ones(n),
                max_cash_borrowing=np.ones(n)*50.)


def test_hand_metrics_and_wilson_interval():
    result=module().summarize(terminal_pnl=np.array([-2.,0.,2.,2.]),nominal_costs=np.array([1.,2.,3.,4.]),turnover=np.array([1.,2.,3.,4.]))
    assert result['mean_pnl']==.5
    assert result['rmse']==pytest.approx(math.sqrt(3))
    assert result['standard_deviation']==pytest.approx(math.sqrt(11/3))
    assert result['pnl_q05']==pytest.approx(-1.7)
    assert result['pnl_median']==1
    assert result['pnl_q95']==2
    assert result['probability_loss']==.25
    assert result['loss_probability_ci_low']==pytest.approx(.04558726080970055)
    assert result['loss_probability_ci_high']==pytest.approx(.6993581574175981)
    assert result['mean_nominal_costs']==2.5


@pytest.mark.parametrize('scale',[1e-170,1e150])
def test_hand_statistics_currency_scaling(scale):
    result=module().summarize(terminal_pnl=np.array([-2.,0.,2.,2.])*scale,nominal_costs=np.ones(4)*scale,turnover=np.ones(4))
    assert result['rmse']/scale==pytest.approx(math.sqrt(3))
    assert result['standard_deviation']/scale==pytest.approx(math.sqrt(11/3))


def test_shared_bootstrap_preserves_identical_pairs_and_exact_premium_shift():
    cases=[case(0,[-2.,0.,2.,2.]),case(1,[-2.,0.,2.,2.],shift=2.)]
    pairs=[dict(comparison_id=0,kind='test',left=1,right=0)]
    metrics,comparisons,boot,labels=module().summarize_study(cases,pairs,bootstrap_repeats=128,seed=90,batch_size=16)
    assert len(metrics)==4 and len(comparisons)==2
    assert boot.shape==(128,4,6)
    raw=next(r for r in comparisons if r['premium_basis']=='model')
    assert raw['rmse_difference']==raw['rmse_difference_ci_low']==raw['rmse_difference_ci_high']==0
    shifted=next(r for r in comparisons if r['premium_basis']=='common_reference')
    assert shifted['mean_pnl_difference']==2
    assert shifted['mean_pnl_difference_ci_low']==shifted['mean_pnl_difference_ci_high']==2
    common=next(r for r in metrics if r['scenario_id']==1 and r['premium_basis']=='common_reference')
    assert common['mean_pnl']==2.5
    assert common['rmse']==pytest.approx(3.)
    assert common['standard_deviation']==pytest.approx(math.sqrt(11/3))
    assert labels[0]['premium_basis']=='model'


def test_bootstrap_reproducible_and_does_not_change_global_rng():
    args=([case(0,[-2.,0.,2.,2.])],[])
    state=np.random.get_state()
    first=module().summarize_study(*args,bootstrap_repeats=32,seed=7,batch_size=8)
    second=module().summarize_study(*args,bootstrap_repeats=32,seed=7,batch_size=8)
    assert first[0]==second[0]
    np.testing.assert_array_equal(first[2],second[2])
    np.testing.assert_array_equal(state[1],np.random.get_state()[1])


@pytest.mark.parametrize('pnl,cost,turnover',[
    ([1.],[0.],[0.]),([0.,float('nan')],[0.,0.],[0.,0.]),
    ([0.,1.],[0.],[0.,0.]),([0.,1.],[0.,-1.],[0.,0.]),
])
def test_invalid_observations_rejected(pnl,cost,turnover):
    with pytest.raises((TypeError,ValueError)):
        module().summarize(terminal_pnl=pnl,nominal_costs=cost,turnover=turnover)
