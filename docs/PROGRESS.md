# Development progress and verification

Current scope: analytic pricing/Greeks, CRR pricing/convergence and the Monte Carlo
research lab are implemented. MC is the computational centerpiece. Exact terminal
and full-path GBM with reusable data are implemented. The self-financing one-path
hedge ledger/demo and paired model-based hedge research are implemented. The final
English report and worked demonstration complete the six original milestones.
See reports/final/ and docs/USE_CASE_TH.md. Real-market/personal-portfolio effectiveness is not
validated. Earlier milestone evidence is historical. V2-A Asian MC/RQMC is now implemented and executed; see the V2-A section below.

## Milestone 1

Implemented: validated frozen OptionSpec; Black-Scholes European call/put pricing;
delta/gamma/vega; analytic pricing demo with CSV, PNG, config bytes and source/version manifest.
Scope: one underlying, no dividends, continuous constant rates; no hedge performance yet.

## Evidence

- Wrote numerical tests before implementation: first run 51 failed because the API did not exist.
- Implemented the analytic API: 51 passed.
- Added actual demo CLI tests before implementation: 2 failed because the module did not exist.
- Implemented CLI, output generation and no-overwrite behavior: 53 passed.
- Independent read-only review found tiny-volatility NaN/overflow and intermediate discount overflow.
- Added five regression cases: 5 failed, 51 passed before fixes.
- Fixed log-CDF underflow, density squaring and representable discounting; preserved exact zero-rate
  strike handling after a kink regression was caught by the existing suite.
- Final whole suite: `.venv/bin/python -m pytest -q --tb=short` -> **58 passed**.
- Demo executed: `PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.pricing_demo
  --output-dir reports/examples/milestone-1`.
- Generated PNG visually inspected for labels, clipping, units and baseline values.

Recorded environment: Python 3.13/macOS, dependency versions in requirements-lock.txt;
exact demo versions and source SHA-256 hashes in reports/examples/milestone-1/manifest.json.
Dependency installation completed using pip's isolated build. A no-build-isolation install
attempt failed because the build backend was absent from the environment; that mode is not
the documented installation path.

## Environment note

The editable installation's .pth file was marked hidden by the local file environment.
Python 3.13 skipped it on subsequent invocations, causing import failures. Source-checkout
commands now explicitly set `PYTHONPATH=src`; pytest also declares its src path in pyproject.toml.
CLI integration tests use that same source path. No global Python settings were changed.

## Research interpretation

For S=K=100, T=1, r=.05, sigma=.20:

| Value | Result |
|---|---:|
| Call | 10.4505835722 |
| Put | 5.5735260223 |
| Call delta | 0.6368306512 |
| Put delta | -0.3631693488 |
| Gamma | 0.01876201735 |
| Vega per +1 percentage point of volatility | 0.3752403469 |

These are model prices and local sensitivities. They are not observed quotes, expected
investment returns or evidence of hedge effectiveness. General extreme floating-point input
coverage is not exhaustive; the research baseline and recorded edge cases are validated.

## Milestone 2A: CRR binomial pricing and convergence

- Wrote 33 CRR tests before implementation; all failed because binomial.price was absent.
- Added real backward induction with O(N^2) time/O(N) memory, stable expm1 probability,
  near-strike payoff calculation, deterministic limits and explicit range errors.
- Full suite then passed 91 tests.
- Wrote 10 convergence CLI/config/output tests before implementation; all failed because
  the new module did not exist. Implemented the demo; whole suite passed 101 tests.
- Independent review found a valid interior probability underflowing to zero and silently
  erasing a material one-step call value. Reproduced this and probability rounding to one
  with two failing regression tests; both cases now raise explicit ValueError.
- Final whole-suite result: **103 passed**, including the prior 58 milestone-1 tests.
- Baseline CRR grid includes adjacent odd/even counts up to 1001. At 1001 steps, call is
  approximately 10.4523346903 and put 5.5752771404; absolute errors are approximately
  0.0017511181 versus the analytic reference for each kind.
- Outputs: convergence.csv, summary.json, convergence.png, exact input and source/version manifest.
- Final example: reports/examples/milestone-2a/. Older examples retain their original manifests.
- CRR has no dependency on the analytic pricing function. The demo uses it as a benchmark.
- Grid errors are not assumed monotonic; elapsed times are single illustrative measurements.

