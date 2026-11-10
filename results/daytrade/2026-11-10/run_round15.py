import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
H = "data/histdata"; BD = pd.bdate_range("2016-01-01", "2026-10-30", tz="UTC")
def m1(s): b = pd.read_pickle(f"{H}/{s}_1m.pkl"); return b[~b.index.duplicated()].sort_index()
def sh(r, a, b): x = r[a:b]; return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0
ev = pd.read_csv("deploy/pineconnector/news_events.csv"); ev["t"] = pd.to_datetime(ev.time_utc, format="%Y.%m.%d %H:%M", utc=True)
ev = ev[ev.z.abs() > 0.5]; ev["s"] = np.sign(ev.z)
k = ev.groupby(["t", "currency"]).s.sum().unstack(fill_value=0)
for c in ("USD", "CAD"):
    if c not in k: k[c] = 0
print("# Part 1: news on other markets\n| Market | Releases traded | Direction (picked on 2016-20) | 2016-20 | 2021-24 | 2025-26 | Verdict |\n|---|---|---|---|---|---|---|")
for sym, cost, sigf in (("SPXUSD", 1e-4, lambda r: r.USD), ("NSXUSD", 1e-4, lambda r: r.USD), ("GRXEUR", 1e-4, lambda r: r.USD),
                        ("BCOUSD", 3e-4, lambda r: r.USD), ("BCOUSD", 3e-4, lambda r: r.USD + r.CAD)):
    b = m1(sym); t = b.index.as_unit("ns").asi8; o, c = b.Open.to_numpy(), b.Close.to_numpy(); rows = []
    for tt, r in k.iterrows():
        s = np.sign(sigf(r))
        if s == 0: continue
        t0 = (tt + pd.Timedelta(minutes=5)).value; i = np.searchsorted(t, t0)
        if i >= len(t) or t[i] - t0 > 120e9: continue
        j = np.searchsorted(t, t0 + 59 * 60e9, side="right") - 1
        if j <= i: continue
        rows.append((tt.floor("D"), s * (c[j] / o[i] - 1)))
    raw = pd.DataFrame(rows, columns=["d", "r"]).groupby("d").r.sum().reindex(BD, fill_value=0)
    cnt = pd.DataFrame(rows, columns=["d", "r"]).groupby("d").r.count().reindex(BD, fill_value=0)
    best = None
    for d in (1, -1):
        r = d * raw - 2 * cost * cnt
        if best is None or sh(r, "2016", "2020") > best[1]: best = (d, sh(r, "2016", "2020"), r)
    d, a, r = best; b2, c2 = sh(r, "2021", "2024"), sh(r, "2025", "2026")
    v = "PASS" if (a >= 0.3 and b2 > 0 and c2 > 0) else ("kept, failed 2025-26" if a >= 0.3 and b2 > 0 else "drop")
    lab = sym + (" (USD+CAD news)" if sigf(pd.Series({"USD": 0, "CAD": 1})) else "")
    print(f"| {lab} | {len(rows)} | {'with good US data' if d == 1 else 'against good US data'} | {a:.2f} | {b2:.2f} | {c2:.2f} | {v} |")
print("\n# Part 2: leader/follower catch-up (hourly, entered 1 bar late)\n| Leader -> follower | 2016-20 | 2021-24 | 2025-26 | Verdict |\n|---|---|---|---|---|")
hr = lambda s: m1(s).Close.resample("1h").last()
for L, F, th, cost in (("SPXUSD", "NSXUSD", 0.003, 1e-4), ("NSXUSD", "SPXUSD", 0.003, 1e-4), ("SPXUSD", "GRXEUR", 0.003, 1e-4),
                       ("EURUSD", "GBPUSD", 0.0015, 1e-4), ("AUDUSD", "AUDJPY", 0.0015, 1e-4)):
    df = pd.concat({"l": hr(L), "f": hr(F)}, axis=1).dropna(); gap = df.l.pct_change() - df.f.pct_change()
    sig = pd.Series(np.where(gap.abs() > th, np.sign(gap), 0.0), index=df.index); held = sig.shift(2).fillna(0)
    rh = held * df.f.pct_change().fillna(0) - held.diff().abs().fillna(0) * cost
    r = rh.groupby(rh.index.floor("D")).sum().reindex(BD, fill_value=0)
    a, b2, c2 = sh(r, "2016", "2020"), sh(r, "2021", "2024"), sh(r, "2025", "2026")
    v = "PASS" if (a >= 0.3 and b2 > 0 and c2 > 0) else "drop"
    print(f"| {L} -> {F} | {a:.2f} | {b2:.2f} | {c2:.2f} | {v} |")
