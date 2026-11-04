# Backtest report: blend

Skeptic verdict: **PASS**

Parameters (frozen): `{'enabled': False, 'components': ['tsmom', 'sma_cross', 'faber']}`

| Period | CAGR | Vol | Sharpe | Max DD |
| --- | --- | --- | --- | --- |
| Strategy, full | 8.4% | 13.7% | 0.66 | -20.6% |
| Strategy, in-sample | 5.5% | 12.0% | 0.51 | -16.9% |
| Strategy, out-of-sample | 11.7% | 15.3% | 0.80 | -20.6% |
| Buy & hold, full | 11.9% | 18.8% | 0.70 | -35.0% |
| Buy & hold, out-of-sample | 15.7% | 17.8% | 0.91 | -26.1% |

## Stress periods

| Period | Strategy return | Strategy max DD | B&H return | B&H max DD |
| --- | --- | --- | --- | --- |
| gfc_2008 | -11.8% | -14.4% | -23.8% | -34.8% |
| covid_2020 | -9.2% | -20.6% | 2.0% | -26.1% |
| rates_2022 | -13.3% | -13.8% | -9.4% | -15.8% |

## Checks

- oos_positive: pass
- beats_bh_on_risk_or_return: pass
- survives_2x_costs: pass
- stable_to_param_nudge: pass

Robustness: `{'oos_cagr_costs_x2': 0.11563962121945837, 'oos_cagr_all_components_nudged': {'x0.8': 0.10510963355055858, 'x1.2': 0.13015674791531273}, 'oos_sharpe_bootstrap_5_95': [0.4239114719599843, 1.277590334809424]}`

Round-trip trades: 7, win rate 71.4%, avg win 52.76%, avg loss 8.28%, avg hold 830.7 days

Second opinion (backtest-expert skill):

```
python3 .claude/skills/backtest-expert/scripts/evaluate_backtest.py --total-trades 7 --win-rate 71.4 --avg-win-pct 52.76 --avg-loss-pct 8.28 --max-drawdown-pct 20.6 --years-tested 21 --num-parameters 4 --slippage-tested --output-dir reports/
```

Orders per year: 3.7; total costs £293
