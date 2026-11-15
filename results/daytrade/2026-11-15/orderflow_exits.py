"""Order-flow exit tests — see results/daytrade/2026-11-15/orderflow_preregistration.md (fixed before data).
Usage (from backtest-bot folder): python3 results/daytrade/2026-11-15/orderflow_exits.py <dir with nq_minute.csv.gz, nq_footprint.csv.gz>
"""
import sys, io, contextlib
from datetime import datetime, timezone
import numpy as np, pandas as pd
sys.path.insert(0, ".")
from data.cache import read_bars

DIR = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/backtestbot/nq_orderflow"
df = read_bars("data/cache", "histdata", "NAS100", "M15", datetime(2016, 1, 1, tzinfo=timezone.utc),
               datetime(2026, 11, 1, tzinfo=timezone.utc)).reset_index(drop=True)
H, L = df.high.values, df.low.values
TS = pd.to_datetime(df.timestamp_utc, utc=True).dt.tz_convert(None).values
t = pd.read_csv("/tmp/nas_trades.csv")
t["window"] = (pd.to_datetime(t.entry_ts) - pd.Timedelta(minutes=60)).dt.strftime("%Y-%m-%dT%H:%M")
t["year"] = pd.to_datetime(t.entry_ts).dt.year

m = pd.read_csv(f"{DIR}/nq_minute.csv.gz", parse_dates=["m1"])
f = pd.read_csv(f"{DIR}/nq_footprint.csv.gz", parse_dates=["m15"])
m["delta"] = m.buy - m.sell
mg, fg = dict(tuple(m.groupby("window"))), dict(tuple(f.groupby("window")))


def value_area_high(fp):
    prof = fp.assign(v=fp.buy + fp.sell).groupby("lvl").v.sum().sort_index()
    if prof.sum() <= 0:
        return np.nan
    lv, v = prof.index.values, prof.values
    i = j = int(np.argmax(v)); tot = v[i]
    while tot < 0.7 * v.sum():
        up = v[j + 1] if j + 1 < len(v) else -1
        dn = v[i - 1] if i - 1 >= 0 else -1
        if up >= dn: j += 1; tot += up
        else: i -= 1; tot += dn
    return lv[j]


def max_stack(fb, ratio):
    fb = fb.sort_values("lvl")
    flag = ((fb.sell >= ratio * fb.buy) & (fb.sell > 0)).values
    lv = fb.lvl.values
    best = run = 0
    for k in range(len(flag)):
        if flag[k] and k > 0 and flag[k - 1] and lv[k] - lv[k - 1] <= 1.0001:
            run += 1
        else:
            run = 1 if flag[k] else 0
        best = max(best, run)
    return best


rows = []
for r in t.itertuples():
    e, s0 = r.entry_price, r.initial_stop_price
    R = e - s0
    cR = r.costs / (r.units * R)
    dec = None
    for i in range(r.entry_idx, r.exit_idx + 1):
        if L[i] <= s0:
            break
        if H[i] >= e + 0.8 * R:
            dec = i
            break
    row = dict(idx=r.Index, year=r.year, base=r.r_multiple, early=0.8 - cR, has_dec=dec is not None,
               has_data=r.window in mg, entry_ts=r.entry_ts)
    if dec is not None and r.window in mg:
        mm, ff = mg[r.window], fg.get(r.window, pd.DataFrame(columns=f.columns))
        te, td = pd.Timestamp(TS[r.entry_idx]), pd.Timestamp(TS[dec])
        tend = td + pd.Timedelta(minutes=15)
        since = mm[(mm.m1 >= te) & (mm.m1 < tend)]
        bar = mm[(mm.m1 >= td) & (mm.m1 < tend)]
        before = mm[(mm.m1 >= te) & (mm.m1 < td)]
        fb = ff[ff.m15 == td]
        if len(bar) and len(since):
            hi, lo, c = bar.h.max(), bar.l.min(), bar.c.iloc[-1]
            bvol = (bar.buy + bar.sell).sum()
            row.update(
                bar_delta=bar.delta.sum(), bar_vol=bvol,
                new_high=(len(before) == 0) or (hi >= before.h.max()),
                cvd=since.delta.sum(), vol_since=(since.buy + since.sell).sum(),
                close_pos=(c - lo) / (hi - lo) if hi > lo else 0.5)
            if len(fb):
                top = fb[fb.lvl >= hi - 0.25 * (hi - lo)]
                row["top_share"] = (top.buy + top.sell).sum() / max((fb.buy + fb.sell).sum(), 1)
                for ratio in (2.5, 3.0, 4.0):
                    row[f"stack{ratio}"] = max_stack(fb, ratio)
            fpre = ff[ff.m15 <= td]
            vah = value_area_high(fpre) if len(fpre) else np.nan
            nq_entry = mm[mm.m1 >= te].o.iloc[0] if (mm.m1 >= te).any() else np.nan
            row["stretch"] = (c - vah) / (R / e * nq_entry) if np.isfinite(vah) else np.nan
    rows.append(row)
D = pd.DataFrame(rows)
ok = D.has_dec & D.has_data & D.bar_vol.notna() if "bar_vol" in D else D.has_dec & False
print(f"Trades: {len(D)}; with order-flow data downloaded: {D.has_data.sum()}; reaching +0.8R with data: {ok.sum()}\n")


def rule_result(close_mask):
    cm = close_mask.fillna(False).values & ok.values
    return np.where(cm, D.early.values, D.base.values), cm


PER = [("2016-20", (2016, 2020)), ("2021-24", (2021, 2024)), ("2025-26", (2025, 2026)), ("Full", (2016, 2026))]
base = D.base.values
yr = D.year.values
cover = D.has_data.values


