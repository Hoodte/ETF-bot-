import io, contextlib, runpy, numpy as np, pandas as pd, sys
sys.argv=["x"]
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path("results/daytrade/2026-11-15/orderflow_exits.py")
J, X0, X1 = g["J"], g["X0"], g["X1"]
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
tr = (J.yr <= 2020).values; te = ~tr
mo = pd.to_datetime(J.entry_ts).dt.strftime("%Y-%m").values
def gains(X, C=0.5, thr=0.5):
    m = make_pipeline(StandardScaler(), LogisticRegression(C=C)).fit(J.loc[tr, X], J.loc[tr, "y"])
    p = m.predict_proba(J[X])[:, 1]
    return np.where(p < thr, J.early - J.hold, 0.0), m
print("Robustness (test 2021-26 gain, R):  C x threshold")
for C in (0.1, 0.5, 2.0):
    row=[]
    for thr in (0.45, 0.5, 0.55):
        g0,_=gains(X0,C,thr); g1,_=gains(X1,C,thr)
        row.append(f"thr{thr}: price {g0[te].sum():+.1f} / +OF {g1[te].sum():+.1f}")
    print(f" C={C}: " + " | ".join(row))
g0,_ = gains(X0); g1,m1 = gains(X1)
print("\nPer year (test): price-only vs +orderflow")
for y in range(2021,2027):
    k=(J.yr==y).values
    print(f" {y}: {g0[k].sum():+.1f} vs {g1[k].sum():+.1f}  (n={k.sum()})")
rng=np.random.default_rng(1)
def boot(v):
    d=pd.Series(v[te]).groupby(mo[te]).sum().values
    return np.mean([rng.choice(d,len(d)).sum()<=0 for _ in range(5000)])
print(f"\np(model+OF test gain <= 0) = {boot(g1):.3f}")
print(f"p(+OF no better than price-only) = {boot(g1-g0):.3f}")
lr=m1[-1]; print("\nstandardised coefs:", dict(zip(X1, np.round(lr.coef_[0],2))))
# who gets closed
k=te & (g1!=0)
print(f"test trades closed early: {k.sum()} of {te.sum()}; their original outcomes: mean hold {J.hold[k].mean():+.2f}R, share losers {np.mean(J.hold[k]<0):.0%}")
