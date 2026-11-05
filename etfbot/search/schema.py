"""Strategy configuration schema for the ETF strategy search.

A config is a plain dict (JSON-serialisable). `validate()` rejects impossible combinations,
`normalise()` collapses equivalent configs to one canonical form, and `config_id()` hashes that
canonical form so duplicates share an ID.
"""
from __future__ import annotations

import hashlib
import json

# ------------------------------------------------------------------ universes
# US-listed ETFs used for research (long, clean histories). Live trading in the UK would use the
# matching UCITS lines. All tickers exist today -> SURVIVORSHIP BIAS FLAG: delisted ETFs are absent.
ASSET_CLASS = {
    "SPY": "equity", "QQQ": "equity", "IWM": "equity", "MDY": "equity",
    "EFA": "equity", "EEM": "equity", "VGK": "equity", "EWJ": "equity",
    "XLK": "equity", "XLF": "equity", "XLE": "equity", "XLV": "equity", "XLY": "equity",
    "XLP": "equity", "XLI": "equity", "XLU": "equity", "XLB": "equity",
    "TLT": "bonds", "IEF": "bonds", "AGG": "bonds", "LQD": "bonds", "TIP": "bonds", "SHY": "bonds",
    "GLD": "gold", "DBC": "commodities", "VNQ": "real_estate",
}
UNIVERSES = {
    "us_equity": ["SPY", "QQQ", "IWM", "MDY"],
    "global_equity": ["SPY", "EFA", "EEM", "VGK", "EWJ"],
    "sectors": ["XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB"],
    "bonds": ["TLT", "IEF", "AGG", "LQD", "TIP"],
    "gold": ["GLD"],
    "multi_asset": ["SPY", "EFA", "EEM", "TLT", "IEF", "GLD", "DBC", "VNQ"],
}
DEFENSIVE_TICKER = "SHY"
# fixed asset-class weights (multi_asset only); unused class weight goes to the defensive asset
CLASS_WEIGHTS = {"equity": 0.40, "bonds": 0.30, "gold": 0.10, "commodities": 0.10, "real_estate": 0.10}

# ------------------------------------------------------------------ allowed values
SMA = [50, 100, 150, 200]
MOM = [63, 126, 189, 252]
BRK = [20, 60, 120]
ABS_SIGNALS = ["sma", "ma_cross", "tsmom", "breakout"]          # absolute (on/off per ETF)
FAMILIES = ABS_SIGNALS + ["rel_mom"]                              # rel_mom = ranking only
ALLOWED = {
    "universe": list(UNIVERSES),
    "family": FAMILIES,
    "combo": ["single", "and", "filter_rank"],
    "selection": ["all", "top1", "top2", "top3", "top5", "top_per_class"],
    "sizing": ["equal", "class_fixed", "inv_vol"],
    "vol_lookback": [None, 20, 60, 120],
    "max_weight": [None, 0.25, 0.50],
    "max_equity": [None, 0.60],
    "min_cash": [0.0, 0.10],
    "rebalance": ["weekly", "biweekly", "monthly", "quarterly"],
    "entry_exit": ["scheduled", "confirm2", "buffer"],
    "defensive": ["cash", "shy"],
}
SCHEMA_VERSION = 1


def signal_params(kind: str) -> list[dict]:
    """All allowed parameter sets for one signal type."""
    if kind == "sma":
        return [{"type": "sma", "n": n} for n in SMA]
    if kind == "ma_cross":
        return [{"type": "ma_cross", "fast": f, "slow": s} for f in SMA for s in SMA if f < s]
    if kind == "tsmom":
        return [{"type": "tsmom", "n": n} for n in MOM]
    if kind == "breakout":
        return [{"type": "breakout", "n": n} for n in BRK]
    if kind == "rel_mom":
        return [{"type": "rel_mom", "n": n} for n in MOM]
    raise ValueError(kind)


def lookbacks(cfg: dict) -> int:
    """Longest look-back the config needs (warm-up)."""
    out = 0
    for s in (cfg["signal"], cfg.get("second")):
        if s:
            out = max(out, s.get("n", 0), s.get("slow", 0))
    if cfg["sizing"] == "inv_vol":
        out = max(out, cfg["vol_lookback"])
    return out


def has_ranking(cfg: dict) -> bool:
    return cfg["signal"]["type"] == "rel_mom" or cfg["combo"] == "filter_rank"


def top_n(cfg: dict) -> int | None:
    s = cfg["selection"]
    return int(s[3:]) if s.startswith("top") and s != "top_per_class" else None


def buffer_exit_rank(n: int) -> int:
    """Rank buffer: enter in the top n, exit only when the ETF drops below the top n + 2."""
    return n + 2


def classes(universe: str) -> set[str]:
    return {ASSET_CLASS[t] for t in UNIVERSES[universe]}


