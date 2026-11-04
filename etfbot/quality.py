"""Data Quality checks. The strategy engine must not run if any check fails."""
from __future__ import annotations

import pandas as pd


def check_prices(prices: pd.DataFrame, max_daily_move=0.25, max_gap_days=7, stale_days=5,
                 as_of: pd.Timestamp | None = None) -> dict:
    issues = []
    if prices.empty:
        return {"ok": False, "issues": ["no data"]}
    if prices.isna().any().any():
        issues.append(f"missing values in: {list(prices.columns[prices.isna().any()])}")
    if prices.index.duplicated().any():
        issues.append("duplicate dates")
    if (prices <= 0).any().any():
        issues.append("non-positive prices")
    moves = prices.pct_change().abs()
    spikes = moves[moves > max_daily_move].stack().dropna()
    for (d, col), v in spikes.items():
        issues.append(f"spike {col} {d.date()} {v:.1%} (check pence/pounds or bad tick)")
    gaps = prices.index.to_series().diff().dt.days
    for d, g in gaps[gaps > max_gap_days].items():
        issues.append(f"gap of {int(g)} days before {d.date()}")
    if as_of is not None:
        age = (as_of.normalize() - prices.index[-1].normalize()).days
        if age > stale_days:
            issues.append(f"data is stale: last bar {prices.index[-1].date()} ({age} days old)")
    return {"ok": not issues, "issues": issues, "last_bar": str(prices.index[-1].date())}
