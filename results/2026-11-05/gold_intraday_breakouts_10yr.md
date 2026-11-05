# Intraday gold breakouts (flat the same day): 10-year test

Engine: backtest-bot (stops and targets inside each bar, spread 0.30 + slippage). Data: Dukascopy XAUUSD H1, 2016–2026. Each trade is closed by its stop, its target, or the end-of-day flatten, so nothing is held overnight. 1% risk per trade.

1. **H2 London–New York overlap breakout** (from backtest-bot): range 05:00–13:00 UTC, breakout entry 13:00–16:00, trend bias (EMA50 on H1, equivalent to the original M15 EMA200), body ≥ 50%, stop 1.2×ATR, target 3×ATR, flat 20:00 UTC. Originally designed for M15 bars; this is the H1 version.
2. **Asian-range breakout** (pre-registered 5 Nov 2026): range 00:00–07:00 UTC, entry 07:00–11:00, same filters and exits, flat 16:00 UTC.

| Strategy | Trades | Profit factor (full) | In-sample / OOS / validation PF | At 2× costs | Permutation p | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| H2 overlap, long | 584 | 0.92 | 0.82 / 0.90 / 1.30 | 0.64 | 0.72 | Fail |
| H2 overlap, short | 505 | 1.10 | 0.86 / 1.91 / 1.01 | 0.76 | 0.31 | Fail |
| Asian range, long | 556 | 0.99 | 1.25 / 0.69 / 0.57 | 0.81 | 0.73 | Fail |
| Asian range, short | 447 | 0.97 | 0.81 / 1.18 / 1.50 | 0.71 | 0.53 | Fail |

All four fail backtest-bot's robustness gates. Each only worked in one volatility regime, none survived doubled costs, and none beat random in the permutation test. Drawdowns ran 29–61% at 1% risk per trade. About one trade a week per side.
