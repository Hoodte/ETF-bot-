# Meta-labelling exit test for Nasdaq lunch-RSI (written 2026-11-12 11:45, before running)
Decision point: the first 15-min bar where a trade reaches +0.8R (355 of ~600 trades).
Choice: close there (+0.8R) or hold with the normal rules (stop 1R / target 3R / 15:55 NY).
Label: 1 if holding finished better than +0.8R.
Features known at that moment (no look-ahead): bars since entry, NY time of day, stop size as % of price,
RSI(14) at entry, return from 09:30 NY open to entry, return over the 4 bars before entry, 20-bar volatility,
how far past +0.8R the bar closed, bar range / ATR.
Models: logistic regression (simple) and a small gradient-boosted tree model (max depth 2, 100 trees).
Train on 2016-2020 trades only; pick the probability threshold on 2016-2020 too.
Then apply unchanged to 2021-2024 and 2025-2026.
PASS = beats "always hold" in total R in BOTH 2021-24 and 2025-26 (and doesn't lower Sharpe of the full strategy).
