"""Signal engine. Pure functions of past prices -> target weights.

Rules:
- A weight on date t uses only prices up to and including t.
- The backtester applies weights from the NEXT bar (no look-ahead).
- Weights are long-or-cash: each between 0 and 1, row sum <= 1. Unallocated = cash.
"""
from __future__ import annotations

import pandas as pd


def week_end_mask(index: pd.DatetimeIndex) -> pd.Series:
    """True on the last available trading day of each calendar week."""
    s = pd.Series(index, index=index)
    last = s.groupby(index.to_period("W-FRI")).transform("max")
    return pd.Series(index == last.values, index=index)


def _hold_between_checks(raw: pd.DataFrame, check: str) -> pd.DataFrame:
    if check == "daily":
        return raw
    mask = week_end_mask(raw.index)
    return raw.where(mask).ffill().fillna(0.0)


def trend(prices: pd.DataFrame, sma_days: int = 200, check: str = "weekly") -> pd.DataFrame:
    """Equal-weight sleeves; each sleeve held only while price > SMA, else cash."""
    sma = prices.rolling(sma_days, min_periods=sma_days).mean()
    on = (prices > sma).astype(float).where(sma.notna(), 0.0)
    w = on / prices.shape[1]
    return _hold_between_checks(w, check)


def rotation(prices: pd.DataFrame, lookback_days: int = 126, top_n: int = 3,
             absolute_filter: bool = True) -> pd.DataFrame:
    """Weekly: hold the top_n sleeves by trailing return, equal weight. One cross-ETF strategy."""
    mom = prices.pct_change(lookback_days)
    ranks = mom.rank(axis=1, ascending=False)
    pick = (ranks <= top_n) & mom.notna()
    if absolute_filter:
        pick &= mom > 0
    w = pick.astype(float) / top_n
    return _hold_between_checks(w, "weekly")


def dip(prices: pd.DataFrame, sleeves: list[str], drop_pct=0.05, lookback_days=5,
        trend_sma_days=200, exit_sma_days=5) -> pd.DataFrame:
    """Daily: buy a sharp short drop while in a long uptrend; exit when price closes above a short SMA."""
    w = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    cols = [c for c in sleeves if c in prices.columns]
    if not cols:
        return w
    p = prices[cols]
    long_sma = p.rolling(trend_sma_days, min_periods=trend_sma_days).mean()
    short_sma = p.rolling(exit_sma_days, min_periods=exit_sma_days).mean()
    drop = p.pct_change(lookback_days)
    entry = (drop <= -drop_pct) & (p > long_sma)
    exit_ = p > short_sma
    state = pd.DataFrame(0.0, index=p.index, columns=cols)
    holding = pd.Series(False, index=cols)
    for t in p.index:
        holding = (holding & ~exit_.loc[t]) | entry.loc[t]
        state.loc[t] = holding.astype(float)
    w[cols] = state / len(cols)
    return w


def build_weights(prices: pd.DataFrame, cfg: dict, name: str) -> pd.DataFrame:
    s = cfg["strategies"][name]
    if name == "trend":
        return trend(prices, s["sma_days"], s["check"])
    if name == "rotation":
        return rotation(prices, s["lookback_days"], s["top_n"], s["absolute_filter"])
    if name == "dip":
        return dip(prices, s["sleeves"], s["drop_pct"], s["lookback_days"],
                   s["trend_sma_days"], s["exit_sma_days"])
    raise ValueError(f"unknown strategy {name}")


def buy_and_hold(prices: pd.DataFrame) -> pd.DataFrame:
    """Equal-weight benchmark. Run it with rebalance='monthly' in the backtester."""
    return pd.DataFrame(1.0 / prices.shape[1], index=prices.index, columns=prices.columns)


def month_end_mask(index: pd.DatetimeIndex) -> pd.Series:
    s = pd.Series(index, index=index)
    last = s.groupby(index.to_period("M")).transform("max")
    return pd.Series(index == last.values, index=index)
