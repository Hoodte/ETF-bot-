"""Weekly profit cap on the full plan (written 2026-11-12 before running): once the week's P&L reaches +X%,
stop all trading (incl. gold) until the next Monday. News 0.15% equity per unit, Nasdaq 1.1% per R, gold research returns x0.75."""
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
BD = pd.bdate_range("2016-01-01", "2026-10-30")
nw = pd.read_csv("results/daytrade/2026-11-05/round10b_trades.csv"); nw["d"] = pd.to_datetime(nw.t, utc=True).dt.tz_convert(None).dt.normalize()
news = nw.groupby("d").pnl.sum().reindex(BD, fill_value=0) * 0.0015
nt = pd.read_csv("/tmp/nas_trades.csv"); nt["d"] = pd.to_datetime(nt.entry_ts, utc=True).dt.tz_convert(None).dt.normalize()
nas = nt.groupby("d").r_multiple.sum().reindex(BD, fill_value=0) * 0.011
src = open("results/2026-11-05/run_gold_variants.py").read().split("ls = np.where")[0].replace("h1 = gq.load_gold_h1(sys.argv[1])", "h1 = gq.load_gold_h1('/mnt/user-data/uploads/backtestbot/data/XAUUSD_H1_2016_2026.csv')")
exec(src)
gh = gq.returns(h1, base * VOL, gq.COST_BPS); gold = (1 + gh).groupby(gh.index.date).prod() - 1; gold.index = pd.to_datetime(gold.index)
plan = news + nas + gold.reindex(BD, fill_value=0) * 0.75
def capped(r, cap):
    out = r.copy(); wk = r.index.to_period("W")
    for _, idx in r.groupby(wk).groups.items():
        cum = 0.0
        for d in idx:
            if cap is not None and cum >= cap: out[d] = 0.0
            else: cum += r[d]
    return out
def sh(x, a=None, b=None): x = x[a:b]; return x.mean() / x.std() * np.sqrt(252)
print("| Weekly cap | Return/yr | Sharpe 2016-20 | 2021-24 | 2025-26 | Worst week | Weeks capped |\n|---|---|---|---|---|---|---|")
for cap in (None, 0.005, 0.01, 0.015, 0.02, 0.03):
    r = capped(plan, cap); wkly = (1 + r).groupby(r.index.to_period("W")).prod() - 1
    hit = (plan.groupby(plan.index.to_period("W")).cumsum() >= (cap or 9)).groupby(plan.index.to_period("W")).any().mean()
    print(f"| {'none (current)' if cap is None else f'+{cap:.1%}'} | {r.mean()*252:.1%} | {sh(r,'2016','2020'):.2f} | {sh(r,'2021','2024'):.2f} | {sh(r,'2025','2026'):.2f} | {wkly.min():.1%} | {hit:.0%} |")
