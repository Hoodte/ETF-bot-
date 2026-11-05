# Round 12: extending the two-strategy plan (written 2026-11-05 13:10, before running)

1. **News rule on other countries, frozen** (follow, +5 min, hold 60 min, |z| > 0.5; same z method, costs and sign rule as round 10b). TradingView high-importance releases from GB to GBPUSD, EU and DE to EURUSD, AU to AUDUSD, JP to USDJPY (JPY good means USDJPY down). Keep if Sharpe is above 0.5 in 2021-24 and above 0 in 2025-26 (all countries combined).
2. **Nasdaq lunch-RSI rule on the S&P 500, frozen** (RSI > 70 during the NY lunch session, long, 1 ATR stop, 3 ATR target). Keep if positive in both 2021-24 and 2025-26.
3. **Per-release sizing:** each release's total risk is split equally across the instruments it trades (in place of full size per instrument). Fixed rule, no tuning.
4. **FTMO-safe risk rules:** (a) daily loss capped at -2% of the account (approximated at daily level); (b) half size while the account is more than 5% below its start.
5. **Costs:** the effect of 0.5 bps per side lower or higher news costs.
Final: combined account simulation (FTMO $100k, -10%/-5% limits, 80% split), 2021-24 and 2025-26 reported separately.
