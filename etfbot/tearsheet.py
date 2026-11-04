"""QuantStats HTML tearsheet: strategy vs buy-and-hold."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def write_html(strategy_equity: pd.Series, benchmark_equity: pd.Series, path: str | Path, title: str) -> str:
    import logging
    import warnings

    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    warnings.filterwarnings("ignore")
    try:
        import quantstats as qs
    except ImportError as e:
        raise RuntimeError("QuantStats is not installed: pip install quantstats") from e
    r = strategy_equity.pct_change().dropna()
    b = benchmark_equity.pct_change().dropna()
    r.name, b.name = "Strategy", "Buy & hold"
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    qs.reports.html(r, benchmark=b, output=str(path), title=title)
    return str(path)
