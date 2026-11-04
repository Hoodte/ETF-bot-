import copy
from types import SimpleNamespace as NS

import numpy as np
import pandas as pd
import pytest

from etfbot import live_brokers, trades
from etfbot.config import load_config


@pytest.fixture
def cfg(tmp_path):
    c = load_config("config.yaml")
    c["paths"]["state_dir"] = str(tmp_path / "state")
    return c


ORDER = {"sleeve": "US_EQ", "ticker": "CSPX.L", "side": "buy", "value_gbp": 900.0}


def test_demo_broker_needs_no_human_approval(cfg):
    ok, _ = live_brokers.ApprovalGate(cfg).check(ORDER)
    assert ok


def test_real_money_blocked_until_all_three_gates(cfg):
    c = copy.deepcopy(cfg)
    c["broker"]["name"] = "t212_live"
    gate = live_brokers.ApprovalGate(c)
    assert not gate.check(ORDER)[0]                     # mode is paper
    c["mode"] = "live"
    assert not live_brokers.ApprovalGate(c).check(ORDER)[0]  # allow_real_money false
    c["broker"]["allow_real_money"] = True
    ok, why = live_brokers.ApprovalGate(c).check(ORDER)
    assert not ok and "approve" in why                  # queued for a human
    oid = live_brokers.order_id(ORDER)
    assert live_brokers.approve(c, oid)["ok"]
    assert live_brokers.ApprovalGate(c).check(ORDER)[0]


class FakeT212:
    def __init__(self):
        self.orders = []

    def get_account_summary(self):
        return NS(cash=NS(available_to_trade=4000.0), total_value=5000.0)

    def get_positions(self):
        return [NS(instrument=NS(ticker="CSPXl_EQ"), wallet_impact=NS(current_value=1000.0))]

    def place_market_order(self, req):
        self.orders.append(req)
        return NS(id=42)


def test_t212_adapter_sizes_and_signs_orders(cfg, monkeypatch):
    import sys, types
    fake_mod = types.ModuleType("t212")
    fake_mod.MarketOrderRequest = lambda ticker, quantity: NS(ticker=ticker, quantity=quantity)
    monkeypatch.setitem(sys.modules, "t212", fake_mod)
    c = copy.deepcopy(cfg)
    c["instruments"]["US_EQ"]["t212_ticker"] = "CSPXl_EQ"
    client = FakeT212()
    b = live_brokers.Trading212Broker(c, quote_gbp=lambda s: 450.0, client=client)
    snap = b.snapshot()
    assert snap["positions_gbp"] == {"US_EQ": 1000.0} and snap["cash_gbp"] == 4000.0
    b.execute({**ORDER, "value_gbp": 900.0})
    b.execute({**ORDER, "side": "sell", "value_gbp": 450.0})
    assert client.orders[0].quantity == 2.0 and client.orders[1].quantity == -1.0
    with pytest.raises(ValueError):
        b.execute({**ORDER, "sleeve": "GOLD"})          # ticker not configured


def test_round_trip_stats():
    idx = pd.bdate_range("2020-01-01", periods=10)
    prices = pd.DataFrame({"A": np.arange(100, 110, dtype=float)}, index=idx)
    w = pd.DataFrame({"A": [0, 1, 1, 0, 0, 1, 1, 1, 0, 0]}, index=idx, dtype=float)
    s = trades.summary(trades.round_trips(prices, w))
    assert s["total_trades"] == 2 and s["win_rate_pct"] == 100.0
    cmd = trades.backtest_expert_command(s, -0.12, 18, 1)
    assert "--total-trades 2" in cmd and "--max-drawdown-pct 12.0" in cmd


def test_calendar_knows_uk_holidays():
    pytest.importorskip("exchange_calendars")
    from etfbot import market_calendar
    assert market_calendar.status("2026-12-25")["is_trading_day"] is False
    st = market_calendar.status("2026-11-06")
    assert st["is_trading_day"] and st["is_last_trading_day_of_week"]


class FakeIB:
    def __init__(self):
        self.placed = []

    def accountSummary(self):
        return [NS(tag="NetLiquidation", value="5000", currency="GBP"),
                NS(tag="TotalCashValue", value="4100", currency="GBP")]

    def positions(self):
        return [NS(contract=NS(symbol="CSPX"), position=2.0)]

    def qualifyContracts(self, *c):
        return list(c)

    def placeOrder(self, contract, order):
        self.placed.append((contract, order))
        return NS(order=NS(orderId=7))


def test_ibkr_adapter_whole_shares(cfg, monkeypatch):
    import sys, types
    m = types.ModuleType("ib_async")
    m.Stock = lambda symbol, exchange, currency: NS(symbol=symbol, exchange=exchange, currency=currency)
    m.MarketOrder = lambda action, qty: NS(action=action, totalQuantity=qty)
    monkeypatch.setitem(sys.modules, "ib_async", m)
    c = copy.deepcopy(cfg)
    c["broker"]["name"] = "ibkr_paper"
    c["instruments"]["US_EQ"]["ibkr"] = {"symbol": "CSPX", "exchange": "LSEETF", "currency": "USD"}
    ib = FakeIB()
    b = live_brokers.IBKRBroker(c, quote_gbp=lambda s: 450.0, ib=ib)
    snap = b.snapshot()
    assert snap["equity_gbp"] == 5000.0 and snap["positions_gbp"]["US_EQ"] == 900.0
    b.execute({**ORDER, "value_gbp": 1000.0})
    contract, order = ib.placed[0]
    assert order.action == "BUY" and order.totalQuantity == 2 and contract.exchange == "LSEETF"


def test_scaling_steps_up_10pct_and_down_on_drawdown(cfg):
    from etfbot import scaling
    st = {}
    t0 = pd.Timestamp("2027-01-04")
    assert scaling.review(st, 5000, 5000, cfg, t0)["action"] == "started"
    assert scaling.review(st, 5000, 5000, cfg, t0 + pd.Timedelta(weeks=4))["action"] == "none"
    ev = scaling.review(st, 5200, 5200, cfg, t0 + pd.Timedelta(weeks=8))
    assert ev["action"] == "step_up" and abs(ev["multiplier"] - 1.10) < 1e-9 and ev["order_cap_gbp"] == 1100
    ev = scaling.review(st, 4600, 5200, cfg, t0 + pd.Timedelta(weeks=16))   # -11.5%: between limits
    assert ev["action"] == "hold" and abs(ev["multiplier"] - 1.10) < 1e-9
    ev = scaling.review(st, 4300, 5200, cfg, t0 + pd.Timedelta(weeks=24))   # -17%: past the pause
    assert ev["action"] == "step_down" and abs(ev["multiplier"] - 1.0) < 1e-9
    st["size_multiplier"] = 50
    assert scaling.order_cap(cfg, 50) == cfg["risk"]["max_order_gbp"]       # hard ceiling holds


def test_leveraged_prices_decay_and_cost():
    from etfbot import leverage
    idx = pd.bdate_range("2020-01-01", periods=200)
    up_down = pd.Series([100 * (1.05 if i % 2 else 1 / 1.05) ** 1 for i in range(200)], index=idx)
    px = pd.DataFrame({"US_EQ": up_down})
    lev = leverage.leveraged_prices(px, 2, pd.Series(0.0, index=idx), spread=0, fee=0, sleeves=["US_EQ"])
    assert lev["US_EQ"].iloc[-1] < 100   # choppy, flat market: 2x daily-reset loses value
