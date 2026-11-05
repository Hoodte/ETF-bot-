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
pat = Pattern(features=("rsi_overbought_70", "session_lunch"), direction=1)
news = pd.read_csv("/home/claude/etf-bot-/results/daytrade/2026-11-05/round10b_trades.csv", parse_dates=["t"])
def nas_daily(start, a, b, mult=1.0):
    df = read_bars("data/cache", "histdata", "NAS100", "M15", start, datetime(2026, 11, 1, tzinfo=timezone.utc)).reset_index(drop=True)
    st = materialize_pattern(pat, pair="NAS100", timeframe="M15", stop_atr_mult=1.0, target_atr_mult=3.0, risk_pct=1.0)
    res = run_backtest(st, df, cost=CostConfig(spread_override=1.5 * mult, slippage_entry_ticks=1.0 * mult, slippage_stop_ticks=2.0 * mult))
    tr = pd.DataFrame([t.__dict__ for t in res.trades])
    tcol = [c for c in tr.columns if "entry" in c and ("time" in c or "ts" in c)][0]; pcol = [c for c in tr.columns if c in ("pnl", "net_pnl", "pnl_net", "pnl_usd", "net_pnl_usd")][0]
    tr[tcol] = pd.to_datetime(tr[tcol], utc=True)
    r = tr[pcol] / (100000 + tr[pcol].cumsum().shift(1).fillna(0))          # % of equity per trade at 1% risk
    days = pd.date_range(a, b, freq="B", tz="UTC")
    m = (tr[tcol] >= pd.Timestamp(a, tz="UTC")) & (tr[tcol] <= pd.Timestamp(b, tz="UTC"))
    return r[m].groupby(tr.loc[m, tcol].dt.floor("D")).sum().reindex(days, fill_value=0)
def news_daily(a, b):
    x = news[(news.t >= pd.Timestamp(a, tz="UTC")) & (news.t <= pd.Timestamp(b, tz="UTC") + pd.Timedelta(days=1))]
    days = pd.date_range(a, b, freq="B", tz="UTC")
    return x.groupby(x.t.dt.floor("D")).pnl.sum().reindex(days, fill_value=0)   # in daily-vol units per trade
for lab, start, a, b in (("2021-24", datetime(2020, 12, 1, tzinfo=timezone.utc), "2021-01-01", "2024-12-31"),
                         ("2025-26", datetime(2024, 12, 1, tzinfo=timezone.utc), "2025-01-01", "2026-10-30")):
    nd, wd = nas_daily(start, a, b), news_daily(a, b)
    print(f"\n== {lab}: daily correlation Nasdaq vs news = {nd.corr(wd):.2f}")
    rows = []
    for nas_risk in (0.0, 0.5, 0.75, 1.0):
        for news_risk in (0.0, 0.10, 0.15, 0.20, 0.25):          # % of account per 1 daily-vol unit per news trade
            if nas_risk == 0 and news_risk == 0: continue
            d = nd * nas_risk + wd * news_risk / 100
            k, med, avg = V.funded(d, 1.0)
            days = len(d); yrs = days / 261
            raw_wk = d.sum() * 100000 / (days / 5)
            eq = 1 + d.cumsum(); mdd = ((eq - eq.cummax())).min()
            rows.append((nas_risk, news_risk, k, med * 12 / 52, avg * 12 / 52, raw_wk, mdd, d.min()))
    for r in rows:
        print(f"  Nasdaq {r[0]:.2f}% risk + news {r[1]:.2f}%/unit: keep {r[2]:.0%} | your share/wk: typical ${r[3]:,.0f}, avg ${r[4]:,.0f} | gross avg ${r[5]:,.0f}/wk | worst DD {r[6]:.1%}, worst day {r[7]:.1%}")
