# First real-data backtest, 4 Nov 2026

Data: Yahoo Finance daily prices to 4 Nov 2026. US proxies (SPY, EFA, AGG, GLD, EEM) from 2004, UK UCITS funds from the date their Yahoo data becomes reliable (see `check-data` cleaning notes), all in GBP. Out-of-sample = 2016 onwards. Costs: 10 bps per side.

- `discovery.md`: all 14 strategies on the 5-ETF portfolio. No survivors.
- `discovery_US_EQ.md`: the 10 single-ETF strategies on CSPX. No survivors.
- `combine_US_EQ.html`: interactive chart, auto-picked blend (tsmom, sma_cross, faber) vs buy & hold on CSPX.
- `timemachine_*.md`: 10,000 simulated years for the two leading portfolio strategies.
- `leverage.md`: 1x/2x/3x leveraged versions with real borrowing costs, plus 10-year projections with £200/month added.
- `backtest_expert_faber.md`: second opinion from the backtest-expert skill.

Engine check: vectorbt reproduced our results within 0.04% for inverse_vol, faber and trend.
- `markets.md`: all single-ETF strategies on 13 other markets (FX, metals, indices, crypto).
- `intraday.md`: 46 intraday long/short combinations on hourly data (about 2.5 years).
- `crypto.md`: 11 cryptocurrencies incl. smaller coins, judged on 2022 onwards (survivorship-biased).
