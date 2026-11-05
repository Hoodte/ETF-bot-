# ETF strategy search: shortlist report

Data `yahoo-adj-2026-11-04-e672facce1`. Search data ends 2020-12-31; holdout from 2021-01-01 was untouched until the shortlist was frozen.
Attempted 3841 configs: **1772 tested**, 1999 rejected as invalid, 70 duplicates.
Costs 5 bps per unit traded; signals at the close, fills at the next open.
Pass rule (every period: discovery 2005-2012, 2013-2016, 2017-2020): smaller max drawdown than the matched equal-weight benchmark, and CAGR no more than 2%/yr behind it.
**Survivorship bias:** All ETFs in the universes exist today; delisted funds are absent.

## Benchmarks (equal weight, every eligible ETF, monthly)

| Universe | Period | CAGR | Max DD | Sharpe |
|---|---|---|---|---|
| us_equity | disc | 6.6% | -54.9% | 0.39 |
| us_equity | val1 | 14.8% | -18.1% | 1.04 |
| us_equity | val2 | 16.2% | -34.8% | 0.85 |
| global_equity | disc | 5.1% | -58.2% | 0.33 |
| global_equity | val1 | 4.7% | -22.3% | 0.38 |
| global_equity | val2 | 11.5% | -31.7% | 0.72 |
| sectors | disc | 6.2% | -53.7% | 0.38 |
| sectors | val1 | 13.4% | -13.2% | 1.05 |
| sectors | val2 | 11.7% | -34.5% | 0.69 |
| bonds | disc | 6.4% | -10.0% | 0.94 |
| bonds | val1 | 1.5% | -9.5% | 0.28 |
| bonds | val2 | 6.7% | -12.5% | 1.08 |
| gold | disc | 18.1% | -30.2% | 0.91 |
| gold | val1 | -9.5% | -38.4% | -0.54 |
| gold | val2 | 12.9% | -14.0% | 0.95 |
| multi_asset | disc | 9.3% | -37.7% | 0.69 |
| multi_asset | val1 | 0.8% | -15.0% | 0.14 |
| multi_asset | val2 | 9.3% | -20.8% | 0.94 |

## Which strategy families held up

| Universe | Family | Tested | Pass all periods | Pass rate | Best worst-period MAR |
|---|---|---|---|---|---|
| bonds | breakout | 41 | 0 | 0% | 0.35 |
| bonds | ma_cross | 45 | 2 | 4% | 0.40 |
| bonds | rel_mom | 35 | 1 | 3% | 0.31 |
| bonds | sma | 34 | 0 | 0% | 0.36 |
| bonds | tsmom | 31 | 1 | 3% | 0.50 |
| global_equity | breakout | 55 | 0 | 0% | 0.32 |
| global_equity | ma_cross | 69 | 0 | 0% | 0.35 |
| global_equity | rel_mom | 51 | 1 | 2% | 0.32 |
| global_equity | sma | 64 | 0 | 0% | 0.32 |
| global_equity | tsmom | 56 | 0 | 0% | 0.32 |
| gold | breakout | 30 | 0 | 0% | -0.02 |
| gold | ma_cross | 32 | 0 | 0% | 0.43 |
| gold | sma | 29 | 0 | 0% | 0.24 |
| gold | tsmom | 30 | 0 | 0% | 0.23 |
| multi_asset | breakout | 97 | 1 | 1% | 0.44 |
| multi_asset | ma_cross | 95 | 1 | 1% | 0.54 |
| multi_asset | rel_mom | 128 | 21 | 16% | 0.40 |
| multi_asset | sma | 93 | 2 | 2% | 0.46 |
| multi_asset | tsmom | 95 | 3 | 3% | 0.56 |
| sectors | breakout | 62 | 0 | 0% | 0.47 |
| sectors | ma_cross | 71 | 2 | 3% | 0.39 |
| sectors | rel_mom | 77 | 14 | 18% | 0.32 |
| sectors | sma | 60 | 0 | 0% | 0.52 |
| sectors | tsmom | 65 | 0 | 0% | 0.68 |
| us_equity | breakout | 72 | 0 | 0% | 0.46 |
| us_equity | ma_cross | 67 | 2 | 3% | 0.31 |
| us_equity | rel_mom | 59 | 4 | 7% | 0.31 |
| us_equity | sma | 64 | 0 | 0% | 0.54 |
| us_equity | tsmom | 65 | 2 | 3% | 0.64 |

