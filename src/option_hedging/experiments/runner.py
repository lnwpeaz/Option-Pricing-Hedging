"""Predeclared paired physical-GBM short-call study; no market-order integration."""

import argparse
import csv
from dataclasses import asdict,replace
from datetime import datetime,timezone
import hashlib
from importlib.metadata import version
from itertools import product
import json
import math
from pathlib import Path
import platform
from time import perf_counter
import tomllib

import matplotlib.pyplot as plt
import numpy as np

from option_hedging.analysis.hedge_report import make_report
from option_hedging.analysis.metrics import BOOTSTRAP_FIELDS,summarize_study
from option_hedging.analysis.plots import make_figures
from option_hedging.contracts import OptionSpec
from option_hedging.experiments.provenance import finalize_manifest
from option_hedging.hedging.batch import hedge_paths,unhedged_paths
from option_hedging.hedging.ledger import hedge_path,unhedged_path
from option_hedging.pricing.black_scholes import price
from option_hedging.simulation.gbm import simulate_paths
from option_hedging.simulation.time_grid import make_time_grid


META=('scenario_id','strategy','hedge_volatility','rebalance_every_steps','one_way_cost_bps',
      'initial_premium','reference_premium','premium_shift')
ARRAYS=('terminal_pnl','nominal_costs','financed_costs','turnover','traded_notional','max_cash_borrowing')


def _integer(name,value,minimum):
    if isinstance(value,bool) or not isinstance(value,int):
        raise TypeError(f'{name} must be integer')
    if value<minimum:
        raise ValueError(f'{name} must be at least{minimum}')


def _real(name,value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be finite real')


def _grid(name,values,integer=False):
    if not isinstance(values,list) or not values:
        raise ValueError(f'{name} must be nonempty list')
    for value in values:
        if integer:
            _integer(name,value,1)
        else:
            _real(name,value)
    if any(a>=b for a,b in zip(values,values[1:])):
        raise ValueError(f'{name} must be strictly increasing')


def _load(raw):
    config=tomllib.loads(raw.decode('utf-8'))
    expected={'market':{'spot','strike','maturity_years','risk_free_rate','physical_drift','true_volatility','dividend_yield'},
              'simulation':{'paths','steps_per_year','seed','batch_size','scalar_validation_paths'},
              'hedge_grid':{'rebalance_every_steps','one_way_cost_bps','hedge_volatility','reference_volatility'},
              'uncertainty':{'bootstrap_repeats','bootstrap_batch_size','seed'}}
    if set(config)!=set(expected):
        raise ValueError('Expected exactly market/simulation/hedge_grid/uncertainty sections')
    for section,keys in expected.items():
        if not isinstance(config[section],dict) or set(config[section])!=keys:
            raise ValueError(f'Unexpected/missing keys in {section}')
    market,sim,grid,uncertainty=(config[k] for k in expected)
    for key,value in market.items():
        _real('market.'+key,value)
    if market['dividend_yield']!=0:
        raise ValueError('Only dividend_yield=0 supported')
    spec=OptionSpec(market['spot'],market['strike'],market['maturity_years'],market['risk_free_rate'],market['true_volatility'],'call')
    if spec.maturity_years<=0:
        raise ValueError('Study requires positive maturity')
    for key,minimum in (('paths',2),('steps_per_year',1),('seed',0),('batch_size',1),('scalar_validation_paths',1)):
        _integer('simulation.'+key,sim[key],minimum)
    if sim['scalar_validation_paths']>sim['paths']:
        raise ValueError('scalar_validation_paths cannot exceed paths')
    _grid('rebalance_every_steps',grid['rebalance_every_steps'],True)
    _grid('one_way_cost_bps',grid['one_way_cost_bps'])
    _grid('hedge_volatility',grid['hedge_volatility'])
    _real('reference_volatility',grid['reference_volatility'])
    if grid['one_way_cost_bps'][0]!=0 or grid['hedge_volatility'][0]<=0:
        raise ValueError('Costs must start at0; hedge volatilities must be positive')
    if grid['reference_volatility'] not in grid['hedge_volatility']:
        raise ValueError('reference_volatility must occur in hedge_volatility grid')
    for key,minimum in (('bootstrap_repeats',16),('bootstrap_batch_size',1),('seed',0)):
        _integer('uncertainty.'+key,uncertainty[key],minimum)
    return config,market,sim,grid,uncertainty,spec


def _calculate(spec,paths,times,grid):
    reference=price(replace(spec,volatility=grid['reference_volatility']))
    cases=[]
    for sigma,freq,cost in product(grid['hedge_volatility'],grid['rebalance_every_steps'],grid['one_way_cost_bps']):
        result=hedge_paths(replace(spec,volatility=sigma),times=times,paths=paths,rebalance_every_steps=freq,one_way_cost_bps=cost)
        cases.append(dict(scenario_id=len(cases),strategy='delta_hedged',hedge_volatility=sigma,
                          rebalance_every_steps=freq,one_way_cost_bps=cost,initial_premium=result.initial_premium,
                          reference_premium=reference,premium_shift=(reference-result.initial_premium)*math.exp(spec.risk_free_rate*spec.maturity_years),
                          **{key:getattr(result,key) for key in ARRAYS}))
    for sigma in grid['hedge_volatility']:
        result=unhedged_paths(replace(spec,volatility=sigma),times=times,paths=paths)
        cases.append(dict(scenario_id=len(cases),strategy='unhedged',hedge_volatility=sigma,
                          rebalance_every_steps=0,one_way_cost_bps=0.,initial_premium=result.initial_premium,
                          reference_premium=reference,premium_shift=(reference-result.initial_premium)*math.exp(spec.risk_free_rate*spec.maturity_years),
                          **{key:getattr(result,key) for key in ARRAYS}))
    return cases


def _comparisons(cases,grid):
    lookup={(c['hedge_volatility'],c['rebalance_every_steps'],c['one_way_cost_bps']):c['scenario_id'] for c in cases if c['strategy']=='delta_hedged'}
    unhedged={c['hedge_volatility']:c['scenario_id'] for c in cases if c['strategy']=='unhedged'}
    pairs=[]
    def add(kind,left,right):
        pairs.append(dict(comparison_id=len(pairs),kind=kind,left=left,right=right))
    freqs,costs,sigmas=(grid[k] for k in ('rebalance_every_steps','one_way_cost_bps','hedge_volatility'))
    for sigma,cost,freq in product(sigmas,costs,freqs[1:]):
        add('frequency',lookup[sigma,freqs[0],cost],lookup[sigma,freq,cost])
    for sigma,freq,cost in product(sigmas,freqs,costs[1:]):
        add('cost',lookup[sigma,freq,cost],lookup[sigma,freq,0.])
    for sigma,freq,cost in product(sigmas,freqs,costs):
        if sigma!=grid['reference_volatility']:
            add('volatility',lookup[sigma,freq,cost],lookup[grid['reference_volatility'],freq,cost])
    for (sigma,freq,cost),case_id in lookup.items():
        add('hedged_vs_unhedged',case_id,unhedged[sigma])
    return pairs


def _validate_scalar(cases,spec,paths,times,n):
    rows=[]
    for case in cases:
        model=replace(spec,volatility=case['hedge_volatility'])
        for path_id in range(n):
            args=dict(times=times,spots=paths[path_id])
            scalar=(hedge_path(model,**args,rebalance_every_steps=case['rebalance_every_steps'],one_way_cost_bps=case['one_way_cost_bps'])
                    if case['strategy']=='delta_hedged' else unhedged_path(model,**args))
            funding=max(0.,max(-r.cash_before for r in scalar.ledger),max(-r.cash_after for r in scalar.ledger))
            expected=(scalar.terminal_pnl,scalar.total_nominal_cost,scalar.terminal_value_costs,
                      scalar.stock_turnover,scalar.traded_notional,funding)
            differences={key:abs(float(case[key][path_id])-value) for key,value in zip(ARRAYS,expected)}
            money=max(value for key,value in differences.items() if key!='turnover')
            rows.append(dict(scenario_id=case['scenario_id'],path_id=path_id,max_money_difference=money,
                             max_share_difference=differences['turnover'],**{k+'_difference':v for k,v in differences.items()}))
    return rows


def _csv(path,rows):
    iterator=iter(rows)
    first=next(iterator)
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(first))
        writer.writeheader();writer.writerow(first);writer.writerows(iterator)


