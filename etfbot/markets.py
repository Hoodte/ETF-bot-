"""Strategy lab across other markets (FX, metals, stock indices, crypto) on daily data.

Same strategies, same Skeptic checks as the ETF work. Each market is tested on its own,
in its own currency, long-or-cash (no shorting, so FX pairs are tested on the long side
only). The deflated Sharpe is corrected for EVERY market x strategy combination tried,
so testing many markets does not manufacture a fake winner.
"""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd

from . import backtest, data, discover, report, strategies, timemachine

# name: (yahoo ticker, cost per side in basis points, note)
MARKETS = {
    "EURUSD": ("EURUSD=X", 2, "FX, long side only"),
    "GBPUSD": ("GBPUSD=X", 2, "FX, long side only"),
    "USDJPY": ("USDJPY=X", 2, "FX, long side only"),
    "AUDUSD": ("AUDUSD=X", 3, "FX, long side only"),
    "GOLD": ("GC=F", 5, "continuous futures; small roll effects"),
    "SILVER": ("SI=F", 8, "continuous futures; small roll effects"),
    "SP500": ("^GSPC", 3, "index level, excludes dividends"),
    "NASDAQ100": ("^NDX", 3, "index level, excludes dividends"),
    "DAX": ("^GDAXI", 3, "total-return index"),
    "FTSE100": ("^FTSE", 4, "index level, excludes dividends"),
    "NIKKEI": ("^N225", 4, "index level, excludes dividends"),
    "BITCOIN": ("BTC-USD", 20, "from 2014, trades 7 days a week"),
    "ETHEREUM": ("ETH-USD", 25, "from 2017, trades 7 days a week"),
}


def load(cfg: dict, names=None) -> dict[str, pd.Series]:
    d = cfg["data"]
    out = {}
    for n in names or MARKETS:
        t = MARKETS[n][0]
        s = data.download_close(t, d["start"], d["cache_dir"], d.get("source", "yahoo"), d.get("csv_dir", "data/manual"))
        s = s[s > 0].dropna()
        out[n] = s[~s.index.duplicated(keep="last")]
    return out


def _cfg_for(cfg: dict, cost_bps: float) -> dict:
    c = copy.deepcopy(cfg)
    c["risk"]["max_position_frac"] = 1.0
    c["costs"]["spread_bps"] = cost_bps
    c["costs"]["fx_fee_bps"] = 0
    c["discovery"]["candidates"] = list(strategies.SINGLE_ASSET)
    return c


def run(cfg: dict, series: dict[str, pd.Series], paths: int = 2000) -> dict:
    oos = cfg["backtest"]["oos_start"]
    rows, oos_rets = [], {}
    for mkt, s in series.items():
        px = pd.DataFrame({mkt: s})
        c = _cfg_for(cfg, MARKETS[mkt][1])
        bh = backtest.run(px, strategies.buy_and_hold(px), c["costs"], 1.0, 10_000)
        bh_o = backtest.period_metrics(bh.equity, oos, None)
        for name in strategies.SINGLE_ASSET:
            rep = report.evaluate(px, c, name)
            eq = rep.pop("_equity")
            rep.pop("_bh_equity")
            key = (mkt, name)
            oos_rets[key] = eq.loc[oos:].pct_change().dropna()
            o = rep["out_of_sample"]
            rows.append({"market": mkt, "strategy": name, "skeptic": rep["skeptic_verdict"],
                         "failed": [k for k, v in rep["checks"].items() if not v],
                         "oos_cagr": o.get("cagr"), "oos_sharpe": o.get("sharpe"), "oos_max_dd": o.get("max_drawdown"),
                         "bh_oos_cagr": bh_o.get("cagr"), "bh_oos_sharpe": bh_o.get("sharpe"),
                         "bh_oos_max_dd": bh_o.get("max_drawdown"), "orders_per_year": rep["full"].get("orders_per_year"),
                         "history_from": str(s.index[0].date()), "_eq": eq, "_bh": bh.equity})
    srs = [discover._sr_stats(r)[0] for r in oos_rets.values()]
    sr0 = discover.expected_max_sharpe(float(np.var(srs, ddof=1)), len(srs))
    for r in rows:
        r["deflated_sharpe"] = discover.deflated_sharpe(oos_rets[(r["market"], r["strategy"])], sr0)
        r["beats_bh_sharpe"] = bool((r["oos_sharpe"] or -9) > (r["bh_oos_sharpe"] or 9))
        r["survivor"] = bool(r["skeptic"] == "PASS" and r["deflated_sharpe"] == r["deflated_sharpe"]
                             and r["deflated_sharpe"] >= cfg["discovery"]["deflated_sharpe_min"])
    rows.sort(key=lambda r: (r["survivor"], r["deflated_sharpe"] if r["deflated_sharpe"] == r["deflated_sharpe"] else -1), reverse=True)
    for r in rows[:5]:
        mc = timemachine.monte_carlo(r["_eq"].pct_change(), r["_bh"].pct_change(), 252, paths,
                                     pause=cfg["risk"]["drawdown_pause_frac"])
        r["prob_losing_year"] = mc["prob_loss"]
    for r in rows:
        r.pop("_eq"), r.pop("_bh")
    return {"trials": len(rows), "markets": len(series), "rows": rows,
            "survivors": [f"{r['market']} {r['strategy']}" for r in rows if r["survivor"]]}


def to_markdown(res: dict) -> str:
    def pct(x):
        return "-" if x is None or x != x else f"{x:.1%}"

    rows = res["rows"]
    lines = ["# Strategy lab: other markets", "",
             f"{res['markets']} markets x {len(strategies.SINGLE_ASSET)} strategies = {res['trials']} combinations, "
             "daily data, long-or-cash, judged on 2016 onwards. Deflated Sharpe corrected for all "
             f"{res['trials']} combinations.", "",
             f"**Survivors: {', '.join(res['survivors']) or 'none'}**", "",
             "## Best strategy per market (by deflated Sharpe) vs buy & hold", "",
             "| Market | Best strategy | OOS return/yr | OOS max DD | Buy & hold return/yr | B&H max DD | Beats B&H Sharpe | Deflated Sharpe | Failed checks |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    seen = set()
    for r in rows:
        if r["market"] in seen:
            continue
        seen.add(r["market"])
        lines.append(f"| {r['market']} | {r['strategy']} | {pct(r['oos_cagr'])} | {pct(r['oos_max_dd'])} | "
                     f"{pct(r['bh_oos_cagr'])} | {pct(r['bh_oos_max_dd'])} | {'yes' if r['beats_bh_sharpe'] else 'no'} | "
                     f"{pct(r['deflated_sharpe'])} | {', '.join(r['failed']) or '-'} |")
    lines += ["", "## Top 15 combinations overall", "",
              "| Market | Strategy | OOS return/yr | OOS Sharpe | OOS max DD | Deflated Sharpe | Orders/yr | Skeptic |",
              "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows[:15]:
        lines.append(f"| {r['market']} | {r['strategy']} | {pct(r['oos_cagr'])} | {(r['oos_sharpe'] or 0):.2f} | "
                     f"{pct(r['oos_max_dd'])} | {pct(r['deflated_sharpe'])} | {(r['orders_per_year'] or 0):.0f} | {r['skeptic']} |")
    lines += ["", "Notes: " + "; ".join(f"{k}: {v[2]}" for k, v in MARKETS.items()) + "."]
    return "\n".join(lines) + "\n"
