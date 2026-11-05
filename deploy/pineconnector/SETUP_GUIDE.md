# 3-strategy FTMO plan: setup guide (PineConnector + MT5)

| File | Runs on | What it does |
|---|---|---|
| `1_Nasdaq_LunchRSI_PineConnector.pine` | TradingView, Nasdaq 100 CFD **15m** chart | Long when RSI(14) > 70 during 11:30-13:30 New York; 1 ATR stop, 3 ATR target; about 1 trade a week |
| `2_Gold_Macro_PineConnector.pine` | TradingView, spot gold **daily** chart | Long gold when 2 of 3 macro votes agree (weak dollar, rising TIP, COT not crowded); volatility-sized; holds days/weeks |
| `3_NewsSurprise_Guard_EA.mq5` | MT5 (same account as PineConnector) | US/CA news-surprise trades on 6 pairs **plus the account-wide FTMO guard** for all three strategies |
| `news_events.csv` | MT5 Strategy Tester only | 2,855 past US/CA releases (2016-Oct 2026) with surprise scores, for backtesting the news EA |

The news strategy is an MT5 EA, not Pine, because Pine can read economic data but **not the forecasts**, so it can't calculate a surprise. MT5's built-in calendar has both.

---

## 0. Keeping the strategies separate (do this first)
| Symbol | Traded by | Opens with | Closed by |
|---|---|---|---|
| US100.cash | Nasdaq script (PineConnector) | `buy` + stop/target, comment `NasLunchRSI` | its stop/target, or `closelong` at the end of the day |
| XAUUSD | Gold script (PineConnector) **and** news EA | gold: comment `GoldMacro`; news: comment `NEWS`, magic 26110510 | gold: `closelong` / 5% stop; news: the EA closes **its own ticket** after 60 min |
| EURUSD, GBPUSD, AUDUSD, USDJPY, USDCAD | News EA only | comment `NEWS`, magic 26110510 | the EA, by ticket |

Three settings keep them apart:
1. **Use a HEDGING MT5 account** (MT5: Toolbox → Trade, or ask FTMO). On a netting account, gold trades from both strategies would merge into one position. The news EA detects netting, warns you, and stops trading gold.
2. **PineConnector EA → "Magic Restriction" ON.** Then `closelong,XAUUSD` from the gold script only closes PineConnector's own gold trades, never the news EA's.
3. The news EA only manages the tickets it opened (checked by magic number), so it never closes a PineConnector trade. The one exception is the **safety guard**, which closes **everything** on purpose after a -2% day.

## 1. MT5 + PineConnector
1. Install the **PineConnector EA** in your FTMO MT5 terminal (EA v3.53.2 or later, for the explicit syntax used here) and enter your licence ID.
2. Enable *Algo Trading*. Keep MT5 running 24/5 (a VPS is best).

## 2. TradingView scripts (Nasdaq + gold)
For each `.pine` file:
1. Pine Editor → New → paste the file → **Save** → **Add to chart**.
   - Nasdaq: a Nasdaq 100 CFD on **15-minute** bars (e.g. `FOREXCOM:NSXUSD` or `CAPITALCOM:US100`).
   - Gold: spot gold on **daily** bars (e.g. `OANDA:XAUUSD`).
2. Settings → Inputs: your **PineConnector licence ID** and the **FTMO MT5 symbol names** (`US100.cash`, `XAUUSD`).
3. The Strategy Tester tab shows the TradingView backtest.
4. Alert: Create alert → Condition = the strategy → **"alert() function calls only"** → Notifications: tick **Webhook URL** and paste PineConnector's webhook → Create. (Webhooks need a paid TradingView plan.)

**Gold COT check:** the table (top right) shows each vote. If "COT data" says **n/a**, the default COT tickers are wrong for your account. Add TradingView's built-in *Commitment of Traders: Disaggregated Metrics* indicator to a `GC1!` chart, pick *Managed Money Positions* Long, then Short, then *Open Interest*, and copy the ticker IDs it shows into the three COT inputs.

## 3. MT5 news EA + safety guard
1. MT5 → File → Open Data Folder → copy `3_NewsSurprise_Guard_EA.mq5` into `MQL5\Experts\` and `news_events.csv` into `MQL5\Files\`.
2. Open it in MetaEditor → **Compile** (F7). If there are errors, send me the error lines.
3. Attach it to **one** chart (e.g. EURUSD M1). Inputs:
   - symbol names (FTMO defaults are filled in)
   - `InpStartBalance` = your account size
   - `InpGuardAll = true`, so the guard also closes the PineConnector trades
4. Leave it running alongside the PineConnector EA.

**Backtest the news EA in MT5:** Strategy Tester → this EA → symbol EURUSD → model "1 minute OHLC" or "Every tick based on real ticks" → dates 2021-2026. It reads `news_events.csv` automatically in the tester. The server time zone is assumed FTMO-style (GMT+2, GMT+3 in US summer time); for another broker set `InpServerGMT`.

## 4. Sizes used (the "plan x1.5" from the research)
| Strategy | Setting | Meaning |
|---|---|---|
| Nasdaq | Risk per trade 1.1% | stop hit = -1.1% of equity |
| News | `InpRiskPerUnit` 0.15 | a normal day's move against one trade = -0.15% of equity (stop is at 0.4 of that move) |
| Gold | Plan size 0.75 | holds about 0.75 x equity in gold when on (scaled by volatility, max 1.1x) |
| All | -2% daily stop, half size below -5% | the guard EA closes everything for the day at -2% |

## 5. Paper-trade checklist (4 weeks on an FTMO demo / free trial)
- [ ] Every TradingView alert reached MT5 (PineConnector log).
- [ ] News trades: fill price vs the price 5 minutes after release. The edge is about 2 bps a trade, so slippage matters most here.
- [ ] Weekly P&L per strategy vs the backtest (about $100-450/week per $100k combined).
- [ ] The guard never needed to fire, or fired correctly.
- [ ] The FTMO account type allows weekend holding (needed for gold).

## Known differences from the research backtests
- TradingView prices differ slightly from FTMO's; the Nasdaq script sends stop/target as % from entry to reduce this.
- MT5's "high importance" list is not identical to TradingView's (used in research), so live news trades will differ a little.
- Gold is sized at entry and not resized while held (research resized hourly), which saves trading costs.
- These files have not yet been compiled in TradingView/MetaEditor; expect a possible small syntax fix on first compile.
