import numpy as np, pandas as pd
MK = {"SPXUSD": ("America/New_York", "16:00", "10:00", "15:00", "15:30", 1.0), "NSXUSD": ("America/New_York", "16:00", "10:00", "15:00", "15:30", 1.0),
      "GRXEUR": ("Europe/Berlin", "17:30", "09:30", "16:30", "17:00", 1.2)}
def daily(sym):
    tz, close_t, first_end, mid_t, last_start, cost = MK[sym]
    b = pd.read_pickle(f"data/histdata/{sym}_5m.pkl"); b.index = b.index.tz_convert(tz)
    t = b.index.strftime("%H:%M"); day = b.index.normalize()
    def px_at(hhmm, field="Open"):      # price at a clock time = open of the bar starting then
        s = b[field][t == hhmm]; s.index = s.index.normalize(); return s[~s.index.duplicated()]
    def last_close_before(hhmm):        # close of the bar ending at hhmm (bar starting 5 min earlier)
        hh, mm = map(int, hhmm.split(":")); prev = (pd.Timestamp(2000, 1, 1, hh, mm) - pd.Timedelta(minutes=5)).strftime("%H:%M")
        s = b["Close"][t == prev]; s.index = s.index.normalize(); return s[~s.index.duplicated()]
    c_close = last_close_before(close_t)       # session close each day
    p_first = px_at(first_end); p_mid = px_at(mid_t); p_last = px_at(last_start)
    df = pd.concat({"prev_close": c_close.shift(1), "first": p_first, "mid": p_mid, "last_open": p_last, "close": c_close}, axis=1).dropna()
    df["r1"] = df["first"] / df["prev_close"] - 1; df["r12"] = df["last_open"] / df["mid"] - 1
    df["r_last"] = df["close"] / df["last_open"] - 1
    df["cost"] = cost / 1e4
    df.index = df.index.tz_localize(None)
    return df
def strat(df, v, mult=1.0):
    if v == "V1": s = np.sign(df.r1)
    elif v == "V2": s = np.sign(df.r1).where(df.r1.abs() > df.r1.abs().rolling(60).median().shift(1), 0)
    else: s = np.sign(df.r1 + df.r12)
    return s * df.r_last - s.abs() * 2 * df.cost * mult
def sh(x):
    x = x.dropna(); return x.mean() / x.std() * np.sqrt(252) if x.std() > 0 else 0
D = {s: daily(s) for s in MK}
for v in ("V1", "V2", "V3"):
    P = {s: strat(D[s], v) for s in MK}; P2 = {s: strat(D[s], v, 2) for s in MK}
    port = pd.DataFrame({s: p / p.std() for s, p in P.items()}).fillna(0).mean(axis=1)
    port2 = pd.DataFrame({s: p / P[s].std() for s, p in P2.items()}).fillna(0).mean(axis=1)
    row = [f"{v}:"]
    for a, b_ in (("2016", "2020"), ("2021", "2024"), ("2025", "2026")):
        row.append(f"{a}-{b_} port {sh(port[a:b_]):.2f} (2x {sh(port2[a:b_]):.2f}) [" + ", ".join(f"{s[:3]} {sh(P[s][a:b_]):.2f}" for s in MK) + "]")
    print("  ".join(row))
