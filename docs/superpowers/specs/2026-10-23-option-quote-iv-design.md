# Milestone 7: option-quote diagnostics and implied volatility

Status: written design for user review; implementation has not started.
Date: 23 October 2026 (Asia/Bangkok).

Update 24 October 2026: the user requested consideration of a larger/deeper scope.
This smaller draft remains unapproved. See docs/PROJECT_V2_PROPOSAL_TH.md and the
proposed first-slice 2026-10-24-asian-rqmc-design.md. Quote/IV is retained as the
market-bridge candidate; neither scope is silently treated as implemented.

## อ่านส่วนนี้ก่อน

เป้าหมายคือเพิ่มเครื่องมือที่รับรายละเอียดสัญญาและราคา bid/ask แล้วตอบว่า
ข้อมูลตรงกับโมเดลหรือไม่, implied volatility (IV) เท่าไร, Greeks เป็นอย่างไร
และผลเปลี่ยนแค่ไหนเมื่อปรับสมมติฐาน โดยเก็บข้อมูลและผลให้ตรวจซ้ำได้
ไม่เพิ่มงานเลือกหุ้นหรือจัดพอร์ตของ Portfolio Quantitative Research

เริ่มจากไฟล์ CSV ที่มี timestamp และประเภทสัญญาชัดเจน ไม่ผูกกับผู้ให้บริการ
ข้อมูลรายใด เวอร์ชันแรกมีตัวอย่าง synthetic ที่ระบุว่าเป็นข้อมูลสร้างขึ้น
สามารถรับไฟล์ตลาดที่ผู้ใช้จัดเตรียมได้เมื่อสัญญาตรงกับขอบเขตโมเดล แต่ยังไม่ได้
สาธิตหรือรับรองผลกับข้อมูลตลาดจริง ระบบไม่อนุมาน exercise/dividend จาก ticker

ขอบเขตยังเป็น European, ไม่มีเงินปันผล, cash payoff และราคาอ้างอิงต่อหนึ่งหน่วย
ถ้าเป็น American, มีเงินปันผล หรือข้อมูลไม่ครบ จะรายงานว่าใช้ไม่ได้พร้อมเหตุผล
การรองรับ equity options สหรัฐฯ อย่างครบถ้วนต้องทำ exercise/dividend อีกขั้น

Monte Carlo ยังอยู่ในงาน: ตรวจการประมาณราคาภายใต้ IV ที่ได้ พร้อม SE/CI และ
จำนวนงานคำนวณ ส่วนการเพิ่มราคากระโดด/volatility เปลี่ยนเวลา และการจำลอง hedge
จาก quote เป็นขั้นต่อไป ไม่แอบเรียก IV ว่า true volatility หรือผลตอบแทนคาดหวัง

## Intent, alternatives and scope decision

The user wants a distinct financial/computational-engineering profile project
with usable, extendable outputs. Existing milestones 1-6 are complete. They
approved proceeding with quote diagnostics, IV and model-risk reporting; no
market feed, brokerage integration, new portfolio subsystem or execution is requested.

Approaches considered:

1. **CSV snapshot + deterministic IV + audit report (selected).** Reusable with
   explicit inputs, synthetic truth tests and saved replay data; no vendor lock-in.
2. Direct broker/vendor option-chain ingestion. Useful later, but introduces data
   access and contract-normalization dependencies before the inverse pricer is verified.
3. American/dividend engine first. Expands instrument coverage, but changes the
   financial conventions and needs its own design and independent benchmarks.

Milestone 7 produces one coherent pipeline. Its optional MC check reuses the
existing estimator. New hedge policies, jumps/stochastic volatility, an IV surface,
historical trading backtests, a dashboard and all buy/sell recommendations are excluded.

## Data flow and component boundaries

CSV bytes + TOML -> schema/time/contract checks -> endpoint IV results
-> midpoint Greeks / what-if repricing / optional MC check -> CSV + report + manifest.

- `pricing/implied_volatility.py`: pure scalar inverse of existing q=0 analytic
  pricer; validated settings and immutable diagnostic result. No CSV, clock or RNG.
- `quotes/contracts.py`: immutable parsed row and quote-analysis settings;
  explicit units and timestamp conventions. No market inference from symbols.
- `quotes/analysis.py`: pure per-row validation and endpoint analysis, accepting
  an explicit as-of time; no file writes, live clock or hidden market estimates.