Decisions: reject interior probability values that collapse to 0 or 1 in floating point,
while allowing true endpoint probabilities. Reject terminal-node overflow explicitly.
The cost is that some extreme configurations require a different grid or future log-space
implementation; the API returns no misleading premium for those cases.

## Milestone 2B: Monte Carlo and Computer Engineering

Implemented three statistically distinct estimators: plain MC, antithetic pair means,
and a discounted-stock control variate with independent pilot beta fitting. Returns
price, sample SE, approximate normal 95% CI and explicit production/independent/pilot
counts. Exact terminal risk-neutral GBM avoids time-grid bias for European payoffs.

Engineering: NumPy vectorization, O(N + pilot) runtime, O(batch size) workspace,
merged central moments in spot units, explicit PCG64 streams, repeated scalar/vector
kernel timings and complete batch timing/allocation measurements. NumPy build/BLAS,
platform, thread environment, config, source and artifact hashes are recorded.

Evidence:

- Fresh pre-implementation baseline: 103 passed.
- Core RED: 32 failing tests because the pricing/terminal APIs were absent.
- First green full suite: 135 passed.
- Experiment RED: 17 failed because demo and benchmark APIs were absent.
- Demo/CLI implemented; initial full suite: 162 passed.
- Independent read-only review found zero-RMSE baseline report formatting and
  false zero SE caused by tiny squared currency values. Added failing regressions,
  fixed n/a reporting and normalized moments. Exact-expiry ATM regression also fixed.
- Follow-up review found intermediate normalization erasing finite discounted
  payoffs and singleton-batch merge variance underflow. Both reproduced with failing
  tests and fixed by discounting before normalization and explicit underflow guards.
- Independent review rechecked all four findings; no remaining actionable findings
  in its review scope. Final whole suite with warnings treated as errors: **171 passed**.
- Actual full experiment: **5,760 estimates**, **90 metric cells**, 64 independent
  repeats per cell, both call/put, strikes 80/100/120, five sample sizes 1024..262144.
- Every aggregate RMSE recomputed from raw rows; config, 21 source hashes and 13
  output hashes verified. Four figures inspected; kernel annotation moved to avoid overlap.

At baseline K=100 and N=262144, empirical RMSE across 64 runs:

| Method | Call RMSE | Put RMSE |
|---|---:|---:|
| Plain | 0.03074841 | 0.01585143 |
| Antithetic | 0.02020726 | 0.01206729 |
| Independent-pilot stock control | 0.00974821 | 0.00953583 |

Control uses 2048 additional pilot samples; at this N its work-normalized MSE gain
is about 9.87x for call and 2.74x for put. This is empirical, not a guarantee, and
the benefit differs across strikes. Call/put log-RMSE slopes are near -0.5 over
the recorded grid. Benchmark timings are machine/run dependent; read the executed
RESULTS.md for the actual measurements and their boundaries.

Outputs: reports/examples/milestone-2b/; learning guide: docs/MONTE_CARLO_TH.md.
Normal CIs and bootstrap intervals are approximate; zero observed sample variance
does not prove accuracy. Kernel-only speedup is distinct from complete estimator
performance. These outputs describe modeled prices, not hedge or trading results.

## Milestone 3: full GBM paths and paired measure diagnostics

Implemented `simulate_paths` with explicit drift, exact log increments, irregular
time grids, local RNG and path-major batching. Returned float64 shape is
(n_paths, len(times)); initial spot is exact, prices are finite/positive, and zero
volatility/[0] consume no random samples. The existing terminal MC API is preserved.
`make_time_grid` retains regular k/frequency points and exact expiry, including a
possible shorter final interval. No real-market calendar is implied.

Evidence:

- Fresh strict baseline: **171 passed**.
- Wrote core tests first: **45 failed** because APIs were absent; after implementation,
  all 45 passed and the whole existing+core suite passed 216 tests.
- Wrote 18 actual CLI/output/config/reproducibility tests before the demo; all failed
  because the module was absent. Implemented demo; all 18 passed.
- Reproduced mixed-bool time coercion and squared tiny-currency SD/SE underflow with
  three failing regressions. Rejected mixed bools and scaled/centered moments before reduction.
- Added six hand-worked price and independent-repeat statistic cases across scales
  1, 1e-170 and 1e150. Independent review also identified missing saved log-return
  diagnostics; observed/theoretical log means/variances are now in time/repeat CSVs
  and summary/report, with saved-data comparisons in the demo tests.
