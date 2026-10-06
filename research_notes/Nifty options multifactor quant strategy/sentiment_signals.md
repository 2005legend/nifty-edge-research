# Sentiment signals for intraday and next-day Nifty / Sensex timing: evidence and a cheap, leakage-free pipeline (as of Oct 2026)

Evidence grades: **A** = peer-reviewed + India + robust out-of-sample (OOS). **B** = peer-reviewed non-India, or India but not robustly OOS-tested. **B(WP)** = academic working paper or preprint (not yet peer-reviewed), otherwise B-level. **C** = practitioner or vendor. **D** = anecdote. **Own probe** = a measurement made in this session (6 Oct 2026, 08:40 IST).
I did not re-research facts already in `research_notes/02_strategy_evidence_part1.md` (Dasgupta et al. 2024; arXiv 2608.04200; verdict "news = risk filter, not engine") or `research_notes/03_indian_signals_data_regulation.md` (PCR, India VIX, FII positioning, GIFT Nifty, data sources). This file only cites them as context.

## 1. LLM news sentiment and return predictability: index level vs single stocks, and how fast it decays

### Takeaway
Most of the strong LLM-sentiment results (Sharpe 2–3+) are **cross-sectional, single-stock, long-short results**, concentrated in **small stocks and negative news**, and the initial reaction is non-tradable. At the **index level** the evidence is older, smaller and mostly **contrarian**: a one-standard-deviation (SD) move in media pessimism shifts next-day index returns by about 3–12 bps, and the move reverses within days. That is roughly a tenth of Nifty's average absolute daily move (0.70%), which is far too small to pay for an option buyer's spread and theta.

