"""Auditable single-path short-call ledger, before paired Monte Carlo research."""

import argparse
import csv
from dataclasses import asdict, fields
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
from pathlib import Path
import platform
import tomllib

import matplotlib.pyplot as plt

from option_hedging.analysis.ledger_plots import make_ledger_figure
from option_hedging.contracts import OptionSpec
from option_hedging.experiments.provenance import finalize_manifest
from option_hedging.hedging.ledger import hedge_path, unhedged_path


def _load(raw):
    config = tomllib.loads(raw.decode('utf-8'))
    if set(config) != {'option','hedging','path'}:
        raise ValueError('Expected exactly [option], [hedging], [path]')
    option,hedging,path = (config[key] for key in ('option','hedging','path'))
    if set(option) != {'spot','strike','maturity_years','risk_free_rate','volatility','kind','dividend_yield'}:
        raise ValueError('option must contain exactly OptionSpec fields and dividend_yield')
    q = option['dividend_yield']
    if isinstance(q,bool) or not isinstance(q,(int,float)) or q != 0:
        raise ValueError('Only dividend_yield=0 is supported')
    spec = OptionSpec(**{k:v for k,v in option.items() if k != 'dividend_yield'})
    if set(hedging) != {'position','quantity','rebalance_every_steps','one_way_cost_bps','liquidate_stock_at_expiry'}:
        raise ValueError('Unexpected or missing hedging settings')
    if hedging['position'] != 'short_call' or isinstance(hedging['quantity'],bool) or hedging['quantity'] != 1.:
        raise ValueError('Only position=short_call, quantity=1 are supported')
    if hedging['liquidate_stock_at_expiry'] is not True:
        raise ValueError('liquidate_stock_at_expiry must be true')
    if set(path) != {'times','spots'}:
        raise ValueError('path must contain exactly times and spots')
    return config,spec,hedging,path


def _compact(result):
    return {f.name:getattr(result,f.name) for f in fields(result) if f.name != 'ledger'}


def _checks(hedged,unhedged,zero_cost,spot):
    rows = []
    for result in (hedged,unhedged):
        for row in result.ledger:
            residual = math.fsum([row.cash_after,-row.cash_before,-row.option_cashflow,
                                  row.stock_trade*row.spot,row.transaction_cost])
            rows.append(dict(strategy=result.strategy,step=row.step,time=row.time,
                             cash_residual=residual,
                             stock_residual=math.fsum([row.stock_after,-row.stock_before,-row.stock_trade])))
    cash_max = max(abs(r['cash_residual']) for r in rows)
    stock_max = max(abs(r['stock_residual']) for r in rows)
    finance_residual = math.fsum([zero_cost.terminal_pnl,-hedged.terminal_pnl,-hedged.terminal_value_costs])
    tolerance = 1e-10*spot
    checks = dict(cash_absolute_tolerance=tolerance,stock_absolute_tolerance=1e-12,
                  max_cash_residual=cash_max,max_stock_residual=stock_max,
                  financed_cost_identity_residual=finance_residual,
                  passed=cash_max<=tolerance and stock_max<=1e-12 and abs(finance_residual)<=tolerance)
    return rows,checks


def _report(spec,hedging,summary):
    h,u,c = summary['hedged'],summary['unhedged'],summary['checks']
    return f'''# Self-financing short-call hedge ledger

This executed example uses one explicit illustrative stock path from input_config.toml.
It validates cash/trade accounting; it does not estimate average hedge effectiveness
or establish that hedging improves returns. No random samples or market data are used.

## Contract and policy

One short European call, S0={spec.spot:g}, K={spec.strike:g}, T={spec.maturity_years:g},
continuous r={spec.risk_free_rate:g}, no dividends. Model/hedge sigma={spec.volatility:g}
determines **both initial premium and delta**. Rebalance every
{hedging['rebalance_every_steps']} grid steps strictly before expiry. One-way stock
cost={hedging['one_way_cost_bps']:g}bps of absolute traded notional, charged at open,
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
| Initial model premium | {h['initial_premium']:.10f} |
| Terminal call payoff paid | {h['terminal_payoff']:.10f} |
| Hedged terminal P&L, after all costs | {h['terminal_pnl']:.10f} |
| Same path, zero-cost hedge P&L | {summary['zero_cost_terminal_pnl']:.10f} |
| Unhedged short-call P&L | {u['terminal_pnl']:.10f} |
| Nominal stock costs paid | {h['total_nominal_cost']:.10f} |
| Terminal value of those paid costs | {h['terminal_value_costs']:.10f} |
| Stock turnover (shares) | {h['stock_turnover']:.10f} |
| Traded notional (currency) | {h['traded_notional']:.10f} |

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

Maximum cash residual={c['max_cash_residual']:.6g}; tolerance predeclared at
1e-10*S0={c['cash_absolute_tolerance']:g} currency units.
Maximum stock residual={c['max_stock_residual']:.6g}; tolerance 1e-12 shares.
Zero-cost P&L minus paid-cost P&L minus financed costs residual:
{c['financed_cost_identity_residual']:.6g}. All checks pass: **{c['passed']}**.
These internal reconciliations supplement independent hand-arithmetic unit tests;
they alone are not an independent proof of the policy or pricing formulas.

## Files and reproduction

ledger.csv and unhedged_ledger.csv retain every event; path.csv preserves inputs.
accounting_checks.csv retains per-row residuals. ledger.png separates prices,
shares, cash and nominal costs; no ensemble confidence interval is applicable here.

```sh
PYTHONPATH=src .venv/bin/python -m option_hedging.experiments.hedge_demo \\
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
'''


