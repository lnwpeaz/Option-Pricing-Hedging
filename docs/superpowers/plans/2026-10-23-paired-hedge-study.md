# Paired Hedge Study Implementation Plan

> Implement inline with executing-plans/test-driven-development; one fresh final
> review under requesting-code-review. User authorized the already specified stage.

**Goal:** Measured paired hedge results plus honest practical-use boundaries.
**Architecture:** vectorized path accounting → paired statistics → dedicated runner/report.
**Tech Stack:** existing Python/NumPy/SciPy/matplotlib/pytest, no new dependencies.
**Spec:** docs/superpowers/specs/2026-10-23-paired-hedge-study-design.md; RESEARCH_SPEC.md.

## Global constraints

One short call/no dividends/model-priced premium; no expiry rebalance, all stock
costs and same-rate cash funding. Identical path IDs for every scenario. All cases
retained. Scalar ledger is reference. No market/live-performance inference.

## Review focus

- Vectorized cancellation/underflow must match supported scalar accounting domain.
- Shared path bootstrap must preserve covariance and premium adjustments.
- Rebalance timing, actual dt and borrowing diagnostics must include hold/expiry events.
- Volatility comparisons must separate premium changes from hedge-policy changes.
- Numerical precision/Monte Carlo CI cannot be mistaken for model realism or broker margin.

## Task1: vectorized path engine

Files: hedging/batch.py, tests/test_batch_hedge.py.
Consumes: OptionSpec, scalar ledger semantics; produces BatchHedgeResult and
hedge_paths(spec,*,times,paths,rebalance_every_steps,one_way_cost_bps), unhedged_paths.
- [x] Write tests: hand path sigma/r0 gives P&L−40.48/cost.48; all18 mode combinations
  agree with scalar records; irregular/negative-rate/zero-sigma/underflow/range cases.
- [x] Run focused pytest, expect missing batch module failures.
- [x] Implement vectorized date loop, ndtr delta, compensated cash sum, strict guards,
  immutable summary arrays, costs/funding diagnostics and no RNG.
- [x] Focused/full suite pass; record outputs.

## Task2: ensemble metrics and paired uncertainty

Files: analysis/metrics.py, tests/test_hedge_metrics.py.
Consumes: per-case arrays/metadata. Produces summarize and summarize_study returning
metric rows, comparison rows, bootstrap statistics and labels.
- [x] Write tests with hand P&L[−2,0,2,2]:mean.5,RMSEsqrt3,SDsqrt(11/3),
  negative-probability.25; identical pairs yield zero difference intervals; fixed
  shifts/premium decomposition and currency scaling remain correct.
- [x] Run focused pytest, expect absent API failures.
- [x] Implement scaled moments and common path-ID bootstrap; share resamples across
  all cases/bases, preserve pointwise labels and Wilson probability intervals.
- [x] Focused/full suite pass with actual hand expectations.

## Task3: executed paired runner and research/practical-use report

Files: experiments/runner.py, configs/hedge_study.toml, analysis/plots.py,
tests/test_experiment.py, learning/current-status docs, milestone5 run/verification.
Consumes Task1/2 contracts plus existing GBM/scalar/provenance.
- [x] Write real CLI/config/output/parity/reproducibility/no-overwrite tests.
- [x] Run focused pytest, expect absent runner functions.
- [x] Implement dedicated strict config,21cases/42metric cells/102pair rows,
  raw paths/results/bootstrap data/representative ledger/scalar parity/figures/report.
- [x] Independent final review; important findings get RED regressions/minimal fixes.
- [x] Execute full fixed experiment, inspect figures, independently recompute metrics,
  source replay, artifact integrity and final strict suite.
- [x] Thai measured-results guide and readiness assessment with current primary sources;
  update scope/progress. No claim that simulation alone certifies corporate/live use.

## Execution ledger / preflight

- Existing research spec and explicit continuation authorize this stage without
  repeated approval. Portfolio instrument/goal questions sent asynchronously.
- Work in existing source directory; unrelated parent /Users/robot Git unchanged.
  Git-dependent skill scripts/commits/worktrees do not apply to this project folder.
- Task1→Task2: result arrays → aligned per-case vectors, same path order required.
- Task2→Task3: shared bootstrap labels/CI fields → CSV/plots, model/common bases explicit.
- Task1→Task3: first16 fixed scalar checks and representative ledger validate batching.
- Fresh baseline332 strict tests passed in21.22s.
- Firecrawl CLI unauthenticated; use built-in web fallback for current primary sources.
- Task1:36 tests RED for absent batch module→36 GREEN; strict suite368 passed in21.90s.
  One synthetic zero-sigma fixture price was moved off a deterministic kink before
  engine implementation, preserving the test's intended currency-scaling question.
- Task2:9 hand/bootstrap/input tests RED for absent metrics APIs→9 GREEN.
- Task3:13 actual runner tests RED for absent run_study. An interim whole-suite
  run was deliberately still red while those new feature tests awaited implementation.
- Long-only US-stock/ETF portfolios have a distinct risk-reduction objective;
  personal holdings are omitted from the public project documentation.
  Ruling: finish the authorized short-call study and explicitly distinguish its
  results from their portfolio protection; do not fabricate weights/correlation or
  recommend trades. Cost: portfolio-specific sizing remains a subsequent project.
- Task3 runner:13 tests now GREEN. Whole strict suite390 passed in23.66s.
- Full preliminary run:10000paths/252intervals,210000raw rows,42metrics,102pairs,
  1000bootstrap repeats,336scalar comparisons. Max money difference7.96e-13.
- Final fresh review:58 targeted tests passed; independent shared-ID bootstrap
  recomputation/batch-size invariance verified. No Important/Critical findings.
- Final: minor(deferred optimization): matrix-wide input validation uses O(NM)
  boolean workspace; date-loop O(N) remains accurate. Clarified all memory claims
  rather than claiming full O(N) extra memory. Default boolean temporary~2.53MB.
- Final: minor presentation clarified: reference-sigma title no longer implies
  it equals true sigma in every custom config; daily/weekly description explicitly
  scoped to default252steps/year. No calculation behavior changed.
- Final: Ruling: pending full-run/replay/docs are parent-owned acceptance items,
  completed below; not waived. Real-market effectiveness/production remain
  unsupported, and explicit numerical range errors bound floating-input support.

- Final verification:390strict tests passed in24.32s; final example completed and
 all18artifact hashes/current-source alignment verified.11numerical artifacts
 matched bytes in actual isolated archived-source full replay.
- Independent raw checks:42metric cells/102contrasts and allCI endpoints, first16
 shared bootstrap samples,21complete aligned path-ID sets, cost-financing and
 premium identities, and three initial premiums versus independent quadrature.
- Verification-tool correction: Pandas cross-scenario row labels initially caused
 misalignment; checked explicit path-ID ordering/reset indices before comparison.
 This was a checker failure, not a mutation to experiments or claims.
- Current scope/practical-use/Thai results docs complete; canonical figures inspected.
- Ruling: Long/short-option question is fit-for-purpose clarification, not permission
 to invent live quotes/weights or execute trades. Preserve audited research scope,
 explain protective-put/covered-call distinctions with primary sources, and keep
 actual long-portfolio risk adaptation a separately validated extension.
- Complete. No unresolved Important/Critical findings. Deferred minor: bounded-block
 input validation memory optimization; current O(NM)validation cost disclosed.
