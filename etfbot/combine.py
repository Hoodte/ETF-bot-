"""Combine up to 3 strategies on one ETF and compare them on one chart.

The blend gives each strategy an equal share of the ETF's capital and averages
their positions. Blending different signals usually smooths the ride; it does
not magically add return.

Picking components: `--pick auto` chooses the 3 strategies with the best
IN-SAMPLE Sharpe (before backtest.oos_start), so the out-of-sample period stays
unseen when the choice is made. Choosing by looking at out-of-sample results
would make the out-of-sample test meaningless.
"""
from __future__ import annotations

import copy

import pandas as pd

from . import backtest, discover, report, strategies

MAX_COMPONENTS = 3


def auto_pick(prices: pd.DataFrame, cfg: dict, n: int = MAX_COMPONENTS) -> list[str]:
    oos = cfg["backtest"]["oos_start"]
    scores = {}
    for name in strategies.SINGLE_ASSET:
        w = strategies.build_weights(prices, cfg, name)
        eq = backtest.run(prices, w, cfg["costs"], 1.0, cfg["account"]["starting_equity_gbp"]).equity
        scores[name] = backtest.period_metrics(eq, None, oos).get("sharpe", -9)
    return sorted(scores, key=scores.get, reverse=True)[:n]


def run(prices: pd.DataFrame, cfg: dict, sleeve: str, components: list[str] | None) -> dict:
    px, c = discover.single_etf(prices, cfg, sleeve)
    picked_by = "you"
    if not components:
        components, picked_by = auto_pick(px, c), "in-sample Sharpe (out-of-sample unseen)"
    bad = [x for x in components if x not in strategies.SINGLE_ASSET]
    if bad or not 1 <= len(components) <= MAX_COMPONENTS:
        raise ValueError(f"choose 1-{MAX_COMPONENTS} of {strategies.SINGLE_ASSET}; got {components}")
    c = copy.deepcopy(c)
    c["strategies"]["blend"]["components"] = list(components)

    eq0 = c["account"]["starting_equity_gbp"]
    curves = {}
    for name in components:
        curves[name] = backtest.run(px, strategies.build_weights(px, c, name), c["costs"], 1.0, eq0).equity
    blend_rep = report.evaluate(px, c, "blend")
    curves["blend"] = blend_rep.pop("_equity")
    curves["buy_hold"] = blend_rep.pop("_bh_equity")

    oos = c["backtest"]["oos_start"]
    table = []
    for name, eq in curves.items():
        o = backtest.period_metrics(eq, oos, None)
        f = backtest.metrics(eq)
        table.append({"series": name, "end_value_gbp": round(float(eq.iloc[-1]), 0),
                      "cagr": f.get("cagr"), "max_drawdown": f.get("max_drawdown"),
                      "oos_cagr": o.get("cagr"), "oos_sharpe": o.get("sharpe"),
                      "oos_max_drawdown": o.get("max_drawdown")})
    return {"etf": sleeve, "ucits": cfg["instruments"][sleeve]["ucits"], "components": list(components),
            "picked_by": picked_by, "blend_skeptic_verdict": blend_rep["skeptic_verdict"],
            "blend_checks": blend_rep["checks"], "blend_report": blend_rep, "table": table,
            "curves": curves, "oos_start": oos, "start_equity_gbp": eq0}
