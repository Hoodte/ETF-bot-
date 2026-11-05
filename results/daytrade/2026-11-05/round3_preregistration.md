# Intraday round 3: crypto derivatives and order-flow signals (perpetual futures, hourly)

Written 2026-11-05, before any round-3 run. The data (Binance USD-M perpetuals: 1h klines with taker-buy volume, 8-hourly funding rates, 1h premium index) starts in 2020, so the periods differ from rounds 1-2.

## Periods
- Selection (BTC + ETH only): 2020-01-01 to 2022-06-30
- Validation (all 14 coins): 2022-07-01 to 2024-12-31
- Holdout: 2025-01-01 to 2026-10-31, run once at the end

## Signal families (each signal at the close of hour t, using only data known by then)
| Family | Measure | Variants |
|---|---|---|
| funding | z-score of the latest funding rate vs the last W days | W {14, 30, 60}; threshold {1.5, 2, 2.5}; fade or follow |
| taker | (taker buys - taker sells) / volume over the last n hours, z-scored over 500 hours | n {1, 4, 12, 24}; threshold {1.5, 2, 2.5}; fade or follow |
| premium | perp premium vs index, averaged over n hours, z-scored over 500 hours | n {1, 8, 24}; threshold {1.5, 2, 2.5}; fade or follow |
| crowd_momentum | the round-2 momentum rule (n=48, z=1.5, with trend) taken only when funding is NOT stretched the same way (z below threshold) | threshold {0.5, 1.0, 1.5} |

Exits: time {4, 8, 24} hours, or bracket (1,2) / (1.5,1.5) ATR with 24-hour max; trend filter none or with (except crowd_momentum, always with); both directions.

## Selection
For each family: the best mean selection-period Sharpe across BTC and ETH, with both above 0.5 and at least 0.5 trades a week per coin. That gives up to 4 frozen candidates.

## Pass (each candidate, all required)
- 14-coin portfolio (equal ATR risk per trade) Sharpe of at least 1.0 in validation at 5 bps per side, and above 0 at 10 bps
- At least 8 of the 12 coins not used for selection positive over validation
- At least 1 trade a day for the portfolio
- Holdout portfolio Sharpe above 0.5

## Bug fix after the first run (2026-11-05)
The first run read funding and premium timestamps as timezone-naive, so they didn't line up with the price bars (premium never fired; funding and the crowding filter were mostly blank). Fixed by tagging them UTC and putting a floor on the funding z-score's standard deviation (funding often sits flat at 0.01%). Rerun with the same grid and rules. **Honesty note:** the taker and crowd_momentum holdout results were already seen in the buggy run. Taker is unaffected by the fix, so its earlier result stands. For crowd_momentum the holdout is no longer fully unseen.
