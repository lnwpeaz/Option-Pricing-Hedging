# SDD ledger — plan: docs/superpowers/plans/2026-10-24-asian-rqmc.md

Execution approved 2026-10-24. Native inline implementation, one fresh independent final review.
Spec: docs/superpowers/specs/2026-10-24-asian-rqmc-design.md.
Before snapshot: reports/verification/asian-execution/before.zip and before-sha256.json.
Project-local checkpoints replace Git operations as explicitly required by approved plan (parent repository is unrelated).

## Pre-flight interfaces
- Tasks 1→2/3/4/5/6: frozen AsianOptionSpec, maturity from final fixing; no existing OptionSpec changes. Compatible.
- Tasks 1/2→3/4: normalized paired arithmetic/geometric discounted payoffs; geometric analytic expectation divided by S0. Compatible.
- Tasks 3→4→6: AsianEstimate work counters and scramble prices immutable; QMC uncertainty across R independent estimates. Compatible.
- Tasks 1/5→6: independent internal/external references and empirical external precision band; no exact-truth claims from external reference. Compatible.
- Tasks 6→7: full canonical 2,880 estimates / 18,432 scramble rows, manifests and numerical replay. Compatible.
- Tasks 5/6→7: optional pinned QuantLib recorded in provenance and recoverable source/config snapshot. Compatible.

## Tasks
Task 1: starting — contract validation and independent numerical references.

Task 1: complete — RED observed in task1-red.log; GREEN strict full suite: 421 passed in 22.99s. SHA-256 checkpoint: reports/verification/asian-execution/task1-sha256.json.
Baseline: .venv/bin/python -m pytest -q -W error → 390 passed in 23.10s (baseline.log).
Task 2: starting — FIFO Brownian bridge and normalized paired payoff kernel.

Task 2: complete — RED observed in task2-red.log; GREEN strict full suite: 440 passed in 22.60s. SHA-256 checkpoint: reports/verification/asian-execution/task2-sha256.json.
Bridge: terminal first; FIFO index midpoint; actual-time weights; left then right.
Task 3: starting — scaled moments and independent-pilot control.
Ruling: add target_payoffs alongside paired discounted_payoffs — noncontrol estimators must not compute unused geometric control payoffs while reporting zero control evaluations — cost if wrong: one small additional kernel entry point to maintain.

Task 3: complete — RED observed in task3-red.log; GREEN strict full suite: 460 passed in 22.59s. SHA-256 checkpoint: reports/verification/asian-execution/task3-sha256.json.
Task 4: starting — R independent scrambles, base-2 points, t uncertainty.

Task 4: complete — RED observed in task4-red.log; GREEN strict full suite: 484 passed in 22.90s. SHA-256 checkpoint: reports/verification/asian-execution/task4-sha256.json.
QMC derivation: parent.integers(0,2**32,size=(R,4),dtype=uint32); each row → SeedSequence → PCG64 → scrambled Sobol(bits=52); random_base2 without skipping. Forward/bridge share the same parent key. R-scramble t interval only.
Task 5: starting — optional pinned independent comparator, date validation, precision assessment and provenance.

Task 5: complete — RED observed in task5-red.log; GREEN strict full suite: 492 passed in 24.60s. SHA-256 checkpoint: reports/verification/asian-execution/task5-sha256.json.
QuantLib 1.44 installed project-locally; direct official wheel SHA-256 verified against PyPI (quantlib-wheel.json). Default full-body download stalled; ranged retrieval delivered identical verified bytes. No dependency/version change.
Task 6: starting — strict config, full evidence runner, reference-aware metrics and measured plots.
Bootstrap key: [81,contract index,N,seed]; requested macro IDs shared across methods, missing pairs remain excluded explicitly. Conditional RMSE sensitivity is not a CI.
Task 6 edge checks: missing references, zero errors and failed-only runs initially exposed plotting/schema faults. Root causes traced to absent positive x-data on log axes, object None arrays, extreme log-axis ticks and deferred schema construction. Existing failing cases plus new all-failed regression now pass; task6-edge-red.log / task6-focused-green.log.
Small-run figure inspection found clipped text on a one-panel canvas. Increased minimum canvas and tight export bounds; numerical tables unaffected.

Task 6: complete — RED observed in task6-red.log; GREEN strict full suite: 510 passed in 28.93s. SHA-256 checkpoint: reports/verification/asian-execution/task6-sha256.json.
Task 6 final layout verification: full strict suite → 510 passed in 29.55s (task6-green-layout.log). CLI, 40 estimates/64 scrambles, numeric reproducibility, optional-reference failure, all-failed output, actual benchmark and overwrite/integrity cases pass.
Task 7: starting — canonical full research, numerical audit, recovered-source replay, Thai guide and fresh final review. The immediately preceding full strict suite is the pre-run verification.
Ruling: raise declared SciPy minimum from 1.10 to 1.15 — Sobol's rng= API used by the approved derivation was introduced in 1.15 (verified installed official docstring) — cost if wrong: older SciPy environments must upgrade; the recorded 1.18.1 research environment is unchanged.

