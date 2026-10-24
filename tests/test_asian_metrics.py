"""Hand-derived errors and paired resampling, including uncertain truth."""
import math
import numpy as np
import pandas as pd
import pytest
from option_hedging.analysis.asian_metrics import coverage_flags,summarize


def fixture_rows():
    rows=[]
    for method,values in [('sobol',[-1.,0.,1.]),('sobol_bridge',[-.5,0.,.5])]:
        for repeat,value in enumerate(values):
            rows.append(dict(contract_id='c000',n_paths=64,macro_repeat=repeat,method=method,
                price=value,standard_error=.2,ci_low=value-.4,ci_high=value+.4,status='sampled',
                production_paths=64,pilot_paths=0,payoff_evaluations=64,control_payoff_evaluations=0,normal_coordinates=128))
    return pd.DataFrame(rows)


def reference(radius=0,kind='analytic_model',status='available'):
    return pd.DataFrame([dict(contract_id='c000',price=0.,precision_radius=radius,
        precision_kind=kind,status=status,is_exact=radius==0)])


def test_reference_band_possible_and_definite_are_distinct():
    assert coverage_flags(-.1,.1,0.,.2)==(True,False)
    assert coverage_flags(-.3,.3,0.,.2)==(True,True)
    assert coverage_flags(.3,.4,0.,.2)==(False,False)


def test_hand_rmse_bootstrap_pairing_and_zero_denominator():
    metrics,paired=summarize(fixture_rows(),reference(),bootstrap_repeats=64,seed=11)
    m=metrics.set_index('method')
    assert m.loc['sobol','rmse']==pytest.approx(math.sqrt(2/3))
    assert m.loc['sobol','bias']==0 and m.loc['sobol','empirical_sd']==1
    assert m.loc['sobol','coverage_exact']==pytest.approx(1/3)
    assert 0<m.loc['sobol','coverage_wilson_low']<1/3<m.loc['sobol','coverage_wilson_high']<1
    p=paired.iloc[0]
    assert p['method_a']=='sobol_bridge' and p['method_b']=='sobol'
    assert p['rmse_ratio']==.5
    # Every nonzero paired bootstrap sample has exactly half the RMSE.
    assert p['rmse_ratio_ci_low']==pytest.approx(.5) and p['rmse_ratio_ci_high']==pytest.approx(.5)
    assert p['paired_repeats']==3


def test_reference_dominance_withholds_rank_but_keeps_dispersion():
    metrics,_=summarize(fixture_rows(),reference(.2,'empirical_cross_method'),bootstrap_repeats=64,seed=11)
    assert metrics['reference_dominates_error'].all() and not metrics['rank_eligible'].any()
    m=metrics.set_index('method').loc['sobol']
    assert m['conditional_rmse_low']==pytest.approx(math.sqrt(2/3)-.2)
    assert m['conditional_rmse_high']==pytest.approx(math.sqrt(2/3)+.2)
    assert pd.isna(m['coverage_exact']) and m['empirical_sd']==1


def test_missing_reference_and_failed_rows_remain_visible():
    rows=fixture_rows();rows.loc[0,'status']='failed';rows.loc[0,'price']=np.nan
    metrics,paired=summarize(rows,reference(None,status='unavailable'),bootstrap_repeats=64,seed=11)
    m=metrics.set_index('method').loc['sobol']
    assert m['requested_count']==3 and m['completed_count']==2 and m['failed_count']==1
    assert pd.isna(m['rmse']) and m['reference_dominates_error'] and m['empirical_sd']>0
    assert paired.iloc[0]['paired_repeats']==2


@pytest.mark.parametrize('scale',[1e-300,1e200])
def test_currency_scale_does_not_zero_or_overflow_empirical_dispersion(scale):
    rows=fixture_rows()
    for field in ['price','ci_low','ci_high']:rows[field]=(rows[field]+2)*scale
    rows['standard_error']*=scale
    refs=reference();refs['price']=2*scale
    m,_=summarize(rows,refs,bootstrap_repeats=64,seed=11)
    one=m.set_index('method').loc['sobol']
    assert one['empirical_sd']==pytest.approx(scale,rel=1e-13,abs=0)
    assert one['rmse']==pytest.approx(scale*math.sqrt(2/3),rel=1e-13,abs=0)
