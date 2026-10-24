"""Validated inputs and sensitivity results; all time/rate units are annual."""

from dataclasses import dataclass
import math
from numbers import Real
from typing import Literal


@dataclass(frozen=True)
class OptionSpec:
    """A European option without dividends; rates are continuously compounded.

    Volatility 0.20 means 20% per year, and maturity_years=0 means expiry.
    Nonfinite values, booleans and numeric strings are rejected explicitly.
    """

    spot: float
    strike: float
    maturity_years: float
    risk_free_rate: float
    volatility: float
    kind: Literal["call", "put"]

    def __post_init__(self) -> None:
        for name in ("spot", "strike", "maturity_years", "risk_free_rate", "volatility"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real):
                raise TypeError(f"{name} must be a finite real number")
            if not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            object.__setattr__(self, name, float(value))
        if self.spot <= 0 or self.strike <= 0:
            raise ValueError("spot and strike must be strictly positive")
        if self.maturity_years < 0 or self.volatility < 0:
            raise ValueError("maturity_years and volatility must be nonnegative")
        if self.kind not in ("call", "put"):
            raise ValueError("kind must be 'call' or 'put'")


@dataclass(frozen=True)
class Greeks:
    """Delta, gamma and vega. Vega is per 1.0 absolute volatility change."""

    delta: float
    gamma: float
    vega: float


@dataclass(frozen=True)
class PriceEstimate:
    """MC price and approximate normal 95% interval, without clipping.

    n_paths counts production terminal evaluations. Antithetic independent_samples
    counts pairs. pilot_paths is additional work used only to fit control_beta.
    A zero sample SE can mean an unobserved rare payoff, not an exact price.
    """

    price: float
    standard_error: float
    ci_low: float
    ci_high: float
    n_paths: int
    independent_samples: int
    pilot_paths: int
    method: str
    control_beta: float = 0.0


@dataclass(frozen=True)
class HedgeRow:
    """Cash is after interest, then option cash flow, trade and transaction cost.

    assets_value excludes the outstanding option liability before settlement.
    model_delta is absent on hold/expiry rows; stock_after is actual holdings.
    """

    step: int
    time: float
    spot: float
    event: str
    model_delta: float | None
    stock_before: float
    stock_trade: float
    stock_after: float
    cash_interest: float
    cash_before: float
    option_cashflow: float
    transaction_cost: float
    cash_after: float
    assets_value: float


@dataclass(frozen=True)
class HedgeResult:
    """Signed P&L of one short call; terminal_value_costs is diagnostic only.

    Costs and their financing are already deducted through the cash ledger.
    stock_turnover is shares; traded_notional is currency units.
    """

    strategy: str
    initial_premium: float
    terminal_payoff: float
    terminal_pnl: float
    total_nominal_cost: float
    terminal_value_costs: float
    stock_turnover: float
    traded_notional: float
    rebalance_decisions: int
    n_stock_trades: int
    ledger: tuple[HedgeRow, ...]
