"""Independent arithmetic protects cash timing, costs, settlement and causality."""

from dataclasses import FrozenInstanceError, replace
import importlib
import math

import numpy as np
import pytest

from option_hedging.contracts import OptionSpec


BASE = OptionSpec(120, 100, 1, 0, 0, 'call')


def hedge(spec=BASE, **kwargs):
    values = dict(times=[0, .2, .6, 1], spots=[120, 90, 130, 140],
                  rebalance_every_steps=1, one_way_cost_bps=10.)
    values.update(kwargs)
    return importlib.import_module('option_hedging.hedging.ledger').hedge_path(spec, **values)


def unhedged(spec=BASE, **kwargs):
    values = dict(times=[0, .2, .6, 1], spots=[120, 90, 130, 140])
    values.update(kwargs)
    return importlib.import_module('option_hedging.hedging.ledger').unhedged_path(spec, **values)


def test_hand_worked_open_rebalance_close_and_payoff_with_all_costs():
    result = hedge()
    assert [r.event for r in result.ledger] == ['open', 'rebalance', 'rebalance', 'settle']
    assert [r.cash_after for r in result.ledger] == pytest.approx([-100.12, -10.21, -140.34, -40.48])
    assert [r.stock_trade for r in result.ledger] == [1, -1, 1, -1]
    assert [r.stock_after for r in result.ledger] == [1, 0, 1, 0]
    assert [r.option_cashflow for r in result.ledger] == [20, 0, 0, -40]
    assert [r.transaction_cost for r in result.ledger] == pytest.approx([.12, .09, .13, .14])
    assert result.initial_premium == 20
    assert result.terminal_payoff == 40
    assert result.terminal_pnl == pytest.approx(-40.48)
    assert result.total_nominal_cost == pytest.approx(.48)
    assert result.terminal_value_costs == pytest.approx(.48)
    assert result.stock_turnover == 4
    assert result.traded_notional == 480
    assert result.rebalance_decisions == 2
    assert result.n_stock_trades == 4


def test_hand_worked_borrowing_interest_and_financed_costs():
    rate = math.log(1.21)
    result = hedge(replace(BASE, risk_free_rate=rate), times=[0, .5, 1], spots=[120, 130, 140])
    # Delta=1 throughout. Opening cash is -100/1.21-.12; each half year grows1.1.
    first = -100/1.21 - .12
    assert result.ledger[0].cash_after == pytest.approx(first)
    assert result.ledger[1].cash_before == pytest.approx(first*1.1)
    assert result.ledger[1].cash_interest == pytest.approx(first*.1)
    assert result.ledger[-1].cash_before == pytest.approx(-100-.12*1.21)
    assert result.total_nominal_cost == pytest.approx(.26)
    assert result.terminal_value_costs == pytest.approx(.12*1.21+.14)
    assert result.terminal_pnl == pytest.approx(-.2852)


@pytest.mark.parametrize('rate', [-.07, .05])
def test_cost_difference_equals_terminal_value_of_costs_on_irregular_grid(rate):
    spec = replace(BASE, volatility=.2, risk_free_rate=rate)
    paid = hedge(spec)
    free = hedge(spec, one_way_cost_bps=0)
    independently_financed = sum(r.transaction_cost*math.exp(rate*(1-r.time)) for r in paid.ledger)
    assert free.terminal_pnl-paid.terminal_pnl == pytest.approx(independently_financed, abs=1e-12)
    assert paid.terminal_value_costs == pytest.approx(independently_financed)
    for row in paid.ledger:
        assert row.cash_after == pytest.approx(row.cash_before+row.option_cashflow-row.stock_trade*row.spot-row.transaction_cost)


def test_positive_sigma_known_opening_price_delta_and_cash():
    spec = OptionSpec(100, 100, 1, .05, .2, 'call')
    result = hedge(spec, times=[0, .5, 1], spots=[100, 110, 90], one_way_cost_bps=0)
    assert result.initial_premium == pytest.approx(10.450583572185565)
    assert result.ledger[0].model_delta == pytest.approx(.6368306511756191)
    assert result.ledger[0].cash_after == pytest.approx(-53.232481545376345)
    assert result.ledger[-1].stock_after == 0
    assert result.terminal_payoff == 0
    assert result.terminal_pnl == result.ledger[-1].cash_after


def test_hold_dates_accrue_interest_and_frequency_counts_grid_steps():
    result = hedge(replace(BASE, risk_free_rate=.03), rebalance_every_steps=2)
    assert [r.event for r in result.ledger] == ['open', 'hold', 'rebalance', 'settle']
    held = result.ledger[1]
    assert held.model_delta is None and held.stock_trade == 0 and held.transaction_cost == 0
    assert held.stock_after == 1
    assert held.cash_after == pytest.approx(result.ledger[0].cash_after*math.exp(.03*.2))
    assert result.rebalance_decisions == 1


def test_frequency_larger_than_grid_holds_opening_delta_until_liquidation():
    result = hedge(rebalance_every_steps=100)
    assert [r.event for r in result.ledger] == ['open', 'hold', 'hold', 'settle']
    assert result.rebalance_decisions == 0
    assert result.n_stock_trades == 2


