import sys
from datetime import datetime, timezone
import pandas as pd, numpy as np
sys.path.insert(0, "."); sys.path.insert(0, "/home/claude/etf-bot-")
import blocks, features
blocks.load_all(); features.load_all()
from backtester import CostConfig, run_backtest
from data.cache import read_bars
from research.materialize import materialize_pattern
from research.patterns import Pattern
from etfbot.daytrade import evaluate as V
PAIR, SPREAD = "SPX500", 0.5
pat = Pattern(features=("rsi_overbought_70", "session_lunch"), direction=1)
for start, a, b, lab in ((datetime(2020, 12, 1, tzinfo=timezone.utc), "2021-01-01", "2024-12-31", "2021-24"),
                         (datetime(2024, 12, 1, tzinfo=timezone.utc), "2025-01-01", "2026-10-30", "2025-26")):
    df = read_bars("data/cache", "histdata", PAIR, "M15", start, datetime(2026, 11, 1, tzinfo=timezone.utc)).reset_index(drop=True)
    for tm in (3.0,):
        for mult in (1.0, 2.0):
            st = materialize_pattern(pat, pair=PAIR, timeframe="M15", stop_atr_mult=1.0, target_atr_mult=tm, risk_pct=1.0)
            res = run_backtest(st, df, cost=CostConfig(spread_override=SPREAD * mult, slippage_entry_ticks=1.0 * mult, slippage_stop_ticks=2.0 * mult))
            tr = pd.DataFrame([t.__dict__ for t in res.trades])
            tcol = [c for c in tr.columns if "entry" in c and ("time" in c or "ts" in c)][0]; pcol = [c for c in tr.columns if c in ("pnl", "net_pnl", "pnl_net", "pnl_usd", "net_pnl_usd")][0]
            tr[tcol] = pd.to_datetime(tr[tcol], utc=True); h = tr[(tr[tcol] >= pd.Timestamp(a, tz="UTC")) & (tr[tcol] <= pd.Timestamp(b, tz="UTC"))]
            # per-trade return as % of equity at the time (removes compounding), then fixed $100k
            eq_before = 100000 + tr[pcol].cumsum().shift(1).fillna(0)
            r = (tr[pcol] / eq_before).loc[h.index]
            days = pd.date_range(a, b, freq="B", tz="UTC")
            dret = r.groupby(h[tcol].dt.floor("D")).sum().reindex(days, fill_value=0)
            weeks = len(days) / 5
            usd = r * 100000
            wk = usd.groupby(h[tcol].dt.to_period("W")).sum().reindex(pd.period_range(a, b, freq="W"), fill_value=0)
            eq = 100000 + usd.cumsum()
            line = f"{lab} 1:{tm:g} cost x{mult:g}: trades {len(h)} ({len(h)/weeks:.1f}/wk), avg week ${usd.sum()/weeks:,.0f}, median week ${wk.median():,.0f}, best/worst week ${wk.max():,.0f}/${wk.min():,.0f}, % weeks positive {(wk>0).mean():.0%}, max DD {((eq/eq.cummax())-1).min():.1%}"
            if mult == 1.0:
                for risk in (0.5, 1.0):
                    k, med, avg = V.funded(dret * risk, 1.0)
                    line += f" | FTMO sim @{risk}% risk: keep {k:.0%}, avg ${avg*12/52*1:,.0f}/wk after 80% split"
            print(line, flush=True)
