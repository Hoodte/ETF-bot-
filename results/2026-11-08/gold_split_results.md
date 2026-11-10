# Gold split-trade test

Run the pre-registered macro_composite variants through backtest, Time Machine and funded sim.
Usage: PYTHONPATH=. python3 results/2026-11-05/run_gold_variants.py <XAUUSD_H1 csv>


| Version | 2016-21 Sharpe | 2022-26 Sharpe | 2025-26 Sharpe | 10y %/yr | Worst drop | Pass |
|---|---|---|---|---|---|---|
| current (hold all) | 1.05 | 1.13 | 1.47 | 10.3% | -19.1% | - |
| half off at +2%, half held | 1.00 | 0.99 | 1.41 | 6.6% | -12.2% | no |
| half off at +3%, half held | 1.00 | 1.15 | 1.58 | 7.6% | -11.1% | no |
| half off at +5%, half held | 1.01 | 1.11 | 1.29 | 8.6% | -16.4% | no |
