# Intraday strategy search: report

Attempted 4987 configs: **4659 tested**, 242 invalid, 86 duplicates. Search data ends 2024-12-31; the holdout from 2025-01-01 was untouched until the shortlist was frozen.
Pass rule: Sharpe of at least 0.5 and profit factor of at least 1.05 net of costs, in discovery (to 2020) and in both validation folds (2021-22, 2023-24), with at least 5.0 trades a week.
Costs per side: XAUUSD_1h 3.0 bps, BTCUSDT_1h 5.0 bps, BTCUSDT_15m 5.0 bps, BTCUSDT_5m 5.0 bps, ETHUSDT_1h 5.0 bps, ETHUSDT_15m 5.0 bps, ETHUSDT_5m 5.0 bps. Entries at the next bar's open; stops/targets from the signal bar; stop assumed first if both are hit in one bar.

## Pass rate by dataset and family

| Dataset | Family | Tested | Pass | Best worst-period Sharpe | Median search Sharpe |
|---|---|---|---|---|---|
| BTCUSDT_15m | band_fade | 139 | 0 | 0.00 | -1.54 |
| BTCUSDT_15m | breakout | 136 | 0 | 0.43 | -1.47 |
| BTCUSDT_15m | momentum | 158 | 0 | 1.16 | -1.36 |
| BTCUSDT_15m | orb | 143 | 0 | -0.13 | -2.04 |
| BTCUSDT_15m | rsi_revert | 135 | 0 | 0.00 | -1.77 |
| BTCUSDT_1h | band_fade | 133 | 0 | 0.13 | -1.09 |
| BTCUSDT_1h | breakout | 126 | 0 | 0.10 | -0.50 |
| BTCUSDT_1h | momentum | 149 | 0 | 0.51 | -0.20 |
| BTCUSDT_1h | orb | 88 | 0 | -0.17 | -1.11 |
| BTCUSDT_1h | rsi_revert | 144 | 0 | 0.00 | -1.16 |
| BTCUSDT_5m | band_fade | 125 | 0 | -0.24 | -3.87 |
| BTCUSDT_5m | breakout | 160 | 0 | 0.00 | -4.80 |
| BTCUSDT_5m | momentum | 156 | 0 | 0.40 | -2.81 |
| BTCUSDT_5m | orb | 136 | 0 | -0.60 | -3.09 |
| BTCUSDT_5m | rsi_revert | 141 | 0 | 0.00 | -4.99 |
| ETHUSDT_15m | band_fade | 127 | 0 | 0.71 | -1.82 |
| ETHUSDT_15m | breakout | 137 | 0 | 0.00 | -1.47 |
| ETHUSDT_15m | momentum | 145 | 0 | 0.74 | -0.89 |
| ETHUSDT_15m | orb | 132 | 0 | 0.38 | -1.14 |
| ETHUSDT_15m | rsi_revert | 141 | 0 | 0.00 | -1.40 |
| ETHUSDT_1h | band_fade | 132 | 0 | -0.17 | -1.18 |
| ETHUSDT_1h | breakout | 152 | 0 | 0.49 | -0.21 |
| ETHUSDT_1h | momentum | 143 | 0 | 1.03 | -0.02 |
| ETHUSDT_1h | orb | 76 | 0 | 0.25 | -0.61 |
| ETHUSDT_1h | rsi_revert | 155 | 0 | 0.34 | -0.86 |
| ETHUSDT_5m | band_fade | 133 | 0 | 0.53 | -3.20 |
| ETHUSDT_5m | breakout | 128 | 0 | -0.54 | -4.31 |
| ETHUSDT_5m | momentum | 141 | 0 | 0.00 | -3.45 |
| ETHUSDT_5m | orb | 139 | 0 | -0.06 | -1.97 |
| ETHUSDT_5m | rsi_revert | 131 | 0 | 0.23 | -3.55 |
| XAUUSD_1h | band_fade | 131 | 0 | 0.45 | -0.76 |
| XAUUSD_1h | breakout | 124 | 0 | 0.02 | -0.84 |
| XAUUSD_1h | momentum | 128 | 0 | 0.25 | -0.66 |
| XAUUSD_1h | orb | 54 | 0 | 0.22 | -1.34 |
| XAUUSD_1h | rsi_revert | 141 | 0 | 0.71 | -1.31 |

## Verdict

No configuration passed the pre-registered rule in every period.

Funded sim: closed-trade daily P&L, -10% max loss, -5% daily loss, 80% split, 10,000 bootstrapped years; the size shown is the largest that keeps the account in 85% or more of years. Intraday open losses are not modelled, so the real daily-loss risk is higher.
