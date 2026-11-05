"""Run the pre-registered macro_composite variants through backtest, Time Machine and funded sim.
Usage: PYTHONPATH=. python3 results/2026-11-05/run_gold_variants.py <XAUUSD_H1 csv>
"""
import json, sys
import numpy as np, pandas as pd
from scipy.stats import norm
from etfbot import goldquant as gq
from etfbot import timemachine as tm

N_TRIALS = 30
h1 = gq.load_gold_h1(sys.argv[1]); d = gq.load_daily(); cot = gq.load_cot()
idx, close = h1.index, h1["Close"]

# ---- components (all lagged as in goldquant)
x = d["DXY"]
A = gq.to_hourly((x < x.rolling(50).mean()).astype(float), idx, 1)
B = gq.to_hourly((d["TIPS"].pct_change(20) > 0).astype(float), idx, 1)
pct = cot.rolling(156, min_periods=52).apply(lambda z: (z[:-1] < z[-1]).mean(), raw=True)
C = gq.to_hourly((pct < 0.70).astype(float).where(pct.notna(), 0.0), idx, 6)
D = gq.to_hourly((d["US10Y"].diff(20) < 0).astype(float), idx, 1)
votes = A + B + C
gd = d["GOLD_D"]; TREND = gq.to_hourly((gd > gd.rolling(100).mean()).astype(float), idx, 1)

gr = close.pct_change()
dvol = gr.groupby(gr.index.date).apply(lambda z: (1 + z).prod() - 1).rolling(20).std() * np.sqrt(252)
dvol.index = pd.to_datetime(dvol.index)
VOL = gq.to_hourly((0.10 / dvol).clip(upper=1.5).rename("s"), idx, 1).replace(0, np.nan).ffill().fillna(1.0)
WEEKEND = ~(((idx.dayofweek == 4) & (idx.hour >= 19)) | (idx.dayofweek >= 5))
WEEKEND = pd.Series(WEEKEND.astype(float), index=idx)

base = (votes >= 2).astype(float)

def dd_brake(tgt):
    r = gq.returns(h1, tgt, gq.COST_BPS)
    dr = (1 + r).groupby(r.index.date).prod() - 1; dr.index = pd.to_datetime(dr.index)
    eq = (1 + dr).cumprod(); dd = eq / eq.cummax() - 1
    scale = pd.Series(np.where(dd < -0.08, 0.5, 1.0), index=dd.index)
    return tgt * gq.to_hourly(scale, idx, 1).replace(0, np.nan).ffill().fillna(1.0)

ls = np.where(votes >= 2, 1.0, np.where(votes == 0, -1.0, 0.0)); ls = pd.Series(ls, index=idx)
V = {
    "V0 original": base,
    "V1 vol10": base * VOL,
    "V2 strict_3of3": (votes >= 3).astype(float),
    "V3 loose_1of3": (votes >= 1).astype(float),
    "V4 graded": votes / 3,
    "V5 graded_vol10": votes / 3 * VOL,
    "V6 four_vote": ((votes + D) >= 3).astype(float),
    "V7 long_short": ls,
    "V8 long_short_vol10": ls * VOL,
    "V9 trend_gate": base * TREND,
    "V10 dd_brake": dd_brake(base),
    "V11 weekend_flat": base * WEEKEND,
    "V12 vol10_weekend_flat": base * VOL * WEEKEND,
}

bh = close.pct_change().fillna(0.0)
def daily(r): s = (1 + r).groupby(r.index.date).prod() - 1; s.index = pd.to_datetime(s.index); return s
bh_d = daily(bh)

def dsr(r_d, sr_var):
    r_d = r_d.dropna(); T = len(r_d); sr = r_d.mean() / r_d.std()
    g3, g4 = r_d.skew(), r_d.kurt() + 3
    emax = np.sqrt(sr_var) * ((1 - np.euler_gamma) * norm.ppf(1 - 1 / N_TRIALS) + np.euler_gamma * norm.ppf(1 - 1 / (N_TRIALS * np.e)))
    return float(norm.cdf((sr - emax) * np.sqrt(T - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)))

