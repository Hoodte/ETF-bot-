"""Intraday engine.

No look-ahead, by construction:
  * a signal uses bars up to and including the close of bar t;
  * entry fills at the OPEN of bar t+1;
  * stop/target levels come from bar t's close and ATR (never from the fill bar), and a trade is
    skipped if the open of t+1 has already gapped through the stop;
  * from bar t+1 on, stop and target are checked against each bar's high/low. If both are touched in
    the same bar the STOP is assumed first. A gap through a level fills at that bar's open;
  * time exits fill at the close of the last allowed bar; end-of-day exits at the close of the last
    bar before the session end;
  * costs: cost_bps per side on entry and exit.
Each trade is volatility-normalised: P&L is measured in ATR(14) units of the signal bar, so trades on
quiet and wild days count equally. Daily P&L = sum of trades closed that day.
"""
from __future__ import annotations

import numba as nb
import numpy as np
import pandas as pd

from . import schema as S


class Data:
    def __init__(self, path: str, tf: int, session_end: int, end: str | None = None):
        if path.endswith(".pkl"):
            df = pd.read_pickle(path)
        else:
            df = pd.read_csv(path)
            if "ts" in df.columns:
                df.index = pd.to_datetime(df["ts"], unit="s", utc=True)
                df = df.rename(columns=str.capitalize)[["Open", "High", "Low", "Close"]]
            else:
                df = df.set_index(df.columns[0]); df.index = pd.to_datetime(df.index, utc=True, format="ISO8601")
        df = df[["Open", "High", "Low", "Close"]].astype(float).dropna()
        aligned = (df.index.second == 0) & (df.index.microsecond == 0) & ((df.index.hour * 60 + df.index.minute) % tf == 0)
        df = df[aligned & ~df.index.duplicated()].sort_index()      # drop stray mis-stamped exchange records
        df = df[(df.High >= df.Low) & (df.Close > 0)]
        if end is not None:
            df = df.loc[: pd.Timestamp(end, tz="UTC") + pd.Timedelta(hours=23, minutes=59)]
        self.df, self.tf, self.session_end = df, tf, session_end
        self.o, self.h, self.l, self.c = (df[k].to_numpy() for k in ("Open", "High", "Low", "Close"))
        self.idx = df.index
        self.hour = df.index.hour.to_numpy()
        self.minute_of_day = (df.index.hour * 60 + df.index.minute).to_numpy()
        day = df.index.floor("D")
        self.days = pd.DatetimeIndex(day.unique())
        self.day = pd.factorize(day)[0]
        nxt = np.append(self.day[1:], -1)
        if session_end >= 24:
            self.last_bar = nxt != self.day
        else:   # last bar that STARTS before the session end hour, or the day's last bar
            in_sess = self.minute_of_day < session_end * 60
            nxt_in = np.append(in_sess[1:], False)
            self.last_bar = (in_sess & ~(nxt_in & (nxt == self.day))) | (nxt != self.day)
        self.in_session = self.minute_of_day < min(session_end, 24) * 60
        self._cache = {}
        tr = np.maximum(self.h - self.l, np.maximum(abs(self.h - np.roll(self.c, 1)), abs(self.l - np.roll(self.c, 1))))
        tr[0] = self.h[0] - self.l[0]
        self.atr = pd.Series(tr).rolling(14, min_periods=14).mean().to_numpy()
        self.atr_pct = pd.Series(self.atr).rolling(500, min_periods=200).rank(pct=True).to_numpy()
        self.ema200 = pd.Series(self.c).ewm(span=200, adjust=False, min_periods=200).mean().to_numpy()

    # ---------------- raw entry signals (+1 long, -1 short, 0) at bar close
    def raw_signal(self, s: dict) -> np.ndarray:
        key = tuple(sorted(s.items()))
        if key in self._cache:
            return self._cache[key]
        c = pd.Series(self.c)
        f = s["family"]
        if f == "breakout":
            hi = pd.Series(self.h).rolling(s["n"]).max().shift(1); lo = pd.Series(self.l).rolling(s["n"]).min().shift(1)
            sig = np.where(c > hi, 1, np.where(c < lo, -1, 0))
        elif f == "momentum":
            r = np.log(c).diff(s["n"])
            sd = np.log(c).diff().rolling(500, min_periods=200).std() * np.sqrt(s["n"])
            sig = np.where(r > s["z"] * sd, 1, np.where(r < -s["z"] * sd, -1, 0))
        elif f == "rsi_revert":
            d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / s["p"], adjust=False).mean()
            dn = (-d.clip(upper=0)).ewm(alpha=1 / s["p"], adjust=False).mean()
            rsi = 100 - 100 / (1 + up / dn.replace(0, np.nan))
            sig = np.where(rsi < s["th"], 1, np.where(rsi > 100 - s["th"], -1, 0))
        elif f == "band_fade":
            m = c.rolling(s["n"]).mean(); sd = c.rolling(s["n"]).std()
            sig = np.where(c < m - s["k"] * sd, 1, np.where(c > m + s["k"] * sd, -1, 0))
        elif f == "orb":
            tz, open_min = S.SESSION_OPEN[s["session"]]
            mod, lday = self._local(tz)
            sig = _orb(self.h, self.l, self.c, mod, lday, open_min, s["minutes"], self.tf)
        elif f == "pdhl":
            sig = _pdhl(self.h, self.l, self.c, self.day)
            if s["mode"] == "fade":
                sig = -sig
        else:
            raise ValueError(f)
        sig = np.asarray(sig, dtype=np.int8)
        self._cache[key] = sig
        return sig

    def _local(self, tz):
        k = ("local", tz)
        if k not in self._cache:
            loc = self.idx.tz_convert(tz)
            self._cache[k] = ((loc.hour * 60 + loc.minute).to_numpy(), pd.factorize(loc.floor("D") if tz == "UTC" else loc.normalize())[0])
        return self._cache[k]

    def entries(self, cfg: dict) -> np.ndarray:
        sig = self.raw_signal(cfg["signal"]).copy()
        with np.errstate(invalid="ignore"):
            if cfg["trend"] != "none":
                up = self.c > self.ema200
                ok = np.where(sig > 0, up, ~up) if cfg["trend"] == "with" else np.where(sig > 0, ~up, up)
                sig = np.where(ok & ~np.isnan(self.ema200), sig, 0)
            if cfg["vol"] == "high":
                sig = np.where(self.atr_pct > 0.5, sig, 0)
            elif cfg["vol"] == "low":
                sig = np.where(self.atr_pct <= 0.5, sig, 0)
        if cfg["session"] != "all":
            a, b = S.SESSION_HOURS[cfg["session"]]
            sig = np.where((self.hour >= a) & (self.hour < b), sig, 0)
        if cfg["direction"] == "long":
            sig = np.where(sig > 0, sig, 0)
        elif cfg["direction"] == "short":
            sig = np.where(sig < 0, sig, 0)
        if cfg["eod"]:
            sig = np.where(self.in_session, sig, 0)          # no new trades after the session end
        sig = np.where(np.isnan(self.atr) | (self.atr <= 0), 0, sig)
        return sig.astype(np.int8)


