# Nifty weekly options system: research report

Prepared 5 October 2026, after the market close. This report covers the research phase only. Nothing has been built or traded.

I am not a licensed investment adviser. This is research for a system you will build and run yourself. It is not a recommendation to buy or sell any contract.

Supporting notes are in `research_notes/`:
- 01: market rules and the SEBI study
- 02: strategy evidence
- 03: Indian signals, data and algo rules
- 04: measurements on Nifty data, with the script that produced them

---

## 1. The short version

1. **The instrument has changed.** Weekly options now exist only on **Nifty 50 (expiry every Tuesday)** and **Sensex (Thursday)**. Bank Nifty is monthly only and has been since November 2024. Other changes:
   - The Nifty lot is 65.
   - STT on option sales went up to 0.15% of premium on 1 April 2026.
   - Expiry settlement has come from a closing auction (3:15–3:35 PM) since 3 August 2026.
2. **SEBI's August 2026 study is the base rate we are up against.**
   - 87.7% of individual F&O traders lost money in FY26.
   - Options produced 92% of the losses.
   - The loss rate rises with turnover, reaching 95% for people turning over more than ₹10 crore.
   - SEBI found option-buying losses "largely independent of market direction". Retail buyers lost money even in the quarter when Nifty rose 9%. **Getting direction right is not enough when you buy options.**
3. **A 55% hit rate is a weaker target than it sounds.** Since 2015, Nifty closed higher on 53.3% of days, so "always say up" already scores 53.3%. The number that matters is *expectancy after costs*: hit rate × average win − miss rate × average loss − costs.
4. **Options are usually overpriced, and that is measurable.** India VIX was above the volatility Nifty actually delivered over the next month on 80.5% of days since 2015. Daily moves beyond the VIX-implied 1-sd happened on 21% of days, against 32% if VIX were fairly priced. A plain option buyer pays for about 35–40% more movement than usually happens.
5. **Nifty's gains have come overnight, not during the session.** From 2015 to today, the cumulative close-to-open return is +310% (log) and the open-to-close return is −211%. Only 46.7% of days close above their open. Buying calls at 9:20 and holding to 3:15 has been a headwind trade on average.
6. **Global cues explain the gap and nothing after it.**
   - The previous US session correlates 0.47 with the Nifty opening gap.
   - It correlates −0.03 with the Nifty open-to-close move.
   - GIFT Nifty tells you how the day starts. It tells you nothing about how the day goes.
7. **Simple chart patterns mostly fail honest testing.** A 2026 walk-forward study of 14 retail intraday signal families (ORB, gap fill, volume spikes, news drift and others) on Nasdaq micro futures found none that survived costs. The ones that passed combined a *regime classifier* with a longer hold (60–75 minutes). Published ORB results shrink sharply once slippage is added: one independent replication fell from a Sharpe of 1.06 to 0.23.
8. **What survives the evidence** is a narrow set of ideas:
   - a regime-aware intraday breakout (trade only when price leaves its normal noise band)
   - the volatility risk premium, used through structure choice
   - a few options-market positioning signals
   - strict trade selection: many no-trade days, high-conviction days only
9. **My recommendation:** build a *signal-and-alert* system, not an auto-trader, for the first phase. For each day it outputs:
   - bias (bullish, bearish or no trade)
   - a calibrated probability
   - entry, target and stop on Nifty spot
   - the option strike
   - the premium-level target and stop
   - a structure choice: buy a CALL/PUT, use a spread, or stand aside, depending on whether options are cheap or expensive that day

   You place the orders. Then test it on paper for 8–12 weeks before any money goes in.

---

## 2. Where things stand today (close of Monday 5 October 2026)

| Item | Level | Source |
|---|---|---|
| Nifty 50 | 22,555.75 (+0.60%), first up day after four losses | Business Standard, Yahoo |
| Bank Nifty | 54,714.10 (+0.48%) | same |
| India VIX | 14.67–14.77 (the two sources differ slightly) | Business Standard, Yahoo |
| Nifty vs moving averages | below the 20-DMA (23,203), 50-DMA (23,844) and 200-DMA (24,340) | own calculation |
| RSI(14), ATR(14) | 28.2 (oversold), 243 points | own calculation |
| 20-day realized volatility | 10.8% (VIX about 4 points above it, so options are priced rich) | own calculation |
| 2026 so far | −13.7%. Peak 26,329 on 2 Jan. Low 22,331 on 30 Mar. | own calculation |
| Nifty P/E | 19.3 (long-run average about 20) | Stockpil |
| FII / DII cash | −₹4,699 cr / +₹5,182 cr | Stockpil |
| FII index futures | net short for 333 straight sessions to September, long ratio about 11%, a record | Marketcalls |
| Brent, USD/INR, US 10-year | about $101–102, 96.3, 5.30% | Stockpil, Yahoo |
| VIX-implied move | about ±210 points for one day, about ±460 points for one week | own calculation |

