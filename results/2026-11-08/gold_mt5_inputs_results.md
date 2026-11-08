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
| G1 MT5-DXY,TIP,COT | 1.70 | 0.37 | 1.64 | 17.2% | -18.9% | 11.6% | 10.7% | 98% | 0.98 | yes |
| G2 MT5-DXY+COT 2of2 | 1.16 | 0.46 | 0.91 | 6.1% | -14.6% | 5.5% | 5.0% | 65% | 0.68 | no |
| G3 MT5-DXY,trend,COT | 0.93 | 0.20 | 1.88 | 21.2% | -23.8% | 7.7% | 6.9% | 76% | 0.83 | yes |
| G4 MT5-DXY+trend (pure MT5) | 0.38 | 0.72 | 1.56 | 14.4% | -12.8% | 5.2% | 4.6% | 66% | 0.71 | yes |
