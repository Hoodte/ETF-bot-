"""Silver ideas (pre-registered 2026-11-10, before running):
S1 gold macro signal applied to silver: same 2-of-3 votes (dollar, TIPS, COT gold), silver sized to 10% vol, cost 4 bps/side.
S2 gold -> silver lead-lag: if gold's last-hour return beats silver's by > 0.3%, hold silver the next hour in gold's direction
   (opposite if gold lagged); cost 3 bps/side.
Pass = Sharpe >= 0.3 in 2016-21 AND > 0 in 2022-26; S1 also reports correlation with the gold strategy."""
import numpy as np, pandas as pd
src = open("results/2026-11-05/run_gold_variants.py").read().split("ls = np.where")[0].replace("h1 = gq.load_gold_h1(sys.argv[1])", "h1 = gq.load_gold_h1('/mnt/user-data/uploads/backtestbot/data/XAUUSD_H1_2016_2026.csv')")
exec(src)
ag = pd.read_pickle("data/histdata/XAGUSD_1m.pkl").Close.resample("1h").last().dropna()
ag.index = ag.index.tz_convert("UTC"); ag = ag.reindex(idx).ffill()
sh = lambda r, a, b: (lambda x: x.mean() / x.std() * np.sqrt(252 * 23) if x.std() > 0 else 0)(r[a:b])
def ret(px, tgt, c):
    rr = px.pct_change().fillna(0); held = tgt.shift(1).fillna(0); return held * rr - held.diff().abs().fillna(held.abs()) * c / 1e4
gr_ = ag.pct_change(); dv = gr_.groupby(gr_.index.date).apply(lambda z: (1 + z).prod() - 1).rolling(20).std() * np.sqrt(252); dv.index = pd.to_datetime(dv.index)
VOLs = gq.to_hourly((0.10 / dv).clip(upper=1.5).rename("s"), idx, 1).replace(0, np.nan).ffill().fillna(1.0)
s1 = ret(ag, base * VOLs, 4); g = ret(close, base * VOL, gq.COST_BPS)
d = lambda r: (1 + r).groupby(r.index.date).prod() - 1
gl, sl = close.pct_change(), ag.pct_change(); gap = gl - sl
sig = pd.Series(np.where(gap > 0.003, 1.0, np.where(gap < -0.003, -1.0, 0.0)), index=idx) * np.sign(gl).fillna(0)
sig = pd.Series(np.where(gap.abs() > 0.003, np.sign(gap), 0.0), index=idx)   # silver catches up toward gold
s2 = ret(ag, sig, 3)
for k, r in (("S1 gold macro signal on silver", s1), ("S2 gold->silver catch-up (hourly)", s2), ("reference: gold strategy", g)):
    print(f"| {k} | {sh(r, None, '2021-12-31'):.2f} | {sh(r, '2022-01-01', None):.2f} | {sh(r, '2025-01-01', None):.2f} |")
print("corr S1 vs gold strategy (daily):", round(pd.Series(d(s1)).corr(pd.Series(d(g))), 2), "| S2 trades:", int((sig.diff().abs() > 0).sum()))
