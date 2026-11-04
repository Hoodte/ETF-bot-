"""Trade-size scaling: raise the order-size cap by a fixed step after each good review period.

Every `review_weeks`, the bot reviews the account:
- drawdown from peak at or beyond the pause limit  -> cut the multiplier by step_down_frac (never below 1.0)
- drawdown shallower than `max_drawdown_for_step_up` -> raise it by step_up_frac (e.g. +10%)
- anything in between                               -> hold

order cap = account.base_trade_size_gbp * multiplier, never above risk.max_order_gbp.
Position sizes are a share of equity, so money you add is used automatically; this cap
only controls how big a single order may be, so a big top-up is invested over several runs.
"""
from __future__ import annotations

import pandas as pd


def order_cap(cfg: dict, multiplier: float) -> float:
    return min(cfg["risk"]["max_order_gbp"], cfg["account"]["base_trade_size_gbp"] * multiplier)


def review(state: dict, equity: float, peak: float, cfg: dict, today: pd.Timestamp | None = None) -> dict:
    sc = cfg["scaling"]
    today = (today or pd.Timestamp.now()).normalize()
    m = float(state.get("size_multiplier", 1.0))
    last = state.get("last_scale_review")
    if last is None:
        state["last_scale_review"] = str(today.date())
        return {"action": "started", "multiplier": m}
    weeks = (today - pd.Timestamp(last)).days / 7
    if weeks < sc["review_weeks"]:
        return {"action": "none", "multiplier": m, "next_review_in_weeks": round(sc["review_weeks"] - weeks, 1)}
    dd = equity / peak - 1 if peak > 0 else 0.0
    if dd <= -cfg["risk"]["drawdown_pause_frac"] and sc.get("step_down_on_drawdown", True):
        new, action = max(1.0, m * (1 - sc["step_down_frac"])), "step_down"
    elif dd > -sc["max_drawdown_for_step_up"]:
        new, action = min(sc["max_multiplier"], m * (1 + sc["step_up_frac"])), "step_up"
    else:
        new, action = m, "hold"
    state["size_multiplier"] = round(new, 4)
    state["last_scale_review"] = str(today.date())
    return {"action": action, "multiplier": state["size_multiplier"], "drawdown": round(dd, 4),
            "order_cap_gbp": round(order_cap(cfg, state["size_multiplier"]), 2)}
