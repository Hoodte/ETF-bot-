"""Momentum-fade exits for Nasdaq lunch-RSI (written 2026-11-12 18:40, before running). Base stop/target/15:55 unchanged.
Once a trade has reached +0.5R, exit at the next bar's open if momentum fades:
 M1 a 15-min bar closes below the previous bar's low
 M2 RSI(14) on 15-min drops below 50
 M3 close below the 5-bar EMA
 M4 no new high for 4 bars (1 hour)
 M5 price gives back half of the best open profit
PASS = more total R than current in BOTH 2021-24 and 2025-26 (rule picked before seeing results)."""
import sys; from datetime import datetime, timezone
import numpy as np, pandas as pd
sys.path.insert(0, "/home/claude/backtest-bot")
from data.cache import read_bars
df = read_bars("/home/claude/backtest-bot/data/cache","histdata","NAS100","M15",datetime(2016,1,1,tzinfo=timezone.utc),datetime(2026,11,1,tzinfo=timezone.utc)).reset_index(drop=True)
O,H,L,C = (df[k].to_numpy() for k in ("open","high","low","close"))
d = pd.Series(C).diff(); up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
RSI = (100 - 100/(1+up/dn)).to_numpy(); EMA5 = pd.Series(C).ewm(span=5, adjust=False).mean().to_numpy()
t = pd.read_csv("/tmp/nas_trades.csv")
def run(rule):
    out = []
    for r in t.itertuples():
        e, s0, tg = r.entry_price, r.initial_stop_price, r.initial_target_price; R = e - s0; cR = r.costs/(r.units*R)
        armed = False; best = e; last_hi_i = r.entry_idx; res = None; exit_next = False
        for i in range(r.entry_idx, r.exit_idx + 1):
            if exit_next: res = (O[i] - e)/R; break
            if L[i] <= s0: res = (min(O[i], s0) - e)/R if i > r.entry_idx else (s0 - e)/R; break
            if H[i] >= tg: res = (tg - e)/R; break
            if H[i] > best: best = H[i]; last_hi_i = i
            if best >= e + 0.5*R: armed = True
            if armed and rule and i > r.entry_idx:
                fade = {"M1": C[i] < L[i-1], "M2": RSI[i] < 50, "M3": C[i] < EMA5[i], "M4": i - last_hi_i >= 4,
                        "M5": C[i] <= e + 0.5*(best - e)}[rule]
                if fade: exit_next = True
        if res is None: res = (r.exit_price - e)/R
        out.append(res - cR)
    return pd.Series(out, index=pd.to_datetime(t.entry_ts).dt.year)
labs = {None: "current (no momentum exit)", "M1": "close below previous bar's low", "M2": "RSI falls below 50", "M3": "close below 5-bar EMA",
        "M4": "no new high for 1 hour", "M5": "gives back half the open profit"}
print("| Exit | Win % | 2016-20 R | 2021-24 R | 2025-26 R | Total R |\n|---|---|---|---|---|---|")
for k, lab in labs.items():
    s = run(k)
    print(f"| {lab} | {(s>0).mean():.0%} | {s[s.index<=2020].sum():+.0f} | {s[(s.index>=2021)&(s.index<=2024)].sum():+.0f} | {s[s.index>=2025].sum():+.0f} | {s.sum():+.0f} |", flush=True)
