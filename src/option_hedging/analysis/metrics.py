"""Pathwise hedge error and shared-path bootstrap uncertainty, conditional on model."""

import math
from numbers import Integral

import numpy as np


BOOTSTRAP_FIELDS=('mean_pnl','standard_deviation','rmse','pnl_q05','pnl_median','pnl_q95')
BASES=('model','common_reference')


def _vector(values,name):
    if isinstance(values,(list,tuple)) and any(isinstance(v,(bool,np.bool_)) for v in values):
        raise TypeError(f'{name} cannot contain booleans')
    array=np.asarray(values)
    if array.dtype.kind not in 'iuf':
        raise TypeError(f'{name} must contain real numbers')
    array=np.asarray(array,dtype=float)
    if array.ndim!=1 or len(array)<2 or not np.all(np.isfinite(array)):
        raise ValueError(f'{name} must be a finite vector with at least two paths')
    return array


def _statistics(values):
    """Scaled centered moments/quantiles, observations on the last axis."""
    scale=np.max(np.abs(values),axis=-1,keepdims=True)
    normalized=np.divide(values,scale,out=np.zeros_like(values),where=scale!=0)
    factor=scale[...,0]
    quantiles=np.quantile(normalized,[.05,.5,.95],axis=-1)
    result=np.stack([factor*np.mean(normalized,axis=-1),
                     factor*np.std(normalized,axis=-1,ddof=1),
                     factor*np.sqrt(np.mean(normalized**2,axis=-1)),
                     *(factor*q for q in quantiles)],axis=-1)
    if not np.all(np.isfinite(result)):
        raise ValueError('Statistics outside finite range')
    return result


def _wilson(p,n):
    z=1.959963984540054
    center=(p+z*z/(2*n))/(1+z*z/n)
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    return max(0.,center-half),min(1.,center+half)


def summarize(*,terminal_pnl,nominal_costs,turnover):
    pnl=_vector(terminal_pnl,'terminal_pnl')
    costs=_vector(nominal_costs,'nominal_costs')
    turns=_vector(turnover,'turnover')
    if costs.shape!=pnl.shape or turns.shape!=pnl.shape or np.any(costs<0) or np.any(turns<0):
        raise ValueError('Costs/turnover must align with paths and be nonnegative')
    result=dict(zip(BOOTSTRAP_FIELDS,map(float,_statistics(pnl))))
    probability=float(np.mean(pnl<0))
    low,high=_wilson(probability,len(pnl))
    result.update(paths=len(pnl),probability_loss=probability,
                  loss_probability_ci_low=low,loss_probability_ci_high=high,
                  mean_nominal_costs=float(_statistics(costs)[0]),
                  mean_turnover=float(_statistics(turns)[0]))
    return result


def _integer(name,value,minimum):
    if isinstance(value,(bool,np.bool_)) or not isinstance(value,Integral):
        raise TypeError(f'{name} must be integer')
    if value<minimum:
        raise ValueError(f'{name} must be at least{minimum}')


def summarize_study(cases,comparisons,*,bootstrap_repeats,seed,batch_size=16):
    """Common whole-path resamples preserve covariance in all comparisons.

    Cases retain identical path ordering. CIs are pointwise percentile-bootstrap
    intervals, not simultaneous claims, forecasts or model-risk uncertainty.
    Funding fields always refer to the original model-premium ledger, explicitly
    named as such; the common-premium adjustment here changes terminal P&L only.
    Returns metrics, paired rows, (repeats,cells,6) bootstrap data and cell labels.
    """
    _integer('bootstrap_repeats',bootstrap_repeats,2)
    _integer('seed',seed,0)
    _integer('batch_size',batch_size,1)
    if not cases or len({c['scenario_id'] for c in cases})!=len(cases):
        raise ValueError('Cases must have unique scenario IDs')
    vectors=[]
    metrics=[]
    labels=[]
    n=None
    for case in cases:
        pnl=_vector(case['terminal_pnl'],'terminal_pnl')
        if n is not None and n!=len(pnl):
            raise ValueError('Every case must retain the same path count/order')
        n=len(pnl)
        financed=_vector(case['financed_costs'],'financed_costs')
        borrowing=_vector(case['max_cash_borrowing'],'max_cash_borrowing')
        if financed.shape!=pnl.shape or borrowing.shape!=pnl.shape or np.any(financed<0) or np.any(borrowing<0):
            raise ValueError('Cost/funding vectors must align and be nonnegative')
        if not math.isfinite(case['premium_shift']):
            raise ValueError('Premium shift must be finite')
        for basis in BASES:
            values=pnl+(case['premium_shift'] if basis=='common_reference' else 0.)
            row=summarize(terminal_pnl=values,nominal_costs=case['nominal_costs'],turnover=case['turnover'])
            row.update({key:case[key] for key in ('scenario_id','strategy','hedge_volatility',
                       'rebalance_every_steps','one_way_cost_bps','initial_premium','reference_premium','premium_shift')})
            row.update(premium_basis=basis,mean_financed_costs=float(_statistics(financed)[0]),
                       model_premium_mean_peak_cash_borrowing=float(_statistics(borrowing)[0]),
                       model_premium_max_observed_cash_borrowing=float(np.max(borrowing)))
            metrics.append(row)
            vectors.append(values)
            labels.append(dict(scenario_id=case['scenario_id'],premium_basis=basis))
    lookup={(r['scenario_id'],r['premium_basis']):i for i,r in enumerate(labels)}
    for pair in comparisons:
        if (pair['left'],'model') not in lookup or (pair['right'],'model') not in lookup:
            raise ValueError('Unknown comparison scenario ID')
    rng=np.random.Generator(np.random.PCG64(np.random.SeedSequence([50,int(seed)])))
    bootstrap=np.empty((bootstrap_repeats,len(vectors),len(BOOTSTRAP_FIELDS)))
    for start in range(0,bootstrap_repeats,batch_size):
        stop=min(start+batch_size,bootstrap_repeats)
        ids=rng.integers(0,n,size=(stop-start,n))
        for cell,values in enumerate(vectors):
            bootstrap[start:stop,cell,:]=_statistics(values[ids])
    for cell,row in enumerate(metrics):
        for field,name in enumerate(BOOTSTRAP_FIELDS):
            low,high=np.quantile(bootstrap[:,cell,field],[.025,.975])
            row[name+'_ci_low'],row[name+'_ci_high']=float(low),float(high)
    paired=[]
    for pair in comparisons:
        for basis in BASES:
            left,right=(lookup[(pair[key],basis)] for key in ('left','right'))
            row=dict(comparison_id=pair['comparison_id'],comparison_kind=pair['kind'],
                     left_scenario_id=pair['left'],right_scenario_id=pair['right'],premium_basis=basis,paths=n)
            for field,name in ((0,'mean_pnl'),(2,'rmse')):
                low,high=np.quantile(bootstrap[:,left,field]-bootstrap[:,right,field],[.025,.975])
                row[name+'_difference']=metrics[left][name]-metrics[right][name]
                row[name+'_difference_ci_low'],row[name+'_difference_ci_high']=float(low),float(high)
            paired.append(row)
    return metrics,paired,bootstrap,labels
