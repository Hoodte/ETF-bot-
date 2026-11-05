"""Config schema for the intraday search. Lookbacks are in BARS of the dataset's timeframe."""
from __future__ import annotations

import copy
import hashlib
import json
import random

FAMILIES = ["breakout", "momentum", "rsi_revert", "band_fade", "orb", "pdhl"]
PARAMS = {
    "breakout": {"n": [12, 24, 48, 96]},
    "momentum": {"n": [4, 12, 24, 48], "z": [1.0, 1.5, 2.0]},
    "rsi_revert": {"p": [2, 4, 14], "th": [10, 20, 30]},
    "band_fade": {"n": [20, 50, 100], "k": [2.0, 2.5, 3.0]},
    "orb": {"session": ["london", "ny", "utc0"], "minutes": [15, 30, 60, 120]},
    "pdhl": {"mode": ["follow", "fade"]},       # first break of the previous UTC day's high/low
}
# opening-range sessions in local exchange time (daylight saving handled)
SESSION_OPEN = {"utc0": ("UTC", 0), "london": ("Europe/London", 8 * 60), "ny": ("America/New_York", 9 * 60 + 30)}
ALLOWED = {
    "trend": ["none", "with", "against"],          # 200-bar EMA: trade with it, against it, or ignore
    "vol": ["any", "high", "low"],                 # ATR percentile vs last 500 bars above/below 0.5
    "session": ["all", "asia", "london", "ny"],    # entry window (UTC): 0-7, 7-13, 13-20
    "direction": ["both", "long", "short"],
    "exit": ["bracket", "time"],
    "bracket": [(1.0, 1.0), (1.0, 2.0), (1.5, 1.5), (2.0, 3.0)],   # stop, target in ATR(14) of the signal bar
    "hold": [4, 12, 24, 48],                        # max bars in a trade
    "eod": [False, True],                           # flat by the session end
}
SESSION_HOURS = {"asia": (0, 7), "london": (7, 13), "ny": (13, 20)}


def param_grid(family: str) -> list[dict]:
    keys = list(PARAMS[family])
    out = [{}]
    for k in keys:
        out = [dict(o, **{k: v}) for o in out for v in PARAMS[family][k]]
    return [dict(o, family=family) for o in out]


def validate(c: dict, datasets: dict) -> list[str]:
    e = []
    if c["dataset"] not in datasets:
        e.append("unknown dataset")
        return e
    tf, session_end = datasets[c["dataset"]][1], datasets[c["dataset"]][3]
    s = c["signal"]
    if s not in param_grid(s["family"]):
        e.append(f"bad signal params {s}")
    for k in ("trend", "vol", "session", "direction", "exit", "hold", "eod"):
        if c[k] not in ALLOWED[k]:
            e.append(f"{k}={c[k]!r} not allowed")
    if c["exit"] == "bracket" and tuple(c["bracket"]) not in ALLOWED["bracket"]:
        e.append("bad bracket")
    if s["family"] == "orb":
        if s["minutes"] < tf or s["minutes"] % tf or SESSION_OPEN[s["session"]][1] % tf:
            e.append(f"opening range of {s['minutes']} min at that open impossible on {tf}-min bars")
        if c["session"] != "all":
            e.append("orb sets its own session; session filter must be 'all'")
        if s["session"] == "utc0" and session_end != 24:
            e.append("utc0 range only for 24h markets")
    return e


def normalise(c: dict) -> dict:
    c = copy.deepcopy(c)
    if c["exit"] == "time":
        c["bracket"] = None
    else:
        c["bracket"] = list(c["bracket"])
    return c


def config_id(c: dict) -> str:
    return hashlib.sha256(json.dumps(normalise(c), sort_keys=True).encode()).hexdigest()[:12]


def describe(c: dict) -> str:
    s = c["signal"]
    p = ",".join(f"{k}={v}" for k, v in s.items() if k != "family")
    ex = f"bracket{tuple(c['bracket'])}" if c["exit"] == "bracket" else "time"
    return (f"{c['dataset']}|{s['family']}({p})|trend:{c['trend']}|vol:{c['vol']}|sess:{c['session']}|"
            f"{c['direction']}|{ex}|hold{c['hold']}{'|eod' if c['eod'] else ''}")


DEFAULT_SIGNAL = {"breakout": {"family": "breakout", "n": 24}, "momentum": {"family": "momentum", "n": 12, "z": 1.5},
                  "rsi_revert": {"family": "rsi_revert", "p": 2, "th": 10}, "band_fade": {"family": "band_fade", "n": 50, "k": 2.5},
                  "orb": {"family": "orb", "session": "london", "minutes": 60},
                  "pdhl": {"family": "pdhl", "mode": "follow"}}
HYPOTHESES = {
    "breakout": "A close beyond the recent range starts a short move in that direction.",
    "momentum": "An unusually large move over the last N bars tends to continue briefly.",
    "rsi_revert": "Very short-term extremes (RSI) snap back.",
    "band_fade": "Closes far outside a rolling band revert toward the mean.",
    "orb": "The first break of a session's opening range sets the direction for the next hours.",
    "pdhl": "The first break of yesterday's high or low either runs (stops triggered) or fails and reverses.",
}


def baseline(dataset: str, family: str) -> dict:
    trend_like = family in ("breakout", "momentum", "orb", "pdhl")
    return {"dataset": dataset, "signal": dict(DEFAULT_SIGNAL[family]), "trend": "none", "vol": "any", "session": "all",
            "direction": "both", "exit": "bracket" if trend_like else "time", "bracket": [1.0, 2.0] if trend_like else None,
            "hold": 24 if trend_like else 12, "eod": False}


def generate(datasets: dict, samples: int, seed: int):
    seen = set()
    def emit(stage, c):
        r = validate(c, datasets)
        if r:
            return stage, c, "invalid", r, None
        n = normalise(c); cid = config_id(n)
        if cid in seen:
            return stage, n, "duplicate", [], cid
        seen.add(cid)
        return stage, n, "valid", [], cid
    bases = []
    for d in datasets:
        for f in FAMILIES:
            b = baseline(d, f)
            if f == "orb" and datasets[d][1] > 60:
                continue
            if f == "orb" and b["signal"]["minutes"] < datasets[d][1]:
                b["signal"]["minutes"] = datasets[d][1]
            bases.append(b)
            yield emit("baseline", b)
    for b in bases:
        def var(**kw):
            c = copy.deepcopy(b); c.update(kw); return emit("one_at_a_time", c)
        for s in param_grid(b["signal"]["family"]):
            yield var(signal=s)
        for k in ("trend", "vol", "session", "direction", "hold", "eod"):
            for v in ALLOWED[k]:
                if v != b[k]:
                    yield var(**{k: v})
        for br in ALLOWED["bracket"]:
            yield var(exit="bracket", bracket=list(br))
        yield var(exit="time", bracket=None)
    rng = random.Random(seed)
    for _ in range(samples):
        f = rng.choice(FAMILIES)
        ex = rng.choice(ALLOWED["exit"])
        c = {"dataset": rng.choice(list(datasets)), "signal": rng.choice(param_grid(f)),
             "trend": rng.choice(ALLOWED["trend"]), "vol": rng.choice(ALLOWED["vol"]),
             "session": "all" if f == "orb" else rng.choice(ALLOWED["session"]),
             "direction": rng.choice(ALLOWED["direction"]), "exit": ex,
             "bracket": list(rng.choice(ALLOWED["bracket"])) if ex == "bracket" else None,
             "hold": rng.choice(ALLOWED["hold"]), "eod": rng.choice(ALLOWED["eod"])}
        yield emit("sampled", c)
