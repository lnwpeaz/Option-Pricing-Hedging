# Research Quality Implementation Plan

> Execute inline using test-driven-development; user authorized improvements.

**Goal:** Independent multi-regime evidence, recoverable experiment sources and an honest audit.
**Architecture:** standalone payoff integration + validation runner + shared provenance utilities.
**Spec:** docs/superpowers/specs/2026-10-21-research-quality-design.md.
**Stack:** Existing NumPy/SciPy/matplotlib/pytest, Python zipfile/hashlib; no new dependencies.

## Review focus

- Quadrature tails must be bounded and kink handled without analytic-price reuse.
- Rare-payoff zero SEs must remain visible; underflowed RMSE must not imply perfect accuracy.
- Every grid scenario and independent seed is retained; paired/independent units stay explicit.
- Hashes alone cannot restore source; verifier must read archive contents and replay must use them.
- Old examples must not be rewritten to imply unavailable source provenance.

## Task 1: Source snapshots and integrity verification

- [x] Write failing snapshot/content/tamper/real replay tests.
- [x] Implement deterministic ZIP with source/config/dependencies/replay metadata and optional checkout files.
- [x] Implement verifier CLI; integrate new snapshot+artifact manifests into four existing demos.
- [x] Run strict suite and actual isolated-source replay test.

## Task 2: Independent reference and broad numerical validation

- [x] Write failing known-integral/reference/CLI/grid/rare-payoff tests.
- [x] Implement finite normal-payoff quadrature plus explicit tail bound.
- [x] Implement dedicated144-scenario config, all CRR grid rows and32-repeat MC diagnostics.
- [x] Save raw/summary data, uncertainty, figures, report and source snapshot; run full experiment.

## Task 3: Audit, independent review and close-out

- [x] Incorporate audit reviewer findings without feature bloat.
- [x] Write Thai stage-by-stage quality report and update scope/progress/commands.
- [x] Inspect figures, verify full run and test replay of archived source.
- [x] Run strict full suite, request/recheck code review and report measured findings plus remaining work.

## Execution record

- Existing source folder has no own Git history; parent /Users/robot Git remains untouched.
- Read-only external review requested for quality/claim assessment.
- Fresh baseline strict tests started; improvements do not implement the hedge ledger yet.

- Completed source archives/integrity verifier and integrated five demos (four existing plus validation).
- Baseline241 strict tests; final273 strict tests passed in36.36s.
- Full declared grid completed:144 references/432 CRR/13824 MC/432 metrics; maximum independent difference1.563194e-13 below1e-7.
- Independent reviewer checked initial design and focused implementation; label, near-coincident integration splits and failure-plot visibility fixed with regressions.
- Recomputed all432 MC metric cells independently; verified unique seeds, scenario joins and artifact integrity.
- Actual full replay used recovered source in a separate directory and matched four CSVs plus summary bytes; proof in reports/verification/research-validation-replay.json.
- Two final figures inspected; Thai audit, reproducibility guide, README/interfaces/roadmap/progress updated.
- Scope complete; hedge ledger and paired research remain explicitly next. Parent Git untouched.
