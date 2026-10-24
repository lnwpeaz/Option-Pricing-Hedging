# V2-A design: path-dependent Asian pricing and randomized QMC

Status: written spec approved by the user on 24 October 2026; implementation plan and inline execution approved the same day. Executed V2-A evidence is
recorded in the paired plan ledger and reports/examples/v2-asian/.
Date: 24 October 2026 (Asia/Bangkok).
Programme context: docs/PROJECT_V2_PROPOSAL_TH.md.

## สรุปสำหรับตรวจขอบเขต

ชิ้นแรกของ V2 จะเพิ่ม Asian options ที่ payoff ขึ้นกับราคาเฉลี่ยหลายเวลา
เพื่อให้ Monte Carlo เป็นวิธีคำนวณที่มีหน้าที่ชัดขึ้น เปรียบเทียบ 5 วิธีบน
สัญญาและงบงานเดียวกัน พร้อมตรวจความแม่น ช่วงความไม่แน่นอน เวลาและ memory
งานเดิม European/hedging และรายงานที่เสร็จแล้วจะเก็บไว้เหมือนเดิม

สิ่งที่ได้คือ reusable pricing/benchmark module พร้อม CLI/config/CSV/report
ไม่ได้เพิ่มการเทรด Asian options ให้บัญชีส่วนบุคคล และยังไม่รองรับ American,
barrier options, jumps หรือ IV จากข้อมูลตลาดในชิ้นนี้
สเปก IV เดิมเก็บเป็นทางเลือกย่อยและฐานของ V2-C ไม่ถือว่าถูกอนุมัติแล้ว

## Intent and alternatives

The user prioritizes Monte Carlo/Computer Engineering, wants distinct profile
value from Portfolio Quantitative Research, and requested a stronger scope than
the q=0 IV-only draft. This design deepens numerical research first; quote/IV and
model-risk hedging remain separate later slices with their own specifications.

Alternatives considered: (1) smaller IV-only tool; (2) path-dependent pricing plus
verified randomization and efficiency research (recommended first slice);
(3) full US equity-options tooling, requiring exercise/dividend/market-operation
work before broad real-account usefulness. No outcome is called globally best.

## Financial contract and model

European cash-settled fixed-strike arithmetic/geometric average-price calls/puts,
one underlying, unit multiplier, no dividends, constant annual r/sigma and exact
risk-neutral GBM. q=0 is a declared research domain, not arbitrary market coverage.

Fixings are explicit strictly increasing times 0<t1<...<tm=T. No past fixings or
running average; no initial spot in the average. Equal weights 1/m. Require finite
S0,K>0, T>0, sigma>=0 and finite r, with explicit numerical range failures.

Arithmetic A=(1/m)*sum(S_tj); geometric G=exp((1/m)*sum(log(S_tj))).
Call payoff=max(A-K,0), put=max(K-A,0), discounted by exp(-rT).
The geometric contract substitutes G for A. The observation schedule is part of
the contract; changing m changes the contract. Do not present a change in discrete
averaging as numerical convergence to the same continuously averaged payoff.

Exact GBM fixings eliminate Euler transition bias under this model. They do not
remove MC error, floating-point error or misspecification relative to a market.
European single-fixing T and sigma=0 limits are required acceptance cases.
Check the arithmetic expectation E[A]=S0*mean(exp(r*tj)), discounted-payoff bounds,
and pathwise A>=G (arithmetic call >= geometric call, arithmetic put <= geometric
put). These are independent financial checks, not replacements for price references.

## Independent geometric benchmark and control

For log G, use analytically derived mean and variance:

    a = log(S0) + (r - sigma^2/2) * mean(tj)
    b2 = sigma^2 / m^2 * sum_i sum_j min(ti,tj)

G is lognormal with these parameters; integrate its payoff or apply the derived
lognormal call/put formula with discount exp(-rT). Handle b2=0 directly. Derive and
validate formula and rate/discount conventions independently of the path sampler.

The arithmetic estimator may use discounted geometric payoff X as a control,
with its analytic expectation. Beta is fitted on an independent pilot, frozen for
production, and extra pilot paths/time counted. No arithmetic reference price is
used to fit beta. Do not clip the adjusted estimate or confidence bounds.

## Five predeclared methods

