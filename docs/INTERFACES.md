# Implemented and planned interfaces

OptionSpec, Greeks, PriceEstimate, analytic price/greeks, binomial.price,
monte_carlo.price, terminal_from_normals, simulate_paths, make_time_grid, the independent
payoff reference, hedge_path/unhedged_path, vectorized hedge_paths/unhedged_paths and all seven
demos/experiments are implemented.
The remaining interfaces below are design contracts. Core modules must not read files,
fetch data, use global random state or silently change user inputs.

| File | Planned responsibility / public interface |
|---|---|
| contracts.py | Frozen OptionSpec(spot, strike, maturity_years, risk_free_rate, volatility, kind); Greeks(delta, gamma, vega); PriceEstimate(price, standard_error, ci_low, ci_high, n_paths); HedgeResult with time/stock/cash/cost ledger and terminal P&L |
| pricing/black_scholes.py | price(spec: OptionSpec) -> float; greeks(spec: OptionSpec) -> Greeks |
| pricing/binomial.py | price(spec: OptionSpec, *, steps: int) -> float |
| pricing/monte_carlo.py | price(spec: OptionSpec, *, n_paths: int, rng: numpy.random.Generator, method='plain', batch_size=65536, pilot_paths=1024) -> PriceEstimate; exact terminal risk-neutral GBM |
| simulation/gbm.py | simulate_paths(*, spot: float, drift: float, volatility: float, times: numpy.ndarray, n_paths: int, rng: numpy.random.Generator, batch_size=512) -> numpy.ndarray; shape (n_paths, len(times)) |
| hedging/ledger.py | hedge_path(spec: OptionSpec, *, times: numpy.ndarray, spots: numpy.ndarray, rebalance_every_steps: int, one_way_cost_bps: float) -> HedgeResult; v1 short one call, model sigma=spec.volatility |
| analysis/metrics.py | summarize(*, terminal_pnl: numpy.ndarray, nominal_costs: numpy.ndarray, turnover: numpy.ndarray) -> dict[str, float] |
| analysis/plots.py | make_figures(results: pandas.DataFrame, metrics: pandas.DataFrame) -> dict[str, matplotlib.figure.Figure]; caller saves figures |
| experiments/runner.py | run(config_path: pathlib.Path, output_root: pathlib.Path) -> pathlib.Path; only this layer loads config and writes run artifacts |

Dependencies: contracts -> pricing/simulation -> hedging -> analysis -> experiments.
Monte Carlo pricing may consume the shared GBM helper but analytic/tree pricing do not.
The runner supplies physical or risk-neutral drift explicitly; the GBM helper never infers a measure.

Validate finite numeric inputs, positive spot/strike, nonnegative T/sigma/costs,
strictly increasing finite times starting at zero, and option kind in {call, put}.
The ledger requires final time equal to option maturity, first spot equal to spec.spot,
strictly positive path prices and a positive integer rebalance interval. The first
hedging version rejects puts and zero maturity; expiry pricing still supports T=0.
Integer settings must reject booleans. No silent clipping of probabilities or negative inputs.

Keep dividend_yield=0 in config validation for v1; OptionSpec has no dividend field.
In the first version the ledger's liquidation convention is mandatory; reject false config values
instead of silently ignoring them. The runner rejects position/quantity/model/measure values
outside the supported short_call/1.0/gbm/physical contract.

The analytic learning CLI is `python -m option_hedging.experiments.pricing_demo`.
Its `run_demo(config_path: Path, output_dir: Path) -> Path` writes pricing artifacts only,
requires positive maturity and volatility, and refuses an existing output directory.
The paired hedge experiment runner/CLI are implemented. Avoid a database,
service layer or plugin system for v1.

The CRR learning CLI is `python -m option_hedging.experiments.convergence_demo`.
Its `run_demo(config_path: Path, output_dir: Path) -> Path` consumes [option] and
[convergence].steps; the latter is at least two strictly increasing positive integers.
All prices are calculated before creating output, and invalid probabilities fail explicitly.
The core tree validates steps even at expiry and handles zero volatility without forming p.
It uses O(N^2) time and O(N) memory; unrepresentable nodes raise ValueError.
Interior probabilities that underflow/round to endpoints also raise ValueError;
true p=0 or p=1 endpoints are retained. No silent probability clipping is used.

