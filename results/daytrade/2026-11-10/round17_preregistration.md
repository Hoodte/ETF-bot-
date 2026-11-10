# Round 17: five new strategy types (written 2026-11-10 15:55, before running)
Higher bar because many ideas have now been tried: PASS = Sharpe >= 0.4 in 2016-20 AND >= 0.2 in 2021-24 AND > 0 in 2025-26,
AND most nearby settings (listed) also positive in all three periods.
1. Month-end FX flows: S&P month-to-date return vs DAX (to the close 3 trading days before month end). If S&P beat DAX,
   sell USD (long EURUSD, GBPUSD, AUDUSD; short USDJPY, USDCAD, equal weight) from 16:00 London 2 trading days before
   month end to 16:00 London on the last trading day; buy USD if it lagged. Nearby: 1 or 3 days. Cost 1 bp/side/leg.
2. Currency momentum basket: EUR, GBP, AUD, NZD (from NZDJPY/USDJPY), JPY, CAD and USD. Every Friday close rank by
   3-month return vs USD; long top 2, short bottom 2 for the next week. Nearby: 1 or 6 months; top/bottom 1. Cost 1 bp/side/leg.
   (No swap/carry included: limitation.)
3. Options-expiry week: long S&P 500 and Nasdaq 50/50 from the Friday close before the 3rd Friday of the month to the
   3rd-Friday close. Nearby: the same rule but enter Monday open. Cost 1 bp/side + 5%/yr financing.
4. Risk-off filter on the CURRENT plan parts (news bot trades, gold macro, Nasdaq lunch-RSI): skip/flatten when the previous
   day's VIX > 30. Nearby: 25, 35. Kept only if it improves Sharpe of the parts in 2016-20 and does not cut 2021-26 Sharpe.
5. Quarter-end rebalancing: S&P quarter-to-date vs IEF (Treasury ETF) at the close 6 trading days before quarter end.
   If S&P beat bonds by > 0, short S&P over the last 5 trading days; else long. Nearby: last 3 or 7 days. Cost 1 bp/side + financing.
