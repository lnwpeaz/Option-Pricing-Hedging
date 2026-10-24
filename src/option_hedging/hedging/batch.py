"""Date-wise vectorized hedge accounting, audited against the scalar ledger."""

from dataclasses import dataclass
import math
from numbers import Integral, Real

import numpy as np
from scipy.special import ndtr

from option_hedging.contracts import OptionSpec
from option_hedging.hedging.ledger import _path
from option_hedging.pricing.black_scholes import price


@dataclass(frozen=True)
class BatchHedgeResult:
    initial_premium: float
    terminal_pnl: np.ndarray
    nominal_costs: np.ndarray
    financed_costs: np.ndarray
    turnover: np.ndarray
    traded_notional: np.ndarray
    max_cash_borrowing: np.ndarray


def _has_bool(values):
    if isinstance(values,(bool,np.bool_)):
        return True
    return isinstance(values,(list,tuple)) and any(_has_bool(v) for v in values)


def _inputs(spec,times,paths):
    if _has_bool(paths):
        raise TypeError('paths cannot contain booleans')
    matrix=np.asarray(paths)
    if matrix.dtype.kind not in 'iuf':
        raise TypeError('paths must contain real numbers')
    matrix=np.asarray(matrix,dtype=np.float64)
    if matrix.ndim != 2 or matrix.shape[0]<1:
        raise ValueError('paths must be a nonempty two-dimensional matrix')
    grid,_=_path(spec,times,matrix[0])
    if matrix.shape[1]!=len(grid) or not np.all(np.isfinite(matrix)) or np.any(matrix<=0) or np.any(matrix[:,0]!=spec.spot):
        raise ValueError('Every path must be finite/positive and begin at spec.spot')
    return grid,matrix


def _accrue(cash,exponent):
    if not math.isfinite(exponent):
        raise ValueError('Accrual exponent outside floating-point range')
    try:
        growth=math.exp(exponent)
    except OverflowError:
        growth=math.inf
    if math.isfinite(growth) and growth>0:
        result=cash*growth
    else:
        result=np.zeros_like(cash)
        mask=cash!=0
        result[mask]=np.sign(cash[mask])*np.exp(np.log(np.abs(cash[mask]))+exponent)
    if not np.all(np.isfinite(result)) or np.any((cash!=0)&(result==0)):
        raise ValueError('Nonzero cash accrual overflowed or underflowed')
    return result


def _sum(*terms):
    """Neumaier compensation across the four event cash-flow components."""
    total=np.zeros_like(terms[0])
    correction=np.zeros_like(total)
    for term in terms:
        new=total+term
        correction+=np.where(np.abs(total)>=np.abs(term),(total-new)+term,(term-new)+total)
        total=new
    return total+correction


def _payoff(terminal,strike):
    value=np.maximum(terminal-strike,0.)
    # Error-free TwoSum residual of S + (-K), without extended-precision assumptions.
    difference=terminal-strike
    z=difference-terminal
    lost=(terminal-(difference-z))+(-strike-z)
    if np.any((terminal>strike)&(np.abs(lost)>64*math.ulp(strike))):
        raise ValueError('Terminal payoff loses strike precision outside ledger range')
    return value


def _calculate(spec,grid,paths,frequency,cost_rate,hedged):
    try:
        with np.errstate(over='raise',invalid='raise',under='ignore',divide='raise'):
            premium=price(spec)
            if not math.isfinite(premium):
                raise ValueError('Initial premium outside finite range')
            n=len(paths)
            cash=np.zeros(n)
            stock=np.zeros(n)
            nominal=np.zeros(n)
            financed=np.zeros(n)
            turnover=np.zeros(n)
            notional=np.zeros(n)
            borrowing=np.zeros(n)
            for i,time in enumerate(grid):
                spot=paths[:,i]
                if i:
                    cash=_accrue(cash,spec.risk_free_rate*float(time-grid[i-1]))
                    borrowing=np.maximum(borrowing,-cash)
                last=i==len(grid)-1
                flow=premium if i==0 else -_payoff(spot,spec.strike) if last else 0.
                if last:
                    target=np.zeros(n)
                elif hedged and (i==0 or i%frequency==0):
                    tau=spec.maturity_years-float(time)
                    if spec.volatility==0:
                        boundary=spec.strike*math.exp(-spec.risk_free_rate*tau)
                        if np.any(spot==boundary):
                            raise ValueError('Greeks undefined at deterministic payoff kink')
                        target=(spot>boundary).astype(float)
                    else:
                        v=spec.volatility*math.sqrt(tau)
                        if not math.isfinite(v) or v==0:
                            raise ValueError('Delta scale outside floating-point range')
                        target=ndtr((np.log(spot)-math.log(spec.strike)+spec.risk_free_rate*tau)/v+v/2)
                else:
                    target=stock
                trade=target-stock
                traded=np.abs(trade)*spot
                if np.any((trade!=0)&(traded==0)):
                    raise ValueError('Nonzero traded notional underflowed')
                cost=cost_rate*traded
                if cost_rate>0 and np.any((traded>0)&(cost==0)):
                    raise ValueError('Nonzero transaction cost underflowed')
                cash=_sum(cash,flow,-trade*spot,-cost)
                stock=target
                nominal+=cost
                financed+=_accrue(cost,spec.risk_free_rate*(spec.maturity_years-float(time)))
                turnover+=np.abs(trade)
                notional+=traded
                borrowing=np.maximum(borrowing,-cash)
            outputs=(cash,nominal,financed,turnover,notional,borrowing)
            if any(not np.all(np.isfinite(a)) for a in outputs):
                raise ValueError('Batch ledger output outside finite range')
            for a in outputs:
                a.setflags(write=False)
            return BatchHedgeResult(premium,*outputs)
    except (FloatingPointError,OverflowError) as error:
        raise ValueError('Batch ledger arithmetic outside floating-point range') from error


def hedge_paths(spec: OptionSpec, *, times, paths, rebalance_every_steps: int,
                one_way_cost_bps: float) -> BatchHedgeResult:
    """Vectorize independent paths, preserving the scalar ledger's conventions.

    O(NM) path input. The date loop uses O(N) extra workspace; input validation
    currently allocates O(NM) boolean temporaries. No full trade matrices/RNG/I/O.
    max_cash_borrowing is an observed cash-funding diagnostic, not broker margin.
    Numerical agreement targets the validated domain, not bitwise scalar identity.
    """
    grid,matrix=_inputs(spec,times,paths)
    if isinstance(rebalance_every_steps,(bool,np.bool_)) or not isinstance(rebalance_every_steps,Integral):
        raise TypeError('rebalance_every_steps must be an integer')
    if rebalance_every_steps<1:
        raise ValueError('rebalance_every_steps must be positive')
    if isinstance(one_way_cost_bps,(bool,np.bool_)) or not isinstance(one_way_cost_bps,Real):
        raise TypeError('one_way_cost_bps must be real')
    if not math.isfinite(one_way_cost_bps) or one_way_cost_bps<0:
        raise ValueError('one_way_cost_bps must be finite/nonnegative')
    rate=float(one_way_cost_bps)/10000
    if one_way_cost_bps>0 and rate==0:
        raise ValueError('Cost rate underflowed outside range')
    return _calculate(spec,grid,matrix,int(rebalance_every_steps),rate,True)


def unhedged_paths(spec: OptionSpec, *, times, paths) -> BatchHedgeResult:
    grid,matrix=_inputs(spec,times,paths)
    return _calculate(spec,grid,matrix,1,0.,False)
