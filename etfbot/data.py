"""Price data: download, cache, proxy splice and GBP conversion.

All series are handled as daily *returns*, then turned back into a price index.
Working in returns makes the splice unit-free (Yahoo sometimes quotes London
lines in pence and sometimes in pounds) and keeps proxy and UCITS histories
comparable.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def download_close(ticker: str, start: str, cache_dir: str | Path) -> pd.Series:
    """Adjusted close for one ticker, cached to CSV. Needs internet + yfinance."""
    cache = Path(cache_dir) / f"{ticker.replace('=', '_')}.csv"
    if cache.exists():
        s = pd.read_csv(cache, index_col=0, parse_dates=True).iloc[:, 0]
        s.name = ticker
        return s
    import yfinance as yf  # optional dependency, only needed to fetch

    df = yf.download(ticker, start=start, auto_adjust=True, progress=False)
    if df.empty:
        raise RuntimeError(f"No data returned for {ticker}")
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    close = close.dropna()
    close.name = ticker
    cache.parent.mkdir(parents=True, exist_ok=True)
    close.to_csv(cache)
    return close


def blend_returns(closes: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
    """Weighted daily returns of several proxies (rebalanced daily)."""
    rets = pd.concat({t: closes[t].pct_change() for t in weights}, axis=1).dropna()
    w = pd.Series(weights)
    return rets.mul(w, axis=1).sum(axis=1)


def usd_to_gbp_returns(usd_rets: pd.Series, gbpusd: pd.Series) -> pd.Series:
    """Convert USD asset returns to GBP returns. gbpusd = USD per 1 GBP."""
    fx = gbpusd.reindex(usd_rets.index).ffill()
    usd_per_gbp_change = fx.pct_change()
    # value in GBP = value in USD / (USD per GBP)
    return (1 + usd_rets) / (1 + usd_per_gbp_change) - 1


def splice(proxy_rets: pd.Series, ucits_rets: pd.Series | None) -> tuple[pd.Series, pd.Timestamp | None]:
    """Use proxy returns before the UCITS fund's first date, real returns after."""
    if ucits_rets is None or ucits_rets.dropna().empty:
        return proxy_rets.dropna(), None
    ucits_rets = ucits_rets.dropna()
    first = ucits_rets.index[0]
    before = proxy_rets[proxy_rets.index < first]
    out = pd.concat([before, ucits_rets]).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out, first


def returns_to_index(rets: pd.Series, base: float = 100.0) -> pd.Series:
    return base * (1 + rets.fillna(0)).cumprod()


def build_universe(cfg: dict, closes: dict[str, pd.Series] | None = None) -> tuple[pd.DataFrame, dict]:
    """Return a DataFrame of GBP price indices (one column per sleeve) plus splice info.

    `closes` can be supplied (tests, offline use); otherwise tickers are downloaded.
    """
    start = cfg["data"]["start"]
    cache = cfg["data"]["cache_dir"]
    insts = cfg["instruments"]

    def get(t: str) -> pd.Series:
        if closes is not None:
            return closes[t]
        return download_close(t, start, cache)

    fx = get(cfg["fx_ticker"])
    series, info = {}, {}
    for name, inst in insts.items():
        proxy = {t: get(t) for t in inst["proxy"]}
        p_rets = blend_returns(proxy, inst["proxy"])
        if inst.get("fx_to_gbp", False):
            p_rets = usd_to_gbp_returns(p_rets, fx)
        try:
            u = get(inst["ucits"]).pct_change()
        except Exception:  # UCITS line unavailable -> proxy only
            u = None
        rets, first = splice(p_rets, u)
        series[name] = rets
        info[name] = {"ucits": inst["ucits"], "ucits_from": None if first is None else str(first.date())}
    rets = pd.concat(series, axis=1).dropna()
    prices = rets.apply(returns_to_index)
    return prices, info


def synthetic_universe(names: list[str], start="2004-01-01", end="2025-12-31", seed=0) -> pd.DataFrame:
    """Random-walk prices for tests and offline demos. Not market data."""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range(start, end)
    cols = {}
    for i, n in enumerate(names):
        drift = 0.0002 + 0.0001 * i
        vol = 0.008 + 0.002 * i
        cols[n] = returns_to_index(pd.Series(rng.normal(drift, vol, len(idx)), index=idx))
    return pd.DataFrame(cols)
