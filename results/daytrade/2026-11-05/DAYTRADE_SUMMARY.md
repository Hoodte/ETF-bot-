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
| 6 | Full round-1 search plus DST-aware London/NY opening ranges and previous-day high/low breaks on EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, gold, Nasdaq, S&P, DAX at 5m/15m/1h (HistData 1-minute, FTMO-like costs 0.6-1.2 bps) | 17,523 | **0 pass.** Every 5m market loses on average; the 21 configs positive in all periods trade under 2 times a week |
| 7a | Index intraday momentum (first half-hour predicts last half-hour; Gao et al. 2018) on S&P, Nasdaq, DAX | 3 | Real before costs in 2016-24 (US gross Sharpe 0.3-0.8) but only about 1-2 bps per trade against 2 bps of costs, and gone in 2025-26. Fail |
| 7b | Best hourly rules picked on EURUSD/Nasdaq/gold 2016-20, applied to 6 unseen markets | 2,754 | Best (momentum) positive on only 1/6 unseen markets; portfolio -1.15. Fail |

## What the evidence says
- Short holds (5-15 min) lose to trading costs in every family tested.
- The only repeatable edge found is multi-hour crypto momentum (12-48 h holds). It worked from 2018 to 2024 across 14 coins but has stopped working in 2025-26, and that drop is about 2.5 standard errors, so it is probably not just noise.
- Nothing found meets the 1-2 trades/day + GBP 500-1,000/week target at survivable prop-firm sizing. The closest (round 3 before the holdout) implied about $100-180 a week at 85% or more account survival, and it then failed the holdout.

## The arithmetic of the target
GBP 500-1,000 a week after an 80% split = about $41k-83k a year of gross profit on $100k, i.e. 40-80% a year, while never losing 10% from the start (or 5% in a day).
At the ~6% annual volatility a 10% max-loss account can survive, that needs a Sharpe ratio of roughly 6-12, net of costs. In ~28,000 tested configurations the best robust strategies scored around 1-2 before failing out-of-sample.
Funds with Sharpe above 3 generally rely on market-making, co-location or proprietary data, which are not available through a retail prop-firm account.
