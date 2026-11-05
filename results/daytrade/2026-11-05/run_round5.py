import numpy as np, pandas as pd
from etfbot.daytrade import evaluate as V
COINS = ["BTCUSDT","ETHUSDT","BNBUSDT","XRPUSDT","ADAUSDT","LTCUSDT","TRXUSDT","LINKUSDT","ATOMUSDT","DOGEUSDT","BCHUSDT","SOLUSDT","DOTUSDT","AVAXUSDT"]
def load(m):
    if m == "XAUUSD":
        df = pd.read_csv("/mnt/user-data/uploads/backtestbot/data/XAUUSD_H1_2016_2026.csv"); df.index = pd.to_datetime(df.ts, unit="s", utc=True)
        df = df.rename(columns=str.capitalize)
    else:
        df = pd.read_pickle(f"data/crypto_h1/{m}_1h.pkl"); df = df[(df.index.minute == 0) & (df.index.second == 0)]
    r = np.log(df.Open).diff().shift(-1).dropna()   # open of hour h -> open of hour h+1 (the bar's own move)
    return r
def run(T, key, a, b, mult=1.0):
    dps, n = [], 0
    for m in ["XAUUSD"] + COINS:
        r = load(m); cost = (3.0 if m == "XAUUSD" else 5.0) * mult / 1e4
        sel_end = "2020-12-31" if m == "XAUUSD" else "2021-12-31"
        k = (r.index.hour if key == "hod" else r.index.dayofweek * 24 + r.index.hour)
        rs = r[:sel_end]; ks = k[: len(rs)]
        g = rs.groupby(ks); t = g.mean() / (g.std() / np.sqrt(g.count()))
        side = pd.Series(np.where(t > T, 1, np.where(t < -T, -1, 0)), index=t.index)
        pos = pd.Series(np.asarray(side.reindex(k).fillna(0)), index=r.index)
        p = pos * r - pos.abs() * 2 * cost
        p = p[a:b]
        if len(p) == 0: continue
        d = p.groupby(p.index.floor("D")).sum(); dps.append(d / d.std() if d.std() > 0 else d); n += int((pos[a:b] != 0).sum())
    P = pd.concat(dps, axis=1).fillna(0).sum(axis=1)
    yrs = (P.index[-1] - P.index[0]).days / 365.25
    return P.mean() / P.std() * np.sqrt(len(P) / yrs) if P.std() > 0 else 0, n / max(len(P), 1)
for key in ("hod", "how"):
    for T in (2.0, 2.5, 3.0):
        v, tpd = run(T, key, "2022-01-01", "2024-12-31"); v2, _ = run(T, key, "2022-01-01", "2024-12-31", 2)
        h, _ = run(T, key, "2025-01-01", "2026-10-31")
        print(f"{key} T={T}: validation Sharpe {v:.2f} (2x cost {v2:.2f}), {tpd:.1f} trades/day | holdout {h:.2f}")
