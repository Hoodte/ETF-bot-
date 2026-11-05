# Round 10: economic-news surprise strategy (US + Canada releases), 1-minute execution

Written 2026-11-05 before running.

## Data
- Forex Factory calendar archive (Hugging Face dataset Ehsanrs2/Forex_Factory_Calendar, 2007 to 2025-04-07). Its timestamps are shifted. For USD and CAD events, wall-clock + 8h30m in New York time reproduces the known schedule (NFP Friday 08:30, CPI 08:30, CAD jobs Friday 08:30). Non-North-American events are inconsistent and excluded. Rows whose corrected time differs from that event's usual release time (mode over 2016-2020) are dropped.
- Prices: HistData 1-minute EURUSD, GBPUSD, AUDUSD, USDJPY, USDCAD, XAUUSD.

## Signal
- High-impact USD and CAD events with numeric actual and forecast.
- Surprise z = (actual - forecast) / standard deviation of that event's PAST surprises (at least 10 prior), sign flipped where Forex Factory says "Actual less than Forecast is good for currency".
- USD events trade all 6 instruments (long USD side when the surprise is good for USD; gold is treated as USD-quoted); CAD events trade USDCAD.
- Modes: follow (trade in the surprise direction) or fade (the opposite).

## Grid (54 configs)
Entry delay after release {1, 5, 15} min x hold {15, 60, 240} min x |z| threshold {0.5, 1.0, 1.5} x mode {follow, fade}.
Entry at the open of the 1-minute bar at release + delay; exit at the close of the last bar of the hold.

## Costs
News-time spreads are wider, so double the normal per-side cost: FX 1.2-1.6 bps, gold 2.0 bps. Stress test at 2x that.

## Periods
- Selection: 2016-2020 (best portfolio Sharpe, P&L per trade scaled by the instrument's 20-day daily volatility)
- Validation: 2021-2024
- Holdout: 2025-01-01 to 2025-04-07 (the dataset ends there, so only about 3 months: a weak check)

## Pass
Validation Sharpe of at least 1.0 and above 0 at 2x stress costs; at least 1 trade a day on average; holdout Sharpe above 0.

## Round 10b: independent re-test on TradingView calendar data (written before running)
The round-10 holdout was only 3 months (Forex Factory archive ends 2025-04). TradingView's calendar API gives US and CA events 2015-2026 with correct UTC times and actual/forecast values.
- **Frozen rule from round 10, unchanged:** follow the surprise, enter 5 min after release, hold 60 min, |z| > 0.5, same instruments and costs.
- Events: importance = high (1), country US or CA, numeric actual and forecast; energy-inventory releases excluded (Crude/Gasoline/Natural Gas/EIA). Lower is good for the currency for titles containing "Unemployment Rate" or "Jobless Claims"; higher is good otherwise.
- z = surprise / std of that title's past surprises (at least 10 prior).
- Report 2016-2020, validation 2021-2024, **holdout 2025-01 to 2026-10 (about 22 months, never used)**.
- Pass: validation Sharpe of at least 1.0 and above 0 at 2x stress costs; holdout Sharpe above 0.5 and above 0 at 2x stress costs.
