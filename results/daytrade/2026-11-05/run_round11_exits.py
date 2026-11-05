"""Round 11: exit variants for the news-surprise strategy. Entries frozen (5 min after release, |z|>0.5, follow).
Exits chosen on 2016-2020 only; 2021-24 and 2025-26 reported (2025-26 was seen once before for the baseline exit only)."""
import itertools, json
import numba as nb
import numpy as np, pandas as pd
exec(open("results/daytrade/2026-11-05/run_round10b.py").read().split('src = open')[0])   # builds `cal` from TradingView
INST = {"EURUSD": ("USD", -1, 1.2), "GBPUSD": ("USD", -1, 1.6), "AUDUSD": ("USD", -1, 1.6), "USDJPY": ("USD", 1, 1.4),
        "USDCAD": (None, 1, 1.6), "XAUUSD": ("USD", -1, 2.0)}
px = {}
for s in INST:
    m = pd.read_pickle(f"data/histdata/{s}_1m.pkl")
    dv = m.Close.resample("1D").last().dropna().pct_change().rolling(20).std().shift(1)
    px[s] = (m.index.as_unit("ns").asi8, m.Open.to_numpy(), m.High.to_numpy(), m.Low.to_numpy(), m.Close.to_numpy(), dv)

@nb.njit(cache=True)
def path_exit(o, h, l, c, i, d, risk, kind, a, b, maxbars):
    """Returns gross return (fraction) for a trade entered at o[i] in direction d.
    risk = price distance of 1R. kind: 0 time, 1 fixed SL/TP (a*R stop, b*R target), 2 trailing stop a*R,
    3 breakeven at 1R then time, 4 half at 1R + runner trailing a*R (stop a*R initially)."""
    e = o[i]; stop = e - d * a * risk; tgt = e + d * b * risk
    best = e; half_done = False; booked = 0.0; frac = 1.0; be = False
    for j in range(i, min(i + maxbars, len(c))):
        hi, lo = h[j], l[j]
        if kind == 0:
            pass
        else:
            adverse = lo if d == 1 else hi
            fav = hi if d == 1 else lo
            # stop first (conservative)
            if (d == 1 and adverse <= stop) or (d == -1 and adverse >= stop):
                px_ = stop if j > i else stop
                return booked + frac * d * (px_ / e - 1)
            if kind == 1 and ((d == 1 and fav >= tgt) or (d == -1 and fav <= tgt)):
                return booked + frac * d * (tgt / e - 1)
            if kind == 3 and not be and ((d == 1 and fav >= e + risk) or (d == -1 and fav <= e - risk)):
                stop = e; be = True
            if kind == 4 and not half_done and ((d == 1 and fav >= e + risk) or (d == -1 and fav <= e - risk)):
                booked += 0.5 * d * ((e + d * risk) / e - 1); frac = 0.5; half_done = True
                stop = e
            if kind in (2, 4):
                if (d == 1 and fav > best) or (d == -1 and fav < best):
                    best = fav
                trail = best - d * a * risk
                if kind == 2 or half_done:
                    if (d == 1 and trail > stop) or (d == -1 and trail < stop):
                        stop = trail
    j = min(i + maxbars, len(c)) - 1
    return booked + frac * d * (c[j] / e - 1)

def trades(kind, a, b, maxbars, risk_dv, cmult=1.0):
    rows = []
    for _, e in cal[cal.z.abs() > 0.5].iterrows():
        for s, (cur, orient, cost) in INST.items():
            if e.Currency == "CAD":
                if s != "USDCAD": continue
                d = -int(np.sign(e.z))
            else:
                d = int(np.sign(e.z)) if s == "USDCAD" else int(orient * np.sign(e.z))
            t, o, h, l, c, dv = px[s]
            t0 = (e.t_utc + pd.Timedelta(minutes=5)).value
            i = np.searchsorted(t, t0)
            if i >= len(t) or t[i] - t0 > 120e9: continue
            vol = dv.asof(e.t_utc.floor("D"))
            if not vol or np.isnan(vol): continue
            risk = risk_dv * vol * o[i]
            r = path_exit(o, h, l, c, i, d, risk, kind, a, b, maxbars) - 2 * cost * cmult / 1e4
            rows.append((e.t_utc, s, r / vol, r))
    return pd.DataFrame(rows, columns=["t", "inst", "pnl", "raw"])

