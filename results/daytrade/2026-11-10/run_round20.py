import numpy as np, pandas as pd, warnings, sys; warnings.filterwarnings("ignore")
from numba import njit
BD = pd.bdate_range("2016-01-01", "2026-10-30")
def sh(r, a, b): x = r[a:b]; return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0.0
@njit(cache=True)
def sim(O, H, L, C, V, A, k, sfrac, rr, cost, maxbars):
    n = len(C); out_i = np.zeros(n, np.int64); out_r = np.zeros(n); nt = 0
    d = 0; ext_i = 0; ext = H[0]; piv_i = 0   # d: 1 = looking for swing high (in up move), -1 = looking for swing low
    d = -1; ext = L[0]; piv_i = 0; ext_i = 0
    arm = 0; poc = 0.0; stp = 0.0; tgt = 0.0; inv = 0.0; arm_until = 0
    pos = 0; ep = 0.0; R = 0.0; t_end = 0
    for i in range(20, n):
        # manage open trade
        if pos != 0:
            hit_s = (pos == 1 and L[i] <= stp) or (pos == -1 and H[i] >= stp)
            hit_t = (pos == 1 and H[i] >= tgt) or (pos == -1 and L[i] <= tgt)
            px = -1.0
            if hit_s: px = min(O[i], stp) if pos == 1 else max(O[i], stp)
            elif hit_t: px = tgt
            elif i >= t_end: px = C[i]
            if px > 0:
                out_i[nt] = i; out_r[nt] = pos * (px - ep) / R - 2 * cost * ep / R; nt += 1; pos = 0
            continue
        # armed setup: wait for retest of POC
        if arm != 0:
            if i > arm_until or (arm == -1 and H[i] >= inv) or (arm == 1 and L[i] <= inv):
                arm = 0
            elif (arm == -1 and H[i] >= poc) or (arm == 1 and L[i] <= poc):
                pos = arm; ep = max(O[i], poc) if arm == -1 else min(O[i], poc)
                R = abs(stp - ep)
                if R <= 0: pos = 0; arm = 0
                else:
                    tgt = ep - pos * rr * R if True else 0.0; tgt = ep + pos * rr * R
                    t_end = i + maxbars; arm = 0
                    # same-bar stop check
                    if (pos == 1 and L[i] <= stp) or (pos == -1 and H[i] >= stp):
                        out_i[nt] = i; out_r[nt] = -1.0 - 2 * cost * ep / R; nt += 1; pos = 0
                continue
        # zigzag
        th = k * A[i]
        if d == -1:   # tracking a low after a swing high at piv_i
            if L[i] < ext: ext = L[i]; ext_i = i
            elif H[i] - ext >= th:
                # down leg confirmed: piv_i (high) -> ext_i (low)
                lo = ext; hi = H[piv_i]; rng = hi - lo
                if rng > 0 and ext_i > piv_i:
                    bins = np.zeros(30)
                    for j in range(piv_i, ext_i + 1):
                        b = int((0.5 * (H[j] + L[j]) - lo) / rng * 29.999); bins[max(0, min(29, b))] += V[j]
                    poc = lo + (np.argmax(bins) + 0.5) / 30 * rng
                    if H[i] < poc:
                        arm = -1; stp = poc + sfrac * rng; inv = hi; arm_until = i + maxbars
                d = 1; piv_i = ext_i; ext = H[i]; ext_i = i
        else:
            if H[i] > ext: ext = H[i]; ext_i = i
            elif ext - L[i] >= th:
                hi = ext; lo = L[piv_i]; rng = hi - lo
                if rng > 0 and ext_i > piv_i:
                    bins = np.zeros(30)
                    for j in range(piv_i, ext_i + 1):
                        b = int((0.5 * (H[j] + L[j]) - lo) / rng * 29.999); bins[max(0, min(29, b))] += V[j]
                    poc = lo + (np.argmax(bins) + 0.5) / 30 * rng
                    if L[i] > poc:
                        arm = 1; stp = poc - sfrac * rng; inv = lo; arm_until = i + maxbars
                d = -1; piv_i = ext_i; ext = L[i]; ext_i = i
    return out_i[:nt], out_r[:nt]
def load(kind, sym):
    if kind == "hd":
        b = pd.read_pickle(f"data/histdata/{sym}_5m.pkl"); b["Volume"] = 1.0
    else:
        b = pd.read_pickle(f"data/crypto_h1/{sym}_5m.pkl")
    b = b[~b.index.duplicated()].sort_index(); b.index = b.index.tz_convert("UTC")
    h, l, c = b.High, b.Low, b.Close
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    b["ATR"] = tr.ewm(alpha=1/14, adjust=False).mean().bfill(); return b
M = {"Nasdaq": ("hd", "NSXUSD", 0.5e-4), "S&P": ("hd", "SPXUSD", 0.5e-4), "BTC": ("bn", "BTCUSDT", 4e-4), "ETH": ("bn", "ETHUSDT", 4e-4)}
sets = {"base (k3, stop .25, 2R)": (3, .25, 2), "k 2": (2, .25, 2), "k 5": (5, .25, 2), "stop .15": (3, .15, 2), "stop .35": (3, .35, 2), "target 1.5R": (3, .25, 1.5), "target 3R": (3, .25, 3)}
print("| Market | Setting | Trades/yr | Win % | Avg R | 2016-20 | 2021-24 | 2025-26 |\n|---|---|---|---|---|---|---|---|")
for m, (kind, sym, cost) in M.items():
    b = load(kind, sym); a = [b[x].to_numpy(np.float64) for x in ("Open", "High", "Low", "Close", "Volume", "ATR")]
    yrs = (b.index[-1] - b.index[0]).days / 365.25
    for lab, (k, sf, rr) in sets.items():
        ii, rr_ = sim(*a, k, sf, rr, cost, 288)
        t = pd.Series(rr_, index=b.index[ii].tz_convert(None).normalize()); daily = t.groupby(level=0).sum().reindex(BD, fill_value=0.0)
        print(f"| {m} | {lab} | {len(t)/yrs:.0f} | {(t>0).mean():.0%} | {t.mean():+.3f} | {sh(daily,'2016','2020'):.2f} | {sh(daily,'2021','2024'):.2f} | {sh(daily,'2025','2026'):.2f} |", flush=True)