- `experiments/quote_review.py`: strict input/config parsing, existing MC calls,
  results/report output, source capture and CLI. Formatting may be split into
  `analysis/quote_report.py` if it otherwise mixes too many responsibilities.
- `experiments/provenance.py`: backward-compatible optional replay-input bytes
  for the CSV, so the archived source can run without the original external file.

Existing `OptionSpec`, analytic prices/Greeks, MC estimators and hedge conventions
remain unchanged. No new runtime dependency is required.

## Quote CSV v1 contract

Require exactly these columns (a documented fixed order for the example; parser
may accept a different column order). Duplicate/missing/unknown headers are file errors.

| Field | Meaning / validation |
|---|---|
| quote_id | Nonempty stable identifier; duplicate nonempty IDs are a file error |
| underlying_id | Nonempty descriptive ID; no inference of contract specifications |
| data_kind | `synthetic` or `user_supplied_market`; declaration, not authenticated provenance |
| quote_time_utc | ISO-8601 timezone-aware timestamp, normalized to UTC |
| underlying_time_utc | Timestamp of the supplied spot, also timezone-aware |
| expires_at_utc | Explicit expiry instant, not a date interpreted at midnight |
| spot, strike | Finite positive real values |
| risk_free_rate | Finite continuously compounded annual rate, same currency |
| dividend_yield | Required finite input; only exactly zero is supported |
| kind | Exactly `call` or `put` |
| exercise_style | Explicit; only `european` is supported |
| settlement_style | Explicit; only `cash` is supported |
| currency | Explicit uppercase three-letter currency declaration shared by spot/strike/premium |
| quote_unit | Exactly `per_underlying_unit`; do not silently divide contract premiums |
| contract_multiplier | Positive finite metadata; retained, not used as a capital/margin estimate |
| bid, ask | Finite nonnegative prices, bid <= ask; locked quote is retained with a flag |

Malformed numeric/date values are row failures and remain in the output. Numeric
strings in CSV are parsed intentionally; NaN/infinity/empty/boolean spellings fail.
An unreadable/invalid-UTF8 file or invalid file schema fails the run before a
completed manifest. A UTF-8 BOM may be accepted while preserving original bytes.

As-of time is fixed in TOML, never taken silently from the wall clock. Maturity
uses `(expires_at_utc - quote_time_utc).total_seconds() / (365*86400)` (ACT/365F).
Freshness uses as-of minus quote time. Reject a future quote, future underlying
observation, expiry <= quote time, quote age above the configured maximum, or
absolute quote/underlying timestamp skew above the configured maximum.
Equality at each age/skew limit is accepted. Default maximum age is 300 seconds;
default underlying skew is 5 seconds. Neither proves execution availability.

Preserve raw input records and every row outcome. Quote ID is not evidence that
the row is an exchange-issued contract; caller-supplied metadata must be accurate.

## Pure implied-volatility API and diagnostics

Public API takes market price and the five non-volatility inputs (S,K,T,r,kind)
as named arguments. Reuse `OptionSpec` validation at sigma=0; do not require callers
to enter a dummy volatility. Return a frozen result containing:

- status, optional volatility, model price and signed price residual;
- lower/upper model bounds, final bracket, iterations/function evaluations;
- effective price tolerance, vega and optional local price-error/vega sensitivity;
- diagnostic flags. No NaN/Infinity in serialized outputs; absent quantities are null.

Input/settings type or domain errors raise explicit TypeError/ValueError.
Validly typed but uninvertible prices return diagnostics rather than pretending
there is a solution. Status set:

`converged`, `at_lower_bound`, `at_upper_bound`, `outside_bounds`, `expired`,
`precision_limited`, `not_bracketed`, `not_converged`, `numerical_range_error`.

At T>0, q=0, let D=K*exp(-rT): call bounds [max(S-D,0),S), put bounds
[max(D-S,0),D). Exact lower-bound price has mathematical boundary sigma=0 and
status at_lower_bound, with a precision/identifiability warning. Exact upper-bound
price has no finite IV; return at_upper_bound and null IV. Prices strictly outside
the financial bounds fail even if the violation is small; never clip a price.
At expiry IV is not identified: return expired, not an arbitrary sigma.
If discounted strike underflows to zero or becomes nonfinite, or distinct bounds
collapse numerically, report numerical_range_error instead of interpreting the
collapsed bounds as an identifiable zero/infinite IV.

