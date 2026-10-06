# Intraday technical, microstructure, volatility and regime signals for Nifty / Sensex (15-min to end-of-day)

Scope: which price, volume, order-book and regime signals have out-of-sample, after-cost predictive value at 15-minute-to-close horizons on an equity index, and how to build them from 1-minute bars plus live ticks with 5-level depth (Angel One SmartAPI). Facts already established in `02_strategy_evidence_part1.md` (Gao et al. 2018, Zarattini ORB and noise-area results, the Brusco ORB replication, Mesfin's headline result, Kang et al. option order imbalance) and in `04_nifty_measured_facts.md` (overnight vs intraday drift, gap behaviour, VIX vs realized) are referenced, not re-derived.

Evidence grades: **A** = peer-reviewed + India + survives costs; **B** = peer-reviewed or strong replication, but not India or not cost-tested; **C** = practitioner backtest or unrefereed preprint; **D** = anecdote. Volatility-forecasting results have no "after cost" dimension; they are graded B even when India-specific, and marked "(India)".

Headline: **no signal in this note reaches grade A.** India-specific peer-reviewed evidence exists only for (i) order-imbalance predictability at under 30 minutes in NSE stocks, (ii) intraday volatility periodicity and expiry-day effects, and (iii) volatility-forecast quality (range-based and RV-based beat implied). Every directional intraday signal (noise band, intraday momentum, gamma conditioning, opening order imbalance) is grade B from other markets and has to be re-tested on Nifty and Sensex.

---

## 1. Order-flow imbalance (OFI): predictive power at 1–15 minutes, decay, and use by a 15-minute retail system

### Takeaway
OFI explains *contemporaneous* index and stock price changes very well (out-of-sample R² about 65% for best-level OFI and about 82–84% for 5–10-level integrated OFI). Its power to *forecast* the next minute is close to zero (OOS R² is negative at one minute ahead) and decays within seconds to a few minutes. In India the forecastable part lasts about 5 minutes and is gone within 30 minutes. Raw OFI is therefore **not usable as a standalone direction signal on a 15-minute check cycle.** It is usable only as (a) an at-the-moment confirmation or veto of an entry, or (b) aggregated *opening* option-order imbalance (first 10–15 minutes), which has a rest-of-day horizon and survived costs in Korea.

### Cited Findings
- **Definition (Cont, Kukanov & Stoikov 2014, JFEc 12(1):47–88).** OFI is the net of bid-side and ask-side order-flow changes at the best quotes. Price change is linear in OFI with slope roughly 1/(2 × depth), so the same imbalance moves price more when the book is thin. — [Takahashi (2025), arXiv 2508.06788, summarising Cont et al.](https://arxiv.org/abs/2508.06788)
- **Event formula used in practice** (best-level). For consecutive book states n−1 → n, with bid price/size P^b, q^b and ask P^a, q^a:
  e_n = q^b_n·1{P^b_n ≥ P^b_{n−1}} − q^b_{n−1}·1{P^b_n ≤ P^b_{n−1}} − q^a_n·1{P^a_n ≤ P^a_{n−1}} + q^a_{n−1}·1{P^a_n ≥ P^a_{n−1}}.
  OFI over an interval is the sum of e_n. — [Takahashi (2025)](https://arxiv.org/abs/2508.06788)
- **Multi-level and integrated OFI (Cont, Cucuringu & Zhang 2023, top-100 S&P 500 stocks, 2017–2019, Nasdaq ITCH).**
  - Level-m order flow: OF^{m,b} = +q^{m,b}_n if the bid price rose, q^{m,b}_n − q^{m,b}_{n−1} if unchanged, −q^{m,b}_n if it fell. The ask side is mirrored.
  - OFI^m = Σ(OF^{m,b} − OF^{m,a}), scaled by the average depth over the first M levels.
  - Integrated OFI = first principal component of the level OFIs, l1-normalised. The first PC explains more than 89% of multi-level OFI variance.
  — [Cont, Cucuringu & Zhang, arXiv 2112.13213](https://arxiv.org/abs/2112.13213)
- **Contemporaneous fit (same source).** 1-minute returns regressed on same-minute OFI inside 30-minute windows, with the first and last 30 minutes of the session excluded:
  - Best-level OFI: in-sample R² 71.16%, out-of-sample R² 64.64%.
  - Integrated OFI: in-sample 87.14%, out-of-sample 83.83%.
  - OOS R² by number of levels: 1 level 64.64%, 2 levels 75.81%, 3 levels 79.47%, **5 levels 82.05%**, peaking at 8 levels (83.16%).
  - A simple average across levels is nearly as good as PCA weights (OOS 82.34% vs 83.83%).
  — [Cont, Cucuringu & Zhang](https://arxiv.org/abs/2112.13213)
- **Forecasting (same source).** For **one-minute-ahead** returns, the OOS R² of lagged own OFI is −0.37% (best-level) and −0.36% (integrated). Cross-asset lagged OFI improves this only to −0.10%. Lagged cross-impact "decays rapidly in time". The authors argue forecast-based strategies still show economic gains, but the excerpt reports no cost-adjusted figures. — [Cont, Cucuringu & Zhang](https://arxiv.org/abs/2112.13213)
- **Decay in index futures (S&P 500 E-mini, 2008–2013, 1-second best-bid/offer data, SVAR).**
  - Impulse responses of returns to flow shocks "dissipate almost entirely within a second".
  - Around macro announcements, price impact rises while flow volatility falls just before the release, i.e. liquidity withdraws.
  - A 1,000-contract flow shock moves price about 1.42 bp in the long run.
  — [Takahashi (2025)](https://arxiv.org/abs/2508.06788)
- **Lagged OFI at 15 minutes (Chinese soybean-meal futures).**
  - Contemporaneous: at 10-second sampling within 15-minute windows, OFI is significant in 97.9% of subsamples with R² 46.5%. When OFI and trade imbalance (TI) enter together, OFI stays significant in 93.8% of subsamples and TI in only 31.4%.
  - Lagged one period: OFI coefficients are significant in only 29.7% of 15-minute subsamples, with average R² 2.38% (27.0% and 1.26% at the 1-minute/1-day setting).
  — [Jin, Kearney, Li & Yang (2021), IJFE 28(1):606–625](https://onlinelibrary.wiley.com/doi/10.1002/ijfe.2439)
- **India (NSE, 195 most active stocks; Tripathi, Dixit & Vipul 2021, Finance Research Letters 41:101863).** Order imbalance predicts short-term returns once bid-ask bounce is controlled. **Predictability is strong for the first five minutes and perishes within thirty minutes.** Order-flow information also shows up in deeper levels of the limit order book, which points to informed traders beyond the best quotes. Grade B: India, but no cost test. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S1544612320316779); [EconBiz record](https://www.econbiz.de/Record/information-content-of-order-imbalance-in-an-order-driven-market-indian-evidence-tripathi-abhinava/10013336223)
- **Magnitudes are sub-basis-point (Chinese commodity futures, skilled-investor order imbalance per minute, Subrahmanyam, Tang, Wang & Yang 2024, JF 79(2)).** In-sample:
  - next-minute return: 0.341 bp (t = 12.4)
  - minutes 1–5: 0.420 bp
  - minutes 1–10: 0.499 bp

  These are statistically strong but economically tiny relative to option bid-ask spreads. — [JF](https://onlinelibrary.wiley.com/doi/10.1111/jofi.13316)
- **Opening order imbalance predicting the next day (first half-hour order imbalance, FOIB, sample 2005–2015).** FOIB predicts next-day market returns with Newey-West t = 2.447 and R² 0.33%. Whole-day order imbalance is insignificant (R² 0.08%, t = 1.05). — [Chu & Qiu (2020), IJFE 26(3)](https://onlinelibrary.wiley.com/doi/10.1002/ijfe.1960)
- **Option order imbalance at the open (Korea, KOSPI 200).** Option order imbalances in the **first 10 minutes** significantly predict index and index-futures returns for the rest of the day. Simple market-timing strategies are profitable **after transaction costs**. The effect is stronger under uncertainty and is driven by institutions rather than day traders. Plain intraday momentum is insignificant in that market. Grade B. — [Kang, Kang & Lee (2021), JFM 42(3):338–364](https://onlinelibrary.wiley.com/doi/10.1002/fut.22301)
- **Deep learning on OFI.** Models trained on OFI features outperform models trained on raw order-book states or returns across several short horizons (stock-level, horizons up to the short intraday range). — [Kolm, Turiel & Westray (2023), Mathematical Finance 33(4)](https://onlinelibrary.wiley.com/doi/10.1111/mafi.12413)
- **Timing fragility at bar resolution (practitioner, MNQ futures).**
  - Asia-session expansion bars: the directional move is fully consumed inside the signal bar, so a next-bar entry captures the reversal (T = −11.52).
  - For a regime signal on 15-minute bars, **a one-bar (15-minute) delay flips the out-of-sample T from +4.30 to −2.78.**

  Grade C. — [Mesfin (2026), arXiv 2605.04004](https://arxiv.org/abs/2605.04004)

### Inferences
- With 15-minute checks and manual or alert-driven execution, any edge with a 1–5-minute half-life (Tripathi et al.; Cont et al.) is already spent by the time an order is placed. OFI's only valid roles are:
  1. **Veto at the moment of the check:** for example, do not issue a long alert if the integrated 5-level OFI over the last 3–5 minutes is below −1 standard deviation for that time of day.
  2. **Liquidity/regime feature:** OFI volatility, depth, and the OFI-to-return slope (price impact) measure book thinness, which tells you when moves will be larger.
  3. **Aggregated opening flow:** sum option-order imbalance from 9:15 to 9:30 into a single rest-of-day tilt (Kang et al. design).
- SmartAPI streams depth **snapshots**, not order events. Snapshot-to-snapshot OFI (treating each snapshot pair as one "event" in the formula above) undercounts flow between snapshots. Cont-style R² should be expected to be lower, and the gap grows with the snapshot interval. Build it, but validate by measuring contemporaneous R² of 1-minute futures returns on snapshot-OFI. If R² < 40%, the feature is too noisy even for a veto.
- Five levels capture most of the multi-level gain (82% vs 64.6% OOS R² for 1 level in US stocks). Using all 5 SmartAPI levels with a simple average is a reasonable default. PCA weights add little.
- Nifty futures OFI, rather than spot, is the right input: the spot index has no book. For option-flow imbalance, trades must be signed with a quote or tick rule (LTP vs the prevailing best bid/ask from the snapshot). This is noisy for illiquid strikes, so restrict it to ATM ± 3 strikes.

### Gaps
- I found **no study of OFI on Nifty or Sensex index futures** at minute horizons, and no after-cost OFI strategy evidence for any Indian instrument.
- I could not find the effect sizes (R², hit rate) in Kang et al.'s Korea option-imbalance paper. Only the qualitative "profitable after costs" claim was available.
- SmartAPI's depth snapshot rate and timestamp precision are unknown to me. They need to be measured before OFI can be relied on.

---

## 2. Intraday momentum and reversal: replications, Baltussen gamma channel, India evidence, conditions

### Takeaway
"Market intraday momentum" (the day's return so far predicts the last 30 minutes) is robust across 60+ futures markets from 1974 to 2020, with R² of about 1.5–3.6%. It is concentrated on days when option dealers are **net short gamma** (R² 3.58% vs 0.05% when long gamma). It is stronger on high-volatility and high-volume days, and when the first-half-hour and rest-of-day returns agree. However:
- It **disappeared out-of-sample after publication for SPY** (Rosa 2022).
- It is **insignificant in Korea**.
- There is **no peer-reviewed India test**. The only India paper found is an unrefereed student study.

Reversals after large opening moves are real but conditional: no-news and scheduled-news jumps reverse, while unscheduled-news jumps continue. Fixed directional gap rules failed out-of-sample in the most careful practitioner test.

### Cited Findings
- **Baltussen, Da, Lammers & Martens (2021), JFE 142(1):377–403. Over 60 futures, 1974–2020, equity-index futures pooled.** Coefficients are ×100.
  - First half-hour incl. overnight (r_ONFH) → last half-hour (r_LH): β = 4.86 (t = 6.52), R² 1.49%, but **OOS R² −1.71%**.
  - **Rest-of-day return** (r_ROD = previous close → 30 minutes before close): β = 4.18 (t = 7.29), R² 2.45%, **OOS R² +2.88%**.
  - Adding the second-to-last half-hour: β_SLH = 9.08 (t = 4.82).

  — [Baltussen et al. PDF](https://academicweb.nd.edu/~zda/intramom.pdf); [RePEc](https://ideas.repec.org/a/eee/jfinec/v142y2021i1p377-403.html)
- **Sign agreement (same paper).** When r_ONFH and r_ROD have the **same sign**, r_ROD gives β = 4.26 (t = 7.19), R² 3.13%. When the signs **differ**, r_ONFH turns negative (β = −3.71, t = −2.76, a reversal) and r_ROD still predicts (β = 3.59, R² 0.80%). — [Baltussen et al.](https://academicweb.nd.edu/~zda/intramom.pdf)
- **Trading results, equity futures 1/N portfolio (same paper, no transaction costs):**

  | Strategy | Annual return | Volatility | Sharpe | Daily success |
  |---|---|---|---|---|
  | η(r_ROD): long/short last half-hour by sign of r_ROD | 6.86% | 3.96% | **1.73** | 55% |
  | η(r_ONFH) | 4.21% | 3.95% | 1.07 | 55% |
  | Trade only when both agree | 5.47% | 3.42% | 1.60 | **61%** |
  | Always long last half-hour | 0.44% | 4.20% | 0.11 | — |

  The authors state they "do not consider transaction costs". S&P 500 futures still give a positive net Sharpe at a one-tick cost. — [Baltussen et al.](https://academicweb.nd.edu/~zda/intramom.pdf)
- **Gamma channel (same paper).** Regress r_LH on r_ROD by sign of the previous day's net gamma exposure (NGE) of S&P 500 option dealers, 1996–2020:
  - NGE < 0: β = 6.63 (t = 4.78), R² **3.58%**
  - NGE ≥ 0: β = 0.82 (t = 1.03), R² **0.05%**

  NGE per option = Γ × OI × 100 × index level. Calls are assumed bought by dealers and puts sold by dealers. Last-half-hour predictability **reverts over the next days**, which is consistent with transitory hedging pressure. Grade B. — [Baltussen et al.](https://academicweb.nd.edu/~zda/intramom.pdf)
- **Post-publication out-of-sample (Rosa 2022, JFM 42(12):2218–2234, SPY).**
  - Splits the data into in-sample, post-sample and post-publication periods; **"the predictability disappears in the out-of-sample period."**
  - A Markov-switching model finds two regimes; predictability depends on signal strength.
  - **A strategy with thresholds beats an always-active one.**

  Grade B (negative). — [Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1002/fut.22375); [RePEc](https://ideas.repec.org/a/wly/jfutmk/v42y2022i12p2218-2234.html)
- **Other replications.**
  - Zhang et al. (2019): China stocks. Jin et al. (2020): Chinese commodities. Ho et al. (2022): Australia. Wen et al. (2019): crude oil.
  - Li et al. (2022): 16 developed equity markets, "significant in most countries".

  — summarised in [Rosa (2022) introduction](https://onlinelibrary.wiley.com/doi/abs/10.1002/fut.22375)
  - Liu & Tse (2017): S&P ETFs and 12 international index futures. The first half-hour is **not** predictive, but the overnight return predicts the last half-hour.
  - Elaut, Frömmel & Lampaert (2018): the first half-hour predicts the last half-hour in RUB/USD.

  — summarised in [Jin, Kearney, Li & Yang (2019), JFM 40(4):632–650](https://onlinelibrary.wiley.com/doi/10.1002/fut.22084)
- **Chinese commodity futures (copper, steel, soybean, soybean meal).** The first half-hour positively predicts the last half-hour in all four. In metals, **first sessions with high volume or volatility give the strongest momentum.** An informed timing strategy beats always-long and buy-and-hold. — [Jin et al. (2019)](https://onlinelibrary.wiley.com/doi/10.1002/fut.22084)
- **Bitcoin (Shen, Urquhart & Wang 2022, Financial Review 57(2)).**
  - Slope 0.968 (NW t = 4.38), R² 1.44%.
  - Adding the second-to-last half-hour (which has a *negative* coefficient) raises R² to 2.12%.
  - R² is 1.89–3.19% when the first half-hour is positive vs 0.11–0.89% when negative.
  - The effect is stronger with high first-session volume and volatility.
  - Timing strategy: Sharpe 1.15 with both signals.

  — [Financial Review](https://onlinelibrary.wiley.com/doi/10.1111/fire.12290)
- **Korea: intraday momentum insignificant**, while opening option order imbalance works after costs. — [Kang, Kang & Lee (2021)](https://onlinelibrary.wiley.com/doi/10.1002/fut.22301)
- **India.**
  - An unrefereed study (Motwani) applies Baltussen et al.'s regressions and NGE signals to Indian markets. It reports that "certain elements … translate well" but that Indian microstructure "necessitate[s] tailored approaches". No statistics were accessible. Grade C/D. — [ResearchGate](https://www.researchgate.net/publication/383567351_Hedging_Demand_and_Intraday_Momentum_within_the_Indian_Stock_Market)
  - **NSE "micro-momentum" (Murphy & Thirumalai 2017, JFR 40(4)).** A stock's half-hour return predicts the *same half-hour on following days*: +1% today → +0.54 bp in that half-hour tomorrow. Bid-ask bounce is controlled using ask prices. The effect is linked to repetitive institutional VWAP-style execution. It is statistically significant but economically negligible for index options. — [JFR](https://onlinelibrary.wiley.com/doi/10.1111/jfir.12131)
- **India expiry microstructure (Agarwalla & Pandey 2013, JFM 33(11)).** NSE stock volatility rises **only in the last half-hour of expiry day** (the settlement averaging window). It is significantly lower in the first two hours and at midday on expiry days. Intraday volatility is reverse-J shaped. — [JFM](https://onlinelibrary.wiley.com/doi/10.1002/fut.21632)
- **Reversal after jumps (US equity ETFs).**
  - 57% of intraday jumps are not news-related, and **no-news jumps reverse for at least 60 minutes**.
  - Scheduled-news jumps reverse; **unscheduled-news jumps show momentum**.
  - Negative jumps reverse more than positive ones.

  Grade B. — [Xiao, Yin & Zhao (2020), JFR 43(3)](https://onlinelibrary.wiley.com/doi/10.1111/jfir.12223)
- **Opening reversals are largely microstructure.** Reversals after large one-day declines are mostly bid-ask bounce and liquidity, and are "doubtful" to be profitable after costs. — [Cox & Peterson (1994), JF 49(1)](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1994.tb04428.x). Open-to-day reversals reflect pricing errors by liquidity suppliers at the open. — [Lee & Lin (1995), JFR](https://onlinelibrary.wiley.com/doi/10.1111/j.1475-6803.1995.tb00579.x)
- **Practitioner falsification on MNQ, 5-minute bars, 2021–2025, walk-forward, 2-point friction.**
  - Gap-fill fade fails (T from −0.26 to −0.44).
  - Gap-continuation short (Kalman velocity on the first 30 minutes) is the closest near-miss: net +14.52 pts, T = 1.46, only 35 OOS trades, failed 2024.
  - "Volatility-volume-gap" days (top tercile of |first-30-min return|, |gap| and first-bar volume; 4.4% of days) show a 77.6% peak-reversal rate, but **no fixed directional rule survives across years**: reversal entry gave −11.45 / +8.35 / −22.76 pts in 2023/2024/2025.

  Grade C. — [Mesfin (2026)](https://arxiv.org/abs/2605.04004)
- **Nifty descriptive (2015–2026).** Gap-down > 0.5%: P(close > open) = 53.8%, mean +0.11%. Gap-up > 0.5%: mean −0.04%. — [04_nifty_measured_facts.md](../04_nifty_measured_facts.md)

### Inferences
- **Upgrade H4 (first-30-minute → last hour) to the Baltussen rest-of-day form.** Use r_ROD = ln(F_15:00 / F_close,t−1) to predict the 15:00–15:25 futures return. r_ONFH had *negative* OOS R² in Baltussen's pooled equity sample, while r_ROD had +2.88%. Keep H4 only as a filter: act when r_ONFH and r_ROD agree (61% success vs 55%).
- **Use thresholds (Rosa).** Act only when |r_ROD| exceeds, say, the 70th percentile of |r_ROD| / σ_HAR over the training window. Expect the edge to concentrate in the top tercile of signal strength.
- **Gamma conditioning is the most promising India-specific extension.**
  - Nifty weekly options (Tuesday expiry) concentrate gamma near expiry.
  - The sign of Indian dealers' net gamma is *not* obvious. Retail is a heavy buyer of OTM options, so liquidity providers may be short gamma more often than in the US, where Baltussen et al. find NGE is positive on most days.
  - Compute NGE under both sign conventions and let the walk-forward test decide.
- **Expiry days need separate treatment.** Agarwalla & Pandey show settlement-window volatility on expiry, and option gamma is largest there. A last-half-hour momentum trade on expiry day trades into the settlement averaging window, and option buyers face total theta collapse.
- **Long-side asymmetry.** Nifty's average intraday drift is negative (−0.069%/day; [04](../04_nifty_measured_facts.md)), and momentum is stronger after positive first-half-hour returns (Shen et al.; Gao et al. per [02](../02_strategy_evidence_part1.md)). Test long and short signals separately, with separate thresholds.
- **H3 (gap-down recovery).** The +0.11% mean is descriptive and close to costs. The jump literature suggests conditioning on *news vs no-news*: no-news gaps reverse, unscheduled-news gaps continue. A practical proxy is to classify gaps by whether GIFT Nifty and US futures explain them, using the 0.47 correlation from [04](../04_nifty_measured_facts.md). A gap far larger than global cues imply is "idiosyncratic/no-news" and a reversal candidate. This is an inference only and must be tested.

### Gaps
- No peer-reviewed test of Gao et al. or Baltussen et al. on Nifty or Sensex was found. The Motwani paper's numbers were inaccessible.
- No Indian dealer-positioning data. NSE participant-wise OI (client / FII / DII / Pro) could proxy who is short options, but I found no study validating it as a gamma proxy.
- Gao et al.'s exact conditional R² by volatility tercile and news days were not re-extracted (see [02](../02_strategy_evidence_part1.md)).

---

## 3. Trend-day vs range-day classification: which regime measures predict rest-of-day range or persistence?

### Takeaway
The regime inputs with real out-of-sample support are:
- **volatility state** (ORB returns depend heavily on it);
- **dealer gamma sign** (momentum only when dealers are short gamma);
- the **"outside the normal noise" condition** (noise-area logic);
- **persistent regime classifiers** (statistical jump models beat HMMs at daily frequency after costs; GMM regime classifiers were the only intraday signals passing a strict practitioner falsification).

I found **no peer-reviewed out-of-sample evidence** that Kaufman efficiency ratio, ADX, intraday Hurst exponents, variance ratios, opening-range-size ratios or market-profile "initial balance" predict rest-of-day persistence on an index. Those are hypotheses to test (grade D–C), not established tools.

### Cited Findings
- **ORB profitability.** On US crude-oil futures, 30 Mar 1983 – 26 Jan 2011, an ORB (trade only when price moves beyond a threshold from the open) produced returns significantly above zero and a success rate above a fair game. Grade B; cost treatment not confirmed. — [Holmberg, Lönnbark & Lundström (2013), Finance Research Letters 10(1):27–33](https://ideas.repec.org/a/eee/finlet/v10y2013i1p27-33.html)
- **ORB by volatility state (crude oil and S&P 500 futures).** The working-paper summary reports average return differences of about 200 bp/day (crude) and about 150 bp/day (S&P 500) between the highest and lowest volatility states: "success in day trading can depend to a large extent on the volatility". I could not access the full text; the magnitude and units look implausibly large and must be verified. — [Lundström, "Day trading returns across volatility states"](https://econpapers.repec.org/paper/hhsumnees/0861.htm)
- **Noise-area breakout (SPY) works better when VIX > 20** (see [02](../02_strategy_evidence_part1.md)).
- **Gamma regime.** Intraday momentum is present only when dealer NGE < 0 (R² 3.58% vs 0.05%). — [Baltussen et al. (2021)](https://academicweb.nd.edu/~zda/intramom.pdf)
- **Markov-switching regimes.** In SPY intraday momentum, two regimes are identified and predictability depends on signal strength. — [Rosa (2022)](https://onlinelibrary.wiley.com/doi/abs/10.1002/fut.22375)
- **Intraday GMM regime classifiers (MNQ, practitioner).** The only signals that passed all five validation gates (OOS net T ≥ 2, ≥ 30 trades per fold, positive net, year-stable, permutation p < 0.001) were GMM regime signals with 60–75-minute holds.
  - **"RTH Confluence" signal**
    - Model: GMM with 3 components (low activity / active flow / extreme volatility), fit once on 2022.
    - 4 features: ATR ratio (20-bar ATR computed on **1-minute** bars ÷ a fixed baseline), 50-bar volume z-score, close position within the bar range, 5-minute return.
    - Gates: rolling 200-bar Markov transition probability P(regime 1 → regime 2) > 0.15, and volume z > 0.5.
    - Entry on a 25 × ATR-ratio-point pullback; exit at bar 13 (65 minutes).
    - Results: walk-forward **OOS T = 3.11, N = 196, mean +11.82 pts net**; in-sample win rate 61%.
  - **"London Signal B"**
    - 5 features including directional consistency; GMM refit each fold.
    - Results: OOS T = 4.30, N = 247, per-trade Sharpe 0.27, win rate 61.5%.
  - Caveats stated by the author: **53+ parameter combinations searched**, partial fold contamination, a fixed ATR baseline (mild look-ahead), and the one-bar-delay sign flip.

  Grade C. — [Mesfin (2026)](https://arxiv.org/abs/2605.04004)
- **Daily statistical jump model vs HMM (Shu, Yu & Mulvey 2024).**
  - Setup: 2-state model, features EWM downside deviation (half-life 10 days), EWM Sortino (half-lives 20 and 60), jump penalty λ chosen monthly by time-series cross-validation on Sharpe, 3,000-day training window, **10 bp one-way cost, 1-day trading delay**, 1990–2023.

  | Index | Sharpe: buy-and-hold | Sharpe: HMM | Sharpe: jump model |
  |---|---|---|---|
  | S&P 500 | 0.48 | 0.54 | **0.68** |
  | DAX | 0.30 | 0.35 | **0.44** |
  | Nikkei 225 | 0.12 | 0.19 | **0.31** |

  - S&P max drawdown: −26.6% (jump model) vs −55.2% (buy-and-hold).
  - Turnover: 44% (jump model) vs 141% (HMM).
  - The jump model is robust to 5–10-day delays, whereas the HMM underperforms the index at a 5-day delay on DAX and Nikkei.

  Grade B (daily, not India). — [arXiv 2402.05272](https://arxiv.org/abs/2402.05272)
- **HMM caveats (cited in the same paper).** HMMs are sensitive to mis-estimation and mis-specification (Nystrup et al. 2020). The purpose of regime models is "not to predict regime shifts … but to identify when a regime shift has occurred, and then benefit from the persistence". — [Shu, Yu & Mulvey (2024)](https://arxiv.org/abs/2402.05272)
- **Hurst value for MNQ** (5-minute) is about 0.59. The author corrects an earlier error: H = 0.5 is a random walk and mean reversion requires H < 0.5. Grade C. — [Mesfin (2026)](https://arxiv.org/abs/2605.04004)
- **LeBaron effect (daily).** Trend PnL accrues disproportionately in **low-volatility** periods. Post-2008 trend losses on small-tick contracts come from high-volatility, large-return days. — [Kurth, Eisler, Rej & Bouchaud (2026), arXiv 2607.01550](https://arxiv.org/abs/2607.01550)

### Inferences
- **Classify the regime with what is evidenced, then test the classic indicators as *added* features.**
  1. Volatility state: HAR forecast relative to its 1-year median, plus India VIX percentile.
  2. Gamma state: NGE sign and size.
  3. "Outside the noise band" state: where price sits relative to the band at each check.
  4. A persistent regime label: a jump model on daily data, and optionally a GMM on 5-minute bars.

  Add ER, ADX, VR, Hurst and the initial-balance ratio to a logistic or gradient-boosted model, and keep them only if they raise walk-forward log-loss skill.
- **Trend-day target definition** (to avoid leakage). At decision time τ (e.g. 10:15):
  - persistence label: sign(F_15:15 − F_τ) = sign(F_τ − F_open), and |F_15:15 − F_τ| > 0.5 × σ_remaining(τ);
  - range label: (High − Low after τ) / σ_remaining(τ).
- **A note of caution:** the intraday-momentum literature implies "trend-day" behaviour is partly a dealer-hedging phenomenon. In India, expiry-day gamma can create either pinning (dealers long gamma) or acceleration (dealers short gamma). The gamma sign may matter more than any price-only indicator.

### Gaps
- I found no peer-reviewed study testing Kaufman ER, ADX, rolling Hurst, intraday variance ratios, opening-range-size ratios or market-profile initial balance as predictors of rest-of-day range or direction persistence, out of sample, on any index. Only practitioner lore. These need our own Nifty tests.
- No HMM, jump-model or GMM regime study on Indian index data was found.
- Lundström's volatility-state magnitudes are unverified (full text inaccessible).

---

## 4. Volatility forecasting for stops and targets: HAR-RV, realized-GARCH, periodicity, India VIX, remaining-day range

### Takeaway
For daily volatility:
- Internationally, the best simple model is **HAR-RV augmented with implied volatility and the overnight return** (HAR-IV-ON).
- For Nifty, **realized-volatility-based forecasts are more efficient and less biased than model-free implied volatility**, because India VIX embeds a volatility risk premium.
- **Range-based estimators** forecast Nifty volatility substantially better than close-to-close historical volatility.

For intraday stops and targets, convert the daily forecast into a **remaining-variance forecast** using a time-of-day periodicity profile (reverse-J in India, with separate profiles for expiry and non-expiry days), updated by how much of the expected morning variance has already been realised.

### Cited Findings
- **HAR-IV and extensions (Kambouroudis, McMillan & Tsakou 2021, JFM 41(10):1618–1639).** Across 10 international stock indices, HAR augmented with implied volatility (HAR-IV) is more accurate than any HAR without IV. **Overnight returns improve forecasts in all markets except the UK.** The leverage effect helps in 5 markets. A VaR exercise confirms economic significance. Grade B. — [JFM](https://onlinelibrary.wiley.com/doi/10.1002/fut.22241)
- **IV alone is worse than combinations.** Implied volatility on its own underperforms GARCH and RV models. An asymmetric GARCH combined with implied and realised volatility is preferred. — [Kambouroudis, McMillan & Tsakou (2016), JFM 36(12)](https://onlinelibrary.wiley.com/doi/10.1002/fut.21783)
- **Nifty: RV beats implied for forecasting.** Forecasts based on model-free realized volatility are "significantly more efficient and less biased" than model-free implied volatility (MFIV, the India VIX methodology). The VRP follows an autoregressive process. Grade B (India). — [Garg & Vipul (2015), JFM 35(9)](https://onlinelibrary.wiley.com/doi/10.1002/fut.21680)
- **Nifty: range-based estimators.** Extreme-value (high-low) estimators with simple forecasting methods give "substantially better short-term and long-term forecasts" than historical volatility. The benchmark is two-scale realized volatility. Adding them also improves GARCH. Grade B (India). — [Vipul & Jacob (2007), JFM 27(11)](https://onlinelibrary.wiley.com/doi/10.1002/fut.20283)
- **India VIX as a forecaster (conflicting evidence).** One study reports India VIX as the best estimate of future realized volatility, with slope "very close to unity" at 10- and 22-day horizons. Abstract-level only via search; not verified. — [Global Business Perspectives (2013)](https://link.springer.com/article/10.1007/s40196-013-0025-4). This conflicts with [Garg & Vipul (2015)](https://onlinelibrary.wiley.com/doi/10.1002/fut.21680) on bias, and with our own data: VIX was above the next 21-day RV on 80.5% of days, and the VIX-implied 1-day move averaged 1.04% vs 0.70% realized ([04](../04_nifty_measured_facts.md)).
- **VIX jumps** add information to HAR-RV at short, medium and long horizons (S&P 500). — [Dutta & Das (2022), JFM 42(12)](https://onlinelibrary.wiley.com/doi/10.1002/fut.22372)
- **Time of day matters for implied vol.** Intraday VIX levels around **noon** are the most informative for predicting realized volatility (US). In the 2008 crisis the informativeness persisted to the close. — [Wang & Wang (2015), J. Forecasting 35(2)](https://onlinelibrary.wiley.com/doi/10.1002/for.2373)
- **Overnight component.** Overnight volatility components improve log-HAR forecasts, whereas first-half-hour components of a related market add little (China, INE oil). — [Chen & Huang (2025), JFM 45(10)](https://onlinelibrary.wiley.com/doi/10.1002/fut.70008)
- **Range efficiency.** The daily high-low range carries about as much information as intraday returns sampled every 4 hours. Range proxies are highly efficient, approximately Gaussian and robust to microstructure noise (Parkinson 1980; Alizadeh et al. 2002; Andersen & Bollerslev 1998). — summarised in [Harris & Mazibas (2021), Bull. Econ. Research](https://onlinelibrary.wiley.com/doi/10.1111/boer.12314)
- **India intraday periodicity.**
  - NSE volatility is **reverse-J** shaped: high at the open, flatter at the close than in other markets.
  - Volume and trade counts are U-shaped.
  - The autocorrelogram of 5-minute absolute returns shows a repeating U every 67 lags (one day).
  - The Andersen-Bollerslev Flexible Fourier Form fits well.

  — [Agarwalla & Pandey (2013)](https://onlinelibrary.wiley.com/doi/10.1002/fut.21632)
- **Nifty futures intraday pattern.** Volatility, volume and trade counts are U-shaped (Nov 2016 – Oct 2017; 10/30/60-minute bars). Returns Granger-cause volume more strongly than the reverse. — [Sampath & Garg (2018), IRF 19(3)](https://onlinelibrary.wiley.com/doi/10.1111/irfi.12175)
- **News days thin the book.** Price impact rises and liquidity withdraws around macro releases, so the same flow moves price more. — [Takahashi (2025)](https://arxiv.org/abs/2508.06788)

### Inferences
**Daily model (fit after the close, used next day).**

log RV_{t+1} = β0 + βd·log RV_t + βw·log RV_t^(5) + βm·log RV_t^(22) + βiv·log(VIX_t²/252) + βon·log(r_on,t² + c)

- RV_t = sum of squared 5-minute log returns of Nifty futures, 9:20–15:25.
- RV^(5) and RV^(22) are 5- and 22-day means.
- r_on = overnight (close → 9:15/9:20) return.
- Estimate by OLS on a rolling 3–4-year window, or WLS (Clements-Preve style).
- Add a Parkinson range term, (ln H/L)² / (4 ln 2), as an alternative regressor, since Vipul & Jacob favour range estimators for Nifty.
- Treat VIX as an *input*, not as the forecast; the VRP bias is documented above.

**Remaining-variance forecast at time τ.**
1. Build a periodicity profile s(u) = average share of daily RV in 5-minute bucket u over the last 60 days. Keep separate profiles for **expiry vs non-expiry** days, and drop event days.
2. Expected morning share: S_≤τ = Σ_{u≤τ} s(u).
3. Surprise ratio: k_τ = RV_realised_so_far / (RV̂_t × S_≤τ).
4. Remaining variance: σ²_rem(τ) = RV̂_t × (1 − S_≤τ) × k_τ^α, with α ≈ 0.5 as a starting shrinkage to be estimated walk-forward. Volatility clusters intraday, so a hot morning implies a hotter afternoon, but not one-for-one.
5. Expected remaining high-low range ≈ √(8/π) × σ_rem ≈ 1.6 σ_rem under Brownian motion. Use the empirical ratio once measured.

**Stops and targets.**
- Initial stop just beyond the noise band, or at 0.75–1.0 σ_rem from entry, whichever is wider.
- Target at 1.5–2 σ_rem, or the nearest strong level (section 5).
- Trail with VWAP, as in Zarattini.
- Widen everything on scheduled-event days (RBI, US CPI/FOMC overnight, budget).

**Sizing reality check (inference, illustrative numbers).**
- Rupee risk per lot for a 1% index move ≈ delta × lot × index level × 1%.
- With an *assumed* Nifty level of 25,000, an ATM option (delta ≈ 0.5) moves about ₹8,100 per lot per 1% index move. A ₹500 risk budget therefore corresponds to about 0.06% of the index (about 15 points). That is inside ordinary 1–5-minute noise, and well inside a 14-day noise band.
- Sensex lot 20 × an assumed level of about 82,000 gives similar notional.
- Implications:
  - Index-level stops sized from σ_rem will usually exceed ₹500 per ATM lot.
  - To fit, either use low-delta (OTM) options, which carry worse theta and VRP drag ([04](../04_nifty_measured_facts.md)), or debit spreads; or accept that the ₹200–500 budget only fits setups whose structural stop is very close.
- **This conflict should be resolved explicitly in the system design.** Re-compute with the actual index level on deployment.

### Gaps
- I could not access Pati, Barai & Rajib (2018, Applied Economics; India, Australia, Hong Kong; implied vs GARCH vs RV). The search summary attributed to it appears to repeat another paper's abstract, so it is not relied on here.
- I found no Indian study of HAR-RV vs realized-GARCH out of sample, and none of remaining-day range forecasting from the morning session. The recipe above is an inference to test.
- No India-specific evidence on the noon-VIX effect.

---

## 5. VWAP, anchored VWAP, prior-day high/low/close, pivots, round numbers: support/resistance evidence

### Takeaway
There is rigorous evidence for:
- **round-number and recent-extreme support/resistance** (FX: published S/R levels predict intraday trend interruptions; order clustering explains why levels hold and why breaches accelerate);
- a **"memory" effect at recent highs and lows** (bounce probability rises with the number of prior touches and decays with time).

I found **no rigorous evidence that VWAP, anchored VWAP or floor-trader pivots act as support/resistance** on equity indices. VWAP's empirical role is as an institutional *execution benchmark* and as a trailing stop in the noise-area strategy. Nothing here is India-specific. Use levels for **trade management** (targets, stops, "room to run" filters), not as stand-alone entry signals.

### Cited Findings
- **Osler (2000), FRBNY Economic Policy Review 6(2).** S/R levels published by six firms were tested on 1-minute indicative FX quotes (DEM, JPY, GBP; 1996–1998, 9am–4pm NY). The tests "strongly support the claim that support and resistance levels help predict intraday trend interruptions". Grade B (FX). — [RePEc](https://ideas.repec.org/a/fip/fednep/y2000ijulp53-68nv.6no.2.html); [ResearchGate](https://www.researchgate.net/publication/5050393_Support_for_Resistance_Technical_Analysis_and_Intraday_Exchange_Rates)
- **Osler (2003), JF 58(5).** Stop-loss and take-profit orders at a large FX dealer **cluster at round numbers**, with distinct patterns:
  - take-profit orders cluster *at* round numbers, so trends tend to reverse there;
  - stop-loss orders cluster just *beyond* them, so **trends gain momentum once a level is crossed**.

  Grade B. — [JF](https://onlinelibrary.wiley.com/doi/abs/10.1111/1540-6261.00588); [NY Fed staff report 125](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf)
- **Memory effect (Garzarelli, Cristelli, Pompa, Zaccaria & Pietronero 2014, Scientific Reports 4:4487).** The probability that price bounces on a level increases with the number of previous bounces (LSE stocks, high-frequency). Grade B. — [EconPapers](https://econpapers.repec.org/paper/arxpapers/1110.5197.htm)
- **Replication with an explicit algorithm (Chung & Bellotti 2021).** Data: 2018 1-minute EURUSD (372,607 obs), Lloyds (127,606) and Brent (307,678).
  - Method: support = rolling-window minimum ± γ and resistance = rolling-window maximum ± γ, where γ = average absolute 1-minute price change.
  - p(bounce | previous bounces) is above 0.5 and rises with the number of previous bounces. It is above the shuffled-returns baseline, with permutation confidence of about 0.94–1.0 for 1–6 prior bounces in most series.
  - Bounce probability decays with window length: for EURUSD, a 1-bounce level decays to 0.5 at about a 350-minute window, a 4-bounce level at about 900 minutes. Brent 1-bounce levels drop below 0.5, i.e. they predict penetration, in a bear year.
  - The effect cannot be reproduced by AR(1) processes.
  - **No trading or cost test.** Grade C (preprint).

  — [arXiv 2101.07410](https://arxiv.org/abs/2101.07410)
- **Moving-average signals may proxy order-book skew around S/R** (NYSE evidence reviewed). — [Park & Irwin (2007), J. Econ. Surveys 21(4)](https://onlinelibrary.wiley.com/doi/10.1111/j.1467-6419.2007.00519.x)
- **Level-sweep patterns fail after costs (practitioner).** "Liquidity grab" setups (price pierces a session extreme, then closes back inside; 6,442 events) lose in **both** directions: fade −2.20 pts (T = −14.1), follow −1.80 pts (T = −13.2). Gross content is only 0.2–0.8 pts. Grade C. — [Mesfin (2026)](https://arxiv.org/abs/2605.04004)
- **VWAP as a trailing stop** is part of the noise-area strategy (Sharpe 1.33 on SPY 2007–2024; see [02](../02_strategy_evidence_part1.md)). VWAP is also the dominant institutional execution benchmark, which plausibly creates repetitive intraday flow; the NSE micro-momentum is attributed to VWAP-style multi-day institutional execution. — [Murphy & Thirumalai (2017)](https://onlinelibrary.wiley.com/doi/10.1111/jfir.12131)

### Inferences
- **Levels worth computing** (from futures 1-minute bars):
  - prior-day high, low and close (PDH, PDL, PDC);
  - today's open;
  - session VWAP (futures volume; the spot index has no volume);
  - anchored VWAP from the gap-fill time, or from the 9:15 open on gap days;
  - round numbers (Nifty multiples of 100 and 500; Sensex multiples of 500 and 1,000);
  - the day's running high and low, with a touch count.
- **Use 1: targets and stops (Osler logic).** Put targets just *before* strong round or recent-extreme levels. Put stops just *beyond* levels rather than at them. Treat a clean break through a round number as a modest continuation cue, not a fade.
- **Use 2: "room-to-run" filter.** Skip entries where the distance to the next strong opposing level is less than about 1 × σ_rem(τ). The payoff asymmetry the noise-area strategy depends on (win rate about 43%) needs room.
- **Test the level effect on Nifty before trusting it.** Re-run the Chung-Bellotti bounce-probability test on Nifty futures 1-minute data, 2019–2026, including the shuffled-returns control. Add PDH/PDL/VWAP/round-number levels as candidate level sets. If p(bounce) for PDH/PDL or VWAP is not above the shuffled baseline, drop that level type.
- Pivot-point formulas (P = (H+L+C)/3, R1 = 2P − L, …) have no supporting evidence I could find. They add degrees of freedom without evidence, so exclude them unless the bounce test supports them.

### Gaps
- No peer-reviewed evidence on VWAP or anchored-VWAP reactions, prior-day high/low breakout continuation, or pivot levels for any equity index; none for India.
- Osler's evidence is FX dealer order data, and transfer to NSE order books is unproven. A partial test is possible: look for depth clustering at round strikes and levels in SmartAPI 5-level snapshots.

---

## 6. Daily time-series momentum and short-term reversal as a daily bias input

### Takeaway
Classic time-series momentum (Moskowitz, Ooi & Pedersen 2012) is a **1–12-month** effect. **Fast trend (days to weeks) in equity-index futures has effectively died since about 2009**: an EWM 5/20-day trend portfolio's Sharpe fell from 0.84 (1995–2009) to 0.12 (2009–2025), and equity indices are among the worst-hit sectors. For Nifty, the measured daily persistence (P(up | yesterday up) 56.7% vs 49.5%) and the 50-DMA filter (57.4% vs 54.8% 5-day-up rates) are mild. The daily layer should therefore be a **volatility/risk regime and sizing input** plus an **overnight-intraday reversal tilt**, not a directional engine.

### Cited Findings
- **Moskowitz, Ooi & Pedersen (2012), JFE.** Equity index, currency, commodity and bond futures show time-series momentum: returns persist for 1–12 months, then partially reverse. — [paper](https://fairmodel.econ.yale.edu/ec439/jpde.pdf)
- **Demise of fast trend (Kurth, Eisler, Rej & Bouchaud 2026; about 100 liquid futures, 1995–2025).**

  | Signal (EWM fast-slow, days) | Sharpe 1995–2009 | Sharpe 2009–2025 |
  |---|---|---|
  | 5–20 | 0.84 | **0.12** |
  | 10–40 | 0.83 | 0.22 |
  | 20–80 | 0.79 | 0.27 |
  | 50–200 | 0.70 | 0.40 |

  - Trend "has effectively vanished" for equity indices and FX.
  - The dividing variable is **volatility-normalised tick size**: small-tick contracts collapsed, large-tick ones survived.
  - Losses are concentrated in high-volatility, large-return days.

  Grade B (preprint by an established group; not India). — [arXiv 2607.01550](https://arxiv.org/abs/2607.01550)
- **Overnight-intraday reversal.** Across asset classes, including equity-index futures, an overnight-intraday reversal strategy has returns and Sharpe ratios about **2–5×** those of conventional daily reversal. Grade B (working paper). — [Della Corte, Kosowski et al., "Overnight-Intraday Reversal Everywhere"](https://assets.super.so/e46b77e7-ee08-445e-b43f-4ffd88ae0a0e/files/c953a0e6-e93e-4bf7-b839-45a90cedced4.pdf)
- **India cross-section (BSE stocks).** Intermediate and long-term momentum is significant and stronger in liquid portfolios. **Short-term reversal is significant in India.** Stock-level, not index. — [Pacific-Basin Finance Journal (2023), "Momentum, reversals and liquidity: Indian evidence"](https://www.sciencedirect.com/science/article/abs/pii/S0927538X23002640)
- **Nifty overnight vs intraday.**
  - Since 2015 all the gain is overnight: +0.109%/day overnight vs −0.069%/day intraday.
  - Gap-down days recover slightly.
  - P(5-day up) is 57.4% above the 50-DMA vs 54.8% below, but moves below the 50-DMA are 54% larger.

  — [04_nifty_measured_facts.md](../04_nifty_measured_facts.md). Consistent with the day-night asymmetry in Nifty option returns, 2017–2020. — [Bhat, Pandey & Nageswara Rao (2024), JFM 44(8)](https://onlinelibrary.wiley.com/doi/10.1002/fut.22512)
- **Volatility management helps momentum survive costs** (Chinese commodity momentum). Inverse-RV scaling keeps significant alphas, with break-even costs of 49–157 bp. — [Xu & Wang (2021), JFM 41(5)](https://onlinelibrary.wiley.com/doi/10.1002/fut.22195)

### Inferences
- **Nifty is a small-tick contract.** Tick ₹0.05 on an index in the tens of thousands, with daily σ around 1%, is a tiny volatility-normalised tick. By Kurth et al.'s classification, fast daily trend signals on Nifty are likely in the "collapsed" group. Do not spend model capacity on 5–20-day trend for direction.
- **Daily inputs to keep:**
  1. A regime/risk state from a jump model or HAR-vol percentile, used for sizing and for allowing or vetoing trades. A low-vol regime favours trend continuation (LeBaron effect); a high-vol regime favours wider stops and smaller size.
  2. An overnight-gap reversal tilt: a large unexplained gap gives a mild intraday fade bias (see section 2).
  3. Price above or below the 50-DMA as a volatility-regime flag, not a direction call.

### Gaps
- I found no peer-reviewed India *index-level* time-series momentum or short-term-reversal study with costs.
- I could not verify whether Georgopoulou & Wang (2017, Review of Finance), on time-series momentum across equity and commodity markets, includes India. — [Springer listing](https://link.springer.com/chapter/10.1007/978-3-319-91530-2_2)

---

## 7. Which popular intraday technical rules fail after costs, and what distinguishes the survivors

### Takeaway
Most published and retail intraday rules fail once data-snooping corrections, realistic friction and delay are imposed:
- ORB variants, gap fills, volume spikes and dry-ups, liquidity grabs, news drift, and 5-minute technical rule sets;
- intraday momentum in its plain, always-on form, post-publication.

Survivors share six features:
1. **State or regime conditioning** (volatility, dealer gamma, regime classifiers).
2. **Longer holds** (60–75 minutes to close) that accumulate enough gross edge to clear friction.
3. **Volatility scaling and volatility-adaptive bands.**
4. **Trading only strong signals** (thresholds, signal agreement).
5. **A structural flow mechanism** (hedging, settlement, institutional execution) rather than a chart pattern.
6. **Low turnover.**

### Cited Findings
- **Survey (95 modern studies).** 56 positive, 20 negative, 19 mixed. US stock-market technical profits disappeared after the late 1980s. Most studies have data-snooping, ex-post selection and cost-estimation problems. — [Park & Irwin (2007)](https://onlinelibrary.wiley.com/doi/10.1111/j.1467-6419.2007.00519.x)
- **S&P 500 spot and futures, 2,580 technical models (Schulmeister).** Daily-data models have been unprofitable since the early 1990s. The same models on **30-minute** data earned an average **gross** 7.2%/yr (1983–2007), but performed worse in 2001–2007 than in the 1980s–90s. — [Schulmeister (2009), Rev. Fin. Econ. 18(4)](https://onlinelibrary.wiley.com/doi/10.1016/j.rfe.2008.10.001)
- **Intraday technical analysis in US stocks (5-minute, 2002–2003)** is not profitable after data-snooping correction (Marshall, Cahan & Cahan 2008). — cited in [Chang, Chan & Chiang (2014)](https://onlinelibrary.wiley.com/doi/10.1111/ajfs.12046) and [Jin (2022)](https://onlinelibrary.wiley.com/doi/10.1002/for.2873)
- **Chinese crude-oil futures (5-minute, 2018–2021).** With a false-discovery-rate correction and costs, intraday technical predictive power is "illusory". — [Jin (2022), J. Forecasting 41(7)](https://onlinelibrary.wiley.com/doi/10.1002/for.2873)
- **Chinese A-shares, daily, about 28,000 rules.** Under a stepwise SPA test, **fewer than 1%** are genuinely significant. The survivors (mostly moving-average rules) remain significant at 0.25–0.5% one-way cost. — [Jiang, Tong & Song (2017), IRF 19(1)](https://onlinelibrary.wiley.com/doi/10.1111/irfi.12161)
- **Trend following across indices and stocks** produces "substantial, fading, non-persistent and highly methodology-sensitive excess returns". — [Zoicas-Ienciu (2020), IJFE 26(1)](https://onlinelibrary.wiley.com/doi/10.1002/ijfe.1833)
- **Chinese commodity futures.** Trend rules are robust to costs and delays, but "may be subject to data snooping bias". — [Li, Zhang & Zhou (2017), JFM 37(12)](https://onlinelibrary.wiley.com/doi/10.1002/fut.21856)
- **MNQ falsification (14 families).**
  - 11 families fail because their maximum gross edge (0.07–1.50 pts) is below the 2-pt friction floor.
  - ORB long with a 75-minute hold: net +2.82, T = 0.88.
  - ORB pullback entry: 80.7% stop-out rate.
  - Volume spikes and dry-ups: T from −2.2 to −5.3 on 723–2,412 trades ("a precise null").
  - Event-day drift: T 0.14–0.69.
  - Only GMM regime signals with 60–75-minute holds passed.

  Grade C. — [Mesfin (2026)](https://arxiv.org/abs/2605.04004)
- **Intraday momentum post-publication** disappears for SPY; thresholds help. — [Rosa (2022)](https://onlinelibrary.wiley.com/doi/abs/10.1002/fut.22375)
- **Fast trend collapsed post-2009** on small-tick contracts; **slow and large-tick trend survived**; the LeBaron effect holds. — [Kurth et al. (2026)](https://arxiv.org/abs/2607.01550)
- **Regime models with persistence** survive costs and delays at daily frequency (jump model). — [Shu, Yu & Mulvey (2024)](https://arxiv.org/abs/2402.05272)
- **Opening option order imbalance** (a structural flow signal) survives costs in Korea. — [Kang, Kang & Lee (2021)](https://onlinelibrary.wiley.com/doi/10.1002/fut.22301)
- **ORB and noise-area replications.** Unfiltered ORB lost to the index; the QQQ ORB Sharpe fell from 1.06 to 0.23 with 2¢/4¢ slippage, and 76% of filtered P&L came from 2022 (see [02](../02_strategy_evidence_part1.md)).

### Inferences
**Design rules for this system.**
1. Every signal must name a *mechanism* (hedging flow, settlement window, institutional execution, volatility regime). Pure chart-pattern signals start with a strong prior of failure.
2. Hold to a planned horizon of at least 45–60 minutes, or to 15:15. Do not scalp. Option spreads and costs (next point) dominate any sub-15-minute edge.
3. Trade only the top tercile of signal strength, measured in units of σ_rem.
4. Run a delay test. Mesfin's sign flip shows bar-boundary signals can invert with one bar of delay. Our alert → manual order latency (1–3 minutes) must be in the backtest.
5. Use volatility-adaptive bands and sizing, not fixed points.

**Cost floor for option buyers (inference, illustrative).** One Nifty lot round trip costs about:
- brokerage: ₹40;
- STT: 0.15% of sell premium (₹9.75 on a ₹100 × 65 premium);
- GST on brokerage: about ₹7;
- exchange charges and stamp duty: small (not included here);
- spread slippage: ₹0.5–1.0 per unit × 65 = ₹33–65.

That totals roughly **₹90–125 per lot, or about 1.4–1.9 premium points per unit**. At ATM delta 0.5 this needs a 3–4-point index move *before theta*. Weekly ATM theta near expiry adds several more points per hour in the final sessions. The gross edge per trade must clear something like 5–10 Nifty points. Signals with R² of 1–3% at the last half-hour clear this only on high-volatility days, which is another reason for the volatility and gamma conditioning.

### Gaps
- I found no Indian replication of the intraday technical-rule failure literature (Marshall-type tests on Nifty futures).
- Current NSE exchange transaction charges and SEBI fee rates (October 2026) were not re-verified here.

---

## 8. Concrete recipes, walk-forward protocol on Nifty 1-minute data (2019–2026), and ranked shortlist

### Takeaway
Build a three-layer stack:
1. **Daily regime and volatility layer:** jump-model state, HAR-IV-ON forecast, VIX percentile, gamma sign.
2. **Intraday directional triggers with evidence:** noise-band breakout and rest-of-day momentum in the last 30–60 minutes, each thresholded and regime-gated; opening option-order imbalance as a tilt.
3. **Trade-management layer:** σ_rem-based stops and targets, level-aware targets, VWAP trail, and an OFI veto at the moment of the alert.

Test each component walk-forward on 2019–2026 Nifty futures 1-minute data with explicit option-cost and delay models, deflated-Sharpe and permutation controls, and year-stability gates.

### Cited Findings
- The protocol elements below are borrowed from studies that used them.
  - **Mesfin (2026):** expanding-window folds; five simultaneous gates (OOS net T ≥ 2, ≥ 30 trades per fold, positive net, consistent sign across OOS years, permutation p < 0.001); signal at bar close with entry at the next bar open; an explicit friction floor. — [arXiv 2605.04004](https://arxiv.org/abs/2605.04004)
  - **Shu, Yu & Mulvey (2024):** hyperparameters chosen by time-series cross-validation on the strategy metric, with trading delay and costs applied inside the validation as well. — [arXiv 2402.05272](https://arxiv.org/abs/2402.05272)
  - **Baltussen et al. (2021):** pooled out-of-sample R² definition — R²_OOS = 1 − Σ(r − r̂)² / Σ(r − r̄_hist)², with r̄_hist the historical mean up to t−1. — [Baltussen et al.](https://academicweb.nd.edu/~zda/intramom.pdf)
  - **Cont, Cucuringu & Zhang:** chronological train/test for OFI models. Their note on prior studies: "previous studies … failed to consider the generalization error … or damaged the chronological order". — [arXiv 2112.13213](https://arxiv.org/abs/2112.13213)
  - **Validation standards** (deflated Sharpe, probability of backtest overfitting) are in [02, section 4](../02_strategy_evidence_part1.md).

### Inferences

#### A. Data preparation (applies to everything)
- **Instrument for signals and P&L.**
  - Use Nifty near-month futures 1-minute OHLCV for signals, VWAP and OFI. Build a continuous series with back-adjustment at the roll, rolling on the day volume shifts, about 2–3 days before monthly expiry.
  - Keep the spot index series for gap and level definitions that traders watch: PDH/PDL on spot vs futures. Test both.
  - Sensex: same steps with BSE Sensex futures if 1-minute history is available; otherwise use the spot index and a basis assumption.
- **Session clock.**
  - 9:15 open. First valid check at 9:30. Checks every 15 minutes to 15:00. Flat by 15:15–15:20.
  - The official index close is an averaged last-30-minute price (verify NSE/BSE methodology). Use the futures last traded price at 15:25–15:29 as the "close" for last-half-hour tests, not the official close.
- **Calendar flags.** Expiry day: Tuesday for Nifty since September 2025, Thursday for Sensex. Day before expiry. Monthly expiry. RBI policy days. Union Budget. US CPI/FOMC overnight. Results-heavy weeks. Holidays and half-days. Muhurat sessions are excluded.
- **Structural breaks to test separately.** Weekly expiry day changes; the SEBI F&O changes of late 2024 (lot-size increase, one weekly expiry per exchange — verify dates); the 2020 COVID regime; the 2026 high-volatility year noted in [04](../04_nifty_measured_facts.md).

#### B. Walk-forward protocol (all components)
- **Folds** (expanding window, retrain annually):
  - train 2019–2020 → test 2021
  - train 2019–2021 → test 2022
  - … → test 2026 YTD

  That gives 6 OOS years. Parameters are frozen inside each test year. Regime models (GMM/HMM/jump) are refit only on training data, with no labels fit on overlapping data — the contamination Mesfin admits.
- **Execution model.**
  - Signal computed on the 1-minute bar closing at the check time. Entry at the next bar open plus a delay d ∈ {0, 1, 3, 5} minutes (manual-alert latency).
  - Report all four delays. Reject any signal whose sign flips at d = 3.
- **Option P&L model.**
  - Where historical option 1-minute data exist, use the actual premium of the chosen strike with bid-ask from snapshots.
  - Otherwise, simulate with Black-76 on futures using India VIX (or a skew-adjusted ATM IV) and the actual time to expiry, adding theta explicitly.
  - Costs:
    - brokerage ₹20 per order;
    - STT 0.15% of sell premium;
    - exchange charges, SEBI fee, GST and stamp duty at current schedules;
    - slippage of half the spread plus one tick per side, with a sensitivity run at 2× slippage.
  - Report results for ATM, 1-strike ITM (delta about 0.6) and debit-spread implementations.
- **Gates** (all must hold on OOS years):
  1. Net mean > 0 in rupees per trade.
  2. t ≥ 2 on net returns.
  3. ≥ 30 trades per OOS year.
  4. Positive in at least 4 of 6 OOS years, and never worse than −1 σ in any year.
  5. Permutation test (shuffle signal dates within the same weekday or expiry bucket) p < 0.01.
  6. Deflated Sharpe > 0 after counting *all* parameter combinations tried.
  7. PBO < 0.2 via CSCV.
- **Pre-registration.** Write each component's parameter grid down before the first run and log every run. Mesfin's 53-combination search is the cautionary example.

#### C. Component recipes

**C1. Volatility engine (HAR-IV-ON + periodicity → σ_rem).**
- Formulas: section 4. RV from 5-minute futures returns, 9:20–15:25. Overnight return from the prior 15:29 futures last price to 9:20.
- Estimation: rolling 750-day window, refit monthly.
- Periodicity profile: 60-day rolling 5-minute variance shares, separately for expiry and non-expiry days.
- Update: σ_rem recomputed at every 15-minute check.
- Evaluation:
  - QLIKE and MSE vs (a) VIX²/252 scaled by the training-period VRP ratio, (b) 20-day RV, (c) a Parkinson-range EWMA.
  - Mincer-Zarnowitz regression of realised remaining variance on σ²_rem(τ) at τ = 10:15, 12:00 and 14:00.
  - Success criterion: slope near 1, and QLIKE better than scaled VIX.

**C2. Noise-band breakout (H1, refined).**
- **Band.** σ(τ) = (1/14) Σ_{d=1..14} |C_{d,τ}/O_d − 1| for each minute-of-day τ.
  - Upper = max(O_t, C_{t−1}) × (1 + V·σ(τ)).
  - Lower = min(O_t, C_{t−1}) × (1 − V·σ(τ)).
  - V = 1 (test 0.8, 1.0, 1.2).
- **Checks.** Every 15 minutes from 9:45 (test 30-minute checks as in the original paper). Long when F > Upper; short when F < Lower.
- **Exit.** Close below VWAP (long) or above VWAP (short), or back inside the band (test both); flat at 15:15.
- **Regime gates** (test each, then combine):
  - HAR-forecast percentile > 50%, or India VIX > its 1-year median (the original paper does better when VIX > 20);
  - NGE < 0 (either sign convention);
  - room-to-run ≥ 1 σ_rem to the next strong level;
  - OFI_5min not opposite at > 1 σ.
- **Sizing.** Volatility-targeted, then mapped to lots and capped by the ₹200–500 risk budget (see the sizing reality check in section 4).
- **Recompute the bands separately for expiry Tuesdays.** The time-of-day volatility profile differs.

**C3. Rest-of-day intraday momentum, last 30–60 minutes (H4 upgrade).**
- Signal at 14:45 or 15:00: r_ROD = ln(F_τ / F_close,t−1). Strength z = r_ROD / σ_HAR,day.
- Trade: in the direction of r_ROD if |z| > z* (z* = training-window 70th percentile of |z|). Optional filter: sign(r_ONFH) = sign(r_ROD), where r_ONFH = ln(F_9:45 / F_close,t−1).
- Hold to 15:25.
- Conditioning to test: NGE < 0; expiry day vs non-expiry; high-volatility days (top tercile of HAR or VIX).
- Report R²_OOS (Baltussen definition) as well as trading metrics.
- Expected effect (from US/global): R² of 2–4% in the right regime, about 0 otherwise.

**C4. Gamma regime (NGE) from the Nifty and Sensex option chain.**
- For each strike K and expiry m:
  - Γ = Black-76 gamma from the chain's IV.
  - GEX_K = Γ × OI × lot × F² × 0.01. This is the rupee delta change for a 1% move.
- Two sign conventions:
  - (a) Baltussen: dealers long calls, short puts → NGE = Σ_calls GEX − Σ_puts GEX.
  - (b) Dealers short all customer-bought options (NGE = −Σ GEX), as an alternative check.
- Normalise by futures ADV in rupees.
- Update: 9:15 using the prior-day final OI, then every 15 minutes with intraday OI if SmartAPI's OI field updates intraday.
- Also compute the "zero-gamma level": the futures price at which NGE changes sign, found by re-pricing gammas on a grid of F. Treat it as a candidate level for section 5.
- Validation: does the sign predict the r_ROD → r_LH slope (C3) and rest-of-day realised range / σ_rem? Expect larger ranges and positive autocorrelation when NGE < 0.

**C5. Opening option-order imbalance (Kang et al. design).**
- Window 9:15–9:30. For ATM ± 3 strikes, current weekly expiry:
  - sign each trade by the quote rule against the latest 5-level snapshot (LTP ≥ ask → buy; ≤ bid → sell; otherwise tick rule);
  - OIB_C = (B_C − S_C) / (B_C + S_C) by volume, and the same for puts.
  - Signal = OIB_C − OIB_P, or delta-weighted net buying Σ Δ·(B − S).
- Predict: return from 9:30 to 15:15 of futures; use as a tilt or gate for C2.
- Data caveat: this requires tick-level option trades plus depth for 2019–2026. If history is unavailable, start recording live now; at least one year is needed before testing.

**C6. Integrated 5-level OFI veto.**
- Per snapshot pair, compute OF^{m,b} and OF^{m,a} for m = 1..5 (section 1).
- OFI^m over the last h minutes (h = 3 and 5), scaled by average 5-level depth.
- ofi_I = simple average across levels (or PCA weights estimated on training data).
- z-score against the same time-of-day over the last 20 days.
- Role: block alerts where z_OFI < −1 for longs or > +1 for shorts.
- Validation:
  - contemporaneous R² of 1-minute returns on ofi_I (target > 40%);
  - incremental improvement in C2/C3 net expectancy with vs without the veto.

  Expected horizon: < 5 minutes (Tripathi et al.).

**C7. Daily regime: statistical jump model.**
- Features on Nifty daily excess returns: EWM downside deviation (half-life 10), EWM Sortino (half-lives 20 and 60). Optionally add the India VIX level and the VIX-minus-RV spread.
- K = 2, λ chosen monthly by time-series CV on the strategy Sharpe, 1-day delay. Training window 8–12 years; Nifty daily data back to the 1990s are available.
- Role: size multiplier (bear or turbulent → half size, longs only on strong signals) and a gate for C2/C3.

**C8. Intraday GMM regime (exploratory, grade C).**
- Features on 5-minute bars:
  - ATR ratio: 20-bar ATR from 1-minute bars ÷ the 60-day *rolling* median ATR. Not a fixed baseline, which avoids Mesfin's look-ahead.
  - 50-bar volume z-score.
  - Close location (C − L)/(H − L).
  - 5-minute return.
  - Efficiency ratio over 6 bars, ER = |C_t − C_{t−6}| / Σ|ΔC|.
- 3 components, fit on training folds only, labelled by ascending ATR.
- Gate: rolling 200-bar transition frequency into the "active" state.
- Hold 60–75 minutes.
- Treat as a candidate. It passes only if it clears the full gate set with the parameter count deflated.

**C9. Trend-day classifier at 10:15 (exploratory, grade D → test).**
- Features:
  - IB ratio = (H − L over 9:15–10:15) / 20-day median of the same.
  - ER_60 on 1-minute bars over 9:15–10:15.
  - Variance ratio VR(5) = Var(5-minute returns) / (5·Var(1-minute returns)) over 9:15–10:15.
  - Open location vs the prior-day range (inside, above PDH, below PDL).
  - First-hour close location.
  - ADX(14) on 5-minute bars.
  - Gap size / σ_HAR.
  - NGE sign.
  - HAR percentile.
- Labels as in section 3. Model: L2 logistic regression.
- Metric: walk-forward log-loss and Brier skill vs a base-rate model, plus the improvement in C2 net expectancy when gating on P(trend) > 0.6.

**C10. Level map (trade management).**
- PDH, PDL, PDC, today's open, VWAP, anchored VWAP (from 9:15 and from gap fill), round numbers, running extremes with touch counts, zero-gamma level (C4).
- Validation: Chung-Bellotti bounce test per level type on Nifty futures 1-minute data against the shuffled baseline.
- Keep only level types with p(bounce) significantly above baseline. Use them for targets, stops and the room-to-run filter.

#### D. Ranked shortlist of technical and regime components to implement

| Rank | Component | Formula (short) | Data needed | Update frequency | Role | Evidence grade |
|---|---|---|---|---|---|---|
| 1 | **HAR-IV-ON daily vol + periodicity → σ_rem(τ)** | log RV_{t+1} on log RV (1/5/22 days), log VIX²/252, log r_on²; σ²_rem = RV̂·(1 − S_≤τ)·k_τ^α | Futures 1-min (5-min RV), India VIX daily | Daily fit; σ_rem every 15 min | Volatility (stops, targets, sizing, normalisation of all signals) | B (India support for RV/range over implied: Garg & Vipul; Vipul & Jacob; global HAR-IV: Kambouroudis et al.) |
| 2 | **Noise-band breakout with VWAP trail, regime-gated** | Band = open/prev-close ± V·mean_14d \|C_τ/O − 1\|; enter outside band at checks; exit at VWAP; gates: vol regime, NGE, room-to-run | Futures 1-min OHLCV | Every 15 min | Direction + regime | B (SPY paper) / C (replications weaker); untested in India |
| 3 | **Dealer gamma regime (NGE, zero-gamma level)** | Σ Γ·OI·lot·F²·1% with dealer-sign convention; normalised by ADV | Option chain: OI, IV per strike (SmartAPI), futures price | 9:15, then 15-min | Regime (trend vs pin), level | B (Baltussen, US); India untested, sign convention uncertain |
| 4 | **Rest-of-day momentum into close (thresholded)** | r_ROD = ln(F_14:45 or 15:00 / C_{t−1}); trade if \|r_ROD\|/σ_HAR > z*; optional agreement with r_ONFH | Futures 1-min | Once at 14:45 / 15:00 | Direction | B (Baltussen 60+ futures; R²_OOS 2.88%), with negative OOS evidence for SPY (Rosa) |
| 5 | **Daily jump-model regime** | 2-state JM on EWM downside deviation (half-life 10), EWM Sortino (half-lives 20, 60); λ by TS-CV | Nifty daily returns (+ VIX optional) | Daily | Regime (sizing / risk on-off) | B (US, DE, JP after costs and delay) |
| 6 | **Opening option-order imbalance (first 15 min)** | OIB_C − OIB_P (quote-rule-signed volume, ATM ± 3 strikes) | Option ticks + 5-level depth (must be recorded live) | Once at 9:30 | Direction (rest-of-day tilt) | B (Korea, after costs); India untested, needs data collection |
| 7 | **Level map for targets, stops, room-to-run** | PDH/PDL/PDC, open, VWAP/AVWAP, round 100/500, running extremes with touch count, zero-gamma | Futures 1-min, spot index | Daily + live | Level (trade management) | B (Osler FX; Garzarelli) / C (Chung-Bellotti); VWAP and pivots have no evidence |
| 8 | **Integrated 5-level OFI veto** | Σ_levels (OF^b − OF^a) over 3–5 min / avg depth, time-of-day z-score | Futures 5-level depth snapshots | At each check | Direction-timing veto | B (US, China futures; India: predictability < 30 min, Tripathi et al.) |
| 9 | **Intraday GMM regime + transition gate** | 3-component GMM on ATR ratio, volume z, close location, 5-min return, ER; hold 60–75 min | Futures 1-min / 5-min | Every 5–15 min | Regime (+ entry) | C (Mesfin MNQ; search-bias caveats) |
| 10 | **Trend-day classifier at 10:15** | Logistic on IB ratio, ER_60, VR(5), open vs prior range, ADX, gap/σ, NGE, HAR percentile | Futures 1-min, option chain | Once at 10:15 (re-score at 11:15) | Regime (trend vs range day) | D → test (no evidence found for these indicators) |

**Deprioritise or drop** (failure evidence): plain ORB without filters; gap-fill fade; volume-spike and volume-dry-up signals; liquidity-grab/sweep setups; post-news drift; fast (5–20-day) daily trend as a direction signal; pivot-point levels; first-30-minute → last-half-hour as a stand-alone signal (negative OOS R² in Baltussen's pooled equity sample; post-publication decay in SPY). Sources: [Mesfin (2026)](https://arxiv.org/abs/2605.04004); [Kurth et al. (2026)](https://arxiv.org/abs/2607.01550); [Baltussen et al. (2021)](https://academicweb.nd.edu/~zda/intramom.pdf); [Rosa (2022)](https://onlinelibrary.wiley.com/doi/abs/10.1002/fut.22375).

**Mapping to the current draft setups**
- **H1 (noise band + VWAP trail):** keep as the core directional trigger (rank 2). Add the vol, gamma and room-to-run gates, and separate expiry-day bands.
- **H2 (first-hour trend + VWAP pullback):** the only comparable evidence is mixed. A plain pullback entry failed (80.7% stop-outs, Mesfin), while a regime-gated, ATR-scaled pullback passed (Mesfin's positive control, grade C). Re-specify H2 as "C9 trend-day probability > threshold **and** a pullback to VWAP within σ_rem/2", and test it as a variant of rank 2 rather than as an independent strategy.
- **H3 (gap-down recovery):** keep only as a conditional tilt. Separate "unexplained" gaps (versus GIFT Nifty and US futures) from news gaps, per the jump literature. The unconditional effect (+0.11%) is below option costs.
- **H4 (first-30 minutes → last hour):** replace with rank 4 (rest-of-day, thresholded, gamma-conditioned). Keep r_ONFH only as an agreement filter.

### Gaps
- Historical option tick and depth data for 2019–2026 (needed for C5, C6 history and realistic option P&L) may not be available from SmartAPI. If not, those components can only be tested on data recorded from now on, about one year minimum.
- Whether SmartAPI's option-chain OI updates intraday, and how often, determines whether NGE can be refreshed intraday or only daily.
- Exact current Indian cost schedule (exchange transaction charges, SEBI fee, stamp duty) and the precise dates of SEBI's F&O structural changes were not verified in this note.
