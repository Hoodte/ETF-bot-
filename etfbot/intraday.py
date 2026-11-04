"""Intraday strategy lab on hourly bars (long AND short).

Data: Yahoo hourly bars, about the last 730 days (Yahoo's limit). That is short: treat any
result as a first screen, not proof. Longer, cleaner 5-minute data lives in backtest-bot.

Rules, same discipline as the daily work:
- Signal on bar t's close, position held from bar t+1 (no look-ahead).
- Positions are -1 (short), 0 (flat) or +1 (long).
- Cost = spread_bps x |change in position| on every trade.
- First 60% of bars = in-sample, last 40% = out-of-sample (judged).
- Checks: OOS positive, survives 2x costs, stable to +/-20% on the main parameter.
- Deflated Sharpe corrected for every market x strategy combination tried.
"""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pandas as pd

from . import discover

MARKETS = {  # name: (yahoo ticker, cost bps per side, session timezone, session start hour, end hour)
    "EURUSD": ("EURUSD=X", 1.0, "Europe/London", 8, 17),
    "GBPUSD": ("GBPUSD=X", 1.5, "Europe/London", 8, 17),
    "GOLD": ("GC=F", 2.0, "America/New_York", 9, 16),
    "NASDAQ100": ("NQ=F", 1.5, "America/New_York", 9, 16),
    "SP500": ("ES=F", 1.5, "America/New_York", 9, 16),
    "DAX": ("^GDAXI", 2.0, "Europe/Berlin", 9, 17),
    "BITCOIN": ("BTC-USD", 8.0, "Europe/London", 8, 20),
}

PARAMS = {  # frozen before testing; main parameter first
    "donchian": {"lookback": 20},
    "ema_cross": {"slow": 48, "fast": 12},
    "rsi2_both": {"entry": 10.0, "trend": 200, "exit_sma": 5},
    "bollinger_fade": {"lookback": 20, "z_in": 2.0, "z_out": 0.5},
    "orb": {"bars": 1},
    "session_momentum": {"split_bars": 3},
    "overnight": {},
}


def load(name: str, cache_dir="data") -> pd.DataFrame:
    import yfinance as yf

    t = MARKETS[name][0]
    path = Path(cache_dir) / f"intraday_{t.replace('=', '_').replace('^', '')}.csv"
    if path.exists() and pd.Timestamp(path.stat().st_mtime, unit="s").date() == pd.Timestamp.now().date():
        df = pd.read_csv(path, index_col=0)
        df.index = pd.to_datetime(df.index, utc=True)
        return df
    df = yf.download(t, period="730d", interval="1h", progress=False, auto_adjust=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close"]].dropna()
    df.index = pd.to_datetime(df.index, utc=True)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path)
    return df


def _hold(entry_long, entry_short, exit_long, exit_short) -> pd.Series:
    pos, out = 0, []
    for el, es, xl, xs in zip(entry_long, entry_short, exit_long, exit_short):
        if pos == 1 and xl:
            pos = 0
        elif pos == -1 and xs:
            pos = 0
        if pos == 0:
            pos = 1 if el else (-1 if es else 0)
        out.append(pos)
    return pd.Series(out, index=entry_long.index, dtype=float)


def _session(df: pd.DataFrame, mkt: str):
    tz, h0, h1 = MARKETS[mkt][2], MARKETS[mkt][3], MARKETS[mkt][4]
    local = df.index.tz_convert(tz)
    day = pd.Series(local.date, index=df.index)
    hour = pd.Series(local.hour, index=df.index)
    in_sess = (hour >= h0) & (hour < h1)
    return day, hour, in_sess