For interior prices use the deterministic analytic residual and a bracketed Brent
solver, not noisy MC or unguarded Newton steps. Start [0,0.25], double the upper
endpoint up to max_volatility=8.0, then stop. Reaching that cap without bracketing
means not_bracketed within the configured domain, not proof no IV exists anywhere.
The bracket settings are explicit configurable finite values with consistent ordering.

Default sigma xtol=1e-12, rtol=1e-10 and maxiter=128. Default price atol=1e-10,
price rtol=1e-10. Effective price tolerance is the maximum of atol, rtol*abs(price),
and eight ULPs at the larger-magnitude finite financial bound. This numeric floor
is disclosed and can make tiny-premium/deep-ITM cases unidentifiable. It is not a
statistical interval or a market tick-size assumption.

If an interior price is within effective tolerance of a financial bound, return
precision_limited with null IV rather than clamping to zero/infinity. A finite
solver result must converge, be in the bracket, and reprice within tolerance.
Otherwise return not_converged or numerical_range_error with the actual cause.
An extreme finite input that overflows a bound/pricer is a numerical range failure.

At a converged root report vega in units per 1.0 annual volatility and
local `effective_price_tolerance / vega` where finite. Flag low_vega when
vega <= 1e-6*spot. Root xtol alone must not be presented as the uncertainty of IV.
No price clipping, hidden fallback volatility or silent solver retry with different
assumptions is allowed. Solver settings and evaluations are retained.

## Quote-level outputs and interpretation

Evaluate bid, midpoint `(bid+ask)/2` with overflow-safe averaging, and ask separately.
A crossed/invalid quote, unsupported contract, stale/skewed timestamps or a price
strictly outside the model bounds rejects the row with stable reason codes.
Input prices equal to a bound remain endpoint diagnostics. Midpoint must have a
regular converged positive IV to produce Greeks, what-if values and MC checks.

Per-row status is `ok`, `warning` or `rejected`, with all applicable flags and a
human-readable reason. If a bid/ask endpoint lacks finite IV while midpoint is
regular, retain midpoint outputs but mark warning and preserve the endpoint status.
If midpoint has no usable IV, keep the row diagnostics and omit derived outputs.
No aggregate count may hide failed or unsupported records.

IV bid/ask endpoints describe mapping of a quoted spread through this model,
not a confidence interval, expected return, volatility forecast or liquidity guarantee.
Only report an ordered finite IV band when both endpoints are regular; otherwise
show each endpoint's status, not a manufactured range.

Midpoint Greeks use the existing analytic implementation. Vega per percentage
point is vega/100. Every output states per-underlying-unit currency units and
retains multiplier metadata; no contract-margin or required-capital inference.

What-if repricing uses spot factors [0.9,1.0,1.1] crossed with volatility factors
[0.8,1.0,1.2] at unchanged T/r, relative to midpoint IV. Report model price change
per long option unit. It is an instantaneous sensitivity scenario, not a dynamic
hedge P&L, a forecast probability or an executable trade return.

## Monte Carlo connection

For each usable midpoint construct the existing q=0 OptionSpec and run a configured
estimator (default control, N=65,536, pilot=1,024, batch=32,768). Save estimate,
SE, approximate 95% CI, independent counts, pilot counts and analytic reference.
Flag zero SE explicitly. A single missed CI is not an implementation failure or
a market-mispricing signal. No post-run sample/seed selection.

Use PCG64/SeedSequence with stage tag 70, configured seed and deterministic
SHA-256-derived quote-ID words; do not use Python's randomized hash(). Each ID
has an independent explicit stream, so reordering input rows leaves its draws
unchanged. Global NumPy RNG is not read or mutated.

An MC estimate reproducing the calibrated price checks the estimator under the
same model, not whether the market is correctly priced. Analytic inversion and
MC validation are separate tasks. IV is never used automatically as physical drift
or true future scenario volatility. Existing hedge experiments remain separate.

## Configuration, files and replay

Strict TOML sections: input (CSV basename + explicit as-of), quote_checks
(age/skew), solver (settings above), analysis (what-if factors) and monte_carlo
(enabled,method,N,pilot,batch,seed). CSV path must be a basename resolved beside
the config, making replay independent of the original absolute path. Unknown keys
are errors. The selected example settings are saved before its first execution.

