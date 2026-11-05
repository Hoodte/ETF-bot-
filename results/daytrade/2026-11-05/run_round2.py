"""Round 2: crypto momentum replication across coins (see round2_preregistration.md)."""
import itertools, json, sys
import numpy as np, pandas as pd
from etfbot.daytrade import engine as E, evaluate as V

D = "data/crypto_h1"
TRAIN = ["BTCUSDT", "ETHUSDT"]
OTHERS = ["SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT", "LINKUSDT", "AVAXUSDT", "DOTUSDT", "TRXUSDT", "BCHUSDT", "ATOMUSDT"]
COST = 5.0


def path(sym, tf):
    return f"{D}/{sym}_{'15m' if tf == 15 else '1h'}.pkl"


def sharpe_period(tr, data, a, b):
    days = data.days[(data.days >= pd.Timestamp(a, tz="UTC")) & (data.days <= pd.Timestamp(b, tz="UTC"))]
    if len(days) < 30:
        return np.nan, 0
    sub = tr[(tr.exit_time >= days[0]) & (tr.exit_time < days[-1] + pd.Timedelta(days=1))]
    st = V.stats(sub, days)
    return st["sharpe"], st["per_week"]


def grid():
    for n, z in itertools.product([4, 12, 24, 48], [1.0, 1.5, 2.0]):
        for trend, vol, (ex, br), hold in itertools.product(["with", "none"], ["any", "high"],
                                                            [("time", None), ("bracket", [1.0, 2.0]), ("bracket", [1.5, 1.5])], [12, 24, 48]):
            yield {"dataset": "x", "signal": {"family": "momentum", "n": n, "z": z}, "trend": trend, "vol": vol, "session": "all",
                   "direction": "both", "exit": ex, "bracket": br, "hold": hold, "eod": False}


def portfolio(cfg, tf, a, b, cost=COST, syms=TRAIN + OTHERS):
    dps, trades, per = [], 0, {}
    for s in syms:
        d = E.Data(path(s, tf), tf, 24)
        tr = E.run(cfg, d, cost)
        days = d.days[(d.days >= pd.Timestamp(a, tz="UTC")) & (d.days <= pd.Timestamp(b, tz="UTC"))]
        if len(days) < 30:
            continue
        sub = tr[(tr.exit_time >= days[0]) & (tr.exit_time < days[-1] + pd.Timedelta(days=1))]
        dps.append(V.daily_pnl(sub, days).rename(s)); trades += len(sub)
        per[s] = V.stats(sub, days)["sharpe"]
    P = pd.concat(dps, axis=1).fillna(0.0)
    dp = P.sum(axis=1)
    yrs = (dp.index[-1] - dp.index[0]).days / 365.25
    sh = dp.mean() / dp.std() * np.sqrt(len(dp) / yrs)
    return {"sharpe": float(sh), "trades_per_day": trades / len(dp), "per_coin": per, "daily": dp,
            "avg_corr": float(P.corr().where(~np.eye(P.shape[1], dtype=bool)).stack().mean())}


if __name__ == "__main__":
    out = {}
    for tf in (15, 60):
        data = {s: E.Data(path(s, tf), tf, 24, end="2020-12-31") for s in TRAIN}
        best, rows = None, []
        for cfg in grid():
            sh = [sharpe_period(E.run(cfg, data[s], COST), data[s], "2017-01-01", "2020-12-31")[0] for s in TRAIN]
            rows.append((np.mean(sh), min(sh), cfg))
        rows.sort(key=lambda r: -r[0])
        ok = [r for r in rows if r[1] > 0.5]
        print(f"\n== {tf}m selection: {len(rows)} configs, {len(ok)} with both > 0.5")
        for m, mn, c in rows[:5]:
            print(f"  mean {m:.2f} min {mn:.2f} {json.dumps(c['signal'])} trend={c['trend']} vol={c['vol']} {c['exit']} {c['bracket']} hold={c['hold']}")
        if not ok:
            continue
        cfg = ok[0][2]
        out[tf] = {"cfg": cfg, "n_grid": len(rows)}
        # frozen tests
        cross = {}
        for s in OTHERS:
            d = E.Data(path(s, tf), tf, 24, end="2024-12-31")
            cross[s] = sharpe_period(E.run(cfg, d, COST), d, "2017-01-01", "2024-12-31")
        btc_eth_val = {s: sharpe_period(E.run(cfg, E.Data(path(s, tf), tf, 24, end="2024-12-31"), COST),
                                        E.Data(path(s, tf), tf, 24, end="2024-12-31"), "2021-01-01", "2024-12-31") for s in TRAIN}
        pv = portfolio(cfg, tf, "2021-01-01", "2024-12-31")
        pv2 = portfolio(cfg, tf, "2021-01-01", "2024-12-31", cost=2 * COST)
        print(f"  cross-market Sharpe (never-seen coins, to 2024): " + ", ".join(f"{k[:-4]} {v[0]:.2f}" for k, v in cross.items()))
        print(f"  positive on {sum(v[0] > 0 for v in cross.values())}/12 coins; BTC/ETH 2021-24: " + ", ".join(f"{k[:-4]} {v[0]:.2f}" for k, v in btc_eth_val.items()))
        print(f"  portfolio 2021-24: Sharpe {pv['sharpe']:.2f} (2x cost {pv2['sharpe']:.2f}), {pv['trades_per_day']:.1f} trades/day, avg coin correlation {pv['avg_corr']:.2f}")
        out[tf].update(cross={k: v[0] for k, v in cross.items()}, port_val=pv["sharpe"], port_val_2x=pv2["sharpe"], tpd=pv["trades_per_day"])
        passed_pre = pv["sharpe"] >= 1.0 and pv2["sharpe"] > 0 and sum(v[0] > 0 for v in cross.values()) >= 8 and pv["trades_per_day"] >= 1
        print(f"  pre-holdout checks pass: {passed_pre}")
        ph = portfolio(cfg, tf, "2025-01-01", "2026-10-31")
        ph2 = portfolio(cfg, tf, "2025-01-01", "2026-10-31", cost=2 * COST)
        print(f"  HOLDOUT 2025-26 portfolio: Sharpe {ph['sharpe']:.2f} (2x cost {ph2['sharpe']:.2f}), {ph['trades_per_day']:.1f} trades/day; per coin: "
              + ", ".join(f"{k[:-4]} {v:.2f}" for k, v in ph["per_coin"].items()))
        out[tf].update(holdout=ph["sharpe"], holdout_2x=ph2["sharpe"], passed=bool(passed_pre and ph["sharpe"] > 0.5))
        dp = pd.concat([pv["daily"], ph["daily"]])
        for risk in (0.0005, 0.001, 0.0015, 0.002, 0.003):
            k, med, avg = V.funded(dp, risk)
            print(f"  funded $100k, risk {risk:.2%}/ATR unit: keep {k:.0%}, typical month ${med:,.0f}, average ${avg:,.0f} (~${avg*12/52:,.0f}/week)")
        dp.to_frame("pnl_atr").to_csv(f"results/daytrade/2026-11-05/round2_portfolio_daily_{tf}m.csv")
    json.dump(out, open("results/daytrade/2026-11-05/round2_results.json", "w"), indent=1, default=str)
