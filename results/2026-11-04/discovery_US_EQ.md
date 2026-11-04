# Strategy discovery

10 pre-registered candidates. Out-of-sample period judged only. Buy & hold OOS: CAGR 15.7%, max drawdown -26.1%.

**Survivors: none**

| Strategy | Survivor | OOS CAGR | OOS Sharpe | Beats B&H Sharpe | OOS max DD | 2008 return | Deflated Sharpe | Losing year odds | Orders/yr | Failed checks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| tsmom | no | 14.2% | 0.87 | no | -26.1% | -5.6% | 48.9% | 20.4% | 1 | beats_bh_on_risk_or_return |
| faber | no | 11.6% | 0.82 | no | -19.6% | -23.2% | 42.7% | 25.5% | 2 | - |
| trend_voltarget | no | 6.2% | 0.74 | no | -12.0% | -22.6% | 33.3% | 29.9% | 41 | - |
| trend | no | 9.8% | 0.73 | no | -24.6% | -26.9% | 31.6% | 30.0% | 4 | - |
| sma_cross | no | 9.1% | 0.62 | no | -26.1% | -5.9% | 20.2% | 27.8% | 1 | beats_bh_on_risk_or_return |
| turn_of_month | no | 1.8% | 0.25 | no | -15.4% | -17.9% | 2.1% | 43.4% | 24 | survives_2x_costs |
| rsi2 | no | 0.6% | 0.12 | no | -13.9% | 2.8% | 0.6% | 40.4% | 16 | survives_2x_costs |
| calendar_composite | no | -2.0% | -0.13 | no | -33.9% | -1.9% | 0.0% | 54.9% | 41 | oos_positive, beats_bh_on_risk_or_return, survives_2x_costs, stable_to_param_nudge |
| options_expiry_week | no | -2.5% | -0.25 | no | -31.4% | 0.2% | 0.0% | 56.8% | 24 | oos_positive, beats_bh_on_risk_or_return, survives_2x_costs, stable_to_param_nudge |
| pre_holiday | no | -2.1% | -0.79 | no | -21.1% | 5.6% | 0.0% | 72.1% | 18 | oos_positive, survives_2x_costs, stable_to_param_nudge |

Deflated Sharpe = probability the out-of-sample Sharpe is genuine after correcting for the number of strategies tried. Survivors need every Skeptic check plus a deflated Sharpe of at least the configured minimum.

Next for any survivor: `simulate`, `crosscheck`, and the backtest-expert command in `reports/discovery.json`. Then paper trade it.
