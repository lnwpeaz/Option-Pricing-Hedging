"""Reproducible discrete Asian research and custom-contract pricing CLI."""
import argparse
from dataclasses import asdict
from datetime import date
import csv
import hashlib
import json
import math
from pathlib import Path
from time import perf_counter
import tomllib
import numpy as np
import pandas as pd
from option_hedging.asian_contracts import AsianOptionSpec,AsianEstimate,finite_real,validate_times
from option_hedging.pricing.asian_monte_carlo import price,integer,METHODS
from option_hedging.pricing.asian_reference import geometric_price,deterministic_price
from option_hedging.validation.asian_reference import integrate_geometric,integrate_two_fixing
from option_hedging.validation.asian_quantlib import external_checks,assess_reference,ReferenceResult
from option_hedging.analysis.asian_metrics import summarize
from option_hedging.experiments.asian_benchmarks import benchmark
from option_hedging.experiments.provenance import finalize_manifest

STREAM_IDS={'plain':0,'antithetic':1,'control':2,'sobol':3,'sobol_bridge':3}
CHECK_COLUMNS=['contract_id','source','engine','level','price','error_estimate','tail_bound','status','diagnostic']
REF_COLUMNS=['contract_id','fixing_count','strike','price','precision_radius','precision_kind','status','diagnostics','is_exact']
SCRAMBLE_COLUMNS=['estimate_id','contract_id','n_paths','macro_repeat','method','scramble','price']
PAIR_COLUMNS=['contract_id','n_paths','method_a','method_b','paired_repeats','mean_price_difference','difference_ci_low','difference_ci_high','rmse_ratio','rmse_ratio_ci_low','rmse_ratio_ci_high','rmse_difference','rmse_difference_ci_low','rmse_difference_ci_high','undefined_ratio_bootstraps','rank_eligible']


def _keys(data,expected,label):
    if not isinstance(data,dict) or set(data)!=set(expected):
        raise ValueError(f'{label} keys must be exactly {sorted(expected)}')


def _boolean(value,name):
    if type(value) is not bool:raise TypeError(f'{name} must be boolean')


def _list(data,name,convert):
    value=data[name]
    if not isinstance(value,list) or not value:raise ValueError(f'{name} must be a nonempty list')
    value=[convert(x) for x in value]
    if len(set(value))!=len(value):raise ValueError(f'{name} entries must be unique')
    data[name]=value


def load_config(path):
    config=tomllib.loads(Path(path).read_text())
    _keys(config,['option','study','reference','benchmark'],'config')
    o,s,r,b=(config[k] for k in ('option','study','reference','benchmark'))
    _keys(o,['spot','risk_free_rate','volatility','kind','averaging','dividend_yield'],'option')
    if s.get('mode') not in ('study','custom'):raise ValueError('mode must be study or custom')
    schedule='fixing_counts' if s['mode']=='study' else 'fixing_times'
    _keys(s,['mode','base_date',schedule,'strikes','production_paths','methods','repeats','seed','batch_size',
             'pilot_paths','scrambles','sobol_bits','bootstrap_repeats'],'study')
    _keys(r,['external_enabled','quantlib_version','precision_target'],'reference')
    _keys(b,['enabled','paths','fixing_count','strike','batch_sizes','repeats','seed'],'benchmark')
    for field in ['spot','risk_free_rate','volatility','dividend_yield']:o[field]=finite_real(o[field],field)
    if o['dividend_yield']!=0:raise ValueError('only zero dividends are supported')
    date.fromisoformat(s['base_date'])
    for key,minimum in [('repeats',2),('seed',0),('batch_size',2),('pilot_paths',2),('scrambles',2),('bootstrap_repeats',2)]:
        s[key]=integer(key,s[key],minimum)
    s['sobol_bits']=integer('sobol_bits',s['sobol_bits'],1,52)
    _list(s,'production_paths',lambda x:integer('production_paths',x,2))
    _list(s,'strikes',lambda x:finite_real(x,'strike'))
    _list(s,'methods',lambda x:x if isinstance(x,str) and x in METHODS else (_ for _ in ()).throw(ValueError('unknown method')))
    if s['mode']=='study':_list(s,'fixing_counts',lambda x:integer('fixing_count',x,1,365))
    else:
        s['fixing_times']=list(validate_times(s['fixing_times']))
        if len(s['strikes'])!=1:raise ValueError('custom mode requires exactly one strike')
    _boolean(r['external_enabled'],'external_enabled');_boolean(b['enabled'],'benchmark enabled')
    if r['quantlib_version']!='1.44':raise ValueError('research comparator must pin QuantLib 1.44')
    r['precision_target']=finite_real(r['precision_target'],'precision_target')
    if r['precision_target']<=0:raise ValueError('precision_target must be positive')
    for key,minimum in [('paths',2),('fixing_count',1),('repeats',2),('seed',0)]:b[key]=integer(key,b[key],minimum)
    if b['fixing_count']>365:raise ValueError('benchmark fixing count must be <=365')
    b['strike']=finite_real(b['strike'],'benchmark strike')
    if b['strike']<=0:raise ValueError('benchmark strike must be positive')
    _list(b,'batch_sizes',lambda x:integer('batch_size',x,2))
    # Validate the actual estimator settings without consuming a production RNG.
    for strike in s['strikes']:
        dummy=AsianOptionSpec(o['spot'],strike,o['risk_free_rate'],0.,o['kind'],(1.,),o['averaging'])
        for n in s['production_paths']+([b['paths']] if b['enabled'] else []):
            for method in s['methods']:
                price(dummy,n_paths=n,rng=np.random.default_rng(0),method=method,batch_size=s['batch_size'],
                      pilot_paths=s['pilot_paths'],scrambles=s['scrambles'],bits=s['sobol_bits'])
    AsianOptionSpec(o['spot'],s['strikes'][0],o['risk_free_rate'],o['volatility'],o['kind'],(1.,),o['averaging'])
    return config


