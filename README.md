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
| `etfbot/timemachine.py` | Skeptic | Replays 10,000 possible one-year futures from the strategy's own history, plus every real past year: odds of a loss, of hitting the drawdown pause, of beating buy-and-hold. Idea adapted from trader-timemachine in [Jakeschincariol/day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill) (MIT) |
| `etfbot/trades.py` | Skeptic | Round-trip trade stats (win rate, average win/loss) and the ready-made command for the backtest-expert skill |
| `etfbot/crosscheck.py` | Skeptic | Re-runs the same strategy in vectorbt; if the two engines disagree by more than 2%, don't trust the backtest |
| `etfbot/tearsheet.py` | Head of Desk | QuantStats HTML report, strategy vs buy-and-hold |
| `etfbot/market_calendar.py` | Scanner | London Stock Exchange calendar, so nothing runs on weekends or UK market holidays |
| `etfbot/risk.py` | Risk Guardian | Hard limits in code: position cap, order cap, daily order limit, drawdown pause, kill switch, no shorting, no leverage |
| `etfbot/broker.py` | Execution | Built-in paper simulator with state on disk |
| `etfbot/live_brokers.py` | Execution | Trading 212 (pyt212) and IBKR (ib_async) adapters, demo/paper by default. Real money needs three gates: `mode: live`, `broker.allow_real_money: true`, and a human `approve` for each order (pattern from trader-broker in day-trader-skill, MIT) |
| `etfbot/cli.py` | Head of Desk input | Every command prints JSON for n8n |

The signals come from Python only. AI agents read the JSON output and report on it. They must not calculate or override signals.

## Setup

```
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-extras.txt   # tearsheets, London calendar, vectorbt, broker clients
```

## Commands

```
python -m etfbot check-data                 # download + data quality report
python -m etfbot backtest --strategy trend  # writes reports/trend.md and .json
python -m etfbot backtest --html            # also a QuantStats HTML tearsheet
python -m etfbot crosscheck                 # compare our backtester with vectorbt
python -m etfbot discover                   # rank all 14 pre-registered strategy candidates
python -m etfbot discover --etf US_EQ       # rank the 10 single-ETF strategies on one ETF
python -m etfbot combine --etf US_EQ        # blend the top 3 (picked in-sample) + interactive chart
python -m etfbot combine --etf US_EQ --strategies trend,faber,tsmom
python -m etfbot simulate --strategy trend  # Time Machine: 10,000 simulated years + every real past year
python -m etfbot signal                     # today's target weights (JSON)
python -m etfbot paper                      # signal -> risk review -> built-in paper fills
python -m etfbot market-status              # is the London market open today?
python -m etfbot trade                      # same, but through the configured broker (Trading 212 demo by default)
python -m etfbot approve <order-id>         # human approval for one real-money order
python -m pytest                            # tests
```

Add `--synthetic` to run any command offline on random-walk data. Synthetic results mean nothing about real markets; they only prove the code runs.

## Data source

By default prices come from Yahoo Finance via `yfinance`. Yahoo has reportedly restricted free end-of-day downloads, so if `check-data` fails, switch to your own files:

1. Set `data.source: csv` in `config.yaml`.
2. Save one CSV per ticker in `data/manual/`, named like `SPY.csv`, `GBPUSD_X.csv`, `SWDA.L.csv`, with a `Date` column and an `Adj Close` (or `Close`) column. You need every proxy ticker (SPY, EFA, AGG, GLD, EEM), each UCITS ticker, and `GBPUSD=X`.
3. Run `check-data`. It flags gaps, spikes and stale files before anything else runs.

## Strategy discovery

`discover` runs a fixed list of 14 documented, long-or-cash strategy families. Their parameters were frozen in `config.yaml` on 2026-11-04, before any real-data test:

| Candidate | Idea | Rebalance |
| --- | --- | --- |
| trend | hold each ETF while above its 200-day average | weekly |
| faber | hold each ETF while above its 10-month average (Faber) | monthly |
| rotation | hold the top 3 by 6-month return, only if positive | weekly |
| dual_momentum | top 3 by 12-month return; negative picks go to bonds or cash (Antonacci-style) | monthly |
| inverse_vol | always invested, more weight in calmer ETFs | monthly |
| trend_inverse_vol | inverse-vol weights, ETFs below their 200-day average go to cash | weekly |
| trend_voltarget | trend, scaled down when portfolio volatility is above 8% (never levered) | weekly |
| tsmom | time-series momentum: hold while own 12-month return > 0 (Moskowitz, Ooi & Pedersen) | monthly |
| sma_cross | hold while 50-day average > 200-day average | weekly |
| turn_of_month | hold last trading day of month to 3rd trading day of next, cash otherwise | daily |
| rsi2 | buy 2-day RSI < 10 dips inside a 200-day uptrend, sell above the 5-day average (Connors) | daily |
| pre_holiday | hold only on the trading day before a market holiday (Quantpedia, free) | daily |
| options_expiry_week | hold during the week of the month's third Friday (Quantpedia, free; a US effect) | daily |
| calendar_composite | turn-of-month (last 4 / first 3 days) or pre-holiday or option-expiry week, only above the 200-day average (Quantpedia composite with trend filter) | daily |

