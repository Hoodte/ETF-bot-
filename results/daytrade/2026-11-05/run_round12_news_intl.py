import numpy as np, pandas as pd
tv = pd.read_pickle("data/calendar/tv_calendar_intl.pkl")
tv = tv[(tv.importance == 1) & tv.actual.notna() & tv.forecast.notna()].copy()
tv = tv[~tv.title.str.contains("Crude|Gasoline|Natural Gas|EIA", case=False)]
tv["t_utc"] = pd.to_datetime(tv.date, utc=True)
tv["good_sign"] = np.where(tv.title.str.contains("Unemployment Rate|Jobless Claims|Claimant Count", case=False), -1, 1)
tv = tv.sort_values("t_utc")
tv["surp"] = tv.actual.astype(float) - tv.forecast.astype(float)
g = tv.groupby(["country", "title"]).surp
tv["z"] = (tv.surp / g.transform(lambda s: s.expanding().std().shift(1).where(s.expanding().count().shift(1) >= 10))) * tv.good_sign
cal = tv.dropna(subset=["z"]); cal = cal[cal.t_utc >= pd.Timestamp("2016-01-01", tz="UTC")]
MAP = {"GB": ("GBPUSD", 1, 1.6), "EU": ("EURUSD", 1, 1.2), "DE": ("EURUSD", 1, 1.2), "AU": ("AUDUSD", 1, 1.6), "JP": ("USDJPY", -1, 1.4)}
print("events:", cal.country.value_counts().to_dict())
px = {}
for s in {v[0] for v in MAP.values()}:
    m = pd.read_pickle(f"data/histdata/{s}_1m.pkl")
    dv = m.Close.resample("1D").last().dropna().pct_change().rolling(20).std().shift(1)
    px[s] = (m.index.as_unit("ns").asi8, m.Open.to_numpy(), m.Close.to_numpy(), dv)
def trades(cmult=1.0):
    rows = []
    for _, e in cal[cal.z.abs() > 0.5].iterrows():
        s, orient, cost = MAP[e.country]; d = orient * np.sign(e.z)
        t, o, c, dv = px[s]
        t0 = (e.t_utc + pd.Timedelta(minutes=5)).value; t1 = t0 + 59 * 60_000_000_000
        i = np.searchsorted(t, t0)
        if i >= len(t) or t[i] - t0 > 120e9: continue
        j = np.searchsorted(t, t1, side="right") - 1
        if j <= i: continue
        vol = dv.asof(e.t_utc.floor("D"))
        if not vol or np.isnan(vol): continue
        r = d * (c[j] / o[i] - 1) - 2 * cost * cmult / 1e4
        rows.append((e.t_utc, s, e.country, r / vol, r))
    return pd.DataFrame(rows, columns=["t", "inst", "country", "pnl", "raw"])
def sh(x, a, b):
    x = x[(x.t >= pd.Timestamp(a, tz="UTC")) & (x.t <= pd.Timestamp(b, tz="UTC") + pd.Timedelta(days=1))]
    days = pd.date_range(a, b, freq="B", tz="UTC")
    dp = x.groupby(x.t.dt.floor("D")).pnl.sum().reindex(days, fill_value=0)
    return dp.mean() / dp.std() * np.sqrt(252), len(x) / len(days), x.raw.mean() * 1e4
tr, tr2 = trades(), trades(2.0)
for a, b in (("2016-01-01", "2020-12-31"), ("2021-01-01", "2024-12-31"), ("2025-01-01", "2026-10-30")):
    s, tpd, bps = sh(tr, a, b); s2, _, _ = sh(tr2, a, b)
    per = {c: round(sh(tr[tr.country == c], a, b)[0], 2) for c in MAP}
    print(f"{a[:4]}-{b[:4]}: Sharpe {s:.2f} (2x cost {s2:.2f}), {tpd:.2f} trades/day, {bps:.2f} bps/trade | by country {per}")
tr.to_csv("results/daytrade/2026-11-05/round12_news_intl_trades.csv", index=False)
