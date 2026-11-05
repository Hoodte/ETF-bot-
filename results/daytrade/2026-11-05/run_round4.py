"""Round 4: crypto pairs stat-arb. See round4_preregistration.md."""
import itertools, json
import numba as nb
import numpy as np, pandas as pd
from etfbot.daytrade import evaluate as V

COINS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "LTCUSDT", "TRXUSDT", "LINKUSDT", "ATOMUSDT", "DOGEUSDT",
         "BCHUSDT", "SOLUSDT", "DOTUSDT", "AVAXUSDT"]
SEL, VAL, HOLD = ("2018-01-01", "2021-12-31"), ("2022-01-01", "2024-12-31"), ("2025-01-01", "2026-10-31")


def prices():
    cols = {}
    for c in COINS:
        p = f"data/crypto_h1/{c}_1h.pkl"
        df = pd.read_pickle(p)
        df = df[(df.index.minute == 0) & (df.index.second == 0)]
        cols[c] = df["Close"]
    P = pd.DataFrame(cols).sort_index()
    return np.log(P)


@nb.njit(cache=True)
def sim(z, beta, ra, rb, svol, Z, H, cost):
    n = len(z); pnl = np.zeros(n); pos = 0; b = 0.0; age = 0; ntr = 0; scale = 1.0; pend = 0
    for t in range(1, n):
        # P&L of the position held over bar t
        if pos != 0:
            pnl[t] += pos * (ra[t] - b * rb[t]) / scale
            age += 1
        # execute the order decided at t-1, at the close of bar t
        if pend != 0:
            if pend == 2:   # exit
                pnl[t] -= cost * (1 + abs(b)) / scale; pos = 0
            else:
                if np.isnan(beta[t]) or np.isnan(svol[t]) or svol[t] <= 0:
                    pend = 0; continue
                b = beta[t]; scale = svol[t]; pos = pend; age = 0; ntr += 1
                pnl[t] -= cost * (1 + abs(b)) / scale
            pend = 0
        # decide at the close of t
        zt = z[t]
        if np.isnan(zt):
            continue
        if pos == 0:
            if zt > Z: pend = -1
            elif zt < -Z: pend = 1
        else:
            if (pos == 1 and zt >= 0) or (pos == -1 and zt <= 0) or age >= H or abs(zt) > Z + 2:
                pend = 2
    return pnl, ntr


def pair_pnl(la, lb, L, W, Z, H, cost):
    ok = la.notna() & lb.notna()
    a, b = la.where(ok), lb.where(ok)
    cov = a.rolling(L, min_periods=L).cov(b); var = b.rolling(L, min_periods=L).var()
    beta = cov / var
    spread = a - beta * b
    z = (spread - spread.rolling(W, min_periods=W).mean()) / spread.rolling(W, min_periods=W).std()
    ra, rb = a.diff(), b.diff()
    svol = (ra - beta * rb).rolling(W, min_periods=W).std() * np.sqrt(24)    # daily spread vol
    pnl, ntr = sim(z.to_numpy(), beta.to_numpy(), ra.fillna(0).to_numpy(), rb.fillna(0).to_numpy(), svol.to_numpy(),
                   Z, H, cost / 1e4)
    return pd.Series(pnl, index=la.index), z


def run(LP, cfg, a_, b_, cost=5.0):
    L, W, Z, H = cfg
    daily, ntr, pairs_pos = [], 0, []
    sub = LP.loc[pd.Timestamp(a_, tz="UTC") - pd.Timedelta(days=60): pd.Timestamp(b_, tz="UTC") + pd.Timedelta(hours=23)]
    for x, y in itertools.combinations(COINS, 2):
        if sub[x].notna().sum() < 24 * 120 or sub[y].notna().sum() < 24 * 120:
            continue
        p, _ = pair_pnl(sub[x], sub[y], L, W, Z, H, cost)
        p = p[a_:b_]
        d = p.groupby(p.index.floor("D")).sum()
        daily.append(d.rename(f"{x[:-4]}/{y[:-4]}"))
        pairs_pos.append(d.sum() > 0)
    D = pd.concat(daily, axis=1).fillna(0.0)
    # count trades properly: entries are where a pair's cost is charged with a new position; approximate via sim's counter
    port = D.sum(axis=1)
    yrs = (port.index[-1] - port.index[0]).days / 365.25
    sh = port.mean() / port.std() * np.sqrt(len(port) / yrs) if port.std() > 0 else 0
    return {"sharpe": float(sh), "daily": port, "pairs": D.shape[1], "pos_share": float(np.mean(pairs_pos))}


