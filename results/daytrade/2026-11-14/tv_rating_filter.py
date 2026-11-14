"""TradingView-style Technical Rating as a filter for Nasdaq lunch-RSI (pre-registered 14 Nov 2026).

Approximation of TradingView's built-in 'Technical Ratings' (no volume -> no VWMA; Ichimoku, Stoch RSI and
Bull/Bear Power left out). Votes +1 buy / -1 sell / 0 neutral:
  MAs: price vs SMA & EMA 10/20/30/50/100/200 and HMA 9
  Oscillators: RSI14, Stoch 14/3/3, CCI20, ADX14 DI-cross, Awesome Osc, Momentum10, MACD 12/26/9, Williams %R 14, Ultimate Osc
  Rating = mean(mean(MA votes), mean(osc votes)); Strong Buy > 0.5, Buy > 0.1, Neutral, Sell < -0.1, Strong Sell < -0.5
Daily rating at entry = daily bars by NY date with TODAY's partial bar up to the signal-bar close (what you'd see live).
PRIMARY rule: skip trades when the daily rating is Sell/Strong Sell. Others reported for completeness.
"""
import sys, io, contextlib
import numpy as np, pandas as pd
sys.path.insert(0, ".")
sys.path.insert(0, "results/daytrade/2026-11-14")
with contextlib.redirect_stdout(io.StringIO()):
    import exit_candidates as ec
df, t = ec.df, ec.t
NY = ec.NY
yr = t.year.values
r = t.r_multiple.values


def wma(s, n):
    w = np.arange(1, n + 1)
    return s.rolling(n).apply(lambda x: (x * w).sum() / w.sum(), raw=True)


def rating(b):
    """b: DataFrame open/high/low/close. Returns Series of rating for each row."""
    c, h, l = b.close, b.high, b.low
    ma = []
    for n in (10, 20, 30, 50, 100, 200):
        for m in (c.rolling(n).mean(), c.ewm(span=n, adjust=False).mean()):
            ma.append(np.sign(c - m).where(m.notna()))
    hma = wma(2 * wma(c, 4) - wma(c, 9), 3)
    ma.append(np.sign(c - hma).where(hma.notna()))
    MA = pd.concat(ma, axis=1).mean(axis=1)
    osc = []
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + up / dn)
    osc.append(np.where((rsi < 30) & (rsi > rsi.shift()), 1, np.where((rsi > 70) & (rsi < rsi.shift()), -1, 0)))
    st = 100 * (c - l.rolling(14).min()) / (h.rolling(14).max() - l.rolling(14).min())
    k = st.rolling(3).mean(); dd = k.rolling(3).mean()
    osc.append(np.where((k < 20) & (dd < 20) & (k > dd), 1, np.where((k > 80) & (dd > 80) & (k < dd), -1, 0)))
    tp = (h + l + c) / 3
    cci = (tp - tp.rolling(20).mean()) / (0.015 * tp.rolling(20).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True))
    osc.append(np.where((cci < -100) & (cci > cci.shift()), 1, np.where((cci > 100) & (cci < cci.shift()), -1, 0)))
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    pdm = (h.diff()).where((h.diff() > -l.diff()) & (h.diff() > 0), 0.0)
    mdm = (-l.diff()).where((-l.diff() > h.diff()) & (-l.diff() > 0), 0.0)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    pdi = 100 * pdm.ewm(alpha=1 / 14, adjust=False).mean() / atr; mdi = 100 * mdm.ewm(alpha=1 / 14, adjust=False).mean() / atr
    adx = (100 * (pdi - mdi).abs() / (pdi + mdi)).ewm(alpha=1 / 14, adjust=False).mean()
    osc.append(np.where((adx > 20) & (pdi.shift() < mdi.shift()) & (pdi > mdi), 1, np.where((adx > 20) & (pdi.shift() > mdi.shift()) & (pdi < mdi), -1, 0)))
    hl2 = (h + l) / 2
    ao = hl2.rolling(5).mean() - hl2.rolling(34).mean()
    saucer_b = (ao > 0) & (ao > ao.shift()) & (ao.shift() < ao.shift(2))
    saucer_s = (ao < 0) & (ao < ao.shift()) & (ao.shift() > ao.shift(2))
    osc.append(np.where(saucer_b | ((ao > 0) & (ao.shift() <= 0)), 1, np.where(saucer_s | ((ao < 0) & (ao.shift() >= 0)), -1, 0)))
    mom = c - c.shift(10)
    osc.append(np.sign(mom - mom.shift()).fillna(0).values)
    macd = c.ewm(span=12, adjust=False).mean() - c.ewm(span=26, adjust=False).mean()
    osc.append(np.sign(macd - macd.ewm(span=9, adjust=False).mean()).values)
    wr = -100 * (h.rolling(14).max() - c) / (h.rolling(14).max() - l.rolling(14).min())
    osc.append(np.where((wr < -80) & (wr > wr.shift()), 1, np.where((wr > -20) & (wr < wr.shift()), -1, 0)))
    bp = c - pd.concat([l, c.shift()], axis=1).min(axis=1)
    trr = pd.concat([h, c.shift()], axis=1).max(axis=1) - pd.concat([l, c.shift()], axis=1).min(axis=1)
    avg = lambda n: bp.rolling(n).sum() / trr.rolling(n).sum()  # noqa: E731
    uo = 100 * (4 * avg(7) + 2 * avg(14) + avg(28)) / 7
    osc.append(np.where(uo > 70, 1, np.where(uo < 30, -1, 0)))
    OSC = pd.DataFrame(np.column_stack(osc), index=b.index).mean(axis=1)
    return (MA + OSC) / 2


