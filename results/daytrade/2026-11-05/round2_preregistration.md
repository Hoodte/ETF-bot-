# Intraday round 2: does crypto momentum replicate on coins it was never tuned on?

Written 2026-11-05, after round 1 (0 of 4,659 passed) and before any round-2 run.

## Why
In round 1 the only idea that was positive in all three search periods was short-term momentum traded with the 200-bar trend on BTC/ETH, but it fires only about 3 times a week per coin. If the effect is real, it should also appear on other coins. Spread across many coins it would reach 1-2 trades a day.

## Step 1: selection (BTC + ETH, discovery period only, up to 2020-12-31)
- Grid: momentum (n x z, 12 sets) x trend {with, none} x vol {any, high} x exit {time, bracket (1,2), bracket (1.5,1.5)} x hold {12, 24, 48}; session all; both directions; no end-of-day exit.
- Done separately for 15m and 1h bars. Pick the single config with the best **mean** discovery Sharpe over BTC and ETH, with both above 0.5. Nothing after 2020 is looked at.

## Step 2: frozen tests
1. **Cross-market:** the frozen rule on 12 coins never used in selection (SOL, BNB, XRP, ADA, DOGE, LTC, LINK, AVAX, DOT, TRX, BCH, ATOM), from their first data to 2024-12-31.
2. **Validation for BTC/ETH:** 2021-2024.
3. **Portfolio:** all 14 coins, each trade worth the same ATR risk; daily P&L summed. Validation 2021-2024.
4. **Holdout 2025-01 to 2026-10:** run once, after steps 1-3 are written down.

## Pass (all required)
- Portfolio Sharpe of at least 1.0 net of 5 bps per side in 2021-2024, and above 0 at 10 bps.
- At least 8 of the 12 never-seen coins have a positive Sharpe.
- Portfolio averages at least 1 trade a day.
- Holdout portfolio Sharpe above 0.5.

## Funded-account sizing (only if it passes)
Using 2021-2026 daily portfolio P&L only (after selection): the largest risk per ATR unit keeping the account in 85% or more of bootstrapped years under -10% max loss and -5% daily loss; typical and average weekly profit at an 80% split.
