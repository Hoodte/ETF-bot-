"""'Reassurance exit' (Brendan's idea, pre-registered 14 Nov 2026).

At ENTRY, score the trade from conditions known at entry. Model: logistic regression, trained on
2016-20 only, predicting 'trade reaches the 3R target'. The threshold is the median training score.
- 'strong' (score >= threshold): keep the current exit (hold to 3R / 15:55)
- 'weak' (score < threshold): trail 1R below the running high once +1.5R (50% of TP) is reached
Nearby: activation 1.2 / 1.5 / 1.8R (40/50/60% of TP), trail 0.75 / 1.0 / 1.25R; threshold at the 40/50/60th pct.
Features (all known at the entry bar open):
 vol_ratio  ATR at entry / mean ATR of the previous 20 trades' ... -> use the M15 range ratio instead:
            mean(high-low) last 26 bars / mean(high-low) last 520 bars
 day_move   (entry - NY 09:30 open) / R
 week_trend (entry - close ~5 trading days earlier) / R
 prev_day   previous NY day close-to-close return / R
 rsi        RSI(14) of the signal bar (bar before entry)
 mins       minutes after 11:30 NY of the entry
Controls: also report a 'random half' version (same number of trades trailed, chosen at random)
to show whether the model beats luck.
"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, ".")
sys.path.insert(0, "results/daytrade/2026-11-14")
import exit_candidates as ec
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

df, t = ec.df, ec.t
H, L, O, C = ec.H, ec.L, ec.O, ec.C
NY = ec.NY
date = NY.dt.date.values
mins = ec.MIN

# RSI(14), Wilder
d = np.diff(C, prepend=C[0])
up = pd.Series(np.clip(d, 0, None)).ewm(alpha=1 / 14, adjust=False).mean()
dn = pd.Series(np.clip(-d, 0, None)).ewm(alpha=1 / 14, adjust=False).mean()
RSI = (100 - 100 / (1 + up / dn)).values
rng_ = pd.Series(H - L)
r26 = rng_.rolling(26).mean().shift(1).values
r520 = rng_.rolling(520).mean().shift(1).values
# NY 09:30 open per day, and the previous day's last close
open930 = {}
lastclose = {}
for i in range(len(C)):
    dd = date[i]
    if mins[i] == 570 and dd not in open930:
        open930[dd] = O[i]
    if 570 <= mins[i] < 960:
        lastclose[dd] = C[i]
days = sorted(lastclose)
prevclose = {days[k]: lastclose[days[k - 1]] for k in range(1, len(days))}
prev2close = {days[k]: lastclose[days[k - 2]] for k in range(2, len(days))}
c5 = {days[k]: lastclose[days[k - 5]] for k in range(5, len(days))}

rows = []
for r in t.itertuples():
    i = r.entry_idx
    e = r.entry_price
    R = e - r.initial_stop_price
    dd = date[i]
    rows.append(dict(
        vol_ratio=r26[i] / r520[i],
        day_move=(e - open930.get(dd, np.nan)) / R,
        week_trend=(e - c5.get(dd, np.nan)) / R,
        prev_day=(prevclose.get(dd, np.nan) - prev2close.get(dd, np.nan)) / R,
        rsi=RSI[i - 1],
        mins=mins[i] - 690))
X = pd.DataFrame(rows)
X = X.fillna(X.median())
y = (t.exit_reason == "target").values.astype(int)
yr = t.year.values
tr = yr <= 2020

sc = StandardScaler().fit(X[tr])
m = LogisticRegression(C=1.0).fit(sc.transform(X[tr]), y[tr])
score = m.predict_proba(sc.transform(X))[:, 1]
print("Model coefficients (standardised):", dict(zip(X.columns, np.round(m.coef_[0], 2))))
from sklearn.metrics import roc_auc_score
for lab, msk in [("2016-20 (train)", tr), ("2021-24", (yr >= 2021) & (yr <= 2024)), ("2025-26", yr >= 2025)]:
    print(f"  AUC predicting target-hit, {lab}: {roc_auc_score(y[msk], score[msk]):.3f}")
print("  (0.5 = no better than a coin flip)\n")

base, _ = ec.replay()
PER = [("2016-20", (2016, 2020)), ("2021-24", (2021, 2024)), ("2025-26", (2025, 2026)), ("Full", (2016, 2026))]


def show(name, x):
    p = [x[(yr >= a) & (yr <= b)].sum() - base[(yr >= a) & (yr <= b)].sum() for _, (a, b) in PER]
    print(f"| {name} | {x.sum():+.1f} | {p[3]:+.1f} | {p[0]:+.1f} | {p[1]:+.1f} | {p[2]:+.1f} |")


print("| Rule | 10-yr R | vs now | 16-20 (train) | 21-24 | 25-26 |\n|---|---|---|---|---|---|")
show("Current exit", base)
trail_cache = {}
for act in (1.2, 1.5, 1.8):
    for dist in (0.75, 1.0, 1.25):
        trail_cache[(act, dist)] = ec.replay(trail=(act, dist))[0]
show("Trail on ALL trades (1.5R / 1R)", trail_cache[(1.5, 1.0)])
for q in (40, 50, 60):
    thr = np.percentile(score[tr], q)
    weak = score < thr
    for act in (1.2, 1.5, 1.8):
        for dist in (0.75, 1.0, 1.25):
            x = np.where(weak, trail_cache[(act, dist)], base)
            tag = "**PRIMARY** " if (q, act, dist) == (50, 1.5, 1.0) else ""
            show(f"{tag}weak={q}% , trail after {act}R by {dist}R", x)
# random control
thr = np.percentile(score[tr], 50)
weak = score < thr
rs = np.random.default_rng(7)
diffs = []
for _ in range(2000):
    w = rs.permutation(weak)
    diffs.append((np.where(w, trail_cache[(1.5, 1.0)], base) - base)[yr >= 2021].sum())
prim = (np.where(weak, trail_cache[(1.5, 1.0)], base) - base)[yr >= 2021].sum()
print(f"\nPrimary rule 2021-26 vs current: {prim:+.1f}R. Random-half control: mean {np.mean(diffs):+.1f}R; "
      f"share of random picks that do as well or better: {(np.array(diffs) >= prim).mean():.2f}")
# Did weak trades actually reverse more?
for lab, msk in [("train", tr), ("2021-26", yr >= 2021)]:
    hi = t.r_mfe.values >= 1.5
    print(f"{lab}: of trades reaching +1.5R, ended negative -> weak {np.mean(base[msk & hi & weak] < 0):.0%} "
          f"(n={np.sum(msk & hi & weak)}), strong {np.mean(base[msk & hi & ~weak] < 0):.0%} (n={np.sum(msk & hi & ~weak)})")
