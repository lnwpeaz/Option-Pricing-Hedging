# Asian Pricing and Randomized QMC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking. Native execution is recommended for this plan; execution approved 24 October 2026: inline implementation with one fresh final review.

**Goal:** Deliver a reusable, verified Asian-option pricing module and a five-method Monte Carlo research study with honest uncertainty, reference precision and computational measurements.

**Architecture:** New Asian contracts/reference functions remain separate from the completed European/hedge APIs. A pure Brownian transform and payoff kernel feed pseudo-random estimators and randomized Sobol estimators; an experiment runner retains raw evidence, independent references and reproducible reports.

**Tech Stack:** Python >=3.11, NumPy, SciPy (qmc/ndtri/t/quad), pandas/Matplotlib/pytest already installed; optional research-only QuantLib==1.44 wheel. No system-wide dependencies or broker connections.

**Spec:** `docs/superpowers/specs/2026-10-24-asian-rqmc-design.md` (written spec approved by the user on 24 October 2026).

## ผู้ใช้ตรวจส่วนนี้ก่อน

แผนแบ่งเป็น 7 งาน: สูตร/สัญญา -> Brownian paths/payoffs -> MC 3 วิธี -> Sobol
2 วิธี -> benchmark อิสระ -> โปรแกรมรัน/รายงาน -> ทดลองเต็มและตรวจซ้ำ
ทุกงานมี tests ที่ต้องเห็นล้มเหลวก่อนเพิ่ม implementation แล้วตรวจผ่าน

ผลส่งมอบหลักคือใส่เงื่อนไข Asian option แล้วได้ราคา ช่วงความไม่แน่นอนและ
ข้อมูลการคำนวณ พร้อมงานวิจัยครบ 2,880 estimates ไม่เพิ่ม American options,
portfolio optimizer, jump hedging หรือ IV ในชิ้นนี้

แนะนำให้ทำงานหลักในแชตนี้ต่อเนื่อง และมีรีวิวอิสระท้ายงานหนึ่งรอบ เพราะแต่ละงาน
ใช้ interfaces ต่อกัน การแยก implementer/reviewer ทุกชิ้นจะเพิ่มค่าใช้จ่ายจาก
การอ่านบริบทซ้ำ หลังตรวจแผนให้เลือกวิธีดำเนินงานในคำถามประกอบ

## Global Constraints

- European cash-settled fixed-strike arithmetic/geometric average-price calls/puts, one underlying, unit multiplier, no dividends, constant annual r/sigma and exact risk-neutral GBM.
- Fixings are explicit strictly increasing times 0<t1<...<tm=T. No past fixings or running average; no initial spot in the average. Equal weights 1/m.
- Five methods: plain, antithetic, independent-pilot geometric control, scrambled Sobol increments, scrambled Sobol Brownian bridge.
- Each QMC result uses R=16 independent scrambles, n=2^p points per scramble and total production evaluations N=R*n; record bits=52.
- No clipping of estimates/CIs, no dropping the first Sobol point, no silent endpoint resampling, no adaptive optional stopping or favorable-seed selection.
- Primary grid: S0=100,T=1,r=.05,sigma=.20,q=0; arithmetic call; strikes [90,100,110]; fixing counts [12,52]; production budgets [4096,16384,65536]; 32 macro-repeats; control pilot=512.
- Primary fixing j uses floor(365*j/m)/365, j=1..m; base date 2026-10-24, ACT/365F, no business-day adjustment. Exactly 2,880 primary estimates.
- Existing v1 APIs/tests/examples/report bytes remain intact. No new runtime dependency; QuantLib is a pinned optional research extra only.
- Project Git root is unrelated `/Users/robot`. Do not stage, commit, branch, create a worktree or run Git workspace scripts there. Record checkpoints in this plan's project-local ledger.
- No product code/dependency installation before plan review and execution-method selection. A code block in this document is a future action, not an executed change.

## Review Focus

1. A rare payoff with zero observed sample variance must not be presented as an exact price; deterministic sigma=0 is a distinct status (Tasks 3/4).
2. RQMC points within one scramble are dependent; SE/CI must use scramble estimates and refuse invalid N/R or normal-transform endpoints (Task 4).
3. A one-day external fixing shift or accidental inclusion of S0 changes the contract, even if two prices are close (Task 5).
4. Reference uncertainty comparable to a method's RMSE must remain visible; rankings/coverage claims must not treat an empirical reference band as exact truth (Task 6).
5. Finite inputs can produce unrepresentable moments/payoffs or erase tiny currency values; report explicit range errors rather than zero uncertainty (Tasks 1/2/3).

## Workspace and verification conventions

Create `docs/superpowers/plans/2026-10-24-asian-rqmc-progress.md` at execution time.
Its first line names this plan. Record task starts, RED/GREEN commands, rulings,
checkpoints and evidence paths. Keep prior plans/ledgers untouched. Before edits,
capture a project-local source/test/config snapshot without copying `.venv`, Git,
market secrets or generated run folders. No parent-repository mutations.

