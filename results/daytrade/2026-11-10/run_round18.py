import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
C1 = 1e-4; BD = pd.bdate_range("2016-01-01", "2026-10-30")
def sh(r, a, b): x = r[a:b]; return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0
def load(s):
    b = pd.read_pickle(f"data/histdata/{s}_5m.pkl"); b = b[~b.index.duplicated()].sort_index(); b.index = b.index.tz_convert("America/New_York")
    m = b.index.hour * 60 + b.index.minute; b = b[(m >= 570) & (m < 960)]; return {d: g for d, g in b.groupby(b.index.date)}
def run(days, gmin=0.0025, gmax=0.015, entry_min=575, exit_min=720):
    keys = sorted(days); out = {}
    for n in range(1, len(keys)):
        g = days[keys[n]]; pc = days[keys[n - 1]].Close.iloc[-1]; mins = (g.index.hour * 60 + g.index.minute).values
        if mins[0] != 570: continue
        gap = g.Open.iloc[0] / pc - 1
        if not (gmin <= abs(gap) <= gmax): continue
        side = -np.sign(gap); k = np.searchsorted(mins, entry_min)
        if k >= len(g): continue
        ep = g.Open.iloc[k]; tgt = pc; stp = ep - side * abs(ep - pc) if False else ep - side * abs(gap) * pc
        if side * (tgt - ep) <= 0: out[pd.Timestamp(keys[n])] = 0.0; continue   # already filled before entry
        O, H, L, C = g.Open.values, g.High.values, g.Low.values, g.Close.values; res = None
        for i in range(k, len(g)):
            if (side > 0 and L[i] <= stp) or (side < 0 and H[i] >= stp):
                px = min(O[i], stp) if side > 0 else max(O[i], stp); res = side * (px / ep - 1); break
            if (side > 0 and H[i] >= tgt) or (side < 0 and L[i] <= tgt): res = side * (tgt / ep - 1); break
            if mins[i] >= exit_min - 5: res = side * (C[i] / ep - 1); break
        if res is None: res = side * (C[-1] / ep - 1)
        out[pd.Timestamp(keys[n])] = res - 2 * C1
    return pd.Series(out).reindex(BD, fill_value=0.0)
D = {s: load(s) for s in ("SPXUSD", "NSXUSD")}
sets = {"BASE": {}, "min 0.15%": {"gmin": 0.0015}, "min 0.40%": {"gmin": 0.004}, "max 1.0%": {"gmax": 0.01}, "max 2.5%": {"gmax": 0.025},
        "enter 09:30": {"entry_min": 570}, "exit 16:00": {"exit_min": 960}}
print("| Setting | Market | 2016-20 | 2021-24 | 2025-26 | Trades/yr | Win rate |\n|---|---|---|---|---|---|---|")
for k, kw in sets.items():
    rs = {s: run(D[s], **kw) for s in D}; rs["50/50"] = (rs["SPXUSD"] + rs["NSXUSD"]) / 2
    for s, r in rs.items():
        nz = r[r != 0]
        print(f"| {k} | {s.replace('SPXUSD','S&P').replace('NSXUSD','Nasdaq')} | {sh(r,'2016','2020'):.2f} | {sh(r,'2021','2024'):.2f} | {sh(r,'2025','2026'):.2f} | {len(nz)/10.8:.0f} | {(nz>0).mean():.0%} |", flush=True)
