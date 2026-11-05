exec(open("/tmp/bb/final_combo.py").read().split("for lab, start, a, b in")[0])
import warnings; warnings.filterwarnings("ignore")
from etfbot import goldquant as gq
h1 = gq.load_gold_h1("/mnt/user-data/uploads/backtestbot/data/XAUUSD_H1_2016_2026.csv"); dly = gq.load_daily(cache="/home/claude/etf-bot-/data"); cot = gq.load_cot()
tgt = gq.build("macro_composite_vol10", h1, dly, cot)
r = gq.returns(h1, tgt, gq.COST_BPS)
held = tgt.shift(1).fillna(0).abs()
gday = (1 + r).groupby(r.index.floor("D")).prod() - 1
swap = held.groupby(held.index.floor("D")).mean() * 0.02 / 252
gold_d = (gday - swap.reindex(gday.index).fillna(0))
gold_d.index = pd.DatetimeIndex(gold_d.index).tz_convert("UTC") if gold_d.index.tz else pd.DatetimeIndex(gold_d.index).tz_localize("UTC")
for lab, start, a, b in (("2021-24", datetime(2020, 12, 1, tzinfo=timezone.utc), "2021-01-01", "2024-12-31"),
                         ("2025-26", datetime(2024, 12, 1, tzinfo=timezone.utc), "2025-01-01", "2026-10-30")):
    nd = nas_daily(start, a, b); wd = news_daily(a, b)
    days = pd.date_range(a, b, freq="B", tz="UTC")
    gd = gold_d.reindex(days).fillna(0)
    plan = (nd * 0.75 + wd * 0.0010) * 1.5
    sh = lambda x: x.mean() / x.std() * np.sqrt(252)
    print(f"\n== {lab}: gold strategy Sharpe {sh(gd):.2f}, corr with plan {gd.corr(plan):.2f}, plan Sharpe {sh(plan):.2f}")
    for g in (0.0, 0.25, 0.5, 0.75, 1.0):
        d = plan + gd * g
        k, med, avg = sim(d, True)
        print(f"  plan x1.5 + gold {g:.2f}x: Sharpe {sh(d):.2f} | keep {k:.0%} | your share/wk typical ${med:,.0f}, avg ${avg:,.0f}")
    for g in (0.5, 0.75):
        for scale in (1.75, 2.0):
            d = (nd * 0.75 + wd * 0.0010) * scale + gd * g
            k, med, avg = sim(d, True)
            print(f"  plan x{scale} + gold {g:.2f}x: Sharpe {sh(d):.2f} | keep {k:.0%} | your share/wk typical ${med:,.0f}, avg ${avg:,.0f}")
