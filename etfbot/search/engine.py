"""Backtest engine for search configs.

Execution model (fixed for every candidate):
  * signals use data up to and including the close of a rebalance day;
  * trades fill at the NEXT session's open; positions earn open-to-open returns;
  * costs = cost_bps per unit of weight traded (risky ETFs and the defensive ETF); cash moves are free;
  * between rebalances, weights drift with prices;
  * cash earns 0% (conservative);
  * prices are dividend- and split-adjusted (Yahoo auto_adjust, applied to opens and closes alike).
Eligibility on day t uses only data up to t: the ETF must have a price, enough history for every
look-back in the config, and a 60-day median dollar volume of at least MIN_DOLLAR_VOL.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import schema

MIN_DOLLAR_VOL = 5e6
LIQ_WINDOW = 60


@dataclass
class Panel:
    universe: str
    dates: pd.DatetimeIndex
    tickers: list[str]
    close: np.ndarray            # T x A
    g: np.ndarray                # T x A open-to-open return from open t to open t+1 (0 if missing)
    g_def: np.ndarray            # T defensive ETF open-to-open return
    def_ok: np.ndarray           # T bool: defensive ETF tradable
    hist: np.ndarray             # T x A count of valid closes so far
    liquid: np.ndarray           # T x A bool
    classes: list[str]
    _cache: dict = field(default_factory=dict)

    # ---------------- signals (bool T x A, NaN-safe -> False) and scores
    def sma(self, n):
        k = ("sma", n)
        if k not in self._cache:
            c = pd.DataFrame(self.close)
            self._cache[k] = c.rolling(n, min_periods=n).mean().to_numpy()
        return self._cache[k]

    def signal(self, s: dict) -> np.ndarray:
        k = ("sig", tuple(sorted(s.items())))
        if k in self._cache:
            return self._cache[k]
        c = self.close
        with np.errstate(invalid="ignore"):
            if s["type"] == "always":                       # benchmark: every eligible ETF qualifies
                out = np.ones(c.shape, dtype=bool)
            elif s["type"] == "sma":
                out = c > self.sma(s["n"])
            elif s["type"] == "ma_cross":
                out = self.sma(s["fast"]) > self.sma(s["slow"])
            elif s["type"] == "tsmom":
                out = self.momentum(s["n"]) > 0
            elif s["type"] == "breakout":
                out = self._donchian(s["n"])
            else:
                raise ValueError(s)
        out = np.where(np.isnan(c), False, out)
        self._cache[k] = out
        return out

    def momentum(self, n):
        k = ("mom", n)
        if k not in self._cache:
            c = pd.DataFrame(self.close)
            self._cache[k] = (c / c.shift(n) - 1).to_numpy()
        return self._cache[k]

    def vol(self, n):
        k = ("vol", n)
        if k not in self._cache:
            c = pd.DataFrame(self.close)
            self._cache[k] = c.pct_change(fill_method=None).rolling(n, min_periods=n).std().to_numpy()
        return self._cache[k]

    def _donchian(self, n):
        c = pd.DataFrame(self.close)
        hi = c.rolling(n, min_periods=n).max().shift(1).to_numpy()
        lo = c.rolling(n, min_periods=n).min().shift(1).to_numpy()
        cv = self.close
        out = np.zeros(cv.shape, dtype=bool)
        state = np.zeros(cv.shape[1], dtype=bool)
        for t in range(cv.shape[0]):
            with np.errstate(invalid="ignore"):
                up, dn = cv[t] > hi[t], cv[t] < lo[t]
            state = np.where(up, True, np.where(dn, False, state))
            state &= ~np.isnan(cv[t])
            out[t] = state
        return out


def load_ohlcv(path="data/search_ohlcv.pkl") -> pd.DataFrame:
    return pd.read_pickle(path)


def data_version(raw: pd.DataFrame) -> str:
    arr = np.nan_to_num(raw[["Open", "Close"]].to_numpy(dtype=float)).round(4)
    h = hashlib.sha256(arr.tobytes()).hexdigest()[:10]
    return f"yahoo-adj-{raw.index[-1].date()}-{h}"


def build_panel(raw: pd.DataFrame, universe: str, end: str | None = None) -> Panel:
    """end: last date the panel may contain (search runs stop before the holdout)."""
    if end is not None:
        raw = raw.loc[:end]
    tk = schema.UNIVERSES[universe]
    o, c, v = raw["Open"][tk], raw["Close"][tk], raw["Volume"][tk]
    keep = c.notna().any(axis=1)
    o, c, v = o[keep], c[keep], v[keep]
    g = (o.shift(-1) / o - 1).where(o.notna() & o.shift(-1).notna(), 0.0).fillna(0.0)
    dv = (c * v).rolling(LIQ_WINDOW, min_periods=LIQ_WINDOW).median()
    d_o = raw["Open"][schema.DEFENSIVE_TICKER].reindex(c.index)
    gd = (d_o.shift(-1) / d_o - 1).fillna(0.0)
    d_hist = raw["Close"][schema.DEFENSIVE_TICKER].reindex(c.index).notna().cumsum()
    return Panel(universe=universe, dates=c.index, tickers=tk, close=c.to_numpy(float), g=g.to_numpy(float),
                 g_def=gd.to_numpy(float), def_ok=(d_hist >= LIQ_WINDOW).to_numpy(),
                 hist=c.notna().cumsum().to_numpy(), liquid=(dv >= MIN_DOLLAR_VOL).to_numpy(),
                 classes=[schema.ASSET_CLASS[t] for t in tk])


def rebalance_mask(dates: pd.DatetimeIndex, rule: str) -> np.ndarray:
    """True on the trading day whose close generates the signal. Calendar = the data's own trading days."""
    s = pd.Series(dates, index=dates)
    nxt = s.shift(-1)
    week = (dates - pd.Timestamp("2000-01-03")).days // 7
    nweek = pd.Index(week).to_series().shift(-1).to_numpy()
    last_of_week = week != nweek
    if rule == "weekly":
        m = last_of_week
    elif rule == "biweekly":
        m = last_of_week & (week % 2 == 1)
    elif rule == "monthly":
        m = (dates.month != nxt.dt.month).to_numpy()
    elif rule == "quarterly":
        m = (dates.month != nxt.dt.month).to_numpy() & np.isin(dates.month, [3, 6, 9, 12])
    else:
        raise ValueError(rule)
    m = np.array(m, dtype=bool)
    m[-1] = False          # no next open to fill at
    return m


