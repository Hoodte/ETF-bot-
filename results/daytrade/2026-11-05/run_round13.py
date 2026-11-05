import numpy as np, pandas as pd, warnings
warnings.filterwarnings("ignore")
H = "data/histdata"
def m1(s): return pd.read_pickle(f"{H}/{s}_1m.pkl")
def daily(s):
    b = m1(s); d = b.resample("1D").agg({"Open": "first", "Close": "last"}).dropna(); return d
BD = pd.bdate_range("2016-01-01", "2026-10-30", tz="UTC")
out = {}
# 1) oil inventory surprise on Brent
tv = pd.read_pickle("data/calendar/tv_calendar.pkl")
ev = tv[(tv.country == "US") & (tv.title == "EIA Crude Oil Stocks Change") & tv.actual.notna() & tv.forecast.notna()].copy()
ev["t"] = pd.to_datetime(ev.date, utc=True); ev = ev.sort_values("t")
ev["s"] = ev.actual.astype(float) - ev.forecast.astype(float)
ev["z"] = ev.s / ev.s.expanding().std().shift(1).where(ev.s.expanding().count().shift(1) >= 10)
ev = ev.dropna(subset=["z"])
b = m1("BCOUSD"); t = b.index.as_unit("ns").asi8; o = b.Open.to_numpy(); c = b.Close.to_numpy()
rows = []
for _, e in ev[ev.z.abs() > 0.5].iterrows():
    t0 = (e.t + pd.Timedelta(minutes=5)).value; i = np.searchsorted(t, t0)
    if i >= len(t) or t[i] - t0 > 120e9: continue
    j = np.searchsorted(t, t0 + 59 * 60e9, side="right") - 1
    if j <= i: continue
    d = -np.sign(e.z); rows.append((e.t.floor("D"), d * (c[j] / o[i] - 1) - 2 * 3e-4))
oil = pd.DataFrame(rows, columns=["d", "r"]).groupby("d").r.sum()
out["1 Oil inventory surprise (Brent)"] = (oil.reindex(BD, fill_value=0), len(rows))
# 2) pre-FOMC drift on S&P 500
fo = tv[(tv.country == "US") & (tv.title == "Interest Rate")].copy()
fo["t"] = pd.to_datetime(fo.date, utc=True).dt.tz_convert("America/New_York")
fo = fo[fo.t.dt.strftime("%H:%M") == "14:00"]
s = m1("SPXUSD"); s.index = s.index.tz_convert("America/New_York"); st = s.index.as_unit("ns").asi8; so = s.Open.to_numpy(); sc = s.Close.to_numpy()
rows = []
for tt in fo.t:
    prev = tt - pd.offsets.BDay(1)
    t0 = prev.value; t1 = (tt - pd.Timedelta(minutes=6)).value
    i = np.searchsorted(st, t0); j = np.searchsorted(st, t1, side="right") - 1
    if i >= len(st) or j <= i or st[i] - t0 > 600e9: continue
    rows.append((tt.tz_convert("UTC").floor("D"), sc[j] / so[i] - 1 - 2e-4 - 0.05 / 252))
fomc = pd.DataFrame(rows, columns=["d", "r"]).groupby("d").r.sum()
out["2 Pre-Fed drift (S&P)"] = (fomc.reindex(BD, fill_value=0), len(rows))
# 3) RSI(2) dip-buying, S&P and DAX
def rsi2(x):
    dd = x.diff(); up = dd.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-dd.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))