def stats(tr, a, b):
    x = tr[(tr.t >= pd.Timestamp(a, tz="UTC")) & (tr.t <= pd.Timestamp(b, tz="UTC") + pd.Timedelta(days=1))]
    days = pd.date_range(a, b, freq="B", tz="UTC")
    dp = x.groupby(x.t.dt.floor("D")).pnl.sum().reindex(days, fill_value=0)
    w, lo = x.raw[x.raw > 0], x.raw[x.raw < 0]
    return {"sharpe": dp.mean() / dp.std() * np.sqrt(252), "win": (x.raw > 0).mean(), "rr": w.mean() / -lo.mean(),
            "pf": w.sum() / -lo.sum(), "avg_bps": x.raw.mean() * 1e4}

V = [("baseline: 60-min time exit", 0, 0, 0, 60, 0.25)]
for sl, rr in itertools.product([0.15, 0.25, 0.40], [1.0, 2.0, 3.0]):
    V.append((f"fixed SL {sl} dvol, TP 1:{rr:g}, max 4h", 1, 1.0, rr, 240, sl))
for tr_ in (0.15, 0.25, 0.40):
    V.append((f"trailing stop {tr_} dvol, max 4h", 2, 1.0, 0, 240, tr_))
for sl in (0.15, 0.25, 0.40):
    V.append((f"breakeven at 1R (R={sl} dvol), exit 60 min", 3, 1.0, 0, 60, sl))
    V.append((f"breakeven at 1R (R={sl} dvol), exit 4h", 3, 1.0, 0, 240, sl))
    V.append((f"half off at 1R + runner trailing 1R (R={sl} dvol), max 4h", 4, 1.0, 0, 240, sl))
res = []
for name, kind, a, b, mb, rdv in V:
    tr = trades(kind, a, b, mb, rdv)
    res.append((name, (kind, a, b, mb, rdv), stats(tr, "2016-01-01", "2020-12-31"), stats(tr, "2021-01-01", "2024-12-31"), stats(tr, "2025-01-01", "2026-10-30")))
    print(f"{name:55s} | 2016-20 Sh {res[-1][2]['sharpe']:5.2f} | 2021-24 Sh {res[-1][3]['sharpe']:5.2f} win {res[-1][3]['win']:.0%} R:R 1:{res[-1][3]['rr']:.2f} PF {res[-1][3]['pf']:.2f} | 2025-26 Sh {res[-1][4]['sharpe']:5.2f} win {res[-1][4]['win']:.0%} R:R 1:{res[-1][4]['rr']:.2f} PF {res[-1][4]['pf']:.2f} avg {res[-1][4]['avg_bps']:.1f}bps", flush=True)
best = max(res[1:], key=lambda r: r[2]["sharpe"])
print(f"\nPICKED ON 2016-20 ONLY: {best[0]} -> 2021-24 Sharpe {best[3]['sharpe']:.2f}, 2025-26 Sharpe {best[4]['sharpe']:.2f}")
tr2 = trades(*best[1], cmult=2.0)
print(f"   at 2x costs: 2021-24 {stats(tr2,'2021-01-01','2024-12-31')['sharpe']:.2f}, 2025-26 {stats(tr2,'2025-01-01','2026-10-30')['sharpe']:.2f}")
json.dump([(r[0], r[2], r[3], r[4]) for r in res], open("results/daytrade/2026-11-05/round11_exits.json", "w"), indent=1, default=float)
