# Milestone5: paired Monte Carlo hedge study and practical-use assessment

User requests next stage, measured results and candid company/personal-portfolio
readiness. Existing financial conventions in docs/RESEARCH_SPEC.md remain binding.
Execute authorized research inline; portfolio-specific adaptation waits for actual
instrument/market information. No broker connection or live trade is authorized.

## Fixed experimental design

10000 independent physical GBM paths, annual grid252/exact expiry, S=K100,T1,
mu.08,true sigma.2,r.05. Full crossing hedge intervals[1,5], costs[0,5,10]bps and
model sigma[.15,.2,.25]:18 hedge scenarios, plus3 same-model-premium unhedged cases.
Every case uses identical path IDs. No scenario/seed pruning or after-the-fact winner.
Save physical paths/times and210000 case/path rows. RNG PCG64 keys[5,0,seed] for
paths and[50,seed] for bootstrap, no global RNG. Bootstrap1000 resamples of whole
path IDs shared across every case, in bounded batches16. Numerical uncertainty is
conditional on these model assumptions, not uncertainty about future market regimes.

Model sigma changes price and delta. Save model-premium P&L and common-reference
premium P&L with deterministic adjustment(C_ref-C_model)*exp(rT), reference sigma.2.
42 metric cells (21cases*2premium bases). All averages, SD, RMSE,5/50/95% quantiles,
loss probability/Wilson interval, nominal/financed costs, turnover and funding
diagnostics retained. Bootstrap pointwise95% percentile CIs for mean/SD/RMSE and
three quantiles. Shared path resamples give paired mean-P&L/RMSE difference intervals.
Predeclared comparisons: every1 minus every5(9); cost5/10 minus0(12);
sigma15/25 minus20(12); hedged minus same-model unhedged(18), for each premium basis.
102 comparison rows; no multiple-testing superiority or live-trading claim.

## Computation and validation

Scalar ledger is the audit reference; repeated per-path Python/Greek objects would
waste compute. Add pure vectorized hedge_paths/unhedged_paths that iterate dates
and vectorize path dimension, returning summary arrays rather than full ledgers.
Same costs, accrual, zero-sigma kink, expiry convention and explicit range guards.
Use compensated summation for cash, and an error-free subtraction residual for the
existing64-ULP-of-strike payoff range guard. Return max cash borrowing across before/
after-event balances as a funding diagnostic; this is not broker margin or available
buying power. O(NM) input storage, O(N) engine workspace; no trade at expiry besides
liquidation. No noise in analytic hedge policy. Save one scalar ledger(pathID0) and
actual scalar/vector consistency checks on fixed first16 path IDs for all21 cases.

Pure analysis metrics handle finite data/currency scaling, paired resampling and
zero error. Runner validates a dedicated config rather than silently consuming
planned pricing/convergence settings from baseline.toml. Whole run refuses existing
outputs, computes before writing, archives source, writes manifest last. Failures
remain explicit; no unsupported cases are dropped. Save timing observations
separately; no inferred speedup or production performance guarantee.

## Deliverables and acceptance

- Vectorized core, independent hand examples and scalar parity for all modes,
  negative rates/irregular times/zero sigma/underflow and prefix causality.
- Hand-worked metrics/paired bootstrap tests. Identical-case comparisons exactly0;
  shared-ID permutation invariance, fixed-premium decomposition, no global RNG.
- Actual runner CLI/strict config/integrity/no-overwrite/reproducibility tests.
- Full fixed experiment, figures, all raw rows and bootstrap statistic arrays,
  independent recomputation, extracted-source replay and fresh code review.
- Thai results guide and realistic-use assessment: suitable for model experiments,
  not yet validated for corporate production or allocating user's portfolio.
  Identify actual gaps (market quotes/vol surface, contract mechanics, multiasset
  exposures, dividends, gaps/liquidity, spreads/fees/funding/margin, historical/
  forward paper validation, operational controls). Cite current primary sources.
- Ask market/instrument/goal information early without blocking model work.
- Original outputs unchanged; no parent Git mutations or new dependencies.
