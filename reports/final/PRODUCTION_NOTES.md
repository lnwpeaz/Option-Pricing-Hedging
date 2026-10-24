# Final report production record - 23 October 2026

Purpose: complete the existing option-pricing/hedging research project and make
its supported use cases concrete. The user explicitly wants a distinct profile
project, without duplicating Portfolio Quantitative Research, and usable or
extendable model outputs. No portfolio allocation subsystem is being added.

Existing authority: docs/RESEARCH_SPEC.md and docs/ROADMAP_TH.md milestone 6:
an English 8-12-page research report and a short demonstration.

Deliverables:
- [x] An English PDF and matching editable Markdown with Monte Carlo as a major
  component; measured accuracy, uncertainty, runtime/memory and hedge results.
- [x] A second predeclared hypothetical contract, executed through the existing
  pricing and hedge interfaces, with saved config/data/figures/manifests.
- [x] A Thai worked example and short presentation/demo script explaining what
  the outputs support, what requires market extensions, and the next useful scope.
- [x] Reconcile report numbers with original artifacts; render and visually
  inspect every PDF page; update current status documents without rewriting history.

Fresh baseline: full suite 390 passed in 23.37s with warnings as errors.
Milestone-2B / research-validation / milestone-4 / milestone-5 artifact hashes
verified. The older milestone-2B source is hash-only and not recoverable from its
record; later validation and hedge source snapshots are recoverable.

Ruling: these are report/example artifacts using existing APIs, not a new pricing
or portfolio engine. No product code changes or redundant implementation tests
are needed. Numerical cross-checks, artifact verification, replay of the new use
case and PDF visual QA are the relevant acceptance evidence.

Ruling: the second example changes spot, strike, tenor, volatility, drift and cost
grid and is explicitly hypothetical. It cannot be presented as a real market
quote or evidence of a trading edge. Its configuration was saved before running.

Ruling: this folder is not an independent Git repository (earlier project audit).
Do not create commits or worktrees in the unrelated parent home-directory repo.
Keep the production record and verified local artifacts instead.

Completion evidence:
- Final English report has 12 pages; matching Markdown uses the same build source.
  Four main pages cover Monte Carlo methodology, accuracy, engineering and stress
  validation. Full primary scenario grid and paired frequency intervals retained.
- New contract: analytic pricing/Greeks; MC1728estimates in54cells; hedge63000rows
  in21cases. All24pricing/hedge and13MC declared artifacts verified, with recovered
  source available for all three new runs.
- Both hedge datasets independently checked from raw path results:84metric cells,
  204paired rows, saved bootstrap endpoints, financed costs and price integrals.
  New MC point metrics independently recomputed from all1728raw estimates.
- Trusted new pricing/hedge sources extracted, imported from recovered src and
  actually executed via CLI; all14selected numerical artifacts matched bytes.
  Proof: reports/verification/contract-review-replay.json. MC timing not replayed.
- All12PDF pages rendered and inspected in contact sheets; changed/dense pages
  2,9,10,11 also inspected individually. No clipping/overlap or glyph defects seen.
  Automated checks enforce chapter/page count, text bounds, glyph checks and hashes.
- A copied multiline reproduction command initially contained literal leading
  plus signs from authoring. Removed before delivery; final PDF/Markdown checked.
- No pricing/hedging source or production tests changed. The earlier fresh390-test
  strict baseline remains applicable. No cross-platform or live-trading claim.
