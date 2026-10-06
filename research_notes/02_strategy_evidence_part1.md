# 02. Strategy evidence, part 1: option selling, intraday momentum, ORB, ML accuracy

Evidence grades used throughout:
- **A**: peer-reviewed, India-specific, survives costs
- **B**: peer-reviewed or strong replication, but not India or not cost-tested
- **C**: practitioner backtest or blog
- **D**: anecdote or marketing

---

## 1. Selling options / the volatility risk premium (VRP)

**What it is:** implied volatility is, on average, higher than the volatility that later happens. Option sellers collect that gap as payment for taking crash risk.

**India evidence (grade A/B)**
- **Garg & Vipul (2015), J. Futures Markets 35(9):795–812**, DOI [10.1002/fut.21680](https://doi.org/10.1002/fut.21680). Nifty ATM options, 2009–2011. All short option strategies (naked, straddle, delta-hedged) had significant positive returns *before* costs. **Most of the profit disappears after normal transaction costs.** Only "option writers who have sufficiently low transaction costs" benefit. The VRP follows an AR(3) process, so it is partly forecastable.
- **Bhat, Pandey & Nageswara Rao (2024), J. Futures Markets 44(8):1320–1337**, DOI [10.1002/fut.22512](https://doi.org/10.1002/fut.22512). Nifty near-month options, 2017–2020.
  - **Overnight short-option returns are positive and highly significant.** Intraday (open-to-close) short-option returns are "largely negative and insignificant".
  - The VRP is "mainly a reward for overnight risk".
  - After noon, short **calls** have significantly *negative* returns and short **puts** positive returns.
  - The overnight selling strategy is **not profitable after explicit and implicit costs**.
  - Implication: the popular retail "sell a straddle at 9:20, exit at 3:15" is *not* supported by this academic evidence (but note the sample period predates weekly-expiry dominance).
- **Simon (2010), JFM**: front-month straddle and strangle selling was profitable after costs (TLT options, US). It worked better when implied volatility was high *relative to* forecast realized volatility. **Stop-losses reduced profitability. Take-profits helped only modestly.**

**Global (grade B)**
- [Sizing the Risk: Kelly, VIX and hybrid sizing in put-writing (arXiv 2508.16598)](https://www.alphaxiv.org/abs/2508.16598). Position sizing is what decides whether index put-writing survives over the long run.
- 0DTE studies: retail 0DTE buyers lose systematically, and market makers earn the spread.

**Verdict:** a **real, documented premium that is thin after Indian costs** and has crash (fat-tail) risk. It can be harvested only with:
- low costs
- conditioning on IV > forecast realized volatility (IV-RV spread)
- defined risk (spreads or iron condors, not naked)
- strict sizing

The edge is **not** directional, so it does not fit a "CALL or PUT" prediction framing. Keep it as a *separate, second module* for later.

---

## 2. Intraday momentum (first half-hour return predicts last half-hour)

- **Gao, Han, Li & Zhou (2018), J. Financial Economics 129(2):394–414**, "Market intraday momentum". SPY 1993–2013. The first half-hour return (measured from the previous close) predicts the last half-hour return. Slope 6.94, **R² 1.6%**. Stronger on high-volatility days, recession days and macro-news days. Found in **12 of 16 international markets**. [paper](https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/ee7dac49-530b-4950-b5d0-e0b5eee08f2e.pdf), [Alpha Architect summary](https://alphaarchitect.com/attention-prop-traders-the-first-half-hour-of-trading-predicts-the-last-half-hour/)
- Mechanism: dealer gamma hedging and late-informed traders. With 59% of Nifty option turnover happening on expiry day, **dealer-gamma effects should be strong in India**, which makes this a plausible candidate. (There is an Indian paper, "Hedging Demand and Intraday Momentum within the Indian Stock Market" ([ResearchGate](https://www.researchgate.net/publication/383567351_Hedging_Demand_and_Intraday_Momentum_within_the_Indian_Stock_Market)), but I could not access it. **Re-test it ourselves.**)
- Kang, Kang & Lee (2021), JFM, Korea: *intraday momentum was insignificant there*, but **option order imbalance in the first 10 minutes predicted the rest-of-day index return, profitable after costs**, driven by institutions. This idea maps directly onto Nifty option-chain flow.

**Verdict:** grade B globally, untested by us for Nifty. The R² is tiny, so it works only as a **filter or tilt**, not a standalone signal. Worth testing: the first 30-minute return (from previous close) → direction of the last 60–90 minutes on Nifty futures.

---

## 3. Opening Range Breakout (ORB) and the "noise area" breakout

- **Zarattini & Aziz (2023), SSRN 4416622**: 5-min ORB on QQQ, 2016–Feb 2023. 33% annualized alpha, Sharpe about 1.1, **win rate only 24%** (returns come from rare big winners), with leverage. [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416622)
- **Zarattini, Barbon & Aziz (2024), SSRN 4729284**: ORB on US "Stocks in Play". **Unfiltered ORB made only 29% total and lost to the index.** The edge came from the *relative-volume filter*, not from the breakout itself.
- **Zarattini, Aziz & Barbon (2024), "Beat the Market", SPY**: "noise area" = open ± the 14-day average absolute move-from-open at each minute (gap-adjusted). Signals are checked only on the half-hour (10:00, 10:30, …). VWAP is used as a trailing stop. Flat at the close. Position sized by volatility targeting. Results 2007–2024: 19.6% CAGR, **Sharpe 1.33**, **hit rate about 43%**, works better when VIX > 20. [paper PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download), [review](https://quantmacro.substack.com/p/paper-review-an-effective-intraday)
- **Independent replications are much less rosy (grade B, negative):**
  - [QQQ ORB replication](https://github.com/giovannibrusco/zarattini-2023-orb-qqq): gross Sharpe 1.06. **With 2¢ entry and 4¢ stop slippage, Sharpe falls to 0.23.** Break-even slippage is about 2.2¢ per share. **76% of filtered P&L came from 2022 alone.**
  - [Mesfin (2026) falsification study on MNQ futures (arXiv 2605.04004)](https://www.alphaxiv.org/abs/2605.04004): 14 retail-style intraday OHLCV signal families (ORB, gap fill, volume spikes, news drift and others) tested walk-forward with realistic friction. **None passed.** 11 of 14 had gross edge below the cost of trading. The ORB long with a 75-minute hold had T = 0.88 (not significant). Only regime-classifier signals (Gaussian mixture model regimes with a 60–75-minute hold) passed, with OOS T of 3.1 to 4.3. **Lesson: simple chart patterns are arbitraged away; regime context plus a longer hold is where the remaining edge sits.**

**Verdict:** the breakout *concept* (trade only when price leaves the normal-noise zone, and stay out otherwise) is the most promising intraday directional framework. It needs to be:
1. **re-tested on Nifty futures** with Indian costs
2. used with **defined-risk option structures** rather than leveraged futures, *or* with ITM options (delta ≥ 0.6) to limit theta drag
3. expected to have **win rates of 25–45%**. The edge comes from payoff asymmetry, **not** from a 55%+ hit rate.

---

## 4. How accurate can ML direction prediction honestly be?

- **Realistic daily-direction accuracy for an index is about 52–58% out-of-sample.** Anything above 65% on daily index direction is almost always leakage or overfitting.
- Teaching example: [Chen (2026), arXiv 2608.26106](https://www.alphaxiv.org/abs/2608.26106). SPY 1993–2024, walk-forward. XGBoost got 58.45% (CI 54.9–62.1) and logistic regression got "71%". **But the target was "close vs previous close" after already seeing today's open.** The overnight gap is already known at that point, which inflates "accuracy" without giving any tradable edge, because you cannot buy at yesterday's close. **We must define targets from the entry price we can actually get.**
- In the same paper, accuracy rises with predicted move size: 58% overall, **73% when |predicted move| > 1%, but only 154 of 799 days qualify**. That supports a **"trade only when conviction is high"** design (confidence gating).
- [What survives honest evaluation? Leakage-safe, search-aware assessment (arXiv 2608.27734)](https://www.alphaxiv.org/abs/2608.27734) and [When Alpha Disappears: decision-time leakage (arXiv 2605.23959)](https://www.alphaxiv.org/abs/2605.23959) are 2026 papers showing how many reported edges disappear once search bias and decision-time leakage are removed.
- **Bailey, Borwein, López de Prado & Zhu (2017)**, "The probability of backtest overfitting", J. Computational Finance 20(4). **Bailey & López de Prado (2014)**, "The deflated Sharpe ratio", JPM 40(5). These are our validation standards.

## 5. News sentiment for Nifty

- [Dasgupta et al. (2024), arXiv 2412.06794](https://www.alphaxiv.org/abs/2412.06794). About 400k Economic Times articles, 2021–2024. Topic-wise sentiment (VADER for articles, DistilBERT for headlines) improved next-day Nifty *level* RMSE only marginally (about 134.9 → 128.7 points). Market and politics news mattered most. **This is weak evidence.** Predicting the level RMSE is not the same as having a tradable direction edge.
- [Adaptive sentiment for NIFTY 50 via LLM + RAG + RL (arXiv 2512.20082)](https://www.alphaxiv.org/abs/2512.20082) and the [NIFTY Financial News Headlines dataset (arXiv 2405.09747)](https://www.alphaxiv.org/abs/2405.09747) are useful datasets and architectures.
- [From sentiment classification to return predictability: QLoRA LLM benchmark (arXiv 2608.04200)](https://www.alphaxiv.org/abs/2608.04200). **Good sentiment-labelling accuracy ≠ return predictability.**

**Verdict:** for an *index*, news sentiment is best used as a **risk / regime filter**:
- event days
- shock detection
- "stand aside" on very negative surprise news
- a small tilt

It should not be the main directional engine. For macro-driven index moves, global cues (US futures, crude, USD/INR, US yields) usually carry more information than Indian headline sentiment.