def _contracts(config):
    s,o=config['study'],config['option'];result=[]
    if s['mode']=='study':
        schedules=[(m,tuple(((365*j)//m)/365 for j in range(1,m+1))) for m in s['fixing_counts']]
    else:
        times=tuple(s['fixing_times'])
        custom_id=int.from_bytes(hashlib.sha256(json.dumps(times,separators=(',',':')).encode()).digest()[:8],'little')
        schedules=[(custom_id,times)]
    for identity,times in schedules:
        for strike_index,strike in enumerate(s['strikes']):
            spec=AsianOptionSpec(o['spot'],strike,o['risk_free_rate'],o['volatility'],o['kind'],times,o['averaging'])
            result.append((f'c{len(result):03d}',identity,strike_index,spec))
    return result


def _reference(spec,cid,config,timings):
    s,r=config['study'],config['reference'];checks=[];internal=None
    try:
        g=geometric_price(spec);integ=integrate_geometric(spec)
        checks.append(dict(contract_id=cid,source='internal',engine='geometric_formula_vs_integral',price=g,
            error_estimate=integ.error_estimate,tail_bound=integ.tail_bound,
            status='passed' if abs(g-integ.price)<=max(2e-9,4*integ.error_estimate+integ.tail_bound) else 'failed',
            diagnostic=f'integral_price={integ.price:.17g}'))
        if spec.volatility==0:internal=ReferenceResult(deterministic_price(spec),0.,'analytic_model','available')
        elif spec.averaging=='geometric' or len(spec.fixing_times)==1:
            internal=ReferenceResult(g,0.,'analytic_model','available')
    except (ValueError,OverflowError,FloatingPointError) as exc:
        checks.append(dict(contract_id=cid,source='internal',engine='geometric_formula_vs_integral',status='failed',diagnostic=str(exc)))
    if internal is None and len(spec.fixing_times)==2 and spec.averaging=='arithmetic':
        try:
            value=integrate_two_fixing(spec);radius=value.error_estimate+value.tail_bound
            internal=ReferenceResult(value.price,radius,'quadrature_error_estimate_and_tail',
                'available' if radius<=r['precision_target'] else 'low_precision')
            checks.append(dict(contract_id=cid,source='internal',engine='two_fixing_integral',price=value.price,
                error_estimate=value.error_estimate,tail_bound=value.tail_bound,status='completed',diagnostic='QUADPACK error is not a rigorous floating-point bound'))
        except (ValueError,OverflowError,FloatingPointError) as exc:
            checks.append(dict(contract_id=cid,source='internal',engine='two_fixing_integral',status='failed',diagnostic=str(exc)))
    if r['external_enabled']:
        raw=external_checks(spec,base_date=s['base_date'],settings=r)
        for row in raw:
            row=dict(row);timings.append(dict(stage='reference_engine',contract_id=cid,method=row['engine'],elapsed_seconds=row.pop('elapsed_seconds')))
            checks.append(dict(contract_id=cid,source='quantlib',**row))
        external=assess_reference(spec,raw,settings=r)
    else:
        external=ReferenceResult(None,None,'unavailable','unavailable',('external_comparator_not_requested',))
        checks.append(dict(contract_id=cid,source='quantlib',engine='availability',status='not_requested',diagnostic='external_enabled=false'))
    result=internal or external
    row=dict(contract_id=cid,fixing_count=len(spec.fixing_times),strike=spec.strike,**asdict(result),
             is_exact=result.precision_kind=='analytic_model')
    row['diagnostics']=json.dumps(row['diagnostics'],separators=(',',':'))
    return row,checks


def _clean(value):
    if isinstance(value,np.generic):value=value.item()
    if isinstance(value,float):
        if math.isnan(value):return None
        if not math.isfinite(value):raise FloatingPointError('cannot serialize infinite numeric evidence')
    return value


def write_csv(path,rows,columns=None):
    if isinstance(rows,pd.DataFrame):
        columns=list(rows.columns) if len(rows.columns) else columns;rows=rows.to_dict('records')
    if columns is None:columns=list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,extrasaction='raise');writer.writeheader()
        for row in rows:writer.writerow({key:_clean(value) for key,value in row.items()})


def run_study(config_path:Path,output_dir:Path)->Path:
    start=perf_counter();config_path=Path(config_path);output_dir=Path(output_dir)
    raw=config_path.read_bytes();config=load_config(config_path);s=config['study']
    contracts=_contracts(config)
    output_dir.mkdir(parents=True,exist_ok=False)
    (output_dir/'input_config.toml').write_bytes(raw)
    (output_dir/'effective_config.json').write_text(json.dumps(config,indent=2,allow_nan=False)+'\n')
    estimates=[];scrambles=[];references=[];checks=[];timings=[]
    for cid,identity,strike_index,spec in contracts:
        print(f'{cid}: {len(spec.fixing_times)} fixings, K={spec.strike:g}: reference',flush=True)
        ref,raw_checks=_reference(spec,cid,config,timings);references.append(ref);checks.extend(raw_checks)
        for budget in s['production_paths']:
            for repeat in range(s['repeats']):
                for method in s['methods']:
                    identifier=f'{cid}_n{budget}_r{repeat:03d}_{method}'
                    row=dict(estimate_id=identifier,contract_id=cid,fixing_count=len(spec.fixing_times),strike=spec.strike,
                        n_paths=budget,macro_repeat=repeat,method=method)
                    rng=np.random.default_rng(np.random.SeedSequence([80,identity,strike_index,budget,repeat,STREAM_IDS[method],s['seed']]))
                    tick=perf_counter()
                    try:
                        result=price(spec,n_paths=budget,rng=rng,method=method,batch_size=s['batch_size'],
                            pilot_paths=s['pilot_paths'],scrambles=s['scrambles'],bits=s['sobol_bits'])
                        values=asdict(result);prices=values.pop('scramble_prices')
                        values['diagnostics']=json.dumps(values['diagnostics'],separators=(',',':'))
                        row.update(values,error='')
                        for i,value in enumerate(prices):
                            scrambles.append(dict(estimate_id=identifier,contract_id=cid,n_paths=budget,
                                macro_repeat=repeat,method=method,scramble=i,price=value))
                    except (ValueError,FloatingPointError,OverflowError) as exc:
                        row.update(status='failed',error=f'{type(exc).__name__}: {exc}',diagnostics='["work_counts_unavailable_after_failure"]')
                    timings.append(dict(stage='estimator',contract_id=cid,method=method,n_paths=budget,
                        macro_repeat=repeat,elapsed_seconds=perf_counter()-tick))
                    estimates.append(row)
            print(f'{cid}: N={budget}, all {s["repeats"]} repeats retained',flush=True)
    ecols=['estimate_id','contract_id','fixing_count','strike','n_paths','macro_repeat']+[k for k in AsianEstimate.__dataclass_fields__ if k!='scramble_prices']+['error']
    e=pd.DataFrame(estimates).reindex(columns=ecols);refs=pd.DataFrame(references)
    metrics,paired=summarize(e,refs,bootstrap_repeats=s['bootstrap_repeats'],seed=s['seed'])
    bench,alloc=benchmark(config)
    # Timing-derived diagnostic is kept with benchmark observations, never in
    # the numerical-only metrics table.
    b=config['benchmark'];o=config['option'];m=b['fixing_count']
    benchmark_spec=AsianOptionSpec(o['spot'],b['strike'],o['risk_free_rate'],o['volatility'],o['kind'],
        tuple(((365*j)//m)/365 for j in range(1,m+1)),o['averaging'])
    matching_contracts=[cid for cid,_,_,spec in contracts if spec==benchmark_spec]
    for row in bench:
        match=refs[refs.contract_id.isin(matching_contracts)]
        found=metrics[(metrics.contract_id.isin(match.contract_id)) &
                      (metrics.n_paths==config['benchmark']['paths']) & (metrics.method==row['method'])]
        row['point_reference_rmse_squared_times_seconds']=None
        row['precision_ranking_eligible']=False
        if len(found) and pd.notna(found.iloc[0]['rmse']):
            rmse=float(found.iloc[0]['rmse'])
            product=rmse*rmse*row['elapsed_seconds']
            row['point_reference_rmse_squared_times_seconds']=product if math.isfinite(product) else None
            row['precision_ranking_eligible']=bool(found.iloc[0]['rank_eligible'])
    # Fixed complete schema also covers failed-only runs and empty derived tables.
    write_csv(output_dir/'estimates.csv',e)
    write_csv(output_dir/'scramble_estimates.csv',scrambles,SCRAMBLE_COLUMNS)
    write_csv(output_dir/'reference_checks.csv',[{k:row.get(k) for k in CHECK_COLUMNS} for row in checks],CHECK_COLUMNS)
    write_csv(output_dir/'reference_summary.csv',refs,REF_COLUMNS)
    write_csv(output_dir/'metrics.csv',metrics)
    write_csv(output_dir/'paired_comparisons.csv',paired,PAIR_COLUMNS)
    write_csv(output_dir/'benchmark.csv',bench,list(dict.fromkeys(['method','batch_size','repeat','order_index','elapsed_seconds','status','error']+[k for row in bench for k in row])))
    write_csv(output_dir/'allocations.csv',alloc,['method','batch_size','peak_traced_bytes','status','error'])
    summary=dict(requested_estimates=len(e),completed_estimates=int((e.status!='failed').sum()),failed_estimates=int((e.status=='failed').sum()),
        scramble_rows=len(scrambles),metric_cells=len(metrics),reference_dominated_cells=int(metrics.reference_dominates_error.sum()),
        reference_status_counts={str(k):int(v) for k,v in refs.status.value_counts().items()},
        numerical_acceptance=dict(all_estimates_completed=bool((e.status!='failed').all()),
            all_internal_checks_passed=not any(row['source']=='internal' and row['status']=='failed' for row in checks),
            all_references_available=bool((refs.status=='available').all())),
        uncertainty_note='Approximate normal intervals for pseudo-MC; finite-R Student-t intervals for RQMC. Empirical reference bands are not rigorous bounds.')
    (output_dir/'summary.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    from option_hedging.analysis.asian_plots import create_figures
    from option_hedging.analysis.asian_report import write_report
    create_figures(output_dir,metrics,refs,pd.DataFrame(bench),pd.DataFrame(alloc))
    write_report(output_dir,config,summary,metrics,refs,pd.DataFrame(bench))
    timings.append(dict(stage='total_before_manifest',elapsed_seconds=perf_counter()-start))
    write_csv(output_dir/'stage_timings.csv',timings,['stage','contract_id','method','n_paths','macro_repeat','elapsed_seconds'])
    package=Path(__file__).resolve().parents[1]
    manifest=dict(config_sha256=hashlib.sha256(raw).hexdigest(),study='V2-A Asian MC/RQMC',
        source_hashes={p.relative_to(package).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(package.rglob('*.py'))},
        numerical_acceptance=summary['numerical_acceptance'],requested_estimates=len(e),failed_estimates=summary['failed_estimates'])
    finalize_manifest(output_dir,manifest,config_bytes=raw,entrypoint='option_hedging.experiments.asian_study')
    return output_dir


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args()
    try:out=run_study(args.config,args.output_dir)
    except (OSError,ValueError,TypeError) as exc:parser.error(str(exc))
    print(out)


if __name__=='__main__':main()