Background: Nifty fell about 14% from January to March 2026. The causes were the US–Iran conflict, an oil spike, the rupee sliding past 95, and heavy FII selling (₹1.14 lakh crore in March alone). It has not recovered.

**Events this week:**
- Nifty weekly expiry: **Tuesday 6 October**
- RBI policy decision: **Wednesday 7 October at 10:00 AM**. The repo rate is 5.25%. In a Reuters poll, 35 of 61 economists expect a hike to 5.50%.

Under the rules proposed below, Wednesday would be flagged as an event day: no new positions until the announcement is out and the first 30 minutes after it have settled.

---

## 3. The evidence, strategy by strategy

Grades:
- **A**: peer-reviewed, India-specific, survives costs
- **B**: peer-reviewed or a solid replication, but not Indian or not cost-tested
- **C**: practitioner backtest
- **D**: anecdote

Details and citations are in `research_notes/02` and `03`.

| Strategy or signal | Grade | What the evidence says | Use in our system |
|---|---|---|---|
| Selling options (volatility risk premium) | A/B | Real in Nifty options. Garg & Vipul (2015) find it mostly disappears after normal costs. Bhat et al. (2024) find it is earned *overnight*, while intraday short-option returns are flat to negative. Our data: VIX above realized volatility on 80.5% of days. | Decides *structure*. When IV is rich, express a directional view with a credit spread. A standalone non-directional selling module can come later. |
| Intraday noise-band breakout (Zarattini, Aziz & Barbon 2024) | B, needs an Indian test | SPY 2007–2024: Sharpe 1.33, hit rate about 43%, better when VIX is high. Independent replications find that slippage cuts the edge heavily. | Main *intraday entry* candidate. Re-test on Nifty futures with Indian costs. |
| Opening range breakout, plain | B, mostly negative | Unfiltered ORB on US stocks lost to the index. The edge came from a volume filter. On QQQ, the edge was concentrated in 2022. It failed walk-forward on MNQ futures. | Don't use alone. At most, a feature. |
| First half-hour predicts last half-hour (Gao et al. 2018) | B | R² of 1.6% on SPY. Present in 12 of 16 markets. Stronger on volatile and news days. | Test on Nifty. Use as a late-day tilt or filter. |
| Regime classification (Gaussian mixture / hidden Markov model) | B | The only signals that passed the 2026 MNQ falsification study were regime-based, with out-of-sample t-statistics of 3.1 to 4.3. | The backbone: decide *whether today is a trend day or a chop day* before choosing a direction. |
| Trend filter (price vs 50-DMA) | B, plus our data | Our data: P(5-day forward up) is 57.4% above the 50-DMA and 54.8% below it, and moves are 54% larger below it. In-sample edges from moving averages on Nifty rarely hold out of sample. | A bias and size modifier, not an entry signal. |
| Option order-flow imbalance in the first 10 minutes | B (Korea) | Predicted the rest-of-day index return, profitable after costs, driven by institutions (Kang et al. 2021). | Strong candidate. Needs a live option-chain websocket. |
| OI-based PCR, strike OI walls | B/C | PCR on volume has no predictive power. PCR on OI has some. OI walls are untested heuristics. | PCR-OI changes as a confluence feature. OI walls as target and stop *levels*. |
| FII participant-wise futures positioning | C | Short streaks are mostly hedges and not bearish on their own. Flips back to net long were followed by gains over 30 sessions more than 90% of the time (small sample). | A slow regime feature, plus a "flip" event. |
| FII/DII cash flows | B, negative | Flows follow returns rather than lead them. | Context only. |
| GIFT Nifty and US cues | A (our data) | Explain the gap (correlation 0.47). Zero information about the session (correlation −0.03). | Opening context only. Avoid trades that fight a large gap in the first 15 minutes. |
| Gap behaviour | Our data | Gaps above 0.5% fade slightly. Gap-downs close above the open 53.8% of the time. | A small mean-reversion feature. |
| News sentiment (FinBERT/LLM) | C for the index | Studies on Nifty show marginal improvements at best. Labelling accuracy does not mean return predictability. | A shock filter and a small tilt. Not a main signal. |
| Index fundamentals (P/E, earnings, macro) | B for long horizons only | Valuation predicts multi-year returns, not next week's. | A weekly bias prior and position-size modifier (crude, rupee, US yields, RBI, FII trend). |
| Machine-learning direction models | B | Honest out-of-sample daily index accuracy is about 52–58%. Much higher reported figures usually come from leakage. Accuracy rises when the model is confident, but the sample shrinks fast. | Use for *confidence calibration and trade selection* on top of rule-based signals (meta-labelling), not as a black box that picks direction. |
| Popular retail algos (9:20 short straddle and similar) | C/D | Backtests on vendor platforms look good in calm regimes and suffer large drawdowns when volatility spikes. The academic evidence says intraday short-option returns are not significant. | Not part of phase 1. |

