"""Hypothesis 2: XAUUSD M15 London-NY overlap breakout.

User spec (full):
  - Pre-overlap range:  05:00-13:00 GMT (480 min)
  - Entry window:       13:00-16:00 GMT (180 min)
  - Direction filter:   H1 bias — price above/below H1 EMA50 with 5-bar slope
  - News filter:        skip ±15 min around CPI/NFP/FOMC
  - Optional:           long only if DXY below H1 EMA20

Approximations in this run (documented):
  - H1 bias is approximated by **same-timeframe M15 EMA200** (= 50-hour MA,
    i.e. ≈ H1 EMA50). M15 close_above_ema200 / close_below_ema200 features.
  - 5-bar slope filter not implemented; the EMA-side check is the directional
    proxy.
  - News filter not implemented (would require a news calendar adapter).
  - DXY filter not implemented (would require DXY data ingest).
  - TP1 partial-close not implemented in engine; single TP2 target.

This is the IMMEDIATE breakout variant. The user noted "preferred: limit
entry at broken range edge after breakout candle closes (retest entry)"
which is a separate follow-up.

Run:
    .venv/Scripts/python.exe scripts/run_h2_xauusd_london_ny_overlap.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

import blocks
import features
from backtester import CostConfig, run_backtest
from data.cache import read_bars
from data.instruments import get_instrument
from dna.schema import (
    BlockRef, EngineConstraints, ExitSpec, Metadata, RiskSpec, Strategy,
)
from dna.validator import validate
from runner import SplitConfig, run_splits
from scorer import compute_metrics
from scorer.montecarlo import mc_dropout_trials, permutation_test
from scorer.robustness import (
    RobustnessGateConfig, evaluate_robustness_gates, run_robustness_suite,
)

blocks.load_all()
features.load_all()

PAIR = "XAUUSD"
TF = "H1"
SOURCE = "dukascopy"
START = datetime(2025, 5, 25, tzinfo=timezone.utc)
END = datetime(2026, 5, 24, tzinfo=timezone.utc)
RUN_ID = f"h2_xauusd_overlap_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

SPEC = get_instrument(PAIR)
COST = CostConfig(
    spread_override=SPEC.default_spread,
    commission_per_contract_override=0.0,
    slippage_entry_ticks=2.0,
    slippage_stop_ticks=4.0,
)
MC_TRIALS = 1000


def hdr(s):
    print("\n" + "=" * 100, flush=True); print(s, flush=True); print("=" * 100, flush=True)


def fmt(name, m):
    if m is None:
        return f"  {name}: <empty>"
    return (f"  {name:<14}  trades={int(m.trade_count):>4}  win%={m.win_rate*100:>5.1f}  "
            f"PF={m.profit_factor:>5.2f}  Sharpe={m.sharpe:>+6.2f}  "
            f"DD={m.max_drawdown_pct:>5.2f}%  netPnL=${m.net_pnl:>11,.0f}")


def build_strategy(direction):
    dir_int = 1 if direction == "long" else -1
    trend_feat = "close_above_ema50" if direction == "long" else "close_below_ema50"

    entry = BlockRef(
        block="opening_range_breakout",
        params={
            "tz": "UTC",
            "session_start_hour": 5,
            "session_start_minute": 0,
            "range_minutes": 480,         # 05:00-13:00 UTC
            "entry_window_minutes": 180,  # 13:00-16:00 UTC
        },
    )
    filters = [
        # M15-EMA200 approximates H1-EMA50 trend bias
        BlockRef(block="feature_filter",
                 params={"features": f"{trend_feat},body_ratio_above_50"}),
    ]
    exit_spec = ExitSpec(
        block="atr_stop_target",
        params={
            "atr_period": 14,
            "stop_atr_mult": 1.2,
            "target_atr_mult": 3.0,
            "trail": False,
            "trail_atr_mult": 1.0,
        },
    )
    risk_spec = RiskSpec(
        block="fixed_pct",
        params={"risk_pct": 1.0, "max_concurrent": 1},
    )
    constraints = EngineConstraints(
        timezone="UTC",
        max_trades_per_direction_per_day=1,
        daily_loss_lockout_pct=2.5,
        flatten_at_local_time="20:00",
    )
    name = f"h2_xauusd_overlap_{direction}"
    s = Strategy(
        name=name, version="1.0",
        description=(
            f"H2 XAUUSD London-NY overlap ({direction}): 05:00-13:00 UTC pre-overlap "
            f"range, breakout 13:00-16:00 with M15-EMA200 trend bias + body>=50%. "
            f"Stop 1.2*ATR, target 3*ATR. Flat 20:00 UTC. H1-bias is approximated "
            f"by M15-EMA200 (≈ H1-EMA50 in lookback); news/DXY filters not implemented."
        ),
        pair=PAIR, primary_timeframe=TF, direction=direction,
        entry=entry, filters=filters, exit=exit_spec, risk=risk_spec,
        constraints=constraints,
        metadata=Metadata(tags=["hypothesis_2", "xauusd", "overlap", direction]),
    )
    validate(s, strict=True)
    return s


def run_one(direction, df):
    hdr(f"H2 {direction.upper()} — XAUUSD M15 overlap")
    s = build_strategy(direction)
    print(f"[strategy] {s.name}  genome={s.genome_hash()}", flush=True)

    res = run_splits(s, df, cfg=SplitConfig(0.60, 0.20, 0.20), cost=COST)
    windows = {"IS": res.is_window, "OOS": res.oos_window, "VAL": res.val_window}
    for label, w in windows.items():
        print(fmt(label, w.metrics if w else None), flush=True)
    print(f"  degradation_ratio (OOS/IS) = {res.degradation_ratio:+.3f}", flush=True)

    full_result = run_backtest(s, df, cost=COST)
    base_metrics = compute_metrics(full_result)
    print(fmt("FULL", base_metrics), flush=True)

    if base_metrics.trade_count < 30:
        print(f"  [skip robustness] only {int(base_metrics.trade_count)} trades", flush=True)
        return {"direction": direction, "genome": s.genome_hash(),
                "splits": {k: v.metrics.__dict__ if v else None for k, v in windows.items()},
                "full": base_metrics.__dict__, "skipped_robustness": True}

    report = run_robustness_suite(
        s, df, full_result, base_cost=COST,
        cost_multipliers=(1.0, 1.25, 1.5, 2.0, 3.0), perturbation_pct=0.20,
    )
    print("\n  cost sensitivity:")
    for k, m in report.cost_sensitivity.items():
        print(fmt(k, m))
    print("  regime tercile:")
    for k, m in report.regime_split.items():
        print(fmt(k, m))
    print(f"  bootstrap: {report.bootstrap_sharpe}")
    mc = mc_dropout_trials(full_result, n_trials=MC_TRIALS, dropout_pct=0.10, seed=42)
    print(f"  MC dropout p05={mc.sharpe_floor_p05:+.3f}  pos%={mc.sharpe_positive_pct:.1f}")
    p_val = permutation_test(full_result, n_permutations=MC_TRIALS, seed=42)
    print(f"  permutation p={p_val:.4f}")

    gates = evaluate_robustness_gates(base_metrics, report, RobustnessGateConfig())
    extra = []
    if mc.sharpe_floor_p05 < 0.0: extra.append(f"MC p05 = {mc.sharpe_floor_p05:.2f}")
    if p_val > 0.05: extra.append(f"perm p = {p_val:.4f}")
    all_passed = gates.passed and not extra
    hdr(f"VERDICT ({direction})  {'EDGE SURVIVES' if all_passed else 'EDGE DOES NOT SURVIVE'}")
    for f in gates.failures + extra:
        print(f"    FAIL: {f}")

    return {
        "direction": direction, "genome": s.genome_hash(),
        "splits": {k: v.metrics.__dict__ if v else None for k, v in windows.items()},
        "full": base_metrics.__dict__,
        "cost_sensitivity": {k: v.__dict__ for k, v in report.cost_sensitivity.items()},
        "regime_split": {k: v.__dict__ for k, v in report.regime_split.items()},
        "bootstrap_sharpe": report.bootstrap_sharpe,
        "mc_dropout": {"trials": mc.trials, "mean_sharpe": mc.mean_sharpe,
                       "positive_pct": mc.sharpe_positive_pct, "p05": mc.sharpe_floor_p05},
        "permutation_p": p_val,
        "gate_failures": list(gates.failures), "extra_failures": extra,
        "edge_survives": all_passed,
    }



_h2_build = build_strategy


def build_asian(direction):
    """Pre-registered 2026-11-05: Asian-range breakout at the London open, same filters/exits as H2."""
    s = _h2_build(direction)
    d = s.model_dump()
    d["name"] = f"asian_range_breakout_{direction}"
    d["entry"]["params"].update({"session_start_hour": 0, "range_minutes": 420, "entry_window_minutes": 240})
    d["constraints"]["flatten_at_local_time"] = "16:00"
    d["description"] = "Asian range 00:00-07:00 UTC, breakout 07:00-11:00, trend bias EMA50 (H1) + body>=50%, stop 1.2 ATR, target 3 ATR, flat 16:00 UTC."
    s2 = Strategy(**d); validate(s2, strict=True); return s2

raw = pd.read_csv("/mnt/user-data/uploads/backtestbot/data/XAUUSD_H1_2016_2026.csv")
df = pd.DataFrame({"timestamp_utc": pd.to_datetime(raw["ts"], unit="s", utc=True), "open": raw["open"], "high": raw["high"],
                   "low": raw["low"], "close": raw["close"], "volume": raw["volume"], "spread": SPEC.default_spread}
                  ).drop_duplicates("timestamp_utc").sort_values("timestamp_utc").reset_index(drop=True)
print(f"[data] {len(df):,} H1 bars {df.timestamp_utc.min().date()} -> {df.timestamp_utc.max().date()}", flush=True)
import json
out = {}
for label, builder in (("h2_overlap", build_strategy), ("asian_range", build_asian)):
    for direction in ("long", "short"):
        globals()["build_strategy_active"] = builder
        _orig = globals()["build_strategy"]
        globals()["build_strategy"] = builder
        try:
            out[f"{label}_{direction}"] = run_one(direction, df)
        finally:
            globals()["build_strategy"] = _orig
json.dump(out, open("/tmp/intraday_gold_10yr.json", "w"), indent=2, default=str)
