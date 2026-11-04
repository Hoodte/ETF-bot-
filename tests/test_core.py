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


def test_deflated_sharpe_penalises_many_trials():
    from etfbot import discover
    idx = pd.bdate_range("2016-01-01", periods=2500)
    r = pd.Series(np.random.default_rng(3).normal(0.0004, 0.01, len(idx)), index=idx)
    few = discover.deflated_sharpe(r, discover.expected_max_sharpe(0.0001, 2))
    many = discover.expected_max_sharpe(0.0001, 1000)
    assert many > discover.expected_max_sharpe(0.0001, 2)
    assert discover.deflated_sharpe(r, many) < few


def test_cap_weights_redistributes():
    w = pd.DataFrame([[0.6, 0.2, 0.2]], columns=list("abc"))
    out = strategies.cap_weights(w, 0.4)
    assert (out <= 0.4 + 1e-9).all().all() and abs(out.sum(axis=1).iloc[0] - 1.0) < 1e-9


def test_new_strategies_no_lookahead(prices, cfg):
    cut = prices.index[1200]
    shocked = prices.copy()
    shocked.loc[shocked.index > cut] *= 0.3
    for name in ("faber", "dual_momentum", "inverse_vol", "trend_inverse_vol", "trend_voltarget"):
        a = strategies.build_weights(prices, cfg, name).loc[:cut]
        b = strategies.build_weights(shocked, cfg, name).loc[:cut]
        pd.testing.assert_frame_equal(a, b, check_names=False)


def test_research_strategies_no_lookahead(prices, cfg):
    cut = prices.index[1200]
    shocked = prices.copy()
    shocked.loc[shocked.index > cut] *= 0.3
    for name in ("tsmom", "sma_cross", "turn_of_month", "rsi2"):
        a = strategies.build_weights(prices, cfg, name).loc[:cut]
        b = strategies.build_weights(shocked, cfg, name).loc[:cut]
        pd.testing.assert_frame_equal(a, b, check_names=False)


def test_turn_of_month_window(prices):
    w = strategies.turn_of_month(prices[["US_EQ"]], 1, 3)["US_EQ"]
    held_days = w.shift(1).fillna(0)  # what is actually held each day
    jan = held_days.loc["2011-01"]
    assert (jan.iloc[:3] == 1).all() and (jan.iloc[3:-1] == 0).all() and jan.iloc[-1] == 1


def test_combine_auto_pick_and_chart(cfg, tmp_path):
    from etfbot import chart, combine
    p = data.synthetic_universe(list(cfg["instruments"]), start="2008-01-01", end="2020-12-31")
    res = combine.run(p, cfg, "US_EQ", None)
    assert len(res["components"]) == 3 and set(res["curves"]) >= {"blend", "buy_hold"}
    blend = res["curves"]["blend"]
    assert blend.notna().all()
    out = chart.write_html(res, str(tmp_path / "c.html"))
    assert "Out-of-sample" in open(out).read()
    with pytest.raises(ValueError):
        combine.run(p, cfg, "US_EQ", ["trend", "faber", "tsmom", "rsi2"])  # more than 3


def test_calendar_rules():
    from etfbot import strategies as st
    idx = pd.bdate_range("2026-12-01", "2027-01-29").drop(pd.Timestamp("2026-12-25")).drop(pd.Timestamp("2026-12-28"))
    ph = st._pre_holiday_days(idx)
    assert ph.loc["2026-12-24"] and not ph.loc["2026-12-23"]
    opex = st._opex_week_days(idx)
    assert opex.loc["2026-12-14":"2026-12-18"].all() and not opex.loc["2026-12-21"]  # 3rd Fri = 18 Dec 2026
    p = pd.DataFrame({"X": np.linspace(100, 120, len(idx))}, index=idx)
    w = st.pre_holiday(p)["X"]
    assert w.loc["2026-12-23"] == 1 and w.loc["2026-12-24"] == 0  # signal the day before, held on the 24th


def test_manual_csv_source(tmp_path):
    (tmp_path / "SPY.csv").write_text("Date,Open,Close,Adj Close\n2020-01-03,1,2,1.9\n2020-01-02,1,2,1.8\n")
    s = data.read_manual_csv("SPY", tmp_path)
    assert list(s) == [1.8, 1.9] and s.index.is_monotonic_increasing


def test_clean_ucits_spike_and_unit_switch():
    idx = pd.bdate_range("2011-01-03", periods=12)
    px = pd.Series([100, 101, 102, 160, 103, 104, 60, 61, 62, 62.5, 63, 64], index=idx, dtype=float)
    cleaned, trusted, notes = data.clean_ucits(px)
    assert cleaned.iloc[3] == 102            # one-day spike removed
    assert trusted == idx[6]                  # level jump (unit switch) -> trust only after it
    assert any("spike" in n for n in notes) and any("jump" in n for n in notes)
