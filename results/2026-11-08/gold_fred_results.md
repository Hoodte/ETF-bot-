# Gold with MT5-only inputs

Gold vol10 rebuilt with inputs an MT5 EA can see (pre-registered 2026-11-08, before running):
G0 original (Yahoo DXY, TIP, COT)            - reference
G1 MT5 DXY (from EURUSD/USDJPY/GBPUSD/USDCAD) + TIP + COT
G2 MT5 DXY + COT, 2 of 2 (TIP dropped)
G3 MT5 DXY + gold own trend (close > SMA100) + COT, 2 of 3
G4 MT5 DXY + gold own trend, 2 of 2 (no outside data at all)
Pass = 2025-26 Sharpe >= 0.8 x G0's and full-period 2x-cost return > 0. All use vol10 sizing.

| Variant | 2016-20 Sharpe | 2021-24 Sharpe | 2025-26 Sharpe | 2025-26 %/yr | Worst drop | Full %/yr | 2x cost %/yr | Same position as original | Return corr | Pass |
|---|---|---|---|---|---|---|---|---|---|---|
| G0 original (DXY,TIP,COT) | 1.59 | 0.26 | 1.47 | 15.1% | -19.1% | 10.3% | 9.4% | 100% | 1.00 | yes |
| F1 MT5-DXY,FRED real yield,COT | 1.41 | 0.63 | 0.96 | 8.8% | -14.9% | 9.5% | 8.5% | 90% | 0.92 | no |
| F2 Yahoo DXY,FRED real yield,COT | 1.27 | 0.46 | 0.98 | 8.9% | -18.7% | 8.2% | 7.4% | 92% | 0.93 | no |