All pytest commands below use project `.venv` and warnings as errors. In a shell:

```sh
export MPLCONFIGDIR=/private/tmp/option-hedging-mpl-cache
export XDG_CACHE_HOME=/private/tmp/option-hedging-cache
export PYTHONPATH=src
.venv/bin/python -m pytest -q -W error
```

Expected baseline: the existing 390 tests pass; record the actual fresh output.
If it differs, diagnose the existing state before feature implementation.
Task checkpoint = completed tests and file SHA-256s in the ledger, not a Git commit.

## File and responsibility map

| File | Responsibility |
|---|---|
| `src/option_hedging/asian_contracts.py` | Immutable Asian contract and estimate/work diagnostics |
| `pricing/asian_reference.py` | Geometric closed form, deterministic average, arithmetic bounds |
| `validation/asian_reference.py` | Independent geometric/two-fixing integration |
| `simulation/brownian_bridge.py` | Pure increments/bridge normal-to-Brownian transforms |
| `pricing/asian_samples.py` | Discounted arithmetic/geometric payoff kernel |
| `pricing/_asian_statistics.py` | Scaled batch mean/covariance accumulation and CI helper |
| `pricing/asian_monte_carlo.py` | Public five-method dispatcher and pseudo-random methods |
| `pricing/asian_rqmc.py` | Independent scrambles, Sobol transforms and t uncertainty |
| `validation/asian_quantlib.py` | Optional pinned external comparator and precision diagnostics |
| `analysis/asian_metrics.py` | Macro-repeat summaries, reference-aware diagnostics and bootstrap |
| `analysis/asian_plots.py`, `analysis/asian_report.py` | Figures and executed report |
| `experiments/asian_study.py`, `experiments/asian_benchmarks.py` | Strict CLI/config, orchestration and measurements |
| `configs/asian_study.toml`, `configs/asian_custom.toml` | Fixed research grid and editable single-contract example |
| `requirements-research.txt`, `pyproject.toml` extra | Optional QuantLib pin, not base runtime |
| `docs/ASIAN_MONTE_CARLO_TH.md` | Concepts, measured results and use instructions |

Paths without the `src/option_hedging/` prefix in the map are inside that package.
Source files should stay focused. Split only when responsibility warrants it;
record any interface/file change in the ledger and update dependent tasks.

## Interface contracts used across tasks

`AsianOptionSpec(spot, strike, risk_free_rate, volatility, kind, fixing_times,
averaging='arithmetic')` is frozen, normalizes numbers to float and fixings to an
immutable tuple. `kind` is call/put; averaging is arithmetic/geometric;
`maturity_years` is the final fixing. Preserve bool/string/NaN/complex rejection.

`AsianEstimate` is frozen with fields `price,standard_error,ci_low,ci_high,method,
status,requested_paths,production_paths,independent_samples,pilot_paths,
normal_coordinates,payoff_evaluations,control_payoff_evaluations,scrambles,
pilot_beta,scramble_prices,diagnostics`. Last two collections are immutable tuples.
No NaN/Infinity serialization. An absent beta is None. `pilot_beta` is in normalized
payoff units; price/control use the same S0 scale so beta has no currency factor.

Work definitions: production_paths and pilot_paths count actual transformed paths;
payoff_evaluations counts target payoffs (production+pilot); control_payoff_evaluations
counts extra geometric payoffs; normal_coordinates counts newly generated normal
coordinates or inverse-CDF coordinates (antithetic opposites do not add RNG work).
For QMC independent_samples=scrambles=R, not N. Deterministic sigma=0 returns
status='deterministic', exact point interval, requested_paths=N but all actual work
counts zero, no pilot/beta and no RNG consumption. A sampled zero-SE case instead
keeps status='sampled' and diagnostic 'zero_observed_variance'.

Public dispatcher:

```python
def price(spec: AsianOptionSpec, *, n_paths: int,
          rng: np.random.Generator, method: str = 'plain',
          batch_size: int = 1024, pilot_paths: int = 512,
          scrambles: int = 16, bits: int = 52) -> AsianEstimate: ...
```

Method names are exactly `plain`, `antithetic`, `control`, `sobol`, `sobol_bridge`.
Validate all numeric settings even for deterministic pricing; reject bools.
Control requires arithmetic averaging (the geometric reference itself is analytic).

### Task 1: Asian contracts and independent geometric/deterministic references

**Files:** Create `asian_contracts.py`, `pricing/asian_reference.py`,
`validation/asian_reference.py`; create `tests/test_asian_reference.py`.

**Interfaces:**
- Consumes: existing `OptionSpec`, `black_scholes.price` only in tests; SciPy quad/log_ndtr.
- Produces: types above; `geometric_log_moments(spec)->tuple[float,float]`,
  `geometric_price(spec)->float`, `deterministic_price(spec)->float`,
  `arithmetic_bounds(spec)->tuple[float,float]`;
  independent `integrate_geometric(spec)` and `integrate_two_fixing(spec)` returning
  frozen `IntegralReference(price,error_estimate,tail_bound,evaluations)`.

