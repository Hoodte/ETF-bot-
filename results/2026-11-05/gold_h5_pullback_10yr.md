# backtest-bot H5 gold trend pullback: 10-year test

Strategy (frozen, from backtest-bot `scripts/run_h5_xauusd_h1_pullback.py`, originally tested on one year, May 2025 to May 2026): XAUUSD H1, close above/below EMA200, ADX > 25, pullback to EMA50 (ema_pullback block), candle body ≥ 50%, London+NY hours, stop 1.5×ATR, target 3×ATR, 1% risk per trade. Engine: backtest-bot (costs: 0.30 spread, 2/4 ticks slippage). Data: Dukascopy XAUUSD H1, Jan 2016 to Oct 2026 (64,074 bars).

## Long side: passes backtest-bot's robustness gates

| Window | Trades | Win % | Profit factor | Sharpe | Max DD |
| --- | --- | --- | --- | --- | --- |
| In-sample (first 60%) | 122 | 30.3 | 1.20 | 0.27 | 16.3% |
| Out-of-sample (next 20%) | 51 | 39.2 | 1.47 | 0.76 | 10.7% |
| Validation (last 20%) | 45 | 48.9 | 2.24 | 1.51 | 6.7% |
| Full | 218 | 36.2 | 1.49 | 0.55 | 16.3% |

Still profitable at 3× costs (PF 1.15). Loses in low-volatility regimes (PF 0.83), wins in high volatility (PF 1.31). Monte Carlo dropout p05 Sharpe positive; permutation p = 0.050 (borderline).

Year by year (strategy vs holding gold): 2016 −1.4% / +8.2%, 2017 +6.0% / +13.2%, 2018 −3.5% / −1.6%, 2019 +7.1% / +18.3%, 2020 −10.7% / +25.1%, 2021 +27.7% / −3.6%, 2022 −3.8% / −0.3%, 2023 +2.8% / +13.1%, 2024 +23.7% / +27.2%, 2025 +26.2% / +64.6%, 2026 +1.0% / −10.3%.

- Full period: 6.2% a year at 1% risk per trade, about 20 trades a year.
- 2016 to mid-2024 (before the period the spec was designed on): 3.9% a year, max drawdown −16.3%. Holding gold: 9.7% a year, max drawdown −21.9%.

## Short side: fails

Out-of-sample profit factor 0.34; bootstrap Sharpe p05 −3.8; permutation p = 0.14.

## Verdict

A weak but plausible edge on the long side: it survives costs and the robustness gates, and some of its best years (2021) came when gold fell, so it is partly independent of gold's trend. It earned less than simply holding gold, had five losing years out of eleven, and needs a 16% drawdown tolerance at 1% risk per trade, which would break a 10% prop-firm loss limit unless risk is cut to about 0.5%.