# ------------------------------------------------------------------ validation
def validate(cfg: dict) -> list[str]:
    """Return a list of reasons the config is invalid (empty = valid)."""
    e = []
    for k, allowed in ALLOWED.items():
        if k in cfg and cfg[k] not in allowed:
            e.append(f"{k}={cfg[k]!r} not allowed")
    sig, sec, combo = cfg["signal"], cfg.get("second"), cfg["combo"]
    if sig["type"] != cfg["family"]:
        e.append("signal type must match family")
    if sig not in signal_params(sig["type"]):
        e.append(f"bad signal params {sig}")
    if sig["type"] == "ma_cross" and not sig["fast"] < sig["slow"]:
        e.append("fast MA must be shorter than slow MA")
    if combo == "single" and sec:
        e.append("single combo takes no second signal")
    if combo == "and":
        if sig["type"] == "rel_mom":
            e.append("AND needs two absolute signals")
        if not sec or sec["type"] not in ABS_SIGNALS or sec not in signal_params(sec["type"]):
            e.append("AND needs a valid absolute second signal")
        elif sec == sig:
            e.append("AND of a signal with itself")
    if combo == "filter_rank":
        if sig["type"] == "rel_mom":
            e.append("filter_rank needs an absolute eligibility signal first")
        if not sec or sec["type"] != "rel_mom" or sec not in signal_params("rel_mom"):
            e.append("filter_rank needs a rel_mom ranking second")
    n_assets = len(UNIVERSES[cfg["universe"]])
    sel, n = cfg["selection"], top_n(cfg)
    if sig["type"] == "rel_mom" and sel == "all":
        e.append("rel_mom ranking is unused when holding all ETFs (same as the benchmark)")
    if not has_ranking(cfg) and sel != "all":
        e.append("top-N / per-class selection needs a ranking")
    if n is not None and n >= n_assets:
        e.append(f"top{n} needs more than {n} ETFs in the universe")
    if sel == "top_per_class" and len(classes(cfg["universe"])) < 2:
        e.append("top_per_class needs several asset classes")
    if cfg["sizing"] == "inv_vol" and cfg.get("vol_lookback") is None:
        e.append("inv_vol sizing needs a volatility look-back")
    if cfg["sizing"] == "class_fixed" and cfg["universe"] != "multi_asset":
        e.append("class_fixed weights only defined for multi_asset")
    if cfg["max_equity"] is not None and "equity" not in classes(cfg["universe"]):
        e.append("max_equity on a universe with no equities")
    if cfg["entry_exit"] == "buffer":
        if n is None:
            e.append("rank buffer needs top-N selection")
        elif buffer_exit_rank(n) <= n:
            e.append("buffer exit rank must exceed entry rank")
    return e


# ------------------------------------------------------------------ canonical form
def normalise(cfg: dict) -> dict:
    """Collapse settings that cannot change the result, so equivalent configs dedupe."""
    c = json.loads(json.dumps(cfg))
    n_assets = len(UNIVERSES[c["universe"]])
    if c["sizing"] != "inv_vol":
        c["vol_lookback"] = None
    one_holding = n_assets == 1 or c["selection"] == "top1"
    if one_holding and c["sizing"] in ("equal", "inv_vol"):
        c["sizing"], c["vol_lookback"] = "equal", None          # one ETF: weight is 1 either way
    if c["max_weight"] is not None and one_holding is False and c["selection"] != "all":
        n = top_n(c)
        if n and c["sizing"] == "equal" and 1 / n <= c["max_weight"]:
            c["max_weight"] = None                               # cap never binds
    if c["max_weight"] == 0.5 and c["sizing"] == "equal" and c["selection"] == "all" and n_assets >= 2:
        c["max_weight"] = None                                   # equal slots of 1/M never exceed 0.5
    if c["max_weight"] == 0.25 and c["sizing"] == "equal" and c["selection"] == "all" and n_assets >= 4:
        c["max_weight"] = None
    if c["combo"] == "filter_rank" and c["selection"] == "all":
        c["combo"], c["second"] = "single", None                 # ranking unused when holding every qualifier
    if c["combo"] == "single":
        c["second"] = None
    return c


def config_id(cfg: dict) -> str:
    canon = json.dumps(normalise(cfg), sort_keys=True)
    return hashlib.sha256(canon.encode()).hexdigest()[:12]


def describe(cfg: dict) -> str:
    s = cfg["signal"]
    p = ",".join(f"{k}={v}" for k, v in s.items() if k != "type")
    out = f"{cfg['universe']}|{s['type']}({p})"
    if cfg.get("second"):
        q = ",".join(f"{k}={v}" for k, v in cfg["second"].items() if k != "type")
        out += f"{'&' if cfg['combo'] == 'and' else '>rank:'}{cfg['second']['type']}({q})"
    out += f"|{cfg['selection']}|{cfg['sizing']}{cfg['vol_lookback'] or ''}"
    if cfg["max_weight"]:
        out += f"|cap{cfg['max_weight']}"
    if cfg["max_equity"]:
        out += f"|eq<={cfg['max_equity']}"
    if cfg["min_cash"]:
        out += f"|cash>={cfg['min_cash']}"
    return out + f"|{cfg['rebalance']}|{cfg['entry_exit']}|{cfg['defensive']}"


HYPOTHESES = {
    "sma": "Assets trading above their long moving average tend to keep rising; stepping aside below it avoids the worst of big declines.",
    "ma_cross": "When a fast average is above a slow one the trend is up; crossovers react more slowly than a price/average test but whipsaw less.",
    "tsmom": "An asset with a positive trailing return tends to keep a positive return (time-series momentum).",
    "rel_mom": "Assets that outperformed their peers recently tend to keep outperforming (cross-sectional momentum).",
    "breakout": "A close above the recent highest close signals a new uptrend; exit when price breaks the recent low.",
}