def _path_rows(cases):
    for case in cases:
        for path_id in range(len(case['terminal_pnl'])):
            yield dict(scenario_id=case['scenario_id'],path_id=path_id,
                       **{key:float(case[key][path_id]) for key in ARRAYS},
                       common_premium_pnl=float(case['terminal_pnl'][path_id]+case['premium_shift']))


def run_study(config_path: Path,output_dir: Path) -> Path:
    if output_dir.exists():
        raise FileExistsError(f'Output directory already exists: {output_dir}')
    raw=config_path.read_bytes()
    config,market,sim,grid,uncertainty,spec=_load(raw)
    times=make_time_grid(maturity_years=spec.maturity_years,steps_per_year=sim['steps_per_year'])
    rng=np.random.Generator(np.random.PCG64(np.random.SeedSequence([5,0,sim['seed']])))
    started=perf_counter()
    paths=simulate_paths(spot=spec.spot,drift=market['physical_drift'],volatility=market['true_volatility'],
                         times=times,n_paths=sim['paths'],rng=rng,batch_size=sim['batch_size'])
    performance={'simulation_seconds':perf_counter()-started}
    started=perf_counter();cases=_calculate(spec,paths,times,grid)
    performance['batch_hedging_seconds']=perf_counter()-started
    started=perf_counter();checks=_validate_scalar(cases,spec,paths,times,sim['scalar_validation_paths'])
    performance['scalar_validation_seconds']=perf_counter()-started
    started=perf_counter()
    metrics,paired,bootstrap,labels=summarize_study(cases,_comparisons(cases,grid),bootstrap_repeats=uncertainty['bootstrap_repeats'],
                                                  seed=uncertainty['seed'],batch_size=uncertainty['bootstrap_batch_size'])
    performance['statistics_bootstrap_seconds']=perf_counter()-started
    representative=next(c for c in cases if c['strategy']=='delta_hedged' and c['hedge_volatility']==grid['reference_volatility']
                        and c['rebalance_every_steps']==grid['rebalance_every_steps'][0]
                        and c['one_way_cost_bps']==grid['one_way_cost_bps'][len(grid['one_way_cost_bps'])//2])
    ledger=hedge_path(replace(spec,volatility=representative['hedge_volatility']),times=times,spots=paths[0],
                      rebalance_every_steps=representative['rebalance_every_steps'],one_way_cost_bps=representative['one_way_cost_bps'])
    max_money=max(r['max_money_difference'] for r in checks)
    max_shares=max(r['max_share_difference'] for r in checks)
    summary=dict(scenario_count=len(cases),paths=sim['paths'],intervals=len(times)-1,path_result_rows=len(cases)*len(paths),
                 metric_cells=len(metrics),paired_comparison_rows=len(paired),bootstrap_repeats=uncertainty['bootstrap_repeats'],
                 scalar_validation_rows=len(checks),max_scalar_money_difference=max_money,max_scalar_share_difference=max_shares,
                 scalar_validation_passed=max_money<=1e-10*spec.spot and max_shares<=1e-10,
                 scalar_money_tolerance=1e-10*spec.spot,scalar_share_tolerance=1e-10,
                 representative_path_id=0,representative_scenario_id=representative['scenario_id'])
    serialized=json.dumps(summary,indent=2,allow_nan=False)+'\n'
    report=make_report(market,sim,grid,uncertainty,summary,cases,metrics,paired)
    figures=make_figures(cases,metrics,reference_volatility=grid['reference_volatility'],costs=grid['one_way_cost_bps'],frequencies=grid['rebalance_every_steps'])
    try:
        output_dir.mkdir(parents=True,exist_ok=False)
        for filename,array in (('paths.npy',paths),('times.npy',times),('bootstrap_statistics.npy',bootstrap)):
            np.save(output_dir/filename,array,allow_pickle=False)
        _csv(output_dir/'scenarios.csv',({key:c[key] for key in META} for c in cases))
        _csv(output_dir/'path_results.csv',_path_rows(cases))
        _csv(output_dir/'metrics.csv',metrics)
        _csv(output_dir/'paired_comparisons.csv',paired)
        _csv(output_dir/'scalar_checks.csv',checks)
        _csv(output_dir/'ledger.csv',(asdict(row) for row in ledger.ledger))
        (output_dir/'summary.json').write_text(serialized,encoding='utf-8')
        (output_dir/'performance.json').write_text(json.dumps(performance,indent=2,allow_nan=False)+'\n')
        (output_dir/'effective_config.json').write_text(json.dumps(config,indent=2,allow_nan=False)+'\n')
        (output_dir/'bootstrap_fields.json').write_text(json.dumps(dict(statistics=BOOTSTRAP_FIELDS,cells=labels),indent=2)+'\n')
        (output_dir/'input_config.toml').write_bytes(raw)
        (output_dir/'RESULTS.md').write_text(report,encoding='utf-8')
        for name,figure in figures.items():
            figure.savefig(output_dir/name,dpi=160)
        source=Path(__file__).resolve().parents[1]
        manifest=dict(experiment='paired_hedge_study',created_utc=datetime.now(timezone.utc).isoformat(),
                      config_sha256=hashlib.sha256(raw).hexdigest(),
                      rng=dict(bit_generator='PCG64',path_key=[5,0,sim['seed']],bootstrap_key=[50,uncertainty['seed']]),
                      source_hashes={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(source.rglob('*.py'))},
                      versions={'python':platform.python_version(),**{p:version(p) for p in ('numpy','scipy','matplotlib')}},
                      environment={'platform':platform.platform(),'machine':platform.machine()})
        finalize_manifest(output_dir,manifest,config_bytes=raw,entrypoint='option_hedging.experiments.runner')
    finally:
        for figure in figures.values():
            plt.close(figure)
    return output_dir


def run(config_path: Path,output_root: Path) -> Path:
    return run_study(config_path,output_root/datetime.now(timezone.utc).strftime('hedge-study-%Y%m%dT%H%M%S%fZ'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('configs/hedge_study.toml'))
    parser.add_argument('--output-dir',type=Path)
    args=parser.parse_args()
    try:
        output=run_study(args.config,args.output_dir) if args.output_dir else run(args.config,Path('reports/runs'))
    except (ValueError,TypeError,OSError,KeyError,OverflowError,FloatingPointError) as error:
        parser.error(str(error))
    print(f'Paired hedge study saved to {output.resolve()}')
    if not json.loads((output/'summary.json').read_text())['scalar_validation_passed']:
        parser.exit(1,'Scalar/vector accounting validation failed; inspect saved evidence.\n')


if __name__=='__main__':
    main()
