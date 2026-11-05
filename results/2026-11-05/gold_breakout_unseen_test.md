# Gold 20-hour breakout: test on unseen data

The lead (Donchian 20-hour breakout, long and short) was found on Yahoo hourly gold data from June 2024 to November 2026. This test uses 10 years of Dukascopy hourly XAUUSD bars (64,074 bars), with the rule frozen exactly as found, and judges it on Jan 2016 to mid-2024, which it never saw.

| Test | Return/yr | Sharpe | Worst drop | Chance the edge is real |
| --- | --- | --- | --- | --- |
| Unseen 2016–mid 2024, 1.5 bps/side | -1.5% | -0.04 | -28% | 46% |
| Unseen 2016–mid 2024, 3 bps/side | -7.0% | -0.45 | -53% | 10% |
| Unseen 2016–mid 2024, 4.5 bps/side | -12.2% | -0.85 | -71% | 1% |
| 2024–2026, where it was found (3 bps) | +15.6% | 0.77 | -15% | 88% |
| Gold buy & hold, unseen period | +9.7% | 0.73 | -22% | — |

Other lookbacks (16, 24, 40, 60 hours) on the unseen period: all between -8.6% and -0.2% a year.

Year by year (3 bps): 2016 -18.9%, 2017 -3.3%, 2018 -15.7%, 2019 -6.2%, 2020 +11.1%, 2021 -5.1%, 2022 -20.5%, 2023 +2.6%, 2024 +5.0%, 2025 +14.6%, 2026 +18.5%.

**Verdict: rejected.** The rule only worked during gold's unusually strong trend of 2024–2026. Over the eight years before that it lost money after realistic costs. About 0.5 trades a day.

Data: Dukascopy hourly BID candles, downloaded to the laptop folder `backtestbot/data/XAUUSD_H1_2016_2026.csv` with `backtestbot/dukas_hourly.py`.
