# Strategy lab: crypto (incl. smaller coins)

11 markets x 10 strategies = 110 combinations, daily data, long-or-cash, judged on 2022 onwards. Deflated Sharpe corrected for all 110 combinations.

**Survivors: none**

## Best strategy per market (by deflated Sharpe) vs buy & hold

| Market | Best strategy | OOS return/yr | OOS max DD | Buy & hold return/yr | B&H max DD | Beats B&H Sharpe | Deflated Sharpe | Failed checks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| BITCOIN | faber | 31.6% | -32.5% | 11.4% | -66.9% | yes | 57.6% | - |
| ETHEREUM | rsi2 | 13.2% | -18.7% | -8.7% | -74.1% | yes | 47.7% | - |
| SOLANA | trend_voltarget | 5.4% | -15.8% | -12.1% | -94.6% | yes | 27.0% | - |
| SHIBA | turn_of_month | 19.2% | -39.2% | -33.4% | -88.9% | yes | 25.3% | stable_to_param_nudge |
| AVALANCHE | trend_voltarget | 7.7% | -15.6% | -41.2% | -94.8% | yes | 22.8% | - |
| DOGECOIN | tsmom | 10.3% | -69.6% | -15.3% | -85.2% | yes | 19.8% | stable_to_param_nudge |
| LITECOIN | calendar_composite | 9.2% | -35.8% | -18.4% | -73.1% | yes | 17.7% | - |
| CARDANO | turn_of_month | 14.6% | -37.4% | -33.0% | -91.0% | yes | 17.6% | stable_to_param_nudge |
| XRP | trend_voltarget | 4.3% | -17.9% | 9.3% | -72.1% | no | 13.0% | - |
| CHAINLINK | faber | 1.0% | -51.3% | -11.4% | -81.6% | no | 10.4% | stable_to_param_nudge |
| POLKADOT | rsi2 | 1.3% | -23.5% | -50.5% | -97.5% | yes | 6.7% | survives_2x_costs, stable_to_param_nudge |

## Top 15 combinations overall

| Market | Strategy | OOS return/yr | OOS Sharpe | OOS max DD | Deflated Sharpe | Orders/yr | Skeptic |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BITCOIN | faber | 31.6% | 0.77 | -32.5% | 57.6% | 1 | PASS |
| BITCOIN | trend_voltarget | 9.0% | 0.72 | -13.5% | 52.1% | 32 | PASS |
| BITCOIN | tsmom | 28.2% | 0.71 | -32.2% | 50.7% | 1 | PASS |
| ETHEREUM | rsi2 | 13.2% | 0.68 | -18.7% | 47.7% | 15 | PASS |
| BITCOIN | trend | 20.7% | 0.60 | -39.6% | 39.1% | 3 | PASS |
| SOLANA | trend_voltarget | 5.4% | 0.47 | -15.8% | 27.0% | 26 | PASS |
| ETHEREUM | trend_voltarget | 6.1% | 0.49 | -9.4% | 26.9% | 26 | PASS |
| SHIBA | turn_of_month | 19.2% | 0.48 | -39.2% | 25.3% | 24 | FAIL |
| BITCOIN | sma_cross | 13.7% | 0.45 | -38.5% | 25.2% | 2 | PASS |
| AVALANCHE | trend_voltarget | 7.7% | 0.45 | -15.6% | 22.8% | 19 | PASS |
| DOGECOIN | tsmom | 10.3% | 0.39 | -69.6% | 19.8% | 2 | FAIL |
| SOLANA | trend | 8.8% | 0.36 | -69.2% | 17.8% | 3 | PASS |
| SHIBA | calendar_composite | 12.9% | 0.39 | -48.9% | 17.8% | 16 | PASS |
| SOLANA | faber | 8.4% | 0.35 | -70.1% | 17.7% | 1 | PASS |
| LITECOIN | calendar_composite | 9.2% | 0.36 | -35.8% | 17.7% | 24 | PASS |

Notes: EURUSD: FX, long side only; GBPUSD: FX, long side only; USDJPY: FX, long side only; AUDUSD: FX, long side only; GOLD: continuous futures; small roll effects; SILVER: continuous futures; small roll effects; SP500: index level, excludes dividends; NASDAQ100: index level, excludes dividends; DAX: total-return index; FTSE100: index level, excludes dividends; NIKKEI: index level, excludes dividends; BITCOIN: crypto, survivors only; ETHEREUM: crypto, survivors only; SOLANA: crypto, survivors only; XRP: crypto, survivors only; DOGECOIN: crypto, survivors only; CARDANO: crypto, survivors only; AVALANCHE: crypto, survivors only; CHAINLINK: crypto, survivors only; POLKADOT: crypto, survivors only; LITECOIN: crypto, survivors only; SHIBA: crypto, survivors only.

Costs: 30 bps per side for smaller coins, 10 bps for BTC/ETH. Survivorship bias: only coins still trading today are included, so results are flattered.
