"""Gold vol10 exit variations (pre-registered 2026-11-10, before running).
Fixed stop from entry: none, 3%, 5% (current safety stop), 7%.
Trailing stop (from highest price since entry): 3%, 5%, 8%; and 2x, 3x, 4x daily ATR(14).
After any stop-out, stay flat until the signal turns off and on again. Exit otherwise when the signal turns off.
Pass = higher Sharpe than 'no stop' in BOTH 2016-21 and 2022-26 AND 10y return not lower by more than 1 point."""
import numpy as np, pandas as pd
src = open("results/2026-11-05/run_gold_variants.py").read().split("ls = np.where")[0].replace("h1 = gq.load_gold_h1(sys.argv[1])", "h1 = gq.load_gold_h1('/mnt/user-data/uploads/backtestbot/data/XAUUSD_H1_2016_2026.csv')")
exec(src)
O, Hh, L, C, S, VV = h1.Open.to_numpy(), h1.High.to_numpy(), h1.Low.to_numpy(), close.to_numpy(), base.to_numpy(), VOL.to_numpy()
dh = h1.High.groupby(h1.index.date).max(); dl = h1.Low.groupby(h1.index.date).min(); dc = close.groupby(close.index.date).last()
tr = pd.concat([dh - dl, (dh - dc.shift()).abs(), (dl - dc.shift()).abs()], axis=1).max(axis=1).ewm(alpha=1/14, adjust=False).mean()
tr.index = pd.to_datetime(tr.index); ATR = gq.to_hourly(tr.rename("a"), h1.index, 1).replace(0, np.nan).ffill().bfill().to_numpy()
def run(fixed=None, trail=None, atrm=None):
    n = len(C); r = np.zeros(n); held = 0.0; ep = hi = 0.0; done = False
    for i in range(1, n):
        if held > 0:
            lv = []
            if fixed: lv.append(ep * (1 - fixed))
            if trail: lv.append(hi * (1 - trail))
            if atrm: lv.append(hi - atrm * ATR[i])
            stp = max(lv) if lv else None
            if stp is not None and L[i] <= stp:
                px = min(O[i], stp); r[i] = held * (px / C[i-1] - 1) - held * gq.COST_BPS / 1e4; held = 0.0; done = True; continue
            r[i] = held * (C[i] / C[i-1] - 1); hi = max(hi, Hh[i])
        if S[i] == 0: done = False
        want = 0.0 if (S[i] == 0 or done) else VV[i]
        if held == 0 and want > 0: ep = hi = C[i]
        r[i] -= abs(want - held) * gq.COST_BPS / 1e4; held = want
    return pd.Series(r, index=h1.index)
V = {"no stop (signal exit only)": {}, "fixed 3%": {"fixed": .03}, "fixed 5% (current)": {"fixed": .05}, "fixed 7%": {"fixed": .07},
     "trailing 3%": {"trail": .03}, "trailing 5%": {"trail": .05}, "trailing 8%": {"trail": .08},
     "trailing 2x ATR": {"atrm": 2}, "trailing 3x ATR": {"atrm": 3}, "trailing 4x ATR": {"atrm": 4},
     "fixed 5% + trailing 8%": {"fixed": .05, "trail": .08}}
out = ["| Exit | 2016-21 Sharpe | 2022-26 Sharpe | 2025-26 Sharpe | 10y %/yr | Worst drop | Pass |", "|---|---|---|---|---|---|---|"]; b = None
for k, kw in V.items():
    r = run(**kw); m = lambda a=None, bb=None: gq.metrics(r[a:bb])
    row = (m(None, "2021-12-31")["sharpe"], m("2022-01-01")["sharpe"], m("2025-01-01")["sharpe"], m()["cagr"], m()["max_dd"]); b = b or row
    ok = "-" if row is b else ("yes" if row[0] > b[0] and row[1] > b[1] and row[3] >= b[3] - 0.01 else "no")
    out.append(f"| {k} | {row[0]:.2f} | {row[1]:.2f} | {row[2]:.2f} | {row[3]:.1%} | {row[4]:.1%} | {ok} |"); print(out[-1], flush=True)
open("results/2026-11-08/gold_exits2_results.md", "w").write("# Gold exit variations\n\n" + __doc__ + "\n\n" + "\n".join(out) + "\n")