---

## 4. What a 55% hit rate means once options are involved

The hit rate you need depends on the ratio between your average win and your average loss, plus costs (c, measured in units of the average loss):

breakeven hit rate = (1 + c) / (W/L + 1)

| Average win / average loss | Costs = 0.1 of a loss | Breakeven hit rate |
|---|---|---|
| 0.5 (small targets, wide stops) | 0.1 | 73% |
| 1.0 | 0.1 | 55% |
| 1.5 | 0.1 | 44% |
| 2.0 | 0.1 | 37% |

So a 55% hit rate with 1:1 payoffs only breaks even. The published intraday breakout strategies win only 24–43% of the time and make money because the winners are 2–3 times the losers.

Three things push an option buyer's payoff ratio down even when the direction call is right:
- **Theta.** Losses grow toward expiry, and Tuesday expiry options lose value fastest.
- **Overpriced implied volatility**, measured above.
- **Costs.** One lot of 65 at a ₹150 premium costs roughly ₹70 in brokerage, STT, exchange charges and GST per round trip, plus 1–2 points of slippage on each side. That is about 1.5–2% of the premium. Check the exact figure on your broker's calculator.

The system therefore has to predict the *size* of the move and the *time it takes*, not only its sign.

---

## 5. The system I would build

### 5.1 Layers

```
DATA         broker websocket (Nifty spot, futures, full weekly option chain)
             NSE end-of-day: F&O bhavcopy, participant-wise OI, FII/DII
             global: GIFT Nifty, S&P/Nasdaq futures, Brent, USD/INR, US 10-year
             news: RSS headlines → LLM classifier
             calendar: RBI, FOMC, US CPI, Budget, expiry days, results of the top-10 Nifty weights

REGIME       volatility regime (VIX level, VIX minus realized vol, VIX change)
(before      trend regime (20/50/200-DMA, ADX, GMM/HMM day-type classifier)
 9:45 AM)    event flag (event day → no trade or half size)
             weekly fundamental prior (crude, rupee, yields, FII futures trend, valuation)

SIGNALS      noise-band breakout on Nifty futures, checked at :15/:45 marks, VWAP trail
(intraday)   first-30-min return (late-day tilt)
             option-chain order imbalance and OI-PCR change in the first 15 minutes
             gap context, OI walls for levels

DECISION     primary rule gives the side (long/short)
             meta-model gives P(target is hit before stop within the time limit)
             trade only if expectancy after costs > 0 and P ≥ threshold

STRUCTURE    IV cheap (VIX ≤ realized): buy ATM or 1-ITM CALL/PUT, or a debit spread
             IV rich (VIX ≫ realized): credit spread in the forecast direction
             expiry day after 1:30 PM: no new long-option entries
             nothing short held into the 3:15–3:35 closing auction

OUTPUT       alert: spot price, bias, probability, spot target, spot stop,
             strike, premium entry, premium target, premium stop, exit time,
             and the reason (which signals agreed)

JOURNAL      every signal logged, taken or not, with the outcome, for calibration checks
```

### 5.2 How the price, target and stop are set

The target and stop are defined on Nifty spot or futures first, then translated into premium. This keeps them tied to the market rather than to the option's noise.

