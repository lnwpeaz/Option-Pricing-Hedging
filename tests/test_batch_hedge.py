"""Vectorized summaries must match audited scalar cash flows, not just delta math."""
from dataclasses import replace
import importlib
import math

import numpy as np
import pytest

from option_hedging.contracts import OptionSpec
from option_hedging.hedging.ledger import hedge_path, unhedged_path

BASE = OptionSpec(120,100,1,0,0,'call')
TIMES = np.array([0.,.2,.6,1.])
PATHS = np.array([[120.,90.,130.,140.],[120.,130.,95.,80.]])


def run(spec=BASE, **kwargs):
    args=dict(times=TIMES,paths=PATHS,rebalance_every_steps=1,one_way_cost_bps=10.)
    args.update(kwargs)
    return importlib.import_module('option_hedging.hedging.batch').hedge_paths(spec,**args)


def test_hand_cash_costs_turnover_and_peak_borrowing():
    result=run(paths=PATHS[:1])
    assert result.terminal_pnl[0] == pytest.approx(-40.48)
    assert result.nominal_costs[0] == pytest.approx(.48)
    assert result.financed_costs[0] == pytest.approx(.48)
    assert result.turnover[0] == 4
    assert result.traded_notional[0] == 480
    assert result.max_cash_borrowing[0] == pytest.approx(140.34)


@pytest.mark.parametrize('sigma',[.15,.2,.25])
@pytest.mark.parametrize('frequency',[1,5])
@pytest.mark.parametrize('cost',[0.,5.,10.])
def test_all_predeclared_modes_agree_with_scalar_on_irregular_negative_rate_paths(sigma,frequency,cost):
    spec=replace(BASE,volatility=sigma,risk_free_rate=-.03)
    result=run(spec,rebalance_every_steps=frequency,one_way_cost_bps=cost)
    for i,path in enumerate(PATHS):
        actual=hedge_path(spec,times=TIMES,spots=path,rebalance_every_steps=frequency,one_way_cost_bps=cost)
        for field,scalar in [('terminal_pnl','terminal_pnl'),('nominal_costs','total_nominal_cost'),
                             ('financed_costs','terminal_value_costs'),('turnover','stock_turnover'),
                             ('traded_notional','traded_notional')]:
            assert getattr(result,field)[i] == pytest.approx(getattr(actual,scalar),abs=2e-11)
        borrowing=max(0.,max(-r.cash_before for r in actual.ledger),max(-r.cash_after for r in actual.ledger))
        assert result.max_cash_borrowing[i] == pytest.approx(borrowing,abs=2e-11)


def test_long_grid_agrees_with_scalar_without_input_or_global_rng_changes():
    rng=np.random.default_rng(28)
    times=np.linspace(0,1,253)
    paths=120*np.exp(np.cumsum(np.column_stack([np.zeros(4),rng.normal(0,.01,(4,252))]),axis=1))
    before=paths.copy()
    state=np.random.get_state()
    result=run(replace(BASE,volatility=.2,risk_free_rate=.05),times=times,paths=paths)
    for i,path in enumerate(paths):
        scalar=hedge_path(replace(BASE,volatility=.2,risk_free_rate=.05),times=times,spots=path,rebalance_every_steps=1,one_way_cost_bps=10)
        assert result.terminal_pnl[i] == pytest.approx(scalar.terminal_pnl,abs=2e-11)
    np.testing.assert_array_equal(before,paths)
    np.testing.assert_array_equal(state[1],np.random.get_state()[1])
    with pytest.raises(ValueError):
        result.terminal_pnl[0]=0


def test_unhedged_matches_scalar_and_funding_includes_settlement():
    module=importlib.import_module('option_hedging.hedging.batch')
    result=module.unhedged_paths(BASE,times=TIMES,paths=PATHS)
    assert result.terminal_pnl.tolist() == [-20.,20.]
    assert result.max_cash_borrowing.tolist() == [20.,0.]
    assert not np.any(result.nominal_costs)
    assert result.initial_premium == unhedged_path(BASE,times=TIMES,spots=PATHS[0]).initial_premium


def test_different_expiry_prices_do_not_change_preexpiry_turnover():
    spec=OptionSpec(100,100,1,.05,.2,'call')
    result=run(spec,times=[0.,.5,1.],paths=[[100.,110.,90.],[100.,110.,150.]],rebalance_every_steps=5,one_way_cost_bps=0)
    assert result.turnover[0] == result.turnover[1] == pytest.approx(2*.6368306511756191)


@pytest.mark.parametrize('scale',[1e-170,1e150])
def test_currency_scaling_preserves_small_finite_results(scale):
    result=run(replace(BASE,spot=120*scale,strike=100*scale),paths=PATHS*scale)
    assert result.terminal_pnl[0]/scale == pytest.approx(-40.48)
    assert result.nominal_costs[0]/scale == pytest.approx(.48)


@pytest.mark.parametrize('kwargs',[
    {'paths':[]},{'paths':PATHS[0]},{'paths':[[120.,0.,130.,140.]]},
    {'paths':[[120.,True,130.,140.]]},{'paths':[[120.,90.,130.,float('inf')]]},
    {'paths':[[121.,90.,130.,140.]]},{'times':[0.,.2,.2,1.]},{'times':[0.,.2,.6,.99]},
    {'rebalance_every_steps':True},{'rebalance_every_steps':0},{'one_way_cost_bps':-1},
])
def test_invalid_settings_or_matrix_are_rejected(kwargs):
    with pytest.raises((TypeError,ValueError)):
        run(**kwargs)


def test_scalar_range_guards_and_zero_sigma_kink_remain_explicit():
    with pytest.raises(ValueError,match='payoff|precision|range'):
        run(times=[0,1],paths=[[120.,1e18]],one_way_cost_bps=0)
    tiny=OptionSpec(1e-100,1e-97,1,0,.2,'call')
    with pytest.raises(ValueError,match='notional|underflow|range'):
        run(tiny,times=[0,1],paths=[[1e-100,1e-100]],one_way_cost_bps=1e300)
    with pytest.raises(ValueError,match='kink'):
        run(OptionSpec(100,100,1,0,0,'call'),times=[0,1],paths=[[100.,100.]])