The Monte Carlo CLI is `python -m option_hedging.experiments.monte_carlo_demo`,
using configs/monte_carlo.toml. `run_demo(config_path: Path, output_dir: Path) -> Path`
validates the whole config and calculates before creating a new output directory.
It writes independent repeat estimates, metrics/uncertainty, benchmark CSVs, four
figures, RESULTS.md, exact/effective config and a source/environment/artifact manifest.

`simulation.gbm.terminal_from_normals(*, spot, drift, volatility, maturity_years,
normals: numpy.ndarray) -> numpy.ndarray` accepts explicit drift and supplied 1D normals.
Both the terminal helper and full simulate_paths are implemented.
PriceEstimate adds independent_samples, pilot_paths, method and control_beta to the
price/SE/CI/n_paths contract. n_paths is requested production terminal evaluations;
antithetic independent_samples=n_paths/2. Pilot paths are additional work; deterministic
cases draw no random samples and report pilot_paths=0. Moments are calculated in spot
units to avoid notional-scale square underflow/overflow, then price/SE are rescaled.
No global random state or analytic option price enters the Monte Carlo core.

`simulation.time_grid.make_time_grid(*, maturity_years, steps_per_year=252)` returns
regular annual dates strictly before expiry and exact expiry, with a possible shorter
last interval. T=0 returns [0]. simulate_paths accepts [0] and arbitrary strictly
increasing numeric times starting at zero; zero sigma/[0] do not advance RNG.
Explicit Generator and positive integer n_paths/batch_size are required even for
deterministic cases. Reject booleans, nonfinite inputs, and zero/overflowed prices.
Full matrix memory is O(N*M), extra simulation workspace O(B*M).

The path CLI is `python -m option_hedging.experiments.paths_demo`, using
configs/gbm_paths.toml. `run_demo(config_path: Path, output_dir: Path) -> Path` saves
physical paths.npy, times.npy, fixed-ID previews, paired terminal data, cross-sectional
price/log-return statistics, independent-repeat diagnostics, two figures, RESULTS.md
and exact/effective config plus manifest. Market [mu] and RN [r] ensembles share
shocks within a pair; independent repeat IDs use distinct SeedSequence keys.

## Implemented research-quality validation

`validation.payoff_reference.integrate_payoff(spec, *, normal_cutoff=12.)` returns
price, adaptive-quadrature error estimate, analytic omitted-tail upper bound,
evaluation count and normal integration bounds. It integrates payoff directly,
without calling project pricing/GBM routines. For positive sigma it splits around
payoff/density centers, merging numerically coincident splits without dropping domain.
This is an independent numerical comparison under the same model, not market validation.

The fifth CLI `python -m option_hedging.experiments.validation_demo` consumes
configs/validation.toml and writes every reference/CRR/MC row, metrics, two figures,
report and provenance. `run_demo(config_path: Path, output_dir: Path) -> Path` refuses
existing outputs. Numerical-check failures are saved and the CLI exits 1 when the
analytic/reference tolerance fails; invalid parameters or computation errors exit 2.
All scenarios/repeats remain visible, including zero-SE CIs. Below-floor cells are
separated for interpretation; raw price/SE/coverage are unchanged.

All seven demos/experiments use `experiments.provenance.finalize_manifest` after artifact
creation: source_snapshot.zip then a completed manifest with artifact hashes.
`python -m option_hedging.experiments.verify_run RUN_DIR` verifies recorded byte
integrity and source recoverability without executing archived code. Refer to
REPRODUCIBILITY.md for historical records, dependency and authenticity limits.

## Implemented one-path hedge accounting

`hedging.ledger.hedge_path(spec, *, times, spots, rebalance_every_steps,
one_way_cost_bps)->HedgeResult` and `unhedged_path(spec, *, times, spots)->HedgeResult`
are pure, O(M)-time/storage APIs. Both use the same model premium; unhedged keeps
it in cash. Positive maturity/short call only, no dividends. Opening/before-expiry
rebalancing/expiry liquidation costs and actual-dt interest are fully recorded.
Exact initial spot/expiry grid endpoints are required. Sigma0 pre-expiry Greek
kinks remain errors. Nonzero notional/cost underflow and excessive intrinsic-payoff
rounding (over64 ULPs of strike) raise explicit ValueError. No price clipping or RNG.