- [x] **1. Write boundary and reference tests first.** Include these real checks
  and parametrized invalid inputs (empty/repeated/unsorted/nonpositive/boolean/
  NaN/string/complex fixings; invalid averaging/kind/rates/spot/volatility):

```python
def test_geometric_single_fixing_matches_independent_european_baseline():
    s = AsianOptionSpec(100, 100, .05, .20, 'call', (1.0,))
    assert geometric_price(s) == pytest.approx(10.450583572185565, abs=1e-10)

def test_log_covariance_on_nonuniform_grid_is_direct_double_sum():
    s = AsianOptionSpec(100, 95, -.02, .30, 'put', (.1, .4, 1.0))
    a, b2 = geometric_log_moments(s)
    assert a == pytest.approx(math.log(100)+(-.02-.30**2/2)*.5)
    assert b2 == pytest.approx(.30**2/9 * sum(min(x,y) for x in s.fixing_times for y in s.fixing_times))

@pytest.mark.parametrize('kind', ['call', 'put'])
def test_deterministic_average_uses_all_fixings(kind):
    s = AsianOptionSpec(120, 125, .04, 0, kind, (.25,.5))
    a = (120*math.exp(.04*.25)+120*math.exp(.04*.5))/2
    payoff = max(a-125,0) if kind=='call' else max(125-a,0)
    assert deterministic_price(s) == pytest.approx(math.exp(-.04*.5)*payoff)
```

- [x] **2. Run RED.** `.venv/bin/python -m pytest tests/test_asian_reference.py -q -W error`.
  Expected: import failure for the absent new Asian modules; existing baseline is unchanged.
- [x] **3. Implement contracts/reference functions.** Use frozen dataclasses and
  explicit validation. Compute log moments without a mandatory m*m allocation:

```python
t = np.asarray(spec.fixing_times)
a = math.log(spec.spot)+(spec.risk_free_rate-.5*spec.volatility**2)*float(t.mean())
weights = 2*(len(t)-np.arange(len(t)))-1
b2 = spec.volatility**2*float(np.dot(weights,t))/len(t)**2
# Discounted lognormal call: exp(a+b2/2-rT)*Phi(d1)-K*exp(-rT)*Phi(d2).
# Recover the ITM leg by parity; use log-CDF/expm1 differences for tail prices.
```

  Deterministic limits use the actual average. Arithmetic bounds use discounted
  E[A]=S0*mean(exp(r*t)); call lower=max(discount*E[A]-discount*K,0),
  upper=discount*E[A]; put lower=max(discount*K-discount*E[A],0), upper=discount*K.
  Reject unrepresentable arithmetic explicitly, including false zero underflow.

  Independent integration must not call the new closed form/payoff/GBM modules.
  Geometric integration forms log covariance directly and integrates normal payoff
  with separate tail bounds. For two arithmetic fixings integrate over Z1, handling
  the conditional strike L=2K-S1 analytically with a standalone CDF formula for S2.
  If L<=0, conditional call payoff is (S1+E[S2|S1])/2-K and put is zero. Integrate
  over [-12,12], split at the L=0 boundary and density centers; save QUADPACK's
  estimate and a separate omitted-normal-tail bound. Neither is a full rigorous
  floating-point guarantee.
- [x] **4. Add integration comparisons and run GREEN.** Call/put, negative r,
  irregular fixings, m=1 and sigma=0; test tiny positive geometric prices are retained
  or explicitly rejected, never silently changed to zero.
  Run the focused file, then the full strict suite. Expected: all pass.
- [x] **5. Checkpoint.** Save commands/results and file digests to this plan's ledger.

### Task 2: Brownian transforms and paired payoff kernel

**Files:** Create `simulation/brownian_bridge.py`, `pricing/asian_samples.py`;
create `tests/test_brownian_bridge.py`, `tests/test_asian_samples.py`.

**Interfaces:**
- Consumes: `AsianOptionSpec` and validated fixing times from Task 1.
- Produces: `brownian_from_normals(normals, fixing_times, *, construction='increments')`
  returning float64 shape(B,m), excluding W0; `discounted_payoffs(spec,normals,
  *,construction='increments')->tuple[np.ndarray,np.ndarray]` returning discounted
  arithmetic/geometric payoffs in units of S0. It never calls a pricer or RNG.

- [x] **1. Write deterministic transform/payoff tests before implementation.**

```python
@pytest.mark.parametrize('construction', ['increments','bridge'])
def test_transform_has_exact_brownian_covariance(construction):
    t=np.array([.05,.2,.7,1.0])
    transform=brownian_from_normals(np.eye(4),t,construction=construction)
    assert transform.T@transform == pytest.approx(np.minimum.outer(t,t),abs=2e-15)
    if construction=='bridge':
        assert transform[:,-1] == pytest.approx([1,0,0,0],abs=1e-15)

def test_increments_are_cumulative_on_irregular_grid():
    w=brownian_from_normals(np.array([[1.,-2.]]),(.25,1.0))
    assert w[0] == pytest.approx([.5,.5-2*math.sqrt(.75)])
```

  Also test hand-worked A/G payoffs, single fixing, sigma=0, shape/type/finite
  rejection and nonmutation of supplied normal arrays. Use independently computed
  example price paths, not the function under test as the expected value.
