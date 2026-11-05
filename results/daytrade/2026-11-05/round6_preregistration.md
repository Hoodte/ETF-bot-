# Intraday round 6: FX majors, gold and index CFDs (FTMO markets), 5m / 15m / 1h

Written 2026-11-05 before running. Data: HistData 1-minute (the same feed as Dukascopy; spot-checked to match exactly), 2016-01 to 2026-10, resampled to 5m/15m/1h.
Markets: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, XAUUSD, Nasdaq 100, S&P 500, DAX.
Costs per side: FX 0.6-0.8 bps, gold and US indices 1.0 bps, DAX 1.2 bps (half spread + commission + slippage, roughly FTMO raw pricing). Every finalist must also pass at 2x.
Families: as in round 1, plus opening ranges at the real London 08:00 / New York 09:30 opens (daylight-saving aware) and first break of the previous day's high/low (follow or fade).
Rules (config block `daytrade_fx`): Sharpe of at least 0.5 and PF of at least 1.05 in discovery (2016-20) and both validation folds (2021-22, 2023-24); at least 5 trades a week; shortlist of 30 (max 2 per market/timeframe/family) checked against nearby settings, 2x/3x costs, deflated Sharpe over every trial, then the 2025-26 holdout once; FTMO $100k sim (-10% max, -5% daily, 80% split).
Lesson from rounds 1-5 applied in advance: a single winner out of thousands means little, so the verdict needs **robust + holdout pass + deflated Sharpe of 0.95 or more**.