## Frozen shortlist: robustness and holdout

Robust = every nearby setting also passes (and keeps 50% or more of the MAR), and it still passes at 2x and 3x costs.

| Strategy | Search worst MAR | DSR | Nearby failing | 2x cost | 3x cost | Robust | Holdout CAGR (bench) | Holdout max DD (bench) | Holdout pass |
|---|---|---|---|---|---|---|---|---|---|
| `multi_asset|ma_cross(fast=150,slow=200)>rank:rel_mom(n=63)|top3|inv_vol60|weekly|confirm2|shy` | 0.54 | 0.84 | 5/12 | no | no | no | 10.1% (7.2%) | -22.3% (-20.8%) | no |
| `multi_asset|rel_mom(n=126)|top3|inv_vol120|monthly|scheduled|cash` | 0.40 | 0.93 | 4/7 | yes | yes | no | 11.5% (7.2%) | -20.2% (-20.8%) | yes |
| `multi_asset|rel_mom(n=126)|top3|inv_vol20|monthly|scheduled|cash` | 0.39 | 0.94 | 4/7 | yes | yes | no | 11.3% (7.2%) | -20.4% (-20.8%) | yes |
| `multi_asset|tsmom(n=252)>rank:rel_mom(n=126)|top3|equal|monthly|scheduled|cash` | 0.39 | 0.87 | 5/7 | no | no | no | 12.5% (7.2%) | -18.8% (-20.8%) | yes |
| `multi_asset|rel_mom(n=126)|top3|inv_vol60|monthly|scheduled|cash` | 0.37 | 0.94 | 4/8 | yes | no | no | 11.2% (7.2%) | -20.4% (-20.8%) | yes |
| `multi_asset|sma(n=200)>rank:rel_mom(n=126)|top5|equal|eq<=0.6|cash>=0.1|monthly|confirm2|cash` | 0.34 | 0.85 | 2/7 | yes | yes | no | 8.6% (7.2%) | -9.4% (-20.8%) | yes |
| `us_equity|tsmom(n=252)>rank:rel_mom(n=252)|top1|equal|monthly|scheduled|cash` | 0.33 | 0.78 | 2/6 | yes | yes | no | 7.0% (12.0%) | -25.0% (-28.9%) | no |
| `us_equity|tsmom(n=252)>rank:rel_mom(n=63)|top1|equal|monthly|scheduled|cash` | 0.33 | 0.80 | 4/6 | yes | no | no | 9.9% (12.0%) | -28.8% (-28.9%) | no |
| `multi_asset|tsmom(n=126)>rank:rel_mom(n=252)|top3|equal|eq<=0.6|monthly|confirm2|cash` | 0.27 | 0.76 | 4/7 | yes | yes | no | 10.5% (7.2%) | -12.1% (-20.8%) | yes |
| `sectors|ma_cross(fast=50,slow=200)>rank:rel_mom(n=189)|top5|inv_vol20|cap0.25|cash>=0.1|weekly|confirm2|cash` | 0.25 | 0.74 | 6/13 | no | no | no | 8.5% (14.1%) | -14.5% (-18.4%) | no |
| `sectors|ma_cross(fast=50,slow=200)>rank:rel_mom(n=126)|top3|equal|monthly|scheduled|cash` | 0.24 | 0.64 | 4/10 | no | no | no | 8.4% (14.1%) | -19.5% (-18.4%) | no |
| `bonds|ma_cross(fast=100,slow=200)|all|equal|cash>=0.1|monthly|scheduled|shy` | 0.20 | 0.85 | 3/7 | yes | yes | no | -0.5% (-2.1%) | -11.6% (-23.8%) | yes |
| `multi_asset|sma(n=200)>rank:rel_mom(n=252)|top3|equal|monthly|scheduled|cash` | 0.20 | 0.74 | 5/6 | no | no | no | 11.6% (7.2%) | -13.6% (-20.8%) | yes |
| `multi_asset|tsmom(n=189)>rank:rel_mom(n=252)|top5|equal|eq<=0.6|weekly|confirm2|cash` | 0.18 | 0.82 | 2/7 | yes | yes | no | 7.9% (7.2%) | -11.8% (-20.8%) | yes |
| `sectors|rel_mom(n=126)|top5|equal|monthly|scheduled|cash` | 0.15 | 0.57 | 2/4 | yes | yes | no | 12.5% (14.1%) | -16.4% (-18.4%) | yes |
| `bonds|rel_mom(n=126)|top3|equal|cash>=0.1|monthly|scheduled|cash` | 0.15 | 0.80 | 1/4 | yes | yes | no | -1.8% (-2.1%) | -18.5% (-23.8%) | yes |
| `sectors|rel_mom(n=126)|top2|inv_vol60|cap0.5|cash>=0.1|quarterly|buffer|shy` | 0.14 | 0.51 | 4/8 | yes | yes | no | 10.7% (14.1%) | -16.9% (-18.4%) | no |
| `us_equity|ma_cross(fast=50,slow=200)>rank:rel_mom(n=63)|top1|equal|monthly|scheduled|cash` | 0.13 | 0.69 | 6/9 | yes | no | no | 11.1% (12.0%) | -28.8% (-28.9%) | yes |
| `sectors|rel_mom(n=189)|top5|inv_vol120|cap0.25|quarterly|scheduled|shy` | 0.13 | 0.58 | 2/7 | yes | yes | no | 13.7% (14.1%) | -16.6% (-18.4%) | yes |
| `global_equity|rel_mom(n=189)|top3|inv_vol20|cap0.25|cash>=0.1|biweekly|buffer|cash` | 0.13 | 0.36 | 2/7 | yes | yes | no | 7.6% (9.5%) | -22.4% (-30.5%) | yes |
| `us_equity|rel_mom(n=63)|top3|inv_vol60|cap0.5|cash>=0.1|quarterly|confirm2|shy` | 0.12 | 0.60 | 0/7 | yes | yes | **yes** | 11.3% (12.0%) | -23.2% (-28.9%) | yes |
| `us_equity|rel_mom(n=63)|top1|equal|cash>=0.1|monthly|scheduled|shy` | 0.11 | 0.73 | 1/3 | yes | yes | no | 11.2% (12.0%) | -26.2% (-28.9%) | yes |
| `us_equity|ma_cross(fast=50,slow=200)>rank:rel_mom(n=252)|top1|equal|monthly|scheduled|cash` | 0.11 | 0.64 | 6/9 | yes | yes | no | 7.0% (12.0%) | -24.6% (-28.9%) | no |
| `us_equity|rel_mom(n=189)|top3|equal|cash>=0.1|monthly|confirm2|cash` | 0.10 | 0.55 | 3/4 | yes | yes | no | 9.1% (12.0%) | -23.7% (-28.9%) | no |
| `bonds|ma_cross(fast=150,slow=200)|all|equal|weekly|confirm2|shy` | 0.07 | 0.75 | 2/5 | yes | no | no | -0.3% (-2.1%) | -12.0% (-23.8%) | yes |

## Verdict

1 of 25 shortlisted strategies are robust AND passed the untouched holdout.
Deflated Sharpe (DSR) corrects for the number of trials tested; below 0.95 means the Sharpe alone could be luck.
The pass rule is about **lower drawdown at a limited return cost**, not about beating the benchmark's return.
