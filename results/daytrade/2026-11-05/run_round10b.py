import json
import numpy as np, pandas as pd
from etfbot.daytrade import evaluate as V
tv = pd.read_pickle("data/calendar/tv_calendar.pkl")
tv = tv[(tv.importance == 1) & tv.country.isin(["US", "CA"]) & tv.actual.notna() & tv.forecast.notna()].copy()
tv = tv[~tv.title.str.contains("Crude|Gasoline|Natural Gas|EIA", case=False)]
tv["t_utc"] = pd.to_datetime(tv.date, utc=True)
tv["Currency"] = np.where(tv.country == "US", "USD", "CAD")
tv["good_sign"] = np.where(tv.title.str.contains("Unemployment Rate|Jobless Claims", case=False), -1, 1)
tv = tv.sort_values("t_utc")
tv["surp"] = tv.actual.astype(float) - tv.forecast.astype(float)
g = tv.groupby(["country", "title"]).surp
tv["z"] = (tv.surp / g.transform(lambda s: s.expanding().std().shift(1).where(s.expanding().count().shift(1) >= 10))) * tv.good_sign
cal = tv.dropna(subset=["z"]); cal = cal[cal.t_utc >= pd.Timestamp("2016-01-01", tz="UTC")]
print("usable high-impact events:", len(cal), cal.Currency.value_counts().to_dict(), "per business day", round(len(cal) / (10.8 * 261), 2))
src = open("results/daytrade/2026-11-05/run_round10.py").read()
exec(src[src.index("INST = "): src.index("grid = ")])
best = (5, 60, 0.5, "follow")
tr, tr2 = trades(*best), trades(*best, cmult=2.0)
out = {}
for name, a, b in (("2016-20", "2016-01-01", "2020-12-31"), ("validation 2021-24", "2021-01-01", "2024-12-31"), ("HOLDOUT 2025-26", "2025-01-01", "2026-10-30")):
    s, tpd, x = sh(tr, a, b); s2, _, _ = sh(tr2, a, b)
    print(f"{name}: Sharpe {s:.2f} (2x cost {s2:.2f}), {tpd:.2f} trades/day, win {(x.raw>0).mean():.0%}, avg {x.raw.mean()*1e4:.2f} bps/trade, trades {len(x)}")
    out[name] = {"sharpe": s, "sharpe2x": s2, "tpd": tpd, "n": len(x)}
yr = {y: round(sh(tr, f"{y}-01-01", f"{y}-12-31")[0], 2) for y in range(2016, 2027)}
print("by year:", yr)
_, _, h = sh(tr, "2025-01-01", "2026-10-30"); print("holdout by instrument (bps/trade):", h.groupby("inst").raw.agg(lambda r: round(r.mean()*1e4, 2)).to_dict())
tr.to_csv("results/daytrade/2026-11-05/round10b_trades.csv", index=False)
json.dump({"periods": out, "years": yr}, open("results/daytrade/2026-11-05/round10b_results.json", "w"), indent=1, default=str)
