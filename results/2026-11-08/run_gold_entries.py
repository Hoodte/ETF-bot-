"""Gold vol10 entry-timing test (pre-registered 2026-11-09, before running). Exit unchanged (signal off / 5% stop not modelled).
Entry only when macro signal is on AND trigger fires (hourly bars, decided at bar close, filled next bar):
E1 hourly RSI(14) < 40 (pullback)          E2 daily RSI(2) < 25 (short-term oversold)
E3 key level: hourly bar dips below daily EMA20 and closes back above it (rejection)
E4 key level: hourly bar sweeps below previous day's low and closes back above it (rejection)
E5/E6 = E1/E3 but enter anyway after 5 trading days without a trigger (timeout)
Pass = beats baseline Sharpe in BOTH 2016-21 and 2022-26 AND full 10y return >= baseline."""
import numpy as np, pandas as pd
src = open("results/2026-11-05/run_gold_variants.py").read().split("ls = np.where")[0].replace("h1 = gq.load_gold_h1(sys.argv[1])", "h1 = gq.load_gold_h1('/mnt/user-data/uploads/backtestbot/data/XAUUSD_H1_2016_2026.csv')")
exec(src)
def rsi(s, n):
    d = s.diff(); up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn)
hi, lo = h1["High"], h1["Low"]
gd = close.groupby(close.index.date).last(); gd.index = pd.to_datetime(gd.index)
gl = lo.groupby(lo.index.date).min(); gl.index = pd.to_datetime(gl.index)
ema20 = gq.to_hourly(gd.ewm(span=20, adjust=False).mean(), idx, 1)   # yesterday's EMA, known today
pdl = gq.to_hourly(gl, idx, 1)                                        # previous day's low
T = {"E1 RSI14<40": rsi(close, 14) < 40,
     "E2 daily RSI2<25": gq.to_hourly((rsi(gd, 2) < 25).astype(float), idx, 1) > 0,
     "E3 EMA20 rejection": (lo < ema20) & (close > ema20),
     "E4 prev-low sweep": (lo < pdl) & (close > pdl)}
def gated(trig, timeout_h=None):
    s, t = base.to_numpy(), trig.to_numpy(); out = np.zeros(len(s)); pos = 0.0; wait = 0
    for i in range(len(s)):
        if s[i] == 0: pos = 0.0; wait = 0
        elif pos == 0.0:
            wait += 1
            if t[i] or (timeout_h and wait >= timeout_h): pos = 1.0
        out[i] = pos
    return pd.Series(out, index=base.index)
V = {"E0 buy straight away (current)": base}
for k, t in T.items(): V[k] = gated(t)
V["E5 RSI14<40, 5-day timeout"] = gated(T["E1 RSI14<40"], 5 * 23)
V["E6 EMA20 rejection, 5-day timeout"] = gated(T["E3 EMA20 rejection"], 5 * 23)
rows = []
for k, pos in V.items():
    tgt = pos * VOL; r = gq.returns(h1, tgt, gq.COST_BPS); r2 = gq.returns(h1, tgt, 2 * gq.COST_BPS)
    m = lambda a=None, b=None: gq.metrics(r[a:b])
    rows.append((k, m(None, "2021-12-31")["sharpe"], m("2022-01-01")["sharpe"], m("2025-01-01")["sharpe"], m()["cagr"], m()["max_dd"],
                 gq.metrics(r2)["cagr"], (pos > 0).mean() / max((base > 0).mean(), 1e-9)))
b = rows[0]
out = ["| Entry | 2016-21 Sharpe | 2022-26 Sharpe | 2025-26 Sharpe | 10y %/yr | Worst drop | 2x cost %/yr | Time in trade vs current | Pass |", "|" + "---|" * 9]
for k, a, o, h, cg, dd, c2, tim in rows:
    ok = k.startswith("E0") or (a > b[1] and o > b[2] and cg >= b[4])
    out.append(f"| {k} | {a:.2f} | {o:.2f} | {h:.2f} | {cg:.1%} | {dd:.1%} | {c2:.1%} | {tim:.0%} | {'-' if k.startswith('E0') else ('yes' if ok else 'no')} |")
print("\n".join(out)); open("results/2026-11-08/gold_entries_results.md", "w").write("# Gold entry timing\n\n" + __doc__ + "\n\n" + "\n".join(out) + "\n")