- Independent reviewer rechecked fixes: **70 targeted tests passed with warnings as errors**;
  no unresolved actionable findings in its scope. Full strict suite: **241 passed**.

Executed baseline: 10,000 physical paths, 253 times / 252 intervals; paired RN paths
use identical Brownian shocks. Physical `paths.npy` data is 20,240,000 bytes
(19.302 MiB); demo holds both measures, 38.605 MiB of matrix data. Reused float
batch buffer at B=512 is 1,032,192 bytes; these are array sizes, not total RSS.
Work is O(N*M), returned storage O(N*M), temporary simulation workspace O(B*M).

Main physical terminal mean is 107.93855 versus theoretical 108.32871; main RN
discounted mean is 99.63984 versus 100, with sample SE 0.20094. The separate
32-repeat experiment (2,000 paths per measure/repeat) gives discounted RN ensemble
mean 100.00939 and approximate 95% interval [99.85907, 100.15970]. All repeats are
retained. Log-return ensemble means/variances also agree within the reported
sampling uncertainty. These are model checks, not historical forecast validation.

Outputs: reports/examples/milestone-3/, with physical paths.npy/times.npy, fixed-ID
preview CSV, paired terminal CSV, time/validation statistics, two figures, RESULTS.md,
exact/effective config and manifest. Thai guide: docs/GBM_PATHS_TH.md. Fan quantiles
describe dispersion across paths; separate mean CIs are pointwise approximations.
No hedge, transaction costs or trading performance have been simulated in this milestone.

## Next milestone

Self-financing short-call hedge ledger, then paired hedge experiments and the final
cross-milestone research report. Optional MC extensions after the measured CPU
reference include randomized QMC and explicit CPU/GPU parallelism.

## Completed-stage quality audit — 21 October 2026

User authorized a whole-project assessment and strengthening of weak completed
stages, with Monte Carlo remaining central. A read-only review found substantive
existing pricing/MC/path work, but published pricing regimes were narrow and old
source hashes could identify rather than recover source bytes. The hedge ledger
and paired hedge research remain the main unfinished deliverables.

Implemented:

- Standalone discounted-payoff quadrature, independent of production pricers/GBM,
  with estimated integration error and a separate bounded omitted tail.
- Predeclared 144-scenario audit over T/volatility/strike/rate/call-put; 432 CRR rows,
  13,824 MC estimates and 432 uncertainty metric cells. All results retained.
- Actual source/config ZIP snapshots for all five demos, manifest written last,
  artifact/source integrity verifier and extracted-source replay tests.
- Thai quality assessment in PROJECT_AUDIT_TH.md, reproducibility boundaries in
  REPRODUCIBILITY.md, and explicitly planned hedge modules in the repository map.

Verification evidence:

- Fresh pre-change strict baseline: **241 passed**.
- Provenance tests first failed six times for absent APIs, then passed. Independent
  reference and validation-demo tests likewise failed before their implementations.
- Full-grid execution exposed two near-coincident payoff-kink/density-center splits
  that made QUADPACK reject nearly zero-width intervals. Two failing regressions
  preceded the fix; redundant splits are merged without dropping integration domain.
- Independent review corrected an overstrong `roundoff_limited` label. A failing
  regression preceded `below_diagnostic_floor`; small genuine uncertainty is allowed.
- Review also found a fixed plot limit could hide future failed reference checks.
  A failing plot regression preceded the dynamic upper bound fix.
- Hand-worked stress metrics validated at currency scales 1, 1e-170 and 1e150.
- Reviewer rechecked **28 focused tests with warnings as errors**; the final plot
  finding was then fixed and verified. No unresolved important review findings.
- Final whole-suite `.venv/bin/python -m pytest -q --tb=short -W error`:
  **273 passed in 36.36 seconds**.
- Actual full CLI run with warnings as errors completed under
  reports/examples/research-validation/. Both figures visually inspected.
- All 432 MC metric cells independently recomputed from raw rows for RMSE, RMS SE,
  coverage, zero SEs and uncovered above-floor errors; all scenario parameter joins
  and 13,824 unique seed keys checked.
- Exact config and all declared artifact hashes checked for the four historical
  examples and new validation run. Historical first/2A examples lack output hashes;
  the verifier reports those checks unavailable, rather than passing them.