- [x] **2. Run RED.** Run both new test files; expected absent-module/API failures.
- [x] **3. Implement exact transforms and kernel.** Chronological increments:

```python
w=np.cumsum(z*np.sqrt(np.diff(np.r_[0.,t])),axis=1)
log_s=math.log(spec.spot)+(spec.risk_free_rate-.5*spec.volatility**2)*t+spec.volatility*w
log_a=logsumexp(log_s,axis=1)-math.log(len(t))
log_g=np.mean(log_s,axis=1)
```

  Bridge: set W0=0, W_T=sqrt(T)*z[:,0]; process a FIFO queue of index intervals,
  choose mid=(left+right)//2 and fill

```python
mean=((tr-tm)*wl+(tm-tl)*wr)/(tr-tl)
variance=(tm-tl)*(tr-tm)/(tr-tl)
wm=mean+math.sqrt(variance)*z[:,next_coordinate]
```

  Queue left then right subintervals; skip intervals without an interior index.
  Use real times for the weights. Transform log averages to discounted normalized
  payoffs with positive log differences/expm1; guard representability.
- [x] **4. Add repeated-ensemble mean/covariance checks and range tests.** Use fixed
  independent seeds with analytic covariance and declared ensemble tolerances;
  do not require one random CI to cover. Check A>=G and call/put payoff ordering
  before control adjustment, and useful numerical failures for extreme inputs.
  Run both files and the full strict suite; expected all pass.
- [x] **5. Checkpoint transform order, tests and digests in the ledger.**

### Task 3: Three pseudo-random estimators with correct work/uncertainty

**Files:** Create `pricing/_asian_statistics.py`, `pricing/asian_monte_carlo.py`;
create `tests/test_asian_monte_carlo.py`.

**Interfaces:**
- Consumes: Task 1 types/reference, Task 2 normalized arithmetic/geometric samples.
- Produces: public `price(...)` signature above for methods plain/antithetic/control;
  independent-pilot fit and a numerical moment helper reused by Task 4.

- [x] **1. Write reconstruction tests first.** Build expected observations using
  a separate RNG with the same recorded call shape; verify sample SE from actual
  independent units. Example plain test:

```python
def test_plain_reconstructs_all_independent_observations():
    s=AsianOptionSpec(100,100,.05,.2,'call',(.25,.5,1.))
    rng=np.random.Generator(np.random.PCG64(17))
    y,_=discounted_payoffs(s,rng.standard_normal((64,3)))
    result=price(s,n_paths=64,rng=np.random.Generator(np.random.PCG64(17)),batch_size=64)
    assert result.price==pytest.approx(100*y.mean(),abs=1e-12)
    assert result.standard_error==pytest.approx(100*y.std(ddof=1)/8,abs=1e-12)
    assert result.independent_samples==64
```

  Antithetic tests independently average y(z)/y(-z) before SE. Control tests
  reconstruct pilot covariance, frozen beta, disjoint production and all work
  counters. Include nondivisible batches and singleton final batches.
- [x] **2. Run RED.** New estimator tests fail for absent APIs.
- [x] **3. Implement stable batch statistics and estimators.** Use centered merge
  moments/covariance in normalized payoff units; never subtract raw E[Y²]-E[Y]².

```python
y,x=discounted_payoffs(spec,z)
opposite,_=discounted_payoffs(spec,-z)
pair_observation=.5*y+.5*opposite
beta=pilot_cov_yx/pilot_var_x if pilot_var_x>0 else 0.0
adjusted=y-beta*(x-geometric_price(spec)/spec.spot)
se=np.std(independent_observations,ddof=1)/math.sqrt(n_independent)
low,high=mean-1.959963984540054*se,mean+1.959963984540054*se
```

  Beta is fitted on extra pilot draws before fresh production. Plain/control
  production uses N observations; antithetic uses N/2 pairs and N transformed paths.
  Scale final mean/SE by S0 with underflow guards. Preserve negative adjusted prices
  and CIs. Validate N>=2, antithetic even N>=4, batch>=2, pilot>=2 and Generator type.
- [x] **4. Add Review Focus cases.** Deterministic sigma=0 uses no RNG or work;
  stochastic rare zero-payoff samples retain zero-SE warning. Include geometric
  averaging with noncontrol methods, reject control on geometric contracts, global
  RNG unchanged, fixed seeds, invalid settings, tiny finite payoffs and moment overflow.
  Run focused and whole strict suite; expected all pass.
- [x] **5. Record RED/GREEN, counts and checkpoint digests.**

### Task 4: Scrambled Sobol methods and Student-t uncertainty

**Files:** Create `pricing/asian_rqmc.py`; modify dispatcher in
`pricing/asian_monte_carlo.py`; create `tests/test_asian_rqmc.py`.

