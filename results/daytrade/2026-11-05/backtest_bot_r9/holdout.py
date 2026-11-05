"""Test a backtest-bot discovered pattern, frozen, on the untouched 2025-01..2026-10 holdout."""
import sys
from datetime import datetime, timezone
import pandas as pd, numpy as np
sys.path.insert(0, ".")
import blocks, features  # noqa: F401
blocks.load_all()
if hasattr(features, "load_all"): features.load_all()
from backtester import CostConfig, run_backtest
from data.cache import read_bars
from research.materialize import materialize_pattern
from research.patterns import Pattern
pair, tf, feats, direction, spread = sys.argv[1], sys.argv[2], tuple(sys.argv[3].split("+")), int(sys.argv[4]), float(sys.argv[5])
df = read_bars("data/cache", "histdata", pair, tf, datetime(2024, 9, 1, tzinfo=timezone.utc), datetime(2026, 11, 1, tzinfo=timezone.utc))
strat = materialize_pattern(Pattern(features=feats, direction=direction), pair=pair, timeframe=tf, risk_pct=1.0, stop_atr_mult=1.0, target_atr_mult=2.0)
for mult in (1.0, 2.0):
    cost = CostConfig(spread_override=spread * mult, slippage_entry_ticks=1.0 * mult, slippage_stop_ticks=2.0 * mult)
    res = run_backtest(strat, df.reset_index(drop=True), cost=cost)
    tr = pd.DataFrame([t.__dict__ if hasattr(t, "__dict__") else t for t in res.trades])
    tcol = [c for c in tr.columns if "entry" in c and ("time" in c or "ts" in c)][0]
    pcol = [c for c in tr.columns if c in ("pnl", "net_pnl", "pnl_net", "pnl_usd", "net_pnl_usd")][0]
    tr[tcol] = pd.to_datetime(tr[tcol], utc=True)
    h = tr[tr[tcol] >= pd.Timestamp("2025-01-01", tz="UTC")]
    pnl = h[pcol]
    days = pd.date_range("2025-01-01", "2026-10-30", freq="B", tz="UTC")
    dp = h.groupby(h[tcol].dt.floor("D"))[pcol].sum().reindex(days, fill_value=0)
    eq = 100000 + dp.cumsum()
    print(f"{pair} {tf} {'+'.join(feats)} dir={direction} cost x{mult}: holdout trades {len(h)}, win {(pnl>0).mean():.0%}, "
          f"PF {pnl[pnl>0].sum()/max(-pnl[pnl<0].sum(),1e-9):.2f}, net ${pnl.sum():,.0f}, Sharpe {dp.mean()/dp.std()*np.sqrt(252):.2f}, "
          f"max DD {((eq/eq.cummax())-1).min():.1%}")
