# Round 8: combined-analysis machine-learning model (walk-forward), FTMO markets, hourly

Written 2026-11-05 before running. The idea: no single indicator; one model weighs many types of analysis together.

## Markets and data
EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, XAUUSD, Nasdaq 100, S&P 500, DAX: 1h bars from HistData 1-minute (2016-2026). Daily DXY, TIP and VIX from Yahoo, lagged one day.

## Features (all known at the close of bar t)
- **Trend / momentum:** returns over 1, 4, 12, 24, 72, 120 bars (in ATR units); distance to the 20/50/200-bar averages (ATR units)
- **Mean reversion:** RSI(2), RSI(14), Bollinger z-score (20)
- **Volatility regime:** ATR percentile (500 bars), short/long realised-vol ratio
- **Time / session:** hour of day (sin/cos), day of week
- **Price levels:** distance to the previous day's high and low, position in today's range
- **Cross-market:** 4h and 24h normalised returns of EURUSD (dollar), Nasdaq (risk mood), gold, USDJPY
- **Macro (daily, lagged):** DXY vs its 50-day average, TIP 20-day change, VIX level and 5-day change
- **Market identity** (categorical)

## Target and model
- Label: sign of the move from the next bar's open to the close H bars later. Two pre-registered variants: H = 4 and H = 12.
- LightGBM, fixed settings (no tuning): 400 trees, learning rate 0.03, 31 leaves, min 500 rows per leaf, 70% row/column sampling, L2 = 5. One model pooled across all 9 markets.

## Walk-forward (no future data, ever)
For each test year Y in 2019-2024:
1. Train on data ending before Y-1 (7-day purge), predict year Y-1, and set the long/short thresholds at the 95th/5th percentile of those predictions.
2. Retrain on data ending before Y (7-day purge) and trade year Y with those thresholds.

Holdout 2025-01 to 2026-10: the same procedure with the model trained to the end of 2024, run once at the end.

## Trading
Enter at the next bar's open when the prediction is beyond a threshold; hold H bars; one position per market; equal ATR risk; costs per side FX 0.6-0.8 bps, gold/US indices 1.0, DAX 1.2; 2x stress.

## Pass (all)
Walk-forward 2019-2024 portfolio Sharpe of at least 1.0 net, above 0 at 2x costs, positive in at least 4 of the 6 years, at least 1 trade a day, and holdout Sharpe above 0.5.
