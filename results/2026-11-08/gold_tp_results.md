# Gold take-profit test

Run the pre-registered macro_composite variants through backtest, Time Machine and funded sim.
Usage: PYTHONPATH=. python3 results/2026-11-05/run_gold_variants.py <XAUUSD_H1 csv>


| Take profit | 2016-21 Sharpe | 2022-26 Sharpe | 2025-26 Sharpe | 10y %/yr | Worst drop | Pass |
|---|---|---|---|---|---|---|
| none (current) | 1.05 | 1.13 | 1.47 | 10.3% | -19.1% | - |
| +1% | 0.27 | 0.53 | 0.29 | 1.5% | -12.0% | no |
| +2% | 0.60 | 0.48 | 0.81 | 2.8% | -11.1% | no |
| +3% | 0.71 | 0.90 | 1.33 | 4.7% | -11.1% | no |
| +5% | 0.88 | 0.93 | 0.88 | 6.8% | -16.2% | no |
