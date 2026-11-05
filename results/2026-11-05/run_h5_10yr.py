"""Hypothesis 5: XAUUSD H1 trend pullback.

User spec:
  - Trend filter:    close > H1 EMA200 (long) / close < H1 EMA200 (short)
  - Regime filter:   ADX(14) > 25 (trending market only)
  - Entry:           pullback to H1 EMA20 or EMA50 in trend direction
                     (using ema_pullback block with ema_period=50,
                      pullback_atr_mult=0.5; this captures both the
                      uptrend-above-EMA50 condition AND the pullback)
  - Body filter:     entry candle body >= 50% of range
  - Stop:            1.5x ATR(14) on entry bar
  - TP1:             1.5R partial close (engine lacks partial exits;
                     this run uses single 3R target only -- documented)
  - TP2:             3R (single target in this run)
  - Session:         London + NY (07:00-21:00 UTC)
  - Data:            Dukascopy XAUUSD H1, 2025-05 -> 2026-05 (1-year window)

Run:
    .venv/Scripts/python.exe scripts/run_h5_xauusd_h1_pullback.py
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
RUN_ID = f"h5_xauusd_h1_pullback_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

# XAUUSD retail CFD cost model. Spread 0.30 USD, no commission, slippage 2/4 ticks.
SPEC = get_instrument(PAIR)
COST = CostConfig(
    spread_override=SPEC.default_spread,
    commission_per_contract_override=0.0,
    slippage_entry_ticks=2.0,
    slippage_stop_ticks=4.0,
)
MC_TRIALS = 1000


def hdr(s: str) -> None:
    print("\n" + "=" * 100, flush=True)
    print(s, flush=True)
    print("=" * 100, flush=True)


def fmt(name: str, m) -> str:
    if m is None:
        return f"  {name}: <empty>"
    return (
        f"  {name:<14}  trades={int(m.trade_count):>4}  "
        f"win%={m.win_rate * 100:>5.1f}  "
        f"PF={m.profit_factor:>5.2f}  "
        f"Sharpe={m.sharpe:>+6.2f}  "
        f"DD={m.max_drawdown_pct:>5.2f}%  "
        f"netPnL=${m.net_pnl:>11,.0f}"
    )


def build_strategy(direction: str) -> Strategy:
    """Build the H5 pullback strategy for `direction` ('long' or 'short')."""
    dir_int = 1 if direction == "long" else -1

    entry = BlockRef(
        block="ema_pullback",
        params={
            "ema_period": 50,
            "pullback_atr_mult": 0.5,
            "rsi_period": 14,
            "rsi_long_max": 50,    # slightly looser than block default (45)
            "rsi_short_min": 50,   # slightly looser than block default (55)
            "atr_period": 14,
        },
    )

    # Combined filters: EMA200 trend confirmation + ADX>25 regime + body>=50%
    # All composed via the new feature_filter block.
    trend_feature = "close_above_ema200" if direction == "long" else "close_below_ema200"
    filters = [
        BlockRef(
            block="feature_filter",
            params={"features": f"{trend_feature},adx_above_25,body_ratio_above_50"},
        ),
        # Restrict to London + NY sessions (07:00 - 21:00 UTC). The clock_window
        # filter takes one window; we set it to the union 07:00-21:00.
        BlockRef(
            block="clock_window",
            params={
                "tz": "UTC",
                "start_hour": 7, "start_minute": 0,
                "end_hour": 21, "end_minute": 0,
            },
        ),
    ]

    exit_spec = ExitSpec(
        block="atr_stop_target",
        params={
            "atr_period": 14,
            "stop_atr_mult": 1.5,
            "target_atr_mult": 3.0,   # 3R target (TP2 leg; TP1 partial not supported)
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
        max_trades_per_direction_per_day=2,
        daily_loss_lockout_pct=2.5,
        flatten_at_local_time=None,    # H1 swing-ish; no EOD flat
    )
    name = f"h5_xauusd_h1_pullback_{direction}"
    s = Strategy(
        name=name, version="1.0",
        description=(
            f"H5 user spec ({direction}): ema_pullback(50) entry + "
            f"feature_filter(close_above_ema200, adx>25, body>=50%) + "
            f"London+NY session window. Stop 1.5*ATR, target 3*ATR. "
            f"TP1 partial-close not implemented in engine -- single 3R target only."
        ),
        pair=PAIR, primary_timeframe=TF, direction=direction,
        entry=entry, filters=filters, exit=exit_spec, risk=risk_spec,
        constraints=constraints,
        metadata=Metadata(tags=["hypothesis_5", "xauusd", direction]),
    )
    validate(s, strict=True)
    return s


def run_one(direction: str, df: pd.DataFrame) -> dict:
    hdr(f"H5 {direction.upper()} — XAUUSD H1 trend pullback")
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
        print(f"  [skip robustness] only {int(base_metrics.trade_count)} trades — sample too small", flush=True)
        return {
            "direction": direction, "genome": s.genome_hash(),
            "splits": {k: v.metrics.__dict__ if v else None for k, v in windows.items()},
            "full": base_metrics.__dict__,
            "skipped_robustness": True,
        }

    print("\n  [robustness suite]", flush=True)
    report = run_robustness_suite(
        s, df, full_result, base_cost=COST,
        cost_multipliers=(1.0, 1.25, 1.5, 2.0, 3.0),
        perturbation_pct=0.20,
    )
    print("  cost sensitivity:", flush=True)
    for k, m in report.cost_sensitivity.items():
        print(fmt(k, m), flush=True)
    print("  regime tercile:", flush=True)
    for k, m in report.regime_split.items():
        print(fmt(k, m), flush=True)
    print(f"  bootstrap: {report.bootstrap_sharpe}", flush=True)

    mc = mc_dropout_trials(full_result, n_trials=MC_TRIALS, dropout_pct=0.10, seed=42)
    print(f"  MC dropout p05={mc.sharpe_floor_p05:+.3f}  pos%={mc.sharpe_positive_pct:.1f}", flush=True)
    p_val = permutation_test(full_result, n_permutations=MC_TRIALS, seed=42)
    print(f"  permutation p={p_val:.4f}", flush=True)

    gates = evaluate_robustness_gates(base_metrics, report, RobustnessGateConfig())
    extra_fails: list[str] = []
    if mc.sharpe_floor_p05 < 0.0:
        extra_fails.append(f"MC p05 = {mc.sharpe_floor_p05:.2f}")
    if p_val > 0.05:
        extra_fails.append(f"permutation p = {p_val:.4f}")
    all_passed = gates.passed and not extra_fails

    hdr(f"VERDICT ({direction})")
    print(f"  {'EDGE SURVIVES' if all_passed else 'EDGE DOES NOT SURVIVE'}", flush=True)
    for f in gates.failures + extra_fails:
        print(f"    FAIL: {f}", flush=True)

    return {
        "direction": direction,
        "genome": s.genome_hash(),
        "splits": {k: v.metrics.__dict__ if v else None for k, v in windows.items()},
        "full": base_metrics.__dict__,
        "cost_sensitivity": {k: v.__dict__ for k, v in report.cost_sensitivity.items()},
        "regime_split": {k: v.__dict__ for k, v in report.regime_split.items()},
        "bootstrap_sharpe": report.bootstrap_sharpe,
        "mc_dropout": {
            "trials": mc.trials, "mean_sharpe": mc.mean_sharpe,
            "positive_pct": mc.sharpe_positive_pct, "p05": mc.sharpe_floor_p05,
        },
        "permutation_p": p_val,
        "gate_failures": list(gates.failures),
        "extra_failures": extra_fails,
        "edge_survives": all_passed,
    }



hdr("H5 on 10 years of Dukascopy XAUUSD H1 (2016-2026), frozen spec")
raw = pd.read_csv("/mnt/user-data/uploads/backtestbot/data/XAUUSD_H1_2016_2026.csv")
df = pd.DataFrame({
    "timestamp_utc": pd.to_datetime(raw["ts"], unit="s", utc=True),
    "open": raw["open"], "high": raw["high"], "low": raw["low"], "close": raw["close"],
    "volume": raw["volume"], "spread": SPEC.default_spread,
}).drop_duplicates("timestamp_utc").sort_values("timestamp_utc").reset_index(drop=True)
print(f"[data] {len(df):,} bars  {df.timestamp_utc.min().date()} -> {df.timestamp_utc.max().date()}", flush=True)
results = {"long": run_one("long", df), "short": run_one("short", df)}
import json
json.dump(results, open("/tmp/h5_10yr.json", "w"), indent=2, default=str)
