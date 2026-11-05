_s = open("/tmp/bb/final3.py").read(); exec(_s[:_s.rindex("for lab, start, a, b in")])
# --- candidate A: BTC 200-day trend, vol-targeted 10%, cost 10 bps/side, financing 15%/yr on exposure
btc = pd.read_pickle("/home/claude/etf-bot-/data/crypto_h1/BTCUSDT_1h.pkl").Close
btc = btc.resample("1D").last().dropna(); btc.index = btc.index.tz_convert("UTC") if btc.index.tz else btc.index.tz_localize("UTC")
br = btc.pct_change()
on = (btc > btc.rolling(200).mean()).astype(float)
sc = (0.10 / (br.rolling(20).std() * np.sqrt(365))).clip(upper=1.5)
pos = (on * sc).shift(1).fillna(0)
btc_d = pos * br - pos.diff().abs().fillna(0) * 10 / 1e4 - pos * 0.15 / 365
# --- candidate B: 9-market 12-month time-series momentum, each 10%/sqrt(9) vol target, cost 1 bp/side, swap 2%/yr
mk = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "NSXUSD", "SPXUSD", "GRXEUR"]
legs = []
for m in mk:
    c = pd.read_pickle(f"/home/claude/etf-bot-/data/histdata/{m}_1h.pkl").Close.resample("1D").last().dropna()
    r = c.pct_change(); sig = np.sign(c / c.shift(252) - 1)
    s = (0.10 / 3 / (r.rolling(60).std() * np.sqrt(252))).clip(upper=2.0)
    p = (sig * s).shift(1).fillna(0)
    legs.append((p * r - p.diff().abs().fillna(0) * 1 / 1e4 - p.abs() * 0.02 / 252).rename(m))
tsm_d = pd.concat(legs, axis=1).fillna(0).sum(axis=1)
tsm_d.index = tsm_d.index.tz_convert("UTC") if tsm_d.index.tz else tsm_d.index.tz_localize("UTC")
sh = lambda x: x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0
for lab, start, a, b in (("2021-24", datetime(2020, 12, 1, tzinfo=timezone.utc), "2021-01-01", "2024-12-31"),
                         ("2025-26", datetime(2024, 12, 1, tzinfo=timezone.utc), "2025-01-01", "2026-10-30")):
    nd = nas_daily(start, a, b); wd = news_daily(a, b); days = pd.date_range(a, b, freq="B", tz="UTC")
    gd = gold_d.reindex(days).fillna(0)
    bd = btc_d.reindex(pd.date_range(a, b, freq="D", tz="UTC")).fillna(0)
    bd = bd.groupby(bd.index.to_period("W-FRI").start_time.tz_localize("UTC") + pd.Timedelta(days=4)).sum().reindex(days).fillna(0) if False else bd.resample("B").sum().reindex(days).fillna(0)  # weekend P&L lands on Monday
    td = tsm_d.reindex(days).fillna(0)
    plan = (nd * 0.75 + wd * 0.0010) * 1.5 + gd * 0.75
    print(f"\n== {lab}: plan Sharpe {sh(plan):.2f} | BTC trend Sharpe {sh(bd):.2f} corr {bd.corr(plan):.2f} | multi-market trend Sharpe {sh(td):.2f} corr {td.corr(plan):.2f}")
    base = sim(plan, True); print(f"  plan (3 strategies): keep {base[0]:.0%}, typical ${base[1]:,.0f}, avg ${base[2]:,.0f}/wk")
    for name, x in (("BTC trend", bd), ("multi-market trend", td)):
        for w in (0.25, 0.5, 1.0):
            k, med, avg = sim(plan + x * w, True)
            print(f"  + {name} x{w}: Sharpe {sh(plan + x*w):.2f} | keep {k:.0%}, typical ${med:,.0f}, avg ${avg:,.0f}/wk")