### Cited Findings
- **Lopez-Lira & Tang, "Can ChatGPT forecast stock price movements?"** (arXiv 2304.07619, v6 Oct 2025). On post-knowledge-cutoff headlines, GPT-4 scores capture the initial market response with about **90% portfolio-day hit rates for the non-tradable initial reaction**. They also significantly predict the *subsequent drift*, mainly for **small stocks and negative news**. Forecasting ability grows with model size, and **strategy returns decline as LLM adoption rises**, which the authors read as improving price efficiency. Grade B(WP), US single stocks. — [arXiv abstract](https://arxiv.org/abs/2304.07619)
- In an earlier version of the same paper, the ChatGPT-score coefficient for small stocks (below the 10th NYSE size percentile) is **more than 4× the size of the coefficient for the rest of the sample**. The authors say limits to arbitrage may limit how much of the effect can be captured. Grade B(WP). — [Lancaster FoFI 2024 version](http://wp.lancs.ac.uk/fofi2024/files/2024/04/FoFI-2024-139-Alejandro-Lopez-Lira.pdf)
- **Chen, Kelly & Xiu, "Expected returns and large language models"** (SSRN 4416687). LLM *embeddings* of news (ChatGPT, LLaMA) beat bag-of-words and Word2Vec, and add information beyond reversal and firm characteristics. Portfolios earn "economically meaningful" Sharpe ratios after costs, and the authors say the results are not driven by look-ahead bias. The study covers **16 international markets and 13 languages**. **Predictability lasts several days for small stocks but dissipates quickly for large stocks.** Grade B(WP), single stocks. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4416687)
- Kelly's slides on the same paper describe "fast and slow return prediction content in news text" and say "the best strategy is an ensemble of many LLMs". Grade C (presentation). — [Wharton Jacobs Levy slides](https://jacobslevycenter.wharton.upenn.edu/wp-content/uploads/2024/09/Kelly-WhartonJL.pdf)
- **Kirtac & Germano (2024), Finance Research Letters**. Sample: 965,375 US news articles, 2010–2023. OPT reaches **74.4% sentiment accuracy**, vs BERT 72.5% and FinBERT 72.2%. Long-short Sharpe after 10 bps costs: **OPT 3.05**, BERT 2.11, FinBERT 2.07, Loughran-McDonald dictionary 1.23. OPT returned 355% from Aug 2021 to Jul 2023. This is a cross-sectional stock strategy, and OPT's pre-training data overlaps the sample period. Grade B. — [arXiv 2412.19245](https://arxiv.org/abs/2412.19245), [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S1544612324002575)
- **"Buy the rumor, sell the news: when is news priced in?"** (arXiv 2608.14014, Aug 2026). Sample: 4.57M articles on about 3,000 US stocks, 2023–2026, with LLM-tagged event types (17 tags). By the close of publication day, the cumulative move in the direction of the news is **2.8× its value 20 days later**, so most of it gives back. **A large part of the move happens in the 5 days *before* publication.** Rumor-flagged events are priced fully on the rumor day. Quantified fundamental news (earnings, guidance, analyst actions) drifts for weeks. "Story" news (product launches, macro commentary, leadership changes) reverses within 20 days. Grade B(WP), single stocks. — [alphaXiv](https://www.alphaxiv.org/abs/2608.14014)
- **Agentic LLM nowcasting, live OOS** (arXiv 2601.11958). An LLM with web search ranked Russell 1000 stocks every night from Apr 2025 to Jan 2026. The top-20 long portfolio earned **daily alpha 0.184% (t = 2.46), Sharpe 2.43**. The short leg was not significant (t = −1.02): the model picks winners but cannot separate losers from average stocks. Grade B(WP). This is a genuinely leakage-free design, but it covers only 9 months and is cross-sectional. — [alphaXiv](https://www.alphaxiv.org/abs/2601.11958)
- **Index-level, classic text evidence: Tetlock (2007), JF.** A one-SD rise in WSJ "Abreast of the Market" pessimism lowers next-day Dow returns by **8.1 bps**. About **6.8 bps reverses over lags 2–5** (later in the week). Unusually high or low pessimism predicts high trading volume. Grade B. — [Tetlock JF PDF](https://business.columbia.edu/sites/default/files-efs/pubfiles/3097/Tetlock_Media_Sentiment_JF.pdf)
- **Garcia (2013), JF, "Sentiment during recessions".** A one-SD news-sentiment shock predicts a **12 bps** change in next-day DJIA return in recessions, against only **3.5 bps** in expansions. Most of the effect reverses. Grade B. — [Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12027), [author PDF](https://leeds-faculty.colorado.edu/garcia/media_v33.pdf)
- **Bond, Klok & Zhu, "Large language models and financial market sentiment"** (SSRN 4584928). ChatGPT applied to daily US market-news summaries gives an S&P 500 sentiment indicator that is **negatively correlated with short-term market returns** (contrarian). LLMs beat conventional classifiers, and ChatGPT has a "slight edge" OOS. Grade B(WP). The SSRN page returned 403, so this is summarised from search results. — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4584928)
- **Practitioner decay figures (RavenPack, as surfaced in search, pages not fetched).** Sentiment is "essentially fully incorporated" by days 3–4. Fresh news earns a 39 bps response (from 15 min after the timestamp to the next open) vs 23 bps for stale news. Positive events decay over about 2 days and negative ones over about 5 days. Grade C, single stocks, provenance only partly verified. — [RavenPack volatility note](https://www.ravenpack.com/research/news-sentiment-volatility), [RavenPack/CRSP summary PDF](https://agentic-sciences.github.io/assets/papers/ravenpack_sentiment_returns.pdf)
- **India context (already established, not re-researched):** Dasgupta et al. (2024) found that ET topic sentiment only marginally improves next-day Nifty *level* RMSE (about 134.9 → 128.7 points), and arXiv 2608.04200 found that labelling accuracy ≠ return predictability. — see `02_strategy_evidence_part1.md`
- Nifty's average |daily move| in 2015–2026 was **0.70%**, against an implied move of 1.04% (own data). — `04_nifty_measured_facts.md`

### Inferences
- **Why the single-stock results don't carry over to the index:** they come from cross-sectional dispersion (long the good-news names, short the bad), from small caps with slow attention, and from the negative-news leg. An index is an average of mega-caps, it is the most-watched asset in India, and macro news hits all constituents at once. Each of the conditions that produced the edge is weakest there.
- **Decay ranking:** the initial reaction happens in seconds to minutes and is not tradable on a 15-minute poll. Large-cap drift fades within about a day. Small-cap drift lasts several days. Index-level text sentiment shows **overreaction then reversal over 1–5 days**, not continuation. A 15-minute alert system will mostly see news *after* Nifty has priced it.
- **Effect size vs cost:** 3–12 bps per SD of sentiment is about 5–17% of the 0.70% average absolute daily move. A weekly ATM option on ₹5,000 capital loses more than that to bid-ask spread and one hour of theta. **Polarity-based direction tilt is not worth building as an entry signal.**
- If text tone is used for direction at all, the evidence (Tetlock, Garcia, Bond et al., FEARS in §6) points to a **contrarian, next-day, recession or stress-regime** use. It does not point to intraday momentum.
- "Market" headlines (e.g., "Sensex tanks 800 pts") largely *restate the lagged index return*. A sentiment score built on them is mostly a lagged price-momentum feature. This may partly explain why "market news mattered most" in Dasgupta et al. Such headlines should be filtered out before any sentiment is computed (see §2).

### Gaps
- I found **no peer-reviewed study of LLM (GPT-class) news sentiment predicting Nifty or Sensex index returns intraday with a robust OOS trading test**. India-level grade-A evidence for text-sentiment direction does not exist as of Oct 2026, as far as I could find.
- Whether Chen-Kelly-Xiu's 16 markets include India, and their country-level Sharpe ratios, could not be checked (only slides were readable).
- Exact Sharpe and t-stat figures for Lopez-Lira & Tang v6, and any aggregate-market results in it, were not in the readable abstract.

## 2. Look-ahead and leakage risks specific to LLM sentiment backtests, and how to evaluate honestly

### Takeaway
LLM backtests have two separate biases. **Look-ahead** means the model memorised what happened after a headline. **Distraction** means the model's prior knowledge of the entity overrides the headline text. On top of these sit the ordinary data problems: timestamp misalignment, revised or stale feed timestamps, and random train/test splits. Published corrections show in-sample LLM backtest returns can shrink by **up to about 67%** once memory is suppressed. The only fully clean evidence is **live, post-cutoff, point-in-time logged** data.

### Cited Findings
- **Glasserman & Lin (2023)** compared GPT sentiment strategies on original headlines against **anonymised headlines with the company identifiers removed**. In-sample, the anonymised headlines *outperform*, meaning the **distraction effect is larger than look-ahead bias**, especially for large firms. OOS, look-ahead is not a concern but distraction still is. They recommend anonymisation both for debiased backtests and for live use. Grade B(WP). — [arXiv 2309.17322](https://www.alphaxiv.org/abs/2309.17322), [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4586726)
- **He et al., ChronoBERT / ChronoGPT** ("Chronologically consistent large language models"): models pretrained only on timestamped text up to each date. They report that look-ahead impact is **model- and application-specific** and **modest for return prediction**, and that downstream models still deliver significant gains. Grade B(WP). — [arXiv 2502.21206](https://arxiv.org/pdf/2502.21206)
- **Look-Ahead-Bench (Jan 2026)** measures look-ahead as **alpha decay across time regimes**. Standard LLMs (Llama 3.1, DeepSeek 3.2) show "significant lookahead bias". Point-in-time models (the "Pitinf" family) show much less, and generalise better as they scale. Grade B(WP). — [arXiv 2601.13770](https://www.alphaxiv.org/abs/2601.13770)
- **FINCAD (May 2026)**, an inference-time fix that penalises "memory-only" outputs with entity- and date-adaptive penalties. In-sample (2010–2020) it **cut model mean returns by up to 67.1% and Sharpe by up to 25.6%**. On a 2025 OOS period, it left Sharpe within ±0.10 of baseline. It raised the rank correlation between backtested and real post-cutoff performance from **0.779 to 0.846**. Grade B(WP). — [arXiv 2605.24564](https://www.alphaxiv.org/abs/2605.24564)
- **Other 2025–2026 point-in-time work:** DatedGPT (time-aware pretraining) — [arXiv 2603.11838](https://www.alphaxiv.org/abs/2603.11838); "Scaling point-in-time language models" (Kelly et al., NBER w35247) — [NBER PDF](https://www.nber.org/system/files/working_papers/w35247/w35247.pdf), [arXiv 2607.11889](https://arxiv.org/html/2607.11889v2); "ChatGPT as a time capsule", which shows frozen checkpoints extract pre-cutoff information linked to *future* fundamentals and returns, so a model's "knowledge" can itself act as a signal and as a contaminant — [arXiv 2604.21433](https://www.alphaxiv.org/abs/2604.21433). Sarkar & Vafa, "Lookahead bias in pretrained language models" (SSRN 4754678), is the early statement of the problem — [Semantic Scholar](https://www.semanticscholar.org/paper/Lookahead-Bias-in-Pretrained-Language-Models-Sarkar-Vafa/e5097ccd4477c454e0df52945cef4ba74d255b91). All B(WP).
- **A worked example of split leakage:** "Beyond sentiment: structured information extraction from financial news" (arXiv 2607.28496) reports next-day direction F1 of 0.600 using **random (not time-ordered) splits with possible train-test overlap**, and its own limitations section flags this. Results like this should be discounted. Grade B(WP). — [alphaXiv](https://www.alphaxiv.org/abs/2607.28496)
- **Own probe of feed-timestamp hygiene (6 Oct 2026, 08:40 IST):** Moneycontrol's `marketreports.xml` and `latestnews.xml` RSS feeds still return HTTP 200, but their newest items are dated **23 Apr 2024**. They look abandoned, so a scraper built on them would silently ingest nothing new. ET and Business Standard feeds were current (newest items 18 min and 4 min old). — [Moneycontrol market reports RSS](https://www.moneycontrol.com/rss/marketreports.xml), [ET markets RSS](https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms), [BS markets RSS](https://www.business-standard.com/rss/markets-106.rss)
- Decision-time leakage and search bias remove many published edges (arXiv 2608.27734, 2605.23959; see `02_strategy_evidence_part1.md`).

### Inferences
**Leakage checklist for this project:**
1. **Timestamp = first-seen time by your own poller (UTC, stored), never the feed's `pubDate`.** Publishers edit headlines and bodies and can re-date items. Backfills from GDELT should use GDELT's 15-minute file time as the earliest knowable time.
2. **Store raw snapshots.** Keep the headline text exactly as first seen, with a hash and the source. Later edits create new rows; they never overwrite.
3. **Drop price-report headlines** (regex such as `Sensex|Nifty .* (falls|jumps|tanks|surges|ends) .* pts`, "market wrap", "closing bell") before scoring. They encode the lagged return.
4. **LLM backtests are run only on post-cutoff data**, or on anonymised and date-masked text (Glasserman-Lin), or with a point-in-time model (ChronoGPT or DatedGPT) for history. Log the model ID and prompt version, and use temperature 0.
5. **Walk-forward evaluation only.** Use purged, embargoed splits (embargo of at least the label horizon). Never use random splits.
6. **Live shadow mode is the real test:** log signals for 2–3 months before giving them any weight in alerts.
7. **Anonymise heavyweights** (Reliance, HDFC Bank, etc.) when scoring index-relevant corporate news, to cut the distraction effect.

### Gaps
- None of the look-ahead papers test Indian-language or Indian-outlet news, or index targets.
- How often ET, BS, Mint and NDTV Profit edit a headline after first publication (and whether `pubDate` changes) was not measured. It needs a 2–4 week logging study.

## 3. Event and shock detection rather than polarity: news volume and uncertainty measures for volatility

### Takeaway
Text works better for **volatility and risk** than for direction. Newspaper-based uncertainty measures (NVIX, EMV, EPU, GPR) track or lead volatility and risk premia, and policy news explains a large share of big index moves. Most of these indices are **monthly** and largely **coincident** with VIX. For a system that already watches India VIX live, the value of text is in **classifying *what kind* of shock is happening, and spotting unscheduled ones early**, not in a generic uncertainty level.

### Cited Findings
- **NVIX (Manela & Moreira 2017, JFE)** is built from WSJ front-page text back to 1890. High NVIX predicts **above-average future stock returns** (it is a risk-premium signal). A **one-SD rise in NVIX implies a 2.5 pp higher probability of an economic disaster over the next year**. **War and government-policy** news explains most of the time variation. These are monthly-to-annual horizons. Grade B. — [published PDF](https://amoreira2.github.io/alan-moreira.github.io/NVIX_published.pdf), [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0304405X16301751)
- **EMV tracker (Baker, Bloom, Davis & Kost, NBER w25720, rev. May 2025)** is daily and monthly, built from 11 US newspapers. It **co-moves with VIX and S&P realised volatility (correlation about 0.8 monthly, 0.85 quarterly)**, and keeps strong tracking power in a clean OOS period (2019–2023; the term set was frozen in 2018). Topic shares of EMV articles: 72% macro news and outlook, **35% fiscal policy, 30% monetary policy, 25% regulation, 13% national security**. Grade B(WP). — [NBER w25720](https://www.nber.org/system/files/working_papers/w25720/w25720.pdf)
- From the same paper's review: Baker et al. (2024) read next-day newspaper accounts of thousands of daily moves larger than |2.5%| worldwide. **37% of large US daily moves are attributed to government-policy news.** Grade B(WP). — [NBER w25720](https://www.nber.org/system/files/working_papers/w25720/w25720.pdf)
- **EPU (Baker, Bloom & Davis 2016)** is the share of newspaper articles with economy + policy + uncertainty terms. An **India EPU exists from 2003**, built from Indian dailies (Economic Times, Times of India, Hindustan Times, The Hindu, Financial Express, Indian Express, among others, per search summary). It is **monthly**. Grade B. — [EPU paper](https://www.policyuncertainty.com/media/EPU_BBD_Mar2016.pdf)
- Higher EPU is associated with higher stock-market volatility in E7 emerging markets (GARCH-MIDAS, with OOS R² reported). Grade B. — [Journal of Forecasting, doi 10.1002/for.70009](https://doi.org/10.1002/for.70009)
- **GPR (Caldara & Iacoviello 2022, AER)** counts newspaper text on war, terrorism and tensions. **India is one of the countries with a country-specific (monthly) GPR.** Grade B. — [AER](https://www.aeaweb.org/articles?id=10.1257%2Faer.20191823), [GPR paper](https://www.matteoiacoviello.com/gpr_files/GPR_PAPER.pdf). There is also an LLM-based AI-GPR — [AI-GPR paper](https://www.matteoiacoviello.com/research_files/AI_GPR_PAPER.pdf)
- **SenGupta & Debnath (2026), International Economics and Economic Policy 23(4)**, study 28 NSE broad and sectoral indices. **Global GPR shocks cause significant negative responses in most broad-market and resource indices.** Microcap 250, Auto, Tourism, Capital Markets and Defence show positive long-run responses. Threat shocks and act shocks behave differently. Shocks from China, Saudi Arabia, Russia, the US and Europe transmit more strongly. Grade B (India, peer-reviewed; frequency and OOS not verified). — [RePEc](https://ideas.repec.org/a/kap/iecepo/v23y2026i4d10.1007_s10368-026-00785-w.html), [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5224456)
- **RBI policy surprises:** an RBI working paper finds that both the *target* and *path* surprise factors of monetary policy affect equity-price volatility. Grade B(WP), India. — [RBI WP via ResearchGate](https://www.researchgate.net/publication/380127245_Equity_Markets_and_Monetary_Policy_Surprises_RBI_Working_Paper). A low-tier source claims intraday Nifty volatility spikes "within minutes" of an off-consensus RBI release. Grade D. — [IJNTI 2026](https://www.rjpn.org/ijnti/papers/IJNTI2605086.pdf)
- **Volume, not tone:** Tetlock (2007) finds that *extreme* pessimism in either direction predicts **high market volume** (Grade B — [PDF](https://business.columbia.edu/sites/default/files-efs/pubfiles/3097/Tetlock_Media_Sentiment_JF.pdf)). FEARS predicts **temporary increases in volatility** (Grade B, §6).
- **Structured extraction beats a single polarity score.** Six fields (polarity, intensity, event type, impact subject company/industry/macro, horizon, confidence) were **53.5% in disagreement with FinBERT polarity**, and adding them improved F1 (0.576 → 0.600). The split was random, so this is leak-prone. Grade B(WP). — [arXiv 2607.28496](https://www.alphaxiv.org/abs/2607.28496)

### Inferences
- **Event taxonomy for an Indian index shock classifier (LLM output schema):**
  - `category` ∈ {RBI/monetary, fiscal/tax/Budget, SEBI/market-structure (F&O rules, STT, margin), geopolitical/security, global macro (Fed, US CPI, tariffs), commodity/crude, FX/INR, index-heavyweight corporate (top-10 Nifty/Sensex weights), election/political, exchange-outage/technical, other}
  - `scope` ∈ {India-macro, global, sector, single-stock}
  - `surprise` ∈ {scheduled-as-expected, scheduled-surprise, unscheduled}
  - `severity` 0–3
  - `direction_hint` ∈ {−, 0, +} (logged for research, not traded)
  - `is_price_report` (bool; drop if true)
- **Shock score every 15 min** = z-score of the count of *deduplicated*, non-price-report, severity ≥ 2, India-macro or global headlines in the last 60 min. Compare it with the same weekday and time-of-day baseline over 60 sessions. Combine it with the India VIX intraday change, which is already in the system. Text gives the *why* and the *scheduled vs unscheduled* tag. VIX gives the *how much*.
- **Use for an options buyer:**
  - (a) **Stand aside on fresh entries for 15–30 min after an unscheduled severity-3 shock.** The first move is non-tradable, and IV reprices at once.
  - (b) **Avoid buying premium just before scheduled high-impact events** where IV is bid and tends to crush after.
  - (c) After a scheduled event resolves *without* surprise, normal signals can resume.
- Monthly EPU and GPR are **regime context only** (e.g., an elevated GPR month → smaller size). 2026 is already a "war-driven high-volatility year" in the project's own data (`04_nifty_measured_facts.md`).

### Gaps
- No study found that tests an **intraday, India-specific news-volume or shock index** against Nifty realised volatility OOS. This would be the project's own research contribution, and it is testable on 1-min data with GDELT backfill.
- Whether Caldara-Iacoviello publish a *daily* India GPR, and whether India EPU has a daily version, was not verified this session. Both are believed to be monthly only.
- The RBI working paper's effect sizes and its intraday versus daily windows could not be read.

## 4. Social media sentiment (X, StockTwits, Reddit, Telegram, YouTube finfluencers): signal vs noise, manipulation, SEBI rules

### Takeaway
The best index-level social-media result (StockTwits, US) is an intraday half-hour effect that overlaps with plain intraday momentum. **Indian social-sentiment studies are tiny-sample correlation exercises.** Since Aug 2024 to Jan 2025, SEBI has legally separated "education" (price data at least 3 months old) from "advice", and has penalised large finfluencer operations. Indian finfluencer and Telegram content is therefore both **low-signal and adversarial**. Do not build it. At most, treat extreme retail euphoria as a contrarian flag.

### Cited Findings
- **Renault (2017), JBF 84:25–40.** A StockTwits lexicon aggregated in half-hour windows: the **change in sentiment over the first half-hour predicts the last half-hour return of the S&P 500 ETF**. Grade B. — [EconPapers](https://econpapers.repec.org/RePEc:eee:jbfina:v:84:y:2017:i:c:p:25-40), [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0378426617301589)
- **India, X/Twitter:** Saini & Bodla (2024) analysed 22,816 financial tweets against Nifty 50 for **one month (Jan 2023)** and found a **low positive correlation** between positive sentiment or polarity and *hourly* returns. Grade B (India, no OOS, very short sample). — [Sage](https://journals.sagepub.com/doi/abs/10.1177/23210222241289700)
- **India, event study:** 27,175 tweets with 14 hashtags over a 15-day window around the Dec 2020 COVID-vaccine news. Positive sentiment influenced Nifty 50 more than negative. Grade B (single event). — [Inderscience IJIE 2023](https://www.inderscience.com/info/inarticle.php?artid=133830)
- Older Indian work claims "70% accuracy" for Twitter sentiment on Nifty-50 stock prices (15% better when commodity prices are added). Grade D-level methodology (conference paper, no trading test). — [ACM 2016](https://dl.acm.org/doi/10.1145/2979779.2979856); see also [Procedia 2015](https://www.sciencedirect.com/science/article/pii/S187705091503207X)
- **SEBI finfluencer framework:**
  - SEBI (Intermediaries) (Amendment) Regulations, 2024, effective **29 Aug 2024**, bar regulated entities from associating with unregistered persons who give advice or make performance claims.
  - In **Oct 2024**, regulated entities were told to end such contracts. A carve-out exists for SEBI-approved "Specified Digital Platforms".
  - The **Jan 2025 circular** says educators may use **only price data lagged at least 3 months**, and may not use recent prices to imply future price, advice or recommendations.
  - Grade C (legal and press summaries). — [TaxGuru](https://taxguru.in/sebi/sebi-finfluencer-regulations-protecting-investors-digital-age.html), [MediaNama Feb 2025](https://www.medianama.com/2025/02/223-sebi-regulated-entities-restriction-finfluencers/), [Business Standard Jan 2025](https://www.business-standard.com/markets/news/sebi-finfluencer-circular-live-stock-data-market-education-rules-125013000571_1.html), [AIR News Jan 2025](https://www.newsonair.gov.in/sebi-cracks-down-on-finfluencers-selling-stock-tips-in-the-name-of-education)
- **Enforcement:** SEBI's **4 Dec 2025 order against Avadhut Sathe / ASTA impounded ₹546 crore** and imposed a market ban. Grade C (secondary source). — [Dealplexus](https://www.dealplexus.com/blog/sebi-finfluencer-rules)
- "Talking to digital twins" (arXiv 2608.01181) notes that finfluencer posts are *voluntary, selective disclosures*, so what is not posted is unobserved. This is a measurement problem for any social-media sentiment. Grade B(WP). — [alphaXiv](https://www.alphaxiv.org/abs/2608.01181)

### Inferences
- Renault's first-half-hour effect is very likely the social-media reflection of **intraday momentum (Gao et al. 2018)**, which the system can measure directly from price (`02_strategy_evidence_part1.md`). Social data adds cost, delay and manipulation risk for little extra information.
- After SEBI's rules, *legal* public content cannot carry live calls. Live "calls" on YouTube or Telegram during market hours are therefore either non-compliant tip channels (pump-and-dump risk) or noise. A model trained on them learns the behaviour of adversarial accounts.
- **Contrarian use (optional, low priority):** a daily count of "Nifty to the moon" or "crash" style posts, or retail-euphoria proxies, as an *extreme-only* contrarian flag. This is consistent with the reversal evidence (Tetlock, FEARS), but it is untested in India.
- X API access costs make X data out of budget for a ₹5,000 account, and Reddit's r/IndianStreetBets is too small and too meme-driven to matter at index level. This is an inference; no source was checked this session.

### Gaps
- No peer-reviewed India study of Reddit, Telegram or YouTube sentiment vs Nifty with OOS testing was found.
- Current X and Reddit API pricing was not verified this session.
- SEBI's own enforcement statistics on Telegram pump-and-dumps were not retrieved.

## 5. Market-based sentiment for India: Baker–Wurgler-style composites, Market Mood Index, intraday breadth

### Takeaway
Market-based sentiment is **free, leakage-free and real-time**. The Indian academic evidence is that composite sentiment (PCR, advance/decline, turnover, IPOs) **affects volatility**, and that MMI and Nifty Granger-cause each other in-sample. **None of this is robust OOS** (no grade-A results). **Intraday breadth** of the 50 or 30 index constituents has *no* academic intraday evidence in India, but it is the cheapest confirmation filter to backtest on your own 1-min data, and it should be tested first.

### Cited Findings
- **Kumari & Mahakud (2015), J. Behavioral & Experimental Finance 8:25–39.** An Indian sentiment index built from **put-call ratio, advance-decline ratio, turnover ratio, dividend premium, number of IPOs and turnover velocity**. In a non-linear GARCH, sentiment significantly affects Indian stock-market *volatility* in both the mean and variance equations, with clustering, asymmetry and leverage effects. Grade B (India, no OOS trading test). — [RePEc](https://ideas.repec.org/a/eee/beexfi/v8y2015icp25-39.html)
- **Tickertape Market Mood Index (MMI) methodology.** Six equal-weight components: **FII net index-futures OI, volatility (India VIX) and skew (OTM put IV minus OTM call IV of Nifty), momentum, market breadth, price strength, and gold demand**. Each is z-scored against a **45-trading-day rolling mean and SD**, then mapped to 0–100. Grade C. — [Tickertape help: how MMI is built](https://help.tickertape.in/support/solutions/articles/82000143107-how-is-mmi-built-), [MMI volatility & skew](https://www.tickertape.in/market-mood-index/volatility-and-skew)
- **Seth & Kumar (2023), Theoretical and Applied Economics XXX(1):263–272.** With MMI vs Nifty (2,449 daily observations, lag 11, ARDL plus pairwise Granger tests):
  - MMI Granger-causes Nifty (**F = 3.03, p = 0.0005**).
  - **Nifty Granger-causes MMI far more strongly (F = 10.93, p = 6e-20)**.
  - The two are negatively correlated. The authors frame "extreme fear (<30)" as a buy zone.
  - In-sample only. The Granger test is run on the Nifty *index* series, which the paper itself says is I(1).
  - Grade B (weak). — [paper PDF](https://store.ectap.ro/articole/1655.pdf)
- **Breadth in other markets:** cross-country studies find that markets and industries with more rising than falling stocks keep outperforming (breadth acts like momentum at country and industry level). Monthly horizon. Grade B. — [Economic Modelling, "Herding for profits: market breadth and the cross-section of global equity returns"](https://www.sciencedirect.com/science/article/pii/S0264999319312982)
- **Intraday NYSE breadth, practitioner study:** days with 5 or more intraday advance-decline prints above +2,000 ("surge days") were followed by **+1.9% average SPY returns over 21 sessions with a 73% win rate**. Washout-print days returned +1.7% vs a +1.1% baseline over the next month. These are multi-week horizons, not intraday. Grade C. — [thetrading.tools](https://www.thetrading.tools/nyse-advance-decline)
- **Baker & Wurgler (2006), JF.** The composite-sentiment template: high sentiment is followed by low returns on speculative, hard-to-value stocks. Monthly, cross-sectional. Grade B. — [doi 10.1111/j.1540-6261.2006.00885.x](https://doi.org/10.1111/j.1540-6261.2006.00885.x)
- An Indian study of sentiment vs Nifty 500 and sectoral indices exists (Cogent Economics & Finance, 2024), but it returned 403 and its results were not read. — [T&F](https://www.tandfonline.com/doi/full/10.1080/23322039.2024.2303896)
- **Already established (not re-researched):** volume PCR has no predictive power; OI-PCR shows weak contrarian Granger-causality; India VIX predicts realised volatility; FII index-futures long ratio is a slow regime feature; FII cash flows *follow* returns. — `03_indian_signals_data_regulation.md`

### Inferences
- **MMI is mostly a re-expression of recent price.** Momentum, price strength, breadth and VIX are all price-derived, and Nifty → MMI causality is about 3.6× stronger by F-statistic. It is a convenient *dashboard* number, but as a feature it largely duplicates information you already compute. If used, use only its *extremes* (below 20 or above 80) as a slow contrarian context flag.
- **Build your own intraday breadth (free, leakage-free):** from the broker websocket, every 15 min compute:
  1. **Weighted breadth** Bw = Σ wᵢ·sign(rᵢ since open) over Nifty 50 (and separately over Sensex 30).
  2. **% of constituents above their session VWAP**.
  3. **Breadth thrust** = change in (2) over the last 30 min.
  4. **Divergence flag**: index up while Bw < 0, i.e., a rally driven by 2–3 heavyweights.

  Role: **confirmation**. Only send a long-call (CE) alert if Bw > 0 and %>VWAP ≥ 60%, and mirror this for puts. A divergence suggests a heavyweight-driven move that may fade, which matters especially on expiry days given the Jane Street episode (`03_indian_signals_data_regulation.md`).
- A daily composite (Baker–Wurgler style, India) belongs to **slow regime and sizing** (days to weeks), not the 15-minute engine. Suggested inputs: India VIX percentile, OI-PCR z-score, FII long ratio, Nifty 500 EOD advance/decline, F&O turnover z-score, and IPO subscription/listing-gain heat (monthly).

### Gaps
- **There is no published evidence (academic or credible practitioner) on intraday Nifty 50 breadth or %-above-VWAP as a predictor of the next 15–60 min of Nifty returns.** It must be tested on 1-min constituent data (broker historical API; about 50 symbols × years).
- Angel One SmartAPI websocket subscription limits (tokens per connection) were not verified. The system needs about 80 constituents, the indices and a strike ladder of options.
- No OOS test of Tickertape MMI as a timing signal was found.

## 6. Google Trends and search attention at index level in India

### Takeaway
Search attention is a **slow, contrarian or attention-driven signal**. In the US it works at the stock level over 1–2 weeks (Da, Engelberg & Gao 2011), and at market level via FEARS: search-based fear brings low returns today, **reversal over the next 2 days**, and temporarily higher volatility. Indian studies are **stock-level and weekly** (2012–2017). There is **no index-level intraday India evidence**, and Google Trends' sampling and rescaling make it unsuitable for a 15-minute engine.

### Cited Findings
- **Da, Engelberg & Gao (2011), JF, "In search of attention".** Google search volume is a direct attention measure. Increases predict higher stock prices over the **next 2 weeks**, with eventual reversal. Grade B. — [doi 10.1111/j.1540-6261.2011.01679.x](https://doi.org/10.1111/j.1540-6261.2011.01679.x)
- **Da, Engelberg & Gao (2015), RFS, "The sum of all FEARS".** Aggregate household-concern searches ("recession", "unemployment", "bankruptcy"), 2004–2011:
  - High FEARS coincides with **low returns today but predicts high returns over the following 2 days** (reversal).
  - It predicts **temporary increases in volatility**.
  - It predicts mutual-fund flows out of equity and into bonds.
  - Grade B. — [author PDF](https://academicweb.nd.edu/~zda/FEARS.pdf), [RePEc](https://ideas.repec.org/a/oup/rfinst/v28y2015i1p1-32..html)
- **India:** Dharani, Hassan, Abedin & Ismail (2022), Borsa Istanbul Review 22(2):226–239. Using a weekly search attention index (SAI), 2012–2017, high-search-intensity portfolios earn significantly higher abnormal returns, but attention is irrelevant for extremely high-risk stocks. SAI explains market, size, value and momentum factor variation. Grade B (India, in-sample asset pricing). — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2214845021000338)
- **India:** Nifty 50 companies, Jul 2012 to Jun 2017. Higher Google search volume predicts **positive, significant returns over the next 2 weeks**, and domestic searches matter more than worldwide searches. Grade B. — [Review of Behavioral Finance (Emerald)](https://www.emerald.com/insight/content/doi/10.1108/RBF-04-2018-0033/full/pdf), [ResearchGate](https://www.researchgate.net/publication/333421154_Investor_attention_using_the_Google_search_volume_index_-_impact_on_stock_returns)
- **India:** a quantile-regression study finds search attention relates to returns and volatility. Grade B. — [ResearchGate](https://www.researchgate.net/publication/332594436_Investor_Attention_and_Google_Search_Volume_Index_Evidence_from_an_Emerging_Market_using_Quantile_Regression_Analysis)

### Inferences
- **Possible daily or weekly use:** a Hindi + English FEARS-style index for India ("market crash", "Sensex crash", "recession", "job loss", "SIP stop", "शेयर बाजार गिरावट") as a slow **contrarian / volatility-regime** input. It does not belong in the 15-minute engine.
- Google Trends returns sampled, 0–100 rescaled series with coarse granularity over long windows. It is hard to make strictly point-in-time and reproducible, which is a leakage risk if historical pulls are re-sampled. This is a general property of the tool and was not verified in a source this session.
- Ranked below all market-based signals.

### Gaps
- No study of Google search attention and **Nifty index** returns or volatility at daily or intraday frequency with OOS testing was found.
- The current Google Trends API (alpha) access and limits were not verified.

## 7. Free or cheap Indian news sources with reliable timestamps, their latency, and LLM classification cost

### Takeaway
A workable free stack exists today:
- **ET markets and economy RSS, Business Standard markets RSS, Mint markets RSS, NDTV Profit feed** (news)
- **NSE corporate-announcement RSS** (about 2-minute-fresh filings) and **BSE notices**
- **RBI press-release RSS** and **PIB RSS** (official policy)
- **GDELT 2.0** (15-minute global files; backfill and cross-check)

**Moneycontrol's RSS appears dead (last item Apr 2024).** Classifying 500–2,000 headlines a day costs about **US$0.03–0.05/day on the cheapest tier (Gemini 2.5 Flash-Lite or GPT-5 nano)**, or about **$0.5/day on Claude Haiku 4.5**. Cost is not the constraint; signal quality is.

### Cited Findings
**Own probe, 6 Oct 2026, 03:10–03:11 UTC (08:40 IST, before the open):**
- **ET markets RSS:** HTTP 200, 50 items, newest `pubDate` 08:22:42 IST (about 18 min old). — [feed](https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms). **ET economy RSS:** 200, current (newest 05:30 IST). — [feed](https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms)
- **Business Standard markets RSS:** 200, 35 items, newest 08:36:42 IST (about 4 min old). — [feed](https://www.business-standard.com/rss/markets-106.rss)
- **Livemint markets RSS:** 200, 35 items (dates in CDATA). — [feed](https://www.livemint.com/rss/markets). **NDTV Profit (Feedburner):** 200. — [feed](https://feeds.feedburner.com/ndtvprofit-latest)
- **NSE "Online announcements" RSS:** 200, 180 items, newest 08:38:46 IST (about 2 min old). NSE publishes RSS for announcements, board meetings, results, corporate actions, insider trading and more. — [feed](https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml), [NSE RSS index](https://www.nseindia.com/static/rss-feed)
- **BSE notices RSS:** 200, newest Mon 5 Oct 16:32 GMT. — [feed](https://www.bseindia.com/data/xml/notices.xml), [BSE RSS page](https://beta.bseindia.com/rss-feed.html)
- **RBI press-release RSS:** 200, newest Mon 5 Oct 19:15. — [feed](https://www.rbi.org.in/pressreleases_rss.xml). **PIB RSS:** works after a 301 redirect; the `Lang=1` URL returned Hindi titles. — [feed](https://pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3)
- **GDELT 2.0** `lastupdate.txt` lists 15-minute export, mentions and GKG files (e.g., `20261006031500.*`). GKG about 3 MB zipped per 15 min, globally. — [GDELT lastupdate](https://data.gdeltproject.org/gdeltv2/lastupdate.txt)
- **Moneycontrol** `marketreports.xml` / `latestnews.xml`: HTTP 200, but newest items are dated **23 Apr 2024** (stale). — [feed](https://www.moneycontrol.com/rss/marketreports.xml)

**Other sources:**
- Zerodha **Pulse** aggregates Indian market news from all the major sources and is useful as a manual cross-check. — [Pulse](https://pulse.zerodha.com/)
- Third-party RSS generators (e.g., rss.app) refresh free feeds hourly (15 minutes on premium), so they are **too slow**. Use publishers' native feeds. — [rss.app ET feed](https://rss.app/rss-feed/the-economic-times-rss-feed)

**LLM API prices (per 1M tokens, as reported Sep 2026 by an aggregator):**

| Model | Input | Output |
|---|---|---|
| Gemini 2.5 Flash-Lite | $0.10 | $0.40 |
| GPT-5 nano | $0.05 | $0.40 |
| Claude Haiku 4.5 | $1.00 | $5.00 |

Grade C (verify on provider pages before committing). — [CloudZero comparison](https://www.cloudzero.com/blog/llm-api-pricing-comparison/), [benchr](https://benchr.org/articles/ai-model-pricing-comparison)

**Datasets for research or backfill:** NIFTY Financial News Headlines dataset (arXiv 2405.09747) and the LLM+RAG+RL NIFTY sentiment architecture (arXiv 2512.20082). — see `02_strategy_evidence_part1.md`

### Inferences
- **Latency budget:** poll the native RSS feeds every 60–120 s (a light GET with conditional ETag headers), NSE and RBI every 60 s, and GDELT every 15 min. From the probe, end-to-end delay from event to alert is about **2–20 min**. That is slower than the price reaction (seconds to minutes; §1). This is another reason text should *gate* or *explain* moves rather than *predict* them.
- **Volume control:** cap the NSE announcements feed to the top-15 Nifty and Sensex weights plus all exchange/SEBI circulars. Most of its 180+ items per morning are small-cap filings that are irrelevant to the index. Dedupe the same story across outlets with a normalised-title hash or MinHash before the LLM, which should cut LLM calls by about 30–50% (an estimate).
- **Cost arithmetic (assumptions):** 2,000 headlines/day; about 120 input tokens per headline (batched about 20 per call with a shared, cached instruction); about 30 output tokens (compact JSON); so about 0.24M input + 0.06M output tokens per day.
  - **GPT-5 nano:** 0.24×0.05 + 0.06×0.40 ≈ **$0.036/day**
  - **Gemini 2.5 Flash-Lite:** ≈ **$0.048/day**
  - **Claude Haiku 4.5:** 0.24×1 + 0.06×5 ≈ **$0.54/day** (about $16/month, about ₹1,400 at ≈₹88/$, an assumption)

  For a ₹5,000 account, use the **cheapest tier for bulk tagging**, and optionally escalate only severity ≥ 2 items (perhaps 20–50 a day) to a stronger model. That tiered setup costs **under about ₹300/month**.
- **Determinism and audit:** temperature 0, JSON schema output, stored prompt hash and model ID. Re-scoring history with a newer model creates a new column; never overwrite.

### Gaps
- Typical intraday item counts per feed (as opposed to a pre-open snapshot), and how much `pubDate` lags behind the article first appearing on the site, were not measured. This needs a 1–2 week logging run.
- NDTV Profit and Mint `pubDate` precision (CDATA) was not parsed in the probe.
- ToS and rate limits for automated polling of each publisher's RSS were not reviewed.
- Free-tier quotas of the LLM APIs were not verified.

## 8. Recommended role of sentiment in the system, evaluation protocol, and ranked shortlist

### Takeaway
For a 15-minute, alert-only Nifty and Sensex option-buying system:
- **Sentiment should be a volatility/stand-aside filter and a confirmation layer, not a direction engine.** The highest-value pieces are free and price-derived (intraday breadth, India VIX change) or calendar-based.
- Text adds value mainly as an **unscheduled-shock classifier**.
- Polarity-based direction tilt from news or social media has **no India grade-A or B support at intraday horizons**. Its best non-India support is a small contrarian next-day effect (3–12 bps per SD).

### Cited Findings
- Index-level text-tone effects are small and reverse (Tetlock 8.1 bps then −6.8 bps; Garcia 12 bps in recessions vs 3.5 bps in expansions; FEARS reverses within 2 days). — [Tetlock](https://business.columbia.edu/sites/default/files-efs/pubfiles/3097/Tetlock_Media_Sentiment_JF.pdf), [Garcia](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12027), [FEARS](https://academicweb.nd.edu/~zda/FEARS.pdf)
- Text-based uncertainty tracks volatility closely (EMV correlation with VIX about 0.8, holding OOS 2019–2023), and policy news drives a large share of big moves (37% of US moves above |2.5%|). — [NBER w25720](https://www.nber.org/system/files/working_papers/w25720/w25720.pdf)
- LLM backtests can be inflated by memory (FINCAD corrections up to −67% in mean return), and the clean evidence is live and post-cutoff. — [arXiv 2605.24564](https://www.alphaxiv.org/abs/2605.24564), [arXiv 2601.11958](https://www.alphaxiv.org/abs/2601.11958)
- Simple intraday OHLCV signal families mostly fail after costs, while regime-conditioning signals survive (Mesfin 2026; see `02_strategy_evidence_part1.md`). Sentiment is most useful as *regime context*.

### Inferences

#### Role assignment
1. **Volatility/stand-aside filter (main role):**
   - Scheduled-event calendar.
   - Unscheduled-shock detector (text) × India VIX jump (market).
   - Output: `NO_NEW_ENTRY` for X minutes, `REDUCE_SIZE`, or `PREFER_DEFINED-RISK/ATM`.
2. **Confirmation (second role):** intraday breadth of the index constituents must agree with the direction of any price-based signal. A divergence vetoes the signal or downgrades its confidence.
3. **Slow regime tilt and sizing (third role):** a daily composite (FII long ratio, OI-PCR z-score, India VIX percentile, EOD breadth, MMI extremes, optionally a FEARS-India index) adjusts the confidence score by a small amount (e.g., ±5–10 points on a 100-point scale). It never triggers a trade by itself.
4. **Research-only logging:** LLM `direction_hint` and the aggregate news tone are logged but *not used* until they pass the protocol below.

#### Evaluation protocol (pre-registered, leakage-free)
- **Data:**
  - Own point-in-time log (first-seen UTC, source, raw title, hash, LLM JSON, model and prompt IDs) from day 1.
  - Historical backfill: GDELT India-filtered (file time as the timestamp) and the NIFTY headlines dataset (check its timestamp granularity), scored by anonymised + date-masked prompts or a point-in-time model.
  - Breadth backfill: 1-min constituent bars from a broker historical API.
- **Targets (volatility first):**
  - Nifty futures realised volatility over the next 15/60 min and rest-of-day.
  - P(|move over next 60 min| > 0.5%).
  - Option-premium outcome of the alert.
  - Direction hit rate is secondary, always judged against the 53–55% drift baseline (`04_nifty_measured_facts.md`).
- **Baselines** that every component must beat *incrementally*:
  - time-of-day volatility profile
  - prior-day realised volatility
  - India VIX level and 15-min change
  - opening gap and GIFT Nifty
  - event-calendar dummies
- **Metrics:**
  - Incremental R² / AUC, and the ratio of realised volatility in flagged vs unflagged windows.
  - For alerts: expectancy after spread, slippage and theta, with deflated Sharpe and the probability of backtest overfitting (`02_strategy_evidence_part1.md`).
  - Benjamini–Hochberg correction across all tested components.
- **Splits:** walk-forward with purged and embargoed folds. A **final untouched holdout** of the most recent 6 months. Then **live shadow mode for at least 60 sessions** before any component gets weight.
- **Power reality check:**
  - Detecting a daily directional correlation ρ = 0.05 at 80% power needs about ((1.96+0.84)/0.05)² ≈ **3,100 days (about 12 years)**. ρ = 0.10 needs about 780 days.
  - This is why *direction* tilts from sentiment cannot be validated within the project's horizon.
  - Volatility-conditioning effects (e.g., 1.5–2× realised volatility after severity-3 shocks) are much larger and testable in months.

#### Ranked shortlist of sentiment components to implement

| Rank | Component | Data source | Computation | Update | Role | Cost | Evidence grade |
|---|---|---|---|---|---|---|---|
| 1 | **Scheduled high-impact event flag** | RBI MPC calendar and RBI press RSS; Union Budget; US FOMC/CPI; election-result days; top-10 Nifty/Sensex-weight results dates; expiry days (Tue Nifty / Thu Sensex) | Binary `event_today` + `minutes_to_event`; post-event cool-off window; surprise tag from LLM on the first headlines | Daily pre-open + live | Stand-aside / avoid buying inflated pre-event IV; size down | ₹0 | B (EPU/EMV policy share, RBI-WP surprise → volatility; non-India or WP) |
| 2 | **Intraday constituent breadth** (weighted A/D, % above VWAP, breadth thrust, heavyweight-divergence flag) | Angel One SmartAPI websocket (Nifty 50 + Sensex 30 LTP/VWAP); index weights from NSE/BSE monthly factsheets | Bw = Σwᵢ·sign(rᵢ since open); %>VWAP; Δ over 30 min; divergence = sign(index) ≠ sign(Bw) | Every 15 min (computed from live ticks) | Confirmation / veto of direction signals | ₹0 | C (no intraday India study; must self-test, 1-min backfill possible) |
| 3 | **India VIX intraday shock** (already in system) used as the market-side sentiment gauge | NSE India VIX live | 15-min Δ and z-score vs time-of-day norm | Every 15 min | Volatility filter; pairs with #4 | ₹0 | A/B (see `03_…md`) |
| 4 | **Unscheduled news-shock detector** (event type × severity × headline-volume z-score) | ET markets+economy RSS, Business Standard markets RSS, Mint markets RSS, NDTV Profit, RBI press RSS, PIB RSS, NSE announcements (filtered to top weights + circulars); GDELT for backfill | Dedupe → drop price-report headlines → cheap LLM JSON tags (category, scope, surprise, severity) → 60-min count z-score of severity ≥ 2 macro/global items vs same-time baseline | Poll 1–2 min; evaluate at each 15-min check | `NO_NEW_ENTRY` 15–30 min after a severity-3 unscheduled shock; widen stops or reduce size; explain moves in alerts | About ₹100–300/month (Flash-Lite/nano + selective escalation); about ₹1,400/month if all on Haiku | B for the volatility link (EMV, NVIX, GPR, Tetlock-volume, non-India); C/untested for India intraday |
| 5 | **Daily positioning/sentiment composite** | NSE participant-wise OI (FII long ratio), F&O bhavcopy (OI-PCR), India VIX percentile, Nifty 500 EOD A/D, F&O turnover; optionally Tickertape MMI extremes | Equal-weight z-scores over 45–60 sessions (MMI-style), contrarian at extremes only | Daily, pre-open | Slow regime tilt / position-size scaler (±5–10 confidence points) | ₹0 | B/C (Kumari & Mahakud 2015; Seth & Kumar 2023 in-sample; FII and PCR evidence in `03_…md`) |
| 6 | **Overnight news-tone digest** (contrarian next-day) | Same RSS + GDELT, 15:30 to 09:00 IST window | LLM aggregate tone of non-price macro headlines; z-score; contrarian sign | Daily, 09:00 | Research-only until it beats the GIFT Nifty gap model; then at most a ±5 confidence nudge | Included in #4 | B (Tetlock/Garcia/Bond et al., non-India; small, reverses) |
| 7 | **FEARS-India search index** | Google Trends (IN; English + Hindi crash/recession terms) | Weekly or daily ΔSVI z-score | Daily or weekly | Slow volatility-regime / contrarian context | ₹0 | B (US FEARS; India stock-level only) |
| — | **Do not implement:** polarity-based intraday direction from news; X/Reddit/Telegram/YouTube sentiment; MMI as a standalone timing signal | — | — | — | — | — | D–B (weak, noisy, manipulable; SEBI rules make legal live content scarce) |

### Gaps
- None of the ranked components except India VIX has India-specific, robust OOS evidence at intraday horizons. Components 2 and 4 are **hypotheses to be tested by this project**, not established edges.
- The size of IV crush after Indian scheduled events (RBI MPC, Budget) on weekly Nifty and Sensex options was not researched here. It is needed to set the event-flag rule (avoid vs exploit).
- How much a news-shock flag adds beyond India VIX's own 15-min jump is unknown. If India VIX reprices within the same 15-min bar every time, component 4 reduces to an "explanation" feature, which is still useful for alerts but adds no predictive power.
