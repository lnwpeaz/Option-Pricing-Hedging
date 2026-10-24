# Research specification

## Purpose and status

This specification defines a learning-focused financial engineering project. Analytic pricing,
Greeks, CRR pricing/convergence and the three-estimator Monte Carlo research lab are
implemented and tested. Exact terminal/full-path GBM and a reusable path demo are
implemented. The self-financing one-path hedge ledger and explicit-path demo are
implemented. Paired model-based hedge research and the final 12-page report are
complete, with a second hypothetical contract demonstration. Monte Carlo is the computational centerpiece connecting
statistical estimation with vectorization, bounded memory and measured efficiency.
Hedge results must be reported as simulated,
conditional on stated model assumptions, not as historical trading evidence.

## Primary question and hypotheses

Study terminal replication error of a short European call under discrete delta hedging.
Compare every 1 versus every 5 time steps, with one-way costs of 0, 5 and 10 basis points
and hedge volatility of 15%, 20% and 25% against true scenario volatility of 20%.
Predeclare the grid; show all scenarios without selecting a winner after seeing results.
Under correctly specified smooth GBM and zero costs, finer hedging should reduce error
in aggregate. With costs, finer hedging may increase cost and worsen net outcomes.
These are hypotheses to evaluate, not guaranteed outcomes for every finite sample.

## Financial conventions

- Python >=3.11; time in years; continuously compounded annual risk-free rate.
- No dividends for v1, q=0; reject nonzero q until dividend cash flows are implemented.
- One underlying; positive spot and strike; nonnegative maturity and volatility.
- Rates and drift must be finite; negative finite rates are allowed where numerically valid.
- European call and put for pricing; short one call for hedging, multiplier=1.
- A regular k/252 annual grid with exact expiry included; the final interval may be shorter.
- Real-world path drift mu=0.08 and true sigma=0.20 are scenario assumptions, not estimates.
- Pricing uses risk-neutral drift r; physical paths use explicitly supplied mu.
- Initial premium uses hedge/model sigma. Report this when comparing misspecified models.
- Costs are one_way_cost_bps / 10000 * abs(stock_trade) * current_spot.
- Costs apply at opening, every rebalance and final stock liquidation; no option spread in v1.
- Cash earns/pays the same continuously compounded r; no external cash injection.
- European expiry settlement is cash payoff; do not rebalance delta at expiry.
- Daily/weekly labels mean every 1/5 grid steps, not a holiday-aware trading calendar.

## Pricing mathematics

For T>0 and sigma>0, q=0:

    d1 = [log(S/K) + (r + sigma^2/2)T] / (sigma*sqrt(T))
    d2 = d1 - sigma*sqrt(T)
    C = S*N(d1) - K*exp(-r*T)*N(d2)
    P = K*exp(-r*T)*N(-d2) - S*N(-d1)
    delta_call = N(d1); delta_put = N(d1) - 1
    gamma = n(d1)/(S*sigma*sqrt(T))
    vega = S*n(d1)*sqrt(T)

Vega is per 1.0 absolute annual volatility, not per percentage point; divide by 100
for a one-percentage-point presentation. At T=0 return intrinsic value for price.
At sigma=0 price discounted deterministic terminal payoff. At derivative kinks,
Greeks raise a documented ValueError instead of silently dividing by zero.

CRR: u=exp(sigma*sqrt(dt)), d=1/u, p=(exp(r*dt)-d)/(u-d).
Reject invalid p outside [0,1]; do not clip it. Handle deterministic/expiry price
limits separately. Validate an integer positive step count.

Monte Carlo pricing: sample terminal prices under risk-neutral GBM, discount payoff,
and return estimate, sample standard error and approximate 95% normal confidence interval.
Require at least two independent samples for a sample standard error. Antithetic
counts pair means (even n_paths >= 4), not raw correlated payoffs. Control beta is
fitted on extra independent pilot paths and frozen for production; its known
control expectation is discounted stock E_Q[exp(-rT)S_T]=S0. Pilot costs are counted.
No price/CI clipping. Normal intervals are approximate; zero observed sample variance
does not certify an exact price. The dedicated configs/monte_carlo.toml lab records
all independent runs, RMSE bootstrap intervals, Wilson coverage intervals and
separate kernel-only versus complete-estimator benchmarks. Exact GBM transitions use
S_next=S*exp((drift-sigma^2/2)*dt + sigma*sqrt(dt)*Z).

## Hedge ledger and timing

At t0 receive C0, choose delta0 and set cash B0=C0-delta0*S0-cost0.
At each later grid point accrue B_pre=B_previous*exp(r*dt).
If rebalancing before expiry, compute delta_new using only S_now and time remaining;
set B_new=B_pre-(delta_new-delta_old)*S_now-cost_now.
Otherwise hold delta and retain accrued cash.
At expiry liquidate stock and pay the call liability:

    terminal_pnl = B_pre + delta_old*S_T
                   - liquidation_cost - max(S_T-K, 0)

Positive terminal_pnl is profit to the short-option hedger; replication error uses
this signed P&L convention. RMSE is sqrt(mean(terminal_pnl^2)), not standard deviation.
Report nominal paid costs separately; cash accrual already incorporates their financing.
Compare an unhedged short call that retains the premium in cash as a baseline.

## Outputs and reproducibility

For each run save effective_config.json, manifest.json, metrics.csv,
path_results.csv, one representative ledger.csv and figures in reports/runs/<run_id>/.
Use unique run IDs and refuse overwriting completed runs. Manifest includes UTC creation time,
seed, Python/package versions, source revision or source hashes, and config hash.
Reuse physical paths across hedge/cost scenarios; keep pricing and scenario RNG streams separate.

Metrics: mean P&L, standard deviation, RMSE, 5th/50th/95th percentiles, probability
of negative P&L, mean nominal costs and stock turnover. Include Monte Carlo uncertainty
and paired comparison intervals using resampled path IDs when interpreting differences.
Do not call lower-tail P&L quantiles a validated VaR forecasting model.

## Validation requirements

Pricing: baseline C=10.4505835722 and P=5.5735260223, parity, bounds, expiry,
zero volatility, nonfinite inputs and invalid option kind. Analytic Greeks vs finite differences
away from kinks. Compare CRR over a step grid (convergence need not be monotonic).
MC uncertainty should shrink approximately with sqrt(sample count), assessed over repeated
independent seeds rather than a brittle single confidence-interval assertion.

Simulation: shape (n_paths, n_steps+1), exact initial spot, positivity, deterministic
sigma=0 limit, reproducibility and risk-neutral discounted expectation across repeated samples.
Full-path simulation uses exact log increments on explicit irregular grids, with
path-major batched draws. The returned matrix is O(N*M), workspace O(B*M).
The paths demo in configs/gbm_paths.toml saves physical paths.npy/times.npy and
paired physical/RN diagnostics on common shocks. Independent repeats record price
and log-return moments against theory; fan bands are path quantiles, not mean CIs.

Hedging: hand-calculated two-step ledger including costs, opening/closing costs,
cash interest, no expiry rebalance, irregular last interval, and no future observation access.
Use nonuniform test grids to verify dt handling even though baseline grids are uniform.

## Research limits and extensions

Constant-volatility continuous GBM omits jumps, stochastic volatility, spreads varying
over time, liquidity, borrowing limits and market option quotes. Prices are modeled fair values.
Dividend-bearing underlyings, American exercise and real brokerage contract multipliers
require explicit extensions. Optional later work: prospective option quotes and an independent
benchmark library, followed by stochastic volatility/jump stress studies.
