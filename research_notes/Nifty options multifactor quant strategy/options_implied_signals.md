# Options-implied and options-positioning signals for intraday Nifty / Sensex weekly option buying

Scope: which option-market signals have real, out-of-sample, cost-aware predictive value for **intraday index direction, trend-vs-chop regime, or volatility**, and how to compute each one from live option-chain snapshots (Angel One SmartAPI: strike-wise LTP, bid/ask, 5-level depth, volume, OI; 1-min candles for live contracts only; no expired-option or historical intraday OI) plus index/futures prices, NSE/BSE EOD F&O bhavcopy, participant-wise OI and India VIX. Context: 1-lot buyer (Nifty lot 65, Tuesday expiry; Sensex lot 20, Thursday expiry), ₹5,000 capital, alerts only, October 2026.

Evidence grades: **A** = peer-reviewed + India + survives costs; **B** = peer-reviewed or strong replication but not India or not cost-tested; **C** = practitioner backtest / working paper without full results; **D** = anecdote / marketing / tool page. Facts already established in `02_strategy_evidence_part1.md`, `03_indian_signals_data_regulation.md`, `01_market_structure_2026.md` and `04_nifty_measured_facts.md` are referenced, not re-researched.

Headline: **almost nothing in this space is grade A.** The strongest evidence (grade B) is (1) dealer net gamma as a *regime switch* between intraday momentum and reversal / higher vs lower realized volatility, (2) signed option order-flow imbalance in the first 10 minutes (Korea, after costs), and (3) the volatility risk premium as a *cost hurdle* for buyers (India-confirmed). OI walls, max pain, OI build-up classification, PCR changes and futures-premium "sentiment" are popular in India but have no peer-reviewed predictive evidence for index direction.

---

## 1. Dealer gamma exposure (GEX / net gamma): momentum vs mean reversion, who is short gamma in India, and how to compute it

### Takeaway
Peer-reviewed US/China evidence (grade B) consistently finds that when option liquidity providers are **net short gamma**, the index shows **intraday momentum and higher realized volatility**; when they are **net long gamma**, momentum disappears, quiet days revert and volatility is damped. The effect is a **regime conditioner, not a standalone direction signal**, and its size is modest. For India the sign convention is the crux: the US assumption (dealers long calls, short puts) is unjustified here; since ~97% of individual traders are predominantly option *buyers* of both calls and puts, the defensible Indian default is "liquidity providers short both calls and puts" (structurally short gamma), which must be validated on Nifty data before use. One Indian practitioner study exists (Nifty NGE), but its results are not accessible.

