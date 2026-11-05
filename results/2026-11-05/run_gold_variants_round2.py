"""Round 2: entry-rule changes on top of V1 (vol10). Reuses round-1 setup and evaluation."""
import sys, json
import numpy as np, pandas as pd
src = open("results/2026-11-05/run_gold_variants.py").read()
setup, evaluation = src.split("rows = {}")
exec(setup.replace("N_TRIALS = 30", "N_TRIALS = 37"))

ex = pd.read_csv("data/extra_ief_silver.csv", index_col=0, parse_dates=True)
ief, slv = ex["IEF"].dropna(), ex["SI=F"].dropna()
cot_raw = cot

sma = x.rolling(50).mean()
R1A = gq.to_hourly((x.diff(20) < 0).astype(float), idx, 1)
band = pd.Series(np.nan, index=x.index); band[x < sma * 0.995] = 1.0; band[x > sma * 1.005] = 0.0
R2A = gq.to_hourly(band.ffill().fillna(0.0), idx, 1)
ratio = (d["TIPS"] / ief.reindex(d["TIPS"].index).ffill())
R3B = gq.to_hourly((ratio.pct_change(20) > 0).astype(float), idx, 1)
R4C = gq.to_hourly((cot_raw.diff(4) > 0).astype(float), idx, 6)
gsr = d["GOLD_D"] / slv.reindex(d["GOLD_D"].index).ffill()
R7E = gq.to_hourly((gsr < gsr.rolling(50).mean()).astype(float), idx, 1)

def sticky(v):
    out, pos = np.zeros(len(v)), 0.0
    for i, k in enumerate(v.to_numpy()):
        if k >= 2: pos = 1.0
        elif k == 0: pos = 0.0
        out[i] = pos
    return pd.Series(out, index=v.index)

def dip_entry(sig):
    s, dip = sig.to_numpy(), (close < close.shift(24)).to_numpy()
    out, pos = np.zeros(len(s)), 0.0
    for i in range(len(s)):
        if s[i] == 0: pos = 0.0
        elif pos == 0.0 and dip[i]: pos = 1.0
        out[i] = pos
    return pd.Series(out, index=sig.index)

V = {
    "V1 vol10 (baseline)": base * VOL,
    "R1 dxy_momentum": ((R1A + B + C) >= 2).astype(float) * VOL,
    "R2 dxy_band": ((R2A + B + C) >= 2).astype(float) * VOL,
    "R3 breakeven": ((A + R3B + C) >= 2).astype(float) * VOL,
    "R4 cot_flow": ((A + B + R4C) >= 2).astype(float) * VOL,
    "R5 sticky_exit": sticky(votes) * VOL,
    "R6 dip_entry": dip_entry(base) * VOL,
    "R7 silver_vote": ((votes + R7E) >= 3).astype(float) * VOL,
}
evaluation = evaluation.replace("gold_variants_results", "gold_variants_round2_results")
evaluation = evaluation.replace(
    "winner = max(passing, key=lambda k: passing[k][\"is_sharpe\"]) if passing else \"V0 original\"",
    "b0 = rows['V1 vol10 (baseline)']['is_sharpe']\n"
    "beat = {k: v for k, v in passing.items() if k.startswith('R') and v['is_sharpe'] >= b0 + 0.10}\n"
    "winner = max(beat, key=lambda k: beat[k]['is_sharpe']) if beat else 'V1 vol10 (baseline)'")
exec("rows = {}" + evaluation)
