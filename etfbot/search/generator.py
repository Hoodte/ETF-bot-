"""Reproducible config generation: baselines -> one-at-a-time variations -> seeded random combinations.

Every attempt (valid, invalid or duplicate) is yielded with its status so the ledger records the
whole search history.
"""
from __future__ import annotations

import copy
import random

from . import schema as S

DEFAULT_SIG = {"sma": {"type": "sma", "n": 200}, "ma_cross": {"type": "ma_cross", "fast": 50, "slow": 200},
               "tsmom": {"type": "tsmom", "n": 252}, "breakout": {"type": "breakout", "n": 120},
               "rel_mom": {"type": "rel_mom", "n": 126}}


def _default_topn(universe: str) -> str:
    n = len(S.UNIVERSES[universe])
    return "top3" if n >= 5 else "top1"


def baseline(universe: str, family: str) -> dict:
    sel = _default_topn(universe) if family == "rel_mom" else "all"
    return {"universe": universe, "family": family, "signal": dict(DEFAULT_SIG[family]), "combo": "single",
            "second": None, "selection": sel, "sizing": "equal", "vol_lookback": None, "max_weight": None,
            "max_equity": None, "min_cash": 0.0, "rebalance": "monthly", "entry_exit": "scheduled",
            "defensive": "cash"}


def baselines() -> list[dict]:
    out = []
    for u in S.UNIVERSES:
        for f in S.FAMILIES:
            c = baseline(u, f)
            if not S.validate(c):
                out.append(c)
    return out


def one_at_a_time(base: dict) -> list[dict]:
    """Change exactly one component of a baseline at a time."""
    out = []
    def var(**kw):
        c = copy.deepcopy(base); c.update(kw); out.append(c)
    for s in S.signal_params(base["family"]):
        if s != base["signal"]:
            var(signal=s)
    if base["family"] != "rel_mom":
        for f in S.ABS_SIGNALS:
            if f != base["family"]:
                var(combo="and", second=dict(DEFAULT_SIG[f]))
        for s in S.signal_params("rel_mom"):
            var(combo="filter_rank", second=s, selection=_default_topn(base["universe"]))
    for sel in S.ALLOWED["selection"]:
        if sel != base["selection"]:
            var(selection=sel)
    for lb in S.ALLOWED["vol_lookback"][1:]:
        var(sizing="inv_vol", vol_lookback=lb)
    var(sizing="class_fixed")
    for k in ("max_weight", "max_equity", "min_cash", "rebalance", "entry_exit", "defensive"):
        for v in S.ALLOWED[k]:
            if v != base[k]:
                var(**{k: v})
    return out


def random_config(rng: random.Random) -> dict:
    u = rng.choice(list(S.UNIVERSES))
    f = rng.choice(S.FAMILIES)
    combo = "single" if f == "rel_mom" else rng.choice(S.ALLOWED["combo"])
    second = None
    if combo == "and":
        second = rng.choice(S.signal_params(rng.choice([x for x in S.ABS_SIGNALS])))
    elif combo == "filter_rank":
        second = rng.choice(S.signal_params("rel_mom"))
    sizing = rng.choice(S.ALLOWED["sizing"])
    ranked = f == "rel_mom" or combo == "filter_rank"
    return {"universe": u, "family": f, "signal": rng.choice(S.signal_params(f)), "combo": combo, "second": second,
            "selection": rng.choice([x for x in S.ALLOWED["selection"] if x != "all"]) if ranked else "all",
            "sizing": sizing,
            "vol_lookback": rng.choice(S.ALLOWED["vol_lookback"][1:]) if sizing == "inv_vol" else None,
            "max_weight": rng.choice(S.ALLOWED["max_weight"]), "max_equity": rng.choice(S.ALLOWED["max_equity"]),
            "min_cash": rng.choice(S.ALLOWED["min_cash"]), "rebalance": rng.choice(S.ALLOWED["rebalance"]),
            "entry_exit": rng.choice(S.ALLOWED["entry_exit"]), "defensive": rng.choice(S.ALLOWED["defensive"])}


def generate(samples: int = 3000, seed: int = 42):
    """Yield (stage, config, status, reasons, config_id). status: valid | invalid | duplicate."""
    seen: set[str] = set()
    def emit(stage, c):
        reasons = S.validate(c)
        if reasons:
            return (stage, c, "invalid", reasons, None)
        n = S.normalise(c)
        cid = S.config_id(n)
        if cid in seen:
            return (stage, n, "duplicate", [], cid)
        seen.add(cid)
        return (stage, n, "valid", [], cid)
    bases = baselines()
    for b in bases:
        yield emit("baseline", b)
    for b in bases:
        for c in one_at_a_time(b):
            yield emit("one_at_a_time", c)
    rng = random.Random(seed)
    for _ in range(samples):
        yield emit("sampled", random_config(rng))