CLI: `python -m option_hedging.experiments.quote_review --config ... --output-dir ...`.
Refuse an existing output directory. No API keys, feed connections or order side effects.
Save exact input_config.toml/input_quotes.csv, effective_config.json,
quote_results.csv, iv_results.csv (one endpoint per row), sensitivities.csv,
what_if.csv, mc_checks.csv, summary.json, RESULTS.md and source/environment manifest.
Empty derived tables retain a defined header. Summary declares synthetic/market
input counts, total/accepted/warning/rejected rows and every failure reason count.

Extend capture_snapshot/finalize_manifest with an optional replay_inputs mapping
of safe non-reserved basenames to bytes. Existing callers and archive format stay
compatible. Include the CSV under its configured basename; forbid collisions with
source/config/SNAPSHOT/REPLAY reserved entries. Metadata hashes every archive entry.
The existing verifier must continue checking these archives without executing code.
Write completed manifest last. Document that source recovery, byte integrity,
execution replay and financial model validity establish different things.

## Required evidence and acceptance criteria

1. Pre-implementation full strict baseline; TDD for solver, quote validation,
   provenance extension and actual CLI behavior. No replacement of earlier tests.
2. Known call/put IV benchmarks and synthetic round trips across moneyness,
   tenor/volatility/negative rates, plus independent payoff-integral prices.
   Round-trip agreement alone is not the only correctness evidence.
3. Exact/near bounds, zero/short tenor, low vega, nonfinite/bool inputs, invalid
   settings, cap reached, iteration failure and numerical-range diagnostics.
4. Quote matrix covers timestamp offsets, naive datetimes, age/skew thresholds,
   crossed/locked/zero-bid quotes, unsupported styles/dividends/settlement/units,
   malformed cells, file errors, duplicates and all-rejected input.
5. MC uses ID-stable local RNG; reorder and repeat checks; original RNG unchanged;
   retained zero-SE diagnostics; counts and per-unit Greeks independently checked.
6. A predeclared synthetic example contains 16 rows: six regular/edge cases
   (call,put,negative-rate put,locked call,zero bid,poorly identified premium),
   and ten failure cases (crossed,stale,future,underlying skew,American,nonzero
   dividend,physical settlement,outside bounds,expired,malformed number).
   Do not label this dataset a market snapshot.
7. Run actual CLI, independently recompute row results/Greeks/what-if values and
   integral price checks; verify all declared artifacts. Recover archived source
   and CSV into a new directory and actually replay numerical outputs; timings,
   timestamps and figures are not byte-replay targets.
8. Fresh review of the completed implementation, full strict suite, Thai worked
   guide, measured example findings and updated capability/status documents.

Success means trustworthy inversion/diagnostics within the declared domain and a
replayable input-to-report workflow. It does not mean a profitable options strategy,
support for arbitrary US ETF options, market-model validation or production sign-off.

## Process and repository boundaries

This is an architectural extension. Conversational design approval permits this
spec; written-spec review precedes implementation planning and coding under the
applicable brainstorming workflow. No implementation plan/product files are
created before that review. No new separate chat/project is requested.

The checkout resolves to unrelated parent Git root /Users/robot. Do not stage,
commit, branch or create worktrees in that repository. Preserve this spec and the
later plan/ledger locally, as in earlier project work. No new dependencies needed.

## Primary sources inspected

- SciPy brentq: bracket sign conditions, tolerances and convergence diagnostics:
  https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html
- OIC option price behavior: pricing inputs and interpretation of sensitivities:
  https://www.optionseducation.org/referencelibrary/faq/option-price-behavior
- OCC equity contracts: American exercise, units and delivery differ from this model:
  https://www.theocc.com/clearance-and-settlement/clearing/equity-options-product-specifications

Accessed 23 October 2026. Existing conventions: docs/RESEARCH_SPEC.md;
current evidence: docs/PROGRESS.md and reports/final/.

## Spec self-review

- Intent preserved: usable option analysis / numerical engineering, no stock allocation.
- Inputs/outputs/units/clock/solver statuses and unsuccessful cases are explicit.
- No implied promise of American/dividend support or observed real-market results.
- MC repricing is explicitly conditional, not an independent market-value discovery.
- CSV is included in recoverable replay inputs; previous demos retain compatible calls.
- No implementation placeholders or unchosen alternatives remain in this design.
- Fresh existing-suite baseline: 390 passed in 25.06s, warnings treated as errors.
  Only this specification has been added; no new pricing implementation is claimed.
