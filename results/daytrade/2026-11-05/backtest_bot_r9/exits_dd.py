exec(open("/tmp/bb/exits.py").read().split("rows = []")[0])
def dd(sm, tm, trail, flat, mult=1.0):
    st = materialize_pattern(pat, pair="NAS100", timeframe="M15", stop_atr_mult=sm, target_atr_mult=tm, trail=trail, flatten_at_local_time=flat)
    res = run_backtest(st, df, cost=CostConfig(spread_override=1.5 * mult, slippage_entry_ticks=1.0 * mult, slippage_stop_ticks=2.0 * mult))
    tr = pd.DataFrame([t.__dict__ for t in res.trades])
    tcol = [c for c in tr.columns if "entry" in c and ("time" in c or "ts" in c)][0]; pcol = [c for c in tr.columns if c in ("pnl", "net_pnl", "pnl_net", "pnl_usd", "net_pnl_usd")][0]
    tr[tcol] = pd.to_datetime(tr[tcol], utc=True); h = tr[tr[tcol] >= pd.Timestamp("2025-01-01", tz="UTC")]
    eq = 100000 + h[pcol].cumsum(); worst_day = h.groupby(h[tcol].dt.floor("D"))[pcol].sum().min()
    print(f"stop {sm} target {tm} {'overnight' if flat is None else 'flat 15:55'} x{mult}: 2025-26 trades {len(h)}, net ${h[pcol].sum():,.0f}, max DD {((eq/eq.cummax())-1).min():.1%}, worst day ${worst_day:,.0f}")
for g in ((1.0, 2.0, False, "15:55"), (1.0, 3.0, False, "15:55"), (1.0, 3.0, False, None)):
    dd(*g); dd(*g, mult=2.0)
