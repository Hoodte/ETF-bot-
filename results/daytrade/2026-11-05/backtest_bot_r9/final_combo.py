import sys
from datetime import datetime, timezone
import numpy as np, pandas as pd
exec(open("/tmp/bb/combo.py").read().split("for lab, start")[0])
def idx_daily(pair, spread, start, a, b):
    df = read_bars("data/cache", "histdata", pair, "M15", start, datetime(2026, 11, 1, tzinfo=timezone.utc)).reset_index(drop=True)
    st = materialize_pattern(pat, pair=pair, timeframe="M15", stop_atr_mult=1.0, target_atr_mult=3.0, risk_pct=1.0)
    res = run_backtest(st, df, cost=CostConfig(spread_override=spread, slippage_entry_ticks=1.0, slippage_stop_ticks=2.0))
    tr = pd.DataFrame([t.__dict__ for t in res.trades])
    tcol = [c for c in tr.columns if "entry" in c and ("time" in c or "ts" in c)][0]; pcol = [c for c in tr.columns if c in ("pnl", "net_pnl", "pnl_net", "pnl_usd", "net_pnl_usd")][0]
    tr[tcol] = pd.to_datetime(tr[tcol], utc=True); r = tr[pcol] / (100000 + tr[pcol].cumsum().shift(1).fillna(0))
    days = pd.date_range(a, b, freq="B", tz="UTC"); m = (tr[tcol] >= pd.Timestamp(a, tz="UTC")) & (tr[tcol] <= pd.Timestamp(b, tz="UTC"))
    return r[m].groupby(tr.loc[m, tcol].dt.floor("D")).sum().reindex(days, fill_value=0)
def news_event_daily(a, b):
    x = news[(news.t >= pd.Timestamp(a, tz="UTC")) & (news.t <= pd.Timestamp(b, tz="UTC") + pd.Timedelta(days=1))]
    ev = x.groupby("t").pnl.mean()                     # each release: total risk split equally across its instruments
    days = pd.date_range(a, b, freq="B", tz="UTC")
    return ev.groupby(ev.index.floor("D")).sum().reindex(days, fill_value=0)
def sim(d, rules, paths=10000, days=252, block=20, seed=5):
    base = d.to_numpy(); rng = np.random.default_rng(seed); nb = -(-days // block)
    ii = (rng.integers(0, len(base) - block, (paths, nb))[:, :, None] + np.arange(block)).reshape(paths, -1)[:, :days]
    R = base[ii]; eq = np.ones(paths); alive = np.ones(paths, bool)
    for t in range(days):
        r = R[:, t].copy()
        if rules:
            r = np.where(eq < 0.95, r * 0.5, r); r = np.maximum(r, -0.02)
        dead = r <= -0.05
        eq = np.where(alive, eq + r, eq); alive &= ~dead & (eq > 0.9)
    prof = np.where(alive, np.maximum(eq - 1, 0) * 100000 * 0.8, 0)
    return alive.mean(), np.median(prof) / 52, prof.mean() / 52
for lab, start, a, b in (("2021-24", datetime(2020, 12, 1, tzinfo=timezone.utc), "2021-01-01", "2024-12-31"),
                         ("2025-26", datetime(2024, 12, 1, tzinfo=timezone.utc), "2025-01-01", "2026-10-30")):
    nd = nas_daily(start, a, b); sd = idx_daily("SPX500", 0.5, start, a, b); wd = news_daily(a, b); we = news_event_daily(a, b)
    sh = lambda x: x.mean() / x.std() * np.sqrt(252)
    print(f"\n== {lab}: corr NAS/SPX {nd.corr(sd):.2f}, NAS/news {nd.corr(wd):.2f} | news Sharpe per-pair {sh(wd):.2f} vs per-release {sh(we):.2f}")
    combos = {
        "PLAN (middle): Nasdaq 0.75% + news per-pair 0.10": nd * 0.75 + wd * 0.0010,
        "+ per-release news sizing (same total risk)": nd * 0.75 + we * 0.0010 * wd.std() / we.std(),
        "+ S&P rule 0.5% (Nasdaq 0.5%)": nd * 0.5 + sd * 0.5 + we * 0.0010 * wd.std() / we.std(),
    }
    for name, d in combos.items():
        for rules in (False, True):
            k, med, avg = sim(d, rules)
            print(f"  {name:52s} {'+ FTMO risk rules' if rules else '                 '} | Sharpe {sh(d):.2f} | keep {k:.0%} | your share/wk typical ${med:,.0f}, avg ${avg:,.0f}")
    # push size with all improvements: find largest scale keeping >= 95%
    d0 = nd * 0.5 + sd * 0.5 + we * 0.0010 * wd.std() / we.std()
    for scale in (1.25, 1.5, 2.0):
        k, med, avg = sim(d0 * scale, True)
        print(f"  ALL improvements x{scale} size + rules                                      | keep {k:.0%} | your share/wk typical ${med:,.0f}, avg ${avg:,.0f}")
