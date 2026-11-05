# Round 7a: index intraday momentum (Gao, Han, Li & Zhou 2018, "Market intraday momentum", JFE)

Written 2026-11-05 before running. The paper found (S&P 500 ETF, 1993-2013) that the first half-hour return (previous close to 10:00 ET) predicts the last half-hour (15:30-16:00 ET). No parameters are fitted here; every year we test is after the paper's sample.
- Markets: S&P 500, Nasdaq 100 (New York time), DAX (Frankfurt: previous 17:30 to 09:30 predicts 17:00-17:30).
- V1: trade the last half-hour in the direction of the first half-hour return.
- V2: same, only when |first half-hour return| is above its 60-day median.
- V3: direction of (first half-hour + 15:00-15:30 return) (the paper's joint version).
- Entry at the open of the last half-hour (5m bars), exit at its close. Costs 1.0 bps per side (DAX 1.2), plus 2x stress.
- Pass: 3-index portfolio Sharpe of at least 1.0 in 2021-2024 and above 0 at 2x costs, and above 0.5 in the 2025-26 holdout. 2016-2020 is reported too.
