# 04. What the Nifty data itself says (2015 to 5 Oct 2026)

Source: Yahoo Finance daily data (`^NSEI`, `^INDIAVIX`, `^GSPC`), downloaded 5 Oct 2026 into `data/`.

Reproduce with `.venv/Scripts/python research_notes/nifty_daily_facts.py`. Full output is in `nifty_daily_facts_output.txt`. There are 2,893 trading days.

Caveat: these are descriptive statistics, and the 5-day windows overlap, so the significance is overstated. They tell us where to look, not what to trade.

## 1. All of Nifty's gain since 2015 came overnight. Intraday has been a headwind.

| | Overnight (prev close → open) | Intraday (open → close) |
|---|---|---|
| Cumulative log return 2015–2026 | **+309.6%** | **−210.7%** |
| Mean per day | +0.109% | **−0.069%** |
| Share of days the close is above the open | — | **46.7%** |

- The pattern holds in 10 of 12 years. 2025 was the exception (intraday +1.3%).
- This matches Bhat et al. (2024) for 2017–2020 (overnight +0.15%, intraday −0.10%).
- **Implication:** a system that buys calls at 9:15–9:30 and holds to 3:15 fights a negative drift on average. Long intraday trades need a stronger signal than short ones.

## 2. The 55% accuracy target vs the naive baseline

- **P(up day) = 53.3%.** Predicting "up" every day already scores 53.3% "accuracy".
- P(up | yesterday up) = 56.7%. P(up | yesterday down) = 49.5%. There is mild daily persistence.
- So **55% daily-direction accuracy is only about 2 points better than a coin tilted the way the market drifts.** Accuracy has to be judged against this baseline, and much more importantly, on *expectancy after costs*.

## 3. Options are usually overpriced (the volatility risk premium is real in India)

- The implied 1-day move (VIX/√252) averaged **1.04%**. The actual average |daily move| was **0.70%**. A normal distribution would give 0.83%.
- Days where the move exceeded the implied 1-sd: **21.1%** (a normal distribution gives 31.7%). Days beyond 2-sd: **2.6%** (normal 4.6%).
- **VIX was above the next 21 days' realized volatility on 80.5% of days**, by a median of about 3.3 vol points.
- 2026 is the weakest year for this premium (mean 1.17 points, positive on only 67% of days). This is the war-driven high-volatility year, and the premium shrinks exactly when sellers get hurt.
- Weekly window: Nifty stayed inside the VIX-implied 1-sd **weekly** range **74.5%** of the time (normal 68.3%).
  - Since the switch to Tuesday expiry (Sep 2025): 73.5% inside. The average |5-day move| was 1.38% vs 1.90% implied.
- **Implication:** a plain option *buyer* pays for roughly 35–40% more movement than usually happens. A directional view therefore has to clear this hurdle too. That is why the system should consider **debit spreads** (where the short leg returns some of the overpriced premium) or **credit spreads in the forecast direction** when IV is rich.

## 4. Gaps fade slightly

| Open type | N | P(close > open) | Mean open → close |
|---|---|---|---|
| Gap up > +0.5% | 454 | 52.9% | −0.04% |
| Gap down < −0.5% | 251 | **53.8%** | **+0.11%** |
| Flat open (abs gap < 0.2%) | 1,107 | 43.6% | −0.09% |

**Implication:** don't chase large gaps at the open. A gap-down has a small tendency to recover.

## 5. Global cues explain the gap, not the day

- Corr(US previous session, Nifty gap) = **0.47**. The signs agree 68.4% of the time.
- Corr(US previous session, Nifty open → close) = **−0.03**. The signs agree 49.1% of the time, i.e. **zero**.
- **Implication:** GIFT Nifty and US futures are useful for *knowing the opening context*, but they add no information about the intraday direction once the market has opened.

## 6. Trend filter (close vs 50-day moving average), next 5 days

| State | N | P(5-day fwd > 0) | Mean | SD |
|---|---|---|---|---|
| Above 50-DMA | 1,819 | 57.4% | +0.26% | 1.84% |
| Below 50-DMA | 1,020 | 54.8% | +0.09% | **2.84%** |

**Implication:** a mild edge. The main value is as a *volatility regime* flag: below the 50-DMA, moves are 54% larger.

## 7. VIX level vs the next 5 days

| VIX | N | Mean abs 5-day move | P(up) |
|---|---|---|---|
| < 12 | 414 | 1.16% | 50.5% |
| 12–15 | 928 | 1.36% | 56.5% |
| 15–18 | 730 | 1.63% | 58.1% |
| 18–22 | 455 | 1.87% | 56.7% |
| > 22 | 295 | 2.98% | **61.0%** |

**Implication:** high fear tends to mean-revert upward over a week, but with much bigger swings. Fat tails cut both ways, so size must shrink as VIX rises.

## Next measurements, once we have intraday data

- First 30-min return → last 60–90-min return (Gao et al. intraday momentum) on Nifty futures
- Noise-area breakout (Zarattini) on Nifty futures with Indian costs
- Option-chain order imbalance in the first 15 minutes → rest-of-day return
- Expiry-day (Tuesday) vs non-expiry-day behaviour since Sep 2025
