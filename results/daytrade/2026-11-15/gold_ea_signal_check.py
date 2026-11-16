import json, urllib.request, pandas as pd, numpy as np
def yahoo(s):
    u=f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?range=10y&interval=1d"
    j=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=30))["chart"]["result"][0]
    off=j["meta"]["gmtoffset"]
    d=pd.to_datetime(np.array(j["timestamp"])+off,unit="s").normalize()
    v=j["indicators"]["adjclose"][0]["adjclose"]
    return pd.Series(v,index=d).dropna()
dxy=yahoo("DX-Y.NYB"); tip=yahoo("TIP")
print("dxy", dxy.index[:2], len(dxy), "tip", len(tip))
u="https://publicreporting.cftc.gov/resource/72hh-3qpy.json?$select=report_date_as_yyyy_mm_dd,m_money_positions_long_all,m_money_positions_short_all,open_interest_all&cftc_contract_market_code=088691&$order=report_date_as_yyyy_mm_dd%20DESC&$limit=2000"
c=pd.DataFrame(json.load(urllib.request.urlopen(u,timeout=60)))
for k in ("m_money_positions_long_all","m_money_positions_short_all","open_interest_all"): c[k]=pd.to_numeric(c[k])
c["d"]=pd.to_datetime(c.report_date_as_yyyy_mm_dd); c=c.sort_values("d").drop_duplicates("d")
print("cot", c.d.min(), c.d.max(), len(c))
cot=pd.Series(((c.m_money_positions_long_all-c.m_money_positions_short_all)/c.open_interest_all).values,index=pd.DatetimeIndex(c.d.values))
pct=cot.rolling(156,min_periods=52).apply(lambda a:(a[:-1]<a[-1]).mean(),raw=True)
def act(sig,lag):
    s=sig.dropna().astype(float); s.index=s.index+pd.Timedelta(days=lag); return s[~s.index.duplicated(keep="last")]
A=act((dxy<dxy.rolling(50).mean()).astype(float),1)
B=act((tip.pct_change(20)>0).astype(float),1)
C=act((pct<0.70).astype(float).where(pct.notna(),0.0),6)
days=pd.date_range("2018-01-01","2026-11-13",freq="B")
def asof(s,dts): return s.reindex(s.index.union(dts)).ffill().reindex(dts).fillna(0)
ra,rb,rc=asof(A,days),asof(B,days),asof(C,days)
ea_a,ea_b,ea_c=[],[],[]
for sig in days:
    cut=sig-pd.Timedelta(days=1)
    x=dxy[dxy.index<=cut]; t=tip[tip.index<=cut]
    ea_a.append(float(x.iloc[-1]<x.iloc[-50:].mean())); ea_b.append(float(t.iloc[-1]/t.iloc[-21]-1>0))
    cc=cot[cot.index+pd.Timedelta(days=6)<=sig]; w=cc.iloc[-156:]
    ea_c.append(float((len(w)>=52) and ((w.iloc[:-1]<w.iloc[-1]).mean()<0.70)))
for n,r,e in (("dollar",ra,ea_a),("tip",rb,ea_b),("cot",rc,ea_c)):
    e=np.array(e); print(n, "agree", round((r.values==e).mean(),4), "ref mean", round(r.mean(),3), "ea mean", round(e.mean(),3))
ref=((ra+rb+rc)>=2).astype(int); ea=((np.array(ea_a)+np.array(ea_b)+np.array(ea_c))>=2).astype(int)
print("composite agree", round((ref.values==ea).mean(),4))
d=days[ref.values!=ea]; print(len(d), list(d[:8].date))
