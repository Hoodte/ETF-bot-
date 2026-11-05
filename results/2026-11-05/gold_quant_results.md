# Gold quant strategy search: results

14 strategies pre-registered in `gold_quant_preregistration.md`. XAUUSD hourly, Dukascopy, 2016–2026. In-sample 2016–2021, out-of-sample 2022–Oct 2026. Costs 3 bps per side.

Holding gold: in-sample 9.5%/yr (max drop -18.9%), out-of-sample 16.8%/yr (max drop -30.3%, Sharpe 0.93).

**Survivors: none**

| Strategy | In-sample /yr | OOS /yr | OOS Sharpe | OOS max drop | OOS at 2× costs | Nudged ±20% (OOS) | Time in market | Trades/yr | Deflated Sharpe | Failed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| squeeze_breakout | -3.3% | 7.4% | 1.19 | -8.2% | 5.1% | 5.9% / 6.2% | 15.1% | 69 | 0.5% | - |
| dollar_regime | 0.1% | 13.1% | 1.02 | -19.0% | 12.5% | 12.0% / 14.2% | 44.7% | 18 | 0.2% | - |
| day_of_week | 9.5% | 16.8% | 0.93 | -30.3% | 16.8% | 16.8% / 16.8% | 99.9% | 0 | 0.1% | - |
| macro_composite | 9.4% | 10.6% | 0.79 | -20.6% | 9.7% | 11.7% / 9.0% | 52.9% | 24 | 0.0% | - |
| real_yield_momentum | 9.4% | 8.3% | 0.65 | -27.1% | 7.5% | 11.3% / 8.1% | 53.3% | 25 | 0.0% | - |
| month_of_year | 15.9% | 9.5% | 0.65 | -20.0% | 9.3% | 9.5% / 10.7% | 75.8% | 6 | 0.0% | - |
| miners_lead | 0.4% | 10.6% | 0.64 | -29.3% | 7.2% | 14.9% / 12.2% | 99.9% | 57 | 0.0% | - |
| nominal_yield_momentum | 7.6% | 5.5% | 0.55 | -15.3% | 4.8% | 7.2% / 6.3% | 41.0% | 27 | 0.0% | - |
| cot_momentum | 2.2% | 5.0% | 0.47 | -28.9% | 4.7% | -3.2% / 4.2% | 45.9% | 12 | 0.0% | stable_to_nudge |
| fear_spike | 5.2% | 4.8% | 0.46 | -22.3% | 4.5% | 5.0% / 3.9% | 32.2% | 8 | 0.0% | - |
| cot_contrarian | 4.4% | -1.8% | -0.15 | -29.4% | -2.0% | -4.2% / -1.6% | 42.4% | 6 | 0.0% | oos_positive, survives_2x_costs, stable_to_nudge |
| asia_session_long | -5.3% | -4.2% | -0.38 | -27.5% | -18.0% | -7.1% / -3.5% | 39.2% | 518 | 0.0% | oos_positive, survives_2x_costs, stable_to_nudge |
| us_session_short | -14.1% | -12.3% | -1.04 | -55.9% | -24.9% | -13.0% / -14.4% | 34.8% | 518 | 0.0% | oos_positive, survives_2x_costs, stable_to_nudge |
| hour_of_day | -19.4% | -27.2% | -4.14 | -78.4% | -54.1% | -27.0% / -17.1% | 26.0% | 1286 | 0.0% | oos_positive, survives_2x_costs, stable_to_nudge |

## Risk-adjusted comparison with holding gold

| Strategy | In-sample Sharpe | Out-of-sample Sharpe | Chance its edge over zero is real | Chance it beats holding gold at equal risk |
| --- | --- | --- | --- | --- |
| Holding gold | 0.71 | 0.93 | — | — |
| macro_composite | 0.87 | 0.79 | 99.4% | 51% |
| real_yield_momentum | 0.84 | 0.65 | 99.0% | 36% |
| month_of_year | 1.32 (fitted) | 0.65 | 99.9% | 80% |
| nominal_yield_momentum | 0.74 | 0.55 | 98.2% | 26% |
| dollar_regime | 0.06 | 1.02 | 95.6% | 13% |
| squeeze_breakout | -0.61 | 1.19 | 80.5% | 10% |

The Bonferroni bar for 14 trials is 99.64%. The deflated Sharpe in the main table is very strict here, because the losing intraday strategies make the spread of Sharpes across trials (and so the luck bar) very large.

## Time Machine: macro_composite, one year ahead (10,000 paths)

Return: bad (5%) -8.5%, typical 8.3%, great (95%) 30.3%. Typical worst drop -8.4%, bad case -16.7%. Chance of a losing year 22%. Chance of beating holding gold 40%.

## Verdict

None of the 14 strategies adds an edge beyond simply holding gold. The macro strategies are genuinely profitable and consistent across both periods: macro_composite is long about half the time, with a smaller worst drop (−20.6% vs −30.3% out-of-sample). But that profit is gold's own long-run rise, timed. At equal risk they do not beat holding. Every intraday and seasonality idea lost money, mainly to trading costs (the hour-of-day pattern traded about 1,300 times a year).
