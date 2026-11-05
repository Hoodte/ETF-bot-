# Intraday round 5: hour-of-day / hour-of-week seasonality

Written 2026-11-05 before running. Markets: gold 1h and 14 coins 1h.
- Measure the mean return of each hour-of-day (24 buckets) and each hour-of-week (168 buckets) in the selection period only (gold 2016-2020, coins from their start to 2021-12).
- Trade a bucket when its t-statistic is above T (long) or below -T (short), T in {2.0, 2.5, 3.0}: enter at the bucket's open, exit at its close.
- Costs per side: 3 bps for gold, 5 bps for coins.
- Validation 2022-2024; holdout 2025-26.
- Pass: portfolio Sharpe of at least 1.0 in validation and above 0.5 in the holdout, with at least 1 trade a day.
