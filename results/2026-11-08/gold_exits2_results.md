# Gold exit variations

Run the pre-registered macro_composite variants through backtest, Time Machine and funded sim.
Usage: PYTHONPATH=. python3 results/2026-11-05/run_gold_variants.py <XAUUSD_H1 csv>


| Exit | 2016-21 Sharpe | 2022-26 Sharpe | 2025-26 Sharpe | 10y %/yr | Worst drop | Pass |
|---|---|---|---|---|---|---|
| no stop (signal exit only) | 1.05 | 1.13 | 1.47 | 10.3% | -19.1% | - |
| fixed 3% | 0.78 | 0.96 | 1.39 | 6.9% | -18.0% | no |
| fixed 5% (current) | 1.09 | 1.14 | 1.49 | 10.3% | -20.1% | yes |
| fixed 7% | 1.10 | 1.07 | 1.32 | 10.2% | -17.7% | no |
| trailing 3% | 1.07 | 0.81 | 1.77 | 6.7% | -13.7% | no |
| trailing 5% | 0.96 | 0.87 | 1.24 | 7.5% | -17.1% | no |
| trailing 8% | 1.09 | 1.20 | 1.67 | 10.3% | -19.4% | yes |
| trailing 2x ATR | 0.39 | 0.84 | 1.70 | 3.1% | -10.1% | no |
| trailing 3x ATR | 0.97 | 0.57 | 0.83 | 5.6% | -16.6% | no |
| trailing 4x ATR | 1.04 | 0.66 | 0.78 | 7.0% | -13.2% | no |
| fixed 5% + trailing 8% | 1.12 | 1.24 | 1.77 | 10.6% | -19.2% | yes |
