# Gold macro_composite variants: results

See gold_variants_preregistration.md for the fixed rules.
TM = Time Machine (10,000 bootstrapped one-year paths). Funded sim: best size keeping the account in 85% or more of years.

| Variant | IS Sharpe | OOS Sharpe | OOS %/yr | OOS worst drop | TM median yr | TM bad yr (5%) | TM P(loss yr) | TM P(beat gold) | DSR | 2x cost %/yr | Pass |
|---|---|---|---|---|---|---|---|---|---|---|---|
| V1 vol10 (baseline) | 1.05 | 1.13 | 10.0% | -11.6% | 8.5% | -6.3% | 19% | 43% | 0.98 | 9.4% | yes |
| R1 dxy_momentum | 0.94 | 1.21 | 11.0% | -12.8% | 8.3% | -6.8% | 20% | 41% | 0.97 | 9.2% | yes |
| R2 dxy_band | 0.95 | 0.92 | 8.1% | -12.1% | 7.5% | -7.6% | 23% | 38% | 0.94 | 8.1% | no |
| R3 breakeven | 0.29 | 0.88 | 8.2% | -15.5% | 4.0% | -10.1% | 34% | 26% | 0.66 | 4.1% | no |
| R4 cot_flow | 0.47 | 1.11 | 9.4% | -13.3% | 5.0% | -8.4% | 29% | 30% | 0.83 | 5.7% | no |
| R5 sticky_exit | 0.70 | 1.26 | 14.3% | -19.0% | 8.9% | -9.3% | 23% | 40% | 0.95 | 10.2% | no |
| R6 dip_entry | 1.02 | 1.09 | 9.4% | -11.1% | 8.0% | -6.6% | 20% | 42% | 0.97 | 8.9% | yes |
| R7 silver_vote | 0.12 | 1.33 | 9.7% | -9.6% | 3.3% | -8.3% | 33% | 27% | 0.73 | 3.7% | no |

| Variant | Best safe size | Keep account | Typical month | Average month |
|---|---|---|---|---|
| V1 vol10 (baseline) | 1.25x | 88% | $564 | $747 |
| R1 dxy_momentum | 1.00x | 93% | $453 | $588 |
| R2 dxy_band | 1.00x | 91% | $390 | $539 |
| R3 breakeven | 1.00x | 86% | $179 | $385 |
| R4 cot_flow | 1.00x | 91% | $263 | $431 |
| R5 sticky_exit | 0.75x | 93% | $350 | $475 |
| R6 dip_entry | 1.25x | 88% | $527 | $716 |
| R7 silver_vote | 1.25x | 88% | $199 | $428 |

**Winner by the pre-registered rule: V1 vol10 (baseline)**
