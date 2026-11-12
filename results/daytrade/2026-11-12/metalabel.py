import sys; from datetime import datetime, timezone
import numpy as np, pandas as pd, warnings; warnings.filterwarnings("ignore")
sys.path.insert(0, "/home/claude/backtest-bot")
from data.cache import read_bars
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
df = read_bars("/home/claude/backtest-bot/data/cache", "histdata", "NAS100", "M15", datetime(2016,1,1,tzinfo=timezone.utc), datetime(2026,11,1,tzinfo=timezone.utc)).reset_index(drop=True)
O, H, L, C = (df[k].to_numpy() for k in ("open","high","low","close"))
ts = pd.to_datetime(df.timestamp_utc, utc=True); ny = ts.dt.tz_convert("America/New_York")
nymin = (ny.dt.hour * 60 + ny.dt.minute).to_numpy(); nyday = ny.dt.date.to_numpy()
d = pd.Series(C).diff(); up = d.clip(lower=0).ewm(alpha=1/14, adjust=False).mean(); dn = (-d.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
RSI = (100 - 100 / (1 + up / dn)).to_numpy()
tr = np.maximum(H - L, np.maximum(abs(H - np.r_[C[0], C[:-1]]), abs(L - np.r_[C[0], C[:-1]]))); ATR = pd.Series(tr).rolling(14).mean().to_numpy()
VOL20 = pd.Series(C).pct_change().rolling(20).std().to_numpy()
# day open (first bar at/after 09:30 NY)
open_px = {}
for i in range(len(C)):
    if nymin[i] >= 570 and nyday[i] not in open_px: open_px[nyday[i]] = O[i]
t = pd.read_csv("/tmp/nas_trades.csv"); rows = []
for r in t.itertuples():
    e = r.entry_price; R = e - r.initial_stop_price; cR = r.costs / (r.units * R); k = r.entry_idx
    for i in range(k, r.exit_idx + 1):
        if L[i] <= r.initial_stop_price: break
        if H[i] >= e + 0.8 * R:
            f = dict(bars=i - k, nymin=nymin[i], stop_pct=R / e * 100, rsi_entry=RSI[k - 1], day_ret=(e / open_px.get(nyday[k], e) - 1) * 100,
                     pre_ret=(C[k - 1] / C[k - 5] - 1) * 100, vol20=VOL20[k - 1] * 100, close_past=(C[i] - e) / R - 0.8, range_atr=(H[i] - L[i]) / ATR[i])
            f.update(ts=pd.Timestamp(r.entry_ts), hold=r.r_multiple, early=0.8 - cR, base=r.r_multiple)
            rows.append(f); break
D = pd.DataFrame(rows); D["y"] = (D.hold > D.early).astype(int); D["yr"] = D.ts.dt.year
X = ["bars","nymin","stop_pct","rsi_entry","day_ret","pre_ret","vol20","close_past","range_atr"]
tr_, va, te = D[D.yr <= 2020], D[(D.yr >= 2021) & (D.yr <= 2024)], D[D.yr >= 2025]
print(f"decision points: train {len(tr_)}, 2021-24 {len(va)}, 2025-26 {len(te)}; share where holding was better: {D.y.mean():.0%}")
for name, model in (("logistic", make_pipeline(StandardScaler(), LogisticRegression(C=0.5))),
                    ("boosted trees", GradientBoostingClassifier(max_depth=2, n_estimators=100, learning_rate=0.05, subsample=0.8, random_state=0))):
    model.fit(tr_[X], tr_.y)
    p_tr = model.predict_proba(tr_[X])[:, 1]
    # pick threshold on TRAIN: close early when P(hold better) < th
    best = max(np.arange(0.2, 0.71, 0.05), key=lambda th: np.where(p_tr < th, tr_.early, tr_.hold).sum())
    print(f"\n{name}: threshold chosen on 2016-20 = {best:.2f}")
    for lab, S in (("2016-20 (train)", tr_), ("2021-24", va), ("2025-26", te)):
        p = model.predict_proba(S[X])[:, 1]; pol = np.where(p < best, S.early, S.hold)
        print(f"  {lab}: always hold {S.hold.sum():+.1f}R | model {pol.sum():+.1f}R | closed early {np.mean(p < best):.0%} of {len(S)}")

# --- detail for the logistic model
m = make_pipeline(StandardScaler(), LogisticRegression(C=0.5)).fit(tr_[X], tr_.y)
print("\nlogistic coefficients (+ = more likely to be worth holding):")
for f, c in sorted(zip(X, m[-1].coef_[0]), key=lambda z: -abs(z[1])): print(f"  {f:11s} {c:+.2f}")
D["p"] = m.predict_proba(D[X])[:, 1]; D["gain"] = np.where(D.p < 0.5, D.early - D.hold, 0.0)
print("\nper-year gain vs always-hold (R):", D[D.yr >= 2021].groupby("yr").gain.sum().round(1).to_dict())
rng = np.random.default_rng(0); out = D[D.yr >= 2021].gain.to_numpy()
bs = [rng.choice(out, len(out)).sum() for _ in range(5000)]; print(f"2021-26 gain {out.sum():+.1f}R, bootstrap chance it's really <= 0: {np.mean(np.array(bs) <= 0):.0%}")
