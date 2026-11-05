# Gold macro_composite variants: results

See gold_variants_preregistration.md for the fixed rules.
TM = Time Machine (10,000 bootstrapped one-year paths). Funded sim: best size keeping the account in 85% or more of years.

| Variant | IS Sharpe | OOS Sharpe | OOS %/yr | OOS worst drop | TM median yr | TM bad yr (5%) | TM P(loss yr) | TM P(beat gold) | DSR | 2x cost %/yr | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| V0 original | 0.87 | 0.79 | 10.6% | -20.6% | 8.3% | -8.5% | 22% | 40% | 0.89 | 9.1% | no |
| V1 vol10 | 1.05 | 1.13 | 10.0% | -11.6% | 8.5% | -6.3% | 19% | 43% | 0.98 | 9.4% | yes |
| V2 strict_3of3 | 0.32 | 0.36 | 2.9% | -19.0% | 1.5% | -7.6% | 39% | 25% | 0.40 | 1.9% | no |
| V3 loose_1of3 | 0.82 | 0.90 | 15.3% | -29.4% | 10.4% | -11.0% | 22% | 44% | 0.92 | 12.5% | no |
| V4 graded | 0.81 | 0.83 | 9.7% | -19.6% | 6.8% | -7.0% | 22% | 31% | 0.89 | 8.0% | no |
| V5 graded_vol10 | 0.91 | 1.25 | 9.1% | -11.2% | 6.6% | -5.7% | 21% | 33% | 0.98 | 7.7% | yes |
| V6 four_vote | 0.73 | 0.42 | 4.4% | -19.0% | 4.7% | -8.4% | 29% | 31% | 0.68 | 4.8% | no |
| V7 long_short | 0.88 | 0.63 | 8.7% | -20.2% | 8.1% | -9.7% | 24% | 41% | 0.85 | 8.6% | no |
| V8 long_short_vol10 | 1.07 | 0.88 | 8.4% | -10.9% | 8.2% | -7.5% | 21% | 42% | 0.96 | 8.9% | yes |
| V9 trend_gate | 0.64 | 0.80 | 10.3% | -19.0% | 5.9% | -8.9% | 27% | 34% | 0.81 | 7.0% | no |
| V10 dd_brake | 0.97 | 0.69 | 8.0% | -18.7% | 6.9% | -7.5% | 23% | 36% | 0.89 | 8.1% | no |
| V11 weekend_flat | 0.63 | 0.59 | 7.3% | -18.1% | 5.9% | -9.9% | 28% | 30% | 0.71 | 4.1% | no |
| V12 vol10_weekend_flat | 0.82 | 0.87 | 7.3% | -11.0% | 6.3% | -7.5% | 25% | 33% | 0.90 | 5.0% | no |

| Variant | Best safe size | Keep account | Typical month | Average month |
|---|---|---|---|---|
| V0 original | 0.75x | 88% | $282 | $419 |
| V1 vol10 | 1.25x | 88% | $564 | $747 |
| V2 strict_3of3 | 0.50x | 100% | $38 | $119 |
| V3 loose_1of3 | 0.50x | 97% | $293 | $377 |
| V4 graded | 0.75x | 91% | $234 | $344 |
| V5 graded_vol10 | 1.25x | 92% | $431 | $594 |
| V6 four_vote | 0.75x | 90% | $137 | $280 |
| V7 long_short | 0.75x | 85% | $255 | $419 |
| V8 long_short_vol10 | 1.00x | 91% | $435 | $592 |
| V9 trend_gate | 0.75x | 88% | $197 | $339 |
| V10 dd_brake | 0.75x | 90% | $233 | $367 |
| V11 weekend_flat | 0.75x | 87% | $177 | $329 |
| V12 vol10_weekend_flat | 1.25x | 86% | $401 | $599 |

**Winner by the pre-registered rule: V8 long_short_vol10**
