"""Gold vol10: adding a second unit while the signal is on (pre-registered 2026-11-10).
A1/A2 average down: add 1 more unit if price falls 2% / 3% below the first entry.
P1/P2 pyramid: add 1 more unit if price rises 2% / 3% above the first entry.
Both units exit together when the signal turns off. Compared on Sharpe and worst drop (risk-adjusted),
plus 'double size always' to separate the size effect. Pass = higher Sharpe than current in 2016-21 AND 2022-26."""
import numpy as np, pandas as pd
src = open("results/2026-11-05/run_gold_variants.py").read().split("ls = np.where")[0].replace("h1 = gq.load_gold_h1(sys.argv[1])", "h1 = gq.load_gold_h1('/mnt/user-data/uploads/backtestbot/data/XAUUSD_H1_2016_2026.csv')")
exec(src)
C, S = close.to_numpy(), base.to_numpy()
def stack(th):
    out = np.zeros(len(C)); ep = None; added = False
    for i in range(len(C)):
        if S[i] == 0: ep = None; added = False; continue
        if ep is None: ep = C[i]
        if not added and ((th < 0 and C[i] <= ep * (1 + th)) or (th > 0 and C[i] >= ep * (1 + th))): added = True
        out[i] = 2.0 if added else 1.0
    return pd.Series(out, index=base.index)
V = {"current (1 unit)": base, "double size always": base * 2,
     "A1 add on -2% dip": stack(-0.02), "A2 add on -3% dip": stack(-0.03),
     "P1 add on +2% rise": stack(0.02), "P2 add on +3% rise": stack(0.03)}
out = ["| Version | 2016-21 Sharpe | 2022-26 Sharpe | 2025-26 Sharpe | 10y %/yr | Worst drop | Pass |", "|---|---|---|---|---|---|---|"]
res = {}
for k, pos in V.items():
    r = gq.returns(h1, pos * VOL, gq.COST_BPS); m = lambda a=None, b=None: gq.metrics(r[a:b])
    res[k] = (m(None, "2021-12-31")["sharpe"], m("2022-01-01")["sharpe"], m("2025-01-01")["sharpe"], m()["cagr"], m()["max_dd"])
b = res["current (1 unit)"]
for k, (a, o, h, cg, dd) in res.items():
    ok = "-" if k.startswith("current") else ("yes" if a > b[0] and o > b[1] else "no")
    out.append(f"| {k} | {a:.2f} | {o:.2f} | {h:.2f} | {cg:.1%} | {dd:.1%} | {ok} |")
print("\n".join(out)); open("results/2026-11-08/gold_stack_results.md", "w").write("# Gold stacking test\n\n" + __doc__ + "\n\n" + "\n".join(out) + "\n")
