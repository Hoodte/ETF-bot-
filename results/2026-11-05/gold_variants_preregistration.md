# Gold macro_composite: variant search, pre-registration

Written 2026-11-05, before any of these variants were run.

## Base
macro_composite (frozen): long gold when at least 2 of 3 hold:
DXY below its 50-day SMA, TIP 20-day change above 0, and COT managed-money 3-year percentile below 0.70.

## Variants (fixed list; no others will be added after seeing results)
| ID | Variant | What changes |
|---|---|---|
| V0 | original | frozen base |
| V1 | vol10 | size = 10% / 20-day realised vol, capped at 1.5 (already tested; counted again here) |
| V2 | strict_3of3 | all three votes required |
| V3 | loose_1of3 | any one vote |
| V4 | graded | position = votes / 3 |
| V5 | graded_vol10 | V4 x vol scaling |
| V6 | four_vote | add 10y Treasury yield 20-day fall as 4th vote, need 3 of 4 |
| V7 | long_short | long on 2 or more votes, short on 0 votes |
| V8 | long_short_vol10 | V7 x vol scaling |
| V9 | trend_gate | base AND gold above its 100-day SMA |
| V10 | dd_brake | base, size halved while the strategy is more than 8% below its peak (lagged one day) |
| V11 | weekend_flat | base, flat from Friday 19:00 UTC to the Sunday open (prop-firm friendly) |
| V12 | vol10_weekend_flat | V1 + V11 |

## Testing
- Costs: 3 bps per side; 2x-cost stress for the finalists.
- In-sample (IS) 2016-2021; out-of-sample (OOS) 2022 to Oct 2026.
- Time Machine: block bootstrap of daily returns (20-day blocks, 10,000 one-year paths). Report median return, 5th-percentile return, 5th-percentile worst drop, chance of a losing year, chance of beating holding gold.
- Funded $100k simulation: +/-10% overall loss limit, 5% daily loss limit, 80% split, 2%/yr swap on exposure, sizes 0.5x to 1.5x.
- Multiple-testing: deflated Sharpe over the full history, counting **30 trials** in total (14 earlier gold strategies, walk-forward, vol10, vol15, and these 13).

## Selection rule (fixed in advance)
The winner is the variant with the best **IS** Sharpe that also:
1. has an OOS Sharpe at least 80% of its IS Sharpe;
2. has a deflated Sharpe of 0.95 or more at 30 trials;
3. stays profitable at 2x costs.

If no variant passes, V0 stays. OOS is used only to confirm the choice, never to pick it.
