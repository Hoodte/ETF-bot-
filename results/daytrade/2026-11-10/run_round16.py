import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
C1 = 1e-4; BD = pd.bdate_range("2016-01-01", "2026-10-30")
vix = pd.read_csv("data/^VIX.csv", index_col=0, parse_dates=True).iloc[:, 0]
def sh(r, a, b): x = r[a:b]; return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0
def load(s):
    b = pd.read_pickle(f"data/histdata/{s}_5m.pkl"); b = b[~b.index.duplicated()].sort_index(); b.index = b.index.tz_convert("America/New_York")
    m = b.index.hour * 60 + b.index.minute; return b[(m >= 570) & (m < 960)]
def run(b, k, mode):
    days = {d: g for d, g in b.groupby(b.index.date)}; keys = sorted(days); out = {}
    for n in range(1, len(keys)):
        d, pd_ = keys[n], keys[n - 1]; prev = days[pd_].Close.iloc[-1]
        v = vix.asof(pd.Timestamp(pd_))
        if np.isnan(v): continue
        em = prev * v / 100 / np.sqrt(252); up, lo = prev + k * em, prev - k * em
        g = days[d]; O, Hh, L, C = g.Open.values, g.High.values, g.Low.values, g.Close.values
        mins = g.index.hour * 60 + g.index.minute; tot = 0.0; done = {1: False, -1: False}; pos = 0
        i = 0
        while i < len(g):
            if pos == 0:
                if mins[i] >= 955: break
                if mode == "fade":
                    if not done[1] and L[i] <= lo: pos, ep, tgt, stp = 1, min(O[i], lo), prev, lo - 0.5 * em; done[1] = True
                    elif not done[-1] and Hh[i] >= up: pos, ep, tgt, stp = -1, max(O[i], up), prev, up + 0.5 * em; done[-1] = True
                    if pos: tot -= C1;  # check exits from same bar onward (conservative: stop first)
                    if pos:
                        if (pos == 1 and L[i] <= stp) or (pos == -1 and Hh[i] >= stp): tot += pos * (stp / ep - 1) - C1; pos = 0
                    i += 1; continue
                else:
                    if not done[1] and C[i] > up and i + 1 < len(g): pos, ep, stp = 1, O[i + 1], up; done[1] = True; tot -= C1; i += 1; continue
                    if not done[-1] and C[i] < lo and i + 1 < len(g): pos, ep, stp = -1, O[i + 1], lo; done[-1] = True; tot -= C1; i += 1; continue
                    i += 1; continue
            # in position
            if (pos == 1 and L[i] <= stp) or (pos == -1 and Hh[i] >= stp):
                px = min(O[i], stp) if pos == 1 else max(O[i], stp); tot += pos * (px / ep - 1) - C1; pos = 0
            elif mode == "fade" and ((pos == 1 and Hh[i] >= tgt) or (pos == -1 and L[i] <= tgt)):
                tot += pos * (tgt / ep - 1) - C1; pos = 0
            elif mins[i] >= 955:
                tot += pos * (C[i] / ep - 1) - C1; pos = 0
            i += 1
        if pos: tot += pos * (C[-1] / ep - 1) - C1
        out[pd.Timestamp(d)] = tot
    return pd.Series(out).reindex(BD, fill_value=0.0)
B = {s: load(s) for s in ("SPXUSD", "NSXUSD")}
print("| Version | Market | k | 2016-20 | 2021-24 | 2025-26 | Days traded/yr |\n|---|---|---|---|---|---|---|")
for mode in ("fade", "break"):
    for k in (1.0, 0.75, 1.25):
        rs = {}
        for s in B:
            r = run(B[s], k, mode); rs[s] = r
            print(f"| {mode} | {'S&P' if s=='SPXUSD' else 'Nasdaq'} | {k} | {sh(r,'2016','2020'):.2f} | {sh(r,'2021','2024'):.2f} | {sh(r,'2025','2026'):.2f} | {(r != 0).sum()/10.8:.0f} |", flush=True)
