# Brief: can we keep more of the open profit without hurting long-run returns?

I'm running an automated strategy on an FTMO $100k demo account. Please analyse the problem below and suggest exit rules that might help, then **test them on the attached trade data** before recommending anything. I care about total profit over 10 years, not how a single week looks.

## The problem in one paragraph

Trades often go well into profit, then reverse and close at a full loss. In my first live week:
- One Nasdaq trade was up about **+$900**, then closed at **−$1,300**.
- A gold trade was up about **+$400**, then hit its stop at **−$2,085**.
- The week overall ended at **−1.4%** (balance $98,608), when it could have finished up around **+$2.5k**.

I want to know whether there's an exit rule that captures some of that open profit **without cutting off the big winners that make the strategy profitable**.

## The strategy

**1. Nasdaq "lunch RSI" (main earner, the trade data is for this one)**
- Instrument: US100 (Nasdaq 100 CFD), long only.
- Entry: RSI(14) > 70 on an M15 bar starting 11:30–13:29 New York time.
- Stop: 1 ATR. Target: 3 ATR. Anything still open is closed at 15:55 NY.
- Risk: 1.1% of the account per trade (position size varies with ATR).

**2. News surprise**
- After big US/Canada data releases, it enters 5 minutes after the release in the direction of the surprise and holds for 60 minutes.

**3. Gold macro composite** (traded manually, paused for the trial)
- Long gold when 2 of 3 conditions hold: DXY below its 50-day SMA, TIP 20-day change > 0, COT percentile < 0.70.
- 5% stop. Holds for weeks.

## The backtest data (attached CSV)

`nasdaq_backtest_trades_2016-2026.csv` holds **596 Nasdaq trades** from Jan 2016 to Oct 2026, with costs included.

Key columns:
- `r_multiple`: final result in R (1R = initial risk).
- `r_mfe`: furthest the trade went in my favour, in R.
- `r_mae`: furthest the trade went against me, in R.
- `exit_reason`: stop / target / eod_flat.
- `entry_ts`, `exit_ts`, `net_pnl`, `mfe`, `mae` (in price points).

Headline numbers:
- Total **+122.6R** over 10 years. Average +0.21R per trade.
- Win rate 43%.
- Exits: 320 stops, 102 targets, 174 end-of-day closes.
- **355 trades reached +0.8R.** Of those, **132 finished at +2R or better** and **102 finished as losers.**
- Typical results cluster at about −1R (losers) and +1.7R to +3R (winners). The edge comes from the big winners.

## What we've already tested (please don't just repeat these)

| Idea | Result vs current (+123R) |
|---|---|
| Take profit at +0.8R | **−13R** (kills the big winners) |
| Move stop to break-even at +1.5R | About a tie |
| Momentum-fade exits (RSI/speed dropping) | Worse, apart from "exit if RSI < 50", which tied |
| Weekly profit cap (stop trading after +X% in a week) | No benefit |
| Meta-labelling: logistic regression at the +0.8R point predicting "goes to +2R vs reverses" | **+11.5R** out-of-sample 2021–26 (~+2R/yr, bootstrap p≈3%). Promising but small; parked until there's live data |
| Same meta-label with boosted trees | Overfit |

Testing rules I follow:
- Pre-register the idea.
- Train on 2016–20; check on 2021–24 and 2025–26 separately.
- Check that nearby parameter values also work, not just one lucky value.
- Include costs.

## What I'd like from you

1. **Explain why** this pattern (big open profit that then reverses) is or isn't a fixable problem for a strategy with this payoff shape. Is it just the cost of catching the 3R winners?
2. Propose **2–4 exit ideas we haven't tried**. Examples: partial close at +1R with the rest running; trailing stop that starts only after +1.5R; time-based exits; ATR-chandelier trail; scaling out.
3. For each idea, **test what you can with the CSV**.
   - Note: the CSV only has MFE/MAE per trade, not the bar-by-bar path. So say which ideas can be tested properly from it, and which would need M15 bar data. For a trailing stop, the order in which the high and the reversal happened matters.
4. Report each idea's **total R, results split by 2016–20 / 2021–24 / 2025–26, max drawdown, and worst losing streak**, compared with the current exit.
5. Give an **honest verdict**. "Nothing beats the current exit" is an acceptable answer. I'd rather know than add a rule that looks good on one week.

Please don't recommend anything that only helps the trades from this one week. One week is about 3–5 trades and tells us almost nothing on its own.
