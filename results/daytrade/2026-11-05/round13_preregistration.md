# Round 13: five simple add-on strategies (written 2026-11-05 15:25, before running)

All rules are textbook and fixed; no parameters are fitted. Data: HistData 1-minute (WTI, XAGUSD, AUDJPY, NZDJPY, S&P 500, DAX, gold); TradingView calendar.

| # | Strategy | Rule | Costs |
|---|---|---|---|
| 1 | **Oil inventory surprise** | US "EIA Crude Oil Stocks Change": z = (actual - forecast) / std of past surprises (at least 10). If abs(z) > 0.5: **long WTI if stocks fell more than expected** (z < 0), short if they rose more; enter 5 min after the release, close after 60 min | 3 bps/side |
| 2 | **Pre-Fed drift** | Long S&P 500 from 14:00 New York the day before each FOMC decision to 13:55 on decision day (Lucca & Moench 2015) | 1 bp/side + 5%/yr financing |
| 3 | **Deep-dip buying** | S&P 500 and DAX daily: close above its 200-day average and RSI(2) < 5: buy at the next open; sell at the first close above the 5-day average, or after 10 days | 1 bp/side + 5%/yr financing |
| 4 | **Carry with trend** | AUDJPY and NZDJPY daily: long while the previous close is above its 200-day average; assumed net carry credit +1%/yr while long | 1 bp/side |
| 5 | **Gold/silver ratio** | Ratio XAU/XAG, 120-day z-score: z > 2 means long silver and short gold (equal dollars); z < -2 the opposite; exit when abs(z) < 0.5 | 2 bps/side per leg + 2%/yr swap per leg |

## Keep rule (decided now)
A strategy joins the plan only if its Sharpe is at least 0.3 in 2016-2020 **and** above 0 in 2021-2024. 2025-26 is then reported as a fresh check.

## Combining
Each kept strategy is scaled to the same risk (3% annual volatility on the account, measured on 2016-2020 only), added to the 3-strategy plan (plan x1.5 + gold 0.75x), and run through the FTMO simulation (-10% / -5% limits, -2% daily stop, half size below -5%, 80% split).

**Data note (before any results):** HistData has no WTI after 2023, so strategy 1 uses **Brent (BCOUSD)**, which reacts to the same US inventory report.
