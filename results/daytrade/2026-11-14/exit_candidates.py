"""Pre-registered exit candidates A-D (ChatGPT brief, 14 Nov 2026).

Fixed entries, fixed initial risk; only the exit changes. M15 bar replay.
Conventions (same as the original backtester / earlier nas_be.py):
- bar timestamps are bar START (UTC); entry at the open of the entry bar
- within a bar the stop is checked before the target or partial (conservative)
- a stop hit on a later bar fills at min(open, stop), so gaps through the stop fill at the open
- costs: the original round-trip cost in R; partials add +0.02R extra slippage (sensitivity +0.05R)
- EOD: the original backtester flattens at the close of the first bar starting >= 15:55 NY
  (the 16:00 bar). For D we use the same convention: close of the bar starting at the cutoff.
"""
import sys
from datetime import datetime, timezone
import numpy as np, pandas as pd
sys.path.insert(0, ".")
from data.cache import read_bars

df = read_bars("data/cache", "histdata", "NAS100", "M15", datetime(2016, 1, 1, tzinfo=timezone.utc),
               datetime(2026, 11, 1, tzinfo=timezone.utc)).reset_index(drop=True)
H, L, O, C = df.high.values, df.low.values, df.open.values, df.close.values
NY = pd.to_datetime(df.timestamp_utc).dt.tz_convert("America/New_York")
MIN = (NY.dt.hour * 60 + NY.dt.minute).values
t = pd.read_csv("/tmp/nas_trades.csv")
t["year"] = pd.to_datetime(t.entry_ts).dt.year


def replay(partial=None, trail=None, cutoff=None, extra=0.02):
    """partial=(h, f); trail=(act, dist); cutoff=minutes after midnight NY."""
    out, trig = [], []
    for r in t.itertuples():
        e, s0, tg = r.entry_price, r.initial_stop_price, r.initial_target_price
        R = e - s0
        cR = r.costs / (r.units * R)
        stop, hi, res, part = s0, -np.inf, None, None
        for i in range(r.entry_idx, r.exit_idx + 1):
            if cutoff is not None and MIN[i] >= cutoff and i > r.entry_idx:
                res = (C[i] - e) / R          # close of the first bar starting at/after the cutoff
                break
            if L[i] <= stop:
                res = ((min(O[i], stop) if i > r.entry_idx else stop) - e) / R
                break
            if partial and part is None and H[i] >= e + partial[0] * R:
                part = partial[0]
            if H[i] >= tg:
                res = (tg - e) / R
                break
            hi = max(hi, H[i])
            if trail and hi >= e + trail[0] * R:      # completed bar -> new stop from next bar
                stop = max(stop, hi - trail[1] * R)
        if res is None:
            res = (r.exit_price - e) / R              # original exit (EOD / early close)
        if partial and part is not None:
            res = partial[1] * part + (1 - partial[1]) * res - extra
        out.append(res - cR)
        trig.append(part is not None if partial else None)
    return np.array(out), trig


def dd(x):
    c = np.concatenate([[0], np.cumsum(x)])
    return (np.maximum.accumulate(c) - c).max()


def streak(x):
    b = m = 0
    for v in x:
        b = b + 1 if v < 0 else 0
        m = max(m, b)
    return m


PER = [("2016-20", (2016, 2020)), ("2021-24", (2021, 2024)), ("2025-26", (2025, 2026)), ("Full", (2016, 2026))]


def rows(name, x, base):
    o = []
    for p, (a, b) in PER:
        m = ((t.year >= a) & (t.year <= b)).values
        o.append(f"| {name} | {p} | {m.sum()} | {x[m].sum():+.1f} | {x[m].sum() - base[m].sum():+.1f} | {dd(x[m]):.1f} | {streak(x[m])} |")
    return o


