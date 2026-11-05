# Strategy card: Gold macro composite (saved for long-term use, 5 Nov 2026)

**Status:** profitable in both test periods; no edge over simply holding gold at equal risk. Candidate for a slow, long-term bot or a funded account. Paper or demo trade it before any real money.

## Rules (frozen, pre-registered)

Checked once a day, after the US close; positions change from 00:00 UTC the next day.

Be **long gold** when at least 2 of these 3 are true, otherwise flat (never short):
1. The US dollar index (DXY, Yahoo `DX-Y.NYB`) is below its 50-day average.
2. The TIPS bond ETF (`TIP`) is up over the last 20 trading days, meaning real yields are falling.
3. CFTC managed-money net position in gold (% of open interest) is below the 70th percentile of its last 3 years. Use it from the Monday after each Tuesday report.

Code: `etfbot/goldquant.py`, strategy `macro_composite`.

## Results (XAUUSD, Dukascopy hourly, 3 bps per side)

| | 2016–2021 (in-sample) | 2022–Oct 2026 (out-of-sample) | Holding gold, 2022–26 |
| --- | --- | --- | --- |
| Return per year | 9.4% | 10.6% | 16.8% |
| Sharpe | 0.87 | 0.79 | 0.93 |
| Worst drop | — | −20.6% | −30.3% |

- At 2× costs: 9.7% a year out-of-sample. With the 50-day average moved ±20%: 11.7% / 9.0%.
- About 12 trades a year, in the market about half the time.
- Win rate 48%, average win +3.3%, average loss −1.35%; best trade +18.5%, worst −7.1%.
- Chance the edge over zero is real: 99.4%. Chance it beats holding gold at equal risk: 51%.

## Prop-firm projections (simulation of past behaviour, not a forecast)

Typical rules assumed: +10% target, −10% max loss, −5% daily loss; funded split 80%; gold overnight fee 2–4% a year.

| Position size (× account) | Pass the challenge | Time to pass | Keep a funded account (1 yr) | Typical month per $100k | Average month per $100k |
| --- | --- | --- | --- | --- | --- |
| 0.5× | 46–58% | ~13–14 months | 99% | ~$230 | ~$300 |
| **0.75× (sweet spot)** | **64–74%** | **~9–10 months** | **88%** | **~$270** | **~$420** |
| 1.0× | 67–74% | ~6–7 months | 69% | ~$160 | ~$460 |
| 1.3× | — | — | 44% | $0 | ~$440 |
| 2.0× | — | — | 21% | $0 | ~$400 |

**Leverage:** 0.75× means about $75k of gold exposure on a $100k account, which is below 1:1. Using more of a prop firm's available leverage lowers expected income, because the 10% loss limit ends accounts.

**Before going live, check:** the firm's gold swap or overnight fee, whether positions may be held over weekends (this strategy holds for weeks), time limits, and capital caps.

**Next idea to raise income:** combine it with uncorrelated trend strategies (indices, Bitcoin) so the account can carry more size within the same loss limit.