1. Plain pseudo-random exact-GBM MC.
2. Antithetic normal vectors; independent observations are pair-averaged payoffs.
3. Pseudo-random geometric-control MC with independent pilot.
4. Randomized Sobol (scrambled), chronological Brownian increments.
5. Randomized Sobol (scrambled), Brownian-bridge construction.

QMC/control combinations, importance sampling, MLMC, adaptive optional stopping,
GPU and automatic method selection are excluded from this first slice. A method
that underperforms is retained and reported, not silently removed.

Pseudo-random streams use explicit PCG64/SeedSequence identifiers. Sobol scramble
seeds/identifiers, dimension and generation mode are retained. Never use global
RNG or Python hash() for persistent identifiers. Repeats and control pilots are
independent by construction. Batching must not silently change estimator semantics.

## Randomized QMC uncertainty and work

Each result uses R=16 independent scrambles, n=2^p points per scramble and
total production evaluations N=R*n. All points in a scramble are part of the
same randomized quadrature rule; do not count them as IID observations for SE.

Estimate=mean(scramble price estimates). SE=sample_std(scramble estimates)/sqrt(R).
Report an approximate 95% Student-t interval with R-1 degrees of freedom, explicitly
identified as a finite-replicate approximation. Evaluate calibration across new
independent macro-repeats; no confidence guarantee is inferred from one interval.

Use Sobol base-2 generation without dropping the first point, thinning, arbitrary
non-power-of-two sample sizes or post-sampling optimization. Endpoint handling
for inverse normal must be explicit: no silent clipping that changes the rule.
If a finite normal transform cannot be constructed, return a numerical diagnostic.
Record bits=52 for this study, reducing the frequency of exact endpoints relative
to the library's lower default bit depth; endpoint guards still apply.

Methods 4/5 use identical Sobol points within a paired method-comparison replicate
and transform them differently. Independence is across scrambles/macro-repeats,
not between paired method outcomes. Retain raw scramble prices for verification.

Plain/antithetic/control receive the same N production payoff evaluations; count
control pilot work separately. Record total normals, payoff evaluations,
independent observations, scrambles and pilot work. Equal production N is not
claimed to be equal total work or equal wall-clock time.

## Brownian bridge and computational boundaries

Build W_T first, then interior observations conditional on already constructed
neighbors using exact Brownian means/variances on the explicit time grid. The
construction order is deterministic and documented. Validate nonuniform-grid
covariance Cov(W_ti,W_tj)=min(ti,tj), endpoint and deterministic identities.

Expose a pure transform from independent normals to fixing Brownian values; no
option formulas or RNG inside the transform. Chronological and bridge transforms
must both produce the declared GBM law, not identical sample paths for one Z vector.

Stream/batch arithmetic and geometric averages; do not retain all N*m paths for
pricing. Sobol generation can require O(n*m) arrays within one scramble; disclose
and measure this separately rather than claiming O(batch) memory for every method.
Retain result-level summaries and scramble prices, not all raw path matrices.

Use centered/scaled moments and log geometric averages; finite inputs whose
payoffs/moments are unrepresentable fail explicitly. Low/zero observed variance,
rare-payoff and deterministic cases have distinct diagnostics. Normal/t intervals
must not be clipped to price bounds or treated as market forecast bands.

## Modules and interfaces

- New Asian contract/result types isolated from existing OptionSpec/PriceEstimate.
- `pricing/asian_reference.py`: geometric closed form and deterministic limits.
- `simulation/brownian_bridge.py`: pure transform and explicit construction order.
- `pricing/asian_monte_carlo.py`: five methods, independent units and pilot logic;
  split QMC orchestration into a separate module if responsibility requires it.
- `experiments/asian_study.py`: strict config, predeclared grid, actual CLI,
  repeated estimates, measurements, reports and existing source provenance.
- Analysis metrics/plots separated from pricing; existing demos remain compatible.

This is the complete first-slice boundary. Later jump hedging, carry-aware quotes,
American mechanics and external-data ingestion do not alter this implementation.

## Reference strategy: do not hide reference uncertainty

Validate geometric payoffs using analytic formula, independent numerical payoff
integration and an external library where contract conventions match. Arithmetic
one-fixing reduces to existing European pricing; two-fixing cases use independent
low-dimensional quadrature with its numerical error disclosed.