### Cited Findings
- **Baltussen, Da, Lammers & Martens (2021), JFE 142:377–403, "Hedging demand and market intraday momentum".** Over 60 futures (equities, bonds, commodities, FX), Dec 1974–May 2020: the last-30-minute return is positively predicted by the return from the previous close to 30 minutes before the close (r_ROD); the effect "reverts over the next days". — [paper PDF](https://academicweb.nd.edu/~zda/intramom.pdf); [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0304405X21001598)
  - **NGE definition (their eq. 13–15):** per strike/maturity, call NGE = Γ × OI × (+100) × P_t; put NGE = Γ × OI × (−100) × P_t; sum over all strikes and maturities, divide by the index market value. Assumptions: (i) all options are facilitated by delta-hedgers, (ii) calls are sold by investors and bought by market makers, (iii) puts are bought by investors and sold by market makers, (iv) market makers hedge exactly their deltas. — [paper PDF](https://academicweb.nd.edu/~zda/intramom.pdf)
  - **S&P 500, Jan 1996–May 2020 (OptionMetrics to 2017, SqueezeMetrics data after; verified virtually identical 2002–2017):** 2,930 negative-NGE days vs 3,158 positive. Regressing r_LH on r_ROD: **NGE_{t−1} < 0: slope 6.63 (t = 4.78), R² 3.58%; NGE_{t−1} ≥ 0: slope 0.82 (t = 1.03), R² 0.05%** (coefficients ×100). Momentum is stronger the more negative NGE is; results hold using puts only. — [paper PDF](https://academicweb.nd.edu/~zda/intramom.pdf)
  - Authors' caveats: NGE is positive on most days; the data miss OTC positions; the sign assumption is a proxy. Main strategy results ignore transaction costs; they state that in S&P 500 futures a one-tick cost still leaves a positive net Sharpe ratio. — [paper PDF](https://academicweb.nd.edu/~zda/intramom.pdf)
  - Grade: **B** (peer-reviewed, very long sample, US; cost treatment only partial).
- **SqueezeMetrics GEX white paper (2016, rev. Dec 2017)** uses the same four assumptions (calls bought / puts sold by market makers), GEX = Γ × OI × 100 for calls and × (−100) for puts, summed over strikes. Claim: the highest vs second-highest GEX quartile give subsequent 1-day S&P 500 standard deviations of **0.55% vs 0.85%**; "high GEX predicts low volatility"; a GEX near zero/negative is associated with an "exponential increase in volatility". No out-of-sample or cost test. — [SqueezeMetrics white paper](https://squeezemetrics.com/download/white_paper.pdf). Grade **C**.
- **Amaya, Garcia-Ares, Pearson & Vasquez (Jan 2025), "0DTE Index Options and Market Volatility: How Large is Their Impact?"** uses Cboe trade records that identify market-maker trades to build the *actual* aggregate options-market-maker (OMM) position in SPX/SPXW at 1-minute frequency, Jul 2020–Jun 2023. OMM gamma is **most often positive**; return variance is negatively related to OMM gamma; on average hedging **reduces** volatility (mean impact −0.19 / −0.17 annualized vol points at daily / 30-min horizons in one model; −2.1 / −2.3 in another). The maximum gamma-induced increase in daily annualized realized vol is **3.3 points** (vs SD of daily changes 4.5 points); the maximum 30-minute increase is **6.4 points** (vs 63.4 points maximum 30-minute change from all causes). The 90th percentile of impact is positive, i.e. hedging *raises* volatility on roughly 10% of days. — [Cboe-hosted PDF](https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf). Grade **B**.
- **Dim, Eraker & Vilkov, "0DTEs: Trading, Gamma Risk and Volatility Propagation"** (SSRN 4692190; SPX 01/2012–14/06/2023): high 0DTE open-interest gamma **does not propagate past volatility**; for options with >1 DTE, OI gamma is associated with **lower** intraday realized volatility; the change in the volatility response to 0DTE volume shocks between early and late sample is only 0.15 SD of return volatility. The later version adds: market-maker inventory gamma is on average positive and negatively related to future intraday volatility, and **positive (negative) MM inventory gamma strengthens intraday reversal (momentum)**. — [SSRN](https://doi.org/10.2139/ssrn.4692190); [WFA version](https://westernfinance-portal.org/viewpaper?n=950096). Grade **B**.
  - Same paper, citing Hu, Kirilova & Muravyev (2023): option market makers primarily manage risk by **active inventory rebalancing rather than delta-hedging**, which weakens the mechanical GEX story. — [WFA version PDF](https://westernfinance-portal.org/viewpaper?n=950096)
  - Same paper's literature summary: Baltussen et al.'s last-half-hour SPX return "is not significantly related to net gamma but is negatively and significantly related to the interaction of net gamma and lagged return" (i.e., NGE conditions momentum rather than predicting direction); Barbon & Buraschi (2020) link intraday autocorrelation to the call-minus-put gamma difference; Anderegg, Ulmann & Sornette (2022) estimate dealer gamma hedging adds 0.7% (0.9%) annualized vol in EUR/USD (USD/JPY). — [WFA version PDF](https://westernfinance-portal.org/viewpaper?n=950096)
- **Ni, Pearson, Poteshman & White (RFS 2021; earlier "Does option trading have a pervasive impact on underlying stock prices?")**: statistically and economically significant **negative relation between the net purchased-option gamma of likely delta hedgers and subsequent absolute stock returns**; positive hedger gamma lowers volatility, negative hedger gamma predicts higher volatility. Individual US stocks, signed open/close data. — [OptionMetrics summary](https://optionmetrics.com/research/ni_pearson_poteschman_white_2020/); [working paper PDF](https://www.ou.edu/dam/price/Finance/CFS/paper/pdf/pearsonPoteshmanWhite.pdf). Grade **B**.
- **Gamma–theta breakeven range (GTBR), anonymous AFA submission dated 2 Jun 2024, "Where does gamma hedge drive the intraday market move?"**: short dealer gamma alone does **not** produce momentum; intraday momentum appears only when the underlying **breaks the gamma-theta breakeven range**, i.e. moves far enough that the hedger's gamma loss exceeds theta income. In the most-short-gamma quintile, days that never breach the GTBR show **no significant momentum**; in the most-long-gamma quintile on quiet days there is significant **reversal (coefficient −1.25)**. Breakeven derived from PnL = Θ/365 + 50·Γ$·r² with Γ$ = Γ·S²/100 (dollar gamma per 1% move). — [AFA PDF](https://afajof.org/management/viewp.php?n=129472). Grade **B−/C** (working paper).
- **Chen et al. (2025), JFM, SSE 50 ETF options (China):** Chinese market makers "usually carry net long positions"; underlying volatility is **negatively related to lagged net gamma exposure** even after controlling for volatility clustering (only the first lag significant). Shows the sign of dealer positioning is market-specific. — [JFM fut.70038](https://onlinelibrary.wiley.com/doi/abs/10.1002/fut.70038). Grade **B** (emerging market, not cost-tested).
- **Expiry pinning (mechanical, near-expiry only):** Ni, Pearson & Poteshman (2005, JFE): closing prices of optionable stocks **cluster at strike prices on expiration dates**, from hedge rebalancing. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0304405X05000577). Golez & Jackwerth (2012, JFE): S&P 500 futures are **pulled toward the ATM strike on serial-option expiry days** and pushed away just before index-option expiry; at least **$115 million notional shift per expiration day**; effect asymmetric (stronger above the strike) and growing over time. — [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0304405X12001365); [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1664261). Grade **B**.
- **India: Motwani, Burrin & Sharma (Alpha Alternatives, Mumbai), "Hedging Demand and Intraday Momentum within the Indian Stock Market"**: applies Baltussen-style regressions and NGE signals to Nifty 50 / Indian equity futures; abstract says "certain elements of hedging demand research translate well" but "unique market features necessitate tailored approaches". Full text blocked (HTTP 403), so sign convention, sample and effect sizes are unknown. — [ResearchGate](https://www.researchgate.net/publication/383567351_Hedging_Demand_and_Intraday_Momentum_within_the_Indian_Stock_Market). Grade **C** (practitioner working paper, results unseen).
- **India GEX tools are assumption-driven.** A Nifty GEX dashboard states plainly: "Dealer positioning is assumed, not measured. Calls are counted +gamma and puts −gamma (the US convention…). NSE publishes no trade-side data to verify that in India — if the true sign is inverted, every bar below and the flip level invert with it." — [draconic.ai Nifty GEX](https://draconic.ai/tools/nifty-gamma-exposure); similar tools: [quintalmind](https://www.quintalmind.com/gamma-exposure/nifty), [stockmojo](https://stockmojo.in/gamma-exposure/nifty), [optionsflow.in](https://optionsflow.in/). Grade **D**.
- "Gamma blast" claims (Nifty moving 50–150 points in 10–30 minutes near expiry from hedging of concentrated OI) are marketing-grade. — [MarketsEasy](https://marketseasy.in/blog/gamma-blast-nifty-options-expiry-day). Grade **D**.
- **Who holds what in India.** SEBI (Aug 2026, FY25–FY26): ~97% of individual traders predominantly *bought* options, ~2% predominantly sold; 99% of FPI and prop profits came from algo entities (prop ~₹44,000 cr gross, FPI ~₹14,000 cr); 0DTE share of index-option turnover 59% in FY26 (70% FY25). — [SEBI study PDF](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf) (via `01_market_structure_2026.md`); FY25 figures also in [Business Standard](https://www.business-standard.com/amp/markets/news/net-losses-of-traders-in-fo-widens-in-fy25-sebi-study-125070701221_1.html).
- **NSE participant-wise OI** (free, daily) gives long and short OI for Client / DII / FII / Pro in index calls and index puts (and futures), aggregated across all index underlyings, strikes and expiries. — [OIData guide](https://www.oidata.in/blog/participant-wise-open-interest-nse); [stockmojo explainer](https://stockmojo.in/learn/participant-wise-open-interest/)

### Inferences
- **Role:** regime/volatility conditioner. Use "hedgers short gamma + index already moved beyond the breakeven range" as a *permission* for trend-following entries (buy options in the direction of the move), and "hedgers long gamma / inside breakeven range" as a *chop/mean-reversion* flag (stand aside or fade with defined risk). Do not use GEX sign alone to predict direction.
- **Indian sign convention (our reasoning, to be validated):** US assumptions come from institutions buying puts and overwriting calls. In India the dominant end-user flow is retail *buying* both calls and puts, while prop/FPI algos supply liquidity. The natural Indian default is therefore **"liquidity providers are short all listed index options"**, which makes aggregate hedger gamma always ≤ 0; the *magnitude and strike concentration*, not the sign, carry the information. This is opposite to the US convention for calls and must not be copied from US-style dashboards.
- Many Indian premium sellers probably manage risk with **stop-losses and strike rolling rather than continuous delta-hedging** (consistent with Hu–Kirilova–Muravyev's finding that even US MMs rely on inventory management). Stop-loss buy-backs of short calls on rallies and short puts on falls are themselves trend-following, so the *qualitative* short-gamma → momentum prediction may still hold even if "hedging" is the wrong word. It is equally possible that prop desks are net long gamma at times (e.g., buying cheap wings from the ~2% of individuals who sell), so the sign must be measured.
- **Validation plan using free data (most important test in this note):** EOD bhavcopy gives strike-wise OI and settlement/close prices for every Nifty option every day back many years, so a **daily NGE_{t−1} series can be reconstructed historically** (compute IV and gamma per strike from EOD prices). Combine with 1-min Nifty futures history (broker API) to run the Baltussen regression r_LH,t = a + b·r_ROD,t + c·r_ROD,t·1[NGE_{t−1} < median] on Nifty, under each sign convention below, with walk-forward splits and a structural break at Sep 2025 (Tuesday expiry) and Aug 2026 (closing auction). Keep the convention that wins out-of-sample.
- Weekly 0DTE OI dominates gamma near expiry (gamma ∝ 1/√T), so on Nifty Tuesdays and Sensex Thursdays GEX will be dominated by the expiring series; on other days the next weekly dominates. The 3 Aug 2026 closing-auction settlement means expiry-day pinning dynamics may differ from pre-2026 history.

#### Computation recipe (per snapshot, e.g., every 1–5 min)
1. **Forward:** F = synthetic forward from put-call parity at the 3 strikes nearest ATM for the expiry being processed (Section 7), not the monthly future.
2. **Time:** T in years to expiry (15:30 IST; on expiry day consider 15:15 because the settlement is formed in the 15:15–15:35 auction). Use trading-time: T = (minutes left today + 375 × full sessions left + overnight weight w × nights left) / (375 × 252), with w ≈ ratio of overnight to intraday variance estimated from your own data.
3. **IV per strike:** invert Black-76 on mid = (bid + ask)/2 (fallback LTP if spread < 1 tick-multiple), r ≈ 0 when using F. Use OTM options only (calls K > F, puts K < F) and copy IV across for gamma of the ITM counterpart. Drop strikes with no two-sided quote or spread > 20% of mid.
4. **Gamma:** Γ_K = φ(d1)/(F·σ_K·√T), d1 = [ln(F/K) + 0.5σ²T]/(σ√T).
5. **Rupee gamma per 1% move:** G_K = Γ_K × F² × 0.01 × OI_K(units). (Check whether Angel One/NSE OI is in contracts or units; multiply contracts by lot size 65 for Nifty, 20 for Sensex.)
6. **Three sign conventions, compute all three:**
   - US: NGE_US = Σ G_call − Σ G_put.
   - India-default (hedgers short everything): NGE_IN = −Σ (G_call + G_put). Also track **gamma concentration** = share of Σ|G| within ±1 expected move of F.
   - Participant-weighted (EOD prior day): from participant OI, h_c = (Pro_short + FII_short − Pro_long − FII_long)/total index-call OI, same h_p for puts; NGE_PW = −Σ (h_c·G_call + h_p·G_put). (Aggregation across indices/expiries makes this crude.)
7. **Normalize** by the 20-day average daily traded value of Nifty futures (or index free-float market cap, as Baltussen). Z-score by days-to-expiry bucket.
8. **Flip level:** recompute NGE at hypothetical F' on a grid (±3%) holding each strike's IV fixed (sticky strike); the F' where NGE changes sign is the "gamma flip" (practitioner concept, grade C/D).
9. **Breakeven range (GTBR):** for the aggregate hedger book, r* (%) = sqrt(−Θ_book / (365 × 50 × Γ$_book)) with Γ$_book = Σ OI·Γ·F²/100 and Θ_book = Σ OI·Θ (annual). A simpler proxy: the 0DTE ATM straddle price as % of F ≈ the day's breakeven move. Flag when |F − open| > r*.

### Gaps
- No accessible peer-reviewed estimate of Nifty or Sensex GEX and its effect on intraday momentum; Motwani et al. numbers unseen.
- No public data identify which Indian participant is on which side at strike level; participant-wise OI is EOD and aggregated across all index products.
- Whether Indian prop/FPI sellers delta-hedge continuously (vs stop-loss/roll) is unknown; no study found.
- Intraday OI update frequency from NSE via Angel One websocket was not verified (OI is typically refreshed periodically, not per trade).

---

## 2. Implied volatility skew, smile slope and risk reversals as directional or crash signals

### Takeaway
Skew is well established as a *price of crash protection and of buying/selling pressure*, and in some markets it predicts **option returns** (delta-hedged) and **cross-sectional stock returns** over days to months. I found **no evidence, Indian or global, that index skew predicts the next few hours of index direction**, and no Nifty-specific skew-return study. For an intraday buyer, skew is a **strike-selection and stress filter**, not a direction signal (grade C at best for intraday use).

### Cited Findings
- **Indian option smile definitions and drivers (Agarwalla, Varma and co-authors, JFM):**
  - IVSKEW = IV(Δ = 0.25) − IV(Δ = 0.75), with IV from a quadratic smile fitted to NSE bhavcopy data; ATM IV at Δ = 0.5. — [Saurav, Agarwalla & Varma (2023), JFM 44(3):484–517](https://onlinelibrary.wiley.com/doi/10.1002/fut.22478)
  - Indian single-stock options 2011–2019: ATM IV is explained mainly by fundamental and predicted risk; **the cross-section of skew is driven by risk premia and buying/selling pressure** (heterogeneous beliefs, lottery-like and bubble-like stock features). Uses Black-76 on time-matched single-stock futures to avoid carry/dividend estimation. — [Agarwalla, Saurav & Varma (2021), JFM 42(2):231–249](https://onlinelibrary.wiley.com/doi/10.1002/fut.22263). Grade **B** (India, explanatory not predictive).
  - Near 52-week highs (lows), risk-neutral skewness and OTM call volume fall (rise) and OTM put volume rises (falls), consistent with anchoring; OTM calls were 21.9% and OTM puts 9.9% of Indian stock-option volume (Indian investors use options more for upside speculation than insurance). — [Saurav, Agarwalla & Varma (2023), JFM 43(11):1531–1558](https://onlinelibrary.wiley.com/doi/10.1002/fut.22446). Grade **B**.
- **Skew predicts index-option returns, not index direction (China):** risk-neutral skewness from the SSE 50 ETF option smirk (level/slope/curvature method of Zhang & Xiang) negatively predicts 1-day, 2-day and 1–4-week delta-neutral call-option returns, in-sample and out-of-sample; the "293% maximum annual return" ignores costs. — [Guo, Liu, Chen & Lung (2025), JFM 45(7):705–731](https://onlinelibrary.wiley.com/doi/10.1002/fut.22590). Grade **B** for option returns; not a direction signal.
- **Put-demand / order-flow channel (related to put skew):** weekly ISE index-put order flow (mainly net put *buying*) **positively** predicts weekly S&P 500 returns, more so in high-VIX periods and after macro announcements (risk-protection demand is compensated). — [Chordia, Kurov, Muravyev & Subrahmanyam (2021), Management Science 67(3):1758–1778](https://pubsonline.informs.org/doi/abs/10.1287/mnsc.2019.3529). Chen et al. (2019) find order imbalance in **deep OTM index puts negatively** predicts market returns (intermediary constraints); Chordia et al. attribute put-imbalance predictability to retail risk-protection strategies. — [summarized in JFM fut.70038](https://onlinelibrary.wiley.com/doi/abs/10.1002/fut.70038). Grade **B**, horizon weekly, contradictory signs depending on measure.
- Volatility-index term structure (not skew) has been described as a contrarian timing tool (Copeland & Copeland 1999; Fassas & Hourvouliades 2019), as summarized in an Indian-context literature review. — [Lakshmi et al. (2023), IJFE 29(3)](https://onlinelibrary.wiley.com/doi/10.1002/ijfe.2818). Grade **B/C** (secondary).

### Inferences
- **Use 1 (structure choice):** when put skew is steep (OTM puts rich), bearish views are better expressed with **put debit spreads** (the short OTM leg recovers skew premium) than naked OTM puts; when the call wing is rich (retail lottery demand, consistent with Indian OTM-call-heavy volume), prefer call spreads over naked OTM calls.
- **Use 2 (stress filter):** a sharp intraday *rise* in ATM IV together with steepening put skew / falling 25-delta risk reversal signals demand for protection; treat it as "risk-off regime, avoid fresh long calls" rather than a timing signal. Evidence for this is indirect (put order-flow studies at weekly horizon), so grade **C**.
- Near weekly expiry the smile is dominated by 0DTE microstructure (huge gamma, tick-size floors on cheap OTM options), so skew metrics on the expiring series are noisy on expiry day; compute skew on the **next weekly** on expiry days.

#### Computation recipe (every 5 min; history from EOD bhavcopy for daily z-scores)
1. Per expiry, take OTM strikes with valid two-sided quotes; compute IV (Section 1 step 3) and Black-76 delta.
2. Fit IV(x) = a + b·x + c·x², x = ln(K/F)/(σ_ATM√T) (standardized moneyness), weights = 1/spread. Slope b and curvature c are the smile slope and convexity.
3. RR25 = IV(25Δ call) − IV(25Δ put); BF25 = ½[IV(25Δ call) + IV(25Δ put)] − IV_ATM; Indian-literature IVSKEW = IV(Δ = 0.25) − IV(Δ = 0.75) on the call-delta axis.
4. Signal = 15–30-min change in RR25 and b, z-scored against the same days-to-expiry and time-of-day bucket (build the intraday history yourself from the live feed; EOD history from bhavcopy).

### Gaps
- No study found on whether **Nifty index skew** (level or change) predicts Nifty returns or crashes at any horizon; a targeted scholarly search returned only stock-level Indian papers.
- Xing, Zhang & Zhao (2010, JFQA) is widely cited as showing that steep stock-level put skew predicts lower future stock returns, but it is cross-sectional (stocks) and I did not verify its effect sizes in this session.
- No intraday (minutes-to-hours) skew-return evidence in any market was found.

---

## 3. IV term structure (near-week vs next-week ATM IV; India VIX vs near-week IV) as a stress / regime indicator

### Takeaway
Implied volatility (India VIX, ATM IV) leads realized volatility in India (grade A/B), and the slope of the volatility term structure carries information **beyond the level** about future realized volatility and about **option returns**: an inverted structure (front IV above back IV) marks stress and larger expected moves, but it is also when front options are most expensive, so it is a **regime flag for bigger moves, not a "buy options" signal**. No Indian study of weekly term structure was found.

### Cited Findings
- Implied volatility outperforms historical volatility in forecasting future volatility globally and in India (Jain et al. 2019; Panda et al. 2008); in 2020 India VIX and Nifty ATM IV rose days before backward-looking EWMA caught up. — [Agarwalla, Varma & Virmani (2021), JFM 41(10):1498–1519](https://onlinelibrary.wiley.com/doi/10.1002/fut.22240). Grade **B** (India).
- India VIX is a good predictor of Nifty realized volatility, mean-reverting and asymmetric. — [NSE Working Paper 9/2013](https://nsearchives.nseindia.com/research/content/res_WorkingPaper9.pdf) (from `03_indian_signals_data_regulation.md`). Grade **A/B**.
- Own data (2015–Oct 2026): India VIX exceeded the next 21 days' realized vol on **80.5%** of days (median ~3.3 vol points); 2026 is the weakest year (premium positive on only 67% of days). — `04_nifty_measured_facts.md`.
- The VIX is more informative than historical RV for future RV, and **the volatility term structure contains additional information beyond the VIX and historical RV**; the 1-day VIX is the best predictor of 1-day RV, longer tenors are weaker. — [VIX term structure and future realized volatility, Applied Economics (2025)](https://www.tandfonline.com/doi/full/10.1080/00036846.2025.2601895); see also [Term Structure of Option-Implied Volatility and Future Realized Volatility, EMFT (2019)](https://ideas.repec.org/a/mes/emfitr/v55y2019i13p2997-3022.html). Grade **B** (abstract-level verification only).
- **Johnson (JFQA 2017), "Risk premia and the VIX term structure":** the slope of the VIX term structure predicts returns to variance assets (variance swaps / VIX futures), i.e. it times the volatility premium, not equity direction. — [working paper PDF](https://bauer.uh.edu/departments/finance/documents/seminars/Johnson_020712.pdf). Grade **B**.
- **Vasquez (2017), JFQA 52(6):2727–2754:** straddles on stocks with a **high** IV term-structure slope (long-term IV above short-term) **outperform** straddles with low slope by an economically and statistically significant amount; robust to standard factors and jump risk. Mirror image: when short-dated IV is high relative to long-dated (inverted), short-dated straddles subsequently do worse. — [IDEAS](https://ideas.repec.org/a/cup/jfinqa/v52y2017i06p2727-2754_00.html); [ResearchGate](https://www.researchgate.net/publication/321114332_Equity_Volatility_Term_Structures_and_the_Cross_Section_of_Option_Returns). Grade **B** (US stocks, cross-section).
- **0DTE is the most expensive point of the curve:** SPX 0DTE options carry a far higher variance risk premium than 1-DTE, 2–5-DTE and longer buckets (2012–2023). — [Dim, Eraker & Vilkov](https://westernfinance-portal.org/viewpaper?n=950096). Grade **B**.

### Inferences
- **Role:** regime / volatility. An inverted structure (current-week ATM IV above next-week, or current-week IV above India VIX after adjusting for the normal day-of-week pattern) → expect larger realized moves today/tomorrow, widen stops and targets, allow breakout-style entries; but also expect options to be expensive, so prefer **debit spreads** over naked buys.
- India VIX is a ~30-day measure built from the monthly-series order book (verify NSE's current methodology), while trading happens in weekly options; the useful spread is **IV_current-week vs IV_next-week (forward variance)**, plus **India VIX vs next-week IV** as a slower check.
- Two weekly curves exist (Nifty Tuesday, Sensex Thursday). Because the two indices are highly correlated, comparing the Sensex weekly ATM IV with the Nifty weekly IV at a similar DTE may show which instrument is cheaper on a given day (our idea, untested).
- Front-week IV has a strong mechanical calendar (weekend, holiday and event days inside the window; expiry-day decay), so the raw slope must be compared with its own **DTE-matched history**, otherwise every Monday/Tuesday looks "inverted".

#### Computation recipe (every 5 min; daily version from EOD bhavcopy)
1. σ1 = ATM IV of current weekly (interpolate IV at K = F), σ2 = ATM IV of next weekly; total variances w_i = σ_i²·T_i (trading-time T, Section 1).
2. Forward vol between expiries: σ_fwd = sqrt((w2 − w1)/(T2 − T1)). Inversion score TS = σ1 − σ_fwd (or σ1/σ2).
3. TS_VIX = σ_next-weekly − India VIX (both annualized).
4. Event adjustment: on known event days (RBI MPC, Budget, US CPI/FOMC overnight, state election results), remove an event variance estimate before comparing; otherwise flag "event day" separately.
5. Z-score TS by (DTE of current weekly, time-of-day) using your own accumulating history.

### Gaps
- No Indian study on whether an inverted weekly term structure predicts larger Nifty realized moves or option returns.
- Effect sizes for the term-structure → realized-volatility papers were verified only at abstract/summary level.

---

## 4. Implied minus realized volatility (VRP) as a timing tool for option buyers

### Takeaway
In India the VRP is real (options are overpriced on average) and **mainly an overnight phenomenon**: intraday (open-to-close) short-option returns are negative and insignificant, i.e. an intraday buyer does not pay much VRP *before costs*, while holding long options overnight does pay it (grade A/B, India). Conditioning purchases on **IV being low relative to a realized-volatility forecast** is supported by US cross-sectional and straddle evidence (grade B), but I found no index-level, intraday, cost-tested study showing that long options have *positive* expectancy when VRP is low. For a buyer the VRP is best used as a **cost hurdle and a no-trade filter**.

### Cited Findings
- **India:** VRP exists and is priced; short-option strategies earn significant returns before costs but most profit disappears after normal transaction costs (Nifty, 2009–2011); VRP follows an AR(3) and is partly forecastable. — [Garg & Vipul (2015), JFM 35(9):795–812](https://doi.org/10.1002/fut.21680) (from `02_strategy_evidence_part1.md`). Grade **A/B**.
- **India:** overnight short-option returns are positive and highly significant; **intraday (open-to-close) short-option returns are "largely negative and insignificant"**; the VRP is "mainly a reward for overnight risk"; after noon short calls lose and short puts gain; overnight selling is not profitable after explicit and implicit costs (Nifty near-month, 2017–2020). — [Bhat, Pandey & Nageswara Rao (2024), JFM 44(8):1320–1337](https://doi.org/10.1002/fut.22512) (from `02_strategy_evidence_part1.md`). Grade **A/B** (pre-weekly-dominance sample).
- Own data: implied 1-day move (VIX/√252) averaged **1.04%** vs actual average |daily move| **0.70%**; only 21.1% of days exceeded the implied 1-SD move (normal 31.7%). — `04_nifty_measured_facts.md`.
- SEBI: individual options losses were "largely independent of market direction"; 82.1% of individuals were losers before costs. — `01_market_structure_2026.md` / [SEBI PDF](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf).
- **US 0DTE:** ATM 0DTE calls, puts and straddles bought at the end of each 30-minute bar and held to the 16:00 expiry have **negative average returns**; straddle losses grow in absolute value toward the close and are an order of magnitude larger in the last bar than at noon; return dispersion doubles in the final bar (SPX, 2012–2023). — [Dim, Eraker & Vilkov](https://westernfinance-portal.org/viewpaper?n=950096). Grade **B**.
- **Bollerslev, Tauchen & Zhou (2009), RFS:** VRP = model-free implied variance (VIX²) minus realized variance from high-frequency data; high VRP predicts high future equity returns; over 1990–2007 the monthly-horizon R² is just above 1%, the **quarterly** regression has t = 2.86 and **R² 6.82%**; Black-Scholes IV or daily-data RV weaken the result (R² 2.16% with "old" measures). — [RFS PDF](https://public.econ.duke.edu/~boller/Published_Papers/rfs_09.pdf). Grade **B**; monthly/quarterly horizon, irrelevant for intraday direction.
- **Goyal & Saretto (2009), JFE:** sorting stocks on historical (12-month) RV minus 1-month ATM IV, a zero-cost strategy long straddles/delta-hedged options on high (RV − IV) stocks and short low (RV − IV) earns economically and statistically significant monthly returns. — [ResearchGate](https://www.researchgate.net/publication/222532340_Cross-section_of_option_returns_and_volatility). Grade **B** (stock cross-section, monthly).
- Simon (2010): short straddles worked better when IV was high relative to forecast RV (TLT options); stop-losses reduced profitability. — `02_strategy_evidence_part1.md`. Grade **B**.

### Inferences
- **Rule 1 (A/B-supported):** an intraday buyer should **not hold long options overnight** unless the expected overnight move clearly exceeds the overnight VRP; the Indian premium is concentrated there.
- **Rule 2 (B-supported):** buy only when the **remaining-session implied move is not rich versus a realized-volatility forecast** (IV/RV-forecast ratio in the bottom third of its DTE-matched history), or when a directional model's expected move exceeds the straddle breakeven plus costs.
- **Rule 3 (B, US 0DTE):** avoid buying 0DTE options late in the expiry session as a default; that is where the premium is largest and payoff dispersion highest (Nifty Tuesday / Sensex Thursday afternoons, plus the new 15:15–15:35 auction risk).
- When IV is rich but the directional signal is strong, use debit spreads (consistent with `04_nifty_measured_facts.md`).

#### Computation recipe
1. **Implied remaining-session vol (0DTE or nearest weekly):** ATM straddle S_ATM = C(K_ATM) + P(K_ATM) (mids). Since S_ATM ≈ F·σ·√T·√(2/π), σ_impl = (S_ATM/F)·√(π/2)/√T_rem. The breakeven move for a long straddle to expiry is S_ATM points.
2. **Realized-vol forecast:** HAR on 5-min Nifty futures realized variance: RV_{t+1} = b0 + b_d·RV_d + b_w·RV_w(5-day avg) + b_m·RV_m(22-day avg), fitted on your own history; scale to the remaining session with an intraday U-shaped variance profile estimated from 1-min data (share of daily variance remaining after time τ).
3. **VRP_now = σ_impl − σ_forecast** (vol points), and ratio σ_impl/σ_forecast; z-score by DTE and time-of-day.
4. **Trade gate:** require E[|move| from directional model] > breakeven move of the chosen structure + round-trip costs (₹20×2 brokerage, 0.15% STT on sell-side premium from Apr 2026, exchange/SEBI/GST/stamp, plus half-spread × 2).

### Gaps
- No index-level study (any market) showing that *buying* options when VRP is low/negative earns positive returns after costs at intraday horizons.
- Bhat et al.'s sample (2017–2020, monthly-dominated) predates the weekly/0DTE era and the Apr 2026 STT increase; the intraday VRP on Nifty weekly 0DTE options today is unmeasured. Measure it from your own live snapshots (IV at time t vs realized to close).

---

## 5. Open-interest dynamics: long/short build-up classification, OI walls, max pain, intraday change in PCR-OI

### Takeaway
These are the most popular Indian retail signals and the least evidenced. **No peer-reviewed test of the price-change × OI-change classification (long build-up, short covering, etc.) for index direction was found.** OI walls and max pain have a plausible mechanism (expiry pinning from hedge rebalancing, grade B in the US) but only near expiry, with small magnitude, and Indian accuracy claims are anecdotal (grade D). PCR-volume does not predict Nifty; OI-PCR shows weak Granger causality (B/C, established earlier). Use OI-derived levels for **targets/stops on expiry day**, not for direction.

### Cited Findings
- PCR (volume) has no predictive power for Nifty; OI-PCR Granger-causes returns, extremes are a moderate contrarian tool. — [MDPI 2019](https://www.mdpi.com/2227-7099/7/1/24) (from `03_indian_signals_data_regulation.md`). Grade **B/C**.
- Growth in OTM call OI predicts market returns in Korea. — [Seo, Byun & Kim (2020), JFM](https://doi.org/10.1002/fut.22095) (from `03`). Grade **B**.
- Trader identity matters more than aggregate OI: in Taiwan index futures, institutional (especially foreign) trading imbalances forecast returns and reduce volatility, while individual trading forecasts poorly and raises volatility; extreme imbalances matter most. — [Kuo, Chung & Chang (2015), JFM 35(3):222–244](https://onlinelibrary.wiley.com/doi/10.1002/fut.21683). Grade **B**. (India publishes trader-type positions only EOD.)
- **OI build-up states (practitioner definitions):** long build-up = price up, OI up; short build-up = price down, OI up; short covering = price up, OI down; long unwinding = price down, OI down; claims that short-covering rallies fade and long-build-up rallies last are asserted without backtests. — [NiftyTrader guide](https://www.niftytrader.in/markets/open-interest-oi-long-short-build-up-guide/); [NiftyScanner](https://niftyscanner.in/learn/short-covering-open-interest/). Grade **D**. A 2008 Business Standard F&O column ("Build up in longs should take Nifty up") is typical media usage. — [Business Standard](https://www.business-standard.com/amp/article/markets/f-o-build-up-in-longs-should-take-nifty-up-108061200004_1.html). Grade **D**.
- **Pinning mechanism** (supports "OI walls as magnets" near expiry only): stock prices cluster at strikes on expiration dates ([Ni, Pearson & Poteshman 2005](https://www.sciencedirect.com/science/article/abs/pii/S0304405X05000577)); S&P 500 futures are pulled to the ATM strike on serial expiries, ≥$115m notional per expiry ([Golez & Jackwerth 2012](https://www.sciencedirect.com/science/article/abs/pii/S0304405X12001365)). Grade **B** (US).
- **Max pain:** a US study ("No Max Pain, No Max Gain: A Case of Predictable Reversal", US stocks 1996–2021) reports a long-short max-pain strategy averaging ~0.4% per week, concentrated in smaller, less liquid stocks (reported via a secondary source). — [OptionCharts blog](https://optioncharts.io/blog/how-accurate-is-max-pain-in-option-trading). Grade **B−** (unverified primary). Indian claims that Nifty settles within 100 points of max pain 55–65% of the time, or that max pain matches 60–70% of the time, are unsourced; one logged test of 19 expiries reportedly found max pain predicted the close *worse* than assuming no move. — [Stoxra](https://stoxra.com/blog/max-pain-theory-nifty-options-trading); [NiftyDesk](https://niftydesk.app/blog/max-pain-theory-options-trading); [Zerodha Varsity on max pain/PCR](https://zerodha.com/varsity/chapter/max-pain-pcr-ratio/). Grade **D**.
- An "analytical study on max pain theory and PCR" exists in a low-tier journal (not evaluated). — [ResearchGate](https://www.researchgate.net/publication/351686756_Journal_of_Technology_ANALYTICAL_STUDY_ON_MAX_PAIN_THEORY_AND_PCR_IS_THE_NOVEL_STRATEGY_IN_OPTIONS_TRADING). Grade **D**.

### Inferences
- The ΔP × ΔOI classification is logically weak for index futures: every OI change creates one new long *and* one new short, so the label simply infers the aggressor from price direction; it is close to restating price momentum. Treat as **popular but unevidenced**; include only as a candidate feature in walk-forward testing.
- Strike OI walls are better read as **gamma concentration** (Section 1): large OI near spot on expiry day + hedgers short gamma → acceleration once breached; + hedgers long gamma → magnet. Use them for **target and stop placement** on expiry day.
- Max pain and OI walls can be **tested historically for free**: EOD bhavcopy gives strike-wise OI on the day before each weekly expiry; compare max pain / walls with the final settlement for all Nifty weekly expiries (2019–2026) and Sensex weeklies, with a break at the Aug 2026 closing-auction change. Benchmark against the "no change from previous close" forecast.
- Intraday ΔPCR-OI mixes hedging, writing and retail buying; without trade direction it cannot distinguish "put writing" (bullish) from "put buying" (bearish). Pairing ΔOI with the option's price change (OI up + premium down ≈ writing) is the standard practitioner fix; it is untested.

#### Computation recipe (5–15-min bars)
1. Futures state: dP = ΔP_fut, dOI = ΔOI_fut over the bar; classify only when |dP| > 0.5·SD(dP) and |dOI| > 0.5·SD(dOI) (rolling 20-day, same time-of-day); else "neutral".
2. Option writing proxy per strike (ATM ± 5 strikes): writing if ΔOI > 0 and Δpremium < 0 (after removing the delta effect: Δpremium − Δ·ΔF); buying if ΔOI > 0 and residual Δpremium > 0.
3. Walls: K_call-wall = argmax_{K > F} OI_call(K); K_put-wall = argmax_{K < F} OI_put(K); track ΔOI since open at each wall.
4. Max pain: K* = argmin_K Σ_i [OI_call(K_i)·max(K − K_i, 0) + OI_put(K_i)·max(K_i − K, 0)] over listed strikes K.
5. PCR_OI = Σ OI_put / Σ OI_call (current weekly, ±10 strikes); ΔPCR since 9:30.

### Gaps
- No peer-reviewed or rigorous practitioner backtest of OI build-up classification, OI walls, max pain or intraday PCR changes on Nifty/Sensex weeklies.
- Unknown how the Aug 2026 closing auction changes expiry-day pinning.

---

## 6. Option order-flow imbalance at the open, and whether it can be approximated without trade-initiator flags

### Takeaway
The best directional evidence in this note: in KOSPI 200 options, the **signed order imbalance of OTM options in the first 10 minutes** predicts the rest-of-day index and futures return, out-of-sample, and a simple timing rule stays profitable **after costs** (grade B; Korea, uses exchange trade-direction and investor-type data). The signal comes from large/institutional traders, OTM options, and high-uncertainty days. With Angel One's websocket (LTP, last traded quantity, cumulative volume, best bid/ask) the trade sign can be approximated with the quote/Lee-Ready rule, which classifies roughly 60–83% of option trades correctly, so expect a weaker signal. This must be forward-tested on collected live data, because historical option ticks are not available.

### Cited Findings
- **Kang, Kang & Lee (2021/2022), JFM 42(3):338–364, "Who and what drives informed options trading after the market opens?" (KOSPI 200, ~1,106 trading days):** intraday momentum is insignificant, but the first-10-minute option order imbalance (OpOib) significantly predicts the index return for the rest of the day (coefficient t = 3.34; with controls t = 3.25) and the futures return (t = 2.98). — [JFM](https://onlinelibrary.wiley.com/doi/10.1002/fut.22301)
  - A 1-SD OpOib shock forecasts **+0.10%** index and **+0.08%** futures return over the rest of the day; **OOS R² 1.85%** (index) and **1.15%** (futures). — [JFM](https://onlinelibrary.wiley.com/doi/10.1002/fut.22301)
  - Only the first 10 minutes (9:00–9:10) predict; the 9:10–9:30 imbalance does not (t = 0.30). The first-10-minute index return loses its predictive power once OpOib is included. — [JFM](https://onlinelibrary.wiley.com/doi/10.1002/fut.22301)
  - Both call and put imbalances (signed so that positive = bullish) predict individually (OOS R² 1.63% calls, 1.01% puts). **OTM options drive it; ATM and ITM imbalances are not significant** (informed traders prefer leverage and trade direction, not volatility). — [JFM](https://onlinelibrary.wiley.com/doi/10.1002/fut.22301)
  - Big traders (≥2,000 contracts in the first 10 min) predict (t ≈ 3.3); small traders do not; predictability is driven by institutions, not individuals, and is insignificant when VKOSPI is low. — [JFM](https://onlinelibrary.wiley.com/doi/10.1002/fut.22301)
  - **Timing strategy (go with sign of OpOib vs its mean):** index 8.20 bps/day gross, Sharpe 1.79, hit rate 54.1%; **after costs 5.20 bps/day, Sharpe 1.14**; futures after costs 4.26 bps/day, Sharpe 0.91. Trading only when |OpOib − mean| > 2 SD: 127 days, 22.5 bps/day gross (63% hit rate), **19.5 bps after costs** (index), 17.1 bps (futures, Sharpe 1.30). — [JFM](https://onlinelibrary.wiley.com/doi/10.1002/fut.22301). Grade **B**.
- **Conflicting Korean evidence:** institution-vs-retail order imbalances in KOSPI 200 *futures* predict short-term returns, while *options* imbalances predict volatility, not returns (daily horizons). — [Bae & Dixon (2018), JFM 38(2):175–198](https://onlinelibrary.wiley.com/doi/10.1002/fut.21863). Grade **B**.
- **Separating informed from arbitrage flow:** decomposing option order imbalance using synthetic positions from matched calls and puts, the "informed" component (SOI) positively predicts next-interval futures/spot returns (1 SD → +0.092 bp futures, +0.674 bp spot), while convergence-driven imbalance (COI, arbitrage against options–futures mispricing) predicts **negatively**; foreign investors drive options–futures convergence trades. — [Lee, Ryu, Yang & Yu (2026), JFM](https://onlinelibrary.wiley.com/doi/10.1002/fut.70142) (via Wiley Scholar Gateway passages). Grade **B**.
- **Pan & Poteshman (2006), RFS 19(3):871–908:** put-call ratios built from *buyer-initiated, position-opening* volume predict stock returns: low-PCR stocks beat high-PCR stocks by >40 bp next day and >1% next week; the public unsigned PCR carries far less information. — [IDEAS](https://ideas.repec.org/a/oup/rfinst/v19y2006i3p871-908.html). Grade **B** (stocks).
- **Chordia et al. (2021):** weekly index-put order flow positively predicts weekly S&P 500 returns. — [Management Science](https://pubsonline.informs.org/doi/abs/10.1287/mnsc.2019.3529). Grade **B**.
- **Trade-sign inference for options is error-prone:** on CBOE data the quote rule correctly signs 83% of classifiable option trades, Lee-Ready 80%, Ellis-Michaely-O'Hara 77%, the tick rule only 59%; outside-quote and reversed-quote trades are badly misclassified; other work finds Lee-Ready signs only ~60–64% of option trades. — [Savickas & Wilson (2003) record](https://www.econbiz.de/Record/on-inferring-the-direction-of-option-trades-savickas-robert/10005407236); [Grauer, Schuster & Uhrig-Homburg, "Option Trade Classification"](https://www.econbiz.de/Record/option-trade-classification-grauer-caroline/10013290141). Grade **B**.

### Inferences
- **Role:** direction (the only option-flow signal with cost-surviving index-level evidence). Indian analogue window: **9:15–9:25 IST**, predicting 9:25–15:15.
- Expect attenuation in India: (a) sign misclassification (quote rule ~80% at best, tick rule ~59%); (b) no investor IDs, while ~97% of individuals are buyers, so aggregate imbalance is dominated by retail noise; (c) 0DTE gamma trading by algos. Partial fixes: weight by trade size (keep prints ≥ 90th-percentile quantity, as a "big trader" proxy), use OTM strikes only, require a 2-SD signal (Kang et al.'s best-after-cost variant traded only 127 of ~1,100 days).
- On expiry days the 0DTE OTM flow is mostly lottery/gamma trading; consider computing the imbalance on the **next weekly** on Nifty Tuesdays / Sensex Thursdays (our judgment, untested).

#### Computation recipe (websocket, tick or sub-second snapshots)
1. Subscribe (full/snap-quote mode) to current-weekly Nifty options, strikes ATM ± 10 (≈42 tokens) plus the near future; record per update: LTP, last traded qty, cumulative volume, best bid/ask (and 5-level depth), exchange timestamp.
2. For each update i with ΔV_i = vol_i − vol_{i−1} > 0: sign s_i = +1 if LTP_i ≥ ask_{i−1}; −1 if LTP_i ≤ bid_{i−1}; otherwise +1/−1 if LTP_i is above/below mid_{i−1}; if exactly at mid, use the tick rule (vs last different LTP). Signed volume q_i = s_i·ΔV_i.
3. **OpOib_bull(9:15–9:25)** = [Σ_OTM calls q_i·|Δ_i| − Σ_OTM puts q_i·|Δ_i|] / Σ_OTM |q_i|·|Δ_i| (delta-weighted; also compute the unweighted contract version and a premium-weighted version).
4. Large-trade version: same, restricted to updates with ΔV_i ≥ 90th percentile of ΔV for that strike over the prior 20 sessions.
5. **With only 1-min candles (fallback):** bulk volume classification: buy fraction per bar = Φ(ΔClose/σ_ΔClose); signed volume = V·(2·buy fraction − 1) (Easley, López de Prado & O'Hara's BVC; not verified in this session). Expect lower accuracy.
6. Signal: z = (OpOib_today − mean_60d)/SD_60d; act only if |z| > 2 and the VRP gate (Section 4) passes; direction = sign(z).

### Gaps
- No Indian study of opening option order-flow imbalance; no historical Nifty option tick data available to us, so the signal can only be validated by **collecting several months of live data** first.
- Angel One websocket limits (tokens per connection, update frequency, whether each trade is delivered or only snapshots) were not verified in this session; if only throttled snapshots arrive, cumulative-volume deltas will merge many trades and degrade the quote-rule signing.
- How much of Indian opening OTM flow is institutional vs retail is unknown.

---

## 7. Futures basis / synthetic futures premium from put-call parity as a sentiment or flow signal

### Takeaway
Put-call-parity deviations (expensive calls vs expensive puts) predict **stock** returns in the US (grade B), with predictability fading over time. For the Nifty index, futures are documented to be frequently **underpriced** relative to cost of carry because of short-selling restrictions (2003–2012), and arbitrage-driven option imbalances against mispricing predict **reversal**, not continuation (Korea). The "futures premium = sentiment" idea used by Indian traders has no supporting evidence found (grade D). The synthetic forward is mainly a **computational input** (the correct underlying for IV and Greeks); as a directional signal it is grade C/D.

### Cited Findings
- **Cremers & Weinbaum (2010), JFQA:** stocks with relatively expensive calls (positive call-minus-put IV spread) outperform stocks with relatively expensive puts by **51 bp per week**; predictability is larger with high option liquidity / low stock liquidity, with more information risk, and **decreases over the sample period**. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=968237). Grade **B** (stocks).
- **Nandan, Agrawal & Bhargava (2014):** CNX Nifty futures were frequently **underpriced** relative to cost-of-carry fair value (Jan 2003–Dec 2012), possibly due to short-sale restrictions; mispricing differs between positive and negative basis and varies with days to expiry; mispricing signals were largely unexploited by arbitrageurs. — [SAGE](https://journals.sagepub.com/doi/10.1177/2319510X14553726). Grade **B/C** (India, descriptive).
- **Lee, Ryu, Yang & Yu (2026), JFM:** convergence-driven option order imbalances (trades against options–futures/spot mispricing, identified via matched-call/put synthetic positions) negatively predict related-market returns; when mispricing comes from option-side noise, the option price reverts while the futures price barely moves; the authors note this is "unlikely to translate into economically significant net profits". — [JFM fut.70142](https://onlinelibrary.wiley.com/doi/10.1002/fut.70142). Grade **B**.
- Indian empirical options research uses the futures price in Black-76 to avoid estimating dividends and carry. — [Agarwalla, Saurav & Varma (2021)](https://onlinelibrary.wiley.com/doi/10.1002/fut.22263).
- Practitioner claim: rising futures premium = bullish sentiment, falling/negative = bearish, while noting part of it is just carry. — [Tradeverse Journal](https://www.tradeversejournal.com/blog/futures-basis-and-cost-of-carry); [TradingView indicator](https://www.tradingview.com/script/DPXOsSRs-Nifty-vs-Nifty-Fut-Premium-indicator/). Grade **D**.

### Inferences
- **Use the synthetic forward from the weekly chain as F** in all IV/Greek calculations (Sections 1–4): the monthly future has a different expiry and its own mispricing.
- A short-horizon "option-side pressure" feature can be built as SynF − (carry-adjusted future): call buying pushes SynF up relative to futures. Given Lee et al., large deviations are more likely to **revert in the options** than to lead futures, so if used at all it should be a *contrarian-to-option-premium* filter (e.g., avoid buying calls when SynF is unusually rich vs futures, as the calls are bid up), grade C/D.

#### Computation recipe (every 1 min)
1. For the 3 strikes nearest ATM in the current weekly: SynF_K = C_mid(K) − P_mid(K) + K·e^(−rT); SynF = inverse-spread-weighted average.
2. Carry-adjusted spot premium: prem_spot = (SynF − S·e^((r − q)T))/S, with r = 91-day T-bill yield, q = Nifty dividend yield estimate.
3. Option-vs-futures gap: gap = SynF − Fut·e^(−(r − q)(T_fut − T_opt)); track its 5-min change and its z-score vs the same DTE/time-of-day.
4. Futures basis: basis = (Fut − S·e^((r − q)T_fut))/S as a slow (daily) sentiment/financing feature only.

### Gaps
- No Indian evidence on whether the Nifty synthetic premium or futures basis predicts intraday index direction.
- Post-2012 Nifty futures mispricing behaviour (after physical settlement of stock F&O, weekly options, and the 2026 STT hike on futures to 0.05%) was not found.

---

## 8. What is realistic for a retail system with 1-minute snapshots, what needs tick or trader-type data, and the ranked shortlist

### Takeaway
With Angel One's free websocket plus EOD bhavcopy and participant OI, a retail system can compute all **price-implied** signals (ATM IV, expected move, VRP gate, term structure, skew, synthetic forward) and **OI-based** gamma profiles at 1–5-minute frequency, and can reconstruct **daily** history for GEX, max pain and walls from bhavcopy for backtesting. What it cannot get is **trade-initiator flags and trader-type flow**, which are exactly what made the best order-flow results work (Kang et al., Pan & Poteshman, Chordia et al.); those can only be approximated and must be validated on live-collected data. Ranked on evidence × feasibility, the shortlist puts volatility/regime filters first and directional flow signals second.

### Cited Findings
- The strongest option-flow results rely on exchange data with trade direction and investor identity (KRX encrypted account IDs; CBOE open/close buyer-initiated volume; ISE order flow). — [Kang, Kang & Lee](https://onlinelibrary.wiley.com/doi/10.1002/fut.22301); [Pan & Poteshman](https://ideas.repec.org/a/oup/rfinst/v19y2006i3p871-908.html); [Chordia et al.](https://pubsonline.informs.org/doi/abs/10.1287/mnsc.2019.3529)
- Actual dealer positions require signed trade records (Cboe proprietary data in Amaya et al.); public GEX in India is assumption-based. — [Amaya et al.](https://cdn.cboe.com/resources/education/research_publications/gammasqueezes.pdf); [draconic.ai](https://draconic.ai/tools/nifty-gamma-exposure)
- Option trade-sign inference accuracy: 59% (tick rule) to 83% (quote rule). — [Savickas & Wilson record](https://www.econbiz.de/Record/on-inferring-the-direction-of-option-trades-savickas-robert/10005407236)
- Free data available: Angel One / Upstox / Dhan / Fyers websockets for live chain; NSE F&O bhavcopy (EOD strike-wise OI and prices); participant-wise OI (daily); India VIX history; historical expired-option intraday data only from paid vendors. — `03_indian_signals_data_regulation.md`
- Validation standards for any backtest (probability of backtest overfitting, deflated Sharpe ratio, decision-time leakage) are already adopted in `02_strategy_evidence_part1.md` (Bailey, Borwein, López de Prado & Zhu 2017; Bailey & López de Prado 2014).

### Inferences

#### Feasibility table

| Signal | Computable from 1-min snapshots? | Historical backtest possible with free data? | Needs tick / trader-type data? |
|---|---|---|---|
| ATM IV, straddle-implied move, VRP gate | Yes | Daily: yes (bhavcopy + 5-min futures RV); intraday: only by collecting live data | No |
| Term structure (current vs next weekly; vs India VIX) | Yes | Daily: yes (bhavcopy); intraday: collect live | No |
| Skew / RR25 / smile slope | Yes (needs clean bid/ask) | Daily: yes; intraday: collect live | No |
| GEX / NGE (3 sign conventions), gamma concentration, breakeven range | Yes (OI refresh frequency to verify) | **Daily NGE_{t−1}: yes** (bhavcopy) → Baltussen test on Nifty is feasible now | Trader-side data would fix the sign; not available |
| OI walls, max pain, ΔPCR-OI, ΔP×ΔOI states | Yes | Expiry-level walls/max pain: yes (bhavcopy); intraday ΔOI: collect live | No (but lacks aggressor side) |
| Opening OTM order-flow imbalance | Approximate only (quote rule on tick updates; BVC on 1-min bars is weak) | No (no historical option ticks) → forward-collect 3–6 months | **Yes** for full fidelity (initiator flag, investor type) |
| Synthetic forward / PCP gap / basis | Yes | Daily basis: yes; intraday: collect live | No |
| Participant-wise positioning (FII/Pro/Client) | EOD only | Yes, back to ~2016 | Intraday trader-type: not available |

#### Ranked shortlist of signals to implement

1. **Straddle-implied move + VRP gate (implied vs HAR-forecast realized vol)**
   - Formula: σ_impl = (S_ATM/F)·√(π/2)/√T_rem; VRP = σ_impl − σ_HAR,remaining; breakeven = S_ATM (0DTE) or structure-specific; trade only if E|move| > breakeven + costs; no overnight holding of long options.
   - Data: weekly ATM call/put bid/ask, synthetic F, 5-min Nifty futures history, minutes to expiry.
   - Update: every 1–5 min; HAR refit daily.
   - Role: **filter / volatility** (decides whether any buy is allowed, and naked vs debit spread).
   - Grade: **A/B** (Indian VRP is overnight; Garg & Vipul, Bhat et al.) for the no-overnight rule; **B** for IV-vs-RV conditioning (Goyal & Saretto; Simon).

2. **Dealer net gamma regime (prior-day NGE from bhavcopy + intraday gamma concentration + breakeven-range breach)**
   - Formula: G_K = Γ_K·F²·0.01·OI_K; NGE_IN = −Σ(G_call + G_put) (plus US and participant-weighted variants), normalized and z-scored by DTE; breakeven r* = sqrt(−Θ_book/(365·50·Γ$_book)) or ≈ 0DTE straddle %; regime = "trend allowed" if NGE strongly short-gamma *and* |F − open| > r*; "chop" if long-gamma or inside r*.
   - Data: strike-wise OI, bid/ask (for IV), F, T; EOD bhavcopy for history; participant OI for the sign variant.
   - Update: OI-based profile every 5 min (as OI refreshes); NGE_{t−1} once daily.
   - Role: **regime** (momentum vs mean reversion; conditions the late-day continuation trade and breakout entries).
   - Grade: **B** globally (Baltussen et al.; Dim et al.; Amaya et al.; NPPW); **India untested** (Motwani et al. C) → run the Nifty Baltussen test before live use.

3. **Opening 10-minute OTM option order-flow imbalance (quote-rule signed, large-trade weighted)**
   - Formula: OpOib_bull = [Σ_OTM calls q·|Δ| − Σ_OTM puts q·|Δ|]/Σ|q·Δ| over 9:15–9:25, q = quote-rule-signed ΔV; trade only if |z| > 2 vs 60-day history.
   - Data: tick/snapshot websocket for ATM ± 10 strikes (LTP, last qty, cumulative volume, best bid/ask), deltas.
   - Update: computed once at 9:25 (optionally re-check at 9:45); collect continuously from day 1.
   - Role: **direction** (rest-of-day bias).
   - Grade: **B** (Kang et al., Korea, after costs, OOS R² 1.85%); India approximation untested and attenuated by misclassification and missing investor IDs.

4. **Term-structure stress flag (current-week IV vs forward vol to next week; next-week IV vs India VIX)**
   - Formula: σ_fwd = sqrt((σ2²T2 − σ1²T1)/(T2 − T1)); TS = σ1 − σ_fwd, z-scored by (DTE, time-of-day), event-adjusted.
   - Data: ATM IVs for two weekly expiries, India VIX, event calendar.
   - Update: 5–15 min; daily history from bhavcopy.
   - Role: **regime / volatility** (inverted = larger moves expected, but options expensive → widen targets, prefer spreads).
   - Grade: **B** (Johnson; Vasquez; term-structure → RV papers), India weekly evidence absent.

5. **India VIX level and change**
   - Formula: VIX level percentile (1-year), ΔVIX intraday; implied daily move = VIX/√252.
   - Data: India VIX tick/1-min.
   - Update: 1–5 min.
   - Role: **volatility / sizing**, stop/target scaling.
   - Grade: **A/B** (NSE WP 9/2013; Agarwalla, Varma & Virmani; own data).

6. **Skew / 25-delta risk reversal change**
   - Formula: RR25 = IV(25Δc) − IV(25Δp); smile slope b from quadratic fit; 30-min Δ z-scored by DTE/time.
   - Data: OTM strike bid/ask for current and next weekly.
   - Update: 5 min.
   - Role: **filter** (structure choice: spread vs naked; risk-off flag when put skew steepens with rising ATM IV).
   - Grade: **C** for intraday use (no index intraday evidence; B for skew → option returns, China).

7. **Expiry-day OI walls / gamma concentration levels (not max pain as a forecast)**
   - Formula: call wall = argmax_{K>F} OI_call; put wall = argmax_{K<F} OI_put; ΔOI since open at walls; max pain only as a reference level.
   - Data: strike-wise OI, current weekly.
   - Update: 5–15 min on expiry day.
   - Role: **levels** for targets/stops; magnet vs acceleration read jointly with signal 2.
   - Grade: **B** for the pinning mechanism (US); **D** for Indian accuracy claims → backtest walls/max pain vs settlement on all weekly expiries from bhavcopy first.

8. **ΔP × ΔOI build-up states and intraday ΔPCR-OI**
   - Formula: Section 5 recipe (futures states with SD thresholds; option writing proxy using delta-adjusted premium change).
   - Data: futures and option OI, prices.
   - Update: 15 min.
   - Role: **confluence feature only**, to be dropped if it adds nothing in walk-forward tests.
   - Grade: **C/D** (popular, no evidence; OI-PCR Granger result B/C).

9. **Synthetic-forward premium / PCP gap / futures basis**
   - Formula: SynF from ATM PCP; gap = SynF − carry-adjusted future; basis = (Fut − S·e^((r−q)T))/S.
   - Data: ATM call/put mids, future, spot, T-bill yield.
   - Update: 1 min (as an input to IV); daily for basis.
   - Role: **input** (correct F for IV/Greeks); as a signal, weak contrarian filter on option richness.
   - Grade: **C/D** for direction (Cremers & Weinbaum B for stocks; Indian futures mispricing B/C; Lee et al. B suggests reversal).

#### Build order implied by the evidence
1. From day 1, **log the full live chain** (ATM ± 10 strikes, both weeklies, Nifty and Sensex, every 1 min plus tick-level for 9:15–9:30) because no historical intraday option data exist for us.
2. Immediately backtest with free EOD data: (a) Baltussen-style NGE regime test on Nifty with three sign conventions; (b) walls/max pain vs expiry settlement; (c) daily VRP and term-structure vs next-day realized range.
3. After 3–6 months of logged data, test the opening order-flow imbalance and intraday skew/term-structure changes walk-forward, with costs and the deflated-Sharpe standard.

### Gaps
- No verified information on Angel One websocket throughput, token limits, or whether OI updates intraday at fixed intervals; check the SmartAPI documentation before designing the logger.
- No Indian peer-reviewed study tests any of these option-implied signals for *intraday* Nifty/Sensex direction after costs; every ranking above for India is an extrapolation from US/Korea/China evidence plus Indian VRP findings.
- Whether Angel One's own option-Greeks/IV endpoint exists and how it computes IV was not checked; computing IV in-house from bid/ask is recommended regardless.
