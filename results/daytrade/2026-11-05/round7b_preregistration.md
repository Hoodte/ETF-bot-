# Round 7b: do the best hourly rules carry over to markets they weren't picked on? (FX / gold / indices)

Written 2026-11-05 before running.
- Training markets: EURUSD, Nasdaq 100, XAUUSD (1h), discovery period 2016-2020 only.
- Grid: families breakout, momentum, rsi_revert, band_fade (all parameter sets) x trend {none, with, against} x vol {any, high, low} x exit {time; bracket (1,2); bracket (1.5,1.5)} x hold {12, 24, 48}; all sessions; both directions.
- For each family, freeze the config with the best mean discovery Sharpe across the 3 training markets, provided all 3 are above 0.3 and each trades at least 0.5 times a week.
- Frozen tests: (1) the 6 markets never used (GBPUSD, USDJPY, AUDUSD, USDCAD, S&P 500, DAX), 2016-2024; (2) 9-market portfolio (equal ATR risk per trade), 2021-2024; (3) holdout 2025-26 once.
- Pass: at least 4 of the 6 unseen markets positive; portfolio Sharpe of at least 1.0 in 2021-24 and above 0 at 2x costs; at least 1 trade a day; holdout Sharpe above 0.5.