For general multi-fixing arithmetic prices, use an external deterministic/independent
reference with an explicit convergence/error assessment, plus independent large
replicate estimates as cross-checks. A random high-path estimate is not exact truth.
Save reference intervals/error diagnostics; label RMSE relative to a noisy reference
as approximate and do not publish bias below its established reference precision.

QuantLib arithmetic discrete MC/control or finite-difference engines are candidate
comparators, not an automatic oracle. Pin a reviewed version and verify dates,
day count, past-fixing convention, averaging, dividends and discount assumptions.
Add the benchmark as an optional dev/research dependency only after implementation
planning; no requirement to install a system-wide library or compile unmanaged code.
If reference acceptance fails, retain comparison diagnostics and withhold ranking
claims that depend on treating that reference as exact.

## Predeclared experiment and practical outputs

Primary research grid: S0=100,T=1,r=.05,sigma=.20,q=0, arithmetic call, strikes
[90,100,110], fixing counts [12,52], production budgets
[4096,16384,65536], five methods, 32 independent macro-repeats per cell.
Control pilot=512 extra paths per macro-run. QMC R=16, n=N/16 (all powers of 2).
This gives 2,880 recorded estimates before independent reference diagnostics.
Primary fixing j uses integer day offset floor(365*j/m), divided by365, j=1..m.
These approximately equally spaced ACT/365F schedules allow date-based external
comparators to represent exactly the same observation times. Use a declared base
date and no business-day adjustment; this is a model contract, not an exchange calendar.

Separate deterministic/rare-payoff/put/nonuniform-grid validation cases remain
visible; they are not silently substituted for difficult primary-grid outcomes.
Benchmark a fixed representative contract after warm-up with alternating method
order, record raw repetitions and all work counts. Include RNG, path transform,
payoff and uncertainty for complete-estimator timing. Measure allocations in a
separate untimed pass and distinguish tracemalloc from RSS. No speedup guarantee.

Outputs: exact/effective config, raw estimates, raw scramble estimates, pilot
diagnostics, reference checks, aggregate accuracy/CI calibration, work/time/memory
measurements, comparison figures, results narrative and source/environment manifest.
Refuse overwriting completed runs. Same inputs in the recorded environment target
the same numerical results; timing/figures/environment portability are separate.

CLI/config support a single custom supported contract as well as the fixed study.
The user can provide spot, strike, rate, sigma and fixing schedule, then receive
a model price with uncertainty and compute diagnostics. No claim of executable
quotes, retail Asian-option availability or suitability for a real account.

## Acceptance evidence

- TDD for contracts, geometric reference, bridge, estimators, uncertainty and CLI.
- Hand-worked payoffs and exact deterministic/single-fixing cases.
- Geometric reference verified with independent integration; external conventions
  checked explicitly. Arithmetic references have visible precision diagnostics.
- Brownian mean/covariance checks across independent repeats, including irregular
  grids, plus deterministic transform identities; no brittle one-CI pass assertion.
- Antithetic pair units, independent pilot and QMC scramble-unit calculations
  independently recomputed from retained data. Degenerate SE remains visible.
- Fixed seed/call shape reproducibility, global RNG unchanged, no output overwrite;
  total work includes all scrambles and pilots. Actual source recovery and numerical
  replay demonstrated in the recorded environment.
- All predeclared cells retained; report uncertainty in empirical RMSE/coverage,
  reference precision and timing variability rather than select favorable cells.
- Fresh code review, full strict suite, Thai explanation and usable demonstration.

## Review and repository notes

The user approved this written spec before implementation planning. It supersedes
neither the completed v1 report nor its numerical evidence. The smaller IV draft
remains unapproved and deferred as described in the programme roadmap.
Project Git root still belongs to unrelated /Users/robot; do not commit/branch
there. Keep the spec/plan/ledger and evidence within this project directory.

Primary sources inspected 24 October 2026:

- https://github.com/lballabio/QuantLib/blob/master/Examples/AsianOption/AsianOption.cpp
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.qmc.Sobol.html

Spec self-review: purpose, payoff/schedule, independent units, work accounting,
reference uncertainty and component boundaries are explicit. Future modules are
separate. No promise of higher accuracy, market realism or production readiness
is made merely because a more advanced algorithm is present.