def test_expiry_is_settlement_even_on_rebalance_date_and_at_a_greek_kink():
    result = hedge(times=[0, .5, 1], spots=[120, 110, 100], one_way_cost_bps=0)
    assert result.terminal_pnl == pytest.approx(0, abs=1e-12)
    assert result.ledger[-1].model_delta is None
    assert result.ledger[-1].stock_trade == -1
    assert result.ledger[-1].event == 'settle'


def test_policy_and_cash_prefix_do_not_use_future_observations():
    spec = replace(BASE, volatility=.2)
    first = hedge(spec)
    second = hedge(spec, spots=[120, 90, 70, 50])
    assert first.ledger[:2] == second.ledger[:2]
    assert first.ledger[2].model_delta != second.ledger[2].model_delta


def test_unhedged_receives_same_premium_accrues_cash_and_pays_same_liability():
    spec = replace(BASE, volatility=.2, risk_free_rate=-.03)
    result = unhedged(spec)
    assert result.initial_premium == hedge(spec).initial_premium
    assert result.terminal_pnl == pytest.approx(result.initial_premium*math.exp(-.03)-40)
    assert result.total_nominal_cost == result.terminal_value_costs == 0
    assert result.stock_turnover == result.traded_notional == result.n_stock_trades == 0
    assert all(r.stock_after == r.stock_trade == 0 for r in result.ledger)


def test_inputs_unchanged_and_records_immutable():
    times = np.array([0., .2, .6, 1.])
    spots = np.array([120., 90., 130., 140.])
    before_t, before_s = times.copy(), spots.copy()
    result = hedge(times=times, spots=spots)
    np.testing.assert_array_equal(times, before_t)
    np.testing.assert_array_equal(spots, before_s)
    assert isinstance(result.ledger, tuple)
    with pytest.raises(FrozenInstanceError):
        result.terminal_pnl = 0
    with pytest.raises(FrozenInstanceError):
        result.ledger[0].cash_after = 0


@pytest.mark.parametrize('scale', [1e-170, 1e150])
def test_currency_scale_preserves_quantities_and_small_finite_cash(scale):
    spec = replace(BASE, spot=120*scale, strike=100*scale)
    result = hedge(spec, spots=np.array([120, 90, 130, 140])*scale)
    assert result.terminal_pnl/scale == pytest.approx(-40.48)
    assert result.total_nominal_cost/scale == pytest.approx(.48)
    assert result.stock_turnover == 4


@pytest.mark.parametrize('kwargs', [
    {'times': [0, .2, .2, 1]}, {'times': [.1, .2, .6, 1]}, {'times': [0, .2, .6, .99]},
    {'times': [0, .2, float('inf'), 1]}, {'times': [[0, .2, .6, 1]]},
    {'times': [False, .2, .6, 1]}, {'times': ['0', '.2', '.6', '1']},
    {'spots': [120, 90, 130]}, {'spots': [121, 90, 130, 140]},
    {'spots': [120, 0, 130, 140]}, {'spots': [120, -90, 130, 140]},
    {'spots': [120, float('nan'), 130, 140]}, {'spots': [120, True, 130, 140]},
    {'spots': ['120', '90', '130', '140']}, {'spots': [120, 90j, 130, 140]},
    {'rebalance_every_steps': True}, {'rebalance_every_steps': 0}, {'rebalance_every_steps': 1.5},
    {'one_way_cost_bps': -1}, {'one_way_cost_bps': True}, {'one_way_cost_bps': float('inf')},
])
def test_invalid_path_or_settings_are_rejected(kwargs):
    with pytest.raises((TypeError, ValueError)):
        hedge(**kwargs)


@pytest.mark.parametrize('spec', [None, replace(BASE, kind='put'), replace(BASE, maturity_years=0)])
def test_unsupported_contracts_rejected(spec):
    with pytest.raises((TypeError, ValueError)):
        hedge(spec)


def test_zero_sigma_forward_kink_remains_explicit_error():
    with pytest.raises(ValueError, match='kink'):
        hedge(OptionSpec(100, 100, 1, 0, 0, 'call'), spots=[100, 90, 130, 140])


def test_overflowing_cost_is_explicit_range_error():
    with pytest.raises(ValueError, match='range|finite|overflow'):
        hedge(replace(BASE, spot=1e308), times=[0, 1], spots=[1e308, 1e308], one_way_cost_bps=1e308)


def test_nonzero_cost_rate_that_underflows_is_not_silently_free():
    with pytest.raises(ValueError, match='range|underflow'):
        hedge(one_way_cost_bps=5e-324)


@pytest.mark.parametrize('terminal', [1e18, 1e20])
def test_settlement_rejects_intrinsic_rounding_that_erases_material_strike(terminal):
    # A sigma0/r0 delta1 hedge must have zero terminal P&L, independent of S_T.
    # Here rounded (S_T-K) destroys enough strike digits to invent a profit/loss.
    with pytest.raises(ValueError, match='payoff|precision|range'):
        hedge(times=[0,1], spots=[120,terminal], one_way_cost_bps=0)


@pytest.mark.parametrize('bps', [10., 1e300])
def test_nonzero_trade_underflow_cannot_erase_notional_and_representable_fee(bps):
    spec = OptionSpec(1e-100,1e-97,1,0,.2,'call')
    # Delta~3.315e-260 is finite, but delta*S underflows before multiplication by fee rate.
    with pytest.raises(ValueError, match='notional|underflow|range'):
        hedge(spec,times=[0,1],spots=[1e-100,1e-100],one_way_cost_bps=bps)