**Interfaces:**
- Consumes: Task 1 `AsianEstimate`, Task 2 kernel/bridge and Task 3 validation helpers.
- Produces: same `price` result for `sobol`/`sobol_bridge`, with raw immutable
  `scramble_prices` tuple. Private QMC entry accepts the same N/rng/batch/R/bits.

- [x] **1. Write scramble-unit tests.** Directly verify the estimate and Student-t CI:

```python
def test_qmc_uncertainty_uses_scrambles_not_points():
    s=AsianOptionSpec(100,100,.05,.2,'call',(.2,.6,1.))
    r=price(s,n_paths=256,method='sobol',scrambles=16,
            rng=np.random.Generator(np.random.PCG64(61)))
    means=np.asarray(r.scramble_prices)
    se=means.std(ddof=1)/4
    assert r.independent_samples==16 and r.production_paths==256
    assert r.standard_error==pytest.approx(se,abs=1e-12)
    assert r.ci_high-r.price==pytest.approx(scipy.stats.t.ppf(.975,15)*se,abs=1e-12)
```

  Reconstruct Sobol uniform points independently from recorded child entropy.
  For methods 4/5 use separate same-key parent Generators and verify shared base
  uniforms, while transformed Brownian paths differ appropriately.
- [x] **2. Run RED.** Expected missing QMC implementation/method failures.
- [x] **3. Implement R independent scrambles.** Derive an array of R independent
  four-word child entropies from the supplied parent Generator before path work.

```python
for entropy in child_entropies:
    child=np.random.Generator(np.random.PCG64(np.random.SeedSequence(entropy)))
    sampler=qmc.Sobol(d=m,scramble=True,bits=52,rng=child)
    u=sampler.random_base2(int(math.log2(N//R)))
    if np.any((u<=0)|(u>=1)):
        raise ValueError('Sobol endpoint cannot be mapped to a finite normal')
    z=scipy.special.ndtri(u)
    # Batch the payoff transform without thinning/reordering points.
    # Save one currency-valued mean for this scramble.
```

  Require R>=2, N divisible by R and N/R a power of two; the study fixes R=16/bits52.
  Permit configured supported bit depths only up to52 and N/R<=2**bits; record bits.
  Validate every setting even for sigma=0. Compute SE and approximate t interval
  from currency-valued scramble prices using scaled centered moments.
  No retry, clipping, seed selection or IID SE on point payoffs.
- [x] **4. Add error and repeat tests.** R=1, nonpower N/R, bools, endpoint injection
  at the pure normal-transform boundary, zero SE, numerical overflow, deterministic
  no RNG consumption, row/batch policy and independent macro-repeats. Check
  geometric/single-fixing repeated diagnostics against analytic benchmarks with
  finite-repeat intervals; never require every CI to cover truth.
  Run focused/full strict suite; expected all pass.
- [x] **5. Checkpoint the exact RNG derivation and paired Sobol contract.**

### Task 5: Independent multi-fixing benchmark and reference precision

**Files:** Create `validation/asian_quantlib.py`, `tests/test_asian_quantlib.py`,
`requirements-research.txt`; add optional `[project.optional-dependencies].research`
to `pyproject.toml`. Extend provenance's recorded optional pins/files without
changing existing caller signatures; exercise the new captured archive in tests.

**Interfaces:**
- Consumes: `AsianOptionSpec`, actual ACT/365F fixing dates, independent integral
  references from Task 1. QuantLib is lazy-imported only by this optional module.
- Produces: `reference_price(spec, *, base_date, settings)->ReferenceResult` and
  `external_checks(spec, *, base_date, settings)->list[dict]`. ReferenceResult fields:
  `price,precision_radius,precision_kind,status,diagnostics` (all serializable,
  absent values None). `precision_kind='empirical_cross_method'` is not a rigorous bound.

- [x] **1. Install the pinned research wheel locally after plan approval.**

```sh
.venv/bin/python -m pip install --only-binary=:all: 'QuantLib==1.44'
.venv/bin/python -c "import QuantLib as ql; print(ql.__version__)"
```

  Expected: 1.44 in this project's environment. This version has an arm64 macOS
  cp39-abi3 wheel listed by PyPI; do not compile or install system-wide if it fails.
  Record a genuine unavailable comparator, not an invented benchmark pass.
- [x] **2. Write external agreement and convention tests first.** Geometric call/put
  and m=1 agree with independently validated references; negative rates and m=2
  match independent integration. Assert every external date maps back exactly to
  the spec's ACT/365F time. A deliberate one-day mismatch must be rejected before
  comparing prices. Save/restore QuantLib's global evaluation date in try/finally.
- [x] **3. Run RED.** Expected absent adapter APIs. Then implement the explicit process:

