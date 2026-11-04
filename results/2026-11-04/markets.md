# Strategy lab: other markets

13 markets x 10 strategies = 130 combinations, daily data, long-or-cash, judged on 2016 onwards. Deflated Sharpe corrected for all 130 combinations.

**Survivors: none**

## Best strategy per market (by deflated Sharpe) vs buy & hold

| Market | Best strategy | OOS return/yr | OOS max DD | Buy & hold return/yr | B&H max DD | Beats B&H Sharpe | Deflated Sharpe | Failed checks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GOLD | turn_of_month | 8.4% | -8.2% | 13.1% | -26.7% | yes | 62.3% | - |
| BITCOIN | faber | 70.5% | -72.7% | 61.9% | -83.4% | yes | 60.3% | - |
| SP500 | trend | 10.6% | -16.5% | 13.2% | -33.9% | yes | 45.4% | - |
| NASDAQ100 | trend_voltarget | 7.4% | -13.2% | 18.6% | -35.6% | no | 38.5% | - |
| ETHEREUM | trend_voltarget | 10.4% | -12.1% | 26.2% | -94.0% | yes | 24.1% | - |
| NIKKEI | sma_cross | 9.7% | -35.0% | 12.0% | -31.8% | no | 14.6% | beats_bh_on_risk_or_return |
| USDJPY | options_expiry_week | 2.3% | -7.5% | 2.6% | -17.7% | yes | 8.3% | - |
| DAX | faber | 5.7% | -21.3% | 8.9% | -38.8% | no | 6.6% | - |
| SILVER | turn_of_month | 5.7% | -27.6% | 13.1% | -57.3% | no | 4.3% | - |
| FTSE100 | faber | 3.4% | -20.9% | 5.5% | -36.6% | no | 2.6% | - |
| EURUSD | faber | 0.4% | -11.9% | 0.3% | -23.3% | yes | 0.2% | - |
| AUDUSD | turn_of_month | 0.1% | -13.1% | -0.3% | -29.3% | yes | 0.1% | survives_2x_costs, stable_to_param_nudge |
| GBPUSD | tsmom | -0.0% | -13.3% | -0.8% | -27.5% | yes | 0.1% | oos_positive, survives_2x_costs, stable_to_param_nudge |

## Top 15 combinations overall

| Market | Strategy | OOS return/yr | OOS Sharpe | OOS max DD | Deflated Sharpe | Orders/yr | Skeptic |
| --- | --- | --- | --- | --- | --- | --- | --- |
| GOLD | turn_of_month | 8.4% | 1.05 | -8.2% | 62.3% | 24 | PASS |
| BITCOIN | faber | 70.5% | 1.02 | -72.7% | 60.3% | 1 | PASS |
| BITCOIN | tsmom | 69.2% | 1.01 | -69.8% | 57.5% | 1 | PASS |
| BITCOIN | trend_voltarget | 13.7% | 0.96 | -19.2% | 50.1% | 32 | PASS |
| SP500 | trend | 10.6% | 0.92 | -16.5% | 45.4% | 3 | PASS |
| BITCOIN | trend | 55.1% | 0.90 | -69.9% | 40.7% | 3 | PASS |
| BITCOIN | sma_cross | 54.9% | 0.89 | -67.7% | 38.7% | 2 | PASS |
| NASDAQ100 | trend_voltarget | 7.4% | 0.87 | -13.2% | 38.5% | 40 | PASS |
| NASDAQ100 | trend | 14.1% | 0.84 | -27.8% | 35.7% | 3 | PASS |
| SP500 | trend_voltarget | 6.9% | 0.83 | -10.9% | 34.1% | 35 | PASS |
| NASDAQ100 | tsmom | 15.6% | 0.81 | -28.0% | 31.8% | 1 | PASS |
| NASDAQ100 | faber | 13.4% | 0.78 | -28.0% | 28.4% | 2 | PASS |
| ETHEREUM | trend_voltarget | 10.4% | 0.78 | -12.1% | 24.1% | 26 | PASS |
| NASDAQ100 | sma_cross | 13.1% | 0.73 | -28.0% | 22.5% | 1 | PASS |
| BITCOIN | calendar_composite | 26.1% | 0.72 | -48.3% | 17.2% | 31 | PASS |

Notes: EURUSD: FX, long side only; GBPUSD: FX, long side only; USDJPY: FX, long side only; AUDUSD: FX, long side only; GOLD: continuous futures; small roll effects; SILVER: continuous futures; small roll effects; SP500: index level, excludes dividends; NASDAQ100: index level, excludes dividends; DAX: total-return index; FTSE100: index level, excludes dividends; NIKKEI: index level, excludes dividends; BITCOIN: from 2014, trades 7 days a week; ETHEREUM: from 2017, trades 7 days a week.