Task 7 evidence: canonical CLI completed 2,880/2,880 estimates, 18,432 scrambles, 0 failed estimates, total_before_manifest=175.259585s. All 6 references low_precision; all 90 precision-dependent rankings withheld as predeclared. No reference gate pass claimed.
Independent audit: 32,106 assertions, 1,152 QMC estimates, 576 independent pilot beta reconstructions, 90 macro metric and 90 paired comparisons; v2-asian-checks.json. Additional cases include geometric/single-fixing/put/irregular/deterministic/rare diagnostics.
Source recovery: verified archive and exact runtime pins; actual module path is inside recovered/src; full CLI replay complete. 9 numerical/input files byte identical, source hashes and numerical-acceptance flags identical; v2-asian-replay.json. Timing/allocation/figure bytes excluded deliberately.
Custom CLI: 480/480 estimates, 3,072 scramble rows, no failures; unsupported dated arithmetic reference remains unavailable. Four canonical figures visually inspected, all labels and notes readable.
Final review dispatched once to fresh gpt-6-astra/high (review_asian_v2), read-only package; implementation remains inline as approved.

Final review: 4 Important findings accepted: representable payoff cancellation; empirical-SD scale instability; warm-up failures/failed-only benchmark plotting; timing-efficiency contract mismatch. No Critical findings. Detailed independent review received from review_asian_v2.
Final re-grade: subnormal bridge variance erasure → Important, because the public pure transform silently removes an independent Brownian coordinate for accepted inputs. Preserve the representable conditional standard deviation rather than returning an altered law.
Fix pass started: 17 new regression cases observed failing (final-regressions-red.log), plus failed-only plotting RED and symmetric tiny-payoff RED. No implementation changes preceded these reproductions.
Final: Ruling: live trading, calibration, American exercise, dividends and portfolio functionality remain outside this slice — consistent with approved domain and explicit user separation from portfolio research — cost if wrong: those applications require separate model/contract work.
Final: Ruling: no universal method superiority or guaranteed CI coverage claimed — finite-repeat intervals/reference limits do not establish either — cost if wrong: results cannot select one universal best method.
Final: Ruling: environment claims restricted to recorded tested versions/platform — reviewer did not run a platform/minimum-version matrix — cost if wrong: compatibility elsewhere remains unverified.
Final: Ruling: accept the recorded recovered-source replay plus independent audit without a second reviewer replay — actual author replay was executed and reviewer checked all 9 hashes and reran 32,106 numeric checks — cost if wrong: no independently executed second full replay.
Final: Ruling: reviewer editorial scope covers core interface/research/usage documents; author checks remaining links — full editorial review of every historical document was outside reviewer scope — cost if wrong: minor historical prose issues may remain.

Final: fixed representable payoff cancellation — nextafter/small-drift/tiny/symmetric-payoff tests RED→GREEN; relative log ratios and compensated tiny-log expansion preserve first/second-order movement.
Final: fixed scaled aggregate dispersion — currency-scale regressions RED→GREEN; aggregate mean/SD avoid raw squares.
Final: fixed warm-up/failed-only benchmark output — warm-up and failed-plot regressions RED→GREEN; failures retained and plots annotate empty successful groups.
Final: fixed timing×RMSE contract mismatch — custom schedule regression RED→GREEN; matching uses full AsianOptionSpec including fixings/maturity.
Final: fixed subnormal bridge coordinate loss — tiny-grid regression RED→GREEN; conditional SD formed as product of square roots.
Single fix-pass full strict suite: 529/529 passed in 29.84s (final-fix-green.log). No deferred minors and no second reviewer requested.
Pre-review primary/custom runs moved intact to reports/verification/asian-execution/pre-review/; old verification proofs copied there. No completed run overwritten. Rebuilding the full fixed-seed grid and recovered-source replay from final code.

Final rebuilt evidence (fixed source): 2,880/2,880 primary estimates; 18,432 scramble rows; 480/480 custom estimates; 0 estimate failures. Canonical measured total_before_manifest=152.857292s. All six references remain low_precision and all 90 precision rankings withheld.
Final independent numeric audit: 32,106 assertions passed, including 1,152 QMC estimates, 576 control pilot coefficients, 90 metric and 90 paired cells; additional validation diagnostics retained.
Final recovered-source CLI replay: 9/9 numerical/input artifacts byte identical; recorded runtime pins and actual imported recovered module path verified (v2-asian-replay.json, recovered-2/src). Source hashes match final current source in both canonical/custom manifests. Hash verification passes for all 18 artifacts in each run.
Final QA: all four rebuilt canonical figures inspected visually; 35 local document links resolve. File checkpoint: reports/verification/asian-execution/final-sha256.json.
Task 7: complete — full strict suite 529/529 (final-fix-green.log), single fresh independent review with verified fixes, full rebuilt study/custom run, independent audit and actual recovered-source replay. Rulings above remain the explicit boundaries; no deferred minors. V2-B/C/D remain outside this approved slice.
Finish: project-local source/evidence retained as required by plan; no parent-repository commit/merge/push or worktree cleanup. Own regenerable wheel installer removed after successful verified installation; wheel provenance/hash retained.