```python
dc=ql.Actual365Fixed()
spot=ql.QuoteHandle(ql.SimpleQuote(spec.spot))
r=ql.YieldTermStructureHandle(ql.FlatForward(base_date,spec.risk_free_rate,dc))
q=ql.YieldTermStructureHandle(ql.FlatForward(base_date,0.0,dc))
vol=ql.BlackVolTermStructureHandle(ql.BlackConstantVol(base_date,ql.NullCalendar(),spec.volatility,dc))
process=ql.BlackScholesMertonProcess(spot,q,r,vol)
dates=[base_date+day for day in exact_day_offsets]
payoff=ql.PlainVanillaPayoff(ql.Option.Call if spec.kind=='call' else ql.Option.Put,spec.strike)
option=ql.DiscreteAveragingAsianOption(ql.Average.Arithmetic,0.0,0,dates,payoff,ql.EuropeanExercise(dates[-1]))
```

  Only accept times representable exactly by these dated conventions, within
  1e-14 year tolerance; report unsupported reference schedule for arbitrary custom
  fixings, while still allowing numerical pricing. Geometric uses the matching
  average type and no past observations. Verify the installed 1.44 signatures.

  For six primary contracts predeclare FD grids (100,100,80), (200,200,160),
  (400,400,320); Choi lambda 5/10/15 with max integration steps2**21; independent
  QuantLib pseudo-MC control cross-check at262144 paths, seeds9101/9102/9103/9104.
  Retain every result, reported MC errors and timings. No engine chosen because
  it agrees best with our estimator. Choi finest is the reference point; empirical
  radius is max(2*last Choi change,2*last FD change,abs(last Choi-last FD)).
  A finite radius is an empirical precision assessment, not a proven error bound.
  Flag low_precision if radius>5e-4, nonconvergence, invalid financial bounds or
  material MC cross-check disagreement (aggregate3SE+empirical radius criterion).
  Save all diagnostics; withhold accuracy rankings that depend on an inadequate
  reference. A changing reference engine/grid is a recorded ruling and full rerun,
  never a silent improvement selected after seeing our primary results.
- [x] **4. Add optional dependency and source-recovery tests.** Missing QuantLib
  produces unavailable status for external checks, with no base-package import
  failure. Tests that require it are explicit; the full research acceptance must
  actually run them with the pin installed. Archive records the optional version
  and requirements-research.txt when present, preserving old verifier compatibility.
  Run focused and full strict suite; expected all pass, with real benchmark evidence.
- [x] **5. Checkpoint conventions, comparator version and precision limits.**

### Task 6: Research metrics, real runner, custom pricing and measured figures

**Files:** Create `analysis/asian_metrics.py`, `analysis/asian_plots.py`,
`analysis/asian_report.py`, `experiments/asian_study.py`, `experiments/asian_benchmarks.py`,
`configs/asian_study.toml`, `configs/asian_custom.toml`; create
`tests/test_asian_metrics.py`, `tests/test_asian_study.py`.

**Interfaces:**
- Consumes: `price`, `ReferenceResult`, external raw checks and existing
  `finalize_manifest`/`verify_run`. No old MC metrics import: it hardcodes 3 methods.
- Produces: `run_study(config_path:Path,output_dir:Path)->Path`; actual CLI
  `python -m option_hedging.experiments.asian_study --config ... --output-dir ...`.
  Internal mode='study' runs the fixed/configured grid; mode='custom' runs one
  explicit contract over the configured methods/budgets. No live market data.

- [x] **1. Write hand-derived metric and real-run tests.** For errors[-1,0,1],
  point RMSE=sqrt(2/3). Reference interval [-.2,.2] makes an estimate CI[-.1,.1]
  possibly but not definitely covered. A wholly disjoint interval is neither.
  Zero denominator gains are None. Recompute the paired Sobol-bridge/forward
  difference bootstrap from identical macro-ID resamples; do not independently
  resample the paired methods.

```python
def test_real_small_study_preserves_all_cells_and_counts(tmp_path):
    cfg=write_small_config(tmp_path,fixings=[2],strikes=[100.0],
          budgets=[64,256],repeats=4,scrambles=4,methods=ALL_FIVE_METHODS)
    out=run_study(cfg,tmp_path/'out')
    rows=read_csv(out/'estimates.csv')
    assert len(rows)==1*1*2*4*5
    assert len(read_csv(out/'scramble_estimates.csv'))==1*1*2*4*2*4
    assert verify_run(out)['source_recoverable'] is True
```

  Helpers contain the actual small config using the schema below. Add repeated
  numerical-run equality excluding timing, CLI execution and overwrite refusal;
  malformed/unknown config keys fail before a completed output manifest.

  Define the test helpers explicitly (imports csv/json/Path are standard library):