def label(x):
    return np.where(x > .5, "Strong Buy", np.where(x > .1, "Buy", np.where(x >= -.1, "Neutral", np.where(x >= -.5, "Sell", "Strong Sell"))))


# --- daily bars by NY date (full 24h NY day)
b = pd.DataFrame({"open": df.open.values, "high": df.high.values, "low": df.low.values, "close": df.close.values, "d": NY.dt.date.values})
daily = b.groupby("d").agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
dates = list(daily.index)
dpos = {d: i for i, d in enumerate(dates)}
drat = []
for tr_ in t.itertuples():
    k = tr_.entry_idx
    d = NY.dt.date.values[k]
    i = dpos[d]
    hist = daily.iloc[max(0, i - 400):i].copy()
    today = b.iloc[:k][b.d.values[:k] == d] if False else b.iloc[k - 200:k]
    today = today[today.d == d]
    part = pd.DataFrame({"open": [today.open.iloc[0]], "high": [today.high.max()], "low": [today.low.min()], "close": [today.close.iloc[-1]]}, index=[d])
    drat.append(rating(pd.concat([hist, part])).iloc[-1])
drat = np.array(drat)
# --- 15-minute rating at the signal bar (bar before entry)
m15 = rating(b[["open", "high", "low", "close"]])
mrat = m15.values[t.entry_idx.values - 1]

PER = [("2016-20", (2016, 2020)), ("2021-24", (2021, 2024)), ("2025-26", (2025, 2026)), ("Full", (2016, 2026))]
for name, x in (("DAILY rating", drat), ("15-MIN rating", mrat)):
    lab = label(x)
    print(f"\n## {name} at entry: average result per trade by rating\n")
    print("| Rating | " + " | ".join(p for p, _ in PER) + " |\n|---|---|---|---|---|")
    for L in ("Strong Buy", "Buy", "Neutral", "Sell", "Strong Sell"):
        cells = []
        for _, (a, bb) in PER:
            msk = (lab == L) & (yr >= a) & (yr <= bb)
            cells.append(f"{r[msk].mean():+.2f}R (n={msk.sum()})" if msk.sum() else "-")
        print(f"| {L} | " + " | ".join(cells) + " |")
    print(f"\n### {name} as a filter: total R kept (vs all trades)\n")
    print("| Rule | Trades kept | " + " | ".join(p for p, _ in PER) + " |\n|---|---|---|---|---|---|")
    for rule, keep in (("All trades (now)", np.ones(len(x), bool)),
                       ("Skip Sell/Strong Sell" + (" **PRIMARY**" if name.startswith("DAILY") else ""), x >= -.1),
                       ("Only Buy/Strong Buy", x > .1),
                       ("Only Strong Buy", x > .5)):
        cells = []
        for _, (a, bb) in PER:
            msk = (yr >= a) & (yr <= bb)
            cells.append(f"{r[msk & keep].sum():+.1f} ({r[msk & keep].sum() - r[msk].sum():+.1f})")
        print(f"| {rule} | {keep.sum()} | " + " | ".join(cells) + " |")
    print(f"\nCorrelation of {name} with trade result: {np.corrcoef(x[~np.isnan(x)], r[~np.isnan(x)])[0,1]:+.3f}")
