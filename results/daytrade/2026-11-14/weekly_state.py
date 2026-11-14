"""Pre-registered: change size on the next trade depending on the week so far / last trade.
Nasdaq trades only (news trades not included). Size multiplier applies to the R result."""
import numpy as np, pandas as pd
t = pd.read_csv("/tmp/nas_trades.csv"); r = t.r_multiple.values
ts = pd.to_datetime(t.entry_ts); wk = ts.dt.tz_convert(None).dt.to_period("W").values; yr = ts.dt.year.values
def run(rule):
    out, wsum, cur, last = [], 0.0, None, None
    for i in range(len(r)):
        if wk[i] != cur: cur, wsum = wk[i], 0.0
        m = rule(wsum, last); x = m * r[i]; out.append(x); wsum += x; last = r[i]
    return np.array(out)
def dd(x): c = np.concatenate([[0], np.cumsum(x)]); return (np.maximum.accumulate(c) - c).max()
rules = {
 "Current (always full size)": lambda w, l: 1,
 "Week up >= +2R: half size rest of week": lambda w, l: .5 if w >= 2 else 1,
 "Week up >= +2R: stop for the week": lambda w, l: 0 if w >= 2 else 1,
 "Week down <= -2R: half size rest of week": lambda w, l: .5 if w <= -2 else 1,
 "Week down <= -2R: stop for the week": lambda w, l: 0 if w <= -2 else 1,
 "Week down <= -2R: 1.5x size (chase it back)": lambda w, l: 1.5 if w <= -2 else 1,
 "After a loss: half size next trade": lambda w, l: .5 if (l is not None and l < 0) else 1,
 "After a win: half size next trade": lambda w, l: .5 if (l is not None and l > 0) else 1,
}
print("| Rule | 10-yr R | vs now | 2016-20 | 2021-24 | 2025-26 | Max DD R | Avg size |\n|---|---|---|---|---|---|---|---|")
base = run(rules["Current (always full size)"])
for k, f in rules.items():
    x = run(f); sz = np.where(r != 0, x / r, 1).mean()
    p = [x[(yr >= a) & (yr <= b)].sum() - base[(yr >= a) & (yr <= b)].sum() for a, b in ((2016, 2020), (2021, 2024), (2025, 2026))]
    print(f"| {k} | {x.sum():+.1f} | {x.sum()-base.sum():+.1f} | {p[0]:+.1f} | {p[1]:+.1f} | {p[2]:+.1f} | {dd(x):.1f} | {sz:.2f} |")
# return per unit of drawdown, fairer for half-size rules
