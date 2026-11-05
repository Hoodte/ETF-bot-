"""Round 8: combined-analysis LightGBM, yearly walk-forward. See round8_preregistration.md."""
import json, sys, warnings
import numpy as np, pandas as pd, lightgbm as lgb
from etfbot.config import load_config
from etfbot.daytrade import engine as E, evaluate as V
from etfbot import goldquant as gq
warnings.filterwarnings("ignore")
DS = load_config("config.yaml")["daytrade_fx"]["datasets"]
MK = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "XAUUSD", "NSXUSD", "SPXUSD", "GRXEUR"]
CROSS = ["EURUSD", "NSXUSD", "XAUUSD", "USDJPY"]
PARAMS = dict(n_estimators=400, learning_rate=0.03, num_leaves=31, min_child_samples=500, subsample=0.7, subsample_freq=1,
              colsample_bytree=0.7, reg_lambda=5.0, verbose=-1, n_jobs=2)

data = {m: E.Data(DS[f"{m}_1h"][0], 60, DS[f"{m}_1h"][3]) for m in MK}
grid = pd.DatetimeIndex(sorted(set().union(*[set(d.idx) for d in data.values()])))
cross = {}
for m in CROSS:
    c = pd.Series(data[m].c, index=data[m].idx).reindex(grid).ffill()
    lr = np.log(c).diff(); sd = lr.rolling(240, min_periods=100).std()
    cross[m] = pd.DataFrame({f"x_{m}_4": np.log(c).diff(4) / (sd * 2), f"x_{m}_24": np.log(c).diff(24) / (sd * np.sqrt(24))})
daily = gq.load_daily()
mac = pd.DataFrame({"dxy_sma": daily["DXY"] / daily["DXY"].rolling(50).mean() - 1, "tip20": daily["TIPS"].pct_change(20),
                    "vix": daily["VIX"], "vix5": daily["VIX"].diff(5)})


