"""Pure, causal short-call accounting with cash interest and explicit settlement."""

from dataclasses import replace
import math
from numbers import Integral, Real

import numpy as np

from option_hedging.contracts import HedgeResult, HedgeRow, OptionSpec
from option_hedging.pricing.black_scholes import greeks, price


def _path(spec, times, spots):
    if not isinstance(spec, OptionSpec):
        raise TypeError('spec must be OptionSpec')
    if spec.kind != 'call' or spec.maturity_years <= 0:
        raise ValueError('Ledger supports a short call with strictly positive maturity')
    arrays = []
    for name, values in (('times', times), ('spots', spots)):
        if isinstance(values, (list, tuple)) and any(isinstance(v, (bool, np.bool_)) for v in values):
            raise TypeError(f'{name} must contain real numbers, not booleans')
        array = np.asarray(values)
        if array.dtype.kind not in 'iuf':
            raise TypeError(f'{name} must contain real numbers, not strings, bools or complex values')
        array = np.asarray(array, dtype=np.float64)
        if array.ndim != 1 or array.size < 2 or not np.all(np.isfinite(array)):
            raise ValueError(f'{name} must be a finite one-dimensional array of length at least2')
        arrays.append(array)
    grid, path = arrays
    if grid.size != path.size:
        raise ValueError('times and spots must have matching lengths')
    if grid[0] != 0 or grid[-1] != spec.maturity_years or np.any(np.diff(grid) <= 0):
        raise ValueError('times must increase strictly from zero to exact option maturity')
    if path[0] != spec.spot or np.any(path <= 0):
        raise ValueError('spots must be positive and begin at exact spec.spot')
    return grid, path


def _finite(value, label):
    if not math.isfinite(value):
        raise ValueError(f'{label} is outside finite floating-point range')
    return value


def _accrue(cash, exponent):
    """Avoid an overflowing exp intermediate when the final product is finite."""
    if cash == 0:
        return 0., 0.
    _finite(exponent, 'Cash accrual exponent')
    try:
        growth = math.exp(exponent)
    except OverflowError:
        growth = math.inf
    if growth == 0 or not math.isfinite(growth):
        accrued = math.copysign(math.exp(math.log(abs(cash))+exponent), cash)
    else:
        accrued = cash*growth
    _finite(accrued, 'Accrued cash')
    if accrued == 0:
        raise ValueError('Nonzero accrued cash underflowed outside floating-point range')
    interest = cash*math.expm1(exponent) if abs(exponent) < .5 else accrued-cash
    return accrued, _finite(interest, 'Cash interest')


def _run(spec, grid, path, *, frequency, cost_rate, hedged):
    try:
        premium = price(spec)
        payoff = 0.
        cash, stock = 0., 0.
        rows = []
        notional, nominal_costs, financed_costs, turnover = [], [], [], []
        decisions = trades = 0
        for step, (time, spot) in enumerate(zip(grid, path)):
            time, spot = float(time), float(spot)
            before, interest = (_accrue(cash, spec.risk_free_rate*(time-float(grid[step-1])))
                                if step else (0., 0.))
            last = step == len(grid)-1
            if last:
                payoff = max(spot-spec.strike, 0.)
                # fsum cannot recover strike digits already rounded out of S-K.
                # Measure that loss against strike precision, not huge S_T, which
                # would mask a manufactured P&L in an otherwise exact delta1 hedge.
                if spot > spec.strike:
                    lost = math.fsum([spot, -spec.strike, -payoff])
                    if abs(lost) > 64 * math.ulp(spec.strike):
                        raise ValueError('Terminal payoff loses strike precision outside the ledger range')
            model_delta = None
            option_flow = premium if step == 0 else -payoff if last else 0.
            if last:
                event, target = 'settle', 0.
            elif step == 0 or (hedged and step % frequency == 0):
                event = 'open' if step == 0 else 'rebalance'
                if hedged:
                    model_delta = greeks(replace(spec, spot=spot, maturity_years=spec.maturity_years-time)).delta
                    target = model_delta
                    decisions += int(step > 0)
                else:
                    target = 0.
            else:
                event, target = 'hold', stock
            trade = target-stock
            traded = _finite(abs(trade)*spot, 'Traded notional')
            if trade != 0 and traded == 0:
                raise ValueError('Nonzero traded notional underflowed outside floating-point range')
            cost = _finite(cost_rate*traded, 'Transaction cost')
            if cost_rate > 0 and traded > 0 and cost == 0:
                raise ValueError('Nonzero transaction cost underflowed outside floating-point range')
            cash = _finite(math.fsum([before, option_flow, -trade*spot, -cost]), 'Cash balance')
            assets = _finite(math.fsum([cash, target*spot]), 'Assets value')
            rows.append(HedgeRow(step, time, spot, event, model_delta, stock, trade, target,
                                 interest, before, option_flow, cost, cash, assets))
            stock = target
            trades += int(trade != 0)
            notional.append(traded)
            turnover.append(abs(trade))
            nominal_costs.append(cost)
            financed_costs.append(_accrue(cost, spec.risk_free_rate*(spec.maturity_years-time))[0])
        totals = [_finite(math.fsum(values), 'Ledger total') for values in
                  (nominal_costs, financed_costs, turnover, notional)]
        return HedgeResult('delta_hedged' if hedged else 'unhedged', premium, payoff, cash,
                           *totals, decisions, trades, tuple(rows))
    except (OverflowError, FloatingPointError) as error:
        raise ValueError('Ledger calculation is outside floating-point range') from error


def hedge_path(spec: OptionSpec, *, times: np.ndarray, spots: np.ndarray,
               rebalance_every_steps: int, one_way_cost_bps: float) -> HedgeResult:
    """Self-finance one short call on observed path values, never rebalance at expiry.

    Receive the model premium and buy delta at t0. Costs apply at every actual
    stock trade, including opening/liquidation. Negative cash borrows at r.
    Exact grid endpoints are required; no calendar/price/frequency is inferred.
    Sigma=0 Greek kinks and unrepresentable arithmetic raise explicit ValueError.
    O(M) time/storage for M path observations; no RNG, I/O or input mutation.
    """
    grid, path = _path(spec, times, spots)
    if isinstance(rebalance_every_steps, (bool, np.bool_)) or not isinstance(rebalance_every_steps, Integral):
        raise TypeError('rebalance_every_steps must be a positive integer')
    if rebalance_every_steps < 1:
        raise ValueError('rebalance_every_steps must be positive')
    if isinstance(one_way_cost_bps, (bool, np.bool_)) or not isinstance(one_way_cost_bps, Real):
        raise TypeError('one_way_cost_bps must be a finite real')
    if not math.isfinite(one_way_cost_bps) or one_way_cost_bps < 0:
        raise ValueError('one_way_cost_bps must be finite and nonnegative')
    rate = float(one_way_cost_bps)/10000
    if one_way_cost_bps > 0 and rate == 0:
        raise ValueError('Nonzero cost rate underflowed outside floating-point range')
    return _run(spec, grid, path, frequency=int(rebalance_every_steps), cost_rate=rate, hedged=True)


def unhedged_path(spec: OptionSpec, *, times: np.ndarray, spots: np.ndarray) -> HedgeResult:
    """Same short call/model premium, retained in cash until payoff; no stock costs."""
    grid, path = _path(spec, times, spots)
    return _run(spec, grid, path, frequency=1, cost_rate=0., hedged=False)
