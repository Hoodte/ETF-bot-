"""Pre-registered 2026-11-08: replace TIP ETF vote with FRED DFII10 (10y real yield) 20-day change < 0,
lag 1 day. F1 = MT5 dollar index + DFII10 + COT (the all-in-one EA version). Pass = 2025-26 Sharpe >= 0.8x original
and 2x-cost return > 0."""
import numpy as np, pandas as pd
src = open("results/2026-11-08/run_gold_mt5_inputs.py").read().split("V = {")[0]
exec(src)
ry = pd.read_csv("/tmp/dfii10.csv", index_col=0, parse_dates=True)["DFII10"].pipe(pd.to_numeric, errors="coerce").dropna()
F = H((ry.diff(20) < 0).astype(float))
print("TIP vote vs real-yield vote agree:", f"{(F == B).mean():.0%}")
V = {"G0 original (DXY,TIP,COT)": (A0+B+C >= 2), "F1 MT5-DXY,FRED real yield,COT": (A1+F+C >= 2),
     "F2 Yahoo DXY,FRED real yield,COT": (A0+F+C >= 2)}
exec("V = V\n" + open("results/2026-11-08/run_gold_mt5_inputs.py").read().split("V = {")[1].split("\n", 2)[2]
     .replace("gold_mt5_inputs_results.md", "gold_fred_results.md"))
