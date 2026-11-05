import itertools, json, re
import numpy as np, pandas as pd
from etfbot.daytrade import evaluate as V
cal = pd.read_pickle("data/calendar/ff_fixed.pkl")
cal = cal[(cal.Impact == "High Impact Expected") & cal.Currency.isin(["USD", "CAD"]) & cal.t_utc.notna()].copy()
def num(x):
    if not isinstance(x, str): return np.nan
    m = re.match(r"^\s*(-?[\d.]+)\s*([KMBT%]?)", x.replace(",", ""))
    if not m: return np.nan
    v = float(m.group(1)); return v * {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}.get(m.group(2), 1)
cal["a"] = cal.Actual.map(num); cal["f"] = cal.Forecast.map(num)
cal = cal.dropna(subset=["a", "f"])
cal["good_sign"] = np.where(cal.Detail.fillna("").str.contains("'Actual' less than 'Forecast' is good"), -1, 1)
et = cal.t_utc.dt.tz_convert("America/New_York").dt.strftime("%H:%M")
cal["clock"] = et
mode_clock = cal[cal.t_utc < pd.Timestamp("2021-01-01", tz="UTC")].groupby(["Currency", "Event"]).clock.agg(lambda s: s.mode().iloc[0])
cal = cal.join(mode_clock.rename("usual"), on=["Currency", "Event"])
cal = cal[cal.clock == cal.usual].sort_values("t_utc")
cal["surp"] = cal.a - cal.f
cal["z"] = cal.groupby(["Currency", "Event"]).surp.transform(lambda s: s / s.expanding().std().shift(1).where(s.expanding().count().shift(1) >= 10)) * cal.good_sign
cal = cal.dropna(subset=["z"])
cal = cal[cal.t_utc >= pd.Timestamp("2016-01-01", tz="UTC")]
print("usable events:", len(cal), cal.Currency.value_counts().to_dict())
INST = {"EURUSD": ("USD", -1, 1.2), "GBPUSD": ("USD", -1, 1.6), "AUDUSD": ("USD", -1, 1.6), "USDJPY": ("USD", 1, 1.4),
        "USDCAD": (None, 1, 1.6), "XAUUSD": ("USD", -1, 2.0)}    # orientation: +1 if USD (or CAD-quote) is base
px = {}
for s in INST:
    m = pd.read_pickle(f"data/histdata/{s}_1m.pkl")
    dv = m.Close.resample("1D").last().dropna().pct_change().rolling(20).std().shift(1)
    px[s] = (m.index.as_unit("ns").asi8, m.Open.to_numpy(), m.Close.to_numpy(), dv)
def trades(delay, hold, th, mode, cmult=1.0):
    rows = []
    for _, e in cal[cal.z.abs() > th].iterrows():
        for s, (cur, orient, cost) in INST.items():
            if e.Currency == "CAD":
                if s != "USDCAD": continue
                d = -1 * np.sign(e.z)            # CAD good -> USDCAD down
            else:
                if s == "USDCAD": d = np.sign(e.z)
                else: d = orient * np.sign(e.z)
            if mode == "fade": d = -d
            t, o, c, dv = px[s]
            t0 = (e.t_utc + pd.Timedelta(minutes=delay)).value; t1 = t0 + (hold - 1) * 60_000_000_000
            i = np.searchsorted(t, t0)
            if i >= len(t) or t[i] - t0 > 2 * 60e9: continue
            j = np.searchsorted(t, t1, side="right") - 1
            if j <= i: continue
            vol = dv.asof(e.t_utc.tz_convert("UTC").floor("D"))
            if not vol or np.isnan(vol): continue
            r = d * (c[j] / o[i] - 1) - 2 * cost * cmult / 1e4
            rows.append((e.t_utc, s, r / vol, r))
    return pd.DataFrame(rows, columns=["t", "inst", "pnl", "raw"])
def sh(tr, a, b):
    x = tr[(tr.t >= pd.Timestamp(a, tz="UTC")) & (tr.t <= pd.Timestamp(b, tz="UTC") + pd.Timedelta(days=1))]
    if len(x) < 20: return np.nan, 0, x
    days = pd.date_range(a, b, freq="B", tz="UTC")
    dp = x.groupby(x.t.dt.floor("D")).pnl.sum().reindex(days, fill_value=0)
    return dp.mean() / dp.std() * np.sqrt(252), len(x) / len(days), x
grid = list(itertools.product([1, 5, 15], [15, 60, 240], [0.5, 1.0, 1.5], ["follow", "fade"]))
res = []
for g in grid:
    tr = trades(*g); s, tpd, _ = sh(tr, "2016-01-01", "2020-12-31"); res.append((s, tpd, g))
res.sort(key=lambda r: -np.nan_to_num(r[0], nan=-9))
print("selection 2016-20 top 8:")
for s, tpd, g in res[:8]: print(f"  {g}: Sharpe {s:.2f}, {tpd:.2f} trades/day")
best = res[0][2]
tr = trades(*best); tr2 = trades(*best, cmult=2.0)
v, vtpd, vx = sh(tr, "2021-01-01", "2024-12-31"); v2, _, _ = sh(tr2, "2021-01-01", "2024-12-31")
h, htpd, hx = sh(tr, "2025-01-01", "2025-04-07")
yr = {y: round(sh(tr, f"{y}-01-01", f"{y}-12-31")[0], 2) for y in range(2016, 2025)}
print(f"FROZEN {best}: validation 2021-24 Sharpe {v:.2f} (2x cost {v2:.2f}), {vtpd:.2f} trades/day, win rate {(vx.raw>0).mean():.0%}, avg {vx.raw.mean()*1e4:.2f} bps/trade")
print(f"  by year: {yr}")
print(f"  HOLDOUT 2025-01..04: Sharpe {h:.2f}, {len(hx)} trades")
print("  validation by instrument:", vx.groupby("inst").raw.agg(lambda r: round(r.mean() * 1e4, 2)).to_dict())
json.dump({"best": best, "sel": res[0][0], "val": v, "val2x": v2, "tpd": vtpd, "holdout": h, "years": yr}, open("results/daytrade/2026-11-05/round10_results.json", "w"), indent=1, default=str)
