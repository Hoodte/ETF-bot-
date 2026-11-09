# Gold entry timing

Run the pre-registered macro_composite variants through backtest, Time Machine and funded sim.
Usage: PYTHONPATH=. python3 results/2026-11-05/run_gold_variants.py <XAUUSD_H1 csv>


| Entry | 2016-21 Sharpe | 2022-26 Sharpe | 2025-26 Sharpe | 10y %/yr | Worst drop | 2x cost %/yr | Time in trade vs current | Pass |
|---|---|---|---|---|---|---|---|---|
| E0 buy straight away (current) | 1.05 | 1.13 | 1.47 | 10.3% | -19.1% | 9.4% | 100% | - |
| E1 RSI14<40 | 1.04 | 0.94 | 1.08 | 9.0% | -20.6% | 8.2% | 90% | no |
| E2 daily RSI2<25 | 0.99 | 0.79 | 0.99 | 7.5% | -16.8% | 7.0% | 77% | no |
| E3 EMA20 rejection | 1.07 | 0.83 | 1.06 | 7.9% | -19.1% | 7.4% | 74% | no |
| E4 prev-low sweep | 1.01 | 1.01 | 1.43 | 9.2% | -21.0% | 8.4% | 91% | no |
| E5 RSI14<40, 5-day timeout | 1.03 | 0.93 | 1.08 | 8.9% | -20.6% | 8.1% | 90% | no |
| E6 EMA20 rejection, 5-day timeout | 1.05 | 0.68 | 1.19 | 7.8% | -19.8% | 7.1% | 83% | no |
