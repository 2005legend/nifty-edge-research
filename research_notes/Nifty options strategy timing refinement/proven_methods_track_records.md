# Proven systematic methods for equity indices and index options: live track records versus backtests

Evidence grades in this file (they differ from the grades in `02_strategy_evidence_part1.md`):
- **A**: live/real-money record or a published benchmark-index track record, and robust after costs
- **B**: peer-reviewed, with strong out-of-sample or post-publication evidence, but no live record
- **C**: practitioner backtest (Quantpedia, Alpha Architect, Concretum, blogs)
- **D**: anecdote, self-reported industry figures or marketing

Scope note: material already in the project report (`reports/Nifty options multifactor quant strategy.md`) and in `research_notes/02_strategy_evidence_part1.md` is only cross-referenced here, not re-researched. That covers the noise-band breakout, ORB replications, Baltussen et al. (2021) rest-of-day momentum, Rosa (2022), Kang et al. (2021), the Mesfin (2026) falsification study, Kurth et al. (2026) on the end of fast trend, Bhat et al. (2024) on the Indian overnight VRP, SEBI FY26, and 0DTE retail losses. The Wiley Scholar Gateway quota was exhausted during this session (it resets 1 Nov 2026), so academic searches specific to India were limited to web search.

---

## 1. Trend following / time-series momentum: what do live CTA records show net of fees, 2010–2026, and what is known about short-horizon trend?

### Takeaway
Trend following has the longest and best-documented real-money record of any systematic index-related method (grade A). But live results since 2000 are far below the century-long backtest: the SG Trend Index compounded about 5.3% a year against 8.0% for the S&P 500 TR. Its returns come in rare bursts (2008, 2014, 2022) separated by long flat stretches (2010–2019 and 2023–2025). The edge sits at 1–12-month horizons. Short-horizon trend on equity indices has decayed or reversed since about 2000–2009, so for an intraday Nifty system it can serve only as slow context, never as a trigger.

