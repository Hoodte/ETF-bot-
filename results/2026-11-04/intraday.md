# Intraday strategy lab (hourly bars, long and short)

46 market x strategy combinations on Yahoo hourly data (about the last 2.5 years). Out-of-sample = the last 40% of bars. Deflated Sharpe corrected for all combinations. Short history: a first screen, not proof.

**Survivors: none**

| Market | Strategy | OOS return/yr | OOS Sharpe | OOS max DD | Same with 2x costs | Market itself (OOS) | Trades/day | Deflated Sharpe | Failed checks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| GOLD | donchian | 26.6% | 0.97 | -16.6% | 18.1% | 0.9% | 0.48 | 13.4% | - |
| SP500 | overnight | 7.2% | 0.71 | -9.7% | -0.6% | 16.6% | 1.37 | 8.8% | survives_2x_costs |
| NASDAQ100 | overnight | 7.2% | 0.52 | -11.3% | -0.6% | 16.4% | 1.37 | 6.2% | survives_2x_costs |
| GOLD | overnight | 4.9% | 0.32 | -22.7% | -5.1% | 0.9% | 1.38 | 4.2% | survives_2x_costs |
| DAX | bollinger_fade | -4.1% | -0.33 | -11.8% | -7.4% | 10.0% | 0.45 | 3.8% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| EURUSD | rsi2_both | 0.8% | 0.32 | -2.3% | -4.8% | -3.9% | 1.54 | 2.5% | survives_2x_costs, stable_to_param_nudge |
| GOLD | rsi2_both | -0.3% | 0.04 | -15.1% | -10.1% | 0.9% | 1.32 | 2.2% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| DAX | overnight | -7.8% | -0.58 | -13.3% | -16.7% | 10.0% | 1.39 | 2.1% | oos_positive, survives_2x_costs |
| DAX | ema_cross | -11.5% | -0.66 | -25.1% | -13.6% | 10.0% | 0.17 | 1.8% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| GOLD | ema_cross | -7.6% | -0.13 | -27.1% | -12.9% | 0.9% | 0.38 | 1.5% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| SP500 | bollinger_fade | -1.7% | -0.15 | -6.9% | -8.8% | 16.6% | 1.34 | 1.4% | oos_positive, survives_2x_costs |
| DAX | rsi2_both | -4.6% | -0.72 | -9.3% | -8.4% | 10.0% | 0.52 | 1.3% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| DAX | orb | -7.3% | -0.85 | -14.0% | -15.6% | 10.0% | 1.25 | 1.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| GOLD | bollinger_fade | -7.4% | -0.28 | -18.4% | -15.3% | 0.9% | 1.26 | 1.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| BITCOIN | donchian | -10.6% | -0.05 | -27.7% | -43.6% | -19.2% | 0.79 | 0.9% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| DAX | session_momentum | -8.0% | -0.85 | -17.0% | -16.9% | 10.0% | 1.39 | 0.9% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| NASDAQ100 | ema_cross | -9.3% | -0.37 | -30.8% | -13.1% | 16.4% | 0.37 | 0.8% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| NASDAQ100 | bollinger_fade | -6.8% | -0.44 | -12.8% | -13.2% | 16.4% | 1.33 | 0.7% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| NASDAQ100 | donchian | -10.6% | -0.44 | -19.2% | -15.5% | 16.4% | 0.55 | 0.7% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| NASDAQ100 | orb | -5.1% | -0.51 | -9.6% | -11.0% | 16.4% | 1.19 | 0.6% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| BITCOIN | ema_cross | -27.5% | -0.54 | -41.5% | -48.8% | -19.2% | 0.6 | 0.3% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| SP500 | donchian | -12.1% | -0.83 | -14.3% | -16.8% | 16.6% | 0.53 | 0.2% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| EURUSD | bollinger_fade | -2.3% | -0.56 | -4.9% | -7.3% | -3.9% | 1.44 | 0.2% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| EURUSD | ema_cross | -4.5% | -0.78 | -9.3% | -7.3% | -3.9% | 0.41 | 0.1% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| BITCOIN | session_momentum | -27.9% | -0.94 | -38.8% | -59.9% | -19.2% | 2.0 | 0.1% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| SP500 | rsi2_both | -6.6% | -1.15 | -8.2% | -12.8% | 16.6% | 1.35 | 0.1% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| DAX | donchian | -25.3% | -1.68 | -30.8% | -27.7% | 10.0% | 0.21 | 0.1% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| GBPUSD | donchian | -6.1% | -0.95 | -10.4% | -11.4% | 0.0% | 0.58 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| NASDAQ100 | rsi2_both | -11.4% | -1.36 | -14.4% | -17.2% | 16.4% | 1.31 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| GBPUSD | rsi2_both | -2.9% | -1.04 | -3.9% | -10.3% | 0.0% | 1.41 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| BITCOIN | orb | -33.1% | -1.20 | -33.5% | -62.8% | -19.2% | 1.99 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| GOLD | session_momentum | -13.0% | -1.33 | -13.0% | -21.3% | 0.9% | 1.38 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| SP500 | orb | -10.8% | -1.61 | -11.9% | -16.7% | 16.6% | 1.28 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| SP500 | ema_cross | -21.4% | -1.61 | -22.5% | -24.8% | 16.6% | 0.38 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| GBPUSD | ema_cross | -8.3% | -1.33 | -11.6% | -12.7% | 0.0% | 0.43 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| GBPUSD | bollinger_fade | -6.1% | -1.36 | -8.2% | -13.2% | 0.0% | 1.42 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| GOLD | orb | -15.3% | -1.73 | -15.8% | -21.9% | 0.9% | 1.1 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| EURUSD | session_momentum | -5.1% | -1.44 | -6.7% | -9.6% | -3.9% | 1.35 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| EURUSD | orb | -5.6% | -1.63 | -7.6% | -10.3% | -3.9% | 1.39 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| EURUSD | donchian | -9.4% | -1.70 | -12.7% | -13.1% | -3.9% | 0.58 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| BITCOIN | rsi2_both | -33.3% | -2.41 | -31.7% | -64.3% | -19.2% | 2.04 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| GBPUSD | orb | -8.1% | -2.02 | -9.9% | -14.9% | 0.0% | 1.4 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| GBPUSD | session_momentum | -8.6% | -2.10 | -10.0% | -15.4% | 0.0% | 1.41 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| BITCOIN | bollinger_fade | -59.2% | -2.79 | -55.0% | -76.7% | -19.2% | 1.91 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| NASDAQ100 | session_momentum | -24.4% | -3.00 | -27.8% | -29.9% | 16.4% | 1.36 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |
| SP500 | session_momentum | -21.6% | -3.50 | -22.6% | -27.3% | 16.6% | 1.36 | 0.0% | oos_positive, survives_2x_costs, stable_to_param_nudge |

Costs per side: EURUSD 1.0 bps, GBPUSD 1.5 bps, GOLD 2.0 bps, NASDAQ100 1.5 bps, SP500 1.5 bps, DAX 2.0 bps, BITCOIN 8.0 bps.