def rsi(c, p):
    d = c.diff(); up = d.clip(lower=0).ewm(alpha=1 / p, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1 / p, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def features(m, H):
    d = data[m]; idx = d.idx
    c = pd.Series(d.c, index=idx); o = pd.Series(d.o, index=idx); h = pd.Series(d.h, index=idx); l = pd.Series(d.l, index=idx)
    atr = pd.Series(d.atr, index=idx)
    f = pd.DataFrame(index=idx)
    for k in (1, 4, 12, 24, 72, 120):
        f[f"r{k}"] = (c - c.shift(k)) / atr
    for n in (20, 50, 200):
        f[f"sma{n}"] = (c - c.rolling(n).mean()) / atr
    f["rsi2"] = rsi(c, 2); f["rsi14"] = rsi(c, 14)
    f["bz20"] = (c - c.rolling(20).mean()) / c.rolling(20).std()
    f["atrpct"] = d.atr_pct
    lr = np.log(c).diff(); f["volratio"] = lr.rolling(24).std() / lr.rolling(240).std()
    f["hs"] = np.sin(2 * np.pi * idx.hour / 24); f["hc"] = np.cos(2 * np.pi * idx.hour / 24); f["dow"] = idx.dayofweek
    day = idx.floor("D")
    dh = h.groupby(day).max(); dl = l.groupby(day).min()
    pdh = pd.Series(dh.shift(1).reindex(day).to_numpy(), index=idx); pdl = pd.Series(dl.shift(1).reindex(day).to_numpy(), index=idx)
    f["d_pdh"] = (c - pdh) / atr; f["d_pdl"] = (c - pdl) / atr
    th = h.groupby(day).cummax(); tl = l.groupby(day).cummin()
    f["day_pos"] = (c - tl) / (th - tl).replace(0, np.nan)
    for m2 in CROSS:
        f = f.join(cross[m2].reindex(idx))
    mh = pd.DataFrame({k: gq.to_hourly(mac[k].rename(k), idx, 1) for k in mac})
    f = f.join(mh.replace(0.0, np.nan).ffill())
    f["mkt"] = MK.index(m)
    fwd = (c.shift(-H) - o.shift(-1)) / atr          # next open -> close H bars later
    f["y"] = (fwd > 0).astype(float).where(fwd.notna())
    f["m"] = m
    return f


def walk(H):
    F = pd.concat([features(m, H) for m in MK]).sort_index()
    F = F[F.index >= "2016-07-01"]
    X = [c for c in F.columns if c not in ("y", "m")]
    def fit(end):
        tr = F[(F.index < pd.Timestamp(end, tz="UTC") - pd.Timedelta(days=7)) & F.y.notna()]
        mdl = lgb.LGBMClassifier(**PARAMS); mdl.fit(tr[X], tr.y, categorical_feature=["mkt"]); return mdl
    preds = {}
    years = [(str(y), f"{y}-01-01", f"{y}-12-31") for y in range(2019, 2025)] + [("holdout", "2025-01-01", "2026-10-31")]
    for name, a, b in years:
        y0 = int(a[:4])
        cal_mdl = fit(f"{y0 - 1}-01-01")
        cal = F[(F.index >= pd.Timestamp(f"{y0 - 1}-01-01", tz="UTC")) & (F.index < pd.Timestamp(a, tz="UTC"))]
        pc = cal_mdl.predict_proba(cal[X])[:, 1]
        lo, hi = np.quantile(pc, 0.05), np.quantile(pc, 0.95)
        mdl = fit(a)
        te = F[(F.index >= pd.Timestamp(a, tz="UTC")) & (F.index <= pd.Timestamp(b, tz="UTC") + pd.Timedelta(hours=23))]
        p = mdl.predict_proba(te[X])[:, 1]
        preds[name] = pd.DataFrame({"m": te.m.values, "p": p, "lo": lo, "hi": hi}, index=te.index)
        print(f"  H={H} {name}: thresholds {lo:.3f}/{hi:.3f}, test rows {len(te)}", flush=True)
        if name == "holdout":
            imp = pd.Series(mdl.feature_importances_, index=X).sort_values(ascending=False)
    return preds, imp


def trade(preds, H, mult=1.0):
    out = {}
    for name, P in preds.items():
        dps, n = [], 0
        for m in MK:
            d = data[m]; q = P[P.m == m]
            sig = pd.Series(0, index=d.idx, dtype=np.int8)
            s = np.where(q.p > q.hi, 1, np.where(q.p < q.lo, -1, 0)).astype(np.int8)
            sig.loc[q.index] = s
            e, x, dr, pnl = E.simulate(d.o, d.h, d.l, d.c, d.atr, sig.to_numpy().astype(np.int8), d.last_bar, False, 0.0, 0.0, H, False,
                                       DS[f"{m}_1h"][2] * mult / 1e4)
            tr = pd.DataFrame({"exit_time": d.idx[x], "pnl_atr": pnl})
            days = d.days[(d.days >= q.index.min().floor("D")) & (d.days <= q.index.max().floor("D"))]
            tr = tr[(tr.exit_time >= days[0]) & (tr.exit_time < days[-1] + pd.Timedelta(days=1))]
            dps.append(V.daily_pnl(tr, days).rename(m)); n += len(tr)
        D = pd.concat(dps, axis=1).fillna(0).sum(axis=1)
        out[name] = (D, n)
    return out


def sharpe(D):
    yrs = (D.index[-1] - D.index[0]).days / 365.25
    return D.mean() / D.std() * np.sqrt(len(D) / yrs) if D.std() > 0 else 0


res = {}
for H in (4, 12):
    preds, imp = walk(H)
    t1, t2 = trade(preds, H), trade(preds, H, 2.0)
    wf = pd.concat([t1[str(y)][0] for y in range(2019, 2025)]); wf2 = pd.concat([t2[str(y)][0] for y in range(2019, 2025)])
    yearly = {str(y): round(sharpe(t1[str(y)][0]), 2) for y in range(2019, 2025)}
    ntr = sum(t1[str(y)][1] for y in range(2019, 2025)); tpd = ntr / (len(wf) * 5 / 7)
    hold = t1["holdout"][0]; hold2 = t2["holdout"][0]
    pre = sharpe(wf) >= 1.0 and sharpe(wf2) > 0 and sum(v > 0 for v in yearly.values()) >= 4 and tpd >= 1
    print(f"\n== H={H}: walk-forward 2019-24 Sharpe {sharpe(wf):.2f} (2x cost {sharpe(wf2):.2f}), yearly {yearly}, {tpd:.1f} trades/trading day -> pre-holdout {pre}")
    print(f"   HOLDOUT 2025-26 Sharpe {sharpe(hold):.2f} (2x cost {sharpe(hold2):.2f}), trades {t1['holdout'][1]}")
    print("   top features:", ", ".join(f"{k} {v}" for k, v in imp.head(12).items()))
    dp = pd.concat([wf, hold])
    for risk in (0.001, 0.002, 0.003, 0.004):
        k, med, avg = V.funded(dp, risk)
        print(f"   FTMO $100k risk {risk:.2%}/ATR: keep {k:.0%}, typical month ${med:,.0f}, avg ${avg:,.0f} (~${avg*12/52:,.0f}/wk)")
    res[H] = {"wf": sharpe(wf), "wf2x": sharpe(wf2), "yearly": yearly, "tpd": tpd, "holdout": sharpe(hold), "holdout2x": sharpe(hold2),
              "passed": bool(pre and sharpe(hold) > 0.5)}
    dp.to_frame("pnl_atr").to_csv(f"results/daytrade/2026-11-05/round8_H{H}_daily.csv")
json.dump(res, open("results/daytrade/2026-11-05/round8_results.json", "w"), indent=1, default=str)
