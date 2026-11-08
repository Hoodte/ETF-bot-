"""Gold vol10 rebuilt with inputs an MT5 EA can see (pre-registered 2026-11-08, before running):
G0 original (Yahoo DXY, TIP, COT)            - reference
G1 MT5 DXY (from EURUSD/USDJPY/GBPUSD/USDCAD) + TIP + COT
G2 MT5 DXY + COT, 2 of 2 (TIP dropped)
G3 MT5 DXY + gold own trend (close > SMA100) + COT, 2 of 3
G4 MT5 DXY + gold own trend, 2 of 2 (no outside data at all)
Pass = 2025-26 Sharpe >= 0.8 x G0's and full-period 2x-cost return > 0. All use vol10 sizing."""
import sys, numpy as np, pandas as pd
from etfbot import goldquant as gq
h1 = gq.load_gold_h1("/mnt/user-data/uploads/backtestbot/data/XAUUSD_H1_2016_2026.csv")
d = gq.load_daily(); cot = gq.load_cot(); idx, close = h1.index, h1["Close"]
def dclose(p):
    s = pd.read_pickle(f"data/histdata/{p}_1h.pkl"); s = s["Close"] if "Close" in s else s["close"]
    s.index = pd.to_datetime(s.index, utc=True); s = s.groupby(s.index.date).last(); s.index = pd.to_datetime(s.index); return s
fx = pd.concat({p: dclose(p) for p in ["EURUSD", "USDJPY", "GBPUSD", "USDCAD"]}, axis=1).dropna()
mdxy = fx.EURUSD**-0.576 * fx.USDJPY**0.136 * fx.GBPUSD**-0.119 * fx.USDCAD**0.091
gdl = close.groupby(close.index.date).last(); gdl.index = pd.to_datetime(gdl.index)
H = lambda s, lag=1: gq.to_hourly(s, idx, lag)
A0 = H((d["DXY"] < d["DXY"].rolling(50).mean()).astype(float))
A1 = H((mdxy < mdxy.rolling(50).mean()).astype(float))
B = H((d["TIPS"].pct_change(20) > 0).astype(float))
pct = cot.rolling(156, min_periods=52).apply(lambda z: (z[:-1] < z[-1]).mean(), raw=True)
C = H((pct < 0.70).astype(float).where(pct.notna(), 0.0), 6)
T = H((gdl > gdl.rolling(100).mean()).astype(float))
gr = close.pct_change()
dv = gr.groupby(gr.index.date).apply(lambda z: (1 + z).prod() - 1).rolling(20).std() * np.sqrt(252); dv.index = pd.to_datetime(dv.index)
VOL = H((0.10 / dv).clip(upper=1.5).rename("s")).replace(0, np.nan).ffill().fillna(1.0)
V = {"G0 original (DXY,TIP,COT)": (A0+B+C >= 2), "G1 MT5-DXY,TIP,COT": (A1+B+C >= 2), "G2 MT5-DXY+COT 2of2": (A1+C >= 2),
     "G3 MT5-DXY,trend,COT": (A1+T+C >= 2), "G4 MT5-DXY+trend (pure MT5)": (A1+T >= 2)}
def daily(r): s = (1+r).groupby(r.index.date).prod()-1; s.index = pd.to_datetime(s.index); return s
base_pos = V["G0 original (DXY,TIP,COT)"].astype(float)
rows = []; ref = None
for k, sig in V.items():
    tgt = sig.astype(float) * VOL; r = gq.returns(h1, tgt, gq.COST_BPS); r2 = gq.returns(h1, tgt, 2*gq.COST_BPS)
    s = lambda a, b=None: gq.metrics(r[a:b])
    h = s("2025-01-01"); ref = ref or h["sharpe"]
    rows.append((k, s(None, "2020-12-31")["sharpe"], s("2021-01-01", "2024-12-31")["sharpe"], h["sharpe"], h["cagr"], gq.metrics(r)["max_dd"],
                 gq.metrics(r)["cagr"], gq.metrics(r2)["cagr"], (sig.astype(float) == base_pos).mean(),
                 daily(r).corr(daily(gq.returns(h1, base_pos*VOL, gq.COST_BPS))), tgt.diff().abs().gt(0.05).sum()/10.8))
out = ["| Variant | 2016-20 Sharpe | 2021-24 Sharpe | 2025-26 Sharpe | 2025-26 %/yr | Worst drop | Full %/yr | 2x cost %/yr | Same position as original | Return corr | Pass |", "|"+"---|"*11]
for k,a,b,c,cg,dd,fc,f2,same,cor,_ in rows:
    out.append(f"| {k} | {a:.2f} | {b:.2f} | {c:.2f} | {cg:.1%} | {dd:.1%} | {fc:.1%} | {f2:.1%} | {same:.0%} | {cor:.2f} | {'yes' if (c >= 0.8*ref and f2 > 0) else 'no'} |")
print("\n".join(out)); open("results/2026-11-08/gold_mt5_inputs_results.md","w").write("# Gold with MT5-only inputs\n\n"+__doc__+"\n\n"+"\n".join(out)+"\n")
