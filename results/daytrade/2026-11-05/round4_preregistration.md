# Intraday round 4: crypto pairs (statistical arbitrage), hourly, market-neutral

Written 2026-11-05, before any round-4 run.

## Universe and data
14 Binance spot coins, hourly (2017-2026). All 91 pairs; a pair trades only when both coins have at least 60 days of history.

## Rule
- Hedge ratio beta = rolling OLS of log price A on log price B over L hours.
- Spread = log A - beta x log B; z = (spread - rolling mean) / rolling std over W hours.
- Enter when |z| > Z (short the spread if z > Z, long if z < -Z). **Fill at the close of the bar AFTER the signal** (a full bar of delay). Beta is frozen at entry.
- Exit when z crosses back through 0, after H hours, or on a stop at |z| > Z + 2.
- P&L per pair = position x (return of A - beta x return of B), divided by beta-hedged spread volatility at entry (equal risk per pair). Costs: 5 bps per side on both legs, scaled by (1 + |beta|).

## Grid (selection)
L {168, 720} x W {72, 168} x Z {2.0, 2.5, 3.0} x H {24, 72} = 24 configs. Selection: the best portfolio Sharpe (all pairs) over **2018-01 to 2021-12**.

## Periods
Validation 2022-2024; holdout 2025-01 to 2026-10 (run once at the end).

## Pass (all)
Validation portfolio Sharpe of at least 1.0 at 5 bps and above 0 at 10 bps; at least 1 trade a day; at least 55% of pairs with a positive P&L in validation; holdout Sharpe above 0.5.
