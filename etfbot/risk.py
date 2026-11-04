"""Risk Guardian. Hard limits in code. Nothing (bot, workflow, LLM) can override them.

Every proposed order passes through `review`. Rejected orders are logged with reasons.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Order:
    sleeve: str
    ticker: str
    side: str          # "buy" | "sell"
    value_gbp: float


def review(orders: list[Order], state: dict, cfg: dict) -> dict:
    r = cfg["risk"]
    approved, rejected = [], []
    equity = state["equity_gbp"]
    peak = max(state.get("peak_equity_gbp", equity), equity)
    drawdown = equity / peak - 1 if peak > 0 else 0.0
    killed = Path(r["kill_switch_file"]).exists()
    paused = drawdown <= -r["drawdown_pause_frac"]
    from .scaling import order_cap
    max_order = order_cap(cfg, state.get("size_multiplier", 1.0))

    for o in orders:
        why = []
        if killed:
            why.append("kill switch active")
        if o.side not in ("buy", "sell"):
            why.append("invalid side (long-or-cash only)")
        if o.value_gbp <= 0:
            why.append("non-positive order value")
        if o.side == "buy":
            if paused:
                why.append(f"drawdown {drawdown:.1%} beyond pause limit")
            if o.value_gbp > max_order:
                why.append(f"order £{o.value_gbp:.0f} above cap £{max_order:.0f}")
            held = state.get("positions_gbp", {}).get(o.sleeve, 0.0)
            if (held + o.value_gbp) / equity > r["max_position_frac"] + 1e-9:
                why.append(f"{o.sleeve} would exceed {r['max_position_frac']:.0%} of equity")
            if o.value_gbp > state.get("cash_gbp", 0.0) + 1e-9:
                why.append("insufficient cash (no leverage)")
        if o.side == "sell":
            held = state.get("positions_gbp", {}).get(o.sleeve, 0.0)
            if o.value_gbp > held + 1e-6:
                why.append("sell larger than holding (no shorting)")
        if len(approved) >= r["max_orders_per_day"]:
            why.append("daily order limit reached")
        (rejected if why else approved).append({"order": o.__dict__, "reasons": why})
    return {"approved": approved, "rejected": rejected, "drawdown": drawdown,
            "paused": paused, "kill_switch": killed}
