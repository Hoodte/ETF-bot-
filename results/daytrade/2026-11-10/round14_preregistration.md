# Round 14: four documented add-on ideas (written 2026-11-10 15:30, before running)
Data: HistData 5-minute S&P 500 (SPXUSD) and Nasdaq 100 (NSXUSD), New York time, cash session 09:30-16:00.
Costs: 1 bp per side; holding overnight costs 5%/yr financing per night (weekends count 3 nights).
| # | Strategy | Rule (fixed, nothing fitted) |
|---|---|---|
| A | Turn-of-the-month | Long index from the 16:00 close two trading days before month end to the 16:00 close of the 3rd trading day of the new month |
| B | Intraday momentum (Gao et al. 2018) | Sign of the return from the previous 16:00 close to 10:00 today; take that side at 15:30, close at 15:59 |
| C | Overnight drift | Long at 15:59 close, sell at 09:30 open next trading day, every day |
| D | Deep-dip on Nasdaq | Daily close above 200-day average and RSI(2) < 5: buy next 09:30 open; sell at first close above 5-day average or after 10 days |
Each strategy is run on S&P and Nasdaq separately and as a 50/50 pair.
Keep rule (same as round 13): Sharpe >= 0.3 in 2016-2020 AND > 0 in 2021-2024. 2025-26 is then a fresh check that must also be > 0 to recommend.
