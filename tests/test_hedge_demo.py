"""Actual hedge demo CLI and saved accounting evidence, including source recovery."""

import csv
from dataclasses import asdict
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


CONFIG = '''[option]
spot=100.0
strike=100.0
maturity_years=1.0
risk_free_rate=0.05
volatility=0.20
kind="call"
dividend_yield=0.0
[hedging]
position="short_call"
quantity=1.0
rebalance_every_steps=1
one_way_cost_bps=5.0
liquidate_stock_at_expiry=true
[path]
times=[0.0,0.25,0.5,0.75,1.0]
spots=[100.0,108.0,96.0,112.0,105.0]
'''


def run(tmp_path, config=CONFIG, name='out'):
    source = tmp_path/(name+'.toml')
    source.write_text(config)
    return importlib.import_module('option_hedging.experiments.hedge_demo').run_demo(source, tmp_path/name)


def csv_rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def test_saved_ledger_matches_actual_core_and_balances_without_hidden_cash(tmp_path):
    out = run(tmp_path)
    from option_hedging.contracts import OptionSpec
    from option_hedging.hedging.ledger import hedge_path
    from option_hedging.experiments.verify_run import verify_run
    result = hedge_path(OptionSpec(100,100,1,.05,.2,'call'), times=[0,.25,.5,.75,1],
                        spots=[100,108,96,112,105], rebalance_every_steps=1, one_way_cost_bps=5.)
    rows = csv_rows(out/'ledger.csv')
    assert len(rows) == 5
    for row, actual in zip(rows, result.ledger):
        for key,value in asdict(actual).items():
            if value is None:
                assert row[key] == ''
            elif isinstance(value,str):
                assert row[key] == value
            else:
                assert float(row[key]) == pytest.approx(value)
    assert len(csv_rows(out/'unhedged_ledger.csv')) == 5
    assert len(csv_rows(out/'path.csv')) == 5
    checks = csv_rows(out/'accounting_checks.csv')
    assert len(checks) == 10
    assert max(abs(float(r['cash_residual'])) for r in checks) < 1e-10
    summary = json.loads((out/'summary.json').read_text())
    assert summary['checks']['passed'] is True
    assert summary['hedged']['terminal_pnl'] == pytest.approx(result.terminal_pnl)
    assert summary['zero_cost_terminal_pnl']-summary['hedged']['terminal_pnl'] == pytest.approx(result.terminal_value_costs)
    assert (out/'ledger.png').stat().st_size > 10000
    assert verify_run(out)['source_recoverable'] is True


def test_real_cli_and_verifier_use_same_source_checkout(tmp_path):
    source = tmp_path/'config.toml'
    source.write_text(CONFIG)
    out = tmp_path/'cli'
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    result = subprocess.run([sys.executable,'-W','error','-m','option_hedging.experiments.hedge_demo',
                             '--config',str(source),'--output-dir',str(out)], env=env, capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
    verify = subprocess.run([sys.executable,'-m','option_hedging.experiments.verify_run',str(out)],
                            env=env,capture_output=True,text=True)
    assert verify.returncode == 0, verify.stderr
    assert json.loads(verify.stdout)['source_recoverable'] is True


def test_numerical_artifacts_repeat_exactly(tmp_path):
    first,second = run(tmp_path,name='one'),run(tmp_path,name='two')
    for name in ('path.csv','ledger.csv','unhedged_ledger.csv','accounting_checks.csv','summary.json'):
        assert (first/name).read_bytes() == (second/name).read_bytes()


@pytest.mark.parametrize('old,new', [
    ('dividend_yield=0.0','dividend_yield=0.01'), ('quantity=1.0','quantity=2.0'),
    ('quantity=1.0','quantity=true'), ('position="short_call"','position="long_call"'),
    ('liquidate_stock_at_expiry=true','liquidate_stock_at_expiry=false'),
    ('rebalance_every_steps=1','rebalance_every_steps=true'),
    ('one_way_cost_bps=5.0','one_way_cost_bps=-1.0'), ('kind="call"','kind="put"'),
    ('times=[0.0,0.25,0.5,0.75,1.0]','times=[0.0,0.25,0.5,0.75,0.99]'),
    ('spots=[100.0,108.0,96.0,112.0,105.0]','spots=[100.0,true,96.0,112.0,105.0]'),
    ('[path]','[path]\nunknown=1'),
])
def test_unsupported_or_invalid_config_leaves_no_output(tmp_path, old, new):
    with pytest.raises((TypeError,ValueError)):
        run(tmp_path,CONFIG.replace(old,new))
    assert not (tmp_path/'out').exists()


def test_existing_output_is_preserved(tmp_path):
    out = tmp_path/'out'
    out.mkdir()
    (out/'keep').write_text('unchanged')
    with pytest.raises(FileExistsError):
        run(tmp_path)
    assert (out/'keep').read_text() == 'unchanged'
    assert len(list(out.iterdir())) == 1