# ------------------------------------------------------------------ target weights
def _targets(cfg, p: Panel, i: int, held: np.ndarray, prev_qual: np.ndarray, lb: int):
    A = len(p.tickers)
    elig = p.liquid[i] & (p.hist[i] >= max(lb, 1)) & ~np.isnan(p.close[i])
    qual = elig.copy()
    if cfg["signal"]["type"] != "rel_mom":
        qual &= p.signal(cfg["signal"])[i]
    if cfg["combo"] == "and":
        qual &= p.signal(cfg["second"])[i]
    raw_qual = qual.copy()
    if cfg["entry_exit"] == "confirm2":
        qual &= held | prev_qual                     # new entries need two consecutive qualifying checks
    sel = np.zeros(A, dtype=bool)
    selection, n = cfg["selection"], schema.top_n(cfg)
    if schema.has_ranking(cfg):
        rk = cfg["signal"] if cfg["signal"]["type"] == "rel_mom" else cfg["second"]
        score = p.momentum(rk["n"])[i]
        qual &= ~np.isnan(score)
        order = [a for a in np.argsort(-np.where(qual, score, -np.inf), kind="stable") if qual[a]]  # ties -> ticker order
    if selection == "all":
        sel = qual
        slots = max(int(elig.sum()), 1)
    elif selection == "top_per_class":
        present = sorted({p.classes[a] for a in range(A) if elig[a]})
        for k in present:
            for a in order:
                if p.classes[a] == k:
                    sel[a] = True
                    break
        slots = max(len(present), 1)
    else:
        if cfg["entry_exit"] == "buffer":
            keep = [a for r, a in enumerate(order) if held[a] and r < schema.buffer_exit_rank(n)]
            fill = [a for a in order if a not in keep][: max(n - len(keep), 0)]
            chosen = keep + fill
        else:
            chosen = order[:n]
        sel[chosen] = True
        slots = n
    w = np.zeros(A)
    if sel.any():
        if cfg["sizing"] == "class_fixed":
            present = {p.classes[a] for a in range(A) if elig[a]}
            tot = sum(schema.CLASS_WEIGHTS[k] for k in present)
            for k in present:
                members = [a for a in range(A) if sel[a] and p.classes[a] == k]
                if selection == "all":
                    per = schema.CLASS_WEIGHTS[k] / tot / max(sum(1 for a in range(A) if elig[a] and p.classes[a] == k), 1)
                    for a in members:
                        w[a] = per
                elif members:
                    for a in members:
                        w[a] = schema.CLASS_WEIGHTS[k] / tot / len(members)
        elif cfg["sizing"] == "inv_vol":
            v = p.vol(cfg["vol_lookback"])[i]
            iv = np.where(sel & (v > 0), 1 / np.where(v > 0, v, 1), 0.0)
            if iv.sum() > 0:
                w = iv / iv.sum() * (sel.sum() / slots)
        else:
            w[sel] = 1.0 / slots
    if cfg["max_weight"] is not None:
        w = np.minimum(w, cfg["max_weight"])
    if cfg["max_equity"] is not None:
        eq = np.array([k == "equity" for k in p.classes])
        se = w[eq].sum()
        if se > cfg["max_equity"]:
            w[eq] *= cfg["max_equity"] / se
    cap = 1 - cfg["min_cash"]
    if w.sum() > cap:
        w *= cap / w.sum()
    rest = max(0.0, 1 - cfg["min_cash"] - w.sum())
    shy = rest if (cfg["defensive"] == "shy" and p.def_ok[i]) else 0.0
    return w, shy, raw_qual


