# Paired Monte Carlo study: discrete short-call replication

Executed model experiment, not historical backtesting or live portfolio evidence.
One short European call with unit multiplier, no dividends, common physical GBM
paths, fractional shares and unlimited same-rate borrowing/lending. Positive P&L
belongs to the short-option hedger. RMSE measures error around zero, not average
profit, expected investment return or a validated portfolio VaR model.

## Fixed design and retained data

- S0=120, K=125, T=0.5 years,
  continuous r=0.04, assumed physical mu=0.06,
  true scenario sigma=0.3. No parameter was estimated from markets.
- 3,000 independent paths; 126 exact-GBM intervals on k/252 annual grid plus exact expiry.
- Hedge every[1, 5] grid steps; costs[0.0, 2.0, 10.0]bps; model sigma[0.2, 0.25, 0.3].
- 21 cases, including a same-model-premium unhedged baseline for each sigma.
  All 63,000 case/path rows retained; same path IDs across cases.
- 500 bootstrap repeats resample whole path IDs jointly across every case/basis.
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
| 0 | delta_hedged | 20% | 1 | 0 | -3.49950 | 1.87207 | 3.96863 | -6.97380 | 0.00000 |
| 1 | delta_hedged | 20% | 1 | 2 | -3.62897 | 1.91832 | 4.10465 | -7.18254 | 0.12946 |
| 2 | delta_hedged | 20% | 1 | 10 | -4.14682 | 2.10633 | 4.65094 | -8.03442 | 0.64732 |
| 3 | delta_hedged | 20% | 5 | 0 | -3.44156 | 2.37279 | 4.18003 | -7.90105 | 0.00000 |
| 4 | delta_hedged | 20% | 5 | 2 | -3.51289 | 2.39005 | 4.24863 | -7.99524 | 0.07133 |
| 5 | delta_hedged | 20% | 5 | 10 | -3.79822 | 2.46101 | 4.52560 | -8.39996 | 0.35666 |
| 6 | delta_hedged | 25% | 1 | 0 | -1.75503 | 1.14497 | 2.09539 | -3.98951 | 0.00000 |
| 7 | delta_hedged | 25% | 1 | 2 | -1.87534 | 1.17587 | 2.21339 | -4.16714 | 0.12030 |
| 8 | delta_hedged | 25% | 1 | 10 | -2.35656 | 1.30727 | 2.69476 | -4.88985 | 0.60152 |
| 9 | delta_hedged | 25% | 5 | 0 | -1.70468 | 1.90182 | 2.55375 | -5.24560 | 0.00000 |
| 10 | delta_hedged | 25% | 5 | 2 | -1.77239 | 1.91168 | 2.60666 | -5.34643 | 0.06771 |
| 11 | delta_hedged | 25% | 5 | 10 | -2.04323 | 1.95372 | 2.82675 | -5.69897 | 0.33855 |
| 12 | delta_hedged | 30% | 1 | 0 | -0.01424 | 0.84070 | 0.84068 | -1.40272 | 0.00000 |
| 13 | delta_hedged | 30% | 1 | 2 | -0.12690 | 0.84604 | 0.85537 | -1.55062 | 0.11266 |
| 14 | delta_hedged | 30% | 1 | 10 | -0.57756 | 0.88386 | 1.05571 | -2.16523 | 0.56332 |
| 15 | delta_hedged | 30% | 5 | 0 | 0.03098 | 1.76195 | 1.76193 | -2.90963 | 0.00000 |
| 16 | delta_hedged | 30% | 5 | 2 | -0.03372 | 1.76474 | 1.76477 | -2.96314 | 0.06470 |
| 17 | delta_hedged | 30% | 5 | 10 | -0.29250 | 1.77868 | 1.80228 | -3.25938 | 0.32348 |
| 18 | unhedged | 20% | 0 | 0 | -3.65217 | 16.83383 | 17.22271 | -39.86826 | 0.00000 |
| 19 | unhedged | 25% | 0 | 0 | -1.92789 | 16.83383 | 16.94108 | -38.14398 | 0.00000 |
| 20 | unhedged | 30% | 0 | 0 | -0.20132 | 16.83383 | 16.83223 | -36.41741 | 0.00000 |

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
| 20% | 0 | -0.211399 | [-0.287836, -0.116253] |
| 20% | 2 | -0.143983 | [-0.220894, -0.049156] |
| 20% | 10 | 0.125342 | [0.045400, 0.222467] |
| 25% | 0 | -0.458362 | [-0.522094, -0.374879] |
| 25% | 2 | -0.393265 | [-0.457823, -0.309092] |
| 25% | 10 | -0.131988 | [-0.200193, -0.045929] |
| 30% | 0 | -0.921249 | [-0.973296, -0.869039] |
| 30% | 2 | -0.909401 | [-0.963061, -0.858899] |
| 30% | 10 | -0.746569 | [-0.804166, -0.691993] |

Other predeclared contrasts (cost, model sigma and hedged versus unhedged) are
retained in paired_comparisons.csv. A contrast is conditional on this assumed
GBM/drift/cost/funding model. More samples reduce Monte Carlo noise; they do not
remove jumps, volatility-model error, bad market data or execution risk.

## Separate premium changes from policy changes

Common reference sigma=0.25. To hold initial premium
fixed without changing the delta policy, add(C_ref-C_model)*exp(rT) to each path P&L.
This deterministic funded shift is saved as premium_shift and common_premium_pnl.
This isolates the pricing-receipt effect; it does not supply a real executable quote.
Illustration at2bps costs:

| Model sigma | Every steps | Own premium | Own mean P&L | Common-premium mean | Own RMSE | Common-premium RMSE |
|---|---:|---:|---:|---:|---:|---:|
| 20% | 1 | 5.647218 | -3.628968 | -1.904686 | 4.104649 | 2.703066 |
| 20% | 5 | 5.647218 | -3.512894 | -1.788613 | 4.248633 | 2.984893 |
| 25% | 1 | 7.337356 | -1.875338 | -1.875338 | 2.213391 | 2.213391 |
| 25% | 5 | 7.337356 | -1.772391 | -1.772391 | 2.606656 | 2.606656 |
| 30% | 1 | 9.029740 | -0.126905 | -1.853477 | 0.855368 | 2.037382 |
| 30% | 5 | 9.029740 | -0.033717 | -1.760289 | 1.764769 | 2.492367 |

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
reference. Fixed first12 path IDs were checked across
all cases. Validation passed: **True**;
maximum monetary difference=6.82121e-13,
maximum turnover difference=3.55271e-15.
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
