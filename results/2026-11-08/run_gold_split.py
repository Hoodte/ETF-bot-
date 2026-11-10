"""Gold vol10, split trade (pre-registered 2026-11-10): half the position closes at a fixed take-profit
(+2%, +3%, +5%), the other half holds until the signal turns off. Pass = higher Sharpe than current in
2016-21 AND 2022-26 and 10y return within 1 point of current."""
import numpy as np, pandas as pd
src = open("results/2026-11-08/run_gold_tp.py").read().split('out = ["| Take profit')[0]
exec(src)
full = gq.returns(h1, base * VOL, gq.COST_BPS)
out = ["| Version | 2016-21 Sharpe | 2022-26 Sharpe | 2025-26 Sharpe | 10y %/yr | Worst drop | Pass |", "|---|---|---|---|---|---|---|"]
res = {"current (hold all)": full}
for tp in (0.02, 0.03, 0.05): res[f"half off at +{tp:.0%}, half held"] = 0.5 * run_tp(tp) + 0.5 * full
b = None
for k, r in res.items():
    m = lambda a=None, bb=None: gq.metrics(r[a:bb]); row = (m(None, "2021-12-31")["sharpe"], m("2022-01-01")["sharpe"], m("2025-01-01")["sharpe"], m()["cagr"], m()["max_dd"])
    b = b or row
    ok = "-" if b is row else ("yes" if row[0] > b[0] and row[1] > b[1] and row[3] >= b[3] - 0.01 else "no")
    out.append(f"| {k} | {row[0]:.2f} | {row[1]:.2f} | {row[2]:.2f} | {row[3]:.1%} | {row[4]:.1%} | {ok} |")
print("\n".join(out)); open("results/2026-11-08/gold_split_results.md", "w").write("# Gold split-trade test\n\n" + __doc__ + "\n\n" + "\n".join(out) + "\n")
