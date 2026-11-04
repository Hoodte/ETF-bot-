"""Brokers. PaperBroker simulates fills and keeps state on disk.

LiveBroker is deliberately not implemented. Wire it to Trading 212 or IBKR only after
the paper-trade gate passes, and keep every order behind risk.review.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class PaperBroker:
    def __init__(self, state_dir: str | Path, start_cash: float, spread_bps: float = 10.0):
        self.path = Path(state_dir) / "paper_state.json"
        self.spread = spread_bps / 1e4
        if self.path.exists():
            self.state = json.loads(self.path.read_text())
        else:
            self.state = {"cash_gbp": start_cash, "units": {}, "peak_equity_gbp": start_cash,
                          "size_multiplier": 1.0, "fills": []}

    def snapshot(self, prices: dict[str, float]) -> dict:
        pos = {k: u * prices[k] for k, u in self.state["units"].items() if k in prices}
        equity = self.state["cash_gbp"] + sum(pos.values())
        self.state["peak_equity_gbp"] = max(self.state["peak_equity_gbp"], equity)
        return {"cash_gbp": self.state["cash_gbp"], "positions_gbp": pos, "equity_gbp": equity,
                "peak_equity_gbp": self.state["peak_equity_gbp"],
                "size_multiplier": self.state["size_multiplier"]}

    def execute(self, order: dict, price: float) -> dict:
        value = order["value_gbp"]
        cost = value * self.spread
        units = value / price
        if order["side"] == "buy":
            self.state["cash_gbp"] -= value + cost
            self.state["units"][order["sleeve"]] = self.state["units"].get(order["sleeve"], 0.0) + units
        else:
            self.state["cash_gbp"] += value - cost
            self.state["units"][order["sleeve"]] = self.state["units"].get(order["sleeve"], 0.0) - units
            if abs(self.state["units"][order["sleeve"]]) < 1e-9:
                del self.state["units"][order["sleeve"]]
        fill = {**order, "price": price, "cost_gbp": cost, "time": datetime.now(timezone.utc).isoformat()}
        self.state["fills"].append(fill)
        return fill

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.state, indent=2))


class LiveBroker:
    def __init__(self, *_, **__):
        raise NotImplementedError(
            "Live trading is not implemented. Pass the paper-trade gate first, then add a "
            "Trading 212 or IBKR adapter here with every order routed through risk.review.")