def positions(df: pd.DataFrame, mkt: str, name: str, p: dict) -> pd.Series:
    c = df["Close"]
    if name == "donchian":
        hi = c.shift(1).rolling(p["lookback"]).max()
        lo = c.shift(1).rolling(p["lookback"]).min()
        return _hold(c > hi, c < lo, c < lo, c > hi)
    if name == "ema_cross":
        f, s = c.ewm(span=p["fast"]).mean(), c.ewm(span=p["slow"]).mean()
        return np.sign(f - s).where(c.index >= c.index[p["slow"]], 0.0)
    if name == "rsi2_both":
        d = c.diff()
        up = d.clip(lower=0).ewm(alpha=0.5, adjust=False).mean()
        dn = (-d.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
        rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
        tr = c.rolling(p["trend"]).mean()
        ex = c.rolling(p["exit_sma"]).mean()
        return _hold((rsi < p["entry"]) & (c > tr), (rsi > 100 - p["entry"]) & (c < tr), c > ex, c < ex)
    if name == "bollinger_fade":
        m, sd = c.rolling(p["lookback"]).mean(), c.rolling(p["lookback"]).std()
        z = (c - m) / sd
        return _hold(z < -p["z_in"], z > p["z_in"], z > -p["z_out"], z < p["z_out"])
    day, hour, in_sess = _session(df, mkt)
    if name == "orb":
        first = in_sess & ~in_sess.groupby(day).shift(1, fill_value=False).astype(bool)
        n = p["bars"]
        rank = in_sess.astype(int).groupby(day).cumsum()
        rng_hi = df["High"].where(in_sess & (rank <= n)).groupby(day).transform("max")
        rng_lo = df["Low"].where(in_sess & (rank <= n)).groupby(day).transform("min")
        after = in_sess & (rank > n)
        last = in_sess & ~in_sess.groupby(day).shift(-1, fill_value=False).astype(bool)
        pos, out, cur_day, traded = 0, [], None, False
        for t in df.index:
            if day[t] != cur_day:
                cur_day, pos, traded = day[t], 0, False
            if after[t] and not traded and pos == 0:
                if c[t] > rng_hi[t]:
                    pos, traded = 1, True
                elif c[t] < rng_lo[t]:
                    pos, traded = -1, True
            if last[t] or not in_sess[t]:
                pos = 0
            out.append(pos)
        _ = first
        return pd.Series(out, index=df.index, dtype=float)
    if name == "session_momentum":
        rank = in_sess.astype(int).groupby(day).cumsum()
        open_px = c.where(in_sess & (rank == 1)).groupby(day).transform("first")
        k = p["split_bars"]
        sig = np.sign(c / open_px - 1).where(in_sess & (rank == k))
        last = in_sess & ~in_sess.groupby(day).shift(-1, fill_value=False).astype(bool)
        pos = sig.groupby(day).ffill().where(in_sess & (rank >= k) & ~last, 0.0)
        return pos.fillna(0.0)
    if name == "overnight":
        last = in_sess & ~in_sess.groupby(day).shift(-1, fill_value=False).astype(bool)
        pos = pd.Series(np.where(~in_sess | last, 1.0, 0.0), index=df.index)
        return pos
    raise ValueError(name)


def returns(df: pd.DataFrame, pos: pd.Series, cost_bps: float) -> pd.Series:
    r = df["Close"].pct_change().fillna(0.0)
    held = pos.shift(1).fillna(0.0)                     # trade on the next bar
    cost = held.diff().abs().fillna(held.abs()) * cost_bps / 1e4
    return held * r - cost


def _metrics(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 50:
        return {}
    years = (r.index[-1] - r.index[0]).days / 365.25
    eq = (1 + r).cumprod()
    bars_per_year = len(r) / years if years > 0 else np.nan
    sd = r.std()
    return {"cagr": float(eq.iloc[-1] ** (1 / years) - 1) if years > 0 else np.nan,
            "sharpe": float(r.mean() / sd * np.sqrt(bars_per_year)) if sd > 0 else 0.0,
            "max_drawdown": float((eq / eq.cummax() - 1).min()), "years": round(years, 2)}


def run(names=None, oos_frac=0.4, min_dsr=0.95) -> dict:
    rows, oos_rets = [], {}
    for mkt in names or MARKETS:
        df = load(mkt)
        cost = MARKETS[mkt][1]
        split = df.index[int(len(df) * (1 - oos_frac))]
        bh = df["Close"].pct_change().fillna(0.0)
        bh_o = _metrics(bh[bh.index >= split])
        for name, p in PARAMS.items():
            if name == "overnight" and mkt in ("EURUSD", "GBPUSD", "BITCOIN"):
                continue
            pos = positions(df, mkt, name, p)
            r = returns(df, pos, cost)
            o, i = _metrics(r[r.index >= split]), _metrics(r[r.index < split])
            r2 = returns(df, pos, cost * 2)
            o2 = _metrics(r2[r2.index >= split])
            nudges = []
            if p:
                k = next(iter(p))
                for f in (0.8, 1.2):
                    q = copy.deepcopy(p)
                    q[k] = max(1, int(round(p[k] * f))) if isinstance(p[k], int) else p[k] * f
                    nudges.append(_metrics(returns(df, positions(df, mkt, name, q), cost)[r.index >= split]).get("cagr", -1))
            trades_per_day = float(pos.diff().abs().gt(0).sum() / max(1, (df.index[-1] - df.index[0]).days))
            checks = {"oos_positive": o.get("cagr", -1) > 0, "survives_2x_costs": o2.get("cagr", -1) > 0,
                      "stable_to_param_nudge": all(n > 0 for n in nudges) if nudges else True}
            oos_rets[(mkt, name)] = r[r.index >= split]
            rows.append({"market": mkt, "strategy": name, "params": p, "in_sample": i, "out_of_sample": o,
                         "oos_costs_x2": o2, "buy_hold_oos": bh_o, "trades_per_day": round(trades_per_day, 2),
                         "checks": checks, "oos_from": str(split.date())})
    srs = [discover._sr_stats(x)[0] for x in oos_rets.values()]
    sr0 = discover.expected_max_sharpe(float(np.var(srs, ddof=1)), len(srs))
    for r in rows:
        r["deflated_sharpe"] = discover.deflated_sharpe(oos_rets[(r["market"], r["strategy"])], sr0)
        r["survivor"] = bool(all(r["checks"].values()) and r["deflated_sharpe"] == r["deflated_sharpe"]
                             and r["deflated_sharpe"] >= min_dsr)
    rows.sort(key=lambda x: x["deflated_sharpe"] if x["deflated_sharpe"] == x["deflated_sharpe"] else -1, reverse=True)
    return {"trials": len(rows), "rows": rows, "survivors": [f"{r['market']} {r['strategy']}" for r in rows if r["survivor"]]}


def to_markdown(res: dict) -> str:
    def pct(x):
        return "-" if x is None or x != x else f"{x:.1%}"

    lines = ["# Intraday strategy lab (hourly bars, long and short)", "",
             f"{res['trials']} market x strategy combinations on Yahoo hourly data (about the last 2.5 years). "
             "Out-of-sample = the last 40% of bars. Deflated Sharpe corrected for all combinations. "
             "Short history: a first screen, not proof.", "",
             f"**Survivors: {', '.join(res['survivors']) or 'none'}**", "",
             "| Market | Strategy | OOS return/yr | OOS Sharpe | OOS max DD | Same with 2x costs | Market itself (OOS) | Trades/day | Deflated Sharpe | Failed checks |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in res["rows"]:
        o, o2, b = r["out_of_sample"], r["oos_costs_x2"], r["buy_hold_oos"]
        failed = [k for k, v in r["checks"].items() if not v]
        lines.append(f"| {r['market']} | {r['strategy']} | {pct(o.get('cagr'))} | {o.get('sharpe', 0):.2f} | "
                     f"{pct(o.get('max_drawdown'))} | {pct(o2.get('cagr'))} | {pct(b.get('cagr'))} | {r['trades_per_day']} | "
                     f"{pct(r['deflated_sharpe'])} | {', '.join(failed) or '-'} |")
    lines += ["", "Costs per side: " + ", ".join(f"{k} {v[1]} bps" for k, v in MARKETS.items()) + "."]
    return "\n".join(lines) + "\n"
