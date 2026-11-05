# Day-trading strategy hunt, 2026-11-05: summary

Goal: 1-2 trades a day, GBP 500-1,000 a week on a $100k funded account (80% split), i.e. roughly 3.5-7% a month with no 10% drawdown.
Rules: every round was pre-registered; selection used early data only; later periods and a 2025-26 holdout were run once; costs 3 bps (gold) / 5 bps (crypto) per side, stressed at 2x.

| Round | What | Configs | Result |
|---|---|---|---|
| 1 | Breakout, momentum, RSI reversion, band fade, opening-range breakout on gold 1h and BTC/ETH 1h/15m/5m, with trend/vol/session filters and bracket/time exits | 4,659 | **0 pass.** Faster timeframes are destroyed by costs; nothing with 5+ trades/week held up in all periods |
| 2 | Best round-1 idea (momentum with trend) chosen on BTC/ETH up to 2020, applied unchanged to 12 unseen coins | 432 + 2 frozen | 1h version: positive on **12/12 unseen coins**, portfolio Sharpe 1.81 in 2021-24 at about 2 trades/day, but **-0.26 in the 2025-26 holdout**. Fail |
| 3 | Perp-futures data: funding-rate extremes, taker order-flow imbalance, futures premium, momentum with a crowding filter | 615 + 4 frozen | Crowding-filtered momentum: 1.63 in validation, 10/12 unseen coins positive, **-0.23 in the holdout**. Others fail validation. Fail |
| 4 | Crypto pairs stat-arb (91 pairs) | 24 | Strongly negative; crypto spreads trend instead of reverting. Fail |
| 5 | Hour-of-day / hour-of-week seasonality, gold + 14 coins | 6 | Strongly negative after costs. Fail |

## What the evidence says
- Short holds (5-15 min) lose to trading costs in every family tested.
- The only repeatable edge found is multi-hour crypto momentum (12-48 h holds). It worked from 2018 to 2024 across 14 coins but has stopped working in 2025-26, and that drop is about 2.5 standard errors, so it is probably not just noise.
- Nothing found meets the 1-2 trades/day + GBP 500-1,000/week target at survivable prop-firm sizing. The closest (round 3 before the holdout) implied about $100-180 a week at 85% or more account survival, and it then failed the holdout.

## Not yet tested (data needed from the laptop / Windows PC)
FX majors, index CFDs (NAS100, US500, GER40) and gold below 1h, via Dukascopy (blocked from the cloud).
