# Round 18: US opening gap fade (written 2026-11-10 17:03, before running)
Data: HistData 5-minute S&P 500 and Nasdaq 100, New York time.
Gap = 09:30 open / previous 16:00 close - 1.
Base rule: trade only if 0.25% <= |gap| <= 1.5% (skip tiny gaps and big news gaps). Enter against the gap at the
09:35 open. Target = previous close (gap filled). Stop = entry +/- gap size (1:1 vs the target). If neither, exit at 12:00.
Costs 1 bp/side; stop checked before target inside a bar; gaps through the stop filled at the worse open.
Nearby settings: min gap 0.15% / 0.40%; max gap 1.0% / 2.5%; enter at the 09:30 open; exit at 16:00 instead of 12:00.
PASS = Sharpe >= 0.4 in 2016-20 AND >= 0.2 in 2021-24 AND > 0 in 2025-26 AND most nearby settings positive in all periods.
Reported for S&P, Nasdaq and 50/50.
