# Hedge Ledger Implementation Plan

> Execute inline using executing-plans and test-driven-development. User explicitly
> authorized the next milestone under the existing research specification.

**Goal:** Correct, inspectable short-call cash accounting before paired research.
**Architecture:** immutable contracts + pure one-path core + explicit-path artifact demo.
**Tech Stack:** existing Python3.11+, NumPy, SciPy analytic engine, matplotlib/pytest.
**Spec:** docs/superpowers/specs/2026-10-23-hedge-ledger-design.md and docs/RESEARCH_SPEC.md.

## Global constraints

- One short call/unit multiplier, no dividends, continuous r, positive maturity.
- Initial premium uses hedge/model sigma; no external injection; never rebalance at expiry.
- Costs at open/rebalance/close, actual dt interest, negative cash borrows at same r.
- No new dependencies or edits to historical outputs; no parent-repository Git changes.

## Review focus

- Nearly cancelling cash/trade/payoff arithmetic and unrepresentable financed costs.
- Negative rates, irregular last interval and hold rows with cash interest.
- Zero-sigma Greek kink must remain an explicit error; expiry never calls Greeks.
- Prefix decisions cannot depend on later prices; baseline premium must match model.
- Assets-value wording must not disguise an outstanding short call as net profit.

## Task1: immutable records and pure accounting engine

Files: contracts.py, hedging/ledger.py, tests/test_ledger.py.
Consumes: OptionSpec, black_scholes.price/greeks. Produces: HedgeRow/HedgeResult,
hedge_path(spec, *, times, spots, rebalance_every_steps, one_way_cost_bps),
unhedged_path(spec, *, times, spots).

- [x] Write tests first. Hand case sigma=r=0, S0=120,K100,T1,
  times[0,.2,.6,1], spots[120,90,130,140], cost10bps gives cash
  [-100.12,-10.21,-140.34,-40.48], deltas[1,0,1,0], nominal cost.48.
  Add independent interest, positive-sigma constants, frequency/prefix/range cases.
- [x] Run `.venv/bin/python -m pytest tests/test_ledger.py -q --tb=short -W error`.
  Expected: missing hedge_path/unhedged_path/HedgeResult failures.
- [x] Implement records and validated engine using existing analytic price/delta;
  cash update uses math.fsum([cash_before, option_cashflow,-trade*spot,-cost]).
  Financial formulas/record fields are fixed in the design, not duplicate modules.
- [x] Run focused tests then whole strict suite. Expected: all pass; ledger all counts.

## Task2: real demonstration artifacts

Files: configs/hedge_ledger.toml, experiments/hedge_demo.py,
analysis/ledger_plots.py, tests/test_hedge_demo.py.
Consumes: Task1 public API/row fields, existing finalize_manifest. Produces:
run_demo(config_path: Path, output_dir: Path)->Path and executable hedge_demo CLI.

- [x] Write real CLI/output/config/no-overwrite/repeatability tests before modules.
  Small valid explicit path, all accounting rows and snapshot verification required.
- [x] Run `.venv/bin/python -m pytest tests/test_hedge_demo.py -q --tb=short -W error`.
  Expected: missing hedge_demo module failures.
- [x] Implement strict option/path/hedging config, compute hedge/unhedged/zero-cost
  paths before creating output; save the design's files and four-panel plot.
  Use csv.DictWriter on dataclasses.asdict(row), finalize_manifest after artifacts.
- [x] Run focused tests and whole strict suite. Expected: all pass.

## Task3: independent review, executed example and learning handoff

Files: docs/HEDGING_TH.md, README.md, docs/{PROGRESS,INTERFACES,RESEARCH_SPEC,
PROJECT_AUDIT_TH,ROADMAP_TH,REPRODUCIBILITY}.md, tests/README.md;
reports/examples/milestone-4 and replay verification outside completed run.
Consumes: Task1/2 stable signatures and records. Produces: verified example/guide.

- [x] Request one fresh-context read-only review under requesting-code-review.
  Treat important findings with RED regression, minimal fix and full suite.
