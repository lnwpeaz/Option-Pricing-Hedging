# Executed Asian option Monte Carlo / randomized QMC study

Retained **2880 requested estimates**: 2880 completed, 0 failed; 18432 raw scramble prices.

European cash-settled discrete average-price options, q=0, constant-rate/volatility risk-neutral GBM, equal weights and no past fixings. Spot is excluded from the average. Changing fixing count changes the contract. Prices are model premiums, not forecasts or executable quotes.

## Reference precision

| contract_id | fixing_count | strike | price | precision_radius | precision_kind | status |
| --- | --- | --- | --- | --- | --- | --- |
| c000 | 12 | 90 | 12.90998 | 0.00265077 | empirical_cross_method | low_precision |
| c001 | 12 | 100 | 6.143965 | 0.003052628 | empirical_cross_method | low_precision |
| c002 | 12 | 110 | 2.280865 | 0.003822342 | empirical_cross_method | low_precision |
| c003 | 52 | 90 | 12.65193 | 0.01203253 | empirical_cross_method | low_precision |
| c004 | 52 | 100 | 5.83729 | 0.008266987 | empirical_cross_method | low_precision |
| c005 | 52 | 110 | 2.047631 | 0.004022585 | empirical_cross_method | low_precision |

Internal geometric/single-fixing analytic cases are checked by independent quadrature. Two-fixing arithmetic quadrature reports QUADPACK and omitted-tail diagnostics. For dated general arithmetic contracts, external QuantLib 1.44 uses three fixed FD grids, Choi levels 5/10/15 and four independent 262,144-path MC-control checks. The finest Choi point is predeclared; the radius is the maximum of twice the final Choi change, twice the final FD change and the finest cross-engine gap. This empirical band is not a rigorous error bound. Unavailable and failed comparisons remain in reference_checks.csv.

**90 of 90 method/budget cells have reference-dominated error.** Precision-dependent rankings are withheld for these cells; sampling dispersion and computational observations remain usable. A point-reference RMSE can be smaller than the reference uncertainty.

## Largest production budget for each contract

| contract_id | method | completed_count | rmse | empirical_sd | mean_reported_se | possible_coverage | definite_coverage | rank_eligible |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| c000 | plain | 32 | 0.03932525 | 0.03994838 | 0.04285184 | 0.9375 | 0.9375 | False |
| c000 | antithetic | 32 | 0.01588253 | 0.01567815 | 0.01558908 | 0.9375 | 0.90625 | False |
| c000 | control | 32 | 0.0009324743 | 0.0009440749 | 0.001040646 | 1 | 0 | False |
| c000 | sobol | 32 | 0.002306789 | 0.002334685 | 0.002061338 | 1 | 0.53125 | False |
| c000 | sobol_bridge | 32 | 0.000649741 | 0.000653697 | 0.0007118956 | 1 | 0 | False |
| c001 | plain | 32 | 0.03746722 | 0.03792171 | 0.03322484 | 0.9375 | 0.9375 | False |
| c001 | antithetic | 32 | 0.02744344 | 0.02733512 | 0.02299801 | 0.90625 | 0.875 | False |
| c001 | control | 32 | 0.0008961262 | 0.0009101838 | 0.0009295215 | 1 | 0 | False |
| c001 | sobol | 32 | 0.002868411 | 0.00288471 | 0.00297698 | 1 | 0.71875 | False |
| c001 | sobol_bridge | 32 | 0.0008708249 | 0.0008686113 | 0.0008288307 | 1 | 0 | False |
| c002 | plain | 32 | 0.02171653 | 0.02164975 | 0.02109484 | 0.96875 | 0.875 | False |
| c002 | antithetic | 32 | 0.01830483 | 0.01827495 | 0.01905892 | 1 | 0.96875 | False |
| c002 | control | 32 | 0.0007764428 | 0.0007870274 | 0.0008486918 | 1 | 0 | False |
| c002 | sobol | 32 | 0.002591146 | 0.002632606 | 0.003073729 | 1 | 0.6875 | False |
| c002 | sobol_bridge | 32 | 0.0008577812 | 0.000764648 | 0.0009112413 | 1 | 0 | False |
| c003 | plain | 32 | 0.03356043 | 0.03096332 | 0.0410847 | 1 | 0.9375 | False |
| c003 | antithetic | 32 | 0.01877772 | 0.01684182 | 0.01448928 | 0.9375 | 0.65625 | False |
| c003 | control | 32 | 0.009585013 | 0.0008787084 | 0.001001069 | 1 | 0 | False |
| c003 | sobol | 32 | 0.009175994 | 0.002664429 | 0.003160537 | 1 | 0 | False |
| c003 | sobol_bridge | 32 | 0.009346576 | 0.0007854197 | 0.0007263249 | 1 | 0 | False |
| c004 | plain | 32 | 0.02947806 | 0.0295525 | 0.0316021 | 0.9375 | 0.90625 | False |
| c004 | antithetic | 32 | 0.02436395 | 0.02303004 | 0.02188592 | 0.96875 | 0.90625 | False |
| c004 | control | 32 | 0.006638613 | 0.0009874488 | 0.0008747376 | 1 | 0 | False |
| c004 | sobol | 32 | 0.007718 | 0.005236713 | 0.004948804 | 0.96875 | 0.125 | False |
| c004 | sobol_bridge | 32 | 0.006856447 | 0.001049304 | 0.0009588516 | 1 | 0 | False |
| c005 | plain | 32 | 0.01853404 | 0.01778686 | 0.01950575 | 0.9375 | 0.875 | False |
| c005 | antithetic | 32 | 0.01659347 | 0.01641508 | 0.01773575 | 1 | 0.96875 | False |
| c005 | control | 32 | 0.00332494 | 0.0007928542 | 0.0007996226 | 1 | 0 | False |
| c005 | sobol | 32 | 0.006959094 | 0.005842366 | 0.005256018 | 0.9375 | 0.75 | False |
| c005 | sobol_bridge | 32 | 0.003146651 | 0.001110502 | 0.0009494291 | 1 | 0 | False |

