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
    mask = week_end_mask(raw.index) if check == "weekly" else month_end_mask(raw.index)
    return raw.where(mask, axis=0).ffill().fillna(0.0)


def cap_weights(w: pd.DataFrame, cap: float) -> pd.DataFrame:
    """Cap each weight, handing the excess to uncapped assets in proportion. Leftover = cash."""
    w = w.copy()
    for _ in range(10):
        over = w > cap + 1e-12
        if not over.any().any():
            break
        excess = (w - cap).clip(lower=0).sum(axis=1)
        w = w.clip(upper=cap)
        room = (cap - w).where(~over & (w > 0), 0.0)
        share = room.div(room.sum(axis=1).replace(0, float("nan")), axis=0).fillna(0.0)
        w = w + share.mul(excess, axis=0).clip(upper=room)
    return w


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


def faber(prices: pd.DataFrame, months: int = 10) -> pd.DataFrame:
    """Faber-style trend: monthly check, hold each sleeve while its month-end price > its N-month average."""
    me = month_end_mask(prices.index)
    monthly = prices[me.values]
    sma = monthly.rolling(months, min_periods=months).mean()
    on = (monthly > sma).astype(float).where(sma.notna(), 0.0) / prices.shape[1]
    return on.reindex(prices.index).ffill().fillna(0.0)


def dual_momentum(prices: pd.DataFrame, lookback_days: int = 252, top_n: int = 3,
                  safe: str = "BONDS") -> pd.DataFrame:
    """Monthly: rank risky sleeves by trailing return, keep the top_n. A pick with negative
    momentum (absolute filter) goes to the safe sleeve if the safe sleeve's momentum is positive,
    otherwise to cash."""
    mom = prices.pct_change(lookback_days)
    risky = [c for c in prices.columns if c != safe]
    ranks = mom[risky].rank(axis=1, ascending=False)
    picks = (ranks <= top_n) & mom[risky].notna()
    good = picks & (mom[risky] > 0)
    bad_slots = (picks & ~(mom[risky] > 0)).sum(axis=1)
    w = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    w[risky] = good.astype(float) / top_n
    if safe in prices.columns:
        w[safe] = (bad_slots / top_n).where(mom[safe] > 0, 0.0)
    return _hold_between_checks(w, "monthly")


def _inv_vol(prices: pd.DataFrame, vol_days: int) -> pd.DataFrame:
    vol = prices.pct_change().rolling(vol_days, min_periods=vol_days).std()
    inv = 1.0 / vol
    return inv.div(inv.sum(axis=1), axis=0)


def inverse_vol(prices: pd.DataFrame, vol_days: int = 63, cap: float = 1.0) -> pd.DataFrame:
    """Always invested; monthly weights proportional to 1/volatility, capped."""
    w = cap_weights(_inv_vol(prices, vol_days).fillna(0.0), cap)
    return _hold_between_checks(w, "monthly")


def trend_inverse_vol(prices: pd.DataFrame, sma_days: int = 200, vol_days: int = 63,
                      cap: float = 1.0) -> pd.DataFrame:
    """Weekly: inverse-vol weights, but a sleeve below its SMA goes to cash."""
    sma = prices.rolling(sma_days, min_periods=sma_days).mean()
    on = (prices > sma) & sma.notna()
    w = cap_weights(_inv_vol(prices, vol_days).fillna(0.0), cap).where(on, 0.0)
    return _hold_between_checks(w, "weekly")


def trend_voltarget(prices: pd.DataFrame, sma_days: int = 200, target_vol: float = 0.08,
                    lookback_days: int = 63) -> pd.DataFrame:
    """Trend weights scaled down when the portfolio's recent volatility is above target (never levered)."""
    base = trend(prices, sma_days, "daily")
    port = (base.shift(1) * prices.pct_change()).sum(axis=1)
    realised = port.rolling(lookback_days, min_periods=lookback_days).std() * (252 ** 0.5)
    scale = (target_vol / realised).clip(upper=1.0).fillna(1.0)
    return _hold_between_checks(base.mul(scale, axis=0), "weekly")


def build_weights(prices: pd.DataFrame, cfg: dict, name: str) -> pd.DataFrame:
    s = cfg["strategies"][name]
    if name == "trend":
        return trend(prices, s["sma_days"], s["check"])
    if name == "rotation":
        return rotation(prices, s["lookback_days"], s["top_n"], s["absolute_filter"])
    if name == "dip":
        return dip(prices, s["sleeves"], s["drop_pct"], s["lookback_days"],
                   s["trend_sma_days"], s["exit_sma_days"])
    cap = cfg["risk"]["max_position_frac"]
    if name == "faber":
        return faber(prices, s["months"])
    if name == "dual_momentum":
        return dual_momentum(prices, s["lookback_days"], s["top_n"], s["safe"])
    if name == "inverse_vol":
        return inverse_vol(prices, s["vol_days"], cap)
    if name == "trend_inverse_vol":
        return trend_inverse_vol(prices, s["sma_days"], s["vol_days"], cap)
    if name == "trend_voltarget":
        return trend_voltarget(prices, s["sma_days"], s["target_vol"], s["lookback_days"])
    raise ValueError(f"unknown strategy {name}")


def buy_and_hold(prices: pd.DataFrame) -> pd.DataFrame:
    """Equal-weight benchmark. Run it with rebalance='monthly' in the backtester."""
    return pd.DataFrame(1.0 / prices.shape[1], index=prices.index, columns=prices.columns)


def month_end_mask(index: pd.DatetimeIndex) -> pd.Series:
    s = pd.Series(index, index=index)
    last = s.groupby(index.to_period("M")).transform("max")
    return pd.Series(index == last.values, index=index)