```python
def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))

def write_small_config(tmp_path,*,fixings,strikes,budgets,repeats,scrambles,methods):
    text=(
        '[option]\nspot=100.0\nrisk_free_rate=0.05\nvolatility=0.20\n'
        'kind="call"\naveraging="arithmetic"\ndividend_yield=0.0\n'
        '[study]\nmode="study"\nbase_date="2026-10-24"\n'
        f'fixing_counts={json.dumps(fixings)}\nstrikes={json.dumps(strikes)}\n'
        f'production_paths={json.dumps(budgets)}\nmethods={json.dumps(methods)}\n'
        f'repeats={repeats}\nscrambles={scrambles}\n'
        'seed=123\nbatch_size=32\npilot_paths=16\nsobol_bits=52\nbootstrap_repeats=64\n'
        '[reference]\nexternal_enabled=false\nquantlib_version="1.44"\nprecision_target=0.0005\n'
        '[benchmark]\nenabled=false\npaths=256\nfixing_count=2\nstrike=100.0\n'
        'batch_sizes=[16,32]\nrepeats=3\nseed=124\n')
    path=tmp_path/'small.toml'
    path.write_text(text)
    return path
```

  ALL_FIVE_METHODS is the ordered list of the five exact public method names in
  the interface section. `external_enabled=false` disables QuantLib work, not
  the available internal geometric/single-/two-fixing checks. Always save a clear
  external-check-not-requested status and retain the other evidence.
- [x] **2. Run RED.** Expected absent analysis/runner functions.
- [x] **3. Implement strict TOML schema and fixed RNG keys.** Canonical research config:

```toml
[option]
spot=100.0
risk_free_rate=0.05
volatility=0.20
kind="call"
averaging="arithmetic"
dividend_yield=0.0
[study]
mode="study"
base_date="2026-10-24"
fixing_counts=[12,52]
strikes=[90.0,100.0,110.0]
production_paths=[4096,16384,65536]
methods=["plain","antithetic","control","sobol","sobol_bridge"]
repeats=32
seed=20261024
batch_size=1024
pilot_paths=512
scrambles=16
sobol_bits=52
bootstrap_repeats=2000
[reference]
external_enabled=true
quantlib_version="1.44"
precision_target=0.0005
[benchmark]
enabled=true
paths=65536
fixing_count=52
strike=100.0
batch_sizes=[256,1024,4096]
repeats=7
seed=20261025
```

  Study time grid is fixed floor(365*j/m)/365. Custom mode replaces fixing_counts
  with explicit fixing_times and base_date remains explicit for optional reference
  alignment; one strike comes from a single-entry strikes list. No silent schedule
  rounding, exercise inference or nonzero dividend acceptance.

  SeedSequence key: [80,fixing_count_or_custom_id,strike_index,N,macro_repeat,
  stream_method_id,seed]; stream_method_ids plain0/antithetic1/control2/Sobol3.
  sobol_bridge shares stream_method_id3 with sobol; fresh same-key parent Generators
  reproduce paired base uniform points. Control pilot/production draws remain
  disjoint. Seeds vary with budget; no unannounced nested-budget dependence.
  For custom fixings, custom_id is the unsigned little-endian integer from the
  first8bytes of SHA256(JSON fixing tuple with separators=(',',':')); never hash().

  Write every requested estimate row or an explicit failed status with reason,
  not a dropped cell. Summary separates requested/completed/failed counts.
  Save raw scramble rows and pilot beta/work for each estimate. Keep timing fields
  out of numerical-only CSVs; stage/benchmark timing is in separate artifacts.

  Metrics group by contract/N/method and retain macro IDs. Report empirical SD,
  bias/RMSE against reference point (marked approximate where applicable), bootstrap
  intervals from shared macro-ID resampling, Wilson coverage against an exact
  reference where available, and possible/definite coverage against empirical
  reference bands. A conditional RMSE sensitivity range is

```python
point_rmse=np.sqrt(np.mean((estimates-ref_point)**2))
conditional_rmse_range=(max(0.0,point_rmse-ref_radius),point_rmse+ref_radius)
# This range is conditional on the reference band containing truth; not a new CI.
```

  Do not call an empirical reference band exact. Mark reference_dominates_error
  when its radius exceeds0.1*point_RMSE, or the reference status is low_precision
  or unavailable. Then withhold precision-dependent rankings and report sampling
  dispersion/work/time instead. Include zero-SE counts and failed estimates.
  Show path-normalized, total-payoff-normalized and time*RMSE² diagnostics with
  their precise work definitions; no single counter is treated as total FLOPs.

  Complete-estimator benchmark includes RNG, transform, payoffs and uncertainty.
  Warm each method; alternate forward/reverse method order across7repetitions;
  allocation measurement is a separate untimed tracemalloc pass. Preserve all raw
  times and measured peaks; no total-RSS or universal-speedup claim.

- [x] **4. Produce real output artifacts.** `estimates.csv`, `scramble_estimates.csv`,
  `reference_checks.csv`, `reference_summary.csv`, `metrics.csv`,
  `paired_comparisons.csv`, `benchmark.csv`, `allocations.csv`, `summary.json`,
  `effective_config.json`, `input_config.toml`, `RESULTS.md`, four figures
  (accuracy/calibration/efficiency/reference precision), source_snapshot.zip and
  manifest.json written last. Empty tables retain headers. Manifest declares all
  numerical acceptance/failed counts separately from byte-write completion.