### Cited Findings
- **Backtest, 1880–2013 (AQR):** time-series momentum (1-, 3- and 12-month lookbacks) across 67 markets earned **14.9% a year gross and 11.2% net** of simulated costs and 2/20 fees, with 9.7% volatility, a **net Sharpe of 0.77** and **0.00 correlation to US equities**. Returns were positive in every decade. Costs were AQR's 2012 estimates, set at 2× for 1993–2002 and 6× for 1880–1992. — [Hurst, Ooi & Pedersen, AQR (2014 update)](https://www.TrendFollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf) — grade B (hypothetical, out of sample before 1985)
- In the same paper, a 60/40 portfolio with 20% moved into trend had a max drawdown of −50.2% instead of −62.3%, and its Sharpe rose from 0.38 to 0.54 (1880–2013). The authors saw no evidence that the weak post-2008 run was anomalous. They blamed higher cross-asset correlation after the GFC and suggested planning for a **future net Sharpe of about 0.4**, roughly half the historical figure. — [Hurst, Ooi & Pedersen](https://www.TrendFollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf)
- Conflicting summaries of the 2017 JPM version (1880–2016): one gives a net Sharpe of **0.76** after costs and 2/20 fees, with the lowest decade at 4.1% net — [Swedroe/ETF.com](https://www.etf.com/node/93905.md). Another gives an **average Sharpe of 0.4 after 2/20 fees** — [CXO Advisory](https://www.cxoadvisory.com/momentum-investing/trend-following-with-intrinsic-momentum-over-the-very-long-run). The difference is not resolved here (full-sample versus averaged-by-decade is a likely cause).
- AUM run by systematic trend followers grew from about $22bn (1999) to over $280bn (2014), per BarclayHedge as cited by AQR. — [Hurst, Ooi & Pedersen](https://www.TrendFollowing.com/whitepaper/Century_Evidence_Trend_Following.pdf)
- **Live index, since 2000 (grade A):** compound annual returns from Jan 2000 to Dec 2025 were **SG Trend Index 5.33%**, BTOP50 4.08%, TTU TF Index 7.43%, and S&P 500 TR 7.98%. — [Top Traders Unplugged, Dec 2025 report](https://www.toptradersunplugged.com/trend-following-performance-report-december-2025/)
- **Year by year, live:**
  - 2022: SG Trend **+27.3%**; SG CTA +20.1% (its best year since 2000); four-year cumulative 2019–2022 of +61.3% for SG Trend. — [Hedgeweek](https://www.hedgeweek.com/trend-followers-turn-leaders-ctas-deliver-record-returns-2022/)
  - 2023: SG Trend about **−3.3%**, SG CTA about −3%. — [StoneX](https://www.stonex.com/en/insights/ctas-on-course-for-positive-january-returns/)
  - 2024: SG Trend **+2.42%**, BTOP50 +4.44%, TTU TF +2.77%. — [TTU Dec 2024](https://www.toptradersunplugged.com/trend-following-performance-report-december-2024/). SG CTA about +2.4%. — [CFM](https://www.cfm.com/steady-trends-the-reality-of-cta-return-dispersion/)
  - 2025: SG Trend **+2.39%**, BTOP50 +2.81%, against S&P 500 TR +17.89%. — [TTU Dec 2025](https://www.toptradersunplugged.com/trend-following-performance-report-december-2025/). Over the 12 months to June 2025, SG Trend was about −15.05%. — [TTU June 2025](https://www.toptradersunplugged.com/trend-following-performance-report-june-2025/)
  - 2026: SG Trend +10.27% YTD at end-April — [TTU, 1 May 2026](https://www.toptradersunplugged.com/trend-following-week-in-review-may-1-2026/) — and **+7.49% YTD at 31 July 2026** — [TTU, 31 Jul 2026](https://www.toptradersunplugged.com/trend-following-week-in-review-july-31-2026/)
- **Live mutual fund (grade A):** the AQR Managed Futures Strategy Fund (I share), launched 5 Jan 2010, returned **4.16% a year since inception against 1.42% for T-bills**, with a 10-year return of 4.50%, 5-year of 12.53% and 1-year of 20.54% (to 31 Mar 2026). — [AQR fund page](https://funds.aqr.com/funds/aqr-managed-futures-strategy-fund)
  - Calendar years: 2017 −0.97%, 2018 −8.88%, 2019 +1.92%, 2020 −0.43%, 2021 −1.04%, **2022 +35.47%**, 2023 +2.08%, 2024 +8.13%, 2025 +14.62%. — [PortfoliosLab](https://portfolioslab.com/tools/stock-comparison/QLENX/AQMIX) (aggregator, not checked against AQR's annual report)
- **Short-horizon trend, live:** the SG Short-Term Traders Index tracks the 10 largest diversified short-term CTAs with holding periods under 10 days. — [Hedge Fund Journal](https://thehedgefundjournal.com/news/sg-short-term-ctas-show-improved-performance/); [Hedgeweek](https://www.hedgeweek.com/short-term-ctas-show-improved-performance/). Its 2022 return of **+11.3% equalled its best year ever** and was the best risk-adjusted SG index that year. — [Hedgeweek](https://www.hedgeweek.com/trend-followers-turn-leaders-ctas-deliver-record-returns-2022/)
- **Why short-horizon trend in equity indices weakened:** across 20 major indices in 15 countries, daily first-order index autocorrelation hovered around +0.05 from 1951, declined from the 1980s and **turned negative in the 2000s**. Weekly autocorrelation flipped sign before 2000. The change is tied to the growth of index futures, ETFs and index funds. — [Baltussen, van Bekkum & Da, JFE 2019](https://academicweb.nd.edu/~zda/Indexing.pdf) (DOI [10.1016/j.jfineco.2018.07.016](https://doi.org/10.1016/j.jfineco.2018.07.016)) — grade B
- Cross-reference (already in the project report): the Sharpe of a 5/20-day EWMA trend portfolio fell from 0.84 (1995–2009) to 0.12 (2009–2025), with equity indices hit hardest. — [Kurth et al. 2026](https://arxiv.org/abs/2607.01550)

### Inferences
- The A-grade record supports trend following as a **diversifying, slow, low-Sharpe premium** (live net Sharpe probably 0.3–0.5). It delivers in persistent multi-month macro moves and crises, not in day-to-day equity-index noise. Since the 2012 publication of time-series momentum (Moskowitz, Ooi & Pedersen), live performance has been about half the backtest or less, consistent with the McLean–Pontiff decay rates in Section 5.
- Live results come in a few concentrated years (2022 alone was about +27–35%). A system with 60–150 trades a year has nothing like that diversification, so it should expect a lumpier, lower-quality version of the same profile: long flat or losing stretches broken by occasional high-volatility regimes.
- At the horizon that matters here (minutes to one day, on one equity index), the evidence points the other way. Daily and weekly index autocorrelation is negative after 2000, and fast trend has collapsed. Time-series momentum therefore **cannot be the directional engine** of an intraday weekly-option system. At most, the sign of the 3–12-month Nifty futures return could enter as one context feature, which costs a registry trial and is low priority.
- The live short-term CTA index is the closest real-money analogue to "short-horizon systematic", and even there the best year was about +11%. It is not a high-Sharpe category.

### Gaps
- No long-run CAGR or 2023–2026 annual figures were found for the SG Short-Term Traders Index. No data on intraday-specific CTA programmes.
- SG Trend figures after July 2026 were not found. Man AHL and BarclayHedge CTA index records were not checked.
- No India-specific live trend-following track record was found (for example, an Indian CTA-style PMS or AIF with audited results).

---

## 2. Short-term mean reversion in index futures and ETFs (RSI(2)/Connors, IBS, 1–5-day reversal): persistence or decay after publication, and India evidence

### Takeaway
The best evidence (grade B) is structural: since about 2000, index returns have negative serial dependence at 1–5-day horizons around the world. A contrarian strategy had a gross Sharpe of about 0.63 after 1999. The authors tie it to index-product arbitrage and warn that turnover costs may make it unexploitable. Popular rule sets such as RSI(2) and IBS have only practitioner backtests (grade C). Intraday fades after large openings in index futures are statistically real but mostly disappear after the bid-ask spread. No peer-reviewed India study was found.

### Cited Findings
- A contrarian strategy trading against MAC(5), a weighted sum of the last four daily returns, earned an **annualized Sharpe of 0.63 across 20 indices (0.67 for the S&P 500 alone) after 2 March 1999**, against an average buy-and-hold Sharpe of 0.36 across those markets. Futures MAC(5) is negative for all 20 indices and significant for 12. ETF MAC(5) is negative too. The authors caution that "the strategy might not be exploitable to many investors after accounting for transaction costs". India is not among the 15 countries. — [Baltussen, van Bekkum & Da, JFE 2019](https://academicweb.nd.edu/~zda/Indexing.pdf)
- In the same paper, serial dependence reaches zero at an indexing level of about **1.4% of index capitalization**; each 1-point increase in indexing lowers MAC(5) by about 0.031. Month-end flow patterns cause short-term reversals, but the result survives controls for them. — [Baltussen, van Bekkum & Da](https://academicweb.nd.edu/~zda/Indexing.pdf)
- **Intraday reversal after large opening moves, US index futures, 1987–2002:** "highly significant", but adjusting for bid-ask costs "sharply reduces" its significance as a trading profit. — [Grant, Wolf & Yu, J. Banking & Finance 2005](https://ideas.repec.org/a/eee/jbfina/v29y2005i5p1311-1327.html)
- **S&P 500 and Hang Seng futures:** reversals after large opening moves are profitable after costs "though not by much". — [Fung, Mok & Lam, JBF 2000](https://scholars.hkbu.edu.hk/en/publications/intraday-price-reversals-for-index-futures-in-the-us-and-hong-kon/)
- Trading against the overnight return to capture the following intraday move gave the strongest short-term reversal results across stocks and futures, but at about 100% daily turnover. — [Della Corte, Kosowski & Wang 2015, summarized by CXO Advisory](https://www.cxoadvisory.com/technical-trading/overnightintraday-return-reversal-trading/) (secondary summary)
- **IBS on SPY (grade C):** parameters optimized on data up to 2000 "performed well" out of sample, long-only, with no slippage or commissions. — [r-bloggers 2013](https://www.r-bloggers.com/2013/01/ibs-reversion-edge-with-quantshare/). A vendor says IBS "has worked remarkably well for over two decades". — [Quantified Strategies](https://quantifiedstrategies.substack.com/p/the-internal-bar-strength-ibs-indicator) (vendor backtest)
- No independent post-publication study of Connors RSI(2) on SPY was found. Available sources are rule descriptions and forum posts (grade D). — [StockCharts forum](https://scan.stockcharts.com/discussion/comment/5401)
- **India context:** over about 12 years, only **46%** of Nifty days closed above their open, against **64%** of overnight moves being positive. — [Capitalmind 2020](https://premium.capitalmind.in/2020/08/capitalmind-chase-roaring-day-and-night/) (practitioner). Our own data (2015–2026): overnight +0.109% a day, open-to-close −0.069% a day, 46.7% of sessions up; sessions after a holiday gap up +0.18% and then fall −0.22% from open to close (t = −2.96). — [own data](<../04_nifty_measured_facts.md>), [project report](<../../reports/Nifty options multifactor quant strategy.md>)

### Inferences
- The defensible mechanism is **index-arbitrage price pressure**. Flows into index futures and ETFs push all constituents together, and the move partly reverses over 1–5 days. Nifty has a very large derivatives market relative to cash, so the mechanism plausibly applies to Nifty even though India was not in the sample. That is a hypothesis to test, not a finding.
- For our breakout system, the **background drift at the daily horizon is mean-reverting**. A noise-band breakout that extends a large multi-day move is fighting that background; one that runs against a large 3–5-day move is helped by it. This is a cheap, testable context feature (MAC(5) on Nifty daily returns), not a trigger.
- Standalone mean-reversion trades such as RSI(2) and IBS hold for 1–5 days. A weekly-option buyer cannot hold overnight without paying the overnight VRP (Bhat et al. 2024), and the strategies' edge per trade (tens of bps on the index) is below option round-trip costs. **Reject them as triggers.**

### Gaps
- No peer-reviewed estimate of Nifty or Sensex daily or weekly autocorrelation after 2010 was found. It can be computed in minutes from data the project already has (`nifty_daily_facts.py`).
- No independent decay study of RSI(2) or IBS after Connors & Alvarez (2009) was found.
- Della Corte et al. (2015) figures come from a secondary summary only.

---

## 3. Overnight/close-to-open effects and turn-of-day/turn-of-month patterns: persistence, and India evidence

### Takeaway
The overnight-return premium in index data is real and long-lived. India's own data show it strongly: Nifty earns its drift overnight and gives some back intraday. But **every live attempt to harvest it in liquid US products failed or faded after publication**. The NightShares ETFs closed in 2023, and the 2–3 a.m. "overnight drift" averaged about zero from 2021 to 2025. The turn-of-month effect is the most persistent calendar pattern internationally (31 of 35 countries) and has Indian evidence through 2023. The pre-FOMC drift died after 2015. For an intraday option buyer, these patterns are priors and context features, not trades.

### Cited Findings
- **QQQQ, 1999–2006:** the geometric average close-to-open risk premium was **+23.7%**, against **−23.3%** open-to-close. — [Kelly & Clark, J. Asset Management 2011](https://ideas.repec.org/a/pal/assmgt/v12y2011i2d10.1057_jam.2011.2.html); [Lafayette record](https://dspace.lafayette.edu/handle/10385/1012) — grade B
- **US index ETFs and most international index futures, 1999–2014:** overnight returns were significantly positive. — [Liu & Tse, IREF 2017](https://profiles.umsl.edu/en/publications/overnight-returns-of-stock-indexes-evidence-from-etfs-and-futures/) — grade B
- **"Tug of war":** all of the abnormal return on momentum strategies accrues overnight, while the abnormal returns of the other anomalies studied accrue intraday. The authors attribute this to different clienteles trading at the open and during the day. — [Lou, Polk & Skouras, JFE 2019](https://personal.lse.ac.uk/polk/research/TugOfWar.pdf) — grade B
- **The overnight drift and its disappearance:**
  - Original finding: in S&P 500 E-mini futures, 1998–2020 (5,691 days), the 2:00–3:00 a.m. ET window (the European open) earned about **3.7% a year, over 60% of the 5.9% close-to-close return**. The mechanism is dealer inventory risk: end-of-day sell imbalances predict the drift. — [Boyarchenko, Larsen & Whelan, NY Fed SR 917 / RFS 2023](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr917.pdf)
  - **Since 2021 (Jan 2021–Dec 2025, 1,245 days), the window has averaged close to zero.** The same is true in Nasdaq-100 and Dow E-minis. The dispersion of closing order imbalance fell from a 6.5% to a 2.9% standard deviation, "the only input that changed substantially". — [Liberty Street Economics, July 2026](https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/) — grade A for decay (exchange data, out of sample after publication)
- **Live product failure (grade A, negative):** NightShares launched NSPY and NIWM in June 2022 to hold equities only overnight. Both closed about 14 months later. NSPY was down 6.9% since inception against a 22% S&P 500 rally. — [ETF.com](https://www.etf.com/sections/news/2-nightshares-etfs-close-after-struggling-gain-traction); [WealthManagement](https://www.wealthmanagement.com/etfs/-night-effect-etfs-to-shut-down-with-overnight-stock-returns-elusive). The leveraged NSPL was liquidated after 31 Aug 2023. — [SEC 497 filing](https://www.sec.gov/Archives/edgar/data/1199046/000158064223004244/nightshares500_497.htm). The Fed authors note ETF-specific costs may have contributed. — [Liberty Street](https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/)
- **India:** "essentially, all of the moves happen when there is no trading" in cumulative Nifty charts, and about 90% of HDFC Bank's move came overnight. The pre-open auction started in 2010. — [Capitalmind 2019](https://premium.capitalmind.in/2019/10/while-you-were-sleeping-what-stocks-do-overnight-versus-in-trading-hours/) (practitioner). Our own measurement: overnight +0.109%/day, intraday −0.069%/day since 2015. — [own data](<../04_nifty_measured_facts.md>)
- **Turn of month:** over 1926–2005, US investors earned no average reward for market risk outside the turn-of-month window. The effect appears in 31 of 35 countries, is not confined to small stocks or year- or quarter-ends, and is **not explained by month-end flows or volume**. — [McConnell & Xu, FAJ 2008](https://ideas.repec.org/a/taf/ufajxx/v64y2008i2p49-64.html) — grade B
- **India turn of month:** significant for Nifty 50, Sensex and the small-cap indices, April 2007 to February 2023, and stronger in small-cap indices. — [Review of Finance and Banking 15(2), 2023](https://rfb.ase.ro/Vol15-2023/dec2a.asp). Earlier, Nifty 1994–2005 showed high mean returns before and during the first half of the month. — [Mangala & Sharma 2007](https://ideas.repec.org/a/sae/padigm/v11y2007i2p16-22.html) — grade B/C (lower-tier journals, costs not tested)
- **Event drift that died:** Lucca & Moench (2015) found large pre-FOMC excess returns from Sep 1994 to Mar 2011. Extending the sample to Dec 2019, the drift "essentially disappeared after 2015". — [Kurov, Wolfe & Gilbert, Finance Research Letters 2021](https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html); [PDF](https://www.skidmore.edu/economics/documents/KurovWolfeGilbert-TheDisappearingPre-FOMC-Announce-Drift-200914.pdf) — grade B. Cross-reference: on RBI decision days, Nifty's range was 1.02× implied and the sign of the day's direction flipped between 2016–19 and 2020–26. — [project report](<../../reports/Nifty options multifactor quant strategy.md>)

### Inferences
- The pattern repeats: **calendar and clock effects in the most liquid index futures decay fastest once published** (pre-FOMC after 2015, the 2–3 a.m. drift after 2021, intraday momentum in SPY per Rosa 2022). The plain overnight-versus-intraday split has survived longer, but live products could not earn it after costs.
- For a Nifty intraday option buyer, the overnight premium is captured by holders of the underlying and sold to option buyers through overnight VRP (Bhat et al. 2024). The negative open-to-close drift is a **standing headwind for intraday calls and a tailwind for intraday puts**. The model should price this through a side (call/put) feature, not treat both sides as symmetric.
- Turn of month is the most persistent calendar effect with an explicit Indian replication. But its daily size (a few bps of index drift) is far below option costs, so at most it shifts the probability on the margin.

### Gaps
- The figures in Cliff, Cooper & Gulen (2008) could not be retrieved or verified.
- No clean source splits US overnight and intraday returns for 2020–2026. No peer-reviewed India paper tests whether the Nifty overnight/intraday split persists after 2020 (our own data cover it descriptively).
- No study of Indian turn-of-month effects after 2023 or after costs was found.

---

## 4. Option-strategy benchmarks with real history (Cboe PUT, BXM, CNDR, PPUT and others; NSE/BSE): what they show about buying versus selling index options

### Takeaway
Cboe benchmark indices give the cleanest long public record (grade A as published benchmarks, though gross of costs and partly back-filled before 2007). Over 35+ years, put-writing (PUT) and buy-writes (BXM) returned close to the S&P 500 with about two-thirds of its volatility. From 2010 to October 2026, however, they returned **7–9% a year against about 15% for the S&P 500 TR in 2020–2025**, and the defined-risk short-volatility benchmark (**CNDR, iron condors) earned roughly 0% a year from 2010 to 2025**. Buying index options loses on average: ATM straddles lose about 3% a week, and protective puts are beaten by simply holding less equity. No NSE or BSE option-strategy benchmark index was found. India's real-money benchmark is SEBI's trader-level data, where individual option buyers lose and algorithmic proprietary traders and FPIs earn.

### Cited Findings
- **PUT, July 1986 to December 2015:** gross compound return of **10.1% against 9.8% for the S&P 500 TR**, with volatility of 10.1% against 15.3%. Turnover is far higher than the index, figures are gross, and much of PUT's pre-2007 history was built retroactively. — [CXO Advisory on Bondarenko (2016)](https://www.cxoadvisory.com/equity-options/performance-of-cboe-putwrite-indexes)
- **June 1986 to December 2017:** PUT returned 10.1% against 10.3% for the S&P 500 with about 66% of the risk. — [Asset Consulting Group](https://acgnet.com/getattachment/845363f3-97c7-4ac9-be31-762e60b9143d/BXM-PUT-Update;.aspx)
- From 1990 to 2018, VIX averaged **19.3%** against **15.1%** realized S&P 500 volatility, which is the volatility risk premium PUT harvests. — [Cboe on Bondarenko (2019)](https://www.cboe.com/insights/posts/white-paper-shows-volatility-risk-premium-facilitated-higher-risk-adjusted-returns-for-put-index/)
- BXM collected an average gross premium of **1.7% a month** since May 2006. The covered-writing indices had betas of 0.57–0.82 and "often" lagged the S&P 500 in bull markets. — [Cboe](https://www.cboe.com/insights/posts/benchmark-indices-series-income-generation-and-smoother-returns-with-cboes-bxm-bxmd-put-and-cmbo-indices). ETPs tracking BXM substantially underperform the index itself. — [CXO Advisory](https://www.cxoadvisory.com/equity-options/performance-of-cboe-putwrite-indexes)
- **CNDR** (sell ~0.20-delta SPX put and call, buy ~0.05-delta wings, monthly): max drawdown **19%** against 47.1% for BFLY and 51% for the S&P 500 over about 35 years, and 59% of months returned 0–2%. — [Cboe](https://www.cboe.com/insights/posts/benchmark-indices-series-volatility-management-with-cboes-bfly-and-cndr-indices/)
- **Own calculation from Cboe's official daily index files**, as compound annual returns ([PUT](https://cdn-api.cboe.com/api/global/us_indices/daily_prices/PUT_History.csv), [BXM](https://cdn-api.cboe.com/api/global/us_indices/daily_prices/BXM_History.csv), [CNDR](https://cdn-api.cboe.com/api/global/us_indices/daily_prices/CNDR_History.csv), [PPUT](https://cdn-api.cboe.com/api/global/us_indices/daily_prices/PPUT_History.csv); S&P 500 TR annual returns from [YCharts](https://ycharts.com/indicators/sandp_500_total_return_annual)):

  | Index | 2010–19 | 2020–25 | 2022 | 2023 | 2024 | 2025 | 2026 YTD (16 Oct) |
  |---|---|---|---|---|---|---|---|
  | PUT (cash-secured ATM put-write) | 7.3% | 9.1% | −7.7% | +14.3% | +17.8% | +9.2% | +10.7% |
  | BXM (ATM buy-write) | 7.0% | 7.2% | −11.4% | +11.8% | +20.1% | +8.9% | +11.0% |
  | CNDR (iron condor) | **−0.7%** | **+1.1%** | −1.1% | +2.6% | +10.1% | +0.4% | +8.1% |
  | PPUT (S&P 500 + 5% OTM put) | 9.7% | 12.4% | −19.8% | +19.2% | +20.5% | +14.3% | +8.0% |
  | S&P 500 TR | n/a here | ≈15.1% | −18.1% | +26.3% | +25.0% | +17.9% | n/a |

  CNDR rose from 100 (June 1986) to 528 (July 2004), about 9.7% a year, reached 774.8 at end-2009, and stood at 828.9 on 16 Oct 2026. Its 2010–2025 compound return is −0.1% a year.
- **Buying options:** zero-beta ATM S&P 500 straddles lose **about 3% a week** on average, implying a priced volatility-risk factor. — [Coval & Shumway, JF 2001 (abstract)](https://academicnewsletter.sufe.edu.cn/info/361566) — grade B
- **Protective puts:** holding 36.5% S&P 500 and 63.5% cash matched PPUT's 2.5% compound excess return (1996–2014) with a smaller drawdown. Puts reduce drawdowns only when there is no VRP and the drawdown falls exactly within the option's life. — [Israelov, J. Alternative Investments 2019 (AQR)](https://www.aqr.com/insights/research/white-papers/pathetic-protection-the-elusive-benefits-of-protective-puts). PPUT max drawdown was −32.1% against −20.9% for the matched mix (July 1986–May 2016). — [CXO Advisory](https://www.cxoadvisory.com/equity-options/do-protective-equity-index-puts-work-well/) — grade A/B (benchmark data, peer-reviewed analysis)
- **Live volatility hedge funds** (Cboe Eurekahedge indices, grade A but only snapshots found): the long-volatility index returned **+39.70%** and the tail-risk index **+44.29%** in Q1 2020. — [Hedgeweek](https://www.hedgeweek.com/long-volatility-and-tail-risk-hedge-funds-post-strongest-q1-returns/). Short-volatility managers were −8.08% YTD in November 2018, the worst of the volatility indices that year. — [Opalesque](https://www.opalesque.com/industry-updates/5533/eurekahedge_hedge_fund_index_declines_as_of553.html)
- **India, real money:** over FY22–FY24, about 93% of more than 1 crore individual F&O traders lost money, averaging about ₹2 lakh each including costs, and only 1% made more than ₹1 lakh after costs. In FY24, proprietary traders booked about ₹33,000 crore and FPIs about ₹28,000 crore of gross profit, with **96% of prop profits and 97% of FPI profits coming from algorithmic trading**. — [Wright Research summary of SEBI](https://wrightresearch.in/blog/sebi-futures-and-option-report-individual-traders-in-fandos-incur-rs-18-lakh-crore-loss-over-3-years); [Benzinga India](https://in.benzinga.com/24/09/40994647/sebi-study-unveils-93-of-individual-f-o-traders-suffered-losses-between-fy22-and-fy24). FY26: 87.7% of individuals lost, and option losses were "largely independent of market direction". — [SEBI Aug 2026](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf) (already in the report)
- No NSE Indices or BSE covered-call, put-write or other option-strategy benchmark index could be confirmed. Searches of niftyindices.com methodology documents returned none. — [NSE equity index methodology](https://www.niftyindices.com/Methodology/Method_NIFTY_Equity_Indices.pdf)

### Inferences
- **Option selling has the strongest benchmark record, but most of PUT's and BXM's return is equity beta plus a modest VRP.** With the equity beta hedged out (CNDR), the index-level short-volatility premium after 2009 was about zero before costs. That is a striking, under-reported fact: defined-risk premium selling on the world's most liquid index did not pay for 16 years.
- **Option buying is the losing side of a priced premium** in every long record found: Coval–Shumway straddles, PPUT against an equity/cash mix, and SEBI's individual buyers. Long options pay off only in rare, short bursts (Q1 2020). A buyer's edge must therefore come from **direction and timing strong enough to beat VRP plus costs**, and only over short holds. This confirms the report's rules: intraday only, never overnight, and buy only when the remaining-session implied move is not rich against the HAR forecast.
- India's persistent winners are algorithmic institutions, which matches US HFT evidence (Section 6). A manually executed retail buyer is structurally on the other side of most option flow.

### Gaps
- Exact Bondarenko (2019) figures for 1986–2018 were not retrieved. One figure (PUT 10.32% a year, 9.91% volatility) appears in [PlanSponsor](https://www.plansponsor.com/new-study-focuses-on-benchmark-for-collateralized-putwrite-strategy/) with no period stated.
- Cboe benchmark returns are **gross** of costs, and much of their pre-2007 history is back-filled. My table uses index levels only, so 2010–2019 S&P 500 TR and annual Sharpe ratios were not computed.
- WPUT and 0DTE put-write benchmark data were not pulled. Long-run Eurekahedge long-volatility versus short-volatility CAGRs were not found.
- No Indian option-strategy index or audited Indian option-selling fund record was found.

---

## 5. Post-publication decay and replication: what share of edges survive, and what predicts survival?

### Takeaway
Published equity anomalies lose roughly a quarter of their return out of sample and about 58% after publication in the US. About two-thirds of 450 anomalies fail a basic t > 1.96 test when microcaps are handled properly. After trading costs and decay, the average US anomaly earns only about 4 bps a month. But replication is not uniformly bad. Factors grouped by theme replicate across 93 countries, and outside the US, post-publication decay is not reliable. Edges survive when they are **compensation for a real risk** (trend's crisis alpha, VRP crash risk), when they are **driven by a structural flow** (indexing-driven reversal, month-end and payment flows), or when they are **costly or capacity-limited to arbitrage**. They die fastest when they are **cheap, simple timing rules on the most liquid US index futures**.

### Cited Findings
- **McLean & Pontiff (JF 2016), 97 predictors:** returns are **26% lower out of sample**, an upper bound on data mining, and **58% lower after publication**, implying about 32 points of decay from publication-informed trading. Decay is larger for predictors with higher in-sample returns. Returns stay higher in portfolios concentrated in high-idiosyncratic-risk, low-liquidity stocks, where arbitrage is costly. After publication, correlations with other published predictors rise. — [McLean & Pontiff PDF](https://Www.Gwern.net/doc/economics/2016-mclean.pdf); [Ivey PDF](https://ivey.uwo.ca/media/3775549/pontiff.pdf) — grade B
- **Hou, Xue & Zhang (NBER w23394):** with NYSE breakpoints and value-weighted returns, **286 of 447 anomalies (64%) are insignificant at 5%**, including 95 of 102 liquidity variables (93%). At t ≥ 3, 380 (85%) fail. Surviving anomalies are often much smaller than originally reported. — [NBER](https://www.nber.org/papers/w23394.pdf). (The published RFS 2020 version is widely quoted as 65% of 452 failing |t| ≥ 1.96 and 82% failing 2.78. I could not verify that wording.)
- **Jensen, Kelly & Pedersen (JF 2023, 78(5):2465–2518):** using a Bayesian approach, most factors replicate, cluster into 13 themes, and work out of sample across 93 countries. — [NBER w28432](https://www.nber.org/papers/w28432) — grade B
- **Jacobs & Müller (JFE 2020, 135(1):213–230), 241 anomalies in 39 markets:** **the US is the only country with a reliable post-publication decline.** Barriers to arbitrage segment markets, and anomalies look more like mispricing than data mining. — [University of Duisburg-Essen record](https://fin.wiwi.uni-due.de/en/research/publications/anomalies-across-the-globe-once-public-no-longer-existent-14591) — grade B
- **Chen & Velikov (JFQA 2023), 204 anomalies:** the average expected return is **4 bps a month net of effective spreads and post-publication effects**. The strongest anomalies net at most about 10 bps after data-mining controls, and combinations about 20 bps. — [Penn State record](https://pure.psu.edu/en/publications/zeroing-in-on-the-expected-returns-of-anomalies/); [Fed FEDS version (8 bps)](https://www.federalreserve.gov/econres/feds/zeroing-in-on-the-expected-returns-of-anomalies.htm) — grade B
- **Index and timing edges that decayed:**
  - the pre-FOMC drift disappeared after 2015 — [Kurov et al. 2021](https://ideas.repec.org/a/eee/finlet/v40y2021ics1544612320315956.html)
  - the E-mini 2–3 a.m. overnight drift has averaged about zero since 2021, after publication — [Liberty Street 2026](https://libertystreeteconomics.newyorkfed.org/2026/07/the-disappearing-overnight-drift/)
  - SPY intraday momentum vanished out of sample after publication (Rosa 2022), and fast trend collapsed after 2009 (Kurth 2026); both are cross-referenced from the [project report](<../../reports/Nifty options multifactor quant strategy.md>)
- **Edges that survived with lower size:** time-series momentum (live Sharpe roughly half the backtest; Section 1), VRP via PUT and BXM (live benchmark since 1986; Section 4), and turn of month (31 of 35 countries; Indian evidence through 2023; Section 3).
- **A mechanism-driven change of sign:** daily index serial dependence flipped from positive to negative as indexing grew. — [Baltussen, van Bekkum & Da](https://academicweb.nd.edu/~zda/Indexing.pdf)

### Inferences
- **Survival checklist**, synthesized from the sources above:
  1. Is there a counterparty who **pays** for the edge, through risk transfer or hedging demand (VRP, trend's crisis convexity)? If so, it is likely to persist at lower size.
  2. Is there a **structural flow** that does not respond to publication (index arbitrage, month-end payment cycles, dealer gamma hedging)? Likely to persist, but the sign can change when market structure changes (closing imbalances, expiry rules).
  3. Is it **expensive or capacity-limited** to arbitrage? It decays less (McLean–Pontiff; Jacobs–Müller outside the US).
  4. Is it a **cheap, simple clock or pattern rule on a liquid index future**? Expect fast decay to about zero after publication.
- **India-specific nuance:** Jacobs–Müller suggests edges decay less outside the US. India also has explicit structural flows: retail option-buying demand, a 59% expiry-day share of option turnover, and the 15:15–15:35 closing auction since August 2026. A mechanism-grounded US edge could be stronger in India, but **market-structure changes** (expiry-day moves, the auction, lot-size and STT changes) can reset it overnight. The 2021 overnight-drift collapse came from a microstructure change, not from arbitrage of the anomaly itself.
- **Planning haircut for our system:** treat any published intraday edge as worth **at most about 40–50% of its backtest** (McLean–Pontiff's 58% decay applies to cross-sectional anomalies; index-timing edges have shown decay to zero). For the noise-band breakout (published 2024), the decisive test is the **post-publication Nifty sub-sample from mid-2024 onward**.

### Gaps
- No study of post-publication decay specifically for Indian index or derivative timing strategies was found.
- The exact published RFS wording of Hou, Xue & Zhang was not retrieved.

---

## 6. Independently verified profitable day trading: who persistently profits intraday, and with what strategies?

### Takeaway
Exchange- and regulator-level data from Taiwan, Brazil and India all show the same thing: **fewer than 1–3% of individual day traders are predictably profitable after costs**, and losses rise with turnover. The persistent winners in exchange data are **fast, liquidity-taking HFTs and algorithmic proprietary and FPI desks**. They trade with permanent price moves and macro news, provide liquidity, and earn spreads, with large economies of scale and speed. Prop-firm "funded trader" statistics are self-reported (grade D) and point to roughly 1–7% ever receiving a payout. None of these winning strategy types is available to a manual trader acting on alerts with a 30–90-second delay.

### Cited Findings
- **Taiwan, 1992–2006 (exchange data, grade A):** **fewer than 1% of day traders** predictably earn positive abnormal returns net of fees. The top 500 day traders by prior-year return earned **61.3 bps a day before fees and 37.9 after**; the bottom group earned −11.5 and −28.9. — [Barber, Lee, Liu & Odean, J. Financial Markets 2014](https://www.escholarship.org/uc/item/7k75v0qx); [working paper](https://faculty.haas.berkeley.edu/odean/papers/day%20traders/Day%20Trading%20Skill%20110523.pdf)
- A later version finds that fewer than 3% of day traders predictably profit after costs, accounting for under 10% of day-trading volume, and that "97% of day traders can expect to lose money". — [Barber et al., "Learning fast or slow" (2018 draft)](https://www.econ.puc-rio.br/uploads/adm/seminarios/Learning_fast_or_slow_180606.pdf)
- **Brazil mini-Ibovespa futures, 2013–2015 (19,646 people, CVM regulator data, grade A):** of those who day traded more than 300 days, **97% lost money**. Only **1.1% earned more than the minimum wage**, and only 0.4–0.5% more than a bank teller's starting salary. There was no evidence of learning. — [Chague, De-Losso & Giovannetti](https://econpapers.repec.org/RePEc:fgv:eesptd:525)
- **India, equity-cash intraday, FY23 (SEBI, about 6.9 million traders):** about 70–71% lost money, with an average loss of ₹5,371. Loss-makers traded more. Their costs equalled **57% of their trading losses**, against 19% of profits for profit-makers. Traders under 30 had a 76% loss rate. — [Business Standard](https://www.business-standard.com/markets/news/over-70-intra-day-traders-incur-losses-during-fy23-reveals-sebi-study-124072401110_1.html)
- **India F&O:** proprietary traders and FPIs earned gross profits of ₹33,000 crore and ₹28,000 crore in FY24, with 96–97% of those profits from algorithms. Individuals spent about ₹50,000 crore on F&O costs over FY22–24, 51% of it brokerage. — [Wright Research on SEBI](https://wrightresearch.in/blog/sebi-futures-and-option-report-individual-traders-in-fandos-incur-rs-18-lakh-crore-loss-over-3-years)
- **HFT in E-mini S&P 500 (CFTC account-level data, grade A):** aggressive, liquidity-taking HFTs earned an average annualized alpha of **90.67%**, against **23.22%** for passive ones. Revenues pile up at the top firms ("winner-takes-all"). Small latency differences mean large revenue differences, and new entrants are less profitable and more likely to exit. — [Baron, Brogaard & Kirilenko, CFTC 2014 draft](https://www.cftc.gov/idc/groups/public/@economicanalysis/documents/file/oce_riskandreturn0414.pdf)
- HFT liquidity-demanding trades go in the direction of permanent price changes and against transitory pricing errors, including around macro news. HFT liquidity-supplying orders are adversely selected. — [Brogaard, Hendershott & Riordan, RFS 2014 (ECB WP version)](https://ecb.eu/pub/pdf/scpwps/ecbwp1602.pdf) — grade B
- **Prop-firm challenges (self-reported, grade D):** across about 300,000 accounts, about 14% passed and about 45% of those reached a payout, roughly 7% of all traders. The average funded trader lasted about 22 days. — [CoinGape on FPFX Tech data](https://coingape.com/blog/93-of-funded-prop-traders-never-see-a-payout-a-new-report-explains-why/). One firm's CEO put the payout chance at 1–2%. — [Finance Magnates](https://www.financemagnates.com/forex/only-1-in-20-traders-pass-prop-firm-challenges-reports-the-funded-trader/)

### Inferences
- What persistent intraday winners have in common: **speed, liquidity provision or spread capture, very high trade counts across many instruments, low per-trade costs, and information processed in milliseconds**. None of these suit an alerts-only system with manual execution and one lot. The remaining plausible edge for such a system is **slow, low-turnover, regime-level**: holds of 45–90+ minutes, trades taken rarely, and a mechanism (dealer gamma, index arbitrage) that does not depend on being first.
- **Turnover is the variable most consistently tied to loss** (SEBI cash and F&O, Barber et al., Chague et al.). The 1-a-day, 3-a-week cap is directly supported. Costs at 57% of losses among Indian intraday losers match the report's estimate that fixed charges are about 11% of a ₹500 stop.
- Barber et al.'s top-ranked day traders did show persistence. The rare skilled minority exists, so a strategy's live record over 100+ trades, not its backtest, is the evidence that counts. This supports the report's SPRT go/no-go design.

### Gaps
- No independent, audited study of Indian prop-desk strategy types was found; SEBI reports only that profits are algorithmic.
- No exchange-data study isolates profitable *manual* index-option intraday traders in India.

---

## 7. For each method: evidence grade, effect after costs, recent performance, mechanism and fit with a one-lot intraday Nifty/Sensex system; ranked list and rule changes

### Takeaway
The methods with the strongest real-world proof (trend following, VRP harvesting, the turn-of-month and overnight effects) are slow risk premia or calendar flows. None is directly tradable by an intraday, one-lot, long-only option buyer, and two of them (VRP, overnight drift) are paid *by* option buyers. The current design (noise-band breakout as trigger, rest-of-day momentum on probation, option/macro/sentiment data only for gating) stays defensible. But the evidence calls for a lower expected edge, a post-publication test window, a side-asymmetric prior, and one cheap reversal-context test.

### Cited Findings
Each row draws on Sections 1–6 and the sources cited there.

| # | Method | Grade | Effect after costs | 2020–2026 behaviour | Mechanism | Fit for our system |
|---|---|---|---|---|---|---|
| 1 | Time-series trend (1–12-month) | **A** | Live SG Trend 5.33%/yr since 2000; AQR fund 4.16%/yr vs T-bills 1.42% since 2010; backtest net Sharpe 0.77 (1880–2013), planning Sharpe ~0.4 | 2022 +27%; 2023–25 roughly flat; 2026 +7.5% YTD (July) | Under-reaction and over-reaction, hedging flows, crisis convexity | **Reject as trigger** (horizon mismatch); optional slow context feature |
| 2 | Index VRP / option selling (PUT, BXM) | **A** (gross benchmark) | PUT ~10%/yr vs S&P ~10% at ~2/3 the volatility (1986–2017); 7–9%/yr 2010–25; CNDR iron condor ~0%/yr 2010–25 | PUT +9.2% 2025, +10.7% 2026 YTD; mostly equity beta | Insurance premium for crash risk | **Reject** as a strategy (₹29k short-leg margin; Indian VRP is earned overnight). **Adopt** as a cost model for buying |
| 3 | Buying index options (straddles, protective puts) | **A/B (negative)** | Zero-beta straddles −3%/week; PPUT dominated by an equity/cash mix; SEBI individuals lose | Long-volatility funds won only in short bursts (Q1 2020 +40%) | Pays the VRP | Constrains us: buy only with a directional edge, short holds, intraday only (already in design) |
| 4 | Overnight vs intraday split | **A** (index data) / **A-negative** (live ETFs) | Long-run large in index data; NightShares failed live; E-mini 2–3 a.m. drift ~0 since 2021 | Decayed in the US; Nifty 2015–26 still +0.109% overnight vs −0.069% intraday a day | Inventory and clientele effects | **Adapt**: side-asymmetric prior (negative intraday drift taxes calls) |
| 5 | Turn of month | **B** (31/35 countries; India 2007–23 B/C) | A few bps/day; costs not tested | No post-2023 India test | Payment and flow cycles (debated) | **Context feature only**, low priority |
| 6 | 1–5-day index reversal (negative serial dependence) | **B** | Gross Sharpe 0.63 after 1999; may not survive costs | Not measured for 2020–26 | Index-product arbitrage pressure | **Adapt**: a MAC(5)-style context feature to test on Nifty; reject RSI(2)/IBS as triggers |
| 7 | Intraday reversal after big opens | **B** | Significant, but mostly gone after spread | n/a | Liquidity-shock reversal | Context for gap days only (already "gap as context") |
| 8 | Rest-of-day intraday momentum | **B**, decayed in SPY | Futures OOS R² +2.88%; SPY gone after publication | Rosa 2022: decayed | Dealer short-gamma hedging, late-informed trading | **Keep on probation** (already) |
| 9 | Noise-band / ORB breakout | **C/B** | SPY Sharpe 1.33 (paper); replications fall to ~0.2 with slippage | 76% of one replication's profit from 2022 | Volatility-regime and trend days | **Keep as core trigger**, but test strictly post-publication; no live record anywhere |
| 10 | Scheduled-event direction (pre-FOMC) | **B, decayed** | Gone after 2015 | Gone | Uncertainty resolution | **Reject** direction trades on events; keep event volatility gating |
| 11 | Retail day trading in general | **A (negative)** | <1–3% predictably profitable; 97% of persistent Brazilian day traders lost | SEBI: 70% intraday cash losers FY23; 87.7% of F&O individuals lost FY26 | Costs, adverse selection, speed | Supports low turnover, rarity and SPRT |
| 12 | HFT / market making / algo prop | **A** (for those firms) | Aggressive HFT 90% annualized alpha; Indian algo prop/FPI earned ₹61k crore gross in FY24 | Ongoing | Speed, spread, inventory | **Not replicable** manually |

### Inferences
**Ranked by strength of real-world proof, with what each implies for us:**

1. **Trend following (A).** *Implication: reject as trigger; optionally adapt as context.* Its record shows that even the best-proven systematic edge has a live net Sharpe of about 0.3–0.5 with multi-year droughts. It works at horizons we cannot hold.
2. **VRP / option selling (A, gross).** *Implication: reject as strategy at ₹10,000; adopt as a constraint.* We are on the paying side. Keep "never overnight" and "implied move not rich against the HAR forecast". The CNDR result also warns against assuming that the "sell premium" fallback would rescue the account later at ₹50,000: defined-risk index premium-selling earned about 0% over 2010–2025 before costs.
3. **Overnight/intraday split (A in data, failed live).** *Implication: adapt.* Price the persistent negative Nifty open-to-close drift as a side-specific prior.
4. **Turn of month (B).** *Implication: context feature at most.* Below option costs on its own.
5. **Short-horizon index reversal (B).** *Implication: adapt via a single test.* It is the best-supported mechanism near our horizon. It argues that breakouts extending a stretched multi-day move deserve a lower probability.
6. **Rest-of-day momentum (B, decayed in the US).** *Implication: keep on probation.* It is the only intraday directional effect with a multi-market out-of-sample record, and it already has post-publication decay in SPY.
7. **Noise-band breakout (C/B).** *Implication: keep as core, but it is the weakest-proven component.* No live or benchmark record exists anywhere. The system's directional core rests on a single 2024 paper and harsher replications.
8. **Event-drift trades (B, decayed); RSI(2)/IBS (C); retail day-trading patterns (A-negative).** *Implication: reject.*

**Concrete rule changes proposed:**
- **R1. Lower the planning edge to fit the base rates.** The report's working edge is a per-trade Sharpe of about 0.13 (p ≈ 0.43 at +1.9R/−1.1R). That implies an annual Sharpe of about **1.0 at 60 trades a year, 1.3 at 100, and 1.6 at 150** (own calculation, 0.13 × √N). That is two to four times the live Sharpe of the best-proven systematic methods (trend about 0.3–0.5; PUT about 0.6–0.7 gross, with most of it equity beta). Plan and size around **p uplift of 2–4 points above no-edge odds, not 6+**. Treat any backtest showing annual Sharpe above 1.5 as presumptively overfit until the SPRT confirms it live.
- **R2. Make the post-publication period decisive.** In the Nifty backtest of the noise-band trigger, report results separately for before and after June 2024, the publication of Zarattini, Aziz & Barbon. For rest-of-day momentum, use before and after 2021. Demote a trigger whose post-publication edge is less than half its pre-publication edge, even if the full-sample result passes. Record this in the experiment registry as a pre-registered criterion, not an extra trial.
- **R3. Add a call/put side term to the meta-model.** The persistent negative intraday drift and the asymmetric spot-volatility beta mean the model must not share one intercept across sides. This is already partly covered by context features; make it explicit as one binary column. It costs one parameter, within the ridge budget.
- **R4. Run one free reversal-context test (one registry trial).** Compute Nifty daily AR(1) and MAC(5) for 2010–2026 from the existing daily data. If MAC(5) is significantly negative after 2015, add a "stretch" feature to the meta-model, for example the last 3–5 daily returns in units of the HAR forecast, signed against the proposed side. Do not add it as a trigger. If it is not significant, drop it permanently.
- **R5. Keep trades rare.** Keep the 1-a-day, 3-a-week cap even after capital grows. Every verified day-trader dataset ties loss rates to turnover, and turnover is SEBI's strongest correlate of losses.
- **R6. No direction from scheduled events or the calendar.** Pre-FOMC drift, RBI days and turn of month enter only as range or context features (already the design). Add turn of month (last trading day plus the first 3 days) as a context dummy only if the registry budget allows; it is lowest priority.
- **R7. Do not count on spreads as the future rescue.** Before moving to defined-risk premium-selling at about ₹50,000, require a separate Indian test after costs. The best US benchmark for that structure (CNDR) returned about zero for 16 years.
- Record these as decisions with their reasons in the project decision log, per the project's practice.

### Gaps
- The figures behind R1 combine a project-internal edge assumption with external live Sharpe ranges. The live Sharpe of SG Trend since 2000 and the net-of-cost Sharpe of PUT were not computed here, so the "two to four times" comparison is approximate.
- R4's premise (negative Nifty daily serial dependence after 2010) is untested. India was not in the Baltussen et al. sample.
- No live or audited track record of any intraday index-option *buying* strategy, anywhere, was found. The absence is itself informative, but it is a gap.