def summarise(name, x, cm):
    d = x - base
    cells = [f"{d[(yr >= a) & (yr <= b) & cover].sum():+.1f}" for _, (a, b) in PER]
    lo, wi = base < 0, base >= 0
    return f"| {name} | {cm.sum()} | " + " | ".join(cells) + f" | {d[cm & lo].sum():+.1f} | {d[cm & wi].sum():+.1f} |"


rules = {
    "1 Delta divergence (bar delta < 0 on new high) PRIMARY": D.new_high.astype(bool) & (D.bar_delta < 0),
    "1 nearby: delta < -10% vol": D.new_high.astype(bool) & (D.bar_delta < -0.1 * D.bar_vol),
    "1 nearby: delta < +10% vol": D.new_high.astype(bool) & (D.bar_delta < 0.1 * D.bar_vol),
    "2 Absorption at high (top share >= 40%, close lower half) PRIMARY": (D.top_share >= 0.40) & (D.close_pos < 0.5),
    "2 nearby: 35%": (D.top_share >= 0.35) & (D.close_pos < 0.5),
    "2 nearby: 45%": (D.top_share >= 0.45) & (D.close_pos < 0.5),
    "3 Stacked sell imbalances (>=3 levels, 3x) PRIMARY": D["stack3.0"] >= 3,
    "3 nearby: 2 levels": D["stack3.0"] >= 2,
    "3 nearby: 4 levels": D["stack3.0"] >= 4,
    "3 nearby: ratio 2.5x": D["stack2.5"] >= 3,
    "3 nearby: ratio 4x": D["stack4.0"] >= 3,
    "4 Delta not confirming (CVD since entry <= 0) PRIMARY": D.cvd <= 0,
    "4 nearby: CVD <= -5% vol": D.cvd <= -0.05 * D.vol_since,
    "4 nearby: CVD <= +5% vol": D.cvd <= 0.05 * D.vol_since,
    "5 Stretched above value (> 1.0R over VAH) PRIMARY": D.stretch > 1.0,
    "5 nearby: 0.5R": D.stretch > 0.5,
    "5 nearby: 1.5R": D.stretch > 1.5,
}
print("Change in total R vs current exit (trades with order-flow data only)\n")
print("| Rule | Trades closed early | 2016-20 | 2021-24 | 2025-26 | Full | Saved on losers | Given up on winners |\n|---|---|---|---|---|---|---|---|")
results = {}
for k, msk in rules.items():
    x, cm = rule_result(msk)
    results[k] = x
    print(summarise(k, x, cm))

# --- 6: smart-exit logistic with / without order-flow features (train 2016-20 only)
with contextlib.redirect_stdout(io.StringIO()):
    src = open("/home/claude/etf-bot-/results/daytrade/2026-11-12/metalabel.py").read().split('print(f"decision points')[0]
    g = {}
    exec(src, g)
S = g["D"].copy()
S["entry_ts"] = pd.to_datetime(S.ts).dt.tz_convert("UTC") if pd.to_datetime(S.ts).dt.tz is not None else pd.to_datetime(S.ts)
D["entry_ts_p"] = pd.to_datetime(D.entry_ts)
J = S.merge(D[ok].assign(entry_ts=D.entry_ts_p)[["entry_ts", "bar_delta", "bar_vol", "cvd", "vol_since", "top_share", "stack3.0", "stretch", "idx"]],
            on="entry_ts", how="inner")
J["of_bar"] = J.bar_delta / J.bar_vol
J["of_cvd"] = J.cvd / J.vol_since
J["of_stack"] = J["stack3.0"].fillna(0)
J["of_top"] = J.top_share.fillna(J.top_share.median())
J["of_stretch"] = J.stretch.fillna(J.stretch.median()).clip(-5, 5)
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
X0 = g["X"]
X1 = X0 + ["of_bar", "of_cvd", "of_stack", "of_top", "of_stretch"]
tr = J.yr <= 2020
print(f"\n6) Smart-exit model with order flow (decision points with data: train {tr.sum()}, test {(~tr).sum()})\n")
print("| Model | 2016-20 (train) | 2021-24 | 2025-26 | closed early (test) |\n|---|---|---|---|---|")
for lab, X in (("smart exit (price only)", X0), ("smart exit + order flow", X1)):
    if tr.sum() < 30 or (~tr).sum() < 10:
        print(f"| {lab} | not enough data yet | | | |")
        continue
    mdl = make_pipeline(StandardScaler(), LogisticRegression(C=0.5)).fit(J.loc[tr, X], J.loc[tr, "y"])
    p = mdl.predict_proba(J[X])[:, 1]
    gain = np.where(p < 0.5, J.early - J.hold, 0.0)
    cells = [f"{gain[(J.yr >= a) & (J.yr <= b)].sum():+.1f}" for a, b in ((2016, 2020), (2021, 2024), (2025, 2026))]
    print(f"| {lab} | " + " | ".join(cells) + f" | {np.mean(p[~tr] < 0.5):.0%} |")

# bootstrap for the primary rules, 2021-26, month blocks
print("\nMonth-block bootstrap, 2021-26, chance the primary rule's gain is really <= 0:")
mo = pd.to_datetime(D.entry_ts).dt.strftime("%Y-%m").values
rng = np.random.default_rng(0)
for k, x in results.items():
    if "PRIMARY" not in k:
        continue
    msk = (yr >= 2021) & cover
    dd = pd.Series((x - base)[msk]).groupby(mo[msk]).sum().values
    if len(dd) < 5:
        continue
    bs = np.array([rng.choice(dd, len(dd)).sum() for _ in range(5000)])
    print(f"- {k.split(' PRIMARY')[0]}: gain {dd.sum():+.1f}R, p = {np.mean(bs <= 0):.2f}")