Frozen HedgeResult contains summary values and a tuple of frozen HedgeRow records.
Each row records time/spot/event/model_delta, stock before/trade/after, cash interest,
cash before (after accrual), option cash flow, cost, cash after and assets_value.
Only final settled assets are P&L; intermediate assets exclude the call liability.
terminal_value_costs is a diagnostic and must not be deducted again from P&L.
stock_turnover counts shares; traded_notional counts currency. Rebalance decisions
include zero-size changes, while n_stock_trades counts nonzero trades including close.

The sixth CLI `python -m option_hedging.experiments.hedge_demo` uses
configs/hedge_ledger.toml, saves both ledgers, explicit path, accounting checks,
summary/figure/report and source provenance. Output directories must be new; all
calculations precede output creation. CLI exits1 on saved reconciliation failure,
2 on invalid inputs/calculation error. Ensemble runner/metrics are implemented as described below.

## Implemented paired ensemble study

`hedging.batch.hedge_paths(spec, *, times, paths, rebalance_every_steps,
one_way_cost_bps)->BatchHedgeResult` and `unhedged_paths(spec, *, times, paths)`
return read-only path-summary arrays. Date-loop workspaceO(N); validation also
allocatesO(NM) boolean temporaries. Same settlement/range conventions as scalar
ledger, with current-date analytic deltas and no RNG. Peak borrowing covers cash
before/after events, including expiry; it is not a broker margin estimate.

`analysis.metrics.summarize` implements mean/SD/RMSE/quantiles/loss probability/costs.
`summarize_study(cases, comparisons, *, bootstrap_repeats, seed, batch_size=16)`
returns metrics, paired contrasts, bootstrap array(repeats,cells,6) and cell labels.
All case/basis cells use shared resampled path IDs; CIs are pointwise approximate
percentile intervals. Loss probability uses Wilson intervals. Funding fields
explicitly retain model-premium meaning on common-reference rows.

`experiments.runner.run_study(config_path, output_dir)->Path` writes the complete
fixed-config study to a new folder. `run(config_path, output_root)` chooses a new
UTC run ID. CLI `python -m option_hedging.experiments.runner` defaults to
configs/hedge_study.toml; baseline.toml's unused planned sections are not consumed.
Invalid inputs/computation fail before output; saved scalar-validation failure
exits1. Capture paths/times/scenarios/path outcomes/42metrics/102contrasts, bootstrap
data/labels, scalar checks/representative ledger, figures/report and provenance.
Timings are separate from deterministic numeric replay acceptance.


## Implemented V2-A Asian interfaces

- `AsianOptionSpec(spot,strike,risk_free_rate,volatility,kind,fixing_times,averaging='arithmetic')`:
  immutable, q=0, equal weights, 0<t1<...<tm=T, no past observations or S0 in average.
- `AsianEstimate`: price/SE/unclipped CI/status, requested and actual work,
  independent samples, pilot beta, immutable scramble prices and diagnostics.
- `pricing.asian_monte_carlo.price(spec, *, n_paths, rng, method='plain', batch_size=1024,
  pilot_paths=512, scrambles=16, bits=52)`: plain/antithetic/control/sobol/sobol_bridge.
  Deterministic sigma=0 validates settings but consumes no RNG and reports zero actual work.
- `simulation.brownian_bridge.brownian_from_normals(normals,fixing_times,construction='increments')`:
  shape(B,m), no W0 column; bridge builds terminal first, then FIFO index midpoints using actual times.
- `pricing.asian_samples.discounted_payoffs` returns A/G payoff arrays normalized by S0;
  `target_payoffs` evaluates only the requested averaging convention, without unused controls.
- `pricing.asian_reference`: geometric_log_moments, geometric_price, deterministic_price,
  arithmetic_bounds. `validation.asian_reference`: independent geometric/two-fixing integration.
- `validation.asian_quantlib`: optional dated reference checks and empirical precision;
  only exact ACT/365F alignment within 1e-14 years is accepted, no rounding of the contract.
- `experiments.asian_study.run_study(config_path,output_dir)` / matching CLI: strict
  study/custom config, every requested row retained, manifest written last, no overwrite.
- `analysis.asian_metrics.summarize`: shared macro-ID bootstrap; ref-dominated ranking withheld.

See docs/ASIAN_MONTE_CARLO_TH.md for output fields, examples and measured limits.
