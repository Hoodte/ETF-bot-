"""Replicates user's 'NY ORB - FTMO v5' Pine strategy on NSXUSD 5m (HistData, UTC) 2016-2026.
Rules copied from the script defaults; fills at signal-bar close (process_orders_on_close), stop exits intrabar.
Reports R-multiples and $ on $100k (1% risk, 10-unit cap at $1/pt as in the script, and uncapped 1% risk)."""
import numpy as np, pandas as pd
df = pd.read_pickle("data/histdata/NSXUSD_5m.pkl"); df = df[~df.index.duplicated()].sort_index()
ny = df.index.tz_convert("America/New_York"); df["d"] = ny.date; df["mins"] = ny.hour * 60 + ny.minute
# daily (NY 16:00 close) series for prev close + ATR14 (previous days only)
rth = df[(df.mins >= 570) & (df.mins < 960)]
day = rth.groupby("d").agg(o=("Open", "first"), h=("High", "max"), l=("Low", "min"), c=("Close", "last"))
tr = pd.concat([day.h - day.l, (day.h - day.c.shift()).abs(), (day.l - day.c.shift()).abs()], axis=1).max(axis=1)
datr = tr.ewm(alpha=1/14, adjust=False).mean().shift(1); pclose = day.c.shift(1)
# 5m ATR14 (Wilder) on chart
h, l, c = df.High, df.Low, df.Close
tr5 = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
df["atr"] = tr5.ewm(alpha=1/14, adjust=False).mean()

def run(atr_mult=2.0, cost_pts=0.0, band=True, body=True, gap=True, end_min=720):
    trades = []
    for d, g in df.groupby("d"):
        if d not in datr.index or np.isnan(datr.get(d, np.nan)): continue
        orb = g[(g.mins >= 570) & (g.mins < 585)]
        if len(orb) < 3: continue
        orh, orl = orb.High.max(), orb.Low.min(); rng = orh - orl
        if rng <= 0: continue
        if band and not (0.25 * datr[d] <= rng <= 0.80 * datr[d]): continue
        pc = pclose[d]
        G = g[g.mins >= 585]; O, H, L, C, A, M = (G[k].to_numpy() for k in ("Open", "High", "Low", "Close", "atr", "mins"))
        pos = 0; took = {1: False, -1: False}
        for i in range(len(G)):
            if pos != 0:
                # stop check (levels set at previous bar close)
                stp = max(sl, trail) if pos == 1 else min(sl, trail)
                hit = (L[i] <= stp) if pos == 1 else (H[i] >= stp)
                if hit:
                    px = min(O[i], stp) if pos == 1 else max(O[i], stp)
                    trades.append((d, pos, (px - ep) * pos / risk - cost_pts / risk, risk)); pos = 0
                else:
                    if M[i] >= 955:  # 15:55 bar -> flat at close
                        trades.append((d, pos, (C[i] - ep) * pos / risk - cost_pts / risk, risk)); pos = 0; continue
                    ext = max(ext, H[i]) if pos == 1 else min(ext, L[i])
                    if not armed and ((H[i] >= ep + risk) if pos == 1 else (L[i] <= ep - risk)): armed = True
                    if armed:
                        td = atr_mult * A[i]
                        if not active and abs(ext - ep) >= td: active = True
                        if active: trail = (ext - td) if pos == 1 else (ext + td)
                    continue
            if pos == 0 and 585 <= M[i] < end_min:
                br = H[i] - L[i]; bok = (not body) or (br > 0 and abs(C[i] - O[i]) / br >= 0.60)
                for side in (1, -1):
                    if took[side] or not bok: continue
                    brk = C[i] > orh if side == 1 else C[i] < orl
                    gp = (not gap) or (O[i] > pc if side == 1 else O[i] < pc)
                    if brk and gp:
                        ep = C[i]; sl = orl - 0.05 * rng if side == 1 else orh + 0.05 * rng
                        risk = abs(ep - sl); pos = side; took[side] = True; armed = active = False
                        ext = ep; trail = -1e18 if side == 1 else 1e18; break
        if pos != 0:
            trades.append((d, pos, (C[-1] - ep) * pos / risk - cost_pts / risk, risk))
    return pd.DataFrame(trades, columns=["d", "side", "R", "risk_pts"])

def summ(t, label):
    t = t.copy(); t["d"] = pd.to_datetime(t.d); t["yr"] = t.d.dt.year
    def s(x):
        if len(x) == 0: return "n/a"
        pf = x.R[x.R > 0].sum() / -x.R[x.R < 0].sum()
        return f"{len(x)} tr, win {(x.R>0).mean():.0%}, avg {x.R.mean():+.3f}R, PF {pf:.2f}, total {x.R.sum():+.0f}R"
    yrs = (t.groupby("yr").R.sum()).round(1).to_dict()
    # $ on 100k: 1% risk uncapped => $1000 per R; capped 10 units @ $1/pt => min(1000, 10*risk_pts) per R
    capped = (t.R * np.minimum(1000, 10 * t.risk_pts)).sum() / 10.8
    print(f"\n## {label}\nALL     : {s(t)}\n2016-20 : {s(t[t.yr<=2020])}\n2021-24 : {s(t[(t.yr>=2021)&(t.yr<=2024)])}\n2025-26 : {s(t[t.yr>=2025])}")
    print(f"per-year R: {yrs}\n$ per year on 100k: uncapped 1% risk {t.R.sum()*1000/10.8:,.0f}; script's 10-unit cap {capped:,.0f}")

base = run(cost_pts=0.0); summ(base, "v5 defaults, TradingView costs (~0)")
summ(run(cost_pts=2.0), "v5 defaults, realistic FTMO cost 2 pts round trip")
for m in (1.5, 2.5, 3.0): summ(run(atr_mult=m, cost_pts=2.0), f"plateau: trail {m} x ATR, 2 pt cost")
summ(run(cost_pts=2.0, end_min=660), "tight window 09:45-11:00, 2 pt cost")
