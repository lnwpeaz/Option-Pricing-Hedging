"""A real paired-study runner retains all scenarios, shared paths and uncertainty."""
import csv
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest


CONFIG='''[market]
spot=100.0
strike=100.0
maturity_years=1.0
risk_free_rate=0.05
physical_drift=0.08
true_volatility=0.20
dividend_yield=0.0
[simulation]
paths=64
steps_per_year=12
seed=20261023
batch_size=32
scalar_validation_paths=2
[hedge_grid]
rebalance_every_steps=[1,5]
one_way_cost_bps=[0.0,5.0,10.0]
hedge_volatility=[0.15,0.20,0.25]
reference_volatility=0.20
[uncertainty]
bootstrap_repeats=32
bootstrap_batch_size=8
seed=20261024
'''


def run(tmp_path,text=CONFIG,name='out'):
    config=tmp_path/(name+'.toml')
    config.write_text(text)
    return importlib.import_module('option_hedging.experiments.runner').run_study(config,tmp_path/name)


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def test_complete_grid_paths_premium_decomposition_and_source_integrity(tmp_path):
    out=run(tmp_path)
    from option_hedging.experiments.verify_run import verify_run
    cases=rows(out/'scenarios.csv')
    raw=rows(out/'path_results.csv')
    metrics=rows(out/'metrics.csv')
    pairs=rows(out/'paired_comparisons.csv')
    assert len(cases)==21 and len(raw)==21*64 and len(metrics)==42 and len(pairs)==102
    assert np.load(out/'paths.npy',allow_pickle=False).shape==(64,13)
    assert np.load(out/'bootstrap_statistics.npy',allow_pickle=False).shape==(32,42,6)
    assert len(rows(out/'ledger.csv'))==13
    checks=rows(out/'scalar_checks.csv')
    assert len(checks)==21*2
    assert max(float(r['max_money_difference']) for r in checks)<1e-8
    by_case={r['scenario_id']:r for r in cases}
    for r in raw:
        assert float(r['common_premium_pnl'])==pytest.approx(float(r['terminal_pnl'])+float(by_case[r['scenario_id']]['premium_shift']))
    for sid in by_case:
        assert [int(r['path_id']) for r in raw if r['scenario_id']==sid]==list(range(64))
    for m in metrics:
        data=[float(r['terminal_pnl'] if m['premium_basis']=='model' else r['common_premium_pnl']) for r in raw if r['scenario_id']==m['scenario_id']]
        assert float(m['rmse'])==pytest.approx(np.sqrt(np.mean(np.square(data))))
    summary=json.loads((out/'summary.json').read_text())
    assert summary['scalar_validation_passed'] is True
    assert summary['path_result_rows']==1344
    assert verify_run(out)['source_recoverable'] is True
    for filename in ('risk_and_cost.png','volatility_and_premium.png'):
        assert (out/filename).stat().st_size>10000


def test_actual_cli_runs_and_rejects_overwrite(tmp_path):
    config=tmp_path/'config.toml';config.write_text(CONFIG)
    output=tmp_path/'cli'
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    command=[sys.executable,'-W','error','-m','option_hedging.experiments.runner','--config',str(config),'--output-dir',str(output)]
    completed=subprocess.run(command,env=env,capture_output=True,text=True)
    assert completed.returncode==0,completed.stderr
    old=(output/'path_results.csv').read_bytes()
    again=subprocess.run(command,env=env,capture_output=True,text=True)
    assert again.returncode!=0
    assert (output/'path_results.csv').read_bytes()==old


def test_fixed_environment_reproduces_all_numerical_artifacts(tmp_path):
    first,second=run(tmp_path,name='one'),run(tmp_path,name='two')
    for filename in ('scenarios.csv','path_results.csv','metrics.csv','paired_comparisons.csv','scalar_checks.csv','summary.json','ledger.csv'):
        assert (first/filename).read_bytes()==(second/filename).read_bytes()
    for filename in ('paths.npy','times.npy','bootstrap_statistics.npy'):
        np.testing.assert_array_equal(np.load(first/filename),np.load(second/filename))


@pytest.mark.parametrize('old,new',[
    ('dividend_yield=0.0','dividend_yield=0.01'),('paths=64','paths=true'),
    ('paths=64','paths=1'),('seed=20261023','seed=-1'),
    ('scalar_validation_paths=2','scalar_validation_paths=65'),
    ('rebalance_every_steps=[1,5]','rebalance_every_steps=[1,1]'),
    ('one_way_cost_bps=[0.0,5.0,10.0]','one_way_cost_bps=[5.0,10.0]'),
    ('hedge_volatility=[0.15,0.20,0.25]','hedge_volatility=[0.0,0.20,0.25]'),
    ('reference_volatility=0.20','reference_volatility=0.3'),
    ('[market]','[market]\nunknown=1'),
])
def test_invalid_config_creates_no_output(tmp_path,old,new):
    with pytest.raises((TypeError,ValueError)):
        run(tmp_path,CONFIG.replace(old,new))
    assert not (tmp_path/'out').exists()
