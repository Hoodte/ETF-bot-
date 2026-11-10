import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
H = "data/histdata"; C1 = 1e-4; FIN = 0.05 / 365
def load(s):
    b = pd.read_pickle(f"{H}/{s}_5m.pkl"); b = b[~b.index.duplicated()].sort_index(); b.index = b.index.tz_convert("America/New_York"); return b
def sess(b):
    m = b.index.hour * 60 + b.index.minute; r = b[(m >= 570) & (m < 960)]; g = r.groupby(r.index.date)
    d = pd.DataFrame({"o": g.Open.first(), "c": g.Close.last()}); d.index = pd.to_datetime(d.index)
    def px(hm):  # close of the bar ending at hh:mm (bar starting 5 min earlier)
        t = r[(r.index.hour * 60 + r.index.minute) == hm - 5].Close; t.index = pd.to_datetime(t.index.date); return t
    d["c1000"] = px(600); d["o1530"] = r[(r.index.hour * 60 + r.index.minute) == 930].Open.set_axis(pd.to_datetime(r[(r.index.hour * 60 + r.index.minute) == 930].index.date))
    d["c1559"] = px(960); return d.dropna(subset=["o", "c"])
def nights(idx): return pd.Series(idx, index=idx).diff().dt.days.fillna(1).shift(-1).fillna(1)
def rsi2(x):
    dd = x.diff(); up = dd.clip(lower=0).ewm(alpha=0.5, adjust=False).mean(); dn = (-dd.clip(upper=0)).ewm(alpha=0.5, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))
def strategies(d):
    out = {}; n = nights(d.index)
    # A turn of month
    mo = d.index.to_period("M"); pos_in_m = d.groupby(mo).cumcount(); from_end = d.groupby(mo).cumcount(ascending=False)
    hold = ((from_end <= 1) | (pos_in_m <= 2)).astype(float)  # held over close-to-close returns ending on these days
    entry = hold.diff().fillna(hold) > 0
    rA = hold * (d.c / d.c.shift(1) - 1) - entry * C1 - (hold.shift(-1).fillna(0) < hold) * C1 - hold * n.shift(1).fillna(1) * FIN
    out["A Turn-of-month"] = (rA.fillna(0), int(entry.sum()))
    # B intraday momentum
    sig = np.sign(d.c1000 / d.c.shift(1) - 1)
    rB = (sig * (d.c1559 / d.o1530 - 1) - 2 * C1 * (sig != 0)).fillna(0)
    out["B Intraday momentum"] = (rB, int((sig != 0).sum()))
    # C overnight drift (return booked on the next day)
    rC = (d.o / d.c.shift(1) - 1 - 2 * C1 - n.shift(1) * FIN).fillna(0)
    out["C Overnight drift"] = (rC, len(d))
    # D deep dip
    cl, op = d.c, d.o; sg = (cl > cl.rolling(200).mean()) & (rsi2(cl) < 5); s5 = cl.rolling(5).mean()
    r = pd.Series(0.0, index=d.index); held = False; age = 0; nt = 0
    for k in range(1, len(d)):
        if held:
            r.iloc[k] = cl.iloc[k] / cl.iloc[k-1] - 1 - n.iloc[k-1] * FIN; age += 1
            if cl.iloc[k] > s5.iloc[k] or age >= 10: r.iloc[k] -= C1; held = False
        elif sg.iloc[k-1]:
            r.iloc[k] = cl.iloc[k] / op.iloc[k] - 1 - C1; held = True; age = 1; nt += 1
            if cl.iloc[k] > s5.iloc[k]: r.iloc[k] -= C1; held = False
    out["D Deep-dip"] = (r, nt); return out
def sh(r, a, b):
    x = r[a:b]; return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0
res = {s: strategies(sess(load(s))) for s in ("SPXUSD", "NSXUSD")}
rows = []
for k in res["SPXUSD"]:
    for lab, r, nt in (("S&P", *res["SPXUSD"][k]), ("Nasdaq", *res["NSXUSD"][k]),
                       ("Pair", (res["SPXUSD"][k][0].add(res["NSXUSD"][k][0], fill_value=0)) / 2, res["SPXUSD"][k][1] + res["NSXUSD"][k][1])):
        a, b, c = sh(r, "2016", "2020"), sh(r, "2021", "2024"), sh(r, "2025", "2026")
        keep = a >= 0.3 and b > 0; rec = keep and c > 0
        rows.append(f"| {k} | {lab} | {nt} | {a:.2f} | {b:.2f} | {c:.2f} | {r['2016':].mean()*252:.1%} | {'RECOMMEND' if rec else ('keep, failed 2025-26' if keep else 'drop')} |")
        if lab == "Pair" or True: r.to_frame("r").to_csv(f"results/daytrade/2026-11-10/r14_{k[0]}_{lab}.csv")
tab = "| Strategy | Market | Trades | 2016-20 Sharpe | 2021-24 Sharpe | 2025-26 Sharpe | Avg return/yr (unlevered) | Verdict |\n|---|---|---|---|---|---|---|---|\n" + "\n".join(rows)
print(tab); open("results/daytrade/2026-11-10/round14_results.md", "w").write("# Round 14 results\n\nSee round14_preregistration.md.\n\n" + tab + "\n")
