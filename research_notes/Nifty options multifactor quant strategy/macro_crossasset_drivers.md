# Macro, scheduled-event and cross-asset drivers of Nifty 50 / Sensex at daily and intraday horizons, and a daily "macro bias and risk" score

Researched 6 Oct 2026, for a personal alert-only system that buys Nifty (weekly expiry Tuesday) and Sensex (weekly expiry Thursday) options with ₹5,000 capital.

**Grades.** A = peer-reviewed, India, robust. B = peer-reviewed but not India, or India with an old sample, a low-tier journal or no robustness checks. C = practitioner analysis, working paper or news data. D = anecdote or a claim whose sourcing can't be traced.

**Our own measurements** are graded OWN-R (holds in both 2015–19 and 2020–26, or N ≥ 150) or OWN-F (fragile: small N, the sign flips between periods, or many tests were run).
- All OWN numbers are **in-sample and descriptive**. Nothing was tested out of sample.
- Data: Yahoo daily 2015-01-05 to 2026-10-05, 2,893 Nifty sessions. "rng/imp" means the day's high–low range divided by the 1-day sd implied by the previous close's India VIX (VIX/√252). Its all-days average is 1.04.
- Reproduce with `.venv/Scripts/python "research_notes/Nifty options multifactor quant strategy/macro_crossasset_checks.py"`. Output is saved next to it in `macro_crossasset_checks_output.txt`.
- **Date caveat:** RBI MPC dates for 2016–2025 and all FOMC dates were typed in from memory. The 2026 RBI dates were checked on [RBI](https://www.rbi.org.in/Scripts/Annualpolicy.aspx), and the Jul and Sep 2026 FOMC dates on [Fed](https://www.federalreserve.gov/newsevents/pressreleases/monetary20260729a.htm) / [Forbes](https://www.forbes.com/sites/simonmoore/2026/09/29/what-to-expect-from-interest-rates-for-the-rest-of-2026/). Check every date before relying on the event-day numbers.

We did not re-research the facts in `03_indian_signals_data_regulation.md` and `04_nifty_measured_facts.md`: FII flows follow returns, the India VIX premium, US → gap corr 0.47 vs US → open-to-close −0.03, gap fade, and the 50-DMA and VIX regimes. This file uses them.

---

## 1. Scheduled Indian macro events (RBI MPC, CPI/IIP/GDP, Union Budget, election results): reaction patterns, IV crush, pre-announcement drift, and what to do

### Takeaway
- **RBI days.** In our data, RBI decision days do **not** produce a larger Nifty range than India VIX already implies. VIX reliably falls on the day before and the day of the decision, so buying options *into* the event pays for volatility that then deflates. Any reaction comes from the *guidance / path* surprise, and it hits banks hardest.
- **No India pre-announcement drift.** We found no peer-reviewed test of a Lucca–Moench style drift for India. Our own test finds no stable pre-RBI drift.
- **Budget and election days are different.** Their range is about 2× (Budget) and up to 6× (2024 election result) what VIX implies, with violent reversals.
- **CPI, IIP and GDP** come out at 16:00 IST, after the close, so they only show up in the next morning's gap.

### Cited Findings
**RBI monetary policy**
- [A] Lakdawala & Sengupta build target and path monetary-policy shocks for the RBI from high-frequency financial data plus a narrative reading of RBI statements and media coverage. Markets infer the future rate path from RBI communication. **Bond and stock markets react strongly to these shocks, but the reaction differs by governor regime.** The shock database is public. Effect sizes were not retrievable in this pass. — [JMCB 57(2-3), 2025](https://onlinelibrary.wiley.com/doi/10.1111/jmcb.13144); [IGIDR WP 2021-021](https://ideas.repec.org/p/ind/igiwpp/2021-021.html)
- [B/C] Gupta, Pawar, Kumar, Borad & Seet (RBI WP 03/2024) split OIS moves on policy days into target and path factors (Sensex, Jan 2014–Jul 2022). **Equity markets respond more to the path (forward guidance) factor than to the rate surprise itself.** — [ResearchGate](https://www.researchgate.net/publication/380127245_Equity_Markets_and_Monetary_Policy_Surprises_RBI_Working_Paper); [Republic summary](https://www.republicworld.com/business/rbi-analysis-equity-markets-driven-more-by-future-policy-expectations)
- [A, older sample] Prabu, Bhattacharyya & Ray built Indian policy shocks from derivatives data and used tight intraday windows. Main results:
  - The market responds to **unscheduled and unexpected scheduled** announcements. The expected part of scheduled announcements is already priced.
  - The monetary-policy surprise matters more than other macro surprises.
  - **Banking/financial stocks react significantly.** IT, FMCG, pharma, metal, media, energy and utilities do not.
  - Which paper reports which number could not be confirmed. — [Is the stock market impervious… (IREF 2016)](https://www.researchgate.net/publication/308801385_Is_the_Stock_Market_impervious_to_Monetary_Policy_Announcements_Evidence_from_Emerging_India); [Does the devil lie in the detail?](https://www.researchgate.net/publication/339496713_Impact_of_monetary_policy_on_the_Indian_stock_market_Does_the_devil_lie_in_the_detail); [J. Quant. Econ. 2019](https://link.springer.com/article/10.1007/s40953-019-00158-y)
- [A/B] Sahu, Debata & Sachdeva (smooth-transition VAR, Nifty 50, Jan 2003–Dec 2023): **contractionary policy raises illiquidity and lowers returns only when economic-policy uncertainty is high.** The effect is minimal when uncertainty is low. 2026 is a high-uncertainty regime. — [Int. Rev. Finance 25(2), 2025](https://onlinelibrary.wiley.com/doi/10.1111/irfi.70016)
- [C] One low-tier 2026 paper reports that over 72 RBI events Nifty rose 45 times (62.5%), with a mean of +0.21%. It also reports a stronger reaction to unexpected tightening than to easing. Not peer-review quality. — [IJNTI 2026](https://www.rjpn.org/ijnti/papers/IJNTI2605086.pdf)
- [C] Anecdotes:
  - Oct 2023 decision day: Sensex and Nifty both about +0.55%.
  - Dec 2024: Bank Nifty recovered 600 points from its intraday low after the decision. — [Torus Digital](https://www.torusdigital.com/toruscope/budget/market-reaction-to-rbis-monetary-policy-announcements-a-historical-perspective/)
  - 5 Aug 2026: RBI held repo at 5.25%, India VIX slipped to about 12 and indices closed higher. — [HDFC Sky](https://hdfcsky.com/news/india-vix-slips-after-rbi-holds-repo-rate-benchmark-indices-end-higher-august-5-2026)

**Own test: 57 scheduled MPC decision days, Oct 2016–Aug 2026** [OWN; dates partly from memory]

| Window | Mean close-to-close | Mean gap | Mean open-to-close | rng/imp | India VIX change |
|---|---|---|---|---|---|
| Day −1 | +0.19% (t vs all days 1.46, n.s.) | +0.16% | +0.04% | 1.05 | **−1.66% (t −2.46)** |
| Day 0 (decision) | +0.16% (n.s.) | +0.22% (t 1.56) | −0.06% | **1.02 (no excess range)** | **−1.95% (t −3.81)** |
| Day +1 | +0.04% | +0.08% | −0.04% | **0.94 (t −2.16, quieter)** | −0.03% |
| Day 0, 2016–19 (N=20) | −0.27% | +0.16% | **−0.43%, up only 20%** | 1.08 | −0.97% |
| Day 0, 2020–26 (N=37) | **+0.39% (t 2.35)** | +0.25% | +0.15% (t 1.94) | 0.99 | −2.48% |

- The direction on decision day flips sign between sub-periods, so there is no stable drift (OWN-F).
- The VIX decline is consistent in both periods (OWN-R).

**India VIX and other scheduled macro releases**
- [A] Shaikh & Padhi: India VIX **rises before scheduled announcements and falls once they are out**. The announcements studied were RBI policy, CPI, WPI, IIP, employment and GDP.
  - VIX falls significantly after GDP news.
  - VIX rises on monthly WPI inflation releases.
  - The joint effect of policy, IIP, employment and GDP announcements is significantly negative for VIX.
  - Older sample, from the early years of India VIX. — [SAGE 2013](https://journals.sagepub.com/doi/abs/10.1177/0973801013500168)
- [C] Release times:
  - **CPI: the 12th of each month at 16:00 IST** (moved from 17:30). — [Business Standard](https://www.business-standard.com/amp/industry/news/mospi-announces-advancing-of-release-time-of-iip-cpi-data-to-4-pm-124110501248_1.html)
  - **IIP: the 28th of each month at 16:00** since Apr 2025 (previously the 12th). — [PIB](https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=2122427)
  - **GDP: 16:00.** — [Business Standard](https://www.business-standard.com/economy/news/india-to-release-gdp-data-90-minutes-earlier-at-4-pm-to-align-with-markets-124110800833_1.html)
  - Q2 FY27 GDP is scheduled for 30 Nov 2026, per the MoSPI release schedule as summarised in search results. — [MoSPI Annual Report 2025-26](https://www.mospi.gov.in/uploads/publications_reports/publications_reports1780639521826_07b8c57c-dff9-4c75-a7fb-d28c10dd1c75_MoSPI_Annual_Report_English_2025-26.pdf)

**Union Budget**
- [OWN-R direction of effect, N=10] On Budget days found in the Yahoo data (2016–2025; some weekend sessions missing):

  | | Budget days | All days |
  |---|---|---|
  | Mean \|close-to-close\| | 1.09% | 0.69% |
  | Mean high–low range | **2.46%** | 1.09% |
  | rng/imp | **2.10** | 1.04 |
  | India VIX change on the day | **−9.3%** | — |

  - Biggest range: 2021 (4.90%, Nifty +4.74%).
  - Range above 2.1× implied: 2016, 2017, 2018, 2023 and Jul 2024.
  - Interim Budget 2024 was quiet (0.79× implied).
  - Ranges are much bigger than the net close-to-close moves, so expect whipsaws.
- [C/B] Event studies find increased volatility around Budget day and sector abnormal returns (auto, FMCG, IT), with the market broadly efficient. Low-tier journals plus one preprint. — [arXiv 2502.15787](https://arxiv.org/abs/2502.15787); [IJIRT](https://ijirt.org/publishedpaper/IJIRT174710_PAPER.pdf); [IJRESM](https://journal.ijresm.com/index.php/ijresm/article/view/3447)

**General-election results**
- [OWN, N=2 elections; C sources]
  - **4 Jun 2024 (results day):** Nifty −5.93% close-to-close, range 8.19% = **6.2× VIX-implied**, India VIX +27.75%.
  - 5 Jun 2024: Nifty +3.36%, VIX **−29%**.
  - Exit-poll Monday 3 Jun 2024: +3.25%.
  - 2019 results day (23 May): range 3.58% (2.1× implied), VIX −30%.
  - Sources: VIX jumped 27.7% to 26.74 on 4 Jun 2024 — [Business Today](https://www.businesstoday.in/markets/market-commentary/story/election-results-2024-india-vix-jumps-india-alliance-exceeds-expectations-432101-2024-06-04); VIX briefly crossed 25 before the result and collapsed to about 12 afterwards — [HDFC Sky](https://hdfcsky.com/blogs/market-wtf-by-sky/the-vix-spike-nobody-saw-coming)

**Pre-announcement drift (Lucca–Moench)**
- [B] Lucca & Moench: from 1994 to 2011 the S&P 500 rose **49 bp on average in the 24 hours before scheduled FOMC announcements**, about 80% of annual realised excess returns. Other major stock markets showed similar pre-FOMC returns. — [NY Fed SR512](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr512.html)
- [B] Kurov, Wolfe & Gilbert: **the pre-FOMC drift essentially disappeared after 2015**, with or without press conferences (sample extended to Dec 2019). — [Finance Research Letters 40, 2021](https://www.sciencedirect.com/science/article/pii/S1544612320315956)
- [C] A student analysis of MSCI India (1994–Sep 2022) found visually upward drift but **regression coefficients not significant** at 10%. — [BSIC](https://bsic.it/the-pre-fomc-drift-in-emerging-markets/)
- [OWN-F] No India-specific peer-reviewed pre-RBI drift study was found. Our own test is the table above: day −1 +0.19% and the day-0 gap +0.22%, both positive but not significant.

**2026 context: RBI decision on 7 Oct 2026** [C]
- The MPC meets 5–7 Oct. Consensus is a **25 bp hike to 5.50%**; 8 of 10 economists in a Business Standard poll expect a hike.
- The case for a hike: CPI 4.82%, Brent above $100, and the rupee beyond 96 per dollar, heading towards 97.
- Sources: [HDFC Sky](https://hdfcsky.com/news/rbis-panel-starts-monetary-policy-deliberations-0-25-bps-rate-hike-likely); [Goodreturns](https://www.goodreturns.in/news/rbi-mpc-meeting-2026-rate-hike-looms-on-october-7-can-inflation-risks-trigger-75-bps-hike-in-fy27-1539373.html); [Business Standard](https://www.business-standard.com/amp/finance/news/rbi-mpc-october-2026-meeting-when-and-where-to-watch-rate-decision-live-126100600090_1.html)
- India VIX rose 1.73% on 5 Oct ahead of the meeting. — [HDFC Sky](https://hdfcsky.com/news/india-vix-rises-1-73percent-as-rbi-policy-meeting-and-global-risks-lift-volatility-october-5-2026)

### Inferences
- **RBI day rule.**
  - A 25 bp hike is consensus, so the *target* surprise will be small. The tradable information on 7 Oct is the **path signal**: guidance on further hikes, a stance change, FX or liquidity measures. Evidence says equities react to the path factor, with banks reacting most.
  - Rule: no new option buys from 09:15 until about 30–45 minutes after the decision (the 10:00 IST timing is unverified in this pass). Then trade the post-decision direction at normal size.
  - Do not carry long options from day −1 into the decision. India VIX falls about 1.7–2% per day across the event, and weekly ATM IV probably falls more (unmeasured).
- **The expected range on RBI days should NOT be inflated.** VIX already prices them. If anything, cut the target on day +1 (0.94× implied).
- **Budget day rule.** Stand aside until the speech is over. Then allow trades at **half size, with an expected range of about 2× the VIX-implied sd** and wide stops, because ranges are big and reversals common.
  - The fall in VIX on the day means pre-bought straddles lose vega even though realised range is large. For buyers this works out only if the entry comes *after* the morning IV crush.
- **Election-result day:** full stand-aside. The next day: half size, and expect VIX to collapse, which hurts long premium.
- **CPI, IIP and GDP need no intraday rule.** They land after the close and are absorbed into the next gap. The pre-market card should flag the surprise against consensus, and only as context for the gap.

### Gaps
- Effect sizes per unit of RBI shock (Nifty % per 25 bp target or path surprise) could not be extracted. The JMCB tables, the RBI WP PDF and the IGIDR PDF were paywalled or unreachable.
- The exact RBI announcement time across years (it moved from afternoon to morning at some point) was not verified. It affects how day-0 open-to-close should be read.
- No study measures **weekly-option ATM IV crush** around RBI or Budget for Nifty. One practitioner blog claims a 30–50% IV collapse, but we couldn't trace it to data, so it is excluded. Measure it from our own option-chain snapshots.
- India CPI or GDP *surprise* (actual minus consensus) effects on the next Nifty gap: no India study found. Consensus history is not freely available in clean form.
- RBI 2016–2025 dates were typed from memory. Verify them against the [Lakdawala–Sengupta database](https://ideas.repec.org/p/ind/igiwpp/2021-021.html) or the RBI archive before using the table.

---

## 2. US and global event spillovers (FOMC, US CPI, NFP) and intraday lead-lag from US futures, Asian markets, USD/INR, Brent, DXY and US yields

### Takeaway
US news enters Nifty almost entirely through the **opening gap**.
- After the open, the previous US session, Brent and USD/INR have essentially **zero** predictive power for the Nifty open-to-close move. This holds for all years and for 2026.
- FOMC nights do not make the next Indian session unusually volatile. The Indian session *on* FOMC day is quieter than VIX implies.
- The size of the overnight shock **does** predict a larger intraday range than VIX implies. So global cues should drive the **volatility expectation and position size, not direction**.
- In 2026 the oil→Nifty sign has flipped negative. Oil-up days now mean gap-down.
- We found no published intraday study of E-mini or Asian-index lead-lag into Nifty.

### Cited Findings
- [B, India not significant] Hausman & Wongswan (49 countries, FOMC Feb 1994–Mar 2005):
  - On average, a surprise 25 bp Fed cut lifts foreign equity indexes by about 1%. Equities respond mainly to the *target* surprise. FX and long rates respond mainly to the *path* surprise.
  - Responses are larger where exchange rates are less flexible.
  - **India's equity coefficient: target −1.190 (p = 0.689), path 0.270 (p = 0.891), adjusted R² −0.015. Not significant.**
  - Asian markets are closed at announcement time, so the response is measured the next day. — [Fed IFDP 886](https://www.federalreserve.gov/pubs/ifdp/2006/886/ifdp886.pdf); [JIMF 30(3), 2011](https://econpapers.repec.org/article/eeejimfin/v_3a30_3ay_3a2011_3ai_3a3_3ap_3a547-571.htm)
- [OWN-R, 88–93 FOMC meetings 2015–Sep 2026]
  - **Indian session on FOMC day (before the announcement):** close-to-close +0.13% (n.s.). **rng/imp 0.93 vs 1.04 (t −2.38). |close-to-close|/imp 0.53 vs 0.65 (t −2.82): a calm-before-the-event pattern.**
  - **Next Indian session:** gap +0.10% (same as all days), open-to-close −0.13% (n.s.), rng/imp 1.06 (n.s.), **India VIX −1.5% (t −3.06)**.
- [OWN-R] Prior US session vs Nifty, 2015–2026:
  - corr(US prior session, Nifty gap) = 0.475. By year it ranges from 0.15 (2019) to 0.69 (2022); 2026 = 0.46.
  - corr with open-to-close = −0.03 overall; 2026 = −0.006.
  - OLS: gap = 0.296 × US move (t 29.6) − 0.072 × Nifty's own prior day (t −6.8). R² 0.24. In 2026 the US beta is 0.39 and R² 0.24.
  - Open-to-close regression on US, Brent, USD/INR and prior Nifty: **R² 0.002 (2015–26) and 0.003 (2026)**.
- [OWN-R] No follow-through after big US moves:

  | Prior US move | N | Mean Nifty gap | P(open-to-close > 0) | rng/imp |
  |---|---|---|---|---|
  | ≤ −1.5% | 179 | −0.68% | 49.2% | 1.22 |
  | ≥ +1.5% | 151 | +0.68% | 48.3% | 0.97 |

  - Large US *down* days lead to a bigger Indian range than VIX implies. Large up days don't.
- [OWN-R] **Overnight shock size predicts the intraday range beyond the previous close's VIX:**

  | Shock | N | rng/imp |
  |---|---|---|
  | \|US prev\| > 2.5% | 92 | **1.25** |
  | \|US prev\| < 0.5% | 1,462 | 1.02 |
  | \|Brent prev\| > 5% | 148 | **1.21** |
  | \|Brent prev\| < 1% | — | 1.03 |
  | \|Nifty gap\| 1–2% | 139 | **1.13** |
  | \|Nifty gap\| > 2% | 48 | **1.71** |
  | \|Nifty gap\| < 0.2% | — | 1.01 |

  (rng/imp by VIX bucket alone stays flat at 1.01–1.07, so VIX is well calibrated *unconditionally*.)
- [OWN-R for overall, OWN-F for 2026] **Brent:**
  - corr(prior-day Brent, Nifty gap): +0.15 (2015–19), +0.12 (2020–25), **−0.27 (2026 YTD)**.
  - Same-day corr(Nifty close-to-close, Brent): **−0.28 in 2026** vs +0.08 overall.
  - 2026 days after Brent ≥ +2% (N=56): gap −0.35%, close-to-close −0.43%, open-to-close −0.08%.
  - 2026 days after Brent ≤ −2% (N=40): gap +0.28%, close-to-close +0.16%.
  - Brent never predicts open-to-close (corr about 0 in every period).
  - Before 2026, oil and Nifty co-moved as "global risk-on". In the 2026 Hormuz shock, oil is a pure India-negative supply shock.
- [OWN-R] **USD/INR:**
  - The prior day's change has no link to the gap (corr 0.02) or to open-to-close (−0.002).
  - Same-day (coincident) corr with Nifty close-to-close is −0.13 overall and **−0.23 in 2026**. Rupee weakness co-moves with Nifty falls but does not lead them at daily frequency.
- [B/C] India stock–FX feedback: Vadivel finds bidirectional feedback between exchange-rate volatility and stock-price volatility (daily, Feb 2015–Aug 2019). — [J. Public Affairs 2020](https://onlinelibrary.wiley.com/doi/10.1002/pa.2144)
- [B, old] Asian markets:
  - Mukherjee & Mishra (Nov 1997–Apr 2008, daily open and close prices of India plus 12 Asian markets): **contemporaneous intraday return spillovers between India and Asian markets are positive, significant and bidirectional.**
  - Significant information flows into India from Hong Kong, Korea, Singapore and Thailand.
  - Volatility flows from Hong Kong to India. — [MPRA 12788 / RIBF](https://mpra.ub.uni-muenchen.de/12788/1/MPRA_paper_12788.pdf)
  - The effect is contemporaneous, not a lead usable for prediction.
- [B, non-India] Oil and equities across sessions:
  - Overnight oil-futures realised volatility, especially from negative returns, improves out-of-sample forecasts of S&P 500 realised volatility. — [Ma et al., J. Forecasting 2022](https://onlinelibrary.wiley.com/doi/10.1002/for.2903)
  - Oil–equity volatility spillovers differ between intraday and overnight sessions: US equities dominate intraday, while European and Asian equities dominate overnight. — [Hao et al., JFM 2023](https://onlinelibrary.wiley.com/doi/10.1002/fut.22410)
- [C] 2026 global context:
  - **Fed hiked 25 bp to 3.75–4.00% on 16 Sep 2026**, its first hike since 2023. Markets price further hikes on **28 Oct** and in December. — [Forbes](https://www.forbes.com/sites/simonmoore/2026/09/29/what-to-expect-from-interest-rates-for-the-rest-of-2026/); [FedRateCalc](https://fedratecalc.com/fomc-meeting-schedule/october-2026/)
  - US 10-year peaked above 5.34% (highest since 2002) and was 5.26% on 5 Oct 2026. — [Trading Economics](https://tradingeconomics.com/united-states/government-bond-yield); [CNBC](https://www.cnbc.com/2026/09/26/10-year-treasury-yield-is-at-its-highest-in-19-years-how-we-got-here.html)
  - The S&P 500 was 7,772 on 5 Oct 2026, near a record (own data), while Nifty is down about 14% in 2026. The two markets have decoupled.

### Inferences
- **Do not use US/Brent/INR moves as an intraday direction feature.** Use them as:
  1. inputs for the *expected gap*, which GIFT Nifty already shows by 09:00;
  2. **range multipliers**: scale the VIX-implied sd by about 1.1–1.25× after big overnight shocks, and by about 1.7× when the gap exceeds 2%;
  3. **stress-regime inputs** for position sizing.
- **The 2026 oil-sign flip matters for the pre-market read.** A Brent spike after the Indian close now means a gap-down. Revisit this when Hormuz normalises; the correlation reverts in risk-on regimes.
- **FOMC (next one 28 Oct 2026, 14:00 ET = 23:30 IST):** no stand-aside needed for the Indian sessions around it. On the FOMC-day session, lower range targets, since realised range runs about 10% below implied. The next morning is an ordinary gap day.
- **US CPI / NFP (08:30 ET = 18:00 IST while US daylight time lasts, 19:00 IST after the clocks change):** they land after the Indian close. Treat them like FOMC, as next-gap events, with no intraday rule.
- **Intraday ES/NQ and USD/INR moves during Indian hours** should be monitored as *shock detectors*. For example, ES down more than 1% inside the Indian session or USD/INR up more than 0.5% intraday would be a news event. That would trigger "tighten stops / no new longs", not a directional signal. This is untested.

### Gaps
- **We found no published intraday (1–5 minute) lead-lag study of E-mini S&P/Nasdaq futures, Nikkei, Hang Seng, KOSPI, USD/INR, DXY or US yields leading Nifty** during Indian hours. This is the biggest research gap. It needs our own 1-minute test: regress the Nifty futures 5-minute return on lagged 5-minute ES, USD/INR and Brent returns, by session hour.
- US CPI/NFP *surprise* effects on the next Nifty session: no India-specific study found. Hausman–Wongswan covers FOMC only, and in an old sample.
- DXY and US 10-year yields: none of this project's data files contains them, so we could not measure them. The FRED series DGS10 and DTWEXBGS are free. Measure corr(Δ US 10-year, Nifty gap) and its 2026 behaviour.
- The Kishor & Marfatia (JIFMIM 2013) result on time-varying foreign stock responses to Fed surprises could not be checked for whether India was included.

---

## 3. GIFT Nifty (NSE IX) price discovery vs Nifty spot, and whether the overnight move is fully priced by 09:15

### Takeaway
- Offshore Nifty futures (SGX, now GIFT) led onshore futures and spot in price discovery before the 2023 move to GIFT City.
- Today GIFT Nifty trades about 21 hours a day at record volumes. Our data says that once the gap is set, global overnight information has **no residual intraday predictive value**.
- What remains are two small, mostly in-sample patterns: a mild **gap fade** (from notes 04) and a **post-holiday fade** (Section 7).

### Cited Findings
- [A, pre-GIFT sample] Sundararajan & Balasubramanian (5-minute data; Hasbrouck information share, modified IS and Gonzalo–Granger component share):
  - **Offshore SGX Nifty futures "consistently ranked first" in price discovery**, followed by NSE Nifty futures, then spot.
  - Causality and volatility transmission run one way, from futures to spot. Between NSE and SGX futures they run both ways.
  - The exact IS percentages were not visible in the abstract. — [Int. J. Emerging Markets 20(5)](https://www.emerald.com/ijoem/article-abstract/20/5/1888/1246829/Intraday-price-discovery-and-volatility?redirectedFrom=fulltext)
- [B] Khan et al. (1-minute Nifty spot and futures, COVID period):
  - Futures dominate price discovery (Hasbrouck IS; the Gonzalo–Granger permanent factor is futures only). Spot restores disequilibrium.
  - Two-way volatility spillovers.
  - They cite earlier work: spot led before 2014 and futures lead after 2014. — [J. Mathematics 2022](https://onlinelibrary.wiley.com/doi/10.1155/2022/2164974)
- [C] GIFT Nifty hours:
  - First session 06:30 to about 15:40 IST; second session ending 02:45 IST; about 21 hours a day in total.
  - The source gives a 16:05 start for the evening session. Some brokers list a different time; check against NSE IX. — [AlgoTest](https://algotest.in/blog/understanding-gift-nifty-trading-timings-and-their-impact-on-your-trades/); [MNCL](https://www.mnclgroup.com/gift-nifty-trading-hours)
- [C] Record volumes:
  - 24 Sep 2026: 457,999 contracts, $21.18 bn.
  - **25 Sep 2026: 512,023 contracts, $23.67 bn.**
  - Full GIFT operations began 3 Jul 2023. — [NiftyTrader](https://www.niftytrader.in/markets/gift-nifty-trading-surges-to-record/)
- [D] A claim that GIFT Nifty contributes "over 60%" of Nifty price discovery and leads in 65% of sessions is attributed vaguely to "research" and "NSE IX analysis", with no method or period. Treat it as unverified. — [Open Magazine](https://openthemagazine.com/business/gift-nifty-trading-hours-impact-and-role-in-nifty-price-discovery-explained)
- [B, non-India] Extended-hours futures trading helps predict opening spot prices (TAIFEX index and single-stock futures). — [Wang, Chen & Wang, J. Forecasting 2018](https://onlinelibrary.wiley.com/doi/10.1002/for.2554)
- [A] Nifty option returns show a day/night asymmetry: positive overnight returns for short-option strategies and negative intraday returns. The variance risk premium is mainly a reward for overnight risk. — [Bhat, Pandey & Rao, JFM 2024](https://onlinelibrary.wiley.com/doi/10.1002/fut.22512)
- [OWN-R] Once the gap is known, prior US, Brent and INR moves explain 0.2% of open-to-close variance (Section 2). The gap-size → range relation is in Section 2.

### Inferences
- **By 09:15, overnight global news is priced into the level, but not into the volatility.** The pre-market card should read the GIFT Nifty implied gap at about 09:00 and output:
  1. the gap (context);
  2. the expected range multiplier, from |gap| buckets;
  3. a weak fade prior when |gap| > 0.5% (from notes 04: after gap-downs below −0.5%, P(close > open) is 53.8% and the mean open-to-close is +0.11%).
- GIFT Nifty's second session, ending 02:45 IST, already contains the US cash session. **The US close is therefore redundant once GIFT Nifty is read at 09:00.** Use the US close only as a cross-check and for data gaps.
- Option buyers should note the Bhat et al. day/night asymmetry. Long premium bought at 09:15 and held intraday sits on the "cheap" side of the asymmetry, but the overnight premium is lost if held overnight.

### Gaps
- **No published information-share study uses GIFT Nifty (NSE IX) data after July 2023.** All academic IS evidence is from the SGX era.
- No study (and no data of ours) checks whether the 06:30–09:00 GIFT drift continues or reverses in the 09:15–09:45 Nifty move. This can be tested once we have 1-minute GIFT and Nifty futures data.

---

## 4. Earnings season: heavyweight results days, aggregate earnings surprise and revision breadth as index predictors

### Takeaway
- **We found no India-specific evidence** that heavyweight results days move the Nifty's *direction* predictably, or that aggregate earnings surprises or revision breadth predict the index at a weekly horizon.
- The international evidence conflicts. The US aggregate earnings–return relation is negative, while most non-US markets show a positive one.
- Treat results as (a) **next-morning gap and range events** for the reporting stock's weight, and (b) a slow monthly context variable (consensus EPS revisions). Do not use them as a daily direction input.

### Cited Findings
- [B, US] Kothari, Lewellen & Warner: aggregate earnings surprises are **negatively** related to contemporaneous market returns. Stocks rose 6.5% in quarters with negative earnings growth vs 1.9% otherwise, which they attribute to discount-rate effects. — [JFE 2006](https://www.sciencedirect.com/science/article/abs/pii/S0304405X05001182)
- [B, international] He & Hu: in **28 non-US markets, aggregate earnings changes are positively associated with contemporaneous returns**. The negative US relation is unique to the US, and the positive relation weakens with greater transparency. India's inclusion was not confirmed. — [JFQA 2014](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/aggregate-earnings-and-market-returns-international-evidence/0E3ED9FC76BBE11A322F809404603A21)
- [B, US] Savor & Wilson:
  - Firms scheduled to report earn a **9.9% annualised abnormal return**.
  - A portfolio of announcers **predicts aggregate earnings growth**, while the market as a whole does not.
  - Early announcers earn more, consistent with early reporters carrying market-wide information. — [J. Finance 2016](https://onlinelibrary.wiley.com/doi/10.1111/jofi.12361)
- [C] 2026 revision breadth:
  - **Nifty FY27 consensus EPS has fallen about 9%, from 1,357 a year ago to 1,235.** — [5paisa](https://www.5paisa.com/news/nifty-fy27-earnings-estimates-trimmed-9-despite-persistent-downgrade-trend)
  - In May 2026, 31 of 50 Nifty companies saw FY27 EPS cuts. — [Meyka](https://meyka.com/blog/nifty-50-eps-cuts-cipla-lt-adani-enterprises-adani-ports-among-31-downgraded-stocks-in-fy27-forecast-2606/)
  - BofA cut its FY27 Nifty earnings growth forecast to 8.5% from 14%. — [Multibagg](https://www.multibagg.ai/market-pulse/articles/bofa-cuts-nifty-fy27-earnings-cmpxur3fm1tfunz0jxf2o46r7)
- [C] Q2 FY27 results calendar: **TCS on Thu 8 Oct 2026** (also Sensex expiry day), **HCLTech 12 Oct, Infosys 23 Oct**. — [TradingView/Moody's](https://www.tradingview.com/news/moodys:afb6923d174ee:0-it-q2-results-2026-date-and-time-tcs-infosys-hcl-tech-fy-2027-earnings-announcement-schedule/); [Kotak Neo](https://www.kotakneo.com/news/stocks/it-q2-earnings-fy-2026-27-tcs-hcltech-infosys-results-dates/)
- [C, sources conflict] Nifty weights in 2026:
  - One aggregator lists, as of 1 Oct 2026: Reliance 8.84%, HDFC Bank 6.21%, Bharti 6.09%, ICICI 5.25%, Infosys 2.35%. — [Bajaj Finserv](https://www.bajajfinserv.in/nifty-weightage); [Univest](https://univest.in/blogs/nifty-50-stock-list)
  - Others put HDFC Bank at 11.8% (30 Jun 2026) or 10.9% (Apr 2026).
  - ICICI Bank reportedly overtook Reliance at one point. — [Angel One](https://www.angelone.in/news/stocks/icici-bank-overtakes-reliance-industries-in-nifty-50-weightage-on-higher-free-float-market-capitalisation)
  - **Use the NSE monthly index factsheet, not aggregators.**

### Inferences
- **Heavyweight results day = an index gap and range adjustment, not a signal.**
  - Expected index contribution ≈ stock weight × the stock's typical results-day move. For example, a 10% weight × 4% move ≈ 0.4% of Nifty. This is arithmetic, not tested evidence.
  - Flag pre-market when a stock with weight ≥ 5% reported after the previous close. Expect a larger gap and range. For bank results, also expect a Bank Nifty spill-over.
- **TCS on 8 Oct coincides with the Sensex expiry and the day after RBI.** TCS reports after market hours, so its effect is the 9 Oct gap. On 8 Oct itself the drivers are the RBI digestion and the Sensex expiry.
- **Revision breadth** (share of Nifty stocks with upgrades minus downgrades, monthly) is a candidate *monthly* regime variable for directional size tilt. It has no daily role. The current reading (FY27 EPS −9%, breadth deeply negative) is consistent with the 2026 drawdown and is not independent information.

### Gaps
- No India study on index-level return or volatility on heavyweight results days, and none on aggregate earnings surprise predicting Nifty weekly returns.
- No free historical consensus-EPS revision series for Nifty. Brokerage notes are point-in-time only.
- Our own test (results-day stock move × weight vs the Nifty gap) needs a results-date history from NSE corporate announcements.

---

## 5. Flows (FII/DII, SIP, FII futures positioning) and monthly flow patterns (turn of month, expiry week, quarter-end, MSCI/FTSE rebalancing)

### Takeaway
- **Daily FII cash flows are coincident or lagging, not predictive** (established in notes 03).
- In 2026 the domestic SIP/DII bid has absorbed record FPI selling. This moderates drawdowns but does not give a daily direction signal.
- Turn-of-month strength exists in 2020–26 but *reversed* in 2015–19, so it is unstable.
- **Index-rebalancing days concentrate moves into the close**, which is now the closing auction. That is a risk flag, not an edge.

### Cited Findings
- [B, negative for prediction; established] FII flows follow Nifty returns and do not lead them. — see `03_indian_signals_data_regulation.md` (Patnaik, Shah & Singh 2013; Stigler et al. 2010)
- [C] 2026 FPI selling:
  - March 2026 was a monthly record: ₹1.14–1.18 lakh crore. — [Outlook Money](https://www.outlookmoney.com/invest/fpi-selling-dump-record-rs-1-14-lakh-crore-of-indian-equities-in-march-2026-amid-us-iran-war); [The Wire](https://m.thewire.in/article/banking/fpi-outflows-highest-in-34-years-march-sees-rs-1-18-trillion-sell-off-in-wake-of-west-asia-crisis)
  - About ₹2.2 lakh crore withdrawn by early June 2026.
  - FY26 net outflows were the highest in 34 years.
  - The Hormuz closure from late Feb 2026 widened the current account deficit and pressured the rupee. — [ZiroMarket](https://www.ziromarket.com/blog/fpi-outflows-india-2026-record)
- [C] Domestic flows:
  - **Monthly SIP inflows were about ₹32,000 crore** (AMFI, Mar 2026).
  - Jan 2026: FII −₹35,962 crore vs DII +₹71,624 crore, with Nifty −3.0%. — [INDmoney](https://www.indmoney.com/blog/mutual-funds/nifty-50-2026-market-recovery)
  - Claims that DIIs absorbed about 90% of foreign selling come from social posts (D). — [Wright Research](https://www.wrightresearch.in/blog/fii-vs-dii-india-2026/)
- [C, established] FII index-futures positioning: a record **333-session net-short streak** (May 2025–Sep 2026). A flip back to net long has preceded 30-day gains in most cases (small sample). — `03_indian_signals_data_regulation.md` (Marketcalls)
- [A per the search abstract; full text unavailable] *"The turn of the month effect in India: A case of large institutional trading pattern as a source of higher liquidity"*: **FIIs and mutual funds raise buying volumes on the last two days of the month**, linking TOM returns to institutional liquidity. — [Int. Rev. Financial Analysis 2013](https://www.sciencedirect.com/science/article/abs/pii/S1057521913000203)
- [C] A 2026 low-tier study finds significantly positive first-trading-day-of-month returns for Nifty and Sensex, and no consistent end-of-month effect. — [IJMEC](https://ijmec.org.in/index.php/ijmec/article/view/143); also [Sathish et al., SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3672953)
- [OWN-F] Turn of month (TOM = last trading day + first 3 trading days):

  | Period | TOM mean | Non-TOM mean | Note |
  |---|---|---|---|
  | **2020–26** | **+0.168%/day (t 2.40)** | +0.013% | **84% of total log return came on 19% of days** |
  | **2015–19** | **−0.017%** | +0.047% | TOM share of return −13% |
  | All | +0.090% (t 1.90) | — | first day of month +0.167% (t 1.70) |

- [A, established] Expiry-day volatility rises in the last half hour of expiry day, when the settlement price is formed. — [Agarwalla & Pandey, JFM 2013](https://onlinelibrary.wiley.com/doi/10.1002/fut.21632). Expiry-weekday effects since the Sep 2025 swap are in Section 7.
- [C] MSCI rebalancing:
  - In the two rounds before Aug 2026, Nifty fell about 0.5–1% near the close on MSCI days. The Aug 2026 rebalance was the first big test of the **closing auction session**. — [Zerodha Varsity on X](https://x.com/ZerodhaVarsity/status/2094279911687209469); [The Hawk](https://www.thehawk.in/news/economy-and-business/msci-rebalancing-to-test-new-closing-auction-system-stocks-may-see-flows)
  - One rebalance day reportedly brought a 1.5% fall, $1 bn of passive outflows and record cash volume of ₹2.87 trillion. — [Whalesbook](https://www.whalesbook.com/news/English/economy/MSCI-Rebalancing-Triggers-Record-indian-rupee287-Trillion-India-Selloff/6a199c7e49974139aecf62bd)
  - In another rebalance, Nifty gained about 30 points inside the closing auction but still closed −0.39%, and Bank Nifty swung from −0.17% to +0.92%. — [Multibagg](https://www.multibagg.ai/market-pulse/articles/msci-rebalancing-nifty-volatility-cmte6cwv0000s2fpg6k2px725)

### Inferences
- Flows belong in the **regime layer**, as slow context:
  - the FII futures long ratio and flips (days to weeks);
  - FII minus DII net cash as a "who is absorbing" gauge;
  - SIP run-rate as a structural floor.
  - None of them belongs in the daily direction layer.
- **TOM:** don't use it for direction. It is unstable across sub-periods and may be a 2020–26 artefact of SIP-date flows. Re-test yearly. At most, treat the first trading day as "don't fight strength".
- **Index-rebalance and quarterly-review effective days (MSCI, FTSE, Nifty semi-annual):** hard rule of no open option positions after about 15:00, since the closing auction concentrates passive flows. The pre-market card should carry the dates.

### Gaps
- Quarter-end window dressing in Nifty: no India evidence found.
- FTSE and Nifty semi-annual rebalance-day effects: no data found.
- No peer-reviewed test of whether DII or SIP flows *predict* next-day Nifty returns. Flow data arrives in the evening (provisional), so it could only feed the next morning's card. An own test would be cheap with NSE's daily FII/DII archive.

---

## 6. Valuation and fundamental regime (Nifty PE, earnings yield minus bond yield, India 10-year G-sec, credit spreads)

### Takeaway
- Valuation predicts **multi-year** return distributions, and only weakly. Out of sample it is fragile even in the US.
- We found **no India evidence that valuation shifts next-day or intraday return or volatility distributions.**
- For a daily intraday system it is at most a slow, annual-scale risk-budget input, and should probably be ignored.
- The bond-yield level matters more through the *policy-rate path* channel (Section 1) than through valuation.

### Cited Findings
- [B, US] Most classic equity-premium predictors (valuation ratios, yield spreads, etc.) **fail out of sample** (Goyal & Welch). — [RFS 2008](https://doi.org/10.1093/rfs/hhm014)
- [B, US] The stock–bond yield gap (the "Fed model") forecasts excess returns at short and long horizons, with reasonable out-of-sample predictability and higher Sharpe ratios. — [Maio, Review of Finance 17(4), 2013](https://academic.oup.com/rof/article-abstract/17/4/1489/1570701)
- [C, India] Valuation-zone studies:
  - With Nifty at 20–22× trailing PE, the next year averaged +3% (median +1%), positive 66% of the time over two decades. — [Business Standard](https://www.business-standard.com/article/markets/valuations-in-high-optimism-zone-as-nifty-forward-p-e-tops-20x-icici-sec-122120600854_1.html)
  - PE below 12 gave about 39% average 3-year returns. — [Stable Investor](https://stableinvestor.com/2019/01/nifty-pe-ratio-returns-analysis-updated.html)
  - Above 24–26× PE has historically meant below-average 3–5 year returns. — [Wright Research](https://www.wrightresearch.in/blog/nifty-pe-ratio-valuation-historical-cycles-guide/)
- [C, preprint] PE "probabilistically maps" return distributions from days to decades. PE well below 13 has historically shown zero probability of loss; PE well above 27 means unstable returns. — [arXiv 2509.00697](https://arxiv.org/abs/2509.00697)
- [C] DSP's model (backtested from 2000) uses the gap between the bond yield and Nifty's earnings yield. **In Mar 2026 the gap was about 1%, which DSP called attractive for equities.** — [DSP NETRA Apr 2026](https://www.dspim.com/latest-literature/dspnetra-april-26.pdf)
- [C] Current levels:
  - **India 10-year G-sec at 7.21%** on 1 and 5 Oct 2026, a 2.5-year high, up about 24 bp in September, driven by crude and government borrowing. — [Trading Economics](https://tradingeconomics.com/india/government-bond-yield); [Business Standard](https://www.business-standard.com/amp/markets/capital-market-news/g-sec-yields-surge-to-2-5-year-high-on-crude-spike-rupee-nears-96-126092801195_1.html)
  - Nifty trailing PE about 19.3. — [Trendlyne](https://trendlyne.com/equity/PE/NIFTY/1887/nifty-50-price-to-earning-ratios/)
- [OWN, established] Below the 50-DMA, 5-day moves are 54% larger. That is a volatility effect, not a valuation one. — notes 04

### Inferences
- A rough current reading:
  - Forward PE ≈ 22,550 / 1,235 ≈ **18.3×**, so forward earnings yield ≈ **5.5%**.
  - That is about **1.7 points below** the 7.21% 10-year G-sec.
  - The gap has widened against equities since March 2026, because yields are up and EPS has been cut.
  - This is a *multi-month* headwind, not a daily signal.
- **Recommendation:** leave valuation out of the daily score. If used at all, use it to set an *annual* cap on directional long exposure. Use the **G-sec 5-day change** (a rate-shock proxy) in the stress composite instead. Rising yields with a weak rupee and high oil is the 2026 stress mix.

### Gaps
- No India study on valuation → short-horizon volatility.
- Indian corporate credit spreads (AAA minus G-sec) are not freely available as a clean daily series. FBIL and CCIL publish some data, but there is no easy API. Not evaluated.

---

## 7. Calendar anomalies after recent structural changes (day-of-week after the Tuesday expiry shift, Monday effect, holiday effects)

### Takeaway
- The classic Monday effect is weak and inconsistent in Nifty.
- Two patterns in our data are worth implementing as **small intraday tilts**:
  1. **Post-holiday sessions gap up and then fade intraday.** This holds in both sub-periods.
  2. **Since the Sep 2025 swap, the Nifty-expiry Tuesday has had strongly negative open-to-close returns.** This one is fragile: N=54 and many tests were run.
- Old Thursday-expiry patterns no longer apply.

### Cited Findings
- [C] **From 1 Sep 2025, NSE weekly expiry (Nifty) moved from Thursday to Tuesday, and BSE (Sensex) moved to Thursday.** — [Business Standard](https://www.business-standard.com/markets/news/nse-bids-adieu-to-thursday-expiry-as-dates-swap-come-into-effect-explained-125082800635_1.html)
- [OWN-F] **Day of week since the swap (Sep 2025–Oct 2026), open-to-close:**

  | Day | N | Mean open-to-close | t | P(up) | Note |
  |---|---|---|---|---|---|
  | **Tue (Nifty expiry)** | **54** | **−0.204%** | **−2.41** | **27.8%** | binomial p = 0.006 vs the 46.7% base |
  | Thu (Sensex expiry) | 52 | −0.112% | −1.52 | 40.4% | |
  | Mon/Wed/Fri | 164 | +0.047% | 1.03 | 56.1% | |

  - Tuesday close-to-close: −0.08%, up 35.2% of the time.
- [OWN-R] **Before the swap the Thursday expiry showed no such effect.** Thursday (Nifty weekly expiry, Feb 2019–Aug 2025, N=328): open-to-close −0.065% (t −1.47), P(up) 47.0%, which is base rate.
  - Tuesday in that era (N=326): close-to-close **+0.19% (t 3.30, P(up) 57.4%)**. This was a pre-swap Tuesday strength that disappeared after the swap.
- [OWN-R] **Holidays (weekday exchange holiday between sessions, N=165 each):**
  - **Post-holiday session:** gap **+0.18% (t 2.95, positive 64.8%)**, then **open-to-close −0.22% (t −2.96, up only 42.4%)**.
  - It holds in both sub-periods: 2015–19 open-to-close −0.20% (t −2.16); 2020–26 −0.235% (t −2.10).
  - Pre-holiday close-to-close +0.087% (n.s.), up 57.6% of the time; 2020+ +0.08% (n.s.).
- [OWN-F] Monday close-to-close was −0.13% in 2020–24 (t −1.34) but up 57.9% of the time, against +0.06% in 2015–19. No consistent Monday effect.
- [B] COVID-era daily data (2005–2020) found negative Monday returns during the crisis period. — [Sahoo, J. Public Affairs 2021](https://onlinelibrary.wiley.com/doi/10.1002/pa.2621)
- [B] Day-of-week tests for emerging Asian markets, including India, over 2013–19 found weak and mixed effects. India's coefficients were not clearly significant in the visible table. — [Khan et al., IJFE 2021](https://onlinelibrary.wiley.com/doi/10.1002/ijfe.2435)
- [Established] The closing auction session has set expiry settlement since 3 Aug 2026. Volatility rises in the last half hour of expiry (Agarwalla & Pandey). — notes 03

### Inferences
- **Post-holiday rule (best calendar input):** expect a gap up, then lower the prior for intraday longs. P(close > open) is about 42–45% vs the 46.7% base, and the mean is −0.22%.
  - In practice, require one more confidence notch for call buys after a holiday, and prefer fading a post-holiday gap up if the technical setup agrees.
- **Tuesday Nifty-expiry rule:** treat it as a *hypothesis on probation*.
  - Shrink the measured −19 point deviation in P(up) by at least half. So: lower the prior for long-intraday on Tuesdays by about 5–10 points, and re-test every month.
  - Plausible mechanism: option-book hedging and pinning dynamics into the closing auction, as in the Jane Street episode in notes 03. That is a story, not evidence.
  - Thursday (Sensex expiry) shows a smaller version of the same pattern.
- **Today, Tue 6 Oct 2026, is a Nifty expiry, the day before RBI, and the session after Monday's post-holiday session.** (Fri 2 Oct was a holiday; Mon 5 Oct closed +0.10% open-to-close.) The calendar priors for today point to a weak intraday prior and falling VIX into RBI. Neither is strong.

### Gaps
- Results use Yahoo daily data, with expiry days taken from the weekday only. Holiday-shifted expiries are mislabelled.
- No published study covers post-Sep-2025 weekday effects.
- The holiday definition counts any weekday gap, so long weekends where Friday or Monday is a holiday are included. Diwali/Muhurat specifics were not separated.

---

## 8. Geopolitical risk (Caldara–Iacoviello GPR) and oil shocks: effects on Indian equities and volatility, and relevance to 2026

### Takeaway
- GPR shocks are risk-off for Indian large caps, at **monthly** horizons, with sector differences.
- Oil-price *uncertainty* hurts Indian returns asymmetrically.
- In 2026 the oil/Hormuz shock is *the* macro driver. Our data shows the oil–Nifty sign flipped negative this year.
- Use GPR and oil as **stress-regime and sizing inputs**, plus a pre-market gap-sign check. They are not intraday direction signals.

### Cited Findings
- [B for India] Caldara & Iacoviello build a news-based GPR index (from 1985). **Higher geopolitical risk lowers real activity and stock returns and moves capital flows from emerging to advanced economies.** — [AER 2022](https://www.aeaweb.org/articles?id=10.1257%2Faer.20191823)
  - Data: **daily GPR updated every Monday; monthly GPR at the start of each month** (last update 1 Oct 2026). — [matteoiacoviello.com](https://www.matteoiacoviello.com/gpr.htm)
- [A, monthly] SenGupta & Debnath (local projections, monthly Jul 1990–Feb 2025, 28 NSE indices, global, threat, act and country GPR):
  - **Large-cap benchmarks (Nifty 50–500) follow the canonical risk-off response.**
  - Microcap 250, manufacturing, tourism, media and IPO indices show resilience or delayed recovery.
  - Defence gets a short-run lift that does not last uniformly. Auto shows a mild long-run gain. — [Int. Economics & Economic Policy 23(4), 2026](https://link.springer.com/article/10.1007/s10368-026-00785-w); [SSRN 5224456](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5224456)
- [B, global] Across 32 countries and regions, GPR has a significantly positive effect on stock-market volatility. — [Finance Research Letters 2022](https://www.sciencedirect.com/science/article/abs/pii/S1544612322007966)
- [A/B] Oil and Indian stocks:
  - **Shocks to oil-price uncertainty (oil VIX) affect Indian stock returns asymmetrically. Rising oil uncertainty matters most.** — [Energy Strategy Reviews 2022](https://www.sciencedirect.com/science/article/pii/S2211467X22001961)
  - At the firm level, net oil-price increases vs decreases have asymmetric effects on energy-intensive companies. — [Int. J. Energy Sector Management](https://www.emerald.com/ijesm/article-abstract/17/4/693/116955/Is-the-effect-of-oil-price-shock-asymmetric-on-the?redirectedFrom=fulltext)
  - Sector responses to oil are asymmetric. — [Cogent Economics & Finance 2025](https://www.tandfonline.com/doi/full/10.1080/23322039.2025.2588921)
- [C, citing RBI] Macro elasticities:
  - **+10% crude ≈ +30 bp CPI and −15 bp GDP growth** (RBI MPR, Oct 2025, full pass-through).
  - **+$10/bbl oil plus gas ≈ +$20 bn current account deficit (~0.5% of GDP).** — [HDFC MF](https://www.hdfcfund.com/learn/deep-dives/tuesday-talking-point/crude-reality-understanding-risks-india)
- [C] 2026 regime:
  - Global GPR in Aug 2026: 118.2, with threats 157.5 and acts 102.4. — [MacroMicro](https://en.macromicro.me/collections/6447/geopolitical-risk)
  - In early Oct 2026, Iran was still setting conditions for reopening Hormuz. — [Benzinga](https://benzinga.com/markets/equities/26/10/62156134/stock-market-today-dow-jones-sp-500-futures-slip-as-iran-keeps-conditions-to-reopen-hormuz-strait-spcx-qcom-vst-in-focus)
  - Sensex and Nifty fell about 9.4–9.5% in the first phase of the war; the rupee hit a then-record 94.78. — [ZiroMarket](https://www.ziromarket.com/blog/fpi-outflows-india-2026-record)
- [OWN-F, 2026 YTD N=186] The 2026 oil-sign flip (Section 2): corr(prior-day Brent, gap) −0.27 and same-day corr −0.28, vs about +0.1 in earlier years. Big Brent moves (|Δ| > 5%) raise the next session's rng/imp to 1.21 across all years.
- [OWN] India VIX was only **14.77 on 5 Oct 2026** and VIX minus realised volatility is at its weakest in 2026 (notes 04). Implied vol is *not* pricing much geopolitical tail, so in this regime realised shocks have often exceeded what VIX implied.

### Inferences
- **2026-specific rule:** an overnight Brent jump of +3% or more, or headlines of Hormuz/Iran escalation, → expect a gap-down and a bigger range. Cut size, and do not fade the first move until the 09:15–09:45 range is set.
  - A large Brent *drop*, for example on de-escalation news, is the bullish shock. Gap-ups after de-escalation could be the biggest upside days of the regime.
  - This relationship should be re-estimated monthly (rolling 60-day corr of the Nifty gap with prior-day Brent). It will revert when oil stops being a supply shock.
- **GPR daily** has a weekly update cadence, so it is a slow regime variable. Same-day escalation needs a **news/LLM headline classifier**, as notes 03 plans.
- Low VIX combined with high GPR is the dangerous mix for option *sellers*. For our option *buyers* it is mildly favourable, because tails are cheap. But direction is unpredictable, so the right expression is smaller size with a reliance on volatility.

### Gaps
- No daily or intraday India study of GPR shocks. All the India evidence is monthly.
- No India study of oil shocks on the *intraday* Nifty range.
- An India-specific GPR (country index) at daily frequency exists only within the C&I dataset (country-level monthly). Not tested.

---

## 9. Concrete daily "macro bias and risk" scoring recipe, and a ranked shortlist of inputs

### Takeaway
- The evidence supports a macro layer that controls **(1) whether and when to trade, (2) position size, and (3) the expected range**, with only a **small, shrunk direction tilt** from two calendar effects.
- Macro, cross-asset and flow variables have no measurable predictive power for Nifty open-to-close direction once GIFT Nifty has set the gap. Our own regressions give R² ≈ 0.002 for open-to-close. Building them into a direction score would add noise.

### Cited Findings (the evidence each rule rests on)
- Range is about 2× implied on Budget days and up to 6× on the 2024 election-result day. RBI and FOMC days show no excess range. VIX falls on RBI days (−1.7% to −2%/day) and the session after FOMC (−1.5%). — OWN (Sections 1–2); India VIX rises before announcements and falls after — [A, Shaikh & Padhi 2013](https://journals.sagepub.com/doi/abs/10.1177/0973801013500168)
- Overnight shock size predicts the intraday range beyond VIX: |gap| 1–2% → 1.13×, above 2% → 1.71×; |US prior| > 2.5% → 1.25×; |Brent prior| > 5% → 1.21×. — OWN-R (Section 2)
- Prior US, Brent and USD/INR moves do not predict open-to-close (R² 0.002). — OWN-R (Section 2); US → open-to-close −0.03 (notes 04)
- Post-holiday open-to-close −0.22% (t −2.96, both sub-periods); Tuesday-expiry open-to-close −0.20% (t −2.4, N=54, fragile). — OWN (Section 7)
- Policy-surprise reactions run through the path/guidance channel and banks. — [A, Lakdawala & Sengupta](https://onlinelibrary.wiley.com/doi/10.1111/jmcb.13144); [B/C, RBI WP 03/2024](https://www.researchgate.net/publication/380127245_Equity_Markets_and_Monetary_Policy_Surprises_RBI_Working_Paper)
- Tightening hurts more when uncertainty is high. — [A/B, Sahu et al. 2025](https://onlinelibrary.wiley.com/doi/10.1111/irfi.70016)
- GPR is risk-off for large caps. — [A, SenGupta & Debnath 2026](https://link.springer.com/article/10.1007/s10368-026-00785-w)
- FII flows lag returns (notes 03). VIX regime and 50-DMA regime set the volatility level (notes 04).

### Inferences: the recipe

**When to compute:** a first pass at 08:45 IST, finalised at about 09:05 IST using the GIFT Nifty quote or the NSE pre-open indicative price. The evening before (after about 19:00 IST), pre-compute the slow parts: FII/DII, participant OI, India 10-year, GPR, and the event calendar.

**Step 1: Event gate `E`.** This is a lookup from the calendar, and it decides *if* and *when* to trade.

| Level | Days | Action |
|---|---|---|
| E3 | General-election results day; state-election results with national significance | **No trading.** Next day: 0.5 size, expect VIX to crush. |
| E3′ | Union Budget day | No entries until the speech ends. Then 0.5 size, expected range = 2.0× implied, wide stops. |
| E2 | RBI MPC decision day | No entries until about 30–45 minutes after the decision. Do not carry long options from day −1 into the decision. Normal size afterwards; Bank Nifty is most sensitive. |
| E2 | Nifty expiry (Tue) / Sensex expiry (Thu) | No short-gamma or open positions into the 15:15 closing auction. Tilt as in Step 4. |
| E2 | MSCI/FTSE/NSE index-rebalance effective day | Flat by 15:00. |
| E1 | FOMC day (Indian session before the announcement) | Lower range targets (×0.9). Next session is a normal gap day. |
| E1 | India CPI (12th), IIP (28th), GDP (quarter-end), all at 16:00 IST; US CPI/NFP (18:00/19:00 IST) | No intraday rule. Flag for the next morning's gap. |
| E1 | Heavyweight (weight ≥ 5%) results the previous evening | Expect gap and range; check NSE weights. |
| E0 | Otherwise | Normal |

**Step 2: Expected-range multiplier `M`.** This feeds targets, stops and the choice of strike or debit spread.
- `ExpRange = (VIX_prev/100/√252) × Spot × 1.04 × M_event × M_shock`
- `M_event`: 2.0 (Budget), 3–6 (election result), 0.9 (FOMC-day session), 0.95 (RBI day +1), otherwise 1.0.
- `M_shock = max(f(|gap|), g(|US prev|), h(|Brent prev|))`:
  - f(|gap|): 1.0 below 0.5%, 1.05 for 0.5–1%, 1.13 for 1–2%, 1.7 above 2%;
  - g(|US prev|): 1.06 for 1–2.5%, 1.25 above 2.5%, and add +0.15 when the US move was ≤ −1.5%;
  - h(|Brent prev|): 1.05 for 3–5%, 1.2 above 5%.
- These are the in-sample bucket means from Section 2. Shrink towards 1.0 until they are validated on 2027 data.

**Step 3: Stress score `S` (0–9).** This sets *size*, never direction. Add one point for each condition that holds:

| # | Condition | Data source | Update time |
|---|---|---|---|
| 1 | India VIX > 20, or VIX up more than 20% over 5 days | NSE / Yahoo `^INDIAVIX` | Live; prior close at 15:30 |
| 2 | Nifty below its 50-DMA (volatility regime, notes 04) | Own data | EOD |
| 3 | Brent 5-day change > +8% | Yahoo `BZ=F`; FRED `DCOILBRENTEU` (lagged) | Live / overnight |
| 4 | USD/INR 5-day change > +1% (rupee weakening) | Yahoo `INR=X`; FBIL reference rate | Live / daily |
| 5 | US 10-year 5-day change > +20 bp | FRED `DGS10`; Yahoo `^TNX` | Daily |
| 6 | India 10-year G-sec 5-day change > +15 bp | RBI DBIE / CCIL / Investing.com | Daily, evening |
| 7 | FII index-futures long ratio < 15% and falling, or FII net cash selling > ₹5,000 crore over 3 days | NSE participant-wise OI; NSE/NSDL FII-DII data | Evening, after about 18:00–19:00 |
| 8 | Daily GPR > 2 sd above its 1-year mean, or an LLM headline flag of military escalation / Hormuz | matteoiacoviello.com (weekly); RSS/GDELT (live) | Weekly / live |
| 9 | Policy-tightening phase plus a high-uncertainty regime: RBI or Fed hiked within the last 30 days and the India EPU index is above its median | rbi.org.in; federalreserve.gov; policyuncertainty.com (monthly) | Event / monthly |

- **Size multiplier:** 1.0 for S ≤ 2; 0.75 for S = 3–4; 0.5 for S ≥ 5.
- The ₹ risk per trade is then sized off `ExpRange`, so a bigger expected range also means fewer lots.
- **The thresholds are heuristic and have not been backtested.** Calibrate them so that S ≥ 5 occurs on roughly 10–15% of days.
- Today's rough reading: probably S ≈ 4–6 on 6 Oct 2026, with Fed and RBI hiking, G-sec at a 2.5-year high, a record FII futures short, rupee around 96 and Brent above $100. That gives 0.5–0.75 size. Compute it properly; this is an inference.

**Step 4: Direction tilt `B`.** This is a prior shift applied to the technical model's threshold, not a signal on its own.
- Baseline P(close > open) = 46.7% (notes 04).
- Post-holiday session: −3 points (half the measured −4 to −5).
- Nifty expiry Tuesday: −5 points (strongly shrunk from the measured −19; on probation). Sensex Thursday: −2 points.
- |gap| > 0.5%: tilt towards a fade of about +2 points against the gap direction (notes 04: gap-down → 53.8% up).
- **2026 oil regime:** no intraday tilt, since Brent doesn't predict open-to-close. Brent only explains the gap.
- Cap |B| ≤ 8 points. The tilt raises or lowers the confidence a long or short setup needs. It never creates a trade.

**Step 5: Output on the day card.**
- `TRADE_ALLOWED` (yes / after HH:MM / no)
- `SIZE` (0, 0.5, 0.75, 1)
- `EXP_RANGE_PTS` (Nifty and Sensex)
- `TILT` (−8 to +8 points, mostly 0)
- `FLAGS`: event names, expiry, rebalance, heavyweight results, oil regime

**Validation plan.** Log the card daily and forward-test for 3+ months before trusting the multipliers. Track:
- realised range / `ExpRange` (target about 1.0);
- the hit rate of setups by tilt bucket;
- P&L by stress bucket.

### Ranked shortlist of macro / fundamental / cross-asset inputs to implement

| Rank | Input | Data source (free) | Update time (IST) | Role | Evidence grade |
|---|---|---|---|---|---|
| 1 | **Event calendar gate** (Budget, election results, RBI decision window, expiry days, index-rebalance days, FOMC/US CPI/NFP/India CPI-IIP-GDP flags) | rbi.org.in MPC schedule; MoSPI release calendar (CPI 12th 16:00, IIP 28th 16:00, GDP 16:00); federalreserve.gov FOMC calendar; BLS schedule; NSE holiday and F&O expiry lists; MSCI/FTSE review dates | Monthly refresh; checked 08:45 daily | **Stand-aside / timing** + range multiplier | OWN-R (Budget, election, RBI and FOMC range and VIX) + A (VIX pre/post announcements, Shaikh & Padhi) |
| 2 | **Overnight shock size** (|GIFT-implied gap|, |prior US session|, |prior Brent|) | GIFT Nifty (NSE IX, broker feed, Investing.com); Yahoo `^GSPC`, `ES=F`, `BZ=F` | 06:30–09:05 | **Volatility expectation + size** (not direction) | OWN-R (N = 2,893) |
| 3 | **India VIX level/change and VIX vs realised** (already on the card) | NSE / Yahoo `^INDIAVIX` | Live; prior close | Volatility expectation, structure, size | A/B + OWN (notes 03/04) |
| 4 | **Post-holiday session flag** | NSE holiday list | Static | Small **direction tilt** (fade intraday) | OWN-R (both sub-periods, N = 165) |
| 5 | **Expiry-day flag** (Tue Nifty, Thu Sensex) | NSE/BSE expiry calendars | Static | Tilt (on probation) + no positions into the closing auction | OWN-F (N = 54) + A (Agarwalla & Pandey, expiry volatility) |
| 6 | **Oil–rupee–rates stress composite** (Brent 5d, USD/INR 5d, India 10Y 5d, US 10Y 5d) plus the rolling 60-day corr(gap, Brent) sign | Yahoo `BZ=F`, `INR=X`, `^TNX`; FRED `DGS10`, `DCOILBRENTEU`; RBI/CCIL G-sec | Overnight + EOD | **Size (stress regime)**; gap-sign context | OWN-R/F (2026 flip) + A/B (oil uncertainty, India) + C (RBI elasticities) |
| 7 | **Trend regime** (Nifty vs 50-DMA) | Own EOD data | EOD | Volatility regime / size | OWN-R (notes 04) |
| 8 | **Geopolitical risk** (daily GPR z-score + LLM headline escalation flag) | matteoiacoviello.com/gpr.htm (weekly); news RSS/GDELT | Weekly / live | Size (risk-off); stand-aside on extreme headlines | A (monthly, India) / B (volatility, global) |
| 9 | **FII positioning and flows** (index-futures long ratio, flips; FII vs DII net cash; SIP run-rate) | NSE participant-wise OI; NSE/NSDL FII-DII; AMFI monthly | Evening; monthly | Slow regime context; size; the "flip to net long" event | B (flows lag returns; negative for daily prediction) / C (flip study) |
| 10 | **RBI path-surprise proxy** (post-decision 1-year OIS / 2-year G-sec move, statement tone) | CCIL/FBIL (OIS not easily free), news | Decision day | Post-event direction for Bank Nifty, *after* the decision | A (Lakdawala & Sengupta; Prabu et al.) — data access is the constraint |
| 11 | **Heavyweight results flag** (weight ≥ 5%) and **monthly EPS-revision breadth** | NSE corporate announcements and index factsheet; brokerage notes | Evening before; monthly | Gap and range flag; slow context | B (international) / C (India) — no India test |
| 12 | **Turn-of-month (first trading day)** | Calendar | Static | Monitor only, no live use | OWN-F (sign flips across periods) |
| — | **Do not use for intraday direction:** prior US session, prior Brent, prior USD/INR, daily FII cash flow, PE / earnings-yield gap, DXY | — | — | — | OWN-R (R² ≈ 0.002) / B negative / no evidence |

### Gaps
- **No input in this shortlist has been tested out of sample.** The multipliers and tilts are in-sample bucket means from 2015–2026 Yahoo daily data, and the event-day results depend on dates that partly came from memory.
- The two highest-value missing measurements both need intraday data:
  1. intraday lead-lag from ES/NQ, USD/INR and Brent into Nifty futures during Indian hours (Section 2);
  2. ATM weekly-option IV crush around RBI, Budget and expiry days (Section 1).
- **Structural breaks** limit how far older evidence carries:
  - the expiry-day swap (Sep 2025);
  - the closing auction session for expiry settlement (Aug 2026);
  - SEBI's 2024–25 F&O curbs and STT changes;
  - the 2026 oil-supply regime.
  - Every OWN-R number should be re-checked on post-Sep-2025 data only, (about 270 sessions are available as of Oct 2026, roughly 54 per weekday, so day-specific results remain small-sample).