- Extracted the trusted new source ZIP into reports/runs/quality-source-replay/.
  Confirmed the imported package came from extracted src, then executed the full
  validation CLI using the current recorded interpreter/dependencies. All four CSVs
  and summary.json matched original bytes. Both run manifests/archives verified.
  Proof: reports/verification/research-validation-replay.json. This demonstrates
  source recovery/current-environment replay, not cross-platform environment recovery.

Measured results:

- All 144 analytic/reference comparisons pass the predeclared 1e-7 absolute tolerance;
  maximum difference **1.563194e-13**. Maximum quadrature error estimate 6.288758e-11;
  maximum omitted-tail bound 4.532967e-31. These bounds are distinct quantities.
- CRR median absolute errors at 32/128/512 steps: 0.01091184/0.00206591/0.00091446.
  No rejected grids in this matrix; convergence need not be monotone per scenario.
- **74/432** method/scenario cells contain at least one zero-SE repeat. For plain MC
  on put S100/K70/T.25/r-.02/sigma.2 (scenario49), 8/32 estimates have SE0; nominal95%
  CI coverage is18/32, with Wilson interval approximately [.3933,.7183]. Reference
  premium .0004583258. This is meaningful evidence of rare-payoff CI limitations.
- Twenty control cells fall below the declared absolute SE diagnostic floor; this
  classification does not prove roundoff and does not change raw CI/coverage.

The audit is complete. Next substantive work remains the self-financing ledger,
paired hedge frequency/cost/misspecification study and final research report.


## Milestone4: self-financing hedge accounting —23 October2026

Implemented frozen HedgeRow/HedgeResult, pure hedge_path and unhedged_path APIs,
short one European call with model premium/delta, actual-interval cash accrual,
opening/rebalance/liquidation costs, no expiry delta trade and cash payoff settlement.
No extra investor cash enters after the premium; negative cash records borrowing
at the same continuous r. Frequency counts grid indices, not a market calendar.
Terminal P&L is signed profit for the short-call hedger. Intermediate assets_value
excludes the outstanding option liability. Financed costs are diagnostic only,
already included in cash, never an additional P&L deduction.

Dedicated hedge_ledger.toml/hedge_demo uses one explicit path, retains every cash
flow in two ledgers, checks zero-cost versus financed-cost identity, and writes
path/check CSVs, summary, four-panel figure/report, exact config and source snapshot.
This milestone is accounting validation, not an ensemble effectiveness study.

Evidence:

- Fresh strict baseline:273 passed in28.22s.
- Wrote40 core cases first, all failed for absent ledger APIs. Implemented records
  and accounting; all40 passed. Whole strict suite313 passed in29.27s.
- Wrote15 real-CLI/demo/config/integrity cases first, all failed for absent demo.
  Implemented demo/plot/config; all15 passed; whole strict suite328 passed in30.19s.
- Independent fresh-context read-only review ran55 focused tests and found two
  Important numerical defects: rounded intrinsic payoff inventing P&L at huge
  S_T/K ratios, and underflowed trade notional bypassing nonzero-cost checks.
- Reproduced both with four failing regressions: terminal1e18/1e20 in a sigma0
  unit-delta hedge, and tiny share notional at cost rates10/1e300bps. Fixed by
  explicit supported-range errors, not compensating artificial cash injections.
  Reject payoff subtraction residual exceeding64 ULPs of strike, and nonzero
  trade times spot underflowing to0. Targeted59 tests then passed in9.30s.
- Final whole strict suite with writable temporary plotting caches:
  `.venv/bin/python -m pytest -q --tb=short -W error` → **332 passed in22.88s**.
  No unresolved Important/Critical review findings; no deferred Minor findings.
- Actual strict CLI completed at reports/examples/milestone-4/; ledger.png inspected
  for timing, units, clipping and clear distinction between cash and net wealth.
- Verified all10 declared artifact hashes, exact config and archived source bytes.
  Checked current package hashes agree with the example's captured package.
- Independently recomputed every row and the whole-horizon compounded cash flows
  using Decimal precision60. Maximum row difference1.03e-14, total P&L difference
  2.15e-14, and financed-cost difference4.22e-18, all below1e-10 currency units.
- Extracted trusted captured source into reports/runs/hedge-source-replay/, confirmed
  package imports from recovered src, then ran the real CLI with current recorded
  dependencies. All four CSVs and summary.json matched original bytes. Original
  and replay integrity verified. Proof: reports/verification/milestone-4-replay.json.
