# Round 15 (written 2026-11-10 15:40, before running)
## Part 1: US/CA news surprises on other markets
Same events, z-scores and rule as the live news bot (news_events.csv; |z| > 0.5; same-minute releases netted;
z > 0 = good for the dollar). Enter 5 min after the release, close 60 min later.
Markets: S&P 500, Nasdaq 100, DAX, Brent oil (USD news only; oil also uses CAD news netted with USD).
Direction is not known in advance (good US data can lift stocks or sink them through rate fears), so the direction
is chosen on 2016-2020 ONLY, then frozen. Costs: indices 1 bp/side, Brent 3 bps/side.
Pass = Sharpe >= 0.3 in 2016-20 (chosen direction) AND > 0 in 2021-24; 2025-26 is a fresh check that must also be > 0.
## Part 2: "leader moves, follower catches up" on other pairs
Hourly, same rule as the silver test: if the two markets' last-hour returns differ by more than a threshold
(0.3% for metals/indices/oil, 0.15% for FX), hold the follower toward the leader for the next hour, entered one bar late.
Pairs: S&P->Nasdaq, Nasdaq->S&P, S&P->DAX, EURUSD->GBPUSD, AUDUSD->(inverse)USDCAD... kept to 5 pairs:
SPX->NSX, NSX->SPX, SPX->DAX, EURUSD->GBPUSD, AUDUSD->AUDJPY. Costs: indices 1 bp/side, FX 1 bp/side.
Pass rule as Part 1 (no direction choice).