All budgets/methods and failed counts are retained in metrics.csv. RMSE/bias are against the declared point and remain approximate when the reference is approximate. Percentile bootstrap uses shared macro-ID resampling; paired_comparisons.csv preserves Sobol/bridge pairing. Conditional RMSE sensitivity [max(0, RMSE-radius), RMSE+radius] assumes the band contains truth; it is not a confidence interval. Possible coverage means the reported CI overlaps the reference band; definite coverage means it contains that entire band. Exact analytic cases additionally have Wilson coverage intervals.

## Computation and uncertainty

Plain/control use N independent production observations; antithetic uses N/2 pair means and N payoff evaluations. Control fits beta on an extra independent pilot, then freezes it. QMC uses R independent scrambles, each with a power-of-two point count; SE is the standard deviation of scramble prices divided by sqrt(R). Approximate Student-t intervals use R-1 degrees of freedom. A zero observed SE is flagged and is not proof of an exact stochastic price; sigma=0 is a separate deterministic status with zero actual work and no RNG consumption. No estimate or CI is clipped.

normal_coordinates counts newly generated normals or inverse-CDF values, excluding antithetic negatives. payoff_evaluations includes target pilot work; control_payoff_evaluations counts extra geometric evaluations. metrics.csv reports RMSE² times production-path and total-payoff work; these counters do not measure total FLOPs. benchmark.csv also reports seconds × point-reference RMSE² where a matching study cell exists. This remains a conditional diagnostic when reference precision is inadequate.

| method | batch_size | median | min | max |
| --- | --- | --- | --- | --- |
| plain | 256 | 0.05802617 | 0.05246721 | 0.06479221 |
| antithetic | 256 | 0.08027779 | 0.05856417 | 0.08189587 |
| control | 256 | 0.07232404 | 0.07052737 | 0.07390979 |
| sobol | 256 | 0.1364081 | 0.1356607 | 0.1636501 |
| sobol_bridge | 256 | 0.1753917 | 0.1724721 | 0.1998748 |
| plain | 1024 | 0.04317 | 0.04228175 | 0.04475617 |
| antithetic | 1024 | 0.04007208 | 0.03927492 | 0.06865488 |
| control | 1024 | 0.04606104 | 0.04560004 | 0.04740158 |
| sobol | 1024 | 0.1236747 | 0.1213015 | 0.1258554 |
| sobol_bridge | 1024 | 0.1368622 | 0.134762 | 0.1394018 |
| plain | 4096 | 0.04491658 | 0.04442133 | 0.04779917 |
| antithetic | 4096 | 0.03396275 | 0.03364717 | 0.03671662 |
| control | 4096 | 0.04819808 | 0.04718579 | 0.05223921 |
| sobol | 4096 | 0.1253452 | 0.1220053 | 0.1329915 |
| sobol_bridge | 4096 | 0.1306095 | 0.1299114 | 0.1331563 |

Each method is warmed; forward/reverse order alternates across repetitions. Complete-estimator timing includes RNG through CI construction. allocations.csv is a separate untimed tracemalloc pass, not process RSS. Sobol holds O((N/R) × fixing_count) points and normals; batching does not make its whole workspace O(batch). Hardware and load affect timings.

## Reproduce and use

```sh
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.asian_study --config input_config.toml --output-dir NEW_RUN_DIRECTORY
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.verify_run NEW_RUN_DIRECTORY
```

The source_snapshot.zip contains captured sources, exact inputs and runtime pins. Extract trusted captured sources into a new directory and run them with the recorded environment. Numerical tables target replay in that environment; timings, figures and portability are separate. Manifest byte-write completion is distinct from numerical acceptance flags in summary.json.

Custom mode accepts explicit fixings and one strike. Arbitrary times remain valid for pricing but can be unsupported by the dated external reference; no times are rounded. This slice does not add dividends, American exercise, live calibration, investment selection, broker execution or production certification.