- Thai worked explanation: docs/HEDGING_TH.md; scope/architecture/interfaces/roadmap
  and reproducibility docs updated. Earlier examples remain unchanged.

Illustrative result, not a strategy ranking: S=K100,T1,r.05,model sigma.2,
path100→108→96→112→105 at0/.25/.5/.75/1, every-step hedge with5bps costs.
Premium10.45058357, payoff5, hedged terminal P&L−0.62801058, zero-cost hedge
P&L−0.50133404, unhedged P&L+5.98639645. Nominal costs.12411606; financed
costs.12667653 exactly explain the hedge P&L difference within rounding.
The same-premium one-path unhedged outcome cannot rank aggregate risk reduction.

Next: predeclared paired physical-GBM hedge study across every1/5 steps,
costs0/5/10bps and hedge sigma15%/20%/25%, with pathwise uncertainty and unhedged
baselines. Model sigma also changes premium; report that decomposition. Then the
final cross-milestone English report. No real-market or universal-input claim.


## Milestone5: paired Monte Carlo hedge study —23 October2026

Implemented vectorized date-wise accounting audited against the scalar ledger,
scaled path statistics, shared-ID bootstrap,21case runner, dual premium bases,
all path outcomes/uncertainty/figures and source recovery. Same physical paths are
used across18hedge policies(2frequencies*3costs*3model sigmas) and3unhedged cases.
Model sigma sets premium and delta; common-reference P&L applies the deterministic
funded premium shift. Funding fields retain explicit model-premium meaning.

Evidence:

- Fresh baseline332 strict tests passed in21.22s.
-36batch tests first failed for absent module; after engine implementation all36
 passed. Whole strict suite368 passed in21.90s. One zero-sigma test fixture was
 corrected off its unintended Greek kink before implementation.
-9hand metrics/bootstrap tests first failed for absent APIs; then all9passed.
-13real runner/config/integrity/reproducibility tests first failed for absent
 run_study, then passed. Interim whole suite was13failed/377passed while these
 new feature tests awaited implementation; no earlier-test failure was hidden.
- Fresh independent reviewer ran58 targeted tests with warnings as errors,
 independently recomputed shared bootstrap samples and confirmed batch-size
 invariance. No Important/Critical findings. Minor memory/presentation claims
 clarified: O(N)date-loop workspace excludes matrix-sized validation booleans;
 reference-sigma labels and default-grid calendar approximations are explicit.
 Validation-memory optimization remains deferred, not a hidden O(N)whole-pipeline claim.
- Final full strict suite:390passed in24.32s, warnings treated as errors.
- Actual strict full run: reports/examples/milestone-5/,10000paths*253time points,
 210000case/path outcomes,42metric cells,102paired comparison rows and1000shared
 path-bootstrap repeats. All18declared artifact hashes verified.
-336scalar/vector comparisons on predeclared first16paths across21cases; maximum
 monetary difference7.9581e-13 and share-turnover difference5.3291e-15, below
 1e-8currency/1e-10shares tolerances. Fixed representative ledger is pathID0/case7.
- Independently recomputed all42cells' mean/SD/RMSE/quantiles and loss probability,
 all saved metric CI endpoints, all102paired point estimates/CIs, first16bootstrap
 draws for every cell, premium decomposition and per-path financed-cost identities.
 Verified every case has all10000aligned unique path IDs. All three initial model
 premiums also checked against standalone payoff quadrature.
- An initial independent checker used Pandas CSV-row-label alignment across
 scenarios, producing mismatched shapes/NaNs; fixed checker to explicitly align
 verified path IDs. No experiment data or production code was changed for this.
- Captured source ZIP extracted to reports/runs/paired-source-replay/; verified
 imported package originates from recovered src, then ran full study with current
 recorded dependencies. Six CSVs, summary/bootstrap metadata and all three NPYs
 (11numerical artifacts) matched original bytes. Both manifests/archives verified.
 Proof: reports/verification/milestone-5-replay.json. No cross-platform claim.
- Final figures visually inspected. Thai findings docs/HEDGE_STUDY_TH.md and
 primary-source-backed practical assessment docs/PRACTICAL_USE_TH.md completed;
 current architecture/interfaces/roadmap/test/provenance/status docs updated.

