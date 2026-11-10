# FTMO plan: watch list and parked ideas
Last updated: 10 Nov 2026. Live plan (unchanged): news-surprise EA + Nasdaq lunch-RSI 1:3 (EA v1.10 on MQL5 VPS) + gold macro composite vol10 (manual via TradingView alert for now).

## Ready to add (tested improvement)
| Item | Evidence | When |
|---|---|---|
| Gold trailing stop 10% (keep the 5% fixed stop too) | Beats current in 2016-21, 2022-26 and 2025-26; every trailing distance 7-12% also beats current. Gain small (~+0.2%/yr at plan size) but consistent. | When gold is automated (TradingView + PineConnector). Manual rule until then: move stop to 90% of the highest price since entry when that is above the fixed stop. Results: `results/2026-11-08/gold_exits2_results.md` |

## Revisit with live data (after 2-3 months)
| Item | Why parked | Results |
|---|---|---|
| Nasdaq lunch-RSI target 1:3 vs 1:4 | 1:4 better 2021-26, 1:3 better 2016-21 (where it was picked). Both in the same good zone; tighter targets clearly worse. | `results/2026-11-08` chat summary; script `results/daytrade/2026-11-10/nasdaq_targets_exits_tp.py` (run from the backtest-bot folder) |
| News bot panic switch (pause when previous-day VIX > 35) | Improves 2016-20 (mainly March 2020), no harm 2021-26. Thresholds 25/30 hurt later periods. Optional safety catch. | `results/daytrade/2026-11-10/round17_vixfilter_results.md` |

## Watch-list strategies (not good enough yet)
| Strategy | 2016-20 | 2021-24 | 2025-26 | What would change our mind | Results |
|---|---|---|---|---|---|
| Turn-of-the-month (S&P + Nasdaq, 2 days before month end to day 3) | 0.48 | 0.18 | 0.57 | Passed the rules but weak and lumpy (2024 -10%). Next step: add at small size to the combined plan in the FTMO simulation; keep only if the plan gets smoother. | `results/daytrade/2026-11-10/round14_*` |
| US opening gap fade (S&P/Nasdaq, gaps 0.25-1.5%, target previous close) | -0.65 | -1.27 | 1.02 | Lost 2016-24 in every version, works in every version since 2025. Re-check once 2027 data exists. | `results/daytrade/2026-11-10/round18_*` |
| Deep-dip buying (RSI(2) < 5 above 200-day average) | -0.02 to -0.31 | 0.48-0.96 | 0.61-1.39 | More years of good results. | rounds 13 and 14 |
| Pre-Fed drift (long S&P the afternoon before FOMC) | 0.69 | 0.94 | -1.05 | Recovery in 2027; only ~8 trades/yr. | round 13 |

## Tested and dropped (do not re-test without a new reason)
Currency momentum basket, VIX expected-move bands ("IV walls"), US news on S&P/Nasdaq/DAX/oil, oil inventory surprise,
leader-follower catch-up (gold-silver, S&P-Nasdaq, S&P-DAX, EURUSD-GBPUSD, AUDUSD-AUDJPY), gold signal on silver (works but 0.76 correlated with gold),
gold/silver ratio, carry with trend, month-end FX flows, options-expiry week, quarter-end rebalancing, overnight drift,
intraday momentum, NY ORB v5 (user's TradingView script), gold entry timing (RSI, EMA20 rejection, prev-low sweep),
gold take-profits (+1% to +5%), gold stacking (average down / pyramid), gold half-off split (smoother, less profit), gold tight trailing stops (3-5%, ATR).
Results: `results/2026-11-08/`, `results/daytrade/2026-11-10/`.

## Rules for any future test
Write the rule down before running; choose on 2016-20 only, confirm on 2021-24, check on 2025-26; nearby settings must also work;
survive double costs; with this many ideas tried, use the higher bar (Sharpe >= 0.4 / >= 0.2 / > 0).
