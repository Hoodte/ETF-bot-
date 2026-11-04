"""Backtest report + Skeptic gate (adapted from backtest-bot's robustness ideas).

Gate (all must pass, judged on the out-of-sample period only):
1. OOS CAGR > 0 after costs.
2. OOS max drawdown shallower than buy-and-hold, OR OOS CAGR above buy-and-hold.
3. Still positive with costs x2 (cost stress).
4. Still positive with the main parameter nudged -20% and +20% (parameter stability).
5. Bootstrap 5th-percentile OOS Sharpe > 0 is reported (warning, not a hard fail,
   because weekly trend strategies have few independent trades).
"""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from . import backtest, strategies

MAIN_PARAM = {"trend": "sma_days", "rotation": "lookback_days", "dip": "drop_pct", "faber": "months",
              "dual_momentum": "lookback_days", "inverse_vol": "vol_days",
              "trend_inverse_vol": "sma_days", "trend_voltarget": "target_vol",
              "tsmom": "lookback_days", "sma_cross": "slow_days", "turn_of_month": "days_after",
              "rsi2": "entry_below"}


def _nudged(cfg: dict, name: str, f: float) -> dict:
    """Copy of cfg with the strategy's main parameter (or, for a blend, every component's) scaled by f."""
    c2 = copy.deepcopy(cfg)
    names = cfg["strategies"][name]["components"] if name == "blend" else [name]
    for n in names:
        p = MAIN_PARAM[n]
        v = cfg["strategies"][n][p]
        c2["strategies"][n][p] = max(1, int(round(v * f))) if isinstance(v, int) else v * f
    return c2


def _run(prices, cfg, name, cost_mult=1.0):
    costs = dict(cfg["costs"])
    costs["spread_bps"] = costs["spread_bps"] * cost_mult
    costs["commission_gbp"] = costs["commission_gbp"] * cost_mult
    w = strategies.build_weights(prices, cfg, name)
    return backtest.run(prices, w, costs, cfg["risk"]["max_position_frac"],
                        cfg["account"]["starting_equity_gbp"])


def block_bootstrap_sharpe(rets: pd.Series, n=1000, block=20, seed=0) -> tuple[float, float]:
    r = rets.dropna().to_numpy()
    if len(r) < block * 3:
        return float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    nb = len(r) // block
    sh = []
    for _ in range(n):
        starts = rng.integers(0, len(r) - block, nb)
        s = np.concatenate([r[k:k + block] for k in starts])
        sh.append(s.mean() / s.std() * np.sqrt(252) if s.std() > 0 else 0.0)
    return float(np.percentile(sh, 5)), float(np.percentile(sh, 95))