Measured reference-sigma20% results at S=K100,T1,r.05,mu.08,true sigma.2:
- No hedge RMSE16.99733; every1/every5steps with no costs RMSE.43122/.94984.
- At5bps, every1/every5steps RMSE.54279/.97187; mean P&L−.30994/−.17139;
 mean financed cost.31736/.18155. Paired RMSEdifference−.42908 with pointwise95%
 bootstrap interval[−.44634,−.41135]. These are short-call replication amounts,
 not percentages of long-portfolio risk reduction.
- At every1step/5bps, sigma25%own-premium mean+1.68117 changes to−.30092 when
 premium is held equal to the reference. Apparent profit from assuming a higher
 opening receipt is not evidence that a market quote offers a trading edge.
- Model-premium mean peak cash borrowing for reference every1step/5bps is88.38674;
 this is not broker margin, collateral or an adequate initial-capital estimate.

User clarified long US-stock/ETF portfolios and then asked about long/short options.
Current tool can price European calls/puts and research short-call delta hedging;
long-portfolio protection, American assignment/dividends/quotes/margin and actual
long/short trading profitability are unvalidated. Current sources checked include
OCC/OIC contract/strategy guidance, FINRA assignment, NEOSSPYI and FedSR26-2(2026,
which supersedes SR11-7). Practical document cites exact primary URLs and avoids
claiming these institutional guidelines certify the project or apply universally.
No trades, broker connection, invented portfolio weights or allocation advice.

Original project next: final English report. Portfolio adaptation is a separate
multiasset long-risk layer with actual weights/data/costs/out-of-sample and forward
paper evaluation. This milestone answers the model-study question, not live fitness.

## Milestone 6: English report and executable application - 23 October 2026

The user clarified that this project should remain distinct from Portfolio
Quantitative Research and strengthen their financial/computational engineering
profile through usable, extendable model outputs. No portfolio allocation engine
or market trading capability was added.

Completed report: output/pdf/option_pricing_hedging_research_report.pdf, 12 pages,
with matching editable reports/final/research_report.md and a retained build source.
Monte Carlo methods/accuracy/efficiency/stress validation occupy four main pages;
the report also includes accounting, all21primary scenarios, paired intervals,
premium decomposition, source-replay boundaries and a second contract example.

New predeclared hypothetical contract: S120,K125,T.5,r.04,pricing sigma.25,q0.
The existing pricing API returned call7.3373559937, put9.8621901571 and Greeks.
Existing MC lab ran1728estimates over54cells with32independent repeats each.
At N65536,call RMSE plain/antithetic/control=.05976786/.03726069/.02725344;
control work-normalized gain4.73543 includes1024pilot evaluations.
Existing hedge runner used true scenario sigma.30,mu.06,3000paths,126intervals,
21cases,63000outcomes and500shared bootstrap repeats. All outputs are retained
in reports/examples/contract-review/ with separate pricing/monte-carlo/hedging runs.

The new use case demonstrates a meaningful risk distinction: at2bps,receiving
the25%-sigma premium and using30%-sigma every-one-step hedge yields observed
common-premium mean−1.8534768 and RMSE2.0373821. Improving the delta policy does
not supply an adequate premium; the example has no observed quote or trading edge.

Fresh baseline:390passed in23.37s with warnings treated as errors; core source
and tests were unchanged in this documentation/application milestone.
Read-only report QA recomputed every point metric and saved bootstrap endpoint
for both hedge studies, all204paired rows, path alignment, financed-cost identities
and independent-integral opening prices. Maximum numeric differences5.2792e-13
(primary) and3.6693e-13(new). New MC bias/RMSE/coverage independently recomputed
from all1728raw estimates. File/config/source integrity verified where available;
older milestone2B source remains hash-only. Proof: reports/verification/final-report-evidence.json.
New contract pricing/hedging archives were separately extracted into a new local
replay folder; imported package origins checked and both actual CLIs executed.
All14selected numerical artifacts matched bytes. Proof: reports/verification/contract-review-replay.json.
This does not include a replay of MC timing results or a cross-platform claim.

Thai worked application: docs/USE_CASE_TH.md. Five-minute demonstration and
interview questions: docs/DEMO_SCRIPT_TH.md. The report distinguishes numerical
accuracy, sampling uncertainty and external model validity. It is a completed
model-study deliverable, not corporate sign-off or live investment validation.

Proposed subsequent scope: contract-aware option-quote diagnostics and implied
volatility, with explicit supported styles, data quality, bounds and solver tests.
That scope is not implemented. American exercise/dividends, quote calibration,
funding/margin/execution and forward evaluation remain outside this version.

