# Order-flow exits for Nasdaq lunch-RSI — pre-registration (15 Nov 2026, written before any data was seen)

Data: Databento GLBX.MDP3 trades, NQ.v.0 (front contract by volume), aggressor side (B = buyer lifted the ask,
A = seller hit the bid). Windows: entry - 60 min to exit + 16 min for each of the 596 backtest trades.
Shrunk to 1-minute bars (OHLC, buy volume, sell volume) and a 15-minute footprint (volume by 1-point price level,
buy/sell). Signals are computed on NQ; the trade result stays the US100 CFD backtest result.

Decision point (same as the smart-exit test): the first completed M15 bar (from the entry bar on) whose high reaches
entry + 0.8R, provided the stop was not hit first. Trades that never reach +0.8R are unchanged.
"Close" = exit at +0.8R minus the trade's cost. "Hold" = the original result.
Order-flow numbers use only minutes from entry up to the END of the decision bar (no look-ahead).
delta = buy volume - sell volume.

Each rule tested ALONE against the current exit. Thresholds fixed here, no tuning. Nearby values reported as checks.

| # | Signal | Rule at the decision point | Nearby checks |
|---|---|---|---|
| 1 | Delta divergence | decision bar makes a new NQ high since entry AND the decision bar's delta < 0 -> close | bar delta < -10% / < +10% of bar volume |
| 2 | Absorption at the high | share of the decision bar's volume traded in the top 25% of its range >= 40% AND bar closes in the lower half of its range -> close | 35% / 45% |
| 3 | Stacked sell imbalances | >= 3 consecutive 1-point levels in the decision bar where sell vol >= 3x buy vol -> close | 2 levels / 4 levels; ratio 2.5x / 4x |
| 4 | Delta not confirming | cumulative delta from entry to end of decision bar <= 0 -> close (i.e. hold only when buyers have been net aggressive) | CVD <= -5% / <= +5% of volume since entry |
| 5 | Stretched above value | 70% value area of volume from (entry - 60 min) to the decision; (NQ close - VAH) / R(NQ) > 1.0 -> close | 0.5 / 1.5 |

Note on #5: the plan said "the day's value area". The windows start 60 min before entry (~10:30-12:30 NY), not at
09:30, so the value area is the pre-decision window, not the full session. Stated here before testing.

R(NQ) for #5: the trade's R scaled to NQ by price ratio (R_cfd / entry_cfd * NQ price at entry).

6 (model): add the order-flow numbers (bar delta / bar volume, CVD since entry / volume, top-quarter share,
max stacked sell levels, stretch vs VAH) to the existing smart-exit logistic model; train 2016-20 ONLY, threshold 0.5,
judge 2021-24 and 2025-26. Compare with the same model without order-flow features.

Judging (same as all earlier exit tests):
- total R vs current, split 2016-20 / 2021-24 / 2025-26; R saved on losers vs R given up on winners
- a rule only goes to shadow mode if it helps in all three periods (or clearly in both later periods), nearby
  settings agree, and a month-block bootstrap of the 2021-26 gain gives < 5% chance of no gain.
- 6 rules + nearby checks = many comparisons: a single lucky winner is expected by chance; say so.
