# Execution ledger — 2026-10-18-monte-carlo.md

- User authorized continued implementation and emphasized Monte Carlo/Computer Engineering.
- Ruling: execute inline without repeated approval gates under the existing user authorization.
- Ruling: no project Git history exists; leave parent home repository untouched and work in place.
- Pre-flight: Task 2 consumes Task 1 PriceEstimate and explicit RNG API; docs consume actual artifacts.
- Baseline from recap: 103 tests passed; fresh run started before implementation.
- Fresh baseline: 103 passed in 6.06s.
- Task 1 RED: 32 failed, all because the terminal/price APIs were absent.
- Task 1 first implementation: 31 passed; one hand-entered terminal expectation had
  exponent -0.16 instead of 0.08 - 0.02 - 0.20 = -0.14. Corrected that test fixture.
- Task 1 complete: full suite 135 passed in 5.77s.
- Task 2 RED: 17 demo/CLI/benchmark tests failed because modules were absent.
- Ruling: include strikes 80/100/120 and both call/put to avoid judging variance
  reduction on one payoff regime; use 64 independent runs per cell and bootstrap RMSE intervals.
- Task 2 complete: actual demo/CLI tests passed; initial whole suite 162 passed.
- Initial full research run completed: 5,760 estimates, 90 metric cells and 4 figures.
- Review found zero-baseline-RMSE report formatting failure; added failing regression,
  fixed unavailable ratios as n/a and formatted report before output creation; regression passed.
- Review found false zero SE from squared tiny currency values. Three scale tests failed;
  normalized moments/pilot observations by S0 and rescaled final estimates. All 48 core tests passed.
- Added exact-expiry ATM regression (put failed before fix); fixed intrinsic handling.
- Common histogram bins now make method frequency distributions comparable.
- Matplotlib boxplot labels use the declared >=3.7-compatible API.
- Full post-fix suite: 169 passed. Final timing run will execute without concurrent tests.
- Follow-up review found normalization-order and singleton-merge underflow gaps.
  Both regression tests failed first; fixed discounted-sample ordering and merge guards.
- NumPy build metadata no longer requires optional PyYAML or emits its advisory warning.
- Final strict suite: 171 passed in 12.34s; independent reviewer rechecked all findings,
  68 targeted tests passed with warnings as errors, no unresolved findings in scope.
- Verified final run's 5,760 rows, all 90 aggregate RMSEs, config hash, 21 source hashes
  and 13 artifact hashes. Visual QA found kernel caption overlaying a boxplot;
  moved caption to a clear lower area. One final run refreshes source/artifact hashes.

- Task 3 complete: Thai guide, status/docs, review fixes and all visual QA complete.
- Final suite: 171 passed in 12.39s with warnings as errors. Final CLI completed without warnings.
- Final canonical example integrity rechecked: exact config, 21 source hashes, 13 artifact hashes, 5760 estimates and all 90 RMSE aggregates.
- Final kernel median speedup 13.06x (kernel boundary only); batch32768 median complete pricing2.408ms and traced peak1934960bytes.
- All four figures visually verified; completed example at reports/examples/milestone-2b/.
