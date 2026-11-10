# Round 16: IV (VIX) expected-move bands (written 2026-11-10 15:47, before running)
Expected daily move EM = previous 16:00 close x previous-day VIX / 100 / sqrt(252) (no look-ahead).
Bands = previous close +/- k x EM, base k = 1.0. Nasdaq uses the same VIX (proxy; noted as a limitation).
Intraday, 5-minute bars, 09:30-15:55 New York; at most one trade per side per day.
- FADE: price touches the lower band -> buy at the band; touches the upper band -> sell at the band.
  Target = previous close; stop = 0.5 x EM beyond the band; otherwise close 15:55.
- BREAK: a 5-min bar closes beyond a band -> enter that direction at the next bar's open;
  stop = back at the band; otherwise close 15:55.
Costs 1 bp/side; stops filled at the stop level or worse open (gaps); same-bar target+stop counted as a stop.
Pass = Sharpe >= 0.3 in 2016-20 AND > 0 in 2021-24 AND > 0 in 2025-26; then nearby k (0.75, 1.25) must also be positive.
