"""Command line entry point. Every command prints JSON so n8n (Execute Command node) can read it.

    python -m etfbot check-data
    python -m etfbot backtest --strategy trend
    python -m etfbot signal
    python -m etfbot paper              # built-in simulator
    python -m etfbot trade              # configured broker (Trading 212 demo by default)
    python -m etfbot approve <id>       # human approval for a real-money order
    python -m etfbot market-status      # is the London market open today?
    python -m etfbot crosscheck         # compare our backtester with vectorbt
    python -m etfbot discover           # rank every pre-registered strategy candidate
    python -m etfbot discover --etf US_EQ             # same, on one ETF
    python -m etfbot combine --etf US_EQ              # blend top 3 (picked in-sample) + chart
    python -m etfbot combine --etf US_EQ --strategies trend,faber,tsmom

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
STRATS = ["trend", "rotation", "dip", "faber", "dual_momentum", "inverse_vol", "trend_inverse_vol", "trend_voltarget",
          "tsmom", "sma_cross", "turn_of_month", "rsi2", "pre_holiday", "options_expiry_week",
          "calendar_composite"]


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
    eq, bh_eq = rep.pop("_equity"), rep.pop("_bh_equity")
    rep["data"] = {"splice": info, "quality": q}
    out = Path("reports")
    out.mkdir(exist_ok=True)
    (out / f"{a.strategy}.json").write_text(json.dumps(rep, indent=2, default=str))
    (out / f"{a.strategy}.md").write_text(report.to_markdown(rep))
    res = {"ok": True, "strategy": a.strategy, "skeptic_verdict": rep["skeptic_verdict"],
           "checks": rep["checks"], "out_of_sample": rep["out_of_sample"],
           "buy_hold_oos": rep["buy_hold_oos"], "trade_stats": rep["trade_stats"],
           "backtest_expert_command": rep["backtest_expert_command"],
           "report": str(out / f"{a.strategy}.md")}
    if a.html:
        from . import tearsheet
        res["tearsheet"] = tearsheet.write_html(eq, bh_eq, out / f"{a.strategy}_tearsheet.html",
                                                f"ETF bot: {a.strategy} vs buy & hold")
    return res


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


def cmd_discover(cfg, a):
    from . import discover
    prices, info = _prices(cfg, a.synthetic)
    q = quality.check_prices(prices)
    if not q["ok"] and not a.force:
        return {"ok": False, "blocked_by": "data_quality", "quality": q}
    tag = ""
    if a.etf:
        prices, cfg = discover.single_etf(prices, cfg, a.etf)
        tag = f"_{a.etf}"
    res = discover.run(prices, cfg)
    res["etf"] = a.etf or "all five"
    out = Path("reports")
    out.mkdir(exist_ok=True)
    (out / f"discovery{tag}.json").write_text(json.dumps(res, indent=2, default=str))
    (out / f"discovery{tag}.md").write_text(discover.to_markdown(res, synthetic=bool(a.synthetic)))
    short = [{k: b[k] for k in ("strategy", "survivor", "oos_cagr", "oos_sharpe", "oos_max_dd",
                                  "deflated_sharpe", "failed_checks")} for b in res["leaderboard"]]
    return {"ok": True, "survivors": res["survivors"], "leaderboard": short,
            "synthetic_data": bool(a.synthetic), "etf": res["etf"], "report": str(out / f"discovery{tag}.md")}


def cmd_combine(cfg, a):
    from . import chart, combine
    prices, _ = _prices(cfg, a.synthetic)
    q = quality.check_prices(prices)
    if not q["ok"] and not a.force:
        return {"ok": False, "blocked_by": "data_quality", "quality": q}
    comps = [x.strip() for x in a.strategies.split(",")] if a.strategies and a.strategies != "auto" else None
    res = combine.run(prices, cfg, a.etf, comps)
    res["synthetic"] = bool(a.synthetic)
    out = Path("reports")
    out.mkdir(exist_ok=True)
    html_path = chart.write_html(res, str(out / f"combine_{a.etf}.html"))
    (out / f"combine_{a.etf}.md").write_text(report.to_markdown(res["blend_report"]))
    return {"ok": True, "etf": a.etf, "components": res["components"], "picked_by": res["picked_by"],
            "blend_skeptic_verdict": res["blend_skeptic_verdict"], "table": res["table"],
            "chart": html_path, "synthetic_data": bool(a.synthetic)}


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


def build_orders(cfg, target_weights: dict, snap: dict) -> list:
    orders = []
    for sleeve, w in target_weights.items():
        delta = w * snap["equity_gbp"] - snap["positions_gbp"].get(sleeve, 0.0)
        if abs(delta) < MIN_ORDER_GBP:
            continue
        side = "buy" if delta > 0 else "sell"
        value = abs(delta)
        if side == "buy":
            value = min(value, cfg["risk"]["max_order_gbp"])  # fills over several runs
        orders.append(risk.Order(sleeve, cfg["instruments"][sleeve]["ucits"], side, round(value, 2)))
    orders.sort(key=lambda o: o.side != "sell")  # sells first to free cash
    return orders


def _market_closed(a) -> dict | None:
    if a.synthetic or getattr(a, "force", False):
        return None
    from . import market_calendar
    st = market_calendar.status()
    if not st["is_trading_day"]:
        return {"ok": True, "skipped": "London market closed today", "calendar": st}
    return None


def cmd_market_status(cfg, a):
    from . import market_calendar
    return {"ok": True, **market_calendar.status(a.date)}


def cmd_crosscheck(cfg, a):
    from . import crosscheck
    prices, _ = _prices(cfg, a.synthetic)
    w = strategies.build_weights(prices, cfg, a.strategy)
    return {"ok": True, "strategy": a.strategy,
            **crosscheck.run(prices, w, cfg["costs"], cfg["risk"]["max_position_frac"],
                             cfg["account"]["starting_equity_gbp"])}


def cmd_approve(cfg, a):
    from . import live_brokers
    return live_brokers.approve(cfg, a.order_id)


def cmd_trade(cfg, a):
    """Run the signal against the configured broker (demo/paper first!)."""
    from . import live_brokers
    closed = _market_closed(a)
    if closed:
        return closed
    sig = cmd_signal(cfg, a)
    if not sig["ok"]:
        return sig
    fx = None
    quote = lambda sleeve: data.quote_gbp(cfg, sleeve, fx)  # noqa: E731
    b = live_brokers.make_broker(cfg, quote)
    gate = live_brokers.ApprovalGate(cfg)
    snap = b.snapshot()
    snap["peak_equity_gbp"] = _peak(cfg, snap["equity_gbp"])
    sent, rejected, waiting = [], [], []
    for o in build_orders(cfg, sig["target_weights"], snap):
        rv = risk.review([o], snap, cfg)
        if not rv["approved"]:
            rejected += rv["rejected"]
            continue
        order = rv["approved"][0]["order"]
        ok, why = gate.check(order)
        if not ok:
            waiting.append({"order": order, "reason": why})
            continue
        sent.append(b.execute(order))
        snap = b.snapshot()
        snap["peak_equity_gbp"] = _peak(cfg, snap["equity_gbp"])
    out = {"ok": True, "broker": cfg["broker"]["name"], "as_of": sig["as_of"], "sent": sent,
           "rejected": rejected, "awaiting_approval": waiting, "account_after": snap}
    _log(cfg, "trades", out)
    return out


def _peak(cfg, equity: float) -> float:
    p = Path(cfg["paths"]["state_dir"]) / "broker_peak.json"
    peak = max(equity, json.loads(p.read_text())["peak"] if p.exists() else equity)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"peak": peak}))
    return peak


def cmd_paper(cfg, a):
    closed = _market_closed(a)
    if closed:
        return closed
    sig = cmd_signal(cfg, a)
    if not sig["ok"]:
        return sig
    prices, _ = _prices(cfg, a.synthetic)
    last = {k: float(v) for k, v in prices.iloc[-1].items()}
    b = broker.PaperBroker(cfg["paths"]["state_dir"], cfg["account"]["starting_equity_gbp"],
                           cfg["costs"]["spread_bps"])
    snap = b.snapshot(last)
    orders = build_orders(cfg, sig["target_weights"], snap)

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
    for name in ("check-data", "signal", "paper", "trade"):
        s = sub.add_parser(name)
        s.add_argument("--synthetic", action="store_true")
        s.add_argument("--force", action="store_true", help="run even if the London market is closed")
    s = sub.add_parser("market-status")
    s.add_argument("--date", default=None)
    s = sub.add_parser("crosscheck")
    s.add_argument("--strategy", default="trend", choices=STRATS)
    s.add_argument("--synthetic", action="store_true")
    s = sub.add_parser("discover", help="rank all pre-registered strategy candidates")
    s.add_argument("--etf", default=None, help="test on one ETF sleeve only, e.g. US_EQ")
    s.add_argument("--synthetic", action="store_true")
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("combine", help="blend up to 3 strategies on one ETF + chart")
    s.add_argument("--etf", required=True, help="ETF sleeve, e.g. US_EQ")
    s.add_argument("--strategies", default="auto", help="comma list of up to 3, or 'auto' (in-sample pick)")
    s.add_argument("--synthetic", action="store_true")
    s.add_argument("--force", action="store_true")
    s = sub.add_parser("approve")
    s.add_argument("order_id")
    s = sub.add_parser("backtest")
    s.add_argument("--strategy", default="trend", choices=STRATS)
    s.add_argument("--synthetic", action="store_true")
    s.add_argument("--force", action="store_true", help="run even if data quality fails")
    s.add_argument("--html", action="store_true", help="also write a QuantStats HTML tearsheet")
    s = sub.add_parser("simulate", help="Time Machine: thousands of simulated years")
    s.add_argument("--strategy", default="trend", choices=STRATS)
    s.add_argument("--horizon-days", type=int, default=252)
    s.add_argument("--paths", type=int, default=10_000)
    s.add_argument("--seed", type=int, default=19)
    s.add_argument("--synthetic", action="store_true")
    s.add_argument("--force", action="store_true")
    a = p.parse_args(argv)
    cfg = load_config(a.config)
    fn = {"check-data": cmd_check_data, "backtest": cmd_backtest, "simulate": cmd_simulate,
          "signal": cmd_signal, "paper": cmd_paper, "trade": cmd_trade,
          "market-status": cmd_market_status, "crosscheck": cmd_crosscheck,
          "approve": cmd_approve, "discover": cmd_discover, "combine": cmd_combine}[a.cmd]
    try:
        out = fn(cfg, a)
    except Exception as e:  # report failures as JSON so the workflow can alert
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    print(json.dumps(out, indent=2, default=str))
    return 0 if out.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
