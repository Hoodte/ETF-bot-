# Strategy discovery

14 pre-registered candidates. Out-of-sample period judged only. Buy & hold OOS: CAGR 11.4%, max drawdown -15.0%.

**Survivors: none**

| Strategy | Survivor | OOS CAGR | OOS Sharpe | Beats B&H Sharpe | OOS max DD | 2008 return | Deflated Sharpe | Losing year odds | Orders/yr | Failed checks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| inverse_vol | no | 10.3% | 1.20 | yes | -13.2% | 1.6% | 63.5% | 15.1% | 59 | - |
| faber | no | 8.5% | 1.11 | no | -8.5% | -3.7% | 52.1% | 19.7% | 23 | - |
| trend_inverse_vol | no | 7.0% | 1.08 | no | -9.5% | -1.1% | 47.8% | 22.6% | 190 | - |
| tsmom | no | 8.8% | 1.04 | no | -11.6% | 6.5% | 42.1% | 18.4% | 14 | - |
| trend | no | 7.5% | 1.01 | no | -11.2% | -4.5% | 38.5% | 24.2% | 57 | - |
| trend_voltarget | no | 6.8% | 0.97 | no | -11.2% | -3.9% | 33.7% | 25.2% | 121 | - |
| dual_momentum | no | 10.2% | 0.95 | no | -14.6% | 9.5% | 31.9% | 20.4% | 11 | - |
| sma_cross | no | 7.3% | 0.90 | no | -14.5% | 2.4% | 26.8% | 21.6% | 22 | - |
| rotation | no | 8.7% | 0.90 | no | -12.5% | 1.3% | 26.3% | 23.0% | 50 | - |
| turn_of_month | no | 2.9% | 0.65 | no | -8.1% | -14.8% | 7.3% | 36.2% | 121 | - |
| rsi2 | no | 0.1% | 0.05 | no | -8.1% | 4.1% | 0.0% | 42.4% | 94 | survives_2x_costs |
| calendar_composite | no | -0.3% | -0.02 | no | -20.0% | 1.9% | 0.0% | 48.3% | 231 | oos_positive, beats_bh_on_risk_or_return, survives_2x_costs, stable_to_param_nudge |
| options_expiry_week | no | -1.8% | -0.39 | no | -24.6% | 5.4% | 0.0% | 59.8% | 120 | oos_positive, beats_bh_on_risk_or_return, survives_2x_costs, stable_to_param_nudge |
| pre_holiday | no | -1.3% | -0.76 | no | -14.0% | 4.6% | 0.0% | 71.4% | 91 | oos_positive, survives_2x_costs, stable_to_param_nudge |

Deflated Sharpe = probability the out-of-sample Sharpe is genuine after correcting for the number of strategies tried. Survivors need every Skeptic check plus a deflated Sharpe of at least the configured minimum.

Next for any survivor: `simulate`, `crosscheck`, and the backtest-expert command in `reports/discovery.json`. Then paper trade it.
