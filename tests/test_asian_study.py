"""Real runner/CLI, reproducibility, failure retention and source integrity."""
import csv,json,os,subprocess,sys
from pathlib import Path
import pytest
from option_hedging.experiments.asian_study import run_study,load_config
from option_hedging.experiments.verify_run import verify_run

METHODS=['plain','antithetic','control','sobol','sobol_bridge']


def read_csv(path):
    with path.open(newline='') as stream:return list(csv.DictReader(stream))


def write_config(tmp_path):
    text='''[option]
spot=100.0
risk_free_rate=0.05
volatility=0.20
kind="call"
averaging="arithmetic"
dividend_yield=0.0
[study]
mode="study"
base_date="2026-10-24"
fixing_counts=[2]
strikes=[100.0]
production_paths=[64,256]
methods=["plain","antithetic","control","sobol","sobol_bridge"]
repeats=4
scrambles=4
seed=123
batch_size=32
pilot_paths=16
sobol_bits=52
bootstrap_repeats=64
[reference]
external_enabled=false
quantlib_version="1.44"
precision_target=0.0005
[benchmark]
enabled=false
paths=256
fixing_count=2
strike=100.0
batch_sizes=[16,32]
repeats=3
seed=124
'''
    p=tmp_path/'small.toml';p.write_text(text);return p


def test_small_study_all_cells_scrambles_internal_reference_and_replay(tmp_path):
    cfg=write_config(tmp_path);raw=cfg.read_bytes()
    out=run_study(cfg,tmp_path/'one');other=run_study(cfg,tmp_path/'two')
    assert len(read_csv(out/'estimates.csv'))==40
    assert len(read_csv(out/'scramble_estimates.csv'))==64
    assert verify_run(out)['source_recoverable'] is True
    assert (out/'input_config.toml').read_bytes()==raw
    for name in ['estimates.csv','scramble_estimates.csv','reference_checks.csv','reference_summary.csv',
                 'metrics.csv','paired_comparisons.csv','summary.json','effective_config.json']:
        assert (out/name).read_bytes()==(other/name).read_bytes(),name
    summary=json.loads((out/'summary.json').read_text())
    assert summary['requested_estimates']==40 and summary['completed_estimates']==40 and summary['failed_estimates']==0
    checks=read_csv(out/'reference_checks.csv')
    assert any(r['engine']=='two_fixing_integral' for r in checks)
    assert any(r['status']=='not_requested' and r['source']=='quantlib' for r in checks)
    assert all((out/name).is_file() for name in ['accuracy.png','calibration.png','efficiency.png','reference_precision.png','RESULTS.md','benchmark.csv','allocations.csv'])
    before=(out/'manifest.json').read_bytes()
    with pytest.raises(FileExistsError):run_study(cfg,out)
    assert (out/'manifest.json').read_bytes()==before


def test_actual_cli_and_bad_config_rejected_before_manifest(tmp_path):
    cfg=write_config(tmp_path);out=tmp_path/'cli'
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[1]/'src'))
    proc=subprocess.run([sys.executable,'-W','error','-m','option_hedging.experiments.asian_study',
        '--config',str(cfg),'--output-dir',str(out)],env=env,capture_output=True,text=True)
    assert proc.returncode==0,proc.stderr
    assert verify_run(out)['artifact_integrity']
    cfg.write_text(cfg.read_text().replace('dividend_yield=0.0','dividend_yield=0.01'))
    with pytest.raises(ValueError):run_study(cfg,tmp_path/'bad')
    assert not (tmp_path/'bad/manifest.json').exists()


@pytest.mark.parametrize('old,new',[('seed=123','seed=true'),('batch_size=32','batch_size=1'),
 ('fixing_counts=[2]','fixing_counts=[366]'),('sobol_bits=52','sobol_bits=53'),
 ('external_enabled=false','external_enabled=1'),('strike=100.0','unknown=100.0'),
 ('strikes=[100.0]','strikes=[100.0,100.0]'),('scrambles=4','scrambles=3')])
def test_strict_schema_rejects_unknown_or_invalid_types(tmp_path,old,new):
    p=write_config(tmp_path);p.write_text(p.read_text().replace(old,new))
    with pytest.raises((ValueError,TypeError)):load_config(p)


def test_numerical_failure_recorded_without_pruning_other_methods(tmp_path):
    p=write_config(tmp_path);p.write_text(p.read_text().replace('strikes=[100.0]','strikes=[1e300]'))
    out=run_study(p,tmp_path/'failure')
    rows=read_csv(out/'estimates.csv')
    assert len(rows)==40
    bad=[r for r in rows if r['status']=='failed']
    assert len(bad)==8 and all(r['method']=='control' and r['error'] for r in bad)
    assert json.loads((out/'summary.json').read_text())['failed_estimates']==8


