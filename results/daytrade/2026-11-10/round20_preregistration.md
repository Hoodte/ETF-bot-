# Round 20: Volume-profile POC retest, trend continuation (Instagram swift.trades0; written 2026-11-11 09:40, before running)
Objective version of the discretionary rule:
- 5-minute bars. Swings from a zigzag: a swing low is confirmed when price rises k x ATR(14) above the lowest low since
  the last swing high (mirror for highs). Base k = 3.
- When a DOWN leg (swing high -> swing low) is confirmed, build a profile over that leg's bars: 30 price bins,
  weighted by volume (crypto) or by time-at-price (indices: no real volume in the data, so a TPO/market-profile proxy).
  POC = busiest bin.
- Short with a limit at the POC when price comes back up to it (fill at the open if it gaps through), within 1 day.
  Stop = POC + 0.25 x leg range. Target = 2R. Cancel if price breaks the swing high first. Mirror for UP legs (buy).
- Exit at stop/target, else after 1 day. Stop checked before target inside a bar.
Markets: Nasdaq 100, S&P 500 (HistData 5m, TPO proxy); BTC, ETH (Binance 5m, real volume).
Costs/side: indices 0.5 bp; crypto 4 bp. Nearby: k 2/5; stop 0.15/0.35 x range; target 1.5R/3R.
PASS (higher bar) = Sharpe >= 0.4 in 2016-20 (crypto from 2017-08) AND >= 0.2 in 2021-24 AND > 0 in 2025-26, nearby mostly positive.