Strategies marked single-ETF capable (trend, faber, tsmom, sma_cross, turn_of_month, rsi2, trend_voltarget, pre_holiday, options_expiry_week, calendar_composite) can be tested on one ETF with `--etf`.

### Blending strategies on one ETF

`combine --etf US_EQ` gives up to 3 strategies an equal share of that ETF's capital and averages their positions. The blend goes through the full Skeptic check. It writes `reports/combine_US_EQ.html`, an interactive chart of all three strategies, the blend and buy-and-hold, with a results table.

With `--strategies auto` (the default), the 3 components are picked by **in-sample** Sharpe only (before 2016), so the out-of-sample years stay unseen when the choice is made. Picking them by looking at the out-of-sample results would make that test meaningless. Blending usually smooths drawdowns; it rarely raises return above the best single strategy.

A **survivor** must pass every Skeptic check and have a **deflated Sharpe** of at least 95%: the probability its out-of-sample result is genuine after correcting for the fact that 7 strategies were tried. The report also shows whether each beats buy-and-hold on Sharpe, the 2008 result, and the Time Machine odds of a losing year. Results go to `reports/discovery.md`.

Rule: never edit a candidate's parameters after seeing results. To try a variation, add it as a new, separately named candidate, so the deflated Sharpe correction counts it.

## Trade-size scaling

Every 8 weeks the bot reviews the account. If it is less than 7.5% below its peak, the order-size cap rises by 10% (£1,000 → £1,100 → £1,210 …). If the 15% drawdown pause was hit, it falls by 10%, never below the starting £1,000. The cap never exceeds `risk.max_order_gbp` (£10,000). Positions are a share of equity, so money you add is invested automatically; the cap only limits how much goes in per order, so a large top-up is invested over several runs. Settings are under `scaling:` in `config.yaml`.

## Leverage research

`python -m etfbot leverage --etf US_EQ` simulates 1x, 2x and 3x daily-reset leveraged versions with real borrowing costs (US T-bill + 0.5%) and a 0.75% fund fee, for buy-and-hold, Faber and trend, and projects 10 years with monthly top-ups (`--monthly 200`). Research only: live trading stays unleveraged.

## Claude skill: backtest-expert

`.claude/skills/backtest-expert/` is vendored from [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills) (MIT, commit d8e71ce). Claude Code picks it up automatically when you open this repo. Every backtest report ends with the exact command to run it, giving a 0-100 quality score and a Deploy/Refine/Abandon verdict as a second opinion next to our own Skeptic check. It uses only the Python standard library and makes no network calls.

## Broker setup (demo first)

1. Fill in `t212_ticker` (Trading 212) or `ibkr` (IBKR) for each instrument in `config.yaml`, and check each `price_scale` and `ucits_currency` against real quotes. These are marked VERIFY.
2. Trading 212: create an API key in the app, then `export T212_API_KEY=... T212_API_SECRET=...`. IBKR: run TWS or IB Gateway with the API enabled on the paper port 7497.
3. Run `python -m etfbot trade` against the demo/paper account for the full paper-trade period.
4. Real money only after the gates in the plan, by changing `broker.name`, `mode`, and `allow_real_money`.

Emergency stop: create the file `state/KILL`. Nothing trades while it exists.

## n8n

**Ready-made setup:** see [`deploy/README.md`](deploy/README.md) for a VPS setup script, an importable daily workflow (`deploy/n8n_etfbot_workflow.json`) and an error-alert workflow, with Telegram summaries.

Use an **Execute Command** node, for example `cd /path/to/ETF-bot- && python -m etfbot paper`. Parse stdout as JSON. Exit code 1 means blocked or failed, so route it to an alert.

Suggested flow: weekday schedule after the London close → `check-data` → `signal` → `paper` → Telegram/email summary → log. Add a separate error workflow.

## Rules that must not change without a new test

- Parameters in `config.yaml` are frozen before the out-of-sample run. Changing them after seeing results invalidates the test.
- Out-of-sample period starts at `backtest.oos_start` (2016-01-01). Judge strategies on that period only.
- Rotation and dip stay disabled until trend passes the paper-trade gate.
- Long-or-cash only. No shorting, no leverage (the `leverage` command is research only).

## Known limitations

- Proxy history (SPY, EFA, AGG, GLD, EEM) is an approximation of each UCITS fund before launch. The bond proxy is a USD aggregate, not GBP-hedged global.
- Yahoo data can contain errors. The quality check catches the common ones, not all.
- The paper broker fills at the last close plus a spread. Real fills will differ.
- The Trading 212 and IBKR adapters and the vectorbt cross-check were written against each library's source code and tested with fakes, not yet against real accounts or a real vectorbt install. Run them on demo/paper first.
- Order sizing uses the last Yahoo close of the UCITS line, not a live quote.
- Order sizes over the £1,000 cap are filled over several runs, so a new position can take a few weeks to fully build.
- Tickers (e.g. `SWDA.L`) must be checked against what your broker actually offers.

## Next steps

1. Run `check-data` on your machine and fix any data issues it reports.
2. Run `backtest --strategy trend` and review `reports/trend.md`.
3. If the Skeptic verdict is PASS, start the paper schedule in n8n for 1–2 months.
4. Then run `trade` on the Trading 212 demo (or IBKR paper) account and confirm the orders match `paper`.
