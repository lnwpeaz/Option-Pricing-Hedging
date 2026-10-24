"""Executed findings with measured values and explicit reference limitations."""
import pandas as pd


def _format(x):
    if x is None or (isinstance(x,float) and pd.isna(x)):return '—'
    if isinstance(x,float):return f'{x:.7g}'
    return str(x)


def _table(frame,columns):
    return '| '+' | '.join(columns)+' |\n| '+' | '.join('---' for _ in columns)+' |\n'+''.join(
        '| '+' | '.join(_format(v) for v in row)+' |\n' for row in frame[columns].itertuples(index=False,name=None))


def write_report(out,config,summary,metrics,references,bench):
    s=config['study']
    text='# Executed Asian option Monte Carlo / randomized QMC study\n\n'
    text+=f'Retained **{summary["requested_estimates"]} requested estimates**: {summary["completed_estimates"]} completed, {summary["failed_estimates"]} failed; {summary["scramble_rows"]} raw scramble prices.\n\n'
    text+='European cash-settled discrete average-price options, q=0, constant-rate/volatility risk-neutral GBM, equal weights and no past fixings. Spot is excluded from the average. Changing fixing count changes the contract. Prices are model premiums, not forecasts or executable quotes.\n\n'
    text+='## Reference precision\n\n'+_table(references,['contract_id','fixing_count','strike','price','precision_radius','precision_kind','status'])+'\n'
    text+='Internal geometric/single-fixing analytic cases are checked by independent quadrature. Two-fixing arithmetic quadrature reports QUADPACK and omitted-tail diagnostics. For dated general arithmetic contracts, external QuantLib 1.44 uses three fixed FD grids, Choi levels 5/10/15 and four independent 262,144-path MC-control checks. The finest Choi point is predeclared; the radius is the maximum of twice the final Choi change, twice the final FD change and the finest cross-engine gap. This empirical band is not a rigorous error bound. Unavailable and failed comparisons remain in reference_checks.csv.\n\n'
    text+=f'**{summary["reference_dominated_cells"]} of {summary["metric_cells"]} method/budget cells have reference-dominated error.** Precision-dependent rankings are withheld for these cells; sampling dispersion and computational observations remain usable. A point-reference RMSE can be smaller than the reference uncertainty.\n\n'
    text+='## Largest production budget for each contract\n\n'
    chosen=metrics[metrics.n_paths==max(s['production_paths'])]
    text+=_table(chosen,['contract_id','method','completed_count','rmse','empirical_sd','mean_reported_se','possible_coverage','definite_coverage','rank_eligible'])+'\n'
    text+='All budgets/methods and failed counts are retained in metrics.csv. RMSE/bias are against the declared point and remain approximate when the reference is approximate. Percentile bootstrap uses shared macro-ID resampling; paired_comparisons.csv preserves Sobol/bridge pairing. Conditional RMSE sensitivity [max(0, RMSE-radius), RMSE+radius] assumes the band contains truth; it is not a confidence interval. Possible coverage means the reported CI overlaps the reference band; definite coverage means it contains that entire band. Exact analytic cases additionally have Wilson coverage intervals.\n\n'
    text+='## Computation and uncertainty\n\nPlain/control use N independent production observations; antithetic uses N/2 pair means and N payoff evaluations. Control fits beta on an extra independent pilot, then freezes it. QMC uses R independent scrambles, each with a power-of-two point count; SE is the standard deviation of scramble prices divided by sqrt(R). Approximate Student-t intervals use R-1 degrees of freedom. A zero observed SE is flagged and is not proof of an exact stochastic price; sigma=0 is a separate deterministic status with zero actual work and no RNG consumption. No estimate or CI is clipped.\n\n'
    text+='normal_coordinates counts newly generated normals or inverse-CDF values, excluding antithetic negatives. payoff_evaluations includes target pilot work; control_payoff_evaluations counts extra geometric evaluations. metrics.csv reports RMSE² times production-path and total-payoff work; these counters do not measure total FLOPs. benchmark.csv also reports seconds × point-reference RMSE² where a matching study cell exists. This remains a conditional diagnostic when reference precision is inadequate.\n\n'
    if len(bench):
        good=bench[bench.status=='completed'];med=good.groupby(['method','batch_size'],sort=False).elapsed_seconds.agg(['median','min','max']).reset_index()
        text+=_table(med,['method','batch_size','median','min','max'])+'\n'
        text+='Each method is warmed; forward/reverse order alternates across repetitions. Complete-estimator timing includes RNG through CI construction. allocations.csv is a separate untimed tracemalloc pass, not process RSS. Sobol holds O((N/R) × fixing_count) points and normals; batching does not make its whole workspace O(batch). Hardware and load affect timings.\n\n'
    else:text+='Benchmark disabled for this run; no runtime or memory comparison is claimed.\n\n'
    text+='## Reproduce and use\n\n```sh\nPYTHONPATH=src .venv/bin/python -m option_hedging.experiments.asian_study --config input_config.toml --output-dir NEW_RUN_DIRECTORY\nPYTHONPATH=src .venv/bin/python -m option_hedging.experiments.verify_run NEW_RUN_DIRECTORY\n```\n\nThe source_snapshot.zip contains captured sources, exact inputs and runtime pins. Extract trusted captured sources into a new directory and run them with the recorded environment. Numerical tables target replay in that environment; timings, figures and portability are separate. Manifest byte-write completion is distinct from numerical acceptance flags in summary.json.\n\nCustom mode accepts explicit fixings and one strike. Arbitrary times remain valid for pricing but can be unsupported by the dated external reference; no times are rounded. This slice does not add dividends, American exercise, live calibration, investment selection, broker execution or production certification.\n'
    (out/'RESULTS.md').write_text(text)
