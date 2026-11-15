"""Combine smart exit (+/- order flow), reassurance exit and weekly stop. Models trained 2016-20 only."""
import io, contextlib, runpy, sys, numpy as np, pandas as pd
sys.argv = ["x"]
with contextlib.redirect_stdout(io.StringIO()):
    of = runpy.run_path("/tmp/of_check.py")
    ra = runpy.run_path("results/daytrade/2026-11-14/reassurance_exit.py")
t = ra["t"]; base = ra["base"]; weak = ra["weak"]; trail = ra["trail_cache"][(1.5, 1.0)]
yr = t.year.values
J = of["J"]
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
tr = (J.yr <= 2020).values
def smart_close(X):
    m = make_pipeline(StandardScaler(), LogisticRegression(C=0.5)).fit(J.loc[tr, X], J.loc[tr, "y"])
    p = m.predict_proba(J[X])[:, 1]
    sc = np.zeros(len(t), bool); sc[J.idx.values[p < 0.5]] = True
    early = np.zeros(len(t)); early[J.idx.values] = J.early.values
    return sc, early
sc0, early = smart_close(of["X0"]); sc1, _ = smart_close(of["X1"])
wk = pd.to_datetime(t.entry_ts).dt.tz_convert(None).dt.to_period("W").values
def weekly(x):
    out = []; w = 0; cur = None
    for i in range(len(x)):
        if wk[i] != cur: cur, w = wk[i], 0.0
        v = 0.0 if w >= 2 else x[i]; out.append(v); w += v
    return np.array(out)
def comb(smart=None, reass=False, week=False):
    x = base.copy()
    if reass: x = np.where(weak, trail, x)
    if smart is not None: x = np.where(smart, early, x)
    return weekly(x) if week else x
rows = {
 "Current exit": base,
 "Smart (price)": comb(sc0), "Smart (+order flow)": comb(sc1),
 "Reassurance": comb(reass=True), "Weekly stop": comb(week=True),
 "Smart(price) + Reassurance": comb(sc0, True),
 "Smart(price) + Reassurance + Weekly": comb(sc0, True, True),
 "Smart(+OF) + Reassurance": comb(sc1, True),
 "Smart(+OF) + Reassurance + Weekly": comb(sc1, True, True),
}
def dd(x): c = np.concatenate([[0], np.cumsum(x)]); return (np.maximum.accumulate(c) - c).max()
mo = pd.to_datetime(t.entry_ts).dt.strftime("%Y-%m").values; rng = np.random.default_rng(3)
te = yr >= 2021
print("| Combination | 2016-20 (train) | 2021-24 | 2025-26 | 2021-26 vs now | per year | max DD 2021-26 | p(no gain) |\n|---|---|---|---|---|---|---|---|")
for k, x in rows.items():
    d = x - base
    s = [d[(yr >= a) & (yr <= b)].sum() for a, b in ((2016, 2020), (2021, 2024), (2025, 2026))]
    g = pd.Series(d[te]).groupby(mo[te]).sum().values
    p = np.mean([rng.choice(g, len(g)).sum() <= 0 for _ in range(4000)]) if np.any(g) else float("nan")
    print(f"| {k} | {s[0]:+.1f} | {s[1]:+.1f} | {s[2]:+.1f} | {d[te].sum():+.1f} | {d[te].sum()/5.83:+.1f} | {dd(x[te]):.1f} | {p:.2f} |")
