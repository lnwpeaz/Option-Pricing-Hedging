# Self-financing short-call hedge ledger

This executed example uses one explicit illustrative stock path from input_config.toml.
It validates cash/trade accounting; it does not estimate average hedge effectiveness
or establish that hedging improves returns. No random samples or market data are used.

## Contract and policy

One short European call, S0=100, K=100, T=1,
continuous r=0.05, no dividends. Model/hedge sigma=0.2
determines **both initial premium and delta**. Rebalance every
1 grid steps strictly before expiry. One-way stock
cost=5bps of absolute traded notional, charged at open,
each stock trade and final liquidation. No option spread or extra cash injection.

At open: cash = model premium - delta*spot - opening cost.
At later dates: accrue previous cash by exp(r*actual_dt), then pay for stock trades
and costs. Negative cash borrows at the same r. Hold rows also earn/pay interest.
At expiry: sell all remaining stock, pay liquidation cost and call payoff; do not
compute expiry delta or rebalance before liquidation. Positive final P&L belongs
to the short-call hedger. Intermediate assets_value excludes the option liability
and is not mark-to-market net wealth or cumulative profit.

## Executed outcome on this path

| Item | Value |
|---|---:|
| Initial model premium | 10.4505835722 |
| Terminal call payoff paid | 5.0000000000 |
| Hedged terminal P&L, after all costs | -0.6280105786 |
| Same path, zero-cost hedge P&L | -0.5013340445 |
| Unhedged short-call P&L | 5.9863964497 |
| Nominal stock costs paid | 0.1241160583 |
| Terminal value of those paid costs | 0.1266765341 |
| Stock turnover (shares) | 2.3872659847 |
| Traded notional (currency) | 248.2321166438 |

Unhedged retains the same model premium in cash until paying the same liability.
The cost diagnostic compounds each paid cost to expiry. Costs and financing are
already in the cash ledger: **never subtract terminal_value_costs again**.
The no-cost/paid-cost hedge uses identical cost-independent delta decisions.

## Accounting checks

Cash identity in every row:
`cash_after = cash_before + option_cashflow - stock_trade*spot - transaction_cost`.
cash_before is after that interval's interest; opening cash_before is 0.
option_cashflow is +premium at open, -payoff at expiry and 0 otherwise.
Stock identity: `stock_after = stock_before + stock_trade`.

Maximum cash residual=6.85476e-15; tolerance predeclared at
1e-10*S0=1e-08 currency units.
Maximum stock residual=0; tolerance 1e-12 shares.
Zero-cost P&L minus paid-cost P&L minus financed costs residual:
-2.7589e-14. All checks pass: **True**.
These internal reconciliations supplement independent hand-arithmetic unit tests;
they alone are not an independent proof of the policy or pricing formulas.

## Files and reproduction

ledger.csv and unhedged_ledger.csv retain every event; path.csv preserves inputs.
accounting_checks.csv retains per-row residuals. ledger.png separates prices,
shares, cash and nominal costs; no ensemble confidence interval is applicable here.

```sh
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.hedge_demo \
  --config configs/hedge_ledger.toml --output-dir reports/runs/my-ledger
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.verify_run reports/runs/my-ledger
```

Source/config bytes and replay command are in source_snapshot.zip; the completed
manifest records artifact hashes. Exact numerical replay targets the recorded
Python/library environment, not cross-platform figure identity.

## Next research step

Use shared GBM paths for every 1/every 5-step hedge policies, costs 0/5/10bps and
model sigma 15%/20%/25% against true sigma 20%. Compare paired errors/costs with
uncertainty and the unhedged baseline, retaining every scenario. Each model sigma
also changes opening premium; explicitly separate that effect when interpreting
misspecification. This one-path example answers none of those aggregate comparisons.
