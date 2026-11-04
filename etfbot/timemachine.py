"""Time Machine: replay thousands of possible years before risking money.

Idea adapted from trader-timemachine in Jakeschincariol/day-trader-skill (MIT),
rebuilt for a weekly ETF strategy instead of a single intraday trade.

Two views:
1. Monte Carlo: build N alternative futures by stitching together random
   20-day blocks of the strategy's own past daily returns (blocks keep calm and
   volatile spells together). Strategy and buy-and-hold use the SAME blocks,
   so the comparison between them is fair.
2. History: every real past window of the same length (stepped weekly).

This is a simulation built from past behaviour, not a prediction. The future
can contain conditions that are not in the history.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

PCTS = (5, 25, 50, 75, 95)


def _max_dd(paths: np.ndarray) -> np.ndarray:
    """paths: (n, T) equity multiples starting at 1. Returns max drawdown per path (negative)."""
    peak = np.maximum.accumulate(np.concatenate([np.ones((paths.shape[0], 1)), paths], axis=1), axis=1)[:, 1:]
    return (paths / peak - 1).min(axis=1)


def _summary(final: np.ndarray, dd: np.ndarray, pause: float, bh_final: np.ndarray | None) -> dict:
    out = {
        "return_pct": {f"p{p}": float(np.percentile(final - 1, p)) for p in PCTS},
        "max_drawdown_pct": {f"p{p}": float(np.percentile(dd, p)) for p in PCTS},
        "prob_loss": float((final < 1).mean()),
        "prob_hit_drawdown_pause": float((dd <= -pause).mean()),
        "worst_return": float(final.min() - 1),
        "worst_drawdown": float(dd.min()),
    }
    if bh_final is not None:
        out["prob_beats_buy_hold"] = float((final > bh_final).mean())
    return out


def monte_carlo(strat_rets: pd.Series, bh_rets: pd.Series | None, horizon_days=252, paths=10_000,
                block=20, seed=19, pause=0.15) -> dict:
    df = pd.concat({"s": strat_rets, "b": bh_rets if bh_rets is not None else strat_rets * 0}, axis=1).dropna()
    s, b = df["s"].to_numpy(), df["b"].to_numpy()
    if len(s) < block * 5:
        raise ValueError("not enough history for a simulation")
    rng = np.random.default_rng(seed)
    nblocks = -(-horizon_days // block)
    starts = rng.integers(0, len(s) - block, size=(paths, nblocks))
    idx = (starts[:, :, None] + np.arange(block)).reshape(paths, -1)[:, :horizon_days]
    sp = np.cumprod(1 + s[idx], axis=1)
    bp = np.cumprod(1 + b[idx], axis=1)
    res = _summary(sp[:, -1], _max_dd(sp), pause, bp[:, -1] if bh_rets is not None else None)
    res["fan"] = {f"p{p}": np.percentile(sp, p, axis=0)[:: max(1, horizon_days // 52)].round(4).tolist() for p in PCTS}
    res.update({"paths": paths, "horizon_days": horizon_days, "block_days": block, "seed": seed,
                "history_days_used": int(len(s))})
    return res


def history(strat_eq: pd.Series, bh_eq: pd.Series | None, horizon_days=252, step=5, pause=0.15) -> dict:
    e = strat_eq.dropna().to_numpy()
    bh = bh_eq.reindex(strat_eq.index).to_numpy() if bh_eq is not None else None
    finals, dds, bfin, starts = [], [], [], []
    for i in range(0, len(e) - horizon_days, step):
        w = e[i:i + horizon_days + 1] / e[i]
        finals.append(w[-1])
        dds.append((w / np.maximum.accumulate(w) - 1).min())
        if bh is not None:
            bfin.append(bh[i + horizon_days] / bh[i])
        starts.append(strat_eq.index[i])
    if not finals:
        return {}
    finals, dds = np.array(finals), np.array(dds)
    out = _summary(finals, dds, pause, np.array(bfin) if bh is not None else None)
    worst = int(np.argmin(finals))
    out.update({"windows": len(finals), "worst_window_start": str(starts[worst].date())})
    return out


def to_markdown(mc: dict, hist: dict, label: str, start_equity: float) -> str:
    def money(x):
        return f"£{start_equity * (1 + x):,.0f}"

    r, d = mc["return_pct"], mc["max_drawdown_pct"]
    lines = [f"# Time Machine: {label}", "",
             f"{mc['paths']:,} simulated {mc['horizon_days']}-day periods built from "
             f"{mc['history_days_used']:,} days of the strategy's own history. Not a prediction.", "",
             f"Starting with £{start_equity:,.0f}:", "",
             "| Outcome | Bad (5%) | Poor (25%) | Typical (50%) | Good (75%) | Great (95%) |",
             "| --- | --- | --- | --- | --- | --- |",
             "| Return | " + " | ".join(f"{r[k]:.1%}" for k in r) + " |",
             "| Ending value | " + " | ".join(money(r[k]) for k in r) + " |",
             "| Max drawdown | " + " | ".join(f"{d[k]:.1%}" for k in d) + " |", "",
             f"- Chance of a losing period: {mc['prob_loss']:.0%}",
             f"- Chance of hitting the drawdown pause: {mc['prob_hit_drawdown_pause']:.0%}",
             f"- Worst simulated period: {mc['worst_return']:.1%} return, {mc['worst_drawdown']:.1%} drawdown"]
    if "prob_beats_buy_hold" in mc:
        lines.append(f"- Chance of beating buy-and-hold: {mc['prob_beats_buy_hold']:.0%}")
    if hist:
        hr = hist["return_pct"]
        lines += ["", f"## Every real past {mc['horizon_days']}-day window ({hist['windows']} windows)", "",
                  f"- Typical return {hr['p50']:.1%}; bad (5%) {hr['p5']:.1%}; great (95%) {hr['p95']:.1%}",
                  f"- Losing windows: {hist['prob_loss']:.0%}; hit drawdown pause: {hist['prob_hit_drawdown_pause']:.0%}",
                  f"- Worst real window started {hist['worst_window_start']}: {hist['worst_return']:.1%}"]
        if "prob_beats_buy_hold" in hist:
            lines.append(f"- Beat buy-and-hold in {hist['prob_beats_buy_hold']:.0%} of windows")
    return "\n".join(lines) + "\n"
