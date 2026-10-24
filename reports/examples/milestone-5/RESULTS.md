# Paired Monte Carlo study: discrete short-call replication

Executed model experiment, not historical backtesting or live portfolio evidence.
One short European call with unit multiplier, no dividends, common physical GBM
paths, fractional shares and unlimited same-rate borrowing/lending. Positive P&L
belongs to the short-option hedger. RMSE measures error around zero, not average
profit, expected investment return or a validated portfolio VaR model.

## Fixed design and retained data

- S0=100, K=100, T=1 years,
  continuous r=0.05, assumed physical mu=0.08,
  true scenario sigma=0.2. No parameter was estimated from markets.
- 10,000 independent paths; 252 exact-GBM intervals on k/252 annual grid plus exact expiry.
- Hedge every[1, 5] grid steps; costs[0.0, 5.0, 10.0]bps; model sigma[0.15, 0.2, 0.25].
- 21 cases, including a same-model-premium unhedged baseline for each sigma.
  All 210,000 case/path rows retained; same path IDs across cases.
- 1000 bootstrap repeats resample whole path IDs jointly across every case/basis.
  42 metric cells and 102 paired comparison rows retained.

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
| 0 | delta_hedged | 15% | 1 | 0 | -1.91906 | 0.97881 | 2.15424 | -3.70869 | 0.00000 |
| 1 | delta_hedged | 15% | 1 | 5 | -2.26904 | 1.08684 | 2.51588 | -4.23574 | 0.34998 |
| 2 | delta_hedged | 15% | 1 | 10 | -2.61902 | 1.19713 | 2.87963 | -4.76893 | 0.69996 |
| 3 | delta_hedged | 15% | 5 | 0 | -1.91551 | 1.29251 | 2.31076 | -4.36394 | 0.00000 |
| 4 | delta_hedged | 15% | 5 | 5 | -2.11185 | 1.32824 | 2.49479 | -4.62468 | 0.19634 |
| 5 | delta_hedged | 15% | 5 | 10 | -2.30819 | 1.36521 | 2.68167 | -4.88919 | 0.39268 |
| 6 | delta_hedged | 20% | 1 | 0 | 0.00743 | 0.43118 | 0.43122 | -0.70771 | 0.00000 |
| 7 | delta_hedged | 20% | 1 | 5 | -0.30994 | 0.44562 | 0.54279 | -1.09497 | 0.31736 |
| 8 | delta_hedged | 20% | 1 | 10 | -0.62730 | 0.47726 | 0.78820 | -1.49762 | 0.63473 |
| 9 | delta_hedged | 20% | 5 | 0 | 0.01016 | 0.94983 | 0.94984 | -1.57660 | 0.00000 |
| 10 | delta_hedged | 20% | 5 | 5 | -0.17139 | 0.95669 | 0.97187 | -1.79645 | 0.18155 |
| 11 | delta_hedged | 20% | 5 | 10 | -0.35293 | 0.96548 | 1.02792 | -2.00723 | 0.36310 |
| 12 | delta_hedged | 25% | 1 | 0 | 1.97246 | 0.80453 | 2.13021 | 0.75616 | 0.00000 |
| 13 | delta_hedged | 25% | 1 | 5 | 1.68117 | 0.75388 | 1.84245 | 0.55837 | 0.29129 |
| 14 | delta_hedged | 25% | 1 | 10 | 1.38988 | 0.70690 | 1.55930 | 0.35371 | 0.58258 |
| 15 | delta_hedged | 25% | 5 | 0 | 1.97452 | 1.17100 | 2.29561 | 0.29609 | 0.00000 |
| 16 | delta_hedged | 25% | 5 | 5 | 1.80452 | 1.16294 | 2.14676 | 0.13240 | 0.17001 |
| 17 | delta_hedged | 25% | 5 | 10 | 1.63451 | 1.15603 | 2.00197 | -0.02894 | 0.34001 |
| 18 | unhedged | 15% | 0 | 0 | -3.95753 | 16.87971 | 17.33661 | -38.72487 | 0.00000 |
| 19 | unhedged | 20% | 0 | 0 | -2.00329 | 16.87971 | 16.99733 | -36.77063 | 0.00000 |
| 20 | unhedged | 25% | 0 | 0 | -0.02121 | 16.87971 | 16.87888 | -34.78855 | 0.00000 |

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
| 15% | 0 | -0.156514 | [-0.183781, -0.130397] |
| 15% | 5 | 0.021090 | [-0.006493, 0.047737] |
| 15% | 10 | 0.197957 | [0.170189, 0.225322] |
| 20% | 0 | -0.518619 | [-0.535830, -0.502275] |
| 20% | 5 | -0.429083 | [-0.446343, -0.411346] |
| 20% | 10 | -0.239714 | [-0.258285, -0.221122] |
| 25% | 0 | -0.165403 | [-0.181075, -0.150219] |
| 25% | 5 | -0.304313 | [-0.320273, -0.288415] |
| 25% | 10 | -0.442673 | [-0.458837, -0.425904] |

Other predeclared contrasts (cost, model sigma and hedged versus unhedged) are
retained in paired_comparisons.csv. A contrast is conditional on this assumed
GBM/drift/cost/funding model. More samples reduce Monte Carlo noise; they do not
remove jumps, volatility-model error, bad market data or execution risk.

## Separate premium changes from policy changes

Common reference sigma=0.2. To hold initial premium
fixed without changing the delta policy, add(C_ref-C_model)*exp(rT) to each path P&L.
This deterministic funded shift is saved as premium_shift and common_premium_pnl.
This isolates the pricing-receipt effect; it does not supply a real executable quote.
Illustration at5bps costs:

| Model sigma | Every steps | Own premium | Own mean P&L | Common-premium mean | Own RMSE | Common-premium RMSE |
|---|---:|---:|---:|---:|---:|---:|
| 15% | 1 | 8.591658 | -2.269040 | -0.314805 | 2.515877 | 1.131458 |
| 15% | 5 | 8.591658 | -2.111850 | -0.157616 | 2.494787 | 1.337494 |
| 20% | 1 | 10.450584 | -0.309935 | -0.309935 | 0.542787 | 0.542787 |
| 20% | 5 | 10.450584 | -0.171385 | -0.171385 | 0.971869 | 0.971869 |
| 25% | 1 | 12.335999 | 1.681168 | -0.300915 | 1.842446 | 0.811683 |
| 25% | 5 | 12.335999 | 1.804518 | -0.177564 | 2.146759 | 1.176357 |

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
reference. Fixed first16 path IDs were checked across
all cases. Validation passed: **True**;
maximum monetary difference=7.95808e-13,
maximum turnover difference=5.32907e-15.
ledger.csv records pathID0 and predeclared scenarioID7.

paths.npy/times.npy preserve inputs; scenarios.csv supplies case parameters;
path_results.csv supplies all outcomes; bootstrap_statistics.npy plus
bootstrap_fields.json preserve resampled statistics and column labels.
performance.json contains single-run stage timings, not a speedup benchmark.
Source/config/environment and artifact hashes are captured; manifest is written last.

```sh
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.runner \
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