@nb.njit(cache=True)
def _orb(h, l, c, mod, day, open_min, minutes, tf):
    n = len(c); out = np.zeros(n, np.int8)
    cur_day = -1; hi = -1e18; lo = 1e18; done = False; ready = False
    for t in range(n):
        if day[t] != cur_day:
            cur_day = day[t]; hi = -1e18; lo = 1e18; done = False; ready = False
        m = mod[t]
        if open_min <= m < open_min + minutes:
            hi = max(hi, h[t]); lo = min(lo, l[t])
            if m + tf >= open_min + minutes:
                ready = True
            continue
        if ready and not done and open_min + minutes <= m < open_min + minutes + 240:
            if c[t] > hi:
                out[t] = 1; done = True
            elif c[t] < lo:
                out[t] = -1; done = True
    return out


@nb.njit(cache=True)
def _pdhl(h, l, c, day):
    n = len(c); out = np.zeros(n, np.int8)
    cur = -1; ph = np.nan; pl = np.nan; th = -1e18; tl = 1e18; done = False
    for t in range(n):
        if day[t] != cur:
            if cur != -1:
                ph = th; pl = tl
            cur = day[t]; th = -1e18; tl = 1e18; done = False
        if not done and not np.isnan(ph):
            if c[t] > ph:
                out[t] = 1; done = True
            elif c[t] < pl:
                out[t] = -1; done = True
        th = max(th, h[t]); tl = min(tl, l[t])
    return out


@nb.njit(cache=True)
def simulate(o, h, l, c, atr, sig, last_bar, use_bracket, k_stop, k_tgt, hold, eod, cost):
    """Returns arrays per trade: entry bar, exit bar, direction, pnl in ATR units (net of costs)."""
    n = len(c)
    ent = np.empty(n, np.int64); ext = np.empty(n, np.int64); dirs = np.empty(n, np.int8); pnl = np.empty(n)
    k = 0; t = 0
    while t < n - 1:
        d = sig[t]
        if d == 0 or (eod and last_bar[t]):
            t += 1; continue
        a = atr[t]; e = o[t + 1]
        stop = c[t] - d * k_stop * a; tgt = c[t] + d * k_tgt * a
        if use_bracket and ((d == 1 and e <= stop) or (d == -1 and e >= stop)):
            t += 1; continue          # gapped through the stop before we could enter
        x = -1.0; j = t + 1
        while True:
            if use_bracket:
                if d == 1:
                    if l[j] <= stop:
                        x = min(o[j], stop) if j > t + 1 else stop; break
                    if h[j] >= tgt:
                        x = max(o[j], tgt) if j > t + 1 else max(e, tgt); break
                else:
                    if h[j] >= stop:
                        x = max(o[j], stop) if j > t + 1 else stop; break
                    if l[j] <= tgt:
                        x = min(o[j], tgt) if j > t + 1 else min(e, tgt); break
            if j - t >= hold or (eod and last_bar[j]) or j == n - 1:
                x = c[j]; break
            j += 1
        ent[k] = t + 1; ext[k] = j; dirs[k] = d
        pnl[k] = (d * (x - e) - cost * (e + x)) / a
        k += 1
        t = j          # next signal can be the exit bar's close; entry then at the following open
    return ent[:k], ext[:k], dirs[:k], pnl[:k]


def run(cfg: dict, data: Data, cost_bps: float) -> pd.DataFrame:
    sig = data.entries(cfg)
    br = cfg["bracket"] or [0.0, 0.0]
    e, x, d, p = simulate(data.o, data.h, data.l, data.c, data.atr, sig, data.last_bar, cfg["exit"] == "bracket",
                          float(br[0]), float(br[1]), int(cfg["hold"]), bool(cfg["eod"]), cost_bps / 1e4)
    return pd.DataFrame({"entry_time": data.idx[e], "exit_time": data.idx[x], "dir": d, "pnl_atr": p,
                         "bars": x - e + 1})
