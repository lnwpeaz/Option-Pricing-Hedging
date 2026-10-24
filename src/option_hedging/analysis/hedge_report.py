"""Render executed model findings with explicit practical-use boundaries."""


def make_report(market,sim,grid,uncertainty,summary,cases,metrics,comparisons):
    lookup={(r['scenario_id'],r['premium_basis']):r for r in metrics}
    case_lookup={c['scenario_id']:c for c in cases}
    table=[]
    for c in cases:
        m=lookup[c['scenario_id'],'model']
        table.append(f"| {c['scenario_id']} | {c['strategy']} | {100*c['hedge_volatility']:g}% | {c['rebalance_every_steps']} | {c['one_way_cost_bps']:g} | {m['mean_pnl']:.5f} | {m['standard_deviation']:.5f} | {m['rmse']:.5f} | {m['pnl_q05']:.5f} | {m['mean_financed_costs']:.5f} |")
    frequency=[]
    for p in comparisons:
        if p['comparison_kind']=='frequency' and p['premium_basis']=='model':
            c=case_lookup[p['left_scenario_id']]
            frequency.append(f"| {100*c['hedge_volatility']:g}% | {c['one_way_cost_bps']:g} | {p['rmse_difference']:.6f} | [{p['rmse_difference_ci_low']:.6f}, {p['rmse_difference_ci_high']:.6f}] |")
    premium=[]
    middle=grid['one_way_cost_bps'][len(grid['one_way_cost_bps'])//2]
    for c in cases:
        if c['strategy']=='delta_hedged' and c['one_way_cost_bps']==middle:
            own,common=(lookup[c['scenario_id'],b] for b in ('model','common_reference'))
            premium.append(f"| {100*c['hedge_volatility']:g}% | {c['rebalance_every_steps']} | {c['initial_premium']:.6f} | {own['mean_pnl']:.6f} | {common['mean_pnl']:.6f} | {own['rmse']:.6f} | {common['rmse']:.6f} |")
    return f'''# Paired Monte Carlo study: discrete short-call replication

Executed model experiment, not historical backtesting or live portfolio evidence.
One short European call with unit multiplier, no dividends, common physical GBM
paths, fractional shares and unlimited same-rate borrowing/lending. Positive P&L
belongs to the short-option hedger. RMSE measures error around zero, not average
profit, expected investment return or a validated portfolio VaR model.

## Fixed design and retained data

- S0={market['spot']:g}, K={market['strike']:g}, T={market['maturity_years']:g} years,
  continuous r={market['risk_free_rate']:g}, assumed physical mu={market['physical_drift']:g},
  true scenario sigma={market['true_volatility']:g}. No parameter was estimated from markets.
- {sim['paths']:,} independent paths; {summary['intervals']} exact-GBM intervals on k/{sim['steps_per_year']} annual grid plus exact expiry.
- Hedge every{grid['rebalance_every_steps']} grid steps; costs{grid['one_way_cost_bps']}bps; model sigma{grid['hedge_volatility']}.
- {summary['scenario_count']} cases, including a same-model-premium unhedged baseline for each sigma.
  All {summary['path_result_rows']:,} case/path rows retained; same path IDs across cases.
- {uncertainty['bootstrap_repeats']} bootstrap repeats resample whole path IDs jointly across every case/basis.
  {summary['metric_cells']} metric cells and {summary['paired_comparison_rows']} paired comparison rows retained.

The analytic delta policy is evaluated using only current price and time remaining.
No delta update occurs at expiry: existing shares are liquidated, costs paid and
call payoff settled. Costs apply at open, rebalance and close, and their financing
is already in cash. Do not deduct financed costs again. At the default252-steps/year
grid, every1/every5 steps approximate daily/weekly frequency, not an exchange calendar.

## All model-premium outcomes

All amounts are premium units for one short option unit, NOT percentages of a portfolio.
Unhedged frequency0 indicates no stock hedge. Model sigma sets both premium and delta.

| ID | Strategy | Model sigma | Every steps | Cost bps | Mean P&L | SD | RMSE | P&L5th percentile | Mean financed cost |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(table)}

Per-cell bootstrap95% intervals for mean/SD/RMSE/quantiles, Wilson intervals for
loss probability, and all raw values are in metrics.csv. Loss probability alone
does not measure loss magnitude; a tighter error distribution with costs can have
a high frequency of small negative results. A small average error is not a return guarantee.

## Paired frequency effect

Difference is finest-grid RMSE minus coarser-grid RMSE at the same sigma/cost.
Negative indicates smaller observed replication error for the finer policy.
Shared resampled paths preserve covariance; these are pointwise approximate95%
bootstrap intervals, not simultaneous superiority claims across the grid.

| Model sigma | Cost bps | RMSE difference | Paired95% interval |
|---|---:|---:|---|
{chr(10).join(frequency)}

Other predeclared contrasts (cost, model sigma and hedged versus unhedged) are
retained in paired_comparisons.csv. A contrast is conditional on this assumed
GBM/drift/cost/funding model. More samples reduce Monte Carlo noise; they do not
remove jumps, volatility-model error, bad market data or execution risk.

## Separate premium changes from policy changes

Common reference sigma={grid['reference_volatility']:g}. To hold initial premium
fixed without changing the delta policy, add(C_ref-C_model)*exp(rT) to each path P&L.
This deterministic funded shift is saved as premium_shift and common_premium_pnl.
This isolates the pricing-receipt effect; it does not supply a real executable quote.
Illustration at{middle:g}bps costs:

| Model sigma | Every steps | Own premium | Own mean P&L | Common-premium mean | Own RMSE | Common-premium RMSE |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(premium)}

Funding columns explicitly prefixed model_premium always refer to the original
model-premium cash ledger, even on common-reference metric rows. Peak cash
borrowing includes before/after-event balances and settlement; it is NOT broker
margin, collateral requirements, buying power or an investable capital denominator.
The portfolio value needed to survive a real strategy is not established here.

## Engineering, accounting and reproducibility

Vectorized accounting loops over dates and vectorizes across independent paths.
Path input is O(N*M), the date loop uses O(N) workspace, and current input validation
also uses O(N*M) temporary boolean arrays. This is not a measured total-RSS bound.
It does not retain a full ledger for every case/path. The scalar ledger remains the audit
reference. Fixed first{sim['scalar_validation_paths']} path IDs were checked across
all cases. Validation passed: **{summary['scalar_validation_passed']}**;
maximum monetary difference={summary['max_scalar_money_difference']:.6g},
maximum turnover difference={summary['max_scalar_share_difference']:.6g}.
ledger.csv records pathID0 and predeclared scenarioID{summary['representative_scenario_id']}.

paths.npy/times.npy preserve inputs; scenarios.csv supplies case parameters;
path_results.csv supplies all outcomes; bootstrap_statistics.npy plus
bootstrap_fields.json preserve resampled statistics and column labels.
performance.json contains single-run stage timings, not a speedup benchmark.
Source/config/environment and artifact hashes are captured; manifest is written last.

```sh
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.runner \\
  --config configs/hedge_study.toml --output-dir reports/runs/my-paired-study
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.verify_run reports/runs/my-paired-study
```

## Can this be used by a company or a personal investor?

This is a reproducible quantitative research prototype within its declared domain.
It is usable for model-based investigation and testing of numerical methods.
Simulation/tests do not certify a corporate production system or suitability for
placing trades in a real account. Historical/out-of-sample and forward paper
validation, real quotes/volatility calibration, contract-specific settlement,
funding/margin/liquidity constraints and operational controls remain absent.
See docs/PRACTICAL_USE_TH.md for the source-backed assessment.

The user's long stock/ETF portfolios are a different liability/exposure problem
from this short-call replication study. These RMSE improvements are not estimates
of their portfolio drawdown reduction. Long-portfolio risk work needs position
weights, distributions/corporate actions, joint exposures/correlation, currency
and horizon, and a separately evaluated hedge/rebalance policy with real costs.
No portfolio allocation, option sale or broker execution is generated by this run.
'''
