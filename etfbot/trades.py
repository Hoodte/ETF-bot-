"""Round-trip trade statistics, used to feed the backtest-expert skill.

A "trade" is one continuous holding period of a sleeve (weight > 0 from entry
to exit). Its return is the sleeve's price change over that period. This
ignores small top-up rebalances inside a holding period.
"""
from __future__ import annotations

import pandas as pd


def round_trips(prices: pd.DataFrame, exec_weights: pd.DataFrame) -> pd.DataFrame:
    rows = []
    held = exec_weights.reindex(prices.index).fillna(0.0) > 0
    for col in prices.columns:
        h = held[col]
        start = None
        for t, on in h.items():
            if on and start is None:
                start = t
            elif not on and start is not None:
                rows.append({"sleeve": col, "entry": start, "exit": t,
                             "return": prices.at[t, col] / prices.at[start, col] - 1})
                start = None
        if start is not None:  # still open at the end: mark to last price
            t = prices.index[-1]
            rows.append({"sleeve": col, "entry": start, "exit": t,
                         "return": prices.at[t, col] / prices.at[start, col] - 1, "open": True})
    return pd.DataFrame(rows, columns=["sleeve", "entry", "exit", "return", "open"])


def summary(trips: pd.DataFrame) -> dict:
    closed = trips[trips["open"] != True] if "open" in trips else trips  # noqa: E712
    if closed.empty:
        return {"total_trades": 0}
    wins, losses = closed[closed["return"] > 0], closed[closed["return"] <= 0]
    return {
        "total_trades": int(len(closed)),
        "win_rate_pct": round(100 * len(wins) / len(closed), 1),
        "avg_win_pct": round(100 * wins["return"].mean(), 2) if len(wins) else 0.0,
        "avg_loss_pct": round(-100 * losses["return"].mean(), 2) if len(losses) else 0.0,
        "avg_hold_days": round(float((closed["exit"] - closed["entry"]).dt.days.mean()), 1),
    }


def backtest_expert_command(stats: dict, max_dd: float, years: float, num_params: int) -> str:
    """The exact command for the vendored backtest-expert skill's evaluator."""
    return ("python3 .claude/skills/backtest-expert/scripts/evaluate_backtest.py "
            f"--total-trades {stats.get('total_trades', 0)} "
            f"--win-rate {stats.get('win_rate_pct', 0)} "
            f"--avg-win-pct {stats.get('avg_win_pct', 0)} "
            f"--avg-loss-pct {stats.get('avg_loss_pct', 0)} "
            f"--max-drawdown-pct {abs(max_dd) * 100:.1f} "
            f"--years-tested {int(years)} "
            f"--num-parameters {num_params} "
            "--slippage-tested --output-dir reports/")
