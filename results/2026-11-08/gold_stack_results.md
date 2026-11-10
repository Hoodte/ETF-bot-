# Gold stacking test

Run the pre-registered macro_composite variants through backtest, Time Machine and funded sim.
Usage: PYTHONPATH=. python3 results/2026-11-05/run_gold_variants.py <XAUUSD_H1 csv>


| Version | 2016-21 Sharpe | 2022-26 Sharpe | 2025-26 Sharpe | 10y %/yr | Worst drop | Pass |
|---|---|---|---|---|---|---|
| current (1 unit) | 1.05 | 1.13 | 1.47 | 10.3% | -19.1% | - |
| double size always | 1.05 | 1.13 | 1.47 | 20.6% | -35.8% | no |
| A1 add on -2% dip | 1.01 | 0.97 | 1.12 | 12.5% | -26.2% | no |
| A2 add on -3% dip | 1.11 | 1.11 | 1.32 | 13.8% | -24.4% | no |
| P1 add on +2% rise | 0.99 | 1.10 | 1.38 | 16.9% | -33.5% | no |
| P2 add on +3% rise | 1.11 | 0.98 | 1.22 | 15.9% | -31.9% | no |