def _csv(path,rows):
    with path.open('w',encoding='utf-8',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run_demo(config_path: Path, output_dir: Path) -> Path:
    if output_dir.exists():
        raise FileExistsError(f'Output directory already exists: {output_dir}')
    raw = config_path.read_bytes()
    config,spec,hedging,path = _load(raw)
    args = dict(times=path['times'],spots=path['spots'])
    hedged = hedge_path(spec,**args,rebalance_every_steps=hedging['rebalance_every_steps'],
                        one_way_cost_bps=hedging['one_way_cost_bps'])
    unhedged = unhedged_path(spec,**args)
    zero_cost = hedge_path(spec,**args,rebalance_every_steps=hedging['rebalance_every_steps'],one_way_cost_bps=0)
    checks_rows,checks = _checks(hedged,unhedged,zero_cost,spec.spot)
    summary = dict(path_points=len(hedged.ledger),path_source='explicit_config',
                   hedged=_compact(hedged),unhedged=_compact(unhedged),
                   zero_cost_terminal_pnl=zero_cost.terminal_pnl,checks=checks)
    serialized = json.dumps(summary,indent=2,allow_nan=False)+'\n'
    report = _report(spec,hedging,summary)
    figure = make_ledger_figure(hedged,unhedged,strike=spec.strike)
    try:
        output_dir.mkdir(parents=True,exist_ok=False)
        _csv(output_dir/'path.csv',[dict(step=r.step,time=r.time,spot=r.spot) for r in hedged.ledger])
        for name,result in (('ledger.csv',hedged),('unhedged_ledger.csv',unhedged)):
            _csv(output_dir/name,[asdict(r) for r in result.ledger])
        _csv(output_dir/'accounting_checks.csv',checks_rows)
        (output_dir/'summary.json').write_text(serialized,encoding='utf-8')
        (output_dir/'effective_config.json').write_text(json.dumps(config,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        (output_dir/'input_config.toml').write_bytes(raw)
        (output_dir/'RESULTS.md').write_text(report,encoding='utf-8')
        figure.savefig(output_dir/'ledger.png',dpi=160)
        source = Path(__file__).resolve().parents[1]
        manifest = dict(experiment='single_path_hedge_ledger',created_utc=datetime.now(timezone.utc).isoformat(),
                        config_sha256=hashlib.sha256(raw).hexdigest(),rng=None,path_source='explicit_config',
                        source_hashes={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                                       for p in sorted(source.rglob('*.py'))},
                        versions={'python':platform.python_version(),**{p:version(p) for p in ('numpy','scipy','matplotlib')}},
                        environment={'platform':platform.platform(),'machine':platform.machine()})
        finalize_manifest(output_dir,manifest,config_bytes=raw,entrypoint='option_hedging.experiments.hedge_demo')
    finally:
        plt.close(figure)
    return output_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=Path('configs/hedge_ledger.toml'))
    parser.add_argument('--output-dir',type=Path)
    args = parser.parse_args()
    output = args.output_dir or Path('reports/runs')/datetime.now(timezone.utc).strftime('ledger-%Y%m%dT%H%M%S%fZ')
    try:
        result = run_demo(args.config,output)
    except (ValueError,TypeError,OSError,KeyError,OverflowError) as error:
        parser.error(str(error))
    print(f'Hedge ledger saved to {result.resolve()}')
    if not json.loads((result/'summary.json').read_text())['checks']['passed']:
        parser.exit(1,'Accounting checks failed; inspect saved evidence.\n')


if __name__ == '__main__':
    main()