## V2 scope review - 24 October 2026

The user questioned whether the smaller q=0 quote/IV draft was the strongest next
scope, and asked to continue exploring a deeper project. Prepared
docs/PROJECT_V2_PROPOSAL_TH.md comparing the smaller IV tool, an MC/model-risk
research programme and a full US equity-options tool. Recommended the MC/model-risk
programme to preserve the user's stated Computer Engineering priority.

Written first-slice proposal: docs/superpowers/specs/2026-10-24-asian-rqmc-design.md.
It specifies path-dependent Asian pricing with plain/antithetic/geometric control,
scrambled Sobol increments and Sobol Brownian bridge. Independent units, counted
pilot/scramble work, reference uncertainty and external contract matching are explicit.
The proposed fixed study has2880macro estimates; no such results have been produced.

Later proposed slices are jump-risk hedging, contract-aware quotes/IV and market
case/packaging evidence. They have not been specified or implemented as approved
work. The original IV draft remains unapproved and is retained as the smaller
alternative/market-bridge candidate. No production code, dependencies or completed
v1 artifacts changed during this scope review. Await written-design review before
implementation planning under the applicable workflow.

## V2-A written-spec approval and implementation plan - 24 October 2026

User explicitly approved the Monte Carlo-focused written V2-A specification.
Recorded that approval in the spec and programme overview. Prepared the detailed
seven-task implementation plan docs/superpowers/plans/2026-10-24-asian-rqmc.md.
It fixes contract/result interfaces, pseudo-random/QMC work units, independent
references and precision diagnostics, exact grid/RNG keys, actual CLI/schema,
2880estimate/18432scramble-row acceptance, source replay and final review.

Read-only planning checks confirmed installed NumPy2.5.4/SciPy1.18.1 support the
required Sobol API. QuantLib is not installed; PyPI lists a1.44arm64abi3wheel.
The plan pins it as an optional project-local research dependency after approval,
not a new base runtime or a claim that the comparator has already been validated.
External day-count/observation alignment and reference precision are required
checks before accuracy comparisons. A low-precision reference withholds rankings.

Plan examples passed syntax/TOML/count self-review. Native execution with one
fresh final review is recommended because task interfaces are sequential; user
plan review and execution-method selection are still pending. No new product
source, installed dependency, numerical experiment or completed v1 artifact changed.

## V2-A — 24 October 2026

User approved the Monte Carlo spec and seven-task plan, choosing inline execution
with a fresh final review. Implemented discrete Asian contracts/references,
Brownian bridge, five estimators, optional QuantLib 1.44 comparator, strict
study/custom CLI, paired reference-aware metrics and complete-estimator benchmarks.
Full pre-review strict suite: 510 passed (task6-green-layout.log).
Canonical run: 2,880/2,880 estimates, 18,432 scrambles, no estimate failures;
82,575,360 production paths and 294,912 additional pilot paths. All six references
are low_precision: empirical radii 0.00265–0.01203 exceed 0.0005. All 90 cells withhold
precision rankings. This is a reported research limitation, not a passed reference gate.
Independent audit: 32,106 numeric assertions; 1,152 QMC estimates, 576 pilot betas,
90 metric cells and 90 paired comparisons. Custom example: 480/480 estimates,
3,072 scramble rows; external arithmetic reference unavailable for arbitrary dates.
See ASIAN_MONTE_CARLO_TH.md, reports/examples/v2-asian/ and reports/verification/.
Final review and recovered-source replay evidence are recorded in the execution ledger.

Final review found 4 Important issues and one extreme bridge issue regraded by the
executor as Important. Reproducing tests failed first; a single fix pass corrected
relative/second-order payoff arithmetic, scaled aggregate SD, warm-up/failure plotting
and full-contract efficiency matching, plus bridge conditional SD calculation.
Full strict suite after fixes: **529 passed in 29.84s** (final-fix-green.log).
Pre-review runs preserved under reports/verification/asian-execution/pre-review/;
canonical artifacts are rebuilt from the fixed source before completion.

Final rebuilt canonical/custom outputs verified against current source hashes.
Recovered-source replay from final code: 9/9 numerical/input files byte identical;
independent audit remains 32,106 assertions. Final canonical runtime about153s;
reference precision gates remain failed/visible. All four rebuilt figures inspected
and35 local documentation links verified. V2-A execution complete; no deferred minors.