def test_custom_schedule_external_unavailable_keeps_prices(tmp_path):
    p=write_config(tmp_path);text=p.read_text().replace('mode="study"','mode="custom"').replace('fixing_counts=[2]','fixing_times=[0.1,0.25,0.5]').replace('external_enabled=false','external_enabled=true')
    p.write_text(text);out=run_study(p,tmp_path/'custom')
    assert len(read_csv(out/'estimates.csv'))==40
    ref=read_csv(out/'reference_summary.csv')[0]
    assert ref['status']=='unavailable'
    assert json.loads((out/'summary.json').read_text())['completed_estimates']==40


def test_all_requested_estimators_fail_still_produces_complete_failure_record(tmp_path):
    p=write_config(tmp_path);p.write_text(p.read_text().replace('strikes=[100.0]','strikes=[1e300]').replace(
        'methods=["plain","antithetic","control","sobol","sobol_bridge"]','methods=["control"]'))
    out=run_study(p,tmp_path/'all-failed')
    assert json.loads((out/'summary.json').read_text())['failed_estimates']==8
    assert len(read_csv(out/'estimates.csv'))==8
    assert read_csv(out/'scramble_estimates.csv')==[]
    assert read_csv(out/'paired_comparisons.csv')==[]
    assert verify_run(out)['source_recoverable']


def test_real_benchmark_records_all_repetitions_and_separate_allocations(tmp_path):
    p=write_config(tmp_path);p.write_text(p.read_text().replace('enabled=false\npaths=','enabled=true\npaths='))
    out=run_study(p,tmp_path/'benchmark')
    bench=read_csv(out/'benchmark.csv');alloc=read_csv(out/'allocations.csv')
    assert len(bench)==30 and len(alloc)==10
    assert all(r['status']=='completed' and float(r['elapsed_seconds'])>0 for r in bench)
    assert all(r['status']=='completed' and int(r['peak_traced_bytes'])>0 for r in alloc)
    first=[r['method'] for r in bench if r['batch_size']=='16' and r['repeat']=='0']
    second=[r['method'] for r in bench if r['batch_size']=='16' and r['repeat']=='1']
    assert first==list(reversed(second))


def test_failed_benchmark_warmup_retains_failed_repetitions(tmp_path):
    p=write_config(tmp_path);text=p.read_text().replace('strikes=[100.0]','strikes=[1e300]').replace(
        'strike=100.0','strike=1e300').replace('enabled=false\npaths=','enabled=true\npaths=').replace(
        'methods=["plain","antithetic","control","sobol","sobol_bridge"]','methods=["plain","control"]')
    p.write_text(text);out=run_study(p,tmp_path/'bad-benchmark')
    bench=read_csv(out/'benchmark.csv');alloc=read_csv(out/'allocations.csv')
    assert len(bench)==12 and len(alloc)==4
    assert sum(r['status']=='failed' for r in bench)==6
    assert sum(r['status']=='failed' for r in alloc)==2
    assert verify_run(out)['source_recoverable']


def test_time_rmse_diagnostic_requires_identical_full_fixing_contract(tmp_path):
    p=write_config(tmp_path);text=p.read_text().replace('mode="study"','mode="custom"').replace(
        'fixing_counts=[2]','fixing_times=[0.2,0.4986301369863014]').replace('enabled=false\npaths=','enabled=true\npaths=')
    p.write_text(text);out=run_study(p,tmp_path/'different-schedule')
    bench=read_csv(out/'benchmark.csv')
    assert len(bench)==30
    assert all(r['point_reference_rmse_squared_times_seconds']=='' for r in bench)
    assert all(r['precision_ranking_eligible']=='False' for r in bench)


def test_all_failed_benchmark_and_allocations_render_without_warning(tmp_path):
    import pandas as pd
    from option_hedging.analysis.asian_plots import create_figures
    metrics=pd.DataFrame([dict(contract_id='c000',n_paths=64,method='control',rmse=.1,
        bootstrap_rmse_low=.08,bootstrap_rmse_high=.12,possible_coverage=1.,definite_coverage=0.)])
    refs=pd.DataFrame([dict(contract_id='c000',fixing_count=2,strike=100.,precision_radius=.001,status='low_precision')])
    bench=pd.DataFrame([dict(method='control',batch_size=32,elapsed_seconds=0.,status='failed')])
    alloc=pd.DataFrame([dict(method='control',batch_size=32,peak_traced_bytes=None,status='failed')])
    create_figures(tmp_path,metrics,refs,bench,alloc)
    assert (tmp_path/'efficiency.png').is_file()
