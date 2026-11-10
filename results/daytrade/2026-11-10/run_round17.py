import numpy as np, pandas as pd, warnings, sys; warnings.filterwarnings("ignore")
H = "data/histdata"; C1 = 1e-4; FIN = 0.05 / 252; BD = pd.bdate_range("2016-01-01", "2026-10-30")
def sh(r, a, b): x = r[a:b]; return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0
def P(r): return sh(r, "2016", "2020"), sh(r, "2021", "2024"), sh(r, "2025", "2026")
def m1(s): b = pd.read_pickle(f"{H}/{s}_1m.pkl"); return b[~b.index.duplicated()].sort_index()
def daily_close(s, tz="UTC", hm=None):
    c = m1(s).Close
    if hm: c = c.tz_convert(tz); c = c[(c.index.hour == hm[0]) & (c.index.minute == hm[1])]
    else: c = c.resample("1D").last().dropna()
    c.index = pd.to_datetime(c.index.date); return c[~c.index.duplicated()]
rows = []
def report(name, r, nearby=()):
    a, b, c = P(r); ok_near = sum(all(x > 0 for x in P(n)) for n in nearby)
    passed = a >= 0.4 and b >= 0.2 and c > 0 and (not nearby or ok_near * 2 > len(nearby))
    rows.append(f"| {name} | {a:.2f} | {b:.2f} | {c:.2f} | {ok_near}/{len(nearby)} | {'PASS' if passed else 'drop'} |"); print(rows[-1], flush=True)
FX = ["EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "USDCAD"]; USDSIGN = {"EURUSD": -1, "GBPUSD": -1, "AUDUSD": -1, "USDJPY": 1, "USDCAD": 1}
# ---------- 1 month-end FX
fix = pd.concat({s: daily_close(s, "Europe/London", (16, 0)) for s in FX}, axis=1).dropna()
spx = daily_close("SPXUSD", "America/New_York", (15, 59)); dax = daily_close("GRXEUR", "Europe/Berlin", (17, 29))
eq = pd.concat({"s": spx, "d": dax}, axis=1).dropna()
def month_end(nd):
    out = pd.Series(0.0, index=BD); fr = fix.pct_change()
    for _, g in fix.groupby(fix.index.to_period("M")):
        if len(g) < nd + 5: continue
        sig_day = g.index[-(nd + 1)]; e = eq[(eq.index.to_period("M") == sig_day.to_period("M")) & (eq.index <= sig_day)]
        if len(e) < 3: continue
        rel = (e.s.iloc[-1] / e.s.iloc[0]) - (e.d.iloc[-1] / e.d.iloc[0]); usd = -1 if rel > 0 else 1
        for d in g.index[-nd:]:
            out[d] = out.get(d, 0) + np.mean([usd * USDSIGN[s] * fr.loc[d, s] for s in FX])
        out[g.index[-nd]] -= 2 * C1
    return out.reindex(BD, fill_value=0)
report("1 Month-end FX flows (2 days)", month_end(2), [month_end(1), month_end(3)])
# ---------- 2 currency momentum basket (value of 1 unit of currency in USD)
dc = pd.concat({s: daily_close(s) for s in FX + ["NZDJPY"]}, axis=1).dropna()
cur = pd.DataFrame({"EUR": dc.EURUSD, "GBP": dc.GBPUSD, "AUD": dc.AUDUSD, "JPY": 1 / dc.USDJPY, "CAD": 1 / dc.USDCAD,
                    "NZD": dc.NZDJPY / dc.USDJPY, "USD": 1.0})
def mom(lb, n):
    fri = cur.index[cur.index.dayofweek == 4]; w = pd.DataFrame(0.0, index=cur.index, columns=cur.columns); last = None
    for d in fri:
        i = cur.index.get_loc(d)
        if i < lb: continue
        rk = (cur.iloc[i] / cur.iloc[i - lb] - 1).sort_values(); t = pd.Series(0.0, index=cur.columns)
        t[rk.index[-n:]] = 1 / n; t[rk.index[:n]] = -1 / n; w.loc[d:] = t.values
    held = w.shift(1).fillna(0); r = (held * cur.pct_change().fillna(0)).sum(axis=1) - held.diff().abs().sum(axis=1).fillna(0) * C1
    return r.reindex(BD, fill_value=0)
report("2 Currency momentum (3m, top/bottom 2)", mom(63, 2), [mom(21, 2), mom(126, 2), mom(63, 1)])
# ---------- 3 OpEx week
idx = pd.concat({s: daily_close(s, "America/New_York", (15, 59)) for s in ("SPXUSD", "NSXUSD")}, axis=1).dropna()
def third_fridays(ix):
    f = ix[(ix.dayofweek == 4) & (ix.day >= 15) & (ix.day <= 21)]; return set(f)
def opex(enter_monday=False):
    tf = third_fridays(idx.index); ret = idx.pct_change().mean(axis=1).fillna(0); hold = pd.Series(0.0, index=idx.index)
    for f in tf:
        wk = idx.index[(idx.index > f - pd.Timedelta(days=7)) & (idx.index <= f)]
        if enter_monday: wk = wk[1:]
        hold[wk] = 1.0
    r = hold * ret - hold.diff().abs().fillna(0) * C1 - hold * FIN
    return r.reindex(BD, fill_value=0)
report("3 Options-expiry week (S&P+Nasdaq)", opex(), [opex(True)])
# ---------- 5 quarter-end rebalancing
ief = pd.read_csv("data/extra_ief_silver.csv", index_col=0, parse_dates=True)["IEF"].dropna()
sp = idx.SPXUSD
def qend(nd):
    out = pd.Series(0.0, index=sp.index); spr = sp.pct_change()
    for _, g in sp.groupby(sp.index.to_period("Q")):
        if len(g) < nd + 10: continue
        sd = g.index[-(nd + 1)]; b = ief[(ief.index >= g.index[0]) & (ief.index <= sd)]
        if len(b) < 5: continue
        rel = (g.loc[sd] / g.iloc[0]) - (b.iloc[-1] / b.iloc[0]); s = -1 if rel > 0 else 1
        for d in g.index[-nd:]: out[d] = s * spr[d] - FIN
        out[g.index[-nd]] -= 2 * C1
    return out.reindex(BD, fill_value=0)
report("5 Quarter-end rebalancing (5 days)", qend(5), [qend(3), qend(7)])
print("\n| Strategy | 2016-20 | 2021-24 | 2025-26 | Nearby all-positive | Verdict |\n|---|---|---|---|---|---|\n" + "\n".join(rows))
open("results/daytrade/2026-11-10/round17_results.md", "w").write("# Round 17 results (strategies 1,2,3,5)\n\n| Strategy | 2016-20 | 2021-24 | 2025-26 | Nearby all-positive | Verdict |\n|---|---|---|---|---|---|\n" + "\n".join(rows) + "\n")
