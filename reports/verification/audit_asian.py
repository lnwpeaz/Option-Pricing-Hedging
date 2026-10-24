"""Independent saved-data audit; does not call the production metrics code."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import tomllib
import numpy as np
import pandas as pd
from scipy.stats import t


def read(path):return pd.read_csv(path,float_precision='round_trip')


def audit(root):
    config=tomllib.loads((root/'input_config.toml').read_text());s=config['study']
    e=read(root/'estimates.csv');q=read(root/'scramble_estimates.csv')
    refs=read(root/'reference_summary.csv').set_index('contract_id')
    raw=read(root/'reference_checks.csv');metrics=read(root/'metrics.csv');paired=read(root/'paired_comparisons.csv')
    expected=len(s['fixing_counts'])*len(s['strikes'])*len(s['production_paths'])*s['repeats']*len(s['methods'])
    assert len(e)==expected==2880 and len(q)==18432
    assert not (e.status=='failed').any()
    maxima={};checks=0
    def compare(name,actual,expected):
        nonlocal checks
        checks+=1
        if expected is None or (isinstance(expected,float) and math.isnan(expected)):
            assert pd.isna(actual),(name,actual,expected);return
        if isinstance(expected,(bool,np.bool_)):
            assert bool(actual)==bool(expected),(name,actual,expected);return
        actual=float(actual);expected=float(expected)
        diff=abs(actual-expected);maxima[name]=max(maxima.get(name,0.),diff)
        assert math.isclose(actual,expected,rel_tol=1e-10,abs_tol=2e-12),(name,actual,expected,diff)
    for identifier,g in q.groupby('estimate_id',sort=False):
        row=e[e.estimate_id==identifier].iloc[0];v=g.sort_values('scramble').price.to_numpy()
        mean=float(v.mean());se=float(v.std(ddof=1)/math.sqrt(len(v)));half=t.ppf(.975,len(v)-1)*se
        for field,value in [('price',mean),('standard_error',se),('ci_low',mean-half),('ci_high',mean+half)]:compare('qmc_'+field,row[field],value)
    for row in e.itertuples():
        n=int(row.n_paths);pilot=s['pilot_paths'] if row.method=='control' else 0
        units=n//2 if row.method=='antithetic' else (s['scrambles'] if row.method.startswith('sobol') else n)
        normal_paths=n//2 if row.method=='antithetic' else n
        expected_work=dict(requested_paths=n,production_paths=n,independent_samples=units,pilot_paths=pilot,
            normal_coordinates=(normal_paths+pilot)*row.fixing_count,payoff_evaluations=n+pilot,
            control_payoff_evaluations=n+pilot if row.method=='control' else 0,
            scrambles=s['scrambles'] if row.method.startswith('sobol') else 0)
        for field,value in expected_work.items():compare('work_'+field,getattr(row,field),value)
        if row.method=='control':
            cid_index=int(row.contract_id[1:]);strike_index=cid_index%len(s['strikes'])
            times=np.array([((365*j)//row.fixing_count)/365 for j in range(1,row.fixing_count+1)])
            rng=np.random.default_rng(np.random.SeedSequence([80,row.fixing_count,strike_index,n,row.macro_repeat,2,s['seed']]))
            z=rng.standard_normal((pilot,row.fixing_count));w=np.cumsum(z*np.sqrt(np.diff(np.r_[0.,times])),axis=1)
            o=config['option'];logs=(o['risk_free_rate']-.5*o['volatility']**2)*times+o['volatility']*w
            y=np.exp(-o['risk_free_rate']*times[-1])*np.maximum(np.exp(logs).mean(axis=1)-row.strike/o['spot'],0)
            x=np.exp(-o['risk_free_rate']*times[-1])*np.maximum(np.exp(logs.mean(axis=1))-row.strike/o['spot'],0)
            beta=float(np.dot(y-y.mean(),x-x.mean())/np.dot(x-x.mean(),x-x.mean()))
            compare('pilot_beta',row.pilot_beta,beta)
    for cid,ref in refs.iterrows():
        rows=raw[(raw.contract_id==cid)&(raw.source=='quantlib')]
        choi=rows[rows.engine=='choi'].price.to_numpy();fd=rows[rows.engine=='fd'].price.to_numpy()
        assert len(choi)==len(fd)==3 and (rows.status=='completed').all()
        radius=max(2*abs(choi[-1]-choi[-2]),2*abs(fd[-1]-fd[-2]),abs(choi[-1]-fd[-1]))
        compare('reference_price',ref.price,choi[-1]);compare('reference_radius',ref.precision_radius,radius)
        mc=rows[rows.engine=='mc_control'];values=mc.price.to_numpy()
        se=max(float(values.std(ddof=1)/2),float(np.sqrt(np.sum(mc.error_estimate.to_numpy()**2))/4))
        bad=radius>config['reference']['precision_target']
        bad |= abs(choi[-1]-choi[-2])>max(1e-10,1.05*abs(choi[-2]-choi[-3]))
        bad |= abs(fd[-1]-fd[-2])>max(1e-10,1.05*abs(fd[-2]-fd[-3]))
        bad |= abs(values.mean()-choi[-1])>3*se+radius
        assert ref.status==('low_precision' if bad else 'available')
    for (cid,n),group in e.groupby(['contract_id','n_paths'],sort=False):
        ref=refs.loc[cid];p=ref.price;radius=ref.precision_radius
        idx=np.random.default_rng(np.random.SeedSequence([81,int(cid[1:]),int(n),s['seed']])).integers(
            0,s['repeats'],size=(s['bootstrap_repeats'],s['repeats']))
        by={m:g.sort_values('macro_repeat') for m,g in group.groupby('method',sort=False)}
        def ci(v):return np.quantile(v,[.025,.975])
        for method,g in by.items():
            row=metrics[(metrics.contract_id==cid)&(metrics.n_paths==n)&(metrics.method==method)].iloc[0]
            v=g.price.to_numpy();err=v-p;rmse=float(np.sqrt(np.mean(err**2)))
            poss=((g.ci_low<=p+radius)&(g.ci_high>=p-radius)).to_numpy(dtype=float)
            definite=((g.ci_low<=p-radius)&(g.ci_high>=p+radius)).to_numpy(dtype=float)
            expected=dict(bias=float(err.mean()),rmse=rmse,empirical_sd=float(v.std(ddof=1)),
                mean_reported_se=float(g.standard_error.mean()),conditional_rmse_low=max(0.,rmse-radius),
                conditional_rmse_high=rmse+radius,possible_coverage=float(poss.mean()),definite_coverage=float(definite.mean()),
                reference_dominates_error=bool(radius>.1*rmse or ref.status!='available'),
                rank_eligible=bool(radius<=.1*rmse and ref.status=='available'),requested_count=len(g),completed_count=len(g),
                failed_count=0,zero_se_count=int((g.standard_error==0).sum()))
            for name,vals in [('rmse',np.sqrt(np.mean(err[idx]**2,axis=1))),('bias',err[idx].mean(axis=1)),('sd',v[idx].std(axis=1,ddof=1))]:
                expected[f'bootstrap_{name}_low'],expected[f'bootstrap_{name}_high']=ci(vals)
            for name,vals in [('possible',poss),('definite',definite)]:
                expected[f'{name}_coverage_ci_low'],expected[f'{name}_coverage_ci_high']=ci(vals[idx].mean(axis=1))
            for field in ['production_paths','pilot_paths','payoff_evaluations','control_payoff_evaluations','normal_coordinates']:
                expected[field+'_mean']=float(g[field].mean())
            expected['rmse_squared_times_production_paths']=rmse**2*g.production_paths.mean()
            expected['rmse_squared_times_total_payoffs']=rmse**2*(g.payoff_evaluations+g.control_payoff_evaluations).mean()
            for name,value in expected.items():compare('metric_'+name,row[name],value)
        for row in paired[(paired.contract_id==cid)&(paired.n_paths==n)].itertuples():
            a=by[row.method_a].price.to_numpy();b=by[row.method_b].price.to_numpy()
            ea=a-p;eb=b-p;ra=np.sqrt(np.mean(ea**2));rb=np.sqrt(np.mean(eb**2))
            ba=np.sqrt(np.mean(ea[idx]**2,axis=1));bb=np.sqrt(np.mean(eb[idx]**2,axis=1))
            expected=dict(paired_repeats=len(a),mean_price_difference=float((a-b).mean()),rmse_ratio=float(ra/rb),
                rmse_difference=float(ra-rb),undefined_ratio_bootstraps=0,
                rank_eligible=bool(radius<=.1*ra and radius<=.1*rb and ref.status=='available'))
            expected['difference_ci_low'],expected['difference_ci_high']=ci((a-b)[idx].mean(axis=1))
            expected['rmse_ratio_ci_low'],expected['rmse_ratio_ci_high']=ci(ba/bb)
            expected['rmse_difference_ci_low'],expected['rmse_difference_ci_high']=ci(ba-bb)
            for name,value in expected.items():compare('paired_'+name,getattr(row,name),value)
    from option_hedging.experiments.verify_run import verify_run
    return dict(verification=verify_run(root),estimate_rows=len(e),scramble_rows=len(q),
        qmc_estimates_checked=int(e.method.str.startswith('sobol').sum()),control_pilots_checked=int((e.method=='control').sum()),
        metric_cells_checked=len(metrics),paired_comparisons_checked=len(paired),numeric_assertions=checks,
        maximum_absolute_differences=maxima,
        total_production_paths=int(e.production_paths.sum()),total_pilot_paths=int(e.pilot_paths.sum()),
        total_normal_coordinates=int(e.normal_coordinates.sum()),
        external_reference_statuses={str(k):int(v) for k,v in refs.status.value_counts().items()})


def extra_cases():
    from option_hedging.asian_contracts import AsianOptionSpec
    from option_hedging.pricing.asian_monte_carlo import price
    from option_hedging.validation.asian_reference import integrate_geometric,integrate_two_fixing
    cases=[('single_geometric_call',AsianOptionSpec(100,100,.05,.2,'call',(1.,),'geometric'),10.450583572185565),
           ('irregular_geometric_put',AsianOptionSpec(100,95,-.02,.3,'put',(.07,.2,.5,1.),'geometric'),None),
           ('two_fixing_arithmetic_put',AsianOptionSpec(100,105,-.02,.3,'put',(.1,.7)),None)]
    outputs=[]
    for name,spec,truth in cases:
        if truth is None:truth=(integrate_geometric(spec) if spec.averaging=='geometric' else integrate_two_fixing(spec)).price
        for method in ['plain','antithetic','control','sobol','sobol_bridge']:
            if method=='control' and spec.averaging=='geometric':continue
            values=[];covered=0
            for seed in range(8):
                r=price(spec,n_paths=4096,rng=np.random.default_rng(1600+seed),method=method,scrambles=16)
                values.append(r.price);covered+=r.ci_low<=truth<=r.ci_high
            v=np.array(values);error=float(v.mean()-truth);sem=float(v.std(ddof=1)/math.sqrt(8))
            assert abs(error)<=6*sem+.001,(name,method,error,sem)
            outputs.append(dict(case=name,method=method,reference=truth,macro_repeats=8,mean_error=error,
                                empirical_sem=sem,intervals_covering_reference=int(covered),acceptance='aggregate mean within 6 empirical SEM + 0.001; not all-CI coverage'))
    deterministic=AsianOptionSpec(120,125,.04,0,'put',(.1,.25,.5))
    for method in ['plain','antithetic','control','sobol','sobol_bridge']:
        rng=np.random.default_rng(22);state=repr(rng.bit_generator.state)
        r=price(deterministic,n_paths=64,method=method,rng=rng)
        assert r.status=='deterministic' and r.production_paths==r.normal_coordinates==0 and repr(rng.bit_generator.state)==state
        outputs.append(dict(case='deterministic',method=method,price=r.price,status=r.status))
        rare=AsianOptionSpec(100,1e20,.05,.2,'call',(.1,.25,.5))
        try:
            r=price(rare,n_paths=64,method=method,rng=np.random.default_rng(23))
            assert r.status=='sampled' and 'zero_observed_variance' in r.diagnostics
            outputs.append(dict(case='rare_payoff',method=method,price=r.price,status=r.status,diagnostics=r.diagnostics))
        except FloatingPointError as exc:
            assert method=='control'
            outputs.append(dict(case='rare_payoff',method=method,status='explicit_numerical_limit',diagnostic=str(exc)))
    return outputs


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('run',type=Path);parser.add_argument('proof',type=Path)
    args=parser.parse_args();result=audit(args.run);result['additional_validation']=extra_cases()
    args.proof.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['maximum_absolute_differences','additional_validation']},indent=2))