def funded(r_h, tgt, x, swap=0.02, days=252, paths=10000, block=20, seed=5):
    held = tgt.shift(1).fillna(0).abs()
    dr = (1 + r_h).groupby(r_h.index.date).prod() - 1; ex = held.groupby(held.index.date).mean()
    base_ = dr.to_numpy() * x - ex.to_numpy() * x * swap / 252
    rng = np.random.default_rng(seed); nb = -(-days // block)
    ii = (rng.integers(0, len(base_) - block, (paths, nb))[:, :, None] + np.arange(block)).reshape(paths, -1)[:, :days]
    R = base_[ii]; eq = np.cumprod(1 + R, axis=1); lost = ((eq <= 0.9) | (R <= -0.05)).any(1)
    prof = np.where(~lost, np.maximum(eq[:, -1] - 1, 0) * 100000 * 0.8, 0)
    return float((~lost).mean()), float(np.median(prof) / 12), float(prof.mean() / 12)

rows = {}
for name, tgt in V.items():
    r = gq.returns(h1, tgt, gq.COST_BPS); r2 = gq.returns(h1, tgt, 2 * gq.COST_BPS)
    rd = daily(r)
    mc = tm.monte_carlo(rd, bh_d, paths=10000, block=20, seed=19)
    ins, oos, full2 = gq.metrics(r[:gq.IS_END]), gq.metrics(r["2022-01-01":]), gq.metrics(r2)
    best = max(((x_,) + funded(r, tgt, x_) for x_ in (0.5, 0.75, 1.0, 1.25, 1.5)), key=lambda t: (t[1] >= 0.85, t[2]))
    rows[name] = dict(is_sharpe=ins["sharpe"], is_cagr=ins["cagr"], oos_sharpe=oos["sharpe"], oos_cagr=oos["cagr"],
                      oos_dd=oos["max_dd"], full_dd=gq.metrics(r)["max_dd"], cost2x_cagr=full2["cagr"],
                      tm_median=mc["return_pct"]["p50"], tm_p5=mc["return_pct"]["p5"], tm_dd_p5=mc["max_drawdown_pct"]["p5"],
                      tm_ploss=mc["prob_loss"], tm_beat_gold=mc["prob_beats_buy_hold"],
                      prop_size=best[0], prop_keep=best[1], prop_typical=best[2], prop_avg=best[3], _rd=rd)
srs = np.array([v["_rd"].mean() / v["_rd"].std() for v in rows.values()])
sr_var = max(srs.var(ddof=1), 1e-6)
for v in rows.values():
    v["dsr"] = dsr(v.pop("_rd"), sr_var)
    v["passes"] = bool(v["oos_sharpe"] >= 0.8 * v["is_sharpe"] and v["dsr"] >= 0.95 and v["cost2x_cagr"] > 0)

passing = {k: v for k, v in rows.items() if v["passes"]}
winner = max(passing, key=lambda k: passing[k]["is_sharpe"]) if passing else "V0 original"

hdr = "| Variant | IS Sharpe | OOS Sharpe | OOS %/yr | OOS worst drop | TM median yr | TM bad yr (5%) | TM P(loss yr) | TM P(beat gold) | DSR | 2x cost %/yr | Pass |"
lines = [hdr, "|" + "---|" * 12]
for k, v in rows.items():
    lines.append(f"| {k} | {v['is_sharpe']:.2f} | {v['oos_sharpe']:.2f} | {v['oos_cagr']:.1%} | {v['oos_dd']:.1%} | {v['tm_median']:.1%} | "
                 f"{v['tm_p5']:.1%} | {v['tm_ploss']:.0%} | {v['tm_beat_gold']:.0%} | {v['dsr']:.2f} | {v['cost2x_cagr']:.1%} | {'yes' if v['passes'] else 'no'} |")
lines += ["", "| Variant | Best safe size | Keep account | Typical month | Average month |", "|---|---|---|---|---|"]
for k, v in rows.items():
    lines.append(f"| {k} | {v['prop_size']:.2f}x | {v['prop_keep']:.0%} | ${v['prop_typical']:,.0f} | ${v['prop_avg']:,.0f} |")
lines += ["", f"**Winner by the pre-registered rule: {winner}**"]
out = "\n".join(lines)
print(out)
open("results/2026-11-05/gold_variants_results.md", "w").write(
    "# Gold macro_composite variants: results\n\nSee gold_variants_preregistration.md for the fixed rules.\n"
    "TM = Time Machine (10,000 bootstrapped one-year paths). Funded sim: best size keeping the account in 85% or more of years.\n\n" + out + "\n")
json.dump({"winner": winner, "rows": rows}, open("results/2026-11-05/gold_variants_results.json", "w"), indent=1)
