import itertools, json
import numpy as np, pandas as pd
from etfbot.config import load_config
from etfbot.daytrade import engine as E, evaluate as V, schema as S
sc = load_config("config.yaml")["daytrade_fx"]["datasets"]
TRAIN = ["EURUSD", "NSXUSD", "XAUUSD"]; OTHERS = ["GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "SPXUSD", "GRXEUR"]
def data(m, end=None):
    f, tf, cost, se = sc[f"{m}_1h"]; return E.Data(f, tf, se, end), cost
def sh_w(tr, d, a, b):
    days = d.days[(d.days >= pd.Timestamp(a, tz="UTC")) & (d.days <= pd.Timestamp(b, tz="UTC"))]
    sub = tr[(tr.exit_time >= days[0]) & (tr.exit_time < days[-1] + pd.Timedelta(days=1))]
    return V.stats(sub, days), V.daily_pnl(sub, days)
def grid():
    exits = [("time", None), ("bracket", [1.0, 2.0]), ("bracket", [1.5, 1.5])]
    for fam in ("breakout", "momentum", "rsi_revert", "band_fade"):
        for s in S.param_grid(fam):
            for trend, vol, (ex, br), hold in itertools.product(S.ALLOWED["trend"], S.ALLOWED["vol"], exits, [12, 24, 48]):
                yield {"dataset": "x", "signal": s, "trend": trend, "vol": vol, "session": "all", "direction": "both",
                       "exit": ex, "bracket": br, "hold": hold, "eod": False}
tr_data = {m: data(m, "2020-12-31") for m in TRAIN}
rows = []
for c in grid():
    st = [sh_w(E.run(c, d, cost), d, "2016-01-01", "2020-12-31")[0] for d, cost in tr_data.values()]
    rows.append({"c": c, "mean": np.mean([x["sharpe"] for x in st]), "min": min(x["sharpe"] for x in st), "pw": min(x["per_week"] for x in st)})
print("grid size", len(rows))
full = {m: data(m) for m in TRAIN + OTHERS}
out = {}
for fam in ("breakout", "momentum", "rsi_revert", "band_fade"):
    fr = sorted([r for r in rows if r["c"]["signal"]["family"] == fam], key=lambda r: -r["mean"])
    ok = [r for r in fr if r["min"] > 0.3 and r["pw"] >= 0.5]
    print(f"\n== {fam}: {len(fr)} configs, {len(ok)} qualify; best mean {fr[0]['mean']:.2f}")
    if not ok: continue
    c = ok[0]["c"]; print("   FROZEN", S.describe(dict(c, dataset="*")), f"(train mean {ok[0]['mean']:.2f}, min {ok[0]['min']:.2f})")
    unseen = {m: sh_w(E.run(c, full[m][0], full[m][1]), full[m][0], "2016-01-01", "2024-12-31")[0]["sharpe"] for m in OTHERS}
    def port(a, b, mult=1.0):
        dps, n = [], 0
        for m, (d, cost) in full.items():
            st, dp = sh_w(E.run(c, d, cost * mult), d, a, b); dps.append(dp.rename(m)); n += st["trades"]
        P = pd.concat(dps, axis=1).fillna(0).sum(axis=1); yrs = (P.index[-1] - P.index[0]).days / 365.25
        return P.mean() / P.std() * np.sqrt(len(P) / yrs), n / ((pd.Timestamp(b) - pd.Timestamp(a)).days * 5 / 7), P
    v, tpd, pv = port("2021-01-01", "2024-12-31"); v2, _, _ = port("2021-01-01", "2024-12-31", 2)
    npos = sum(x > 0 for x in unseen.values())
    pre = npos >= 4 and v >= 1.0 and v2 > 0 and tpd >= 1
    print("   unseen markets 2016-24: " + ", ".join(f"{k} {x:.2f}" for k, x in unseen.items()) + f"  -> {npos}/6 positive")
    print(f"   portfolio 2021-24 Sharpe {v:.2f} (2x cost {v2:.2f}), {tpd:.1f} trades/trading day -> pre-holdout pass {pre}")
    h, htpd, ph = port("2025-01-01", "2026-10-31"); h2, _, _ = port("2025-01-01", "2026-10-31", 2)
    print(f"   HOLDOUT 2025-26 Sharpe {h:.2f} (2x {h2:.2f}), {htpd:.1f} trades/day")
    dp = pd.concat([pv, ph])
    for risk in (0.001, 0.002, 0.003, 0.004):
        k, med, avg = V.funded(dp, risk); print(f"   FTMO $100k risk {risk:.2%}/ATR: keep {k:.0%}, typical month ${med:,.0f}, avg ${avg:,.0f} (~${avg*12/52:,.0f}/wk)")
    out[fam] = {"cfg": c, "unseen": unseen, "val": v, "val2x": v2, "tpd": tpd, "holdout": h, "holdout2x": h2, "passed": bool(pre and h > 0.5)}
json.dump(out, open("results/daytrade/2026-11-05/round7b_results.json", "w"), indent=1, default=str)