def evaluate(prices: pd.DataFrame, cfg: dict, name: str) -> dict:
    oos = cfg["backtest"]["oos_start"]
    base = _run(prices, cfg, name)
    bh = backtest.run(prices, strategies.buy_and_hold(prices), cfg["costs"], 1.0,
                      cfg["account"]["starting_equity_gbp"], rebalance="monthly")

    rep = {
        "strategy": name,
        "params": cfg["strategies"][name],
        "full": base.metrics,
        "in_sample": backtest.period_metrics(base.equity, None, oos),
        "out_of_sample": backtest.period_metrics(base.equity, oos, None),
        "buy_hold_full": bh.metrics,
        "buy_hold_oos": backtest.period_metrics(bh.equity, oos, None),
        "stress": {},
    }
    for label, (a, b) in cfg["backtest"]["stress_periods"].items():
        rep["stress"][label] = {
            "strategy": backtest.period_metrics(base.equity, a, b),
            "buy_hold": backtest.period_metrics(bh.equity, a, b),
        }

    o, bo = rep["out_of_sample"], rep["buy_hold_oos"]
    checks = {}
    checks["oos_positive"] = bool(o.get("cagr", -1) > 0)
    checks["beats_bh_on_risk_or_return"] = bool(
        o.get("max_drawdown", -1) > bo.get("max_drawdown", 0) or o.get("cagr", -1) > bo.get("cagr", 0))

    stressed = _run(prices, cfg, name, cost_mult=2.0)
    so = backtest.period_metrics(stressed.equity, oos, None)
    checks["survives_2x_costs"] = bool(so.get("cagr", -1) > 0)

    p = "all components" if name == "blend" else MAIN_PARAM[name]
    nudges = {}
    for f in (0.8, 1.2):
        r2 = _run(prices, _nudged(cfg, name, f), name)
        nudges[f"x{f}"] = backtest.period_metrics(r2.equity, oos, None).get("cagr")
    checks["stable_to_param_nudge"] = all(v is not None and v > 0 for v in nudges.values())

    lo, hi = block_bootstrap_sharpe(base.equity.loc[oos:].pct_change())
    rep["robustness"] = {"oos_cagr_costs_x2": so.get("cagr"), f"oos_cagr_{p}_nudged".replace(" ", "_"): nudges,
                         "oos_sharpe_bootstrap_5_95": [lo, hi]}
    rep["warnings"] = [] if (lo == lo and lo > 0) else ["bootstrap 5th-percentile OOS Sharpe <= 0: edge not statistically clear"]
    rep["checks"] = checks
    rep["skeptic_verdict"] = "PASS" if all(checks.values()) else "FAIL"

    from . import trades
    ts = trades.summary(trades.round_trips(prices, base.weights))
    years = (prices.index[-1] - prices.index[0]).days / 365.25
    comps = cfg["strategies"][name]["components"] if name == "blend" else [name]
    n_params = sum(isinstance(v, (int, float)) and not isinstance(v, bool)
                   for c in comps for k, v in cfg["strategies"][c].items() if k != "enabled")
    rep["trade_stats"] = ts
    rep["backtest_expert_command"] = trades.backtest_expert_command(
        ts, base.metrics.get("max_drawdown", 0.0), years, n_params)
    rep["_equity"] = base.equity        # used for the HTML tearsheet, not saved to JSON
    rep["_bh_equity"] = bh.equity
    return rep


def to_markdown(rep: dict) -> str:
    def row(label, m):
        if not m:
            return f"| {label} | - | - | - | - |"
        return (f"| {label} | {m['cagr']:.1%} | {m['vol']:.1%} | {m['sharpe']:.2f} | "
                f"{m['max_drawdown']:.1%} |")

    lines = [f"# Backtest report: {rep['strategy']}", "",
             f"Skeptic verdict: **{rep['skeptic_verdict']}**", "",
             f"Parameters (frozen): `{rep['params']}`", "",
             "| Period | CAGR | Vol | Sharpe | Max DD |", "| --- | --- | --- | --- | --- |",
             row("Strategy, full", rep["full"]), row("Strategy, in-sample", rep["in_sample"]),
             row("Strategy, out-of-sample", rep["out_of_sample"]),
             row("Buy & hold, full", rep["buy_hold_full"]), row("Buy & hold, out-of-sample", rep["buy_hold_oos"]),
             "", "## Stress periods", "", "| Period | Strategy return | Strategy max DD | B&H return | B&H max DD |",
             "| --- | --- | --- | --- | --- |"]
    for k, v in rep["stress"].items():
        s, b = v["strategy"], v["buy_hold"]
        if s and b:
            lines.append(f"| {k} | {s['total_return']:.1%} | {s['max_drawdown']:.1%} | "
                         f"{b['total_return']:.1%} | {b['max_drawdown']:.1%} |")
    lines += ["", "## Checks", ""] + [f"- {k}: {'pass' if v else 'FAIL'}" for k, v in rep["checks"].items()]
    lines += ["", f"Robustness: `{rep['robustness']}`"]
    if rep["warnings"]:
        lines += ["", "Warnings:"] + [f"- {w}" for w in rep["warnings"]]
    if rep.get("trade_stats", {}).get("total_trades"):
        t = rep["trade_stats"]
        lines += ["", f"Round-trip trades: {t['total_trades']}, win rate {t['win_rate_pct']}%, "
                      f"avg win {t['avg_win_pct']}%, avg loss {t['avg_loss_pct']}%, avg hold {t['avg_hold_days']} days",
                  "", "Second opinion (backtest-expert skill):", "", f"```\n{rep['backtest_expert_command']}\n```"]
    if "orders_per_year" in rep["full"]:
        lines += ["", f"Orders per year: {rep['full']['orders_per_year']:.1f}; total costs £{rep['full']['costs_gbp']:.0f}"]
    return "\n".join(lines) + "\n"
