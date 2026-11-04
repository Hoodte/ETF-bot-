"""Strategy discovery: run a FIXED, pre-registered list of documented strategy
families and rank them honestly.

Every candidate goes through the same Skeptic checks as `backtest`, plus:
- Deflated Sharpe ratio (Bailey & Lopez de Prado, 2014): the probability that a
  candidate's out-of-sample Sharpe is real, after correcting for how many
  candidates were tried and for fat tails / skew in the returns.
- Time Machine odds of a losing year and of hitting the drawdown pause.

A candidate is a SURVIVOR only if it passes every Skeptic check AND its deflated
Sharpe is above `discovery.deflated_sharpe_min`. Expect few or none.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

from . import backtest, report, strategies, timemachine

EULER = 0.5772156649
N = NormalDist()


def _sr_stats(rets: pd.Series) -> tuple[float, float, float, int]:
    r = rets.dropna()
    sd = r.std()
    sr = r.mean() / sd if sd > 0 else 0.0     # per-period (daily) Sharpe
    return sr, float(r.skew()), float(r.kurt()) + 3.0, len(r)


def expected_max_sharpe(sr_variance: float, n_trials: int) -> float:
    """Expected best Sharpe from n_trials strategies with no real edge."""
    if n_trials < 2 or sr_variance <= 0:
        return 0.0
    return math.sqrt(sr_variance) * ((1 - EULER) * N.inv_cdf(1 - 1 / n_trials)
                                     + EULER * N.inv_cdf(1 - 1 / (n_trials * math.e)))


def deflated_sharpe(rets: pd.Series, sr0: float) -> float:
    sr, skew, kurt, t = _sr_stats(rets)
    denom = 1 - skew * sr + (kurt - 1) / 4 * sr ** 2
    if t < 3 or denom <= 0:
        return float("nan")
    return N.cdf((sr - sr0) * math.sqrt(t - 1) / math.sqrt(denom))


def run(prices: pd.DataFrame, cfg: dict) -> dict:
    d = cfg["discovery"]
    oos = cfg["backtest"]["oos_start"]
    eq0 = cfg["account"]["starting_equity_gbp"]
    pause = cfg["risk"]["drawdown_pause_frac"]
    bh = backtest.run(prices, strategies.buy_and_hold(prices), cfg["costs"], 1.0, eq0, rebalance="monthly")

    rows, oos_rets = {}, {}
    for name in d["candidates"]:
        rep = report.evaluate(prices, cfg, name)
        eq = rep.pop("_equity")
        rep.pop("_bh_equity")
        r = eq.loc[oos:].pct_change().dropna()
        oos_rets[name] = r
        mc = timemachine.monte_carlo(eq.pct_change(), bh.equity.pct_change(), 252,
                                     d.get("timemachine_paths", 2000), pause=pause)
        rows[name] = {"report": rep, "mc": mc}

    srs = [_sr_stats(r)[0] for r in oos_rets.values()]
    sr0 = expected_max_sharpe(float(np.var(srs, ddof=1)) if len(srs) > 1 else 0.0, len(srs))

    board = []
    for name, v in rows.items():
        rep, mc = v["report"], v["mc"]
        dsr = deflated_sharpe(oos_rets[name], sr0)
        o, bo = rep["out_of_sample"], rep["buy_hold_oos"]
        gfc = rep["stress"].get("gfc_2008", {}).get("strategy", {})
        survivor = rep["skeptic_verdict"] == "PASS" and dsr == dsr and dsr >= d["deflated_sharpe_min"]
        board.append({
            "strategy": name, "survivor": bool(survivor), "skeptic": rep["skeptic_verdict"],
            "failed_checks": [k for k, ok in rep["checks"].items() if not ok],
            "oos_cagr": o.get("cagr"), "oos_sharpe": o.get("sharpe"), "oos_max_dd": o.get("max_drawdown"),
            "bh_oos_cagr": bo.get("cagr"), "bh_oos_max_dd": bo.get("max_drawdown"),
            "beats_bh_sharpe": bool((o.get("sharpe") or -9) > (bo.get("sharpe") or 9)),
            "gfc_2008_return": gfc.get("total_return"), "deflated_sharpe": dsr,
            "prob_losing_year": mc["prob_loss"], "prob_drawdown_pause": mc["prob_hit_drawdown_pause"],
            "orders_per_year": rep["full"].get("orders_per_year"),
            "params": rep["params"], "backtest_expert_command": rep["backtest_expert_command"],
        })
    board.sort(key=lambda x: (x["survivor"], x["oos_sharpe"] or -9), reverse=True)
    return {"candidates_tried": len(board), "expected_best_sharpe_by_luck_daily": sr0,
            "buy_hold_oos": rows[next(iter(rows))]["report"]["buy_hold_oos"],
            "survivors": [b["strategy"] for b in board if b["survivor"]], "leaderboard": board}


def to_markdown(res: dict, synthetic: bool = False) -> str:
    def pct(x):
        return "-" if x is None or x != x else f"{x:.1%}"

    bh = res["buy_hold_oos"]
    lines = ["# Strategy discovery", ""]
    if synthetic:
        lines += ["> **SYNTHETIC PRACTICE DATA. These results say nothing about real markets.**", ""]
    lines += [
             f"{res['candidates_tried']} pre-registered candidates. Out-of-sample period judged only. "
             f"Buy & hold OOS: CAGR {pct(bh.get('cagr'))}, max drawdown {pct(bh.get('max_drawdown'))}.", "",
             f"**Survivors: {', '.join(res['survivors']) or 'none'}**", "",
             "| Strategy | Survivor | OOS CAGR | OOS Sharpe | Beats B&H Sharpe | OOS max DD | 2008 return | "
             "Deflated Sharpe | Losing year odds | Orders/yr | Failed checks |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for b in res["leaderboard"]:
        lines.append(
            f"| {b['strategy']} | {'yes' if b['survivor'] else 'no'} | {pct(b['oos_cagr'])} | "
            f"{(b['oos_sharpe'] or 0):.2f} | {'yes' if b['beats_bh_sharpe'] else 'no'} | {pct(b['oos_max_dd'])} | {pct(b['gfc_2008_return'])} | "
            f"{pct(b['deflated_sharpe'])} | {pct(b['prob_losing_year'])} | "
            f"{(b['orders_per_year'] or 0):.0f} | {', '.join(b['failed_checks']) or '-'} |")
    lines += ["", "Deflated Sharpe = probability the out-of-sample Sharpe is genuine after correcting for "
              "the number of strategies tried. Survivors need every Skeptic check plus a deflated Sharpe "
              "of at least the configured minimum.", "",
              "Next for any survivor: `simulate`, `crosscheck`, and the backtest-expert command in "
              "`reports/discovery.json`. Then paper trade it."]
    return "\n".join(lines) + "\n"
