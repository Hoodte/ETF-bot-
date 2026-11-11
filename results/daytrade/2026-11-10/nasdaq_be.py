import sys; from datetime import datetime, timezone
import numpy as np, pandas as pd
sys.path.insert(0, ".")
from data.cache import read_bars
df = read_bars("data/cache", "histdata", "NAS100", "M15", datetime(2016,1,1,tzinfo=timezone.utc), datetime(2026,11,1,tzinfo=timezone.utc)).reset_index(drop=True)
H, L, O, C = df.high.values, df.low.values, df.open.values, df.close.values
t = pd.read_csv("/tmp/nas_trades.csv")
def replay(be=None, tp=None, half=None):
    out = []
    for r in t.itertuples():
        e, s0, tg = r.entry_price, r.initial_stop_price, r.initial_target_price; R = e - s0; cR = r.costs / (r.units * R)
        stop = s0; tgt = tp * R + e if tp else tg; res = None; half_done = None
        for i in range(r.entry_idx, r.exit_idx + 1):
            if L[i] <= stop: res = (min(O[i], stop) - e) / R if i > r.entry_idx else (stop - e) / R; break
            if half and half_done is None and H[i] >= e + half * R: half_done = half
            if H[i] >= tgt: res = (tgt - e) / R; break
            if be and H[i] >= e + be * R: stop = max(stop, e)
        if res is None: res = (r.exit_price - e) / R
        if half: res = 0.5 * (half_done if half_done is not None else res) + 0.5 * res
        out.append(res - cR)
    return pd.Series(out, index=pd.to_datetime(t.entry_ts).dt.tz_convert(None).dt.normalize())
BD = pd.bdate_range("2016-01-01", "2026-10-30")
def sh(s, a, b): d = s.groupby(level=0).sum().reindex(BD, fill_value=0)[a:b]; return d.mean() / d.std() * np.sqrt(252)
print("| Exit rule | Win % | Avg R | Total R | 2016-20 | 2021-24 | 2025-26 |\n|---|---|---|---|---|---|---|")
for lab, kw in [("current (stop 1R, target 3R, out 15:55)", {}), ("break-even after +0.5R", {"be": .5}), ("break-even after +0.75R", {"be": .75}),
                ("break-even after +1R", {"be": 1}), ("break-even after +1.5R", {"be": 1.5}), ("take profit at +0.8R", {"tp": .8}),
                ("take profit at +1R", {"tp": 1}), ("half off at +1R, rest as now", {"half": 1})]:
    s = replay(**kw)
    print(f"| {lab} | {(s>0).mean():.0%} | {s.mean():+.3f} | {s.sum():+.0f} | {sh(s,'2016','2020'):.2f} | {sh(s,'2021','2024'):.2f} | {sh(s,'2025','2026'):.2f} |", flush=True)
