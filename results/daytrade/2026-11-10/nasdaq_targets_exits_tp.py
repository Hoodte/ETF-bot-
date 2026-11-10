import sys, itertools
from datetime import datetime, timezone
import pandas as pd, numpy as np
sys.path.insert(0, ".")
import blocks, features
blocks.load_all(); features.load_all()
from backtester import CostConfig, run_backtest
from data.cache import read_bars
from research.materialize import materialize_pattern
from research.patterns import Pattern
df = read_bars("data/cache", "histdata", "NAS100", "M15", datetime(2016, 1, 1, tzinfo=timezone.utc), datetime(2026, 11, 1, tzinfo=timezone.utc)).reset_index(drop=True)
pat = Pattern(features=("rsi_overbought_70", "session_lunch"), direction=1)
def run(sm, tm, trail, flat, mult=1.0):
    st = materialize_pattern(pat, pair="NAS100", timeframe="M15", stop_atr_mult=sm, target_atr_mult=tm, trail=trail, flatten_at_local_time=flat)
    res = run_backtest(st, df, cost=CostConfig(spread_override=1.5 * mult, slippage_entry_ticks=1.0 * mult, slippage_stop_ticks=2.0 * mult))
    tr = pd.DataFrame([t.__dict__ for t in res.trades])
    tcol = [c for c in tr.columns if "entry" in c and ("time" in c or "ts" in c)][0]
    pcol = [c for c in tr.columns if c in ("pnl", "net_pnl", "pnl_net", "pnl_usd", "net_pnl_usd")][0]
    tr[tcol] = pd.to_datetime(tr[tcol], utc=True)
    out = {}
    for name, a, b in (("IS 16-21", "2016-01-01", "2021-05-31"), ("21-24", "2021-06-01", "2024-12-31"), ("25-26", "2025-01-01", "2026-10-30")):
        x = tr[(tr[tcol] >= pd.Timestamp(a, tz="UTC")) & (tr[tcol] <= pd.Timestamp(b, tz="UTC"))][pcol]
        days = pd.date_range(a, b, freq="B", tz="UTC")
        dp = tr[(tr[tcol] >= pd.Timestamp(a, tz="UTC")) & (tr[tcol] <= pd.Timestamp(b, tz="UTC"))].groupby(tr[tcol].dt.floor("D"))[pcol].sum().reindex(days, fill_value=0)
        w, l = x[x > 0], x[x < 0]
        out[name] = (dp.mean() / dp.std() * np.sqrt(252), (x > 0).mean(), w.mean() / -l.mean() if len(l) else np.nan, w.sum() / -l.sum() if len(l) else np.nan, x.sum())
    return out
rows = []
grid = [(1.0, tm, False, "15:55") for tm in (2.0, 2.5, 3.0, 3.5, 4.0)]
for g in grid:
    o = run(*g); rows.append((g, o))
    lab = f"stop {g[0]}ATR " + ("trail (runner)" if g[2] else f"target {g[1]}ATR") + ("" if g[3] else " overnight")
    print(f"{lab:32s} | IS Sh {o['IS 16-21'][0]:5.2f} | 21-24 Sh {o['21-24'][0]:5.2f} win {o['21-24'][1]:.0%} R:R 1:{o['21-24'][2]:.2f} PF {o['21-24'][3]:.2f} | 25-26 Sh {o['25-26'][0]:5.2f} win {o['25-26'][1]:.0%} R:R 1:{o['25-26'][2]:.2f} PF {o['25-26'][3]:.2f} ${o['25-26'][4]:,.0f}", flush=True)
best = max(rows, key=lambda r: r[1]["IS 16-21"][0])
print("PICKED ON 2016-21 ONLY:", best[0], {k: round(v[0], 2) for k, v in best[1].items()})
