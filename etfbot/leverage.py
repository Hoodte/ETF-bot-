"""Leverage study: what happens if the bot trades 2x or 3x daily-reset leveraged versions.

Research only. Live trading stays unleveraged unless you change the plan.

How a leveraged ETF is simulated (per day, in GBP):
    lev_return = L * underlying_return - (L - 1) * borrow_rate - fund_fee
borrow_rate = US 13-week T-bill yield (^IRX) + spread, applied daily. This captures the
two things that hurt leveraged funds: borrowing costs and daily-reset decay in choppy markets.

Signals always come from the normal (unleveraged) ETF prices; only the money is leveraged,
which is how "leverage only above the trend" is done in practice.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import backtest, strategies

EQUITY = ["GLOBAL_EQ", "US_EQ", "EM_EQ"]


def leveraged_prices(prices: pd.DataFrame, lev: float, rate_pct: pd.Series, spread=0.005,
                     fee=0.0075, sleeves=None) -> pd.DataFrame:
    sleeves = [c for c in (sleeves or EQUITY) if c in prices.columns]
    r = prices.pct_change()
    rate = (rate_pct.reindex(prices.index).ffill().bfill() / 100 + spread).clip(lower=0) / 252
    out = r.copy()
    for c in sleeves:
        out[c] = lev * r[c] - (lev - 1) * rate - fee / 252
    out = out.fillna(0.0).clip(lower=-0.99)        # a fund cannot lose more than 100% in a day
    return 100 * (1 + out).cumprod()


def contribution_mc(daily_rets: pd.Series, years=10, start=5000.0, monthly=200.0, paths=5000,
                    block=20, seed=19) -> dict:
    """Block-bootstrap future paths with monthly top-ups. Drawdown is measured on the
    strategy itself (top-ups would hide it)."""
    r = daily_rets.dropna().to_numpy()
    T = years * 252
    rng = np.random.default_rng(seed)
    nb = -(-T // block)
    idx = (rng.integers(0, len(r) - block, size=(paths, nb))[:, :, None] + np.arange(block)).reshape(paths, -1)[:, :T]
    R = r[idx]
    value = np.full(paths, start)
    for t in range(T):
        value = value * (1 + R[:, t])
        if t % 21 == 20:
            value = value + monthly
    growth = np.cumprod(1 + R, axis=1)
    dd = (growth / np.maximum.accumulate(growth, axis=1) - 1).min(axis=1)
    put_in = start + monthly * (T // 21)
    return {"years": years, "put_in_gbp": put_in,
            "ending_gbp": {f"p{p}": float(np.percentile(value, p)) for p in (5, 25, 50, 75, 95)},
            "prob_ending_below_put_in": float((value < put_in).mean()),
            "worst_drawdown_median": float(np.median(dd)),
            "prob_drawdown_worse_than_50pct": float((dd <= -0.5).mean())}


def study(prices: pd.DataFrame, cfg: dict, rate_pct: pd.Series, levels=(1, 2, 3),
          strategies_to_test=("buy_hold", "faber", "trend"), sleeves=None, label="portfolio",
          years=10, monthly=200.0) -> dict:
    oos = cfg["backtest"]["oos_start"]
    eq0 = cfg["account"]["starting_equity_gbp"]
    cap = cfg["risk"]["max_position_frac"]
    rows = []
    for name in strategies_to_test:
        w = strategies.buy_and_hold(prices) if name == "buy_hold" else strategies.build_weights(prices, cfg, name)
        for L in levels:
            px = prices if L == 1 else leveraged_prices(prices, L, rate_pct, sleeves=sleeves)
            res = backtest.run(px, w, cfg["costs"], 1.0 if name == "buy_hold" else cap, eq0,
                               rebalance="monthly" if name == "buy_hold" else None)
            e = res.equity
            yearly = e.resample("YE").last().pct_change().dropna()
            full, o = res.metrics, backtest.period_metrics(e, oos, None)
            mc = contribution_mc(e.pct_change(), years=years, start=eq0, monthly=monthly)
            gfc = backtest.period_metrics(e, *cfg["backtest"]["stress_periods"]["gfc_2008"])
            rows.append({"strategy": name, "leverage": L, "cagr": full["cagr"], "max_drawdown": full["max_drawdown"],
                         "oos_cagr": o.get("cagr"), "oos_max_drawdown": o.get("max_drawdown"),
                         "worst_year": float(yearly.min()) if len(yearly) else None,
                         "gfc_2008_return": gfc.get("total_return"), "mc": mc})
    return {"label": label, "rows": rows, "years": years, "monthly": monthly, "start": eq0}


def to_markdown(results: list[dict]) -> str:
    def pct(x):
        return "-" if x is None or x != x else f"{x:.0%}"

    lines = ["# Leverage study", "",
             "Daily-reset leveraged versions of the equity ETFs, with real borrowing costs (US T-bill + 0.5%) "
             "and a 0.75% fund fee. Signals come from the normal ETF; only the money is leveraged. "
             "Research only: past results, not a forecast.", ""]
    for res in results:
        lines += [f"## {res['label']}", "",
                  f"Simulated {res['years']} years ahead with £{res['start']:,.0f} to start and "
                  f"£{res['monthly']:,.0f} a month added (£{res['rows'][0]['mc']['put_in_gbp']:,.0f} put in).", "",
                  "| Strategy | Leverage | Return/yr 2004-26 | Worst drop | 2008 crash | Worst calendar year | "
                  "Typical 10-yr value | Bad case (5%) | Chance of a 50%+ drop |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
        for r in res["rows"]:
            m = r["mc"]
            lines.append(f"| {r['strategy']} | {r['leverage']}x | {pct(r['cagr'])} | {pct(r['max_drawdown'])} | "
                         f"{pct(r['gfc_2008_return'])} | {pct(r['worst_year'])} | £{m['ending_gbp']['p50']:,.0f} | "
                         f"£{m['ending_gbp']['p5']:,.0f} | {pct(m['prob_drawdown_worse_than_50pct'])} |")
        lines.append("")
    return "\n".join(lines) + "\n"
