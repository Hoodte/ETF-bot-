import copy

import numpy as np
import pandas as pd
import pytest

from etfbot import backtest, data, quality, risk, strategies
from etfbot.config import load_config


@pytest.fixture
def cfg():
    return load_config("config.yaml")


@pytest.fixture
def prices(cfg):
    return data.synthetic_universe(list(cfg["instruments"]), start="2010-01-01", end="2016-12-31")


def test_trend_has_no_lookahead(prices):
    """Changing future prices must not change today's signal."""
    w1 = strategies.trend(prices, 200, "weekly")
    cut = prices.index[1000]
    shocked = prices.copy()
    shocked.loc[shocked.index > cut] *= 0.3
    w2 = strategies.trend(shocked, 200, "weekly")
    pd.testing.assert_frame_equal(w1.loc[:cut], w2.loc[:cut])


def test_weights_long_or_cash(prices, cfg):
    for name in ("trend", "rotation", "dip"):
        w = strategies.build_weights(prices, cfg, name)
        assert (w >= 0).all().all()
        assert (w.sum(axis=1) <= 1 + 1e-9).all()


def test_backtest_trades_next_bar(prices):
    w = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    w.iloc[10:, 0] = 1.0
    res = backtest.run(prices, w, {"spread_bps": 0}, start_equity=1000)
    assert res.trades["date"].iloc[0] == prices.index[11]


def test_costs_reduce_returns(prices, cfg):
    w = strategies.trend(prices, 200, "weekly")
    free = backtest.run(prices, w, {"spread_bps": 0}).equity.iloc[-1]
    costly = backtest.run(prices, w, {"spread_bps": 50, "commission_gbp": 1}).equity.iloc[-1]
    assert costly < free


def test_splice_uses_proxy_before_ucits():
    idx = pd.bdate_range("2010-01-01", periods=10)
    proxy = pd.Series(0.01, index=idx)
    ucits = pd.Series(0.02, index=idx[5:])
    out, first = data.splice(proxy, ucits)
    assert first == idx[5]
    assert (out.loc[: idx[4]] == 0.01).all() and (out.loc[idx[5]:] == 0.02).all()


def test_fx_conversion_direction():
    idx = pd.bdate_range("2020-01-01", periods=3)
    usd = pd.Series([np.nan, 0.0, 0.0], index=idx)
    gbpusd = pd.Series([1.25, 1.30, 1.30], index=idx)  # pound strengthens
    gbp = data.usd_to_gbp_returns(usd, gbpusd)
    assert gbp.iloc[1] < 0  # flat USD asset loses value in GBP


def test_quality_flags_spike(prices):
    bad = prices.copy()
    bad.iloc[500, 0] *= 100  # pence/pounds style error
    assert not quality.check_prices(bad)["ok"]
    assert quality.check_prices(prices)["ok"]


def _state(cash=5000, pos=None, equity=5000, peak=5000):
    return {"cash_gbp": cash, "positions_gbp": pos or {}, "equity_gbp": equity, "peak_equity_gbp": peak}


def test_risk_caps_and_blocks(cfg, tmp_path):
    c = copy.deepcopy(cfg)
    c["risk"]["kill_switch_file"] = str(tmp_path / "KILL")
    big = risk.Order("US_EQ", "CSPX.L", "buy", 5000)
    assert risk.review([big], _state(), c)["rejected"]
    ok = risk.Order("US_EQ", "CSPX.L", "buy", 900)
    assert risk.review([ok], _state(), c)["approved"]
    short = risk.Order("US_EQ", "CSPX.L", "sell", 100)
    assert risk.review([short], _state(), c)["rejected"]
    # drawdown pause blocks buys
    assert risk.review([ok], _state(equity=4000, cash=4000, peak=5000), c)["rejected"]
    # kill switch blocks everything
    (tmp_path / "KILL").write_text("stop")
    assert risk.review([ok], _state(), c)["rejected"]


def test_timemachine_reproducible_and_sane():
    from etfbot import timemachine
    idx = pd.bdate_range("2010-01-01", periods=2000)
    rng = np.random.default_rng(1)
    s = pd.Series(rng.normal(0.0003, 0.01, len(idx)), index=idx)
    b = pd.Series(rng.normal(0.0003, 0.012, len(idx)), index=idx)
    a1 = timemachine.monte_carlo(s, b, paths=500, seed=7)
    a2 = timemachine.monte_carlo(s, b, paths=500, seed=7)
    assert a1["return_pct"] == a2["return_pct"]
    r = a1["return_pct"]
    assert r["p5"] <= r["p50"] <= r["p95"]
    assert 0 <= a1["prob_loss"] <= 1 and a1["max_drawdown_pct"]["p50"] <= 0
    h = timemachine.history((1 + s).cumprod(), (1 + b).cumprod())
    assert h["windows"] > 100
