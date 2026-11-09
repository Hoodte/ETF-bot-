"""Gold vol10 with a fixed take-profit (pre-registered 2026-11-09): TP at +1%, +2%, +3%, +5% above entry.
After a TP, stay flat until the signal turns off and on again (a fresh entry). Exit otherwise unchanged.
Pass = beats 'no TP' Sharpe in BOTH 2016-21 and 2022-26 AND 10y return >= no TP."""
import numpy as np, pandas as pd
src = open("results/2026-11-05/run_gold_variants.py").read().split("ls = np.where")[0].replace("h1 = gq.load_gold_h1(sys.argv[1])", "h1 = gq.load_gold_h1('/mnt/user-data/uploads/backtestbot/data/XAUUSD_H1_2016_2026.csv')")
exec(src)
O, H, C, S, VV = h1.Open.to_numpy(), h1.High.to_numpy(), close.to_numpy(), base.to_numpy(), VOL.to_numpy()
def run_tp(tp):
    n = len(C); r = np.zeros(n); held = 0.0; ep = 0.0; done = False; tgt_prev = 0.0
    for i in range(1, n):
        # return over bar i for position held from bar i-1 close
        if held > 0:
            if tp and H[i] >= ep * (1 + tp):
                px = max(O[i], ep * (1 + tp)); r[i] = held * (px / C[i-1] - 1) - held * gq.COST_BPS / 1e4
                held = 0.0; done = True; continue
            r[i] = held * (C[i] / C[i-1] - 1)
        # decide position for next bar at close of bar i
        if S[i] == 0: done = False
        want = 0.0 if (S[i] == 0 or done) else VV[i]
        if held == 0 and want > 0: ep = C[i]
        r[i] -= abs(want - held) * gq.COST_BPS / 1e4; held = want
    return pd.Series(r, index=h1.index)
out = ["| Take profit | 2016-21 Sharpe | 2022-26 Sharpe | 2025-26 Sharpe | 10y %/yr | Worst drop | Pass |", "|---|---|---|---|---|---|---|"]
res = {}
for tp in (None, 0.01, 0.02, 0.03, 0.05):
    r = run_tp(tp); m = lambda a=None, b=None: gq.metrics(r[a:b])
    res[tp] = (m(None, "2021-12-31")["sharpe"], m("2022-01-01")["sharpe"], m("2025-01-01")["sharpe"], m()["cagr"], m()["max_dd"])
b = res[None]
for tp, (a, o, h, cg, dd) in res.items():
    ok = tp is not None and a > b[0] and o > b[1] and cg >= b[3]
    out.append(f"| {'none (current)' if tp is None else f'+{tp:.0%}'} | {a:.2f} | {o:.2f} | {h:.2f} | {cg:.1%} | {dd:.1%} | {'-' if tp is None else ('yes' if ok else 'no')} |")
print("\n".join(out)); open("results/2026-11-08/gold_tp_results.md", "w").write("# Gold take-profit test\n\n" + __doc__ + "\n\n" + "\n".join(out) + "\n")
