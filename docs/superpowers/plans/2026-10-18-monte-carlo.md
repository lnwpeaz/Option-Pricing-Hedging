# Monte Carlo Implementation Plan

> Execute inline using executing-plans and test-driven-development; preserve a progress ledger.

**Goal:** Build and measure a statistically correct, memory-bounded Monte Carlo lab.
**Architecture:** Terminal GBM transform → batched estimators → experiment runner → figures/report.
**Tech Stack:** Existing Python, NumPy, SciPy, matplotlib and pytest; no new dependencies.
**Spec:** `docs/superpowers/specs/2026-10-18-monte-carlo-design.md`.

## Global constraints

- European call/put; no dividends; risk-neutral drift r for pricing.
- No global random state, silent clipping, or analytic option prices in estimators.
- Confidence intervals are approximate normal 95%; antithetic observations are pairs.
- Control pilot is independent of production and counted as additional cost.
- Existing output folders are refused. Save exact inputs, source and artifact hashes.

## Review focus

1. Antithetic covariance changes the SE; treating paths as independent understates it.
2. Same-sample beta fitting can bias estimates; a pilot must be separate.
3. Large drift/volatility can overflow or underflow; never emit misleading finite prices.
4. Timing comparisons must include identical work and label excluded costs.
5. Reproducibility applies to numerical output in a fixed environment, not wall time.

## Task 1: Core pricing and uncertainty

Files: contracts.py, simulation/gbm.py, pricing/monte_carlo.py, tests/test_monte_carlo.py.
Produces `terminal_from_normals(*, spot, drift, volatility, maturity_years, normals)`
and `price(spec, *, n_paths, rng, method='plain', batch_size=65536, pilot_paths=1024)`.

- [x] Add tests with supplied normals and independent literal/NumPy payoff expectations;
  check unbiased sample SE, pair-level SE, independent pilot beta and path counts.
- [x] Run `.venv/bin/python -m pytest tests/test_monte_carlo.py -q`; expect missing API failures.
- [x] Implement frozen estimate, validated terminal transform, central-moment merge,
  vectorized batching and deterministic limits. Check all numeric outputs are finite.
- [x] Run full pytest; add repeated-seed RMSE and coverage diagnostics with broad tolerances.

## Task 2: Reproducible experiment and engineering benchmark

Files: experiments/monte_carlo_demo.py, experiments/mc_benchmarks.py,
analysis/mc_plots.py, configs/monte_carlo.toml, tests/test_monte_carlo_demo.py.
Consumes Task 1 API; produces `run_demo(config_path: Path, output_dir: Path) -> Path`.

- [x] Test real CLI output, exact config, artifact/source hashes, deterministic numerical
  reruns, invalid settings, no overwrite and kernel agreement before implementation.
- [x] Run new tests; expect missing demo/benchmark APIs.
- [x] Implement repeated-seed rows; aggregate RMSE/bias/SE/coverage Wilson intervals,
  runtime and work counts. Compare independent seeds rather than one lucky estimate.
- [x] Implement scalar/vector kernels with identical normals, warm-up and alternating
  timing order; separate allocation pass from end-to-end batch timing pass.
- [x] Save raw and aggregated CSVs, summary/manifest, figures and English RESULTS.md.
- [x] Run the entire suite and actual full experiment.

## Task 3: Interpretation, documentation and review

Files: docs/MONTE_CARLO_TH.md, README.md, docs/PROGRESS.md, docs/INTERFACES.md,
docs/ROADMAP_TH.md, docs/RESEARCH_SPEC.md, reports/examples/milestone-2b/.

- [x] Inspect every generated figure; fix overlap/clipping if found.
- [x] Explain formulas, statistical unit, pilot fit, O(N)/O(B), variance-vs-speed,
  seed stream construction and benchmark limitations, with primary references.
- [x] Update implemented-vs-planned status and include only measured results.
- [x] Review statistical validity, numeric edge cases, configuration handling and artifact integrity.
- [x] Run full pytest and final example consistency checks; report findings and limits.

## Execution record

Progress is recorded in `docs/superpowers/plans/2026-10-18-monte-carlo-progress.md`.
The project folder has no own Git repository; Git resolves to an unrelated home
directory repository with no commits. Work in the explicitly provided project
directory; do not initialize/mutate that parent repository or use worktree scripts.