- **Stop:** the far side of the noise band or VWAP, whichever is tighter, with a cap of about 0.5 × the VIX-implied daily move. Today that cap would be about 105 points.
- **Target:** about 1–1.5 × the daily implied move, cut back to the nearest large OI wall if one sits in the way.
- **Time stop:** exit by 3:00 PM on normal days and by 1:30 PM on expiry days for long options.
- **Premium translation:** premium change ≈ delta × move + ½ × gamma × move² − theta × hours held. Greeks come from Black-76 using the live futures price and IV.

### 5.3 Strike rules

- When **buying**, use the ATM strike or one strike in the money (delta 0.5–0.65) on the current weekly.
  - Strikes below delta 0.25 are lottery tickets. SEBI's loss data is dominated by them.
  - From Monday afternoon, consider the next week's expiry instead of the Tuesday contract, so that theta and gamma don't decide the trade.
- For **debit spreads**, buy ATM and sell a strike near the 1-sd implied move.
- For **credit spreads**, sell around delta 0.30 and buy protection 1–2 strikes further out. Stay defined-risk only.

### 5.4 Confidence

The model labels every historical setup with three barriers (target, stop, time limit), following López de Prado's triple-barrier method. A model then learns P(target first).

- The probability is calibrated: when it says 60%, about 60% of those trades should hit the target. We check this with reliability plots on out-of-sample data.
- That calibrated number is the "confidence" shown in the alert.

---

## 6. Risk rules (fixed before any testing, not tuned)

- Risk per trade: at most 1% of trading capital at the stop.
- At most 2 trades per day. Stop for the day after −2%, for the week after −4%. At −8% in a month, pause and review.
- No averaging down. After a losing trade there is a 30-minute cool-off.
- No naked short options. No short-gamma position held into the closing auction on expiry.
- Event days (RBI, FOMC, US CPI, Budget, elections) and VIX jumps of more than 15% in a day: no trade or half size.
- SEBI's data shows loss rates rising with turnover. The system is allowed, and expected, to say "no trade" on most days.

---

## 7. How we find out whether it works before money goes in

1. **Data.** At least 2019–2026 of 1-minute Nifty futures data and the weekly option chain. Use the lot size, expiry weekday and STT rate in force *on each historical date* (Thursday → Tuesday in September 2025, STT 0.0625% → 0.10% → 0.15%).
2. **Splits.**
   - Develop on 2019–2023.
   - Validate on 2024–2025.
   - Keep **2026 untouched** until the end. It is a war-and-high-rates regime, a good stress test.
3. **Walk-forward only,** with purged and embargoed folds. Every rule or parameter tried gets recorded. We report a deflated Sharpe ratio and the probability of backtest overfitting (Bailey & López de Prado).
4. **Pass bar:**
   - out-of-sample t-statistic ≥ 2 on net returns
   - at least 30 trades per fold
   - positive after full Indian costs
   - the same sign in each test year
   - a permutation test
5. **Paper trading** for 8–12 weeks, at least 40 signals, using live alerts.
6. **Live with 1 lot.** If live results fall below the 5th percentile of the backtest distribution, the system stops itself.

---

## 8. What to expect, stated plainly

- A realistic good outcome:
  - 52–58% directional accuracy on the days it trades
  - fewer trades than you take now
  - a positive expectancy built from payoff asymmetry and from not trading bad days
  - profit measured monthly, not daily
- Drawdowns of 10–20% of trading capital can happen even with a real edge. The first quarter of 2026 is the kind of regime that produces them.
- There is a fair chance that one or more of these signals shows no edge on Nifty after costs. The validation plan is designed to find that out on paper rather than with money.
- "Meaningful profit every day" is not something any of the evidence supports. The people who do make money here are mostly prop firms and FPIs running algorithms: ₹44,000 crore and ₹14,000 crore gross in FY26, almost all from algorithmic entities. They make it from scale, cost advantages and spreads, not from daily calls.

---

## 9. Decisions needed from you before the design phase

1. **Broker and data.**
   - Which broker account do you have?
     - Upstox, Dhan, Fyers and Angel One give free live data APIs.
     - Zerodha needs Kite Connect at ₹500/month.
   - For backtesting, we need 1-minute historical *option* data. One paid source (GDFL, TrueData or a backtest platform) is the cleanest way to get it.
2. **Holding period.**
   - Intraday only (squared off the same day)?
   - Or also 1–3 day swings into the Tuesday expiry?
   - The evidence favours avoiding intraday short options and avoiding long options held through expiry-day afternoons.
