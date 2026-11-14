Model coefficients (standardised): {'vol_ratio': np.float64(-0.19), 'day_move': np.float64(-0.34), 'week_trend': np.float64(0.05), 'prev_day': np.float64(-0.13), 'rsi': np.float64(0.28), 'mins': np.float64(-0.12)}
  AUC predicting target-hit, 2016-20 (train): 0.615
  AUC predicting target-hit, 2021-24: 0.493
  AUC predicting target-hit, 2025-26: 0.665
  (0.5 = no better than a coin flip)

| Rule | 10-yr R | vs now | 16-20 (train) | 21-24 | 25-26 |
|---|---|---|---|---|---|
| Current exit | +122.6 | +0.0 | +0.0 | +0.0 | +0.0 |
| Trail on ALL trades (1.5R / 1R) | +98.6 | -24.0 | -26.5 | +4.4 | -2.0 |
| weak=40% , trail after 1.2R by 0.75R | +116.8 | -5.8 | -12.3 | +5.5 | +1.0 |
| weak=40% , trail after 1.2R by 1.0R | +121.6 | -0.9 | -10.5 | +7.1 | +2.5 |
| weak=40% , trail after 1.2R by 1.25R | +126.2 | +3.6 | -8.8 | +11.0 | +1.4 |
| weak=40% , trail after 1.5R by 0.75R | +119.1 | -3.5 | -12.8 | +7.6 | +1.7 |
| weak=40% , trail after 1.5R by 1.0R | +119.2 | -3.3 | -14.1 | +7.8 | +2.9 |
| weak=40% , trail after 1.5R by 1.25R | +124.5 | +1.9 | -12.2 | +8.7 | +5.5 |
| weak=40% , trail after 1.8R by 0.75R | +122.9 | +0.4 | -8.0 | +8.8 | -0.4 |
| weak=40% , trail after 1.8R by 1.0R | +123.7 | +1.2 | -7.3 | +7.7 | +0.8 |
| weak=40% , trail after 1.8R by 1.25R | +124.9 | +2.4 | -6.6 | +6.2 | +2.8 |
| weak=50% , trail after 1.2R by 0.75R | +119.0 | -3.6 | -11.1 | +4.6 | +3.0 |
| weak=50% , trail after 1.2R by 1.0R | +128.3 | +5.7 | -4.8 | +6.0 | +4.5 |
| weak=50% , trail after 1.2R by 1.25R | +135.0 | +12.5 | -2.7 | +10.3 | +4.8 |
| weak=50% , trail after 1.5R by 0.75R | +125.2 | +2.6 | -8.1 | +7.1 | +3.7 |
| **PRIMARY** weak=50% , trail after 1.5R by 1.0R | +126.5 | +3.9 | -8.4 | +7.4 | +4.9 |
| weak=50% , trail after 1.5R by 1.25R | +132.7 | +10.1 | -6.1 | +7.3 | +8.9 |
| weak=50% , trail after 1.8R by 0.75R | +128.2 | +5.6 | -4.1 | +9.1 | +0.7 |
| weak=50% , trail after 1.8R by 1.0R | +129.6 | +7.0 | -3.3 | +7.3 | +3.0 |
| weak=50% , trail after 1.8R by 1.25R | +130.9 | +8.3 | -1.9 | +5.4 | +4.8 |
| weak=60% , trail after 1.2R by 0.75R | +107.1 | -15.4 | -19.0 | +1.0 | +2.5 |
| weak=60% , trail after 1.2R by 1.0R | +120.8 | -1.8 | -9.7 | +2.8 | +5.2 |
| weak=60% , trail after 1.2R by 1.25R | +128.6 | +6.0 | -6.9 | +8.0 | +4.8 |
| weak=60% , trail after 1.5R by 0.75R | +112.2 | -10.4 | -15.1 | +3.3 | +1.5 |
| weak=60% , trail after 1.5R by 1.0R | +118.1 | -4.5 | -12.5 | +3.6 | +4.5 |
| weak=60% , trail after 1.5R by 1.25R | +126.6 | +4.0 | -8.2 | +3.9 | +8.3 |
| weak=60% , trail after 1.8R by 0.75R | +117.2 | -5.4 | -12.2 | +7.4 | -0.6 |
| weak=60% , trail after 1.8R by 1.0R | +122.7 | +0.1 | -8.3 | +5.9 | +2.5 |
| weak=60% , trail after 1.8R by 1.25R | +126.7 | +4.1 | -4.7 | +4.6 | +4.2 |

Primary rule 2021-26 vs current: +12.3R. Random-half control: mean +1.1R; share of random picks that do as well or better: 0.04
train: of trades reaching +1.5R, ended negative -> weak 17% (n=63), strong 12% (n=64)
2021-26: of trades reaching +1.5R, ended negative -> weak 21% (n=72), strong 12% (n=57)