- [x] Execute `PYTHONPATH=src .venv/bin/python -W error -m
  option_hedging.experiments.hedge_demo --output-dir reports/examples/milestone-4`.
  Expected: completed run, reconciliation checks pass; inspect figure and CSV.
- [x] Verify declared hashes and replay from extracted trusted source in a new
  directory; compare path/ledger/unhedged/check CSVs and summary.json numerically.
- [x] Write Thai guide with actual numbers and explicit one-path limitations;
  update status to milestone4 complete, paired hedge research next.
- [x] Final strict full suite and artifact verification. Expected: no failures.

## Execution ledger / preflight

- Ruling: Existing reviewed research design and repeated explicit authorization to
  continue are sufficient; execute the concrete next milestone inline, without
  reopening permission gates. Cost if scope wrong: reversible local code/doc edits.
- Ruling: Git root is unrelated /Users/robot with no project history. Work in place;
  do not create worktrees/commits or run Git-dependent skill scripts in parent.
  Keep this plan ledger as durable record. Cost: no project commit-level rollback;
  tests and source archives supply reproducible state instead.
- Task1→Task2: immutable row fields feed CSV/plots; both use design fields verbatim.
- Task2→Task3: source snapshots written after artifacts, integrity verification and
  replay acceptance exclude timestamps/images. No interface conflicts found.
- Fresh strict baseline:273 passed in28.22s.

- Task1: complete.40 tests RED for absent engine→40 GREEN; strict full suite313 passed in29.27s.
- Task2:15 real-CLI/demo/config tests RED for missing module→15 GREEN in9.51s; whole strict suite running.
- Final fresh-context review dispatched under requesting-code-review.
- Task2: complete. Whole strict suite328 passed in30.19s; actual illustrative CLI
  and figure inspected in reports/runs/ledger-first/ before final review fixes.
- Final review: two Important numerical findings confirmed with four RED tests:
  prematurely rounded intrinsic payoff invents P&L; underflowed trade notional
  bypasses cost checks. No Critical/Minor findings.
- Final: Ruling: Reject intrinsic-payoff rounding losses above64 ULPs of strike,
  rather than invent a compensating cash flow or claim arbitrary precision.
  This preserves simple auditable scalar cash-flow records. Cost if too strict:
  extreme-ratio paths require a future compensated/arbitrary-precision ledger.
- Final: Ruling: Unchanged analytic pricer universal robustness is outside this
  ledger change; existing tests/144-scenario independent validation bound its
  evidence. Cost if a new pricer edge is encountered: explicit range error or
  another pricer regression is needed; no universal-input claim is made.
- Final: Ruling: Ensemble effectiveness/alternate premium/dividends/brokerage
  mechanics remain outside milestone4; same model-premium convention is preserved.
  Cost: no real-market or aggregate effectiveness conclusion yet.
- Final: Ruling: Documentation/rendering/replay are parent-owned final acceptance,
  not omitted deliverables; complete them below before milestone completion.

- Final: fixed payoff precision loss and zero-notional cost bypass — four targeted
  tests RED→GREEN, focused59 passed, whole strict suite332 passed in22.88s.
- Final: no deferred minors. All reviewer declined-to-judge boundaries ruled above.
- Task3: complete. Canonical example produced/inspected; all10 artifact hashes and
  package source alignment verified. Actual recovered-source CLI reproduced all
  four CSVs plus summary bytes. Independent Decimal60 cash-flow check max global
  discrepancy2.15e-14; proof reports/verification/milestone-4-replay.json.
- Thai guide, current scope/architecture/interfaces/roadmap/audit/provenance/test
  map updated. Milestone4 complete; paired hedge experiment and final report next.
- Environment note: sandbox made user-level plotting/font caches unavailable;
  subsequent verification used MPLCONFIGDIR/XDG_CACHE_HOME under /private/tmp.
  No global settings or parent Git metadata changed. No commit/worktree integration
  is applicable to this source folder; preserve plan ledger/source archive.