@dataclass
class Result:
    returns: pd.Series          # daily (open t -> open t+1), labelled by day t
    exposure: pd.Series         # risky weight per day
    turnover: float             # one-way, annualised
    trades: int


def run(cfg: dict, p: Panel, cost_bps: float = 5.0, start: str | None = None) -> Result:
    """Simulate one config on one panel from `start` (signals may use earlier data)."""
    T, A = p.g.shape
    i0 = 0 if start is None else int(p.dates.searchsorted(pd.Timestamp(start)))
    reb = rebalance_mask(p.dates, cfg["rebalance"])
    lb = schema.lookbacks(cfg)
    fills = [i + 1 for i in range(i0, T - 1) if reb[i]]
    ret = np.zeros(T); expo = np.zeros(T)
    w, s, cash = np.zeros(A), 0.0, 1.0
    held = np.zeros(A, dtype=bool); prev_qual = np.zeros(A, dtype=bool)
    traded, n_trades = 0.0, 0
    bounds = fills + [T]
    for k, f in enumerate(fills):
        tw, ts, prev_qual = _targets(cfg, p, f - 1, held, prev_qual, lb)
        dw = np.abs(tw - w).sum() + abs(ts - s)
        n_trades += int((np.abs(tw - w) > 1e-3).sum() + (abs(ts - s) > 1e-3))
        traded += dw
        cost = dw * cost_bps / 1e4
        w, s = tw * (1 - cost), ts * (1 - cost)
        cash = (1 - cost) - w.sum() - s
        held = tw > 0
        e = bounds[k + 1]
        G = np.cumprod(1 + p.g[f:e], axis=0)                  # (L, A)
        Gd = np.cumprod(1 + p.g_def[f:e])
        H = w * G; S = s * Gd
        V = H.sum(axis=1) + S + cash
        prevV = np.concatenate([[1.0], V[:-1]])
        ret[f:e] = V / prevV - 1
        expo[f:e] = np.concatenate([[w.sum()], H[:-1].sum(axis=1) / V[:-1]]) if e - f > 1 else [w.sum()]
        w, s, cash = H[-1] / V[-1], S[-1] / V[-1], cash / V[-1]
    idx = p.dates
    first = fills[0] if fills else T
    r = pd.Series(ret, index=idx).iloc[i0:]
    yrs = max((idx[-1] - idx[min(i0, T - 1)]).days / 365.25, 1e-9)
    return Result(returns=r, exposure=pd.Series(expo, index=idx).iloc[i0:],
                  turnover=traded / 2 / yrs, trades=n_trades)


def benchmark_config(universe: str) -> dict:
    """Matched benchmark: hold every eligible ETF in the universe, equal weight, monthly rebalance."""
    return {"universe": universe, "family": "always", "signal": {"type": "always"}, "combo": "single",
            "second": None, "selection": "all", "sizing": "equal", "vol_lookback": None, "max_weight": None,
            "max_equity": None, "min_cash": 0.0, "rebalance": "monthly", "entry_exit": "scheduled",
            "defensive": "cash"}


def run_benchmark(p: Panel, cost_bps=5.0, start=None) -> Result:
    return run(benchmark_config(p.universe), p, cost_bps, start)
