# Milestone 4: auditable self-financing hedge ledger

User authorized the next previously specified milestone: hedge accounting, followed
later by paired hedge research. Binding financial conventions: docs/RESEARCH_SPEC.md.
Purpose: make every cash flow inspectable and test the bookkeeping before ensemble
conclusions. Monte Carlo stays the computational research centerpiece; this stage
supplies a trustworthy deterministic consumer of its market paths.

## Design

Use the existing OptionSpec as the hedge model. hedge_path(spec, *, times, spots,
rebalance_every_steps, one_way_cost_bps) returns a frozen HedgeResult containing
immutable HedgeRow records. One short European call, unit multiplier, positive T,
no dividends; initial premium and all deltas use spec.volatility. Inputs are finite
positive path prices, increasing annual times from exactly0 to exactlyT, and exact
initial spot. Do not modify inputs, draw randomness or read files.

At open cash_before=0, option_cashflow=C0, stock_trade=delta0. At later dates accrue
cash at r over actual dt; rebalance at indices divisible by rebalance_every_steps
strictly before expiry, otherwise hold. At expiry sell all shares and pay cash
payoff without evaluating expiry Greeks. Negative cash accrues at the same r.
Every row obeys cash_after = cash_before + option_cashflow - stock_trade*spot - cost.
Costs apply to absolute traded notional at open, rebalance and liquidation.

Rows: step, time, spot, event, model_delta (None on hold/settle), stock_before,
stock_trade, stock_after, cash_interest, cash_before (after interest),
option_cashflow, transaction_cost, cash_after, assets_value. Assets before expiry
exclude the outstanding call liability; final settled cash is signed hedger P&L.
Result: strategy, initial_premium, terminal_payoff, terminal_pnl,
total_nominal_cost, terminal_value_costs (costs financed to T, diagnostic only),
stock_turnover (shares), traded_notional, rebalance_decisions, n_stock_trades, ledger.

unhedged_path(spec, *, times, spots) has the same records: retain premium in cash,
no stock trades/costs, then pay the same payoff. The baseline premium uses the same
model spec; this is not a fixed market premium across later misspecified models.

Explicitly reject unsupported puts/T0, booleans/strings/complex path data, invalid
frequency/costs, nonfinite intermediate cash/interest/costs and unrepresentable
nonzero accrual/cost products. The existing analytic zero-sigma Greek kink raises
ValueError rather than defining an invented hedge there. Do not clip results.

## Deliverable

A dedicated configs/hedge_ledger.toml supplies one explicit illustrative path,
option and hedge settings. experiments.hedge_demo validates all inputs before output,
refuses overwriting, saves path.csv, ledger.csv, unhedged_ledger.csv,
accounting_checks.csv, summary.json, ledger.png, RESULTS.md, exact/effective config,
source snapshot and completed manifest. Includes a zero-cost counterfactual on the
same path to check that terminal P&L loss equals financed costs, with no double charge.
Tolerance for demo cash reconciliation is predeclared at 1e-10*spot.
No RNG, model calibration, statistical hedge ranking or market-performance claim.
A final review added a strike-relative payoff precision guard: reject lost intrinsic
subtraction residual beyond64 ULPs of strike, so gross rounded flows cannot manufacture
P&L. Reject nonzero trade notionals that underflow to0 before computing fees.

## Acceptance

- Independent hand arithmetic with zero-sigma non-kink deltas0/1 checks opening,
  rebalance, closing costs, signed cash/payoff, interest and irregular dt.
- Positive-sigma test uses known price/delta constants and actual pricer integration.
- Prefix-causality, input immutability, no expiry Greek call, hold scheduling,
  exact terminal stock0, financed-cost identity and unhedged identity.
- Invalid input and range failures; tiny/large currency scaling where representable.
- Real CLI, outputs/integrity, numerical repeatability and no overwrite.
- Full strict suite, fresh independent review, inspect figure and execute source replay.
- Thai learning guide and current-scope docs. Preserve older examples unchanged.
