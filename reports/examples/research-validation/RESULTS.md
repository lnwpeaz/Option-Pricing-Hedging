# Numerical validation across a predeclared parameter domain

This extends the baseline evidence. It checks prices/uncertainty under the same
European, constant-volatility, no-dividend model; it is not historical market
validation, a novel pricing model, or evidence of hedge effectiveness.

## Fixed design and independent reference

- Spot=100; strikes=[70.0, 100.0, 130.0]; maturities=[0.003968253968253968, 0.25, 1.0, 3.0] years.
- Volatilities=[0.05, 0.2, 0.8]; continuous rates=[-0.02, 0.05]; both call/put.
- Total option scenarios: **144**; CRR steps=[32, 128, 512].
- Three MC estimators, 8,192 production paths and 32 independent repeats per cell.
- Control uses 512 additional independent pilot paths per estimate.
- Every scenario/repeat is retained, including zero sample variance and CI failures.

The reference numerically integrates discounted payoff against the standard normal
density without calling the project analytic/CRR/MC/GBM implementation. Finite
integration limits are L=-12, U=12+sigma*sqrt(T), split at the payoff kink and density
centers. For a call, payoff <= discounted stock; for a put, payoff <= discounted
strike. Normal-tail probabilities therefore bound the omitted payoff tails.

QUADPACK's absolute integration error is an **estimate**, distinct from the analytic
truncation bound. It is not a proof of exact floating-point arithmetic. Very small
premiums below that error budget are not relatively resolved by this check.

Predeclared absolute analytic tolerance: **1e-07 premium units**.
Maximum analytic/integral difference: **1.56319e-13**.
Largest quadrature error estimate: 6.28876e-11;
largest truncated-tail bound: 4.53297e-31.
All analytic comparisons within tolerance: **True**.
Tree rejected-grid rows retained: 0.
CRR errors can oscillate; boxplots do not imply every scenario improves monotonically.
The reference-error figure uses a linear axis below 1e-12 and log scaling above it.
The CRR figure places errors <= 1e-10 at that display floor;
exact and tiny errors remain unchanged in the CSV.

## Monte Carlo limitations are measured

MC estimates are compared with the analytic reference after the independent
absolute-price check. Normal 95% CIs are approximate. Wilson intervals quantify
finite-repeat uncertainty in observed coverage; with only 32 repeats,
individual coverage differences are noisy. There is no multiple-testing claim that
one method is statistically best over all regimes.

| Method | Regular cells | Cells with any zero SE | Zero-SE runs | Cells below diagnostic floor | Uncovered runs with error above floor |
|---|---:|---:|---:|---:|---:|
| plain | 120 | 24 | 705 | 0 | 409 |
| antithetic | 119 | 25 | 694 | 0 | 415 |
| control | 99 | 25 | 698 | 20 | 574 |

The absolute uncertainty floor is predeclared at 1e-10 premium units.
Cells with RMS standard error at or below this floor are excluded from the regular
SE-calibration comparison. This can reflect genuinely small sampling uncertainty;
it does not prove roundoff. The floor never edits prices, raw CIs or coverage. Zero sample variance can mean a rare payoff was not
observed. A nearly linear payoff with a stock control may also have residual
uncertainty near floating-point precision. Both can make raw normal-CI coverage
misleading for different reasons. Cells with partial degeneracy are recorded
separately. Check mc_metrics.csv and join scenario_id to reference_checks.csv.

Reported coverage failures with tiny monetary errors are not claims of economically
large risk. Lower SE is not automatically more trustworthy. These observations
motivate caution before Monte Carlo uncertainty is used in future hedge analysis.
The existing analytic Greeks remain the planned hedge policy; this audit does not
introduce noisy MC hedge decisions.

## Reproduction and provenance

```sh
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.validation_demo \
  --config configs/validation.toml --output-dir reports/runs/my-validation
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.verify_run reports/runs/my-validation
```

Raw data are reference_checks.csv, tree_checks.csv, mc_estimates.csv and mc_metrics.csv.
Numerical outputs use explicit PCG64 SeedSequence keys [4,scenario_id,repeat,method_id,seed].
source_snapshot.zip preserves actual source, input configuration, dependency versions
and REPLAY.md. Integrity verification checks saved bytes; numerical replay requires
the recorded Python/platform/library environment. Timings and figure bytes are not
replay acceptance criteria. Old hash-only examples remain historical and are not
retroactively described as containing recoverable source.

## Remaining substantive research

Complete the self-financing hedge ledger, validate accounting manually, and run
paired frequency/cost/volatility-misspecification experiments with uncertainty.
Those results answer the original research question. Adding more models or a UI
before that would not close the central evidence gap.

Primary implementation reference: [SciPy quad](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.quad.html).
