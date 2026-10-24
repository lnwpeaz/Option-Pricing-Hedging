# Executed Asian option Monte Carlo / randomized QMC study

Retained **480 requested estimates**: 480 completed, 0 failed; 3072 raw scramble prices.

European cash-settled discrete average-price options, q=0, constant-rate/volatility risk-neutral GBM, equal weights and no past fixings. Spot is excluded from the average. Changing fixing count changes the contract. Prices are model premiums, not forecasts or executable quotes.

## Reference precision

| contract_id | fixing_count | strike | price | precision_radius | precision_kind | status |
| --- | --- | --- | --- | --- | --- | --- |
| c000 | 3 | 125 | — | — | unavailable | unavailable |

Internal geometric/single-fixing analytic cases are checked by independent quadrature. Two-fixing arithmetic quadrature reports QUADPACK and omitted-tail diagnostics. For dated general arithmetic contracts, external QuantLib 1.44 uses three fixed FD grids, Choi levels 5/10/15 and four independent 262,144-path MC-control checks. The finest Choi point is predeclared; the radius is the maximum of twice the final Choi change, twice the final FD change and the finest cross-engine gap. This empirical band is not a rigorous error bound. Unavailable and failed comparisons remain in reference_checks.csv.

**15 of 15 method/budget cells have reference-dominated error.** Precision-dependent rankings are withheld for these cells; sampling dispersion and computational observations remain usable. A point-reference RMSE can be smaller than the reference uncertainty.

## Largest production budget for each contract

| contract_id | method | completed_count | rmse | empirical_sd | mean_reported_se | possible_coverage | definite_coverage | rank_eligible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| c000 | plain | 32 | — | 0.03276339 | 0.03258272 | — | — | False |
| c000 | antithetic | 32 | — | 0.01737709 | 0.01730713 | — | — | False |
| c000 | control | 32 | — | 0.0009216097 | 0.0009200619 | — | — | False |
| c000 | sobol | 32 | — | 0.0007199852 | 0.0006448179 | — | — | False |
| c000 | sobol_bridge | 32 | — | 0.0004585733 | 0.0004162047 | — | — | False |

All budgets/methods and failed counts are retained in metrics.csv. RMSE/bias are against the declared point and remain approximate when the reference is approximate. Percentile bootstrap uses shared macro-ID resampling; paired_comparisons.csv preserves Sobol/bridge pairing. Conditional RMSE sensitivity [max(0, RMSE-radius), RMSE+radius] assumes the band contains truth; it is not a confidence interval. Possible coverage means the reported CI overlaps the reference band; definite coverage means it contains that entire band. Exact analytic cases additionally have Wilson coverage intervals.

## Computation and uncertainty

Plain/control use N independent production observations; antithetic uses N/2 pair means and N payoff evaluations. Control fits beta on an extra independent pilot, then freezes it. QMC uses R independent scrambles, each with a power-of-two point count; SE is the standard deviation of scramble prices divided by sqrt(R). Approximate Student-t intervals use R-1 degrees of freedom. A zero observed SE is flagged and is not proof of an exact stochastic price; sigma=0 is a separate deterministic status with zero actual work and no RNG consumption. No estimate or CI is clipped.

normal_coordinates counts newly generated normals or inverse-CDF values, excluding antithetic negatives. payoff_evaluations includes target pilot work; control_payoff_evaluations counts extra geometric evaluations. metrics.csv reports RMSE² times production-path and total-payoff work; these counters do not measure total FLOPs. benchmark.csv also reports seconds × point-reference RMSE² where a matching study cell exists. This remains a conditional diagnostic when reference precision is inadequate.

Benchmark disabled for this run; no runtime or memory comparison is claimed.

## Reproduce and use

```sh
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.asian_study --config input_config.toml --output-dir NEW_RUN_DIRECTORY
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.verify_run NEW_RUN_DIRECTORY
```

The source_snapshot.zip contains captured sources, exact inputs and runtime pins. Extract trusted captured sources into a new directory and run them with the recorded environment. Numerical tables target replay in that environment; timings, figures and portability are separate. Manifest byte-write completion is distinct from numerical acceptance flags in summary.json.

Custom mode accepts explicit fixings and one strike. Arbitrary times remain valid for pricing but can be unsupported by the dated external reference; no times are rounded. This slice does not add dividends, American exercise, live calibration, investment selection, broker execution or production certification.
