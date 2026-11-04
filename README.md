# ETF-bot

A rules-based, long-or-cash ETF strategy engine for a UK retail account, with backtesting, hard risk limits, and paper trading. This repo implements phases 1–4 of the ETF Trading Bot Plan. Live trading is deliberately not implemented.

**Status:** core engine built and tested on synthetic data only. No real backtest has been run yet. That needs internet access to Yahoo Finance from your machine.

## What's here

| Module | Desk role | Job |
| --- | --- | --- |
| `etfbot/data.py` | Scanner | Downloads prices, splices US-listed proxy history before each UCITS fund launched (so tests cover 2008), converts USD to GBP |
| `etfbot/quality.py` | Data Quality | Blocks the run on missing days, spikes (pence/pounds errors), gaps, or stale data |
| `etfbot/strategies.py` | Trend Engine / Secondary | Trend (on), rotation (off), dip (off). Pure functions, no look-ahead |
| `etfbot/backtest.py` | — | Holdings-based daily backtest, next-bar execution, spread + commission costs |
| `etfbot/report.py` | Skeptic | Out-of-sample metrics, stress periods (2008, 2020, 2022), cost x2 stress, parameter nudge ±20%, bootstrap Sharpe → PASS/FAIL |
| `etfbot/risk.py` | Risk Guardian | Hard limits in code: position cap, order cap, daily order limit, drawdown pause, kill switch, no shorting, no leverage |
| `etfbot/broker.py` | Execution | Paper broker with state on disk; live broker raises an error |
| `etfbot/cli.py` | Head of Desk input | Every command prints JSON for n8n |

The signals come from Python only. AI agents read the JSON output and report on it. They must not calculate or override signals.

## Setup

```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Commands

```
python -m etfbot check-data                 # download + data quality report
python -m etfbot backtest --strategy trend  # writes reports/trend.md and .json
python -m etfbot signal                     # today's target weights (JSON)
python -m etfbot paper                      # signal -> risk review -> paper fills
python -m pytest                            # tests
```

Add `--synthetic` to run any command offline on random-walk data. Synthetic results mean nothing about real markets; they only prove the code runs.

Emergency stop: create the file `state/KILL`. Nothing trades while it exists.

## n8n

Use an **Execute Command** node, for example `cd /path/to/ETF-bot- && python -m etfbot paper`. Parse stdout as JSON. Exit code 1 means blocked or failed, so route it to an alert.

Suggested flow: weekday schedule after the London close → `check-data` → `signal` → `paper` → Telegram/email summary → log. Add a separate error workflow.

## Rules that must not change without a new test

- Parameters in `config.yaml` are frozen before the out-of-sample run. Changing them after seeing results invalidates the test.
- Out-of-sample period starts at `backtest.oos_start` (2016-01-01). Judge strategies on that period only.
- Rotation and dip stay disabled until trend passes the paper-trade gate.
- Long-or-cash only. No shorting, no leverage.

## Known limitations

- Proxy history (SPY, EFA, AGG, GLD, EEM) is an approximation of each UCITS fund before launch. The bond proxy is a USD aggregate, not GBP-hedged global.
- Yahoo data can contain errors. The quality check catches the common ones, not all.
- The paper broker fills at the last close plus a spread. Real fills will differ.
- Order sizes over the £1,000 cap are filled over several runs, so a new position can take a few weeks to fully build.
- Tickers (e.g. `SWDA.L`) must be checked against what your broker actually offers.

## Next steps

1. Run `check-data` on your machine and fix any data issues it reports.
2. Run `backtest --strategy trend` and review `reports/trend.md`.
3. If the Skeptic verdict is PASS, start the paper schedule in n8n for 1–2 months.
4. Only then build the live broker adapter (Trading 212 or IBKR).
