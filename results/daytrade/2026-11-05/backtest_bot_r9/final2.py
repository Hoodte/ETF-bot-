exec(open("/tmp/bb/final_combo.py").read().split("for lab, start, a, b in")[0])
newsc = pd.read_csv("/home/claude/etf-bot-/results/daytrade/2026-11-05/round10b_trades.csv", parse_dates=["t"])
def news_daily_cost(a, b, dbps):        # shift every news trade's cost by dbps per side (2 sides)
    x = newsc[(newsc.t >= pd.Timestamp(a, tz="UTC")) & (newsc.t <= pd.Timestamp(b, tz="UTC") + pd.Timedelta(days=1))].copy()
    vol = x.raw / x.pnl; x["pnl"] = (x.raw - 2 * dbps / 1e4) / vol
    days = pd.date_range(a, b, freq="B", tz="UTC"); return x.groupby(x.t.dt.floor("D")).pnl.sum().reindex(days, fill_value=0)
for lab, start, a, b in (("2021-24", datetime(2020, 12, 1, tzinfo=timezone.utc), "2021-01-01", "2024-12-31"),
                         ("2025-26", datetime(2024, 12, 1, tzinfo=timezone.utc), "2025-01-01", "2026-10-30")):
    nd = nas_daily(start, a, b); wd = news_daily(a, b)
    print(f"\n== {lab}")
    for scale in (1.0, 1.25, 1.5, 2.0):
        d = (nd * 0.75 + wd * 0.0010) * scale
        k0, _, a0 = sim(d, False); k, med, avg = sim(d, True)
        print(f"  PLAN x{scale}: no rules keep {k0:.0%} avg ${a0:,.0f}/wk | WITH rules keep {k:.0%}, typical ${med:,.0f}, avg ${avg:,.0f}/wk")
    for dbps in (-0.5, 0.5):
        d = nd * 0.75 + news_daily_cost(a, b, dbps) * 0.0010
        k, med, avg = sim(d, True)
        print(f"  PLAN x1 with news costs {dbps:+.1f} bps/side: keep {k:.0%}, typical ${med:,.0f}, avg ${avg:,.0f}/wk")
