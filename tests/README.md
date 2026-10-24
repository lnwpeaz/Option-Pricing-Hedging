# Validation map

Black-Scholes, Greeks, CRR, terminal GBM, three MC estimators and their demos have
executable tests. Full time-grid GBM and its demo also have executable tests;
the one-path hedge ledger/demo and paired ensemble study also have executable tests.
Add numerical tests with each corresponding feature.
Do not create passing placeholder tests or treat test count as research evidence.

| File (implemented or planned) | Required cases |
|---|---|
| test_black_scholes.py | Baseline call/put, parity, bounds, expiry, zero sigma, invalid and nonfinite inputs |
| test_greeks.py | Analytic vs finite differences, vega units, documented kink handling |
| test_pricing_demo.py | Actual CLI, CSV/PNG/manifest, dividend rejection and no overwriting |
| test_binomial.py | Step-grid convergence, invalid probability, deterministic limits |
| test_convergence_demo.py | Real CLI, price/error/timing CSV, manifest, no overwrite and invalid grids |
| test_monte_carlo.py | Independent-seed RMSE/coverage, pair SE, pilot separation, scale-equivariance, exact limits, RNG and input validation |
| test_monte_carlo_demo.py | Real CLI/output integrity, numeric reproducibility, no overwrite, invalid configs, scalar/vector agreement and zero-RMSE reporting |
| test_gbm.py | Shape, initial value, positivity, zero-sigma path, RNG reproducibility, explicit drift |
| test_path_statistics.py | Hand-worked mean/SD/SE, path quantiles and ensemble uncertainty across tiny/large currency scales |
| test_paths_demo.py | Actual CLI, NPY matrices, paired drift/seed checks, log moments, hashes, numeric reproducibility and no overwrite |
| test_ledger.py | Hand-worked accounting, negative cash/rates, actual-dt interest, all costs, no expiry rebalance, prefix causality, scaling and explicit range errors |
| test_hedge_demo.py | Actual CLI/verification, saved core records, reconciliations, reproducibility, unsupported config rejection and no overwrite |
| test_experiment.py | Paired scenarios, unsupported config rejection, manifests and no overwriting |

Full acceptance cases and conventions: ../docs/RESEARCH_SPEC.md.

## Completed-stage research-quality additions

- test_payoff_reference.py: known prices, bounded tails, deterministic limits,
  independence from production pricers/GBM and near-coincident integration splits.
- test_validation_demo.py: complete grid/rows, retained degeneracy, strict config,
  no overwrite, saved figures, source recovery and deterministic numerical CSVs.
- test_validation_metrics.py: small genuine SE is below a diagnostic floor, not
  proof of roundoff.
- test_validation_plots.py: a failed reference comparison remains inside plot limits.
- test_provenance.py: deterministic source archive, byte/config hashes, tamper
  rejection, historical limitations and actual extracted-source subprocess replay.

## Paired-study validation

- test_batch_hedge.py: hand accounting, all18 scalar/vector modes, irregular/negative
  rates, long grids, scaling, input immutability and explicit range guards.
- test_hedge_metrics.py: hand moments/Wilson bounds, scaled currency, shared-ID
  bootstrap, identical-pair zero intervals and premium-shift decomposition.
- test_experiment.py: real CLI, all cases/paths/bases, saved scalar checks/NPYs,
  independent raw RMSE recomputation, source verification, repeatability/no overwrite.
