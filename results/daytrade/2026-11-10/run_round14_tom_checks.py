"""Robustness checks for Turn-of-month (decided before running): nearby windows (enter 1-3 days before
month end, exit after day 2-4), double costs, and per-year results. Recommend only if most nearby windows stay > 0
in all three periods at normal cost and the base window stays > 0 at double cost."""
import numpy as np, pandas as pd
exec(open("results/daytrade/2026-11-10/run_round14.py").read().split("def strategies")[0])
def sh(r, a, b):
    x = r[a:b]; return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0
def tom(d, pre, post, c1):
    n = nights(d.index); mo = d.index.to_period("M"); a = d.groupby(mo).cumcount(); e = d.groupby(mo).cumcount(ascending=False)
    hold = ((e <= pre - 1) | (a <= post - 1)).astype(float); entry = hold.diff().fillna(hold) > 0
    return (hold * (d.c / d.c.shift(1) - 1) - entry * c1 - (hold.shift(-1).fillna(0) < hold) * c1 - hold * n.shift(1).fillna(1) * FIN).fillna(0)
D = {s: sess(load(s)) for s in ("SPXUSD", "NSXUSD")}
pair = lambda pre, post, c1: (tom(D["SPXUSD"], pre, post, c1).add(tom(D["NSXUSD"], pre, post, c1), fill_value=0)) / 2
print("| Window (days before end / days into month) | Cost | 2016-20 | 2021-24 | 2025-26 |\n|---|---|---|---|---|")
for pre in (1, 2, 3):
    for post in (2, 3, 4):
        r = pair(pre, post, C1); print(f"| {pre} / {post}{' (base)' if (pre, post) == (2, 3) else ''} | 1x | {sh(r,'2016','2020'):.2f} | {sh(r,'2021','2024'):.2f} | {sh(r,'2025','2026'):.2f} |")
r = pair(2, 3, 2 * C1); print(f"| 2 / 3 (base) | 2x | {sh(r,'2016','2020'):.2f} | {sh(r,'2021','2024'):.2f} | {sh(r,'2025','2026'):.2f} |")
r = pair(2, 3, C1); y = (1 + r).groupby(r.index.year).prod() - 1
print("per year:", {k: f"{v:.1%}" for k, v in y.items()})
mr = (1 + r).resample("ME").prod() - 1; print(f"months positive {(mr[mr != 0] > 0).mean():.0%}, worst month {mr.min():.1%}")