- [x] **5. Run focused/full strict tests and visually inspect the small-run figures.**
  Include mixed method failures without grid pruning, reference-unavailable reporting,
  custom unsupported external-date alignment and paired QMC reconstruction tests.
  Expected: actual CLI works, all numerical tests pass, hashes/source recovery verify.
- [x] **6. Record the complete output schema and checkpoint.**

### Task 7: Execute the fixed research, independent checks, replay and final review

**Files:** New outputs under `reports/examples/v2-asian/` (must not exist),
new proof `reports/verification/v2-asian-checks.json`,
new `docs/ASIAN_MONTE_CARLO_TH.md`; update README, PROGRESS, ROADMAP, architecture,
interfaces, reproducibility and tests guide with measured capabilities only.

**Interfaces:** Consumes actual runner/config/artifacts from Task 6; produces
the executed evidence and usable demonstration. No invented numerical targets.

- [x] **1. Fresh full verification before the research run.**

```sh
.venv/bin/python -m pytest -q -W error
.venv/bin/python -W error -m option_hedging.experiments.asian_study \
  --config configs/asian_study.toml --output-dir reports/examples/v2-asian
.venv/bin/python -m option_hedging.experiments.verify_run reports/examples/v2-asian
```

  Expected: suite passes; 2,880 primary estimate records and 18,432 scramble records
  (2QMC*6contracts*3budgets*32macro*16scrambles), plus honest failed-status counts
  if a numerical/reference limit occurs. A zero-failure goal is checked, not assumed.
  Full research runtime is measured; give concise progress at most60seconds apart.
  Never shrink the grid after seeing which cases are slow or unfavorable.
- [x] **2. Independently verify saved numerical evidence.** Recompute every QMC
  estimate/SE/t interval from raw scramble means, all macro metric points, bootstrap
  endpoints, paired differences/work counts and reference-precision classifications.
  Check single-fixing, geometric, sigma=0, put and irregular-grid validation cases
  beyond the primary arithmetic-call grid. Preserve every limit/failure diagnostic.
  Example raw-scramble acceptance calculation:

```python
v=np.array(saved_scramble_prices,dtype=float)
assert np.isclose(saved_price,v.mean(),rtol=1e-12,atol=1e-12)
se=v.std(ddof=1)/np.sqrt(len(v))
half=scipy.stats.t.ppf(.975,len(v)-1)*se
assert np.allclose([saved_se,saved_low,saved_high],[se,v.mean()-half,v.mean()+half],rtol=1e-11,atol=1e-12)
```

  Record actual maximum differences and checked counts in the proof file. A
  reference status='low_precision' must be explained in the research findings.
- [x] **3. Recover trusted archived sources into a new local folder and actually replay.**
  Verify archive first; check the imported package path originates in recovered
  `src`; use the recorded environment and exact archived config. Compare all
  numerical CSV/JSON outputs excluding timestamps/timing observations. Benchmark
  and figure bytes are not replay targets. Preserve a proof with compared hashes.
- [x] **4. Inspect figures and publish a custom supported-contract example.** Use
  configs/asian_custom.toml with S120,K125,r.04,sigma.25, arithmetic put and
  fixings(.1,.25,.5). This arbitrary grid may use internal integral/MC diagnostics
  without a matching date-based QuantLib reference; state that limit explicitly.
  Give Thai explanation of payoff, correct SE units, method trade-offs and numerical
  limits. Include reproduction commands and a short demonstration narrative.
- [x] **5. Fresh final review and one fix pass.** Use the applicable review skill
  and chosen execution method. Supply this plan/spec, new-file list, saved evidence,
  exact test output, Review Focus and every ledger ruling. Re-grade findings by user
  impact; fix important failures with reproducing RED/GREEN tests, then run the
  full strict suite. Preserve deferred minor findings and actual review scope.
  No review of the unrelated parent Git repository; use a source/evidence package.
- [x] **6. Finish the evidence record.** Mark completed tasks only from observed
  commands, record final tests/replay/source versions and unresolved limits. No
  claim of corporate certification, market forecast accuracy, execution suitability
  or automatic method superiority. No Git commit/merge/push is part of this task.

## Plan self-review and handoff

Coverage: Task1 owns contract/geometric/low-dimensional truth; Task2 owns both
Brownian laws/payoffs; Task3 owns pseudo-random independence/pilot; Task4 owns
scrambles/bridge pairing; Task5 owns external conventions/reference precision;
Task6 owns actual reporting/metrics/measurements; Task7 owns full research/replay/
review/usability. Every Review Focus item has explicit owning tests.

Interfaces use the same method names, counters and fixing schedule throughout.
Reference precision remains independent of our estimator outputs; old APIs are
unchanged. No product code or dependency has been installed by writing this plan.

Execution recommendation: **Native**, because seven sequential tasks share the
contract/result/RNG/reference interfaces; one implementer avoids repeated context
handoffs while a fresh final review checks the completed numerical pipeline.
Alternative: subagent-driven execution with per-task independent review, at the
cost of more context and coordination. User reviews this plan and chooses the
execution method before implementation.
