from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(path: str | Path = "config.yaml") -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    validate(cfg)
    return cfg


def validate(cfg: dict[str, Any]) -> None:
    if cfg.get("mode") not in ("paper", "live"):
        raise ValueError("mode must be 'paper' or 'live'")
    for name, inst in cfg["instruments"].items():
        w = sum(inst["proxy"].values())
        if abs(w - 1.0) > 1e-9:
            raise ValueError(f"{name}: proxy weights sum to {w}, must be 1")
    r = cfg["risk"]
    if not 0 < r["max_position_frac"] <= 1:
        raise ValueError("risk.max_position_frac must be in (0, 1]")
    if not 0 < r["drawdown_pause_frac"] < 1:
        raise ValueError("risk.drawdown_pause_frac must be in (0, 1)")
