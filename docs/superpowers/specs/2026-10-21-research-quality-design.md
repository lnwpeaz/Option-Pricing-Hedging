# Research-quality audit and completed-stage strengthening

User intent: assess substantive value honestly and improve underdeveloped completed
stages. The project is a computational research prototype, not a finished hedge
study or production trading system. Do not mistake number of tests for usefulness.

## Improvements selected

1. A separate numerical benchmark integrates the discounted payoff under a normal
   shock distribution; it must not call the analytic, CRR, MC or shared GBM code.
   Integrate over finite normal bounds L=-12, U=12+sigma*sqrt(T), splitting at the
   payoff kink. Quote both SciPy quadrature error estimate and an analytic upper
   bound on truncated payoff tails. Errors are absolute premium units. This tests
   the analytic baseline using a structurally independent computation.
2. A predeclared stress-validation CLI spans 4 maturities, 3 volatilities, 3 strikes,
   2 rates and call/put (144 scenarios). Compare analytic prices to quadrature,
   CRR over 3 step counts, and all 3 MC methods over 32 independent repeats.
   Keep all raw estimates, errors, quoted SEs/CIs and degenerate zero-SE outcomes.
   Report coverage with finite-repeat uncertainty. Do not demand every 95% CI
   covers truth or hide rare-payoff failures. Time/cost rankings are not the purpose.
3. New experiment runs preserve exact source snapshots, input config, dependency
   versions, replay commands and available checkout tests/configs. Hashes identify
   contents; archived bytes allow recovery. Add an integrity verifier and test actual
   replay in an isolated extracted directory with current dependencies. Archive
   format is deterministic for identical input/source/environment.
4. An honest Thai quality audit explains each stage's value/evidence, residual
   limitations and final acceptance criteria. The hedge ledger and paired hedge
   experiments are the major remaining research deliverables; do not add unrelated
   models/GPU/UI to inflate scope or claim financial novelty.

## Reproducibility contract

Each future demo writes source_snapshot.zip before its completed manifest. Capture
all package Python sources under src/, exact input_config.toml, runtime requirements,
Python/platform metadata and REPLAY.md; include checkout tests/configs/pyproject/
README/lock when available. Dependency pins are a recorded environment snapshot,
not a portable hash-verified lock. Python/platform requirements still matter.
New manifests carry source_snapshot metadata and all artifact hashes; manifest
written last. Old examples stay immutable and are explicitly historical records
whose exact old source may not be recoverable from a hash alone.

Verifier checks config/artifact/archive hashes, safe relative names, exact archived
entry set and archive file hashes, and package source alignment with manifest. It
does not execute archives. No provenance authenticity/signature claim is made.
Actual replay test runs trusted locally created source, not arbitrary downloaded code.

## Scope/acceptance

No new product dependencies. Test-first core/quadrature/manifest/replay/CLI contracts.
Stress-run output includes 144 independent-reference rows, 432 tree rows, 13,824 MC
rows and 432 MC metric rows (N=8192, pilot=512). Main analytic check tolerance is
1e-7 absolute, predeclared; tree errors are descriptive, no monotonicity assumption.
MC coverage failures/zero SEs are results, not rejected parameter cases.
Run strict existing+new tests, execute full validation, visually inspect summary
figures and verify archive/replay. Preserve existing examples and parent home Git.
