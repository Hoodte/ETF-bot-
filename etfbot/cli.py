"""Command line entry point. Every command prints JSON so n8n (Execute Command node) can read it.

    python -m etfbot check-data
    python -m etfbot backtest --strategy trend
    python -m etfbot signal
    python -m etfbot paper

Add --synthetic to any command to use random-walk test data (no internet needed).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from . import broker, data, quality, report, risk, strategies
from .config import load_config

MIN_ORDER_GBP = 50.0


def _prices(cfg, synthetic: bool):
    if synthetic:
        return data.synthetic_universe(list(cfg["instruments"])), {"source": "synthetic"}
    return data.build_universe(cfg)


def _log(cfg, kind: str, payload: dict) -> None:
    d = Path(cfg["paths"]["log_dir"])
    d.mkdir(parents=True, exist_ok=True)
    with open(d / f"{kind}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"time": datetime.now(timezone.utc).isoformat(), **payload}, default=str) + "\n")


def target_weights(prices: pd.DataFrame, cfg: dict) -> pd.Series:
    enabled = [n for n, s in cfg["strategies"].items() if s.get("enabled")]
    if not enabled:
        return pd.Series(0.0, index=prices.columns)
    ws = [strategies.build_weights(prices, cfg, n).iloc[-1] for n in enabled]
    w = sum(ws) / len(ws)
    return w.clip(upper=cfg["risk"]["max_position_frac"])


def cmd_check_data(cfg, a):
    prices, info = _prices(cfg, a.synthetic)
    as_of = None if a.synthetic else pd.Timestamp.now()
    return {"quality": quality.check_prices(prices, as_of=as_of), "splice": info}


def cmd_backtest(cfg, a):
    prices, info = _prices(cfg, a.synthetic)
    q = quality.check_prices(prices)
    if not q["ok"] and not a.force:
        return {"ok": False, "blocked_by": "data_quality", "quality": q}
    rep = report.evaluate(prices, cfg, a.strategy)
    rep["data"] = {"splice": info, "quality": q}
    out = Path("reports")
    out.mkdir(exist_ok=True)
    (out / f"{a.strategy}.json").write_text(json.dumps(rep, indent=2, default=str))
    (out / f"{a.strategy}.md").write_text(report.to_markdown(rep))
    return {"ok": True, "strategy": a.strategy, "skeptic_verdict": rep["skeptic_verdict"],
            "checks": rep["checks"], "out_of_sample": rep["out_of_sample"],
            "buy_hold_oos": rep["buy_hold_oos"], "report": str(out / f"{a.strategy}.md")}


def cmd_simulate(cfg, a):
    from . import backtest, timemachine

    prices, _ = _prices(cfg, a.synthetic)
    q = quality.check_prices(prices)
    if not q["ok"] and not a.force:
        return {"ok": False, "blocked_by": "data_quality", "quality": q}
    w = strategies.build_weights(prices, cfg, a.strategy)
    eq0 = cfg["account"]["starting_equity_gbp"]
    strat = backtest.run(prices, w, cfg["costs"], cfg["risk"]["max_position_frac"], eq0)
    bh = backtest.run(prices, strategies.buy_and_hold(prices), cfg["costs"], 1.0, eq0, rebalance="monthly")
    pause = cfg["risk"]["drawdown_pause_frac"]
    mc = timemachine.monte_carlo(strat.equity.pct_change(), bh.equity.pct_change(),
                                 a.horizon_days, a.paths, seed=a.seed, pause=pause)
    hist = timemachine.history(strat.equity, bh.equity, a.horizon_days, pause=pause)
    out_dir = Path("reports")
    out_dir.mkdir(exist_ok=True)
    md = timemachine.to_markdown(mc, hist, a.strategy, eq0)
    (out_dir / f"timemachine_{a.strategy}.md").write_text(md)
    (out_dir / f"timemachine_{a.strategy}.json").write_text(
        json.dumps({"monte_carlo": mc, "history": hist}, indent=2))
    mc_short = {k: v for k, v in mc.items() if k != "fan"}
    return {"ok": True, "strategy": a.strategy, "monte_carlo": mc_short, "history": hist,
            "report": str(out_dir / f"timemachine_{a.strategy}.md")}


def cmd_signal(cfg, a):
    prices, _ = _prices(cfg, a.synthetic)
    q = quality.check_prices(prices, as_of=None if a.synthetic else pd.Timestamp.now())
    if not q["ok"]:
        return {"ok": False, "blocked_by": "data_quality", "quality": q}
    w = target_weights(prices, cfg)
    out = {"ok": True, "as_of": str(prices.index[-1].date()), "mode": cfg["mode"],
           "target_weights": {k: round(float(v), 4) for k, v in w.items()},
           "cash_weight": round(float(1 - w.sum()), 4)}
    _log(cfg, "signals", out)
    return out


def cmd_paper(cfg, a):
    if cfg["mode"] != "paper":
        return {"ok": False, "error": "paper command requires mode: paper"}
    sig = cmd_signal(cfg, a)
    if not sig["ok"]:
        return sig
    prices, _ = _prices(cfg, a.synthetic)
    last = {k: float(v) for k, v in prices.iloc[-1].items()}
    b = broker.PaperBroker(cfg["paths"]["state_dir"], cfg["account"]["starting_equity_gbp"],
                           cfg["costs"]["spread_bps"])
    snap = b.snapshot(last)
    orders = []
    for sleeve, w in sig["target_weights"].items():
        delta = w * snap["equity_gbp"] - snap["positions_gbp"].get(sleeve, 0.0)
        if abs(delta) < MIN_ORDER_GBP:
            continue
        side = "buy" if delta > 0 else "sell"
        value = abs(delta)
        if side == "buy":
            value = min(value, cfg["risk"]["max_order_gbp"])  # fills over several runs
        orders.append(risk.Order(sleeve, cfg["instruments"][sleeve]["ucits"], side, round(value, 2)))
    orders.sort(key=lambda o: o.side != "sell")  # sells first to free cash

    fills, rejected = [], []
    for o in orders:
        snap = b.snapshot(last)
        rv = risk.review([o], snap, cfg)
        if rv["approved"]:
            fills.append(b.execute(rv["approved"][0]["order"], last[o.sleeve]))
        else:
            rejected += rv["rejected"]
    b.save()
    out = {"ok": True, "as_of": sig["as_of"], "fills": fills, "rejected": rejected,
           "account": b.snapshot(last)}
    _log(cfg, "paper", out)
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="etfbot")
    p.add_argument("--config", default="config.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("check-data", "signal", "paper"):
        s = sub.add_parser(name)
        s.add_argument("--synthetic", action="store_true")
    s = sub.add_parser("backtest")
    s.add_argument("--strategy", default="trend", choices=["trend", "rotation", "dip"])
    s.add_argument("--synthetic", action="store_true")
    s.add_argument("--force", action="store_true", help="run even if data quality fails")
    s = sub.add_parser("simulate", help="Time Machine: thousands of simulated years")
    s.add_argument("--strategy", default="trend", choices=["trend", "rotation", "dip"])
    s.add_argument("--horizon-days", type=int, default=252)
    s.add_argument("--paths", type=int, default=10_000)
    s.add_argument("--seed", type=int, default=19)
    s.add_argument("--synthetic", action="store_true")
    s.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    cfg = load_config(a.config)
    fn = {"check-data": cmd_check_data, "backtest": cmd_backtest, "simulate": cmd_simulate,
          "signal": cmd_signal, "paper": cmd_paper}[a.cmd]
    try:
        out = fn(cfg, a)
    except Exception as e:  # report failures as JSON so the workflow can alert
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    print(json.dumps(out, indent=2, default=str))
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
