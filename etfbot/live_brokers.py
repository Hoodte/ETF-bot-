"""Broker adapters for Trading 212 (pyt212) and Interactive Brokers (ib_async).

Safety design (approval-gate pattern adapted from trader-broker in
Jakeschincariol/day-trader-skill, MIT):

1. Every order must already have passed risk.review (the caller guarantees this).
2. Demo / paper accounts (t212_demo, ibkr_paper) execute after the risk check.
3. Real-money accounts (t212_live, ibkr_live) need ALL of:
   - config `mode: live`
   - config `broker.allow_real_money: true`
   - a human approval file for that exact order: `python -m etfbot approve <id>`
   Orders without approval are queued and reported, never sent.

Status: written against the libraries' source code but NOT yet run against a
real Trading 212 or IBKR account. Test on the demo/paper account first.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import date
from pathlib import Path

REAL_MONEY = {"t212_live", "ibkr_live"}


def order_id(order: dict, day: str | None = None) -> str:
    day = day or date.today().isoformat()
    raw = f"{day}|{order['sleeve']}|{order['side']}|{order['value_gbp']:.2f}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]


class ApprovalGate:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.kind = cfg["broker"]["name"]
        self.dir = Path(cfg["paths"]["state_dir"]) / "approvals"

    def check(self, order: dict) -> tuple[bool, str]:
        if self.kind not in REAL_MONEY:
            return True, "demo/paper account"
        if self.cfg["mode"] != "live":
            return False, "real-money broker selected but mode is not 'live'"
        if not self.cfg["broker"].get("allow_real_money", False):
            return False, "broker.allow_real_money is false"
        oid = order_id(order)
        if not (self.dir / oid).exists():
            self.queue(order, oid)
            return False, f"awaiting human approval: python -m etfbot approve {oid}"
        return True, f"approved by human ({oid})"

    def queue(self, order: dict, oid: str) -> None:
        q = self.dir / "pending"
        q.mkdir(parents=True, exist_ok=True)
        (q / f"{oid}.json").write_text(json.dumps(order, indent=2))


def approve(cfg: dict, oid: str) -> dict:
    d = Path(cfg["paths"]["state_dir"]) / "approvals"
    pending = d / "pending" / f"{oid}.json"
    if not pending.exists():
        return {"ok": False, "error": f"no pending order {oid}"}
    (d / oid).write_text(pending.read_text())
    return {"ok": True, "approved": oid, "order": json.loads(pending.read_text())}


def _round_down(q: float, decimals: int) -> float:
    f = 10 ** decimals
    return math.floor(q * f) / f


class Trading212Broker:
    """Trading 212 Invest / Stocks ISA via pyt212. Needs T212_API_KEY and T212_API_SECRET."""

    def __init__(self, cfg: dict, quote_gbp, client=None):
        self.cfg = cfg
        self.quote_gbp = quote_gbp            # function(sleeve) -> price per unit in GBP
        self.tickers = {k: v.get("t212_ticker") for k, v in cfg["instruments"].items()}
        if client is None:
            import t212
            live = cfg["broker"]["name"] == "t212_live"
            client = t212.Trading212Client(
                api_key=os.environ["T212_API_KEY"], api_secret=os.environ["T212_API_SECRET"],
                base_url=t212.DEFAULT_LIVE_URL if live else t212.DEFAULT_DEMO_URL, retry_on_429=True)
        self.client = client

    def _sleeve_for(self, ticker: str | None):
        return next((s for s, t in self.tickers.items() if t and t == ticker), None)

    def snapshot(self) -> dict:
        summary = self.client.get_account_summary()
        pos = {}
        for p in self.client.get_positions():
            s = self._sleeve_for(p.instrument.ticker if p.instrument else None)
            if s and p.wallet_impact and p.wallet_impact.current_value is not None:
                pos[s] = pos.get(s, 0.0) + float(p.wallet_impact.current_value)
        cash = float(summary.cash.available_to_trade or 0.0) if summary.cash else 0.0
        return {"cash_gbp": cash, "positions_gbp": pos,
                "equity_gbp": float(summary.total_value or cash + sum(pos.values()))}

    def execute(self, order: dict) -> dict:
        import t212
        ticker = self.tickers.get(order["sleeve"])
        if not ticker:
            raise ValueError(f"set instruments.{order['sleeve']}.t212_ticker in config.yaml")
        price = self.quote_gbp(order["sleeve"])
        qty = _round_down(order["value_gbp"] / price, self.cfg["broker"].get("quantity_decimals", 2))
        if qty <= 0:
            raise ValueError("order rounds to zero shares")
        signed = qty if order["side"] == "buy" else -qty   # pyt212: negative quantity = sell
        res = self.client.place_market_order(t212.MarketOrderRequest(ticker=ticker, quantity=signed))
        return {**order, "broker": self.cfg["broker"]["name"], "quantity": signed,
                "est_price_gbp": price, "broker_order_id": getattr(res, "id", None)}


class IBKRBroker:
    """Interactive Brokers via ib_async. Needs TWS or IB Gateway running (paper port 7497)."""

    def __init__(self, cfg: dict, quote_gbp, ib=None):
        self.cfg = cfg
        self.quote_gbp = quote_gbp
        if ib is None:
            from ib_async import IB
            ib = IB()
            b = cfg["broker"]
            port = b.get("ibkr_port", 7496 if b["name"] == "ibkr_live" else 7497)
            ib.connect(b.get("ibkr_host", "127.0.0.1"), port, clientId=b.get("ibkr_client_id", 1))
        self.ib = ib

    def _contract(self, sleeve: str):
        from ib_async import Stock
        c = self.cfg["instruments"][sleeve].get("ibkr")
        if not c:
            raise ValueError(f"set instruments.{sleeve}.ibkr (symbol, exchange, currency) in config.yaml")
        contract = Stock(c["symbol"], c["exchange"], c["currency"])
        self.ib.qualifyContracts(contract)
        return contract

    def snapshot(self) -> dict:
        vals = {v.tag: v for v in self.ib.accountSummary() if v.currency in ("GBP", "BASE")}
        equity = float(vals["NetLiquidation"].value) if "NetLiquidation" in vals else 0.0
        cash = float(vals["TotalCashValue"].value) if "TotalCashValue" in vals else 0.0
        by_symbol = {(v.get("ibkr") or {}).get("symbol"): k for k, v in self.cfg["instruments"].items()
                     if (v.get("ibkr") or {}).get("symbol")}
        pos = {}
        for p in self.ib.positions():
            s = by_symbol.get(p.contract.symbol)
            if s:
                pos[s] = pos.get(s, 0.0) + float(p.position) * self.quote_gbp(s)
        return {"cash_gbp": cash, "positions_gbp": pos, "equity_gbp": equity or cash + sum(pos.values())}

    def execute(self, order: dict) -> dict:
        from ib_async import MarketOrder
        price = self.quote_gbp(order["sleeve"])
        qty = math.floor(order["value_gbp"] / price)   # whole shares
        if qty <= 0:
            raise ValueError("order rounds to zero shares")
        trade = self.ib.placeOrder(self._contract(order["sleeve"]),
                                   MarketOrder("BUY" if order["side"] == "buy" else "SELL", qty))
        return {**order, "broker": self.cfg["broker"]["name"], "quantity": qty,
                "est_price_gbp": price, "broker_order_id": getattr(trade.order, "orderId", None)}


def make_broker(cfg: dict, quote_gbp):
    name = cfg["broker"]["name"]
    if name in ("t212_demo", "t212_live"):
        return Trading212Broker(cfg, quote_gbp)
    if name in ("ibkr_paper", "ibkr_live"):
        return IBKRBroker(cfg, quote_gbp)
    raise ValueError(f"unknown broker {name}")
