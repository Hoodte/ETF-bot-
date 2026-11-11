import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
BD = pd.bdate_range("2016-01-01", "2026-10-30")
def sh(r, a, b): x = r[a:b]; return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0
def ohlc(sym):
    b = pd.read_pickle(f"data/histdata/{sym}_1h.pkl"); b = b[~b.index.duplicated()].sort_index()
    b.index = b.index.tz_convert("America/New_York") + pd.Timedelta(hours=7)   # 17:00 NY day
    d = b.groupby(b.index.date).agg(Open=("Open", "first"), High=("High", "max"), Low=("Low", "min"), Close=("Close", "last"))
    d.index = pd.to_datetime(d.index); return d[d.index.dayofweek < 5]
def crypto(n):
    c = pd.read_csv(f"data/{n}-USD.csv", index_col=0, parse_dates=True).iloc[:, 0].dropna()
    return pd.DataFrame({"Open": c.shift(1), "High": c, "Low": c, "Close": c}).dropna()
def run(d, ch=20, sm=3.0, tm=2.0, cost=1e-4, carry=0.02, ppy=252):
    O, H, L, C = (d[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
    tr = np.maximum(H[1:] - L[1:], np.maximum(abs(H[1:] - C[:-1]), abs(L[1:] - C[:-1]))); tr = np.r_[np.nan, tr]
    atr = pd.Series(tr).ewm(alpha=1/14, adjust=False).mean().to_numpy()
    hi = pd.Series(H).rolling(ch).max().shift(1).to_numpy(); lo = pd.Series(L).rolling(ch).min().shift(1).to_numpy()
    r = np.zeros(len(C)); pos = 0; eidx = -1
    for i in range(ch + 15, len(C)):
        if pos:
            # risk-normalised daily P&L: 1% of equity per 1R
            stp_hit = (pos == 1 and L[i] <= stp) or (pos == -1 and H[i] >= stp)
            px = (min(O[i], stp) if pos == 1 else max(O[i], stp)) if stp_hit else C[i]
            prev = ep if i == eidx else C[i - 1]
            r[i] += 0.01 * pos * (px - prev) / R - 0.01 * (ep / R) * carry / ppy
            if stp_hit: r[i] -= 0.01 * ep * cost / R; pos = 0
            else:
                best = max(best, H[i]) if pos == 1 else min(best, L[i])
                if pos * (best - ep) >= R:
                    trail = best - pos * tm * atr[i]
                    stp = max(stp, ep, trail) if pos == 1 else min(stp, ep, trail)
        if pos == 0 and i + 1 < len(C) and not np.isnan(hi[i]):
            sig = 1 if C[i] > hi[i] else (-1 if C[i] < lo[i] else 0)
            if sig:
                pos = sig; ep = O[i + 1]; R = sm * atr[i]; stp = ep - pos * R; best = ep
                r[i + 1] -= 0.01 * ep * cost / R
                eidx = i + 1
    s = pd.Series(r, index=d.index); s = s.groupby(s.index.normalize()).sum()
    return s.reindex(BD, fill_value=0.0) if ppy == 252 else s.resample("B").sum().reindex(BD, fill_value=0.0)
M = {"BTCUSD": (crypto("BTC"), 10e-4, 0.10, 365), "ETHUSD": (crypto("ETH"), 10e-4, 0.10, 365), "USDJPY": (ohlc("USDJPY"), 1e-4, 0.02, 252),
     "EURUSD": (ohlc("EURUSD"), 1e-4, 0.02, 252), "GBPUSD": (ohlc("GBPUSD"), 1e-4, 0.02, 252), "AUDUSD": (ohlc("AUDUSD"), 1e-4, 0.02, 252),
     "USDCAD": (ohlc("USDCAD"), 1e-4, 0.02, 252), "XAUUSD": (ohlc("XAUUSD"), 2e-4, 0.02, 252), "S&P": (ohlc("SPXUSD"), 1e-4, 0.05, 252),
     "Nasdaq": (ohlc("NSXUSD"), 1e-4, 0.05, 252), "DAX": (ohlc("GRXEUR"), 1e-4, 0.05, 252)}
print("| Market | Setting | 2016-20 | 2021-24 | 2025-26 | Avg %/yr at 1% risk |\n|---|---|---|---|---|---|")
for m, (d, c, cy, ppy) in M.items():
    for lab, kw in (("video (20, 3x stop)", {}), ("channel 10", {"ch": 10}), ("channel 55", {"ch": 55}), ("stop 2x", {"sm": 2.0}), ("stop 4x", {"sm": 4.0})):
        if m not in ("BTCUSD", "ETHUSD", "USDJPY") and lab != "video (20, 3x stop)": continue
        r = run(d, cost=c, carry=cy, ppy=ppy, **kw)
        print(f"| {m} | {lab} | {sh(r,'2016','2020'):.2f} | {sh(r,'2021','2024'):.2f} | {sh(r,'2025','2026'):.2f} | {r['2016':].mean()*252:.1%} |", flush=True)

# ---- re-check crypto with real Binance OHLC (proper intraday stops), 7-day weeks
def binance(sym):
    b = pd.read_pickle(f"data/crypto_h1/{sym}_1h.pkl"); b = b[~b.index.duplicated()].sort_index()
    d = b.resample("1D").agg({"Open": "first", "High": "max", "Low": "min", "Close": "last"}).dropna(); d.index = d.index.tz_localize(None); return d
print("\n| Crypto (Binance OHLC) | Setting | 2016-20 | 2021-24 | 2025-26 | Avg %/yr at 1% risk |\n|---|---|---|---|---|---|")
import os
for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "LTCUSDT"):
    if not os.path.exists(f"data/crypto_h1/{sym}_1h.pkl"): continue
    d = binance(sym)
    for lab, kw in (("video (20, 3x stop)", {}), ("channel 10", {"ch": 10}), ("channel 55", {"ch": 55}), ("stop 2x", {"sm": 2.0}), ("stop 4x", {"sm": 4.0})):
        r = run(d, cost=10e-4, carry=0.10, ppy=365, **kw)
        print(f"| {sym} | {lab} | {sh(r,'2016','2020'):.2f} | {sh(r,'2021','2024'):.2f} | {sh(r,'2025','2026'):.2f} | {r['2016':].mean()*252:.1%} | from {d.index[0].date()}", flush=True)
        r2 = run(d, cost=20e-4, carry=0.20, ppy=365, **kw) if lab.startswith("video") else None
        if r2 is not None: print(f"| {sym} | video, 2x costs+carry | {sh(r2,'2016','2020'):.2f} | {sh(r2,'2021','2024'):.2f} | {sh(r2,'2025','2026'):.2f} | {r2['2016':].mean()*252:.1%} |")
