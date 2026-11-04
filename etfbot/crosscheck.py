"""Independent cross-check of our backtester using vectorbt.

Same prices, same next-bar weights, same spread cost, orders only when the
target changes. If the two engines disagree by more than a small tolerance,
one of them has a bug and the backtest should not be trusted.

vectorbt licence: Apache 2.0 with Commons Clause (free to use, not to resell).
"""
from __future__ import annotations

import pandas as pd

from . import backtest


def run(prices: pd.DataFrame, target: pd.DataFrame, costs: dict, max_position_frac: float,
        start_equity: float, tolerance: float = 0.02) -> dict:
    try:
        import vectorbt as vbt
    except ImportError as e:
        raise RuntimeError("vectorbt is not installed: pip install vectorbt") from e

    ours = backtest.run(prices, target, costs, max_position_frac, start_equity)
    w = ours.weights  # already shifted one bar and capped, exactly as traded
    changed = w.ne(w.shift(1)).any(axis=1)
    changed.iloc[0] = True
    size = w.where(changed, other=float("nan"), axis=0)

    pf = vbt.Portfolio.from_orders(
        close=prices, size=size, size_type="targetpercent",
        fees=costs.get("spread_bps", 0.0) / 1e4, fixed_fees=costs.get("commission_gbp", 0.0),
        init_cash=start_equity, cash_sharing=True, group_by=True, call_seq="auto", freq="1D")
    theirs = pf.value()
    if isinstance(theirs, pd.DataFrame):
        theirs = theirs.iloc[:, 0]

    a, b = float(ours.equity.iloc[-1]), float(theirs.iloc[-1])
    diff = abs(a - b) / a
    return {"ours_final_gbp": round(a, 2), "vectorbt_final_gbp": round(b, 2),
            "difference_pct": round(100 * diff, 3), "agree": bool(diff <= tolerance),
            "tolerance_pct": 100 * tolerance}