def trades_per_day(LP, cfg, a_, b_, cost=5.0):
    L, W, Z, H = cfg; n = 0
    sub = LP.loc[pd.Timestamp(a_, tz="UTC") - pd.Timedelta(days=60): pd.Timestamp(b_, tz="UTC") + pd.Timedelta(hours=23)]
    for x, y in itertools.combinations(COINS, 2):
        if sub[x].notna().sum() < 24 * 120 or sub[y].notna().sum() < 24 * 120:
            continue
        ok = sub[x].notna() & sub[y].notna()
        a, b = sub[x].where(ok), sub[y].where(ok)
        beta = a.rolling(L, min_periods=L).cov(b) / b.rolling(L, min_periods=L).var()
        spread = a - beta * b
        z = (spread - spread.rolling(W, min_periods=W).mean()) / spread.rolling(W, min_periods=W).std()
        ra, rb = a.diff(), b.diff()
        svol = (ra - beta * rb).rolling(W, min_periods=W).std() * np.sqrt(24)
        m = (sub.index >= pd.Timestamp(a_, tz="UTC"))
        _, k = sim(z.to_numpy()[m], beta.to_numpy()[m], ra.fillna(0).to_numpy()[m], rb.fillna(0).to_numpy()[m], svol.to_numpy()[m], Z, H, cost / 1e4)
        n += k
    days = (pd.Timestamp(b_) - pd.Timestamp(a_)).days + 1
    return n / days


if __name__ == "__main__":
    LP = prices()
    grid = list(itertools.product([168, 720], [72, 168], [2.0, 2.5, 3.0], [24, 72]))
    rows = []
    for cfg in grid:
        r = run(LP, cfg, *SEL)
        rows.append((r["sharpe"], cfg))
        print(f"  sel {cfg}: Sharpe {r['sharpe']:.2f}", flush=True)
    rows.sort(key=lambda x: -x[0])
    cfg = rows[0][1]
    print(f"\nFROZEN (L, W, Z, H) = {cfg}, selection Sharpe {rows[0][0]:.2f}")
    v, v2 = run(LP, cfg, *VAL), run(LP, cfg, *VAL, cost=10.0)
    tpd = trades_per_day(LP, cfg, *VAL)
    pre = v["sharpe"] >= 1.0 and v2["sharpe"] > 0 and tpd >= 1 and v["pos_share"] >= 0.55
    print(f"validation 2022-24: Sharpe {v['sharpe']:.2f} (2x cost {v2['sharpe']:.2f}), {tpd:.1f} trades/day, pairs positive {v['pos_share']:.0%} of {v['pairs']} -> pre-holdout pass {pre}")
    h, h2 = run(LP, cfg, *HOLD), run(LP, cfg, *HOLD, cost=10.0)
    print(f"HOLDOUT 2025-26: Sharpe {h['sharpe']:.2f} (2x cost {h2['sharpe']:.2f}), pairs positive {h['pos_share']:.0%}")
    dp = pd.concat([v["daily"], h["daily"]])
    for risk in (0.0005, 0.001, 0.002, 0.003, 0.005):
        k, med, avg = V.funded(dp / max(v["pairs"], 1) * 10, risk)
        print(f"  funded risk {risk:.2%}: keep {k:.0%}, typical month ${med:,.0f}, avg ${avg:,.0f} (~${avg*12/52:,.0f}/wk)")
    json.dump({"cfg": cfg, "sel": rows[0][0], "val": v["sharpe"], "val2x": v2["sharpe"], "tpd": tpd, "pos_share": v["pos_share"],
               "holdout": h["sharpe"], "holdout2x": h2["sharpe"], "passed": bool(pre and h["sharpe"] > 0.5)},
              open("results/daytrade/2026-11-05/round4_results.json", "w"), indent=1)
