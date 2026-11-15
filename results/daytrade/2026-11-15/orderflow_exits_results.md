Trades: 596; with order-flow data downloaded: 596; reaching +0.8R with data: 355

Change in total R vs current exit (trades with order-flow data only)

| Rule | Trades closed early | 2016-20 | 2021-24 | 2025-26 | Full | Saved on losers | Given up on winners |
|---|---|---|---|---|---|---|---|
| 1 Delta divergence (bar delta < 0 on new high) PRIMARY | 99 | -37.7 | -6.9 | -3.5 | -48.1 | +51.6 | -99.7 |
| 1 nearby: delta < -10% vol | 9 | -4.0 | -0.5 | +0.0 | -4.5 | +5.5 | -10.0 |
| 1 nearby: delta < +10% vol | 255 | -88.3 | -28.7 | -10.2 | -127.2 | +114.0 | -241.2 |
| 2 Absorption at high (top share >= 40%, close lower half) PRIMARY | 6 | -2.9 | -2.2 | +0.6 | -4.5 | +0.8 | -5.3 |
| 2 nearby: 35% | 11 | -7.3 | -4.4 | -1.0 | -12.7 | +0.8 | -13.4 |
| 2 nearby: 45% | 3 | +0.8 | -2.2 | +0.6 | -0.9 | +0.8 | -1.6 |
| 3 Stacked sell imbalances (>=3 levels, 3x) PRIMARY | 14 | +1.8 | -0.7 | +2.1 | +3.3 | +9.1 | -5.8 |
| 3 nearby: 2 levels | 45 | -2.5 | -0.8 | +1.4 | -2.0 | +23.5 | -25.5 |
| 3 nearby: 4 levels | 2 | +0.0 | +1.8 | -1.2 | +0.6 | +1.8 | -1.2 |
| 3 nearby: ratio 2.5x | 21 | +1.8 | +2.4 | -0.6 | +3.7 | +14.5 | -10.8 |
| 3 nearby: ratio 4x | 5 | +0.0 | +1.0 | -0.4 | +0.6 | +1.8 | -1.2 |
| 4 Delta not confirming (CVD since entry <= 0) PRIMARY | 153 | -11.2 | +7.9 | +0.6 | -2.7 | +108.5 | -111.2 |
| 4 nearby: CVD <= -5% vol | 32 | +2.1 | +3.5 | +1.2 | +6.7 | +29.9 | -23.1 |
| 4 nearby: CVD <= +5% vol | 315 | -69.4 | -25.0 | -4.7 | -99.1 | +159.4 | -258.5 |
| 5 Stretched above value (> 1.0R over VAH) PRIMARY | 16 | -12.4 | -2.2 | -1.6 | -16.2 | +4.5 | -20.7 |
| 5 nearby: 0.5R | 67 | -37.9 | -22.6 | -5.4 | -65.9 | +12.7 | -78.6 |
| 5 nearby: 1.5R | 7 | -13.2 | -2.2 | +0.0 | -15.4 | +0.0 | -15.4 |

6) Smart-exit model with order flow (decision points with data: train 168, test 187)

| Model | 2016-20 (train) | 2021-24 | 2025-26 | closed early (test) |
|---|---|---|---|---|
| smart exit (price only) | +10.5 | +11.2 | +0.3 | 12% |
| smart exit + order flow | +35.0 | +17.9 | +3.5 | 38% |

Month-block bootstrap, 2021-26, chance the primary rule's gain is really <= 0:
- 1 Delta divergence (bar delta < 0 on new high): gain -10.4R, p = 0.86
- 2 Absorption at high (top share >= 40%, close lower half): gain -1.6R, p = 0.76
- 3 Stacked sell imbalances (>=3 levels, 3x): gain +1.4R, p = 0.40
- 4 Delta not confirming (CVD since entry <= 0): gain +8.6R, p = 0.23
- 5 Stretched above value (> 1.0R over VAH): gain -3.8R, p = 1.00
