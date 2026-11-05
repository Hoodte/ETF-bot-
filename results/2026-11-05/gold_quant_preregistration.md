# Gold quant strategy search: pre-registration (written before any test, 5 Nov 2026 07:30)

**Instrument:** XAUUSD, Dukascopy hourly bars, Jan 2016 to Oct 2026. Every strategy produces an hourly position of +1 (long), 0 (flat) or −1 (short).

**Judging:** in-sample Jan 2016 to Dec 2021, out-of-sample Jan 2022 to Oct 2026. Costs are 3 basis points per side on every position change, with a stress test at 2×.

**Survivor rule:**
- out-of-sample return > 0
- still > 0 at 2× costs
- still > 0 with the main parameter moved ±20%
- deflated Sharpe ≥ 95%, corrected for all 14 strategies

**No look-ahead:**
- Daily signals (from Yahoo daily closes on date d) apply from 00:00 UTC on d+1, after every US close.
- CFTC positioning (as of Tuesday t, published Friday) applies from 00:00 UTC Monday t+6.

## Macro and cross-asset (daily signals)

1. **dollar_regime**: long when the US dollar index (DXY) is below its 50-day average, flat otherwise.
2. **real_yield_momentum**: long when the TIPS ETF (TIP, inverse of real yields) is up over 20 days, flat otherwise.
3. **nominal_yield_momentum**: long when the US 10-year yield (^TNX) is down over 20 days, flat otherwise.
4. **miners_lead**: long when gold miners (GDX) beat gold over the last 5 days, short when they lag.
5. **fear_spike**: long for 10 trading days after VIX closes more than 20% above its 60-day average.
6. **cot_contrarian**: long when managed-money net positioning (as % of open interest) is in the bottom 30% of its 3-year range; short in the top 10%; flat otherwise.
7. **cot_momentum**: long when managed-money net positioning rose over the last 4 reports, flat otherwise.
8. **macro_composite**: long when at least 2 of these hold (DXY below its 50-day average, TIP up over 20 days, COT percentile below 70%), flat otherwise.

## Seasonality and microstructure (hourly; patterns chosen from in-sample data only)

9. **hour_of_day**: from in-sample data, find UTC hours whose average return has t > 2 (long) or t < −2 (short). Trade only those hours out-of-sample.
10. **asia_session_long**: long from 23:00 to 07:00 UTC, flat otherwise.
11. **us_session_short**: short from 13:00 to 20:00 UTC, flat otherwise.
12. **month_of_year**: from in-sample data, be long in calendar months with a positive average daily return, flat otherwise.
13. **day_of_week**: from in-sample data, be long on weekdays with a positive average return, flat otherwise.

## Volatility structure (hourly)

14. **squeeze_breakout**: when 20-hour ATR is in the bottom 10% of its last 500 hours, wait for the price to break the prior 24-hour high or low. Trade in the direction of the break and hold for 24 hours.

**Main parameter nudged ±20%:**

| Strategy | Parameter |
| --- | --- |
| dollar_regime | 50-day average |
| real_yield_momentum, nominal_yield_momentum | 20-day lookback |
| miners_lead | 5-day window |
| fear_spike | 60-day average |
| cot_contrarian | 3-year window |
| cot_momentum | 4 reports |
| macro_composite | 50-day average |
| hour_of_day | t-stat threshold 2 |
| asia_session_long | 7:00 end hour → 6:00 / 8:00 |
| us_session_short | 13:00 start → 12:00 / 14:00 |
| month_of_year, day_of_week | in-sample start year moved one year |
| squeeze_breakout | 10% percentile |