def boot(diff, mask, n=5000, seed=1):
    """Block bootstrap by calendar month of the paired difference."""
    g = pd.to_datetime(t.entry_ts[mask]).dt.to_period("M").values
    d = pd.Series(diff[mask]).groupby(g).sum().values
    rng = np.random.default_rng(seed)
    s = np.array([rng.choice(d, len(d)).sum() for _ in range(n)])
    return (s <= 0).mean()


if __name__ == "__main__":
    base, _ = replay()
    print(f"Replay check: replay {base.sum():+.1f}R vs CSV {t.r_multiple.sum():+.1f}R; "
          f"max per-trade gap {np.abs(base - t.r_multiple.values).max():.3f}R; "
          f"trades differing >0.05R: {(np.abs(base - t.r_multiple.values) > .05).sum()}\n")
    cand = {"A partial 25% @ +1R": dict(partial=(1.0, .25)),
            "B partial 25% @ +2R": dict(partial=(2.0, .25)),
            "C trail 1R after +1.5R": dict(trail=(1.5, 1.0)),
            "D flat at 15:00 NY": dict(cutoff=15 * 60)}
    print("## Primary (pre-registered) settings\n")
    print("| Exit rule | Period | Trades | Net R | vs baseline | Max DD R | Worst streak |\n|---|---|---|---|---|---|---|")
    for l in rows("Original", base, base): print(l)
    res = {}
    for k, kw in cand.items():
        x, _ = replay(**kw)
        res[k] = x
        for l in rows(k, x, base): print(l)
    print("\n## Who gains, who pays (full period, primary settings)\n")
    print("| Rule | Trades changed | R saved on original losers | R given up on original winners | Net | p (2021-26, block bootstrap) |\n|---|---|---|---|---|---|")
    hold = (t.year >= 2021).values
    for k, x in res.items():
        d = x - base
        ch = np.abs(d) > 1e-9
        lo, wi = base < 0, base >= 0
        print(f"| {k} | {ch.sum()} | {d[lo].sum():+.1f} | {d[wi].sum():+.1f} | {d.sum():+.1f} | {boot(d, hold):.2f} |")
    print("\n## Nearby settings (full period net R; 2016-20 / 2021-24 / 2025-26 diffs vs baseline)\n")
    print("| Setting | Full net R | vs base | 16-20 | 21-24 | 25-26 |\n|---|---|---|---|---|---|")
    grids = [("A", [dict(partial=(h, f)) for h in (.8, 1.0, 1.2) for f in (.2, .25, .3)]),
             ("B", [dict(partial=(h, f)) for h in (1.8, 2.0, 2.2) for f in (.2, .25, .3)]),
             ("C", [dict(trail=(a, s)) for a in (1.25, 1.5, 1.75) for s in (.75, 1.0, 1.25)]),
             ("D", [dict(cutoff=c) for c in (14 * 60 + 45, 15 * 60, 15 * 60 + 15)])]
    for g, kws in grids:
        for kw in kws:
            x, _ = replay(**kw)
            d = x - base
            sp = [d[((t.year >= a) & (t.year <= b)).values].sum() for _, (a, b) in PER[:3]]
            print(f"| {g} {kw} | {x.sum():+.1f} | {d.sum():+.1f} | {sp[0]:+.1f} | {sp[1]:+.1f} | {sp[2]:+.1f} |")
    print("\n## Cost sensitivity for partials (+0.05R per partial instead of +0.02R)\n")
    for k in ("A partial 25% @ +1R", "B partial 25% @ +2R"):
        x, _ = replay(**cand[k], extra=.05)
        print(f"- {k}: {x.sum():+.1f}R ({x.sum() - base.sum():+.1f} vs baseline)")
    out = t[["entry_ts", "exit_ts", "exit_reason", "r_mfe", "r_multiple"]].copy()
    out["replay_base"] = base
    for k, x in res.items():
        out[k] = x
    out.to_csv("results/daytrade/2026-11-14/exit_candidates_trades.csv", index=False)