legs, ntr = [], 0
for sym in ("SPXUSD", "GRXEUR"):
    d = daily(sym); cl, op = d.Close, d.Open
    sig = (cl > cl.rolling(200).mean()) & (rsi2(cl) < 5); sma5 = cl.rolling(5).mean()
    r = pd.Series(0.0, index=d.index); held = False; age = 0
    for k in range(1, len(d)):
        if held:
            r.iloc[k] = cl.iloc[k] / cl.iloc[k - 1] - 1 - 0.05 / 252; age += 1
            if cl.iloc[k] > sma5.iloc[k] or age >= 10: r.iloc[k] -= 1e-4; held = False
        elif sig.iloc[k - 1]:
            r.iloc[k] = cl.iloc[k] / op.iloc[k] - 1 - 1e-4 - 0.05 / 252; held = True; age = 1; ntr += 1
            if cl.iloc[k] > sma5.iloc[k]: r.iloc[k] -= 1e-4; held = False
    r.index = r.index.tz_convert("UTC") if r.index.tz else r.index.tz_localize("UTC"); legs.append(r.reindex(BD, fill_value=0))
out["3 Deep-dip buying (S&P + DAX)"] = (sum(legs) / 2, ntr)
# 4) carry with trend, AUDJPY + NZDJPY
legs, ntr = [], 0
for sym in ("AUDJPY", "NZDJPY"):
    cl = daily(sym).Close; on = (cl > cl.rolling(200).mean()).astype(float).shift(1).fillna(0)
    r = on * cl.pct_change().fillna(0) - on.diff().abs().fillna(0) * 1e-4 + on * 0.01 / 252
    ntr += int((on.diff() > 0).sum()); r.index = r.index.tz_convert("UTC") if r.index.tz else r.index.tz_localize("UTC")
    legs.append(r.reindex(BD, fill_value=0))
out["4 Carry with trend (AUDJPY + NZDJPY)"] = (sum(legs) / 2, ntr)
# 5) gold/silver ratio
xau, xag = daily("XAUUSD").Close, daily("XAGUSD").Close
df = pd.concat({"au": xau, "ag": xag}, axis=1).dropna(); ratio = df.au / df.ag
z = (ratio - ratio.rolling(120).mean()) / ratio.rolling(120).std()
pos = pd.Series(0.0, index=df.index); p = 0.0; ntr = 0
for k in range(len(df)):
    zk = z.iloc[k]
    if np.isnan(zk): pos.iloc[k] = 0; continue
    if p == 0 and zk > 2: p = 1.0; ntr += 1
    elif p == 0 and zk < -2: p = -1.0; ntr += 1
    elif p != 0 and abs(zk) < 0.5: p = 0.0
    pos.iloc[k] = p
ps = pos.shift(1).fillna(0)
r = ps * (df.ag.pct_change() - df.au.pct_change()).fillna(0) - ps.diff().abs().fillna(0) * 2 * 2e-4 - ps.abs() * 2 * 0.02 / 252
r.index = r.index.tz_convert("UTC") if r.index.tz else r.index.tz_localize("UTC")
out["5 Gold/silver ratio"] = (r.reindex(BD, fill_value=0), ntr)
sh = lambda x: x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0
P = {"2016-20": ("2016-01-01", "2020-12-31"), "2021-24": ("2021-01-01", "2024-12-31"), "2025-26": ("2025-01-01", "2026-10-30")}
keep = {}
for name, (x, n) in out.items():
    s_ = {k: sh(x[a:b]) for k, (a, b) in P.items()}
    k = s_["2016-20"] >= 0.3 and s_["2021-24"] > 0
    print(f"{name:40s} trades {n:5d} | Sharpe 2016-20 {s_['2016-20']:5.2f} | 2021-24 {s_['2021-24']:5.2f} | 2025-26 {s_['2025-26']:5.2f} | {'KEEP' if k else 'drop'}")
    if k: keep[name] = x / (x["2016-01-01":"2020-12-31"].std() * np.sqrt(252)) * 0.03     # 3% annual vol on the account
pd.DataFrame(keep).to_csv("results/daytrade/2026-11-05/round13_kept_daily.csv")
if len(keep) > 1:
    K = pd.DataFrame(keep); print("correlations between kept:\n", K["2016":].corr().round(2).to_string())
