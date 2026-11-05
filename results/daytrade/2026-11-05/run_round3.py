"""Round 3: perp funding / taker flow / premium signals. See round3_preregistration.md."""
import itertools, json
import numpy as np, pandas as pd
from etfbot.daytrade import engine as E, evaluate as V

D = "data/perp"
TRAIN = ["BTCUSDT", "ETHUSDT"]
OTHERS = ["SOLUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "LTCUSDT", "LINKUSDT", "AVAXUSDT", "DOTUSDT", "TRXUSDT", "BCHUSDT", "ATOMUSDT"]
SEL, VAL, HOLD = ("2020-01-01", "2022-06-30"), ("2022-07-01", "2024-12-31"), ("2025-01-01", "2026-10-31")
COST = 5.0
_cache = {}


def load(sym, end=None):
    key = (sym, end)
    if key in _cache:
        return _cache[key]
    raw = pd.read_pickle(f"{D}/{sym}.pkl")
    kp = f"{D}/{sym}_k.pkl"
    raw["k"][["Open", "High", "Low", "Close"]].to_pickle(kp)
    d = E.Data(kp, 60, 24, end)
    k = raw["k"].reindex(d.idx)
    d.vol_ = k["Volume"].to_numpy(); d.tbuy = k["TakerBuy"].to_numpy()
    f = raw["f"].copy(); f.index = pd.DatetimeIndex(f.index).tz_localize("UTC")
    d.funding_hist = f
    if "p" in raw:
        pr = raw["p"].copy(); pr.index = pd.DatetimeIndex(pr.index).tz_localize("UTC")
        d.premium = pr[~pr.index.duplicated()].reindex(d.idx).ffill().to_numpy()
    else:
        d.premium = np.full(len(d.idx), np.nan)
    _cache[key] = d
    return d


def zs(x, w):
    s = pd.Series(x)
    return ((s - s.rolling(w, min_periods=w // 2).mean()) / s.rolling(w, min_periods=w // 2).std()).to_numpy()


def funding_z(d, days):
    f = d.funding_hist
    sd = f.rolling(days * 3, min_periods=days).std().clip(lower=1e-5)   # funding often sits flat at 0.01%
    z = (f - f.rolling(days * 3, min_periods=days).mean()) / sd
    z = z[~z.index.duplicated()]
    return z.reindex(z.index.union(d.idx)).ffill().reindex(d.idx).to_numpy()   # last settled value at or before t


def raw_sig(d, s):
    with np.errstate(invalid="ignore", divide="ignore"):
        if s["fam"] == "funding":
            z = funding_z(d, s["w"])
        elif s["fam"] == "taker":
            v = pd.Series(d.vol_).rolling(s["n"]).sum(); b = pd.Series(d.tbuy).rolling(s["n"]).sum()
            z = zs(((2 * b - v) / v).to_numpy(), 500)
        elif s["fam"] == "premium":
            z = zs(pd.Series(d.premium).rolling(s["n"]).mean().to_numpy(), 500)
        elif s["fam"] == "crowd_momentum":
            m = d.raw_signal({"family": "momentum", "n": 48, "z": 1.5}).astype(float)
            up = d.c > d.ema200
            m = np.where((m > 0) & up, 1, np.where((m < 0) & ~up, -1, 0))
            fz = funding_z(d, 30)
            ok = np.where(m > 0, fz < s["th"], fz > -s["th"])
            return np.where(ok & ~np.isnan(fz), m, 0).astype(np.int8)
        sig = np.where(z > s["th"], 1, np.where(z < -s["th"], -1, 0))
    if s["mode"] == "fade":
        sig = -sig
    return np.nan_to_num(sig).astype(np.int8)


def entries(d, c):
    sig = raw_sig(d, c["s"])
    if c["trend"] == "with" and c["s"]["fam"] != "crowd_momentum":
        up = d.c > d.ema200
        sig = np.where(np.where(sig > 0, up, ~up) & ~np.isnan(d.ema200), sig, 0)
    return np.where(np.isnan(d.atr), 0, sig).astype(np.int8)


def trades(d, c, cost=COST):
    sig = entries(d, c)
    br = c["bracket"] or [0.0, 0.0]
    e, x, dr, p = E.simulate(d.o, d.h, d.l, d.c, d.atr, sig, d.last_bar, c["bracket"] is not None,
                             float(br[0]), float(br[1]), int(c["hold"]), False, cost / 1e4)
    return pd.DataFrame({"entry_time": d.idx[e], "exit_time": d.idx[x], "dir": dr, "pnl_atr": p})


def window(tr, d, a, b):
    days = d.days[(d.days >= pd.Timestamp(a, tz="UTC")) & (d.days <= pd.Timestamp(b, tz="UTC"))]
    if len(days) < 30:
        return None, None
    return tr[(tr.exit_time >= days[0]) & (tr.exit_time < days[-1] + pd.Timedelta(days=1))], days


def grid():
    exits = [(None, 4), (None, 8), (None, 24), ([1.0, 2.0], 24), ([1.5, 1.5], 24)]
    sigs = []
    for w, th, mode in itertools.product([14, 30, 60], [1.5, 2.0, 2.5], ["fade", "follow"]):
        sigs.append({"fam": "funding", "w": w, "th": th, "mode": mode})
    for n, th, mode in itertools.product([1, 4, 12, 24], [1.5, 2.0, 2.5], ["fade", "follow"]):
        sigs.append({"fam": "taker", "n": n, "th": th, "mode": mode})
    for n, th, mode in itertools.product([1, 8, 24], [1.5, 2.0, 2.5], ["fade", "follow"]):
        sigs.append({"fam": "premium", "n": n, "th": th, "mode": mode})
    for th in (0.5, 1.0, 1.5):
        sigs.append({"fam": "crowd_momentum", "th": th, "mode": "follow"})
    for s in sigs:
        for (br, hold), trend in itertools.product(exits, ["none", "with"]):
            if s["fam"] == "crowd_momentum" and trend == "none":
                continue
            yield {"s": s, "trend": trend, "bracket": br, "hold": hold}


def portfolio(c, a, b, cost=COST, syms=TRAIN + OTHERS):
    dps, n, per = [], 0, {}
    for s in syms:
        d = load(s)
        sub, days = window(trades(d, c, cost), d, a, b)
        if sub is None:
            continue
        dps.append(V.daily_pnl(sub, days).rename(s)); n += len(sub); per[s] = V.stats(sub, days)["sharpe"]
    P = pd.concat(dps, axis=1).fillna(0.0); dp = P.sum(axis=1)
    yrs = (dp.index[-1] - dp.index[0]).days / 365.25
    return {"sharpe": float(dp.mean() / dp.std() * np.sqrt(len(dp) / yrs)), "tpd": n / len(dp), "per": per, "daily": dp}


if __name__ == "__main__":
    data = {s: load(s, SEL[1]) for s in TRAIN}
    rows = []
    for c in grid():
        st = []
        for s in TRAIN:
            sub, days = window(trades(data[s], c), data[s], *SEL)
            st.append(V.stats(sub, days))
        rows.append({"c": c, "mean": np.mean([x["sharpe"] for x in st]), "min": min(x["sharpe"] for x in st),
                     "pw": min(x["per_week"] for x in st)})
    print(f"grid tested on selection data: {len(rows)}")
    res = {}
    for fam in ("funding", "taker", "premium", "crowd_momentum"):
        fr = sorted([r for r in rows if r["c"]["s"]["fam"] == fam], key=lambda r: -r["mean"])
        ok = [r for r in fr if r["min"] > 0.5 and r["pw"] >= 0.5]
        print(f"\n== {fam}: {len(fr)} configs, {len(ok)} qualify. Top by mean Sharpe:")
        for r in fr[:3]:
            print(f"   mean {r['mean']:.2f} min {r['min']:.2f} trades/wk/coin {r['pw']:.1f}  {json.dumps(r['c'])}")
        if not ok:
            continue
        c = ok[0]["c"]
        pv, pv2 = portfolio(c, *VAL), portfolio(c, *VAL, cost=2 * COST)
        unseen_pos = sum(pv["per"].get(s, -1) > 0 for s in OTHERS)
        pre = pv["sharpe"] >= 1.0 and pv2["sharpe"] > 0 and unseen_pos >= 8 and pv["tpd"] >= 1
        print(f"   FROZEN {json.dumps(c)}")
        print(f"   validation portfolio Sharpe {pv['sharpe']:.2f} (2x cost {pv2['sharpe']:.2f}), {pv['tpd']:.1f} trades/day, unseen coins positive {unseen_pos}/12 -> pre-holdout pass {pre}")
        print("   per coin: " + ", ".join(f"{k[:-4]} {v:.2f}" for k, v in pv["per"].items()))
        ph, ph2 = portfolio(c, *HOLD), portfolio(c, *HOLD, cost=2 * COST)
        print(f"   HOLDOUT Sharpe {ph['sharpe']:.2f} (2x cost {ph2['sharpe']:.2f}), {ph['tpd']:.1f} trades/day")
        print("   per coin: " + ", ".join(f"{k[:-4]} {v:.2f}" for k, v in ph["per"].items()))
        passed = bool(pre and ph["sharpe"] > 0.5)
        res[fam] = {"cfg": c, "val": pv["sharpe"], "val2x": pv2["sharpe"], "tpd": pv["tpd"], "unseen_pos": unseen_pos,
                    "holdout": ph["sharpe"], "holdout2x": ph2["sharpe"], "passed": passed}
        dp = pd.concat([pv["daily"], ph["daily"]])
        dp.to_frame("pnl_atr").to_csv(f"results/daytrade/2026-11-05/round3_{fam}_daily.csv")
        for risk in (0.0005, 0.001, 0.002, 0.003):
            k, med, avg = V.funded(dp, risk)
            print(f"   funded $100k risk {risk:.2%}/ATR: keep {k:.0%}, typical month ${med:,.0f}, avg ${avg:,.0f} (~${avg*12/52:,.0f}/wk)")
    json.dump(res, open("results/daytrade/2026-11-05/round3_results.json", "w"), indent=1, default=str)
