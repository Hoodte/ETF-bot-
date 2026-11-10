"""Strategy 4: VIX risk-off filter on the current plan parts (pre-registered in round17_preregistration.md)."""
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
BD = pd.bdate_range("2016-01-01", "2026-10-30")
def sh(r, a, b): x = r[a:b]; return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0
vix = pd.read_csv("data/^VIX.csv", index_col=0, parse_dates=True).iloc[:, 0]; pv = vix.shift(1).reindex(BD).ffill()
nw = pd.read_csv("results/daytrade/2026-11-05/round10b_trades.csv"); nw["d"] = pd.to_datetime(nw.t, utc=True).dt.tz_convert(None).dt.normalize()
news = nw.groupby("d").pnl.sum().reindex(BD, fill_value=0)
nt = pd.read_csv("/tmp/nas_trades.csv"); nt["d"] = pd.to_datetime(nt.entry_ts, utc=True).dt.tz_convert(None).dt.normalize()
nas = nt.groupby("d").r_multiple.sum().reindex(BD, fill_value=0)
src = open("results/2026-11-05/run_gold_variants.py").read().split("ls = np.where")[0].replace("h1 = gq.load_gold_h1(sys.argv[1])", "h1 = gq.load_gold_h1('/mnt/user-data/uploads/backtestbot/data/XAUUSD_H1_2016_2026.csv')")
exec(src)
gh = gq.returns(h1, base * VOL, gq.COST_BPS); gold = ((1 + gh).groupby(gh.index.date).prod() - 1); gold.index = pd.to_datetime(gold.index); gold = gold.reindex(BD, fill_value=0)
def gold_filtered(th):
    off = pd.Series((vix.shift(1) > th).astype(float).values, index=vix.index)
    m = gq.to_hourly(1 - off, h1.index, 0).replace(0, 0)
    r = gq.returns(h1, base * VOL * m, gq.COST_BPS); d = (1 + r).groupby(r.index.date).prod() - 1; d.index = pd.to_datetime(d.index); return d.reindex(BD, fill_value=0)
print("| Part | VIX filter | 2016-20 | 2021-24 | 2025-26 | Days switched off |\n|---|---|---|---|---|---|")
for name, s in (("News bot", news), ("Nasdaq lunch-RSI", nas), ("Gold macro", gold)):
    for th in (None, 25, 30, 35):
        if th is None: r = s
        elif name == "Gold macro": r = gold_filtered(th)
        else: r = s.where(~(pv > th), 0.0)
        off = 0 if th is None else int((pv > th).sum())
        print(f"| {name} | {'none' if th is None else f'off when VIX > {th}'} | {sh(r,'2016','2020'):.2f} | {sh(r,'2021','2024'):.2f} | {sh(r,'2025','2026'):.2f} | {off} |", flush=True)
