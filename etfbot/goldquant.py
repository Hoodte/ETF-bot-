"""Gold quant strategy search: 14 pre-registered strategies (see
results/2026-11-05/gold_quant_preregistration.md). Hourly XAUUSD positions in {-1, 0, +1}."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import data, discover

IS_END, OOS_START = "2021-12-31", "2022-01-01"
COST_BPS = 3.0


# ---------------------------------------------------------------- data
def load_gold_h1(path: str) -> pd.DataFrame:
    raw = pd.read_csv(path)
    df = pd.DataFrame({"Open": raw["open"].values, "High": raw["high"].values, "Low": raw["low"].values,
                       "Close": raw["close"].values}, index=pd.to_datetime(raw["ts"], unit="s", utc=True))
    return df[~df.index.duplicated()].sort_index()


def load_daily(cache="data") -> dict[str, pd.Series]:
    t = {"DXY": "DX-Y.NYB", "US10Y": "^TNX", "TIPS": "TIP", "VIX": "^VIX", "MINERS": "GDX", "GOLD_D": "GC=F"}
    return {k: data.download_close(v, "2010-01-01", cache) for k, v in t.items()}


def load_cot(path="/tmp/cot.json") -> pd.Series:
    d = pd.DataFrame(json.load(open(path)))
    d["date"] = pd.to_datetime(d["report_date_as_yyyy_mm_dd"])
    for c in ("m_money_positions_long_all", "m_money_positions_short_all", "open_interest_all"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.sort_values("date").drop_duplicates("date")
    net = (d["m_money_positions_long_all"] - d["m_money_positions_short_all"]) / d["open_interest_all"]
    return pd.Series(net.values, index=d["date"].values, name="mm_net_pct_oi")


def to_hourly(sig: pd.Series, idx: pd.DatetimeIndex, lag_days: int) -> pd.Series:
    """Daily/weekly signal dated d -> active from 00:00 UTC on d + lag_days (no look-ahead)."""
    s = sig.dropna().astype(float).copy()
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize().tz_localize("UTC") + pd.Timedelta(days=lag_days)
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s.reindex(s.index.union(idx)).ffill().reindex(idx).fillna(0.0)


# ---------------------------------------------------------------- strategies
def build(name: str, h1: pd.DataFrame, d: dict, cot: pd.Series, f: float = 1.0) -> pd.Series:
    """f scales the main parameter (0.8 / 1.0 / 1.2) for the robustness nudge."""
    idx, c = h1.index, h1["Close"]
    n = lambda x: max(1, int(round(x * f)))  # noqa: E731
    if name == "dollar_regime":
        x = d["DXY"]; return to_hourly((x < x.rolling(n(50)).mean()).astype(float), idx, 1)
    if name == "real_yield_momentum":
        return to_hourly((d["TIPS"].pct_change(n(20)) > 0).astype(float), idx, 1)
    if name == "nominal_yield_momentum":
        return to_hourly((d["US10Y"].diff(n(20)) < 0).astype(float), idx, 1)
    if name == "miners_lead":
        k = n(5); spread = d["MINERS"].pct_change(k) - d["GOLD_D"].reindex(d["MINERS"].index).pct_change(k)
        return to_hourly(np.sign(spread), idx, 1)
    if name == "fear_spike":
        v = d["VIX"]; flag = (v > 1.2 * v.rolling(n(60)).mean()).astype(float)
        return to_hourly(flag.rolling(10, min_periods=1).max(), idx, 1)
    if name == "macro_composite_vol10":
        # long-term own-money candidate (variant V1, 2026-11-05): composite x (10% / 20-day realised vol), cap 1.5x
        base = build("macro_composite", h1, d, cot, f)
        gr = c.pct_change()
        dv = gr.groupby(gr.index.date).apply(lambda z: (1 + z).prod() - 1).rolling(20).std() * np.sqrt(252)
        dv.index = pd.to_datetime(dv.index)
        sc = to_hourly((0.10 / dv).clip(upper=1.5).rename("s"), idx, 1).replace(0, np.nan).ffill().fillna(1.0)
        return base * sc
    if name in ("cot_contrarian", "cot_momentum", "macro_composite"):
        w = n(156)
        pct = cot.rolling(w, min_periods=52).apply(lambda a: (a[:-1] < a[-1]).mean(), raw=True)
        if name == "cot_contrarian":
            sig = pd.Series(np.where(pct < 0.30, 1.0, np.where(pct > 0.90, -1.0, 0.0)), index=cot.index).where(pct.notna(), 0.0)
            return to_hourly(sig, idx, 6)
        if name == "cot_momentum":
            return to_hourly((cot.diff(max(1, int(round(4 * f)))) > 0).astype(float), idx, 6)
        x = d["DXY"]
        a = to_hourly((x < x.rolling(n(50)).mean()).astype(float), idx, 1)
        b = to_hourly((d["TIPS"].pct_change(20) > 0).astype(float), idx, 1)
        cc = to_hourly((pct < 0.70).astype(float).where(pct.notna(), 0.0), idx, 6)
        return ((a + b + cc) >= 2).astype(float)
    hour = pd.Series(idx.hour, index=idx)
    r = c.pct_change()
    is_start = f"{2016 + (1 if f > 1.0 else 0)}-01-01" if f != 1.0 else "2016-01-01"
    if name == "hour_of_day":
        ris = r[is_start:IS_END]
        g = ris.groupby(ris.index.hour)
        t = g.mean() / (g.std() / np.sqrt(g.count()))
        thr = 2.0 * f
        mapping = {h: (1.0 if t.get(h, 0) > thr else (-1.0 if t.get(h, 0) < -thr else 0.0)) for h in range(24)}
        held = hour.map(mapping)
        return held.shift(-1).fillna(0.0)            # target at t = position held during bar t+1
    if name == "asia_session_long":
        end = 7 + (0 if f == 1.0 else (-1 if f < 1 else 1))
        held = ((hour >= 23) | (hour < end)).astype(float)
        return held.shift(-1).fillna(0.0)
    if name == "us_session_short":
        start = 13 + (0 if f == 1.0 else (-1 if f < 1 else 1))
        held = -((hour >= start) & (hour < 20)).astype(float)
        return held.shift(-1).fillna(0.0)
    if name in ("month_of_year", "day_of_week"):
        daily = c.resample("D").last().dropna().pct_change()[is_start:IS_END]
        key = daily.index.month if name == "month_of_year" else daily.index.dayofweek
        good = daily.groupby(key).mean() > 0
        k = idx.month if name == "month_of_year" else idx.dayofweek
        held = pd.Series(np.array([float(good.get(x, False)) for x in k]), index=idx)
        return held.shift(-1).fillna(0.0)
    if name == "squeeze_breakout":
        tr = pd.concat([h1["High"] - h1["Low"], (h1["High"] - c.shift()).abs(), (h1["Low"] - c.shift()).abs()], axis=1).max(axis=1)
        atr = tr.rolling(20).mean()
        q = atr.rolling(500).rank(pct=True)
        hi, lo = h1["High"].rolling(24).max().shift(1), h1["Low"].rolling(24).min().shift(1)
        thr = 0.10 * f
        sq = (q < thr).to_numpy(); up = (c > hi).to_numpy(); dn = (c < lo).to_numpy()
        pos, left, out = 0.0, 0, np.zeros(len(c))
        for i in range(len(c)):
            if left > 0:
                left -= 1
                if left == 0:
                    pos = 0.0
            if pos == 0.0 and sq[i] and (up[i] or dn[i]):
                pos, left = (1.0 if up[i] else -1.0), 24
            out[i] = pos
        return pd.Series(out, index=idx)
    raise ValueError(name)


NAMES = ["dollar_regime", "real_yield_momentum", "nominal_yield_momentum", "miners_lead", "fear_spike",
         "cot_contrarian", "cot_momentum", "macro_composite", "hour_of_day", "asia_session_long",
         "us_session_short", "month_of_year", "day_of_week", "squeeze_breakout"]


# ---------------------------------------------------------------- evaluation
def returns(h1: pd.DataFrame, target: pd.Series, cost_bps: float) -> pd.Series:
    r = h1["Close"].pct_change().fillna(0.0)
    held = target.shift(1).fillna(0.0)
    return held * r - held.diff().abs().fillna(held.abs()) * cost_bps / 1e4


def metrics(r: pd.Series) -> dict:
    r = r.dropna()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    eq = (1 + r).cumprod()
    sd = r.std()
    return {"cagr": float(eq.iloc[-1] ** (1 / yrs) - 1), "sharpe": float(r.mean() / sd * np.sqrt(len(r) / yrs)) if sd > 0 else 0.0,
            "max_dd": float((eq / eq.cummax() - 1).min()), "exposure": float((r != 0).mean())}


def run(h1, d, cot, min_dsr=0.95) -> dict:
    rows, oos_r = [], {}
    bh = h1["Close"].pct_change().fillna(0.0)
    for name in NAMES:
        tgt = build(name, h1, d, cot)
        r = returns(h1, tgt, COST_BPS)
        r2 = returns(h1, tgt, 2 * COST_BPS)
        nudges = [metrics(returns(h1, build(name, h1, d, cot, f), COST_BPS)[OOS_START:])["cagr"] for f in (0.8, 1.2)]
        o, i = metrics(r[OOS_START:]), metrics(r[:IS_END])
        oos_r[name] = r[OOS_START:]
        yearly = (1 + r).groupby(r.index.year).prod() - 1
        rows.append({"strategy": name, "in_sample": i, "out_of_sample": o, "oos_2x_costs": metrics(r2[OOS_START:]),
                     "nudges_oos_cagr": nudges, "trades_per_year": float(tgt.diff().abs().gt(0).sum() / 10.8),
                     "yearly": {int(k): float(v) for k, v in yearly.items()},
                     "checks": {"oos_positive": o["cagr"] > 0, "survives_2x_costs": metrics(r2[OOS_START:])["cagr"] > 0,
                                "stable_to_nudge": all(x > 0 for x in nudges)}})
    srs = [discover._sr_stats(x)[0] for x in oos_r.values()]
    sr0 = discover.expected_max_sharpe(float(np.var(srs, ddof=1)), len(srs))
    for row in rows:
        row["deflated_sharpe"] = discover.deflated_sharpe(oos_r[row["strategy"]], sr0)
        row["survivor"] = bool(all(row["checks"].values()) and row["deflated_sharpe"] >= min_dsr)
    rows.sort(key=lambda x: x["deflated_sharpe"], reverse=True)
    return {"rows": rows, "buy_hold_is": metrics(bh[:IS_END]), "buy_hold_oos": metrics(bh[OOS_START:]),
            "survivors": [x["strategy"] for x in rows if x["survivor"]], "_oos": oos_r}


def to_markdown(res: dict) -> str:
    p = lambda x: f"{x:.1%}"  # noqa: E731
    b, bi = res["buy_hold_oos"], res["buy_hold_is"]
    L = ["# Gold quant strategy search: results", "",
         "14 strategies pre-registered in `gold_quant_preregistration.md`. XAUUSD hourly, Dukascopy, 2016–2026. "
         "In-sample 2016–2021, out-of-sample 2022–Oct 2026. Costs 3 bps per side.", "",
         f"Holding gold: in-sample {p(bi['cagr'])}/yr (max drop {p(bi['max_dd'])}), out-of-sample {p(b['cagr'])}/yr "
         f"(max drop {p(b['max_dd'])}, Sharpe {b['sharpe']:.2f}).", "",
         f"**Survivors: {', '.join(res['survivors']) or 'none'}**", "",
         "| Strategy | In-sample /yr | OOS /yr | OOS Sharpe | OOS max drop | OOS at 2× costs | Nudged ±20% (OOS) | Time in market | Trades/yr | Deflated Sharpe | Failed |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in res["rows"]:
        i, o, o2 = r["in_sample"], r["out_of_sample"], r["oos_2x_costs"]
        L.append(f"| {r['strategy']} | {p(i['cagr'])} | {p(o['cagr'])} | {o['sharpe']:.2f} | {p(o['max_dd'])} | {p(o2['cagr'])} | "
                 f"{p(r['nudges_oos_cagr'][0])} / {p(r['nudges_oos_cagr'][1])} | {p(o['exposure'])} | {r['trades_per_year']:.0f} | "
                 f"{p(r['deflated_sharpe'])} | {', '.join(k for k, v in r['checks'].items() if not v) or '-'} |")
    return "\n".join(L) + "\n"
