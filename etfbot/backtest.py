"""Holdings-based daily backtester.

- Target weights from date t are traded at the close of t+1 (one-bar lag, no look-ahead).
- Between trades, holdings drift with prices (no hidden daily rebalancing).
- Costs: spread/slippage in bps on traded value + fixed commission per order.
- Weights are capped at risk.max_position_frac so tests match live limits.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .strategies import month_end_mask

DAYS = 252


@dataclass
class Result:
    equity: pd.Series
    trades: pd.DataFrame
    weights: pd.DataFrame
    metrics: dict = field(default_factory=dict)


def run(prices: pd.DataFrame, target: pd.DataFrame, costs: dict, max_position_frac: float = 1.0,
        start_equity: float = 10_000.0, rebalance: str | None = None, min_trade_gbp: float = 1.0) -> Result:
    target = target.reindex(prices.index).fillna(0.0).clip(lower=0.0, upper=max_position_frac)
    exec_w = target.shift(1).fillna(0.0)          # trade tomorrow on today's signal
    rebal = month_end_mask(prices.index) if rebalance == "monthly" else pd.Series(False, index=prices.index)

    spread = costs.get("spread_bps", 0.0) / 1e4
    commission = costs.get("commission_gbp", 0.0)
    cash_daily = (1 + costs.get("cash_rate", 0.0)) ** (1 / DAYS) - 1

    px = prices.to_numpy()
    w = exec_w.to_numpy()
    cols = list(prices.columns)
    units = np.zeros(len(cols))
    cash = start_equity
    last_w = np.full(len(cols), np.nan)
    eq, trade_rows = [], []

    for i, t in enumerate(prices.index):
        cash *= 1 + cash_daily
        value = units * px[i]
        equity = cash + value.sum()
        changed = not np.allclose(w[i], last_w, equal_nan=False)
        if changed or rebal.iloc[i]:
            desired = w[i] * equity
            delta = desired - value
            for j, d in enumerate(delta):
                if abs(d) < min_trade_gbp:
                    continue
                cost = abs(d) * spread + commission
                units[j] += d / px[i, j]
                cash -= d + cost
                trade_rows.append({"date": t, "sleeve": cols[j], "value_gbp": d, "cost_gbp": cost})
            last_w = w[i].copy()
            equity = cash + (units * px[i]).sum()
        eq.append(equity)

    equity = pd.Series(eq, index=prices.index, name="equity")
    trades = pd.DataFrame(trade_rows, columns=["date", "sleeve", "value_gbp", "cost_gbp"])
    res = Result(equity, trades, exec_w)
    res.metrics = metrics(equity, trades)
    return res


def metrics(equity: pd.Series, trades: pd.DataFrame | None = None) -> dict:
    equity = equity.dropna()
    if len(equity) < 2:
        return {}
    rets = equity.pct_change().dropna()
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1 if years > 0 else float("nan")
    vol = rets.std() * np.sqrt(DAYS)
    sharpe = rets.mean() / rets.std() * np.sqrt(DAYS) if rets.std() > 0 else 0.0
    dd = equity / equity.cummax() - 1
    out = {
        "start": str(equity.index[0].date()),
        "end": str(equity.index[-1].date()),
        "total_return": float(equity.iloc[-1] / equity.iloc[0] - 1),
        "cagr": float(cagr),
        "vol": float(vol),
        "sharpe": float(sharpe),
        "max_drawdown": float(dd.min()),
    }
    if trades is not None and not trades.empty:
        t = trades[(trades["date"] >= equity.index[0]) & (trades["date"] <= equity.index[-1])]
        out["orders"] = int(len(t))
        out["orders_per_year"] = float(len(t) / years) if years > 0 else float("nan")
        out["costs_gbp"] = float(t["cost_gbp"].sum())
    return out


def period_metrics(equity: pd.Series, start: str | None, end: str | None) -> dict:
    e = equity.loc[start:end]
    return metrics(e) if len(e) > 1 else {}