3. **Structure.** Are you open to spreads when options are expensive, or do you want naked CALL/PUT buying only? With buying only, the system will trade less often.
4. **Capital and risk.** The trading capital amount sets the lot count and the 1% rule.
5. **Where alerts go.** Terminal, a web dashboard, or Telegram. The Telegram plugin here failed to connect today and would need fixing.

---

## Sources

Regulation and market structure:
- [SEBI study, Aug 2026 (PDF)](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [NSE lot-size circular](https://nsearchives.nseindia.com/content/circulars/FAOP70616.pdf)
- [HDFC Sky on lot sizes](https://hdfcsky.com/news/nse-revises-market-lot-sizes-for-major-index-derivatives-effective-january-2026)
- [ICICI Direct on STT](https://www.icicidirect.com/futures-and-options/articles/stt-changes-in-budget-2026-what-f-o-traders-need-to-know)
- [MarketsEasy on the closing auction](https://marketseasy.in/blog/sebi-expiry-settlement-price-cas-review-2026)
- [Zerodha on SEBI index-derivative rules](https://zerodha.com/z-connect/business-updates/sebis-new-rules-for-index-derivatives-heres-whats-changing)
- [SEBI algo framework (Zerodha)](https://inthemoneybyzerodha.substack.com/p/sebi-algo-trading-changes-april-2026)
- [Oxford Business Law Blog on Jane Street](https://blogs.law.ox.ac.uk/oblb/blog-post/2025/07/jane-street-and-expiry-day-trap-unpacking-sebis-crackdown-algorithmic)

Peer-reviewed papers:
- [Garg & Vipul (2015), JFM](https://doi.org/10.1002/fut.21680)
- [Bhat, Pandey & Nageswara Rao (2024), JFM](https://doi.org/10.1002/fut.22512)
- [Kang, Kang & Lee (2021), JFM](https://doi.org/10.1002/fut.22301)
- [Seo, Byun & Kim (2020), JFM](https://doi.org/10.1002/fut.22095)
- [Patnaik, Shah & Singh (2013), International Finance](https://doi.org/10.1111/j.1468-2362.2013.12032.x)
- [Gao, Han, Li & Zhou (2018), JFE](https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/ee7dac49-530b-4950-b5d0-e0b5eee08f2e.pdf)
- [NSE Working Paper 9/2013 on India VIX](https://nsearchives.nseindia.com/research/content/res_WorkingPaper9.pdf)
- [PCR causality study (MDPI)](https://www.mdpi.com/2227-7099/7/1/24)

Intraday strategies and replications:
- [Zarattini & Aziz, ORB (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622)
- [Zarattini, Barbon & Aziz (SSRN)](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284)
- [Zarattini, Aziz & Barbon, "Beat the Market"](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)
- [ORB replication](https://github.com/giovannibrusco/zarattini-2023-orb-qqq)
- [Mesfin (2026), arXiv 2605.04004](https://www.alphaxiv.org/abs/2605.04004)

Prediction, overfitting and sentiment:
- [Chen (2026), arXiv 2608.26106](https://www.alphaxiv.org/abs/2608.26106)
- [Dasgupta et al. (2024), arXiv 2412.06794](https://www.alphaxiv.org/abs/2412.06794)
- [Leakage-safe evaluation, arXiv 2608.27734](https://www.alphaxiv.org/abs/2608.27734)

Positioning, brokers and live data:
- [Marketcalls on FII shorts](https://www.marketcalls.in/futures-and-options/what-do-we-actually-know-about-fii-index-futures-shorts.html)
- [AlgoTest broker comparison](https://algotest.in/blog/best-brokers-for-algo-trading-in-india/)
- [Business Standard, 5 Oct 2026](https://www.business-standard.com/amp/markets/news/stock-market-live-october-5-nse-bse-sensex-today-nifty50-gift-nifty-crude-oil-prices-snapdeal-listing-today-rvnl-share-price-today-ipo-today-126100500057_1.html)
- [Stockpil, 5 Oct 2026](https://stockpil.com/india-markets-today-2026-10-05)
- [Business Standard on the RBI MPC](https://www.business-standard.com/amp/economy/news/rbi-s-panel-starts-monetary-policy-deliberations-0-25-bps-rate-hike-likely-126100500635_1.html)
- [mStock on the March 2026 crash](https://www.mstock.com/articles/decoding-stock-market-crash-on-23-march-2026)
