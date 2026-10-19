# Profitable individual traders vs losers, and an audit of popular Indian index-options strategies (as of 18 Oct 2026)

Grading used throughout (my reading of the brief's scale):
- **A** = Indian regulator or exchange data, or a study on real Indian trading data (A− = unrefereed working paper on Indian data)
- **B** = peer-reviewed study (or major working paper, marked B−) on real non-Indian trading data, or a controlled experiment
- **C** = practitioner or platform material with partial verification
- **D** = marketing, anecdote or unverifiable claims

Primary documents parsed locally (full text extracted with pdftotext on 18 Oct 2026):
- SEBI DEPA, *Profitability of Individual Traders in the Equity Derivatives Segment (FY25–FY26)*, Aug 2026, 91 pp. Cited below as **SEBI-P26**. [PDF](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- SEBI, *Trading Behaviour of Individual Traders in the Equity Derivatives Segment (FY25–FY26)*, 20 Aug 2026, 53 pp. Cited below as **SEBI-B26**. Its buyer/seller and capital sections use a random sample of 5,050 traders; its persistence and experience sections use population data. [page](https://www.sebi.gov.in/reports-and-statistics/research/aug-2026/study-trading-behaviour-of-individual-traders-in-the-equity-derivatives-segment-fy25-fy26-_103836.html), [PDF](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)
- Agarwal, Ghosh, Prabhala & Zhao, *Animal Spirits on Steroids: Evidence from Retail Options Trading in India*, working paper, 30 Sep 2025. Uses NSE retail-flagged, investor-ID panel data for 2007–2021. Cited below as **AGPZ**. [PDF](https://www.fma.org/assets/docs/Derivatives2025/Zhao.pdf)
- Barber, Lee, Liu & Odean, *The Cross-Section of Speculator Skill: Evidence from Day Trading*, May 2011 working-paper version. Cited below as **BLLO**. [PDF](https://faculty.haas.berkeley.edu/odean/papers/day%20traders/Day%20Trading%20Skill%20110523.pdf)

Correction to earlier project notes: note 01 says "about 97% of individuals mainly bought options" and attributes it to the profitability study. That figure is **not in SEBI-P26**. It comes from the companion **SEBI-B26** and rests on a 5,050-trader random sample. Cite it that way.

---

## 1. SEBI studies (FY22–FY26): what do the ~10–12% profitable individuals look like?

### Takeaway
SEBI never profiles "winners" directly. It reports loss rates by group, so the profitable minority can only be described as the groups with lower loss rates. Those groups are option sellers, futures-only traders, people with larger capital and equity portfolios, people who trade fewer days and less turnover relative to capital, older traders, higher-income traders, women, and people who are active in the cash market. Even in the best groups, losers are usually the majority. The profitable share also shrinks sharply with horizon: **12.3% were profitable in FY26, 9.0% over FY25–26, 7.2% over FY22–24, 4.4% over FY22–26, and only 0.5% of five-year continuous traders made money in all five years.**

### Cited Findings

**Overall and horizon (persistence)**
- [A] FY26: 87.7% of individuals were net loss-makers (90.9% FY25, 91.1% FY24, 91.5% FY23, 90.2% FY22), so 12.3% were profitable in FY26. Before costs, 82.1% were loss-makers. — [SEBI-P26, §6.23](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [A] Over the two years FY25–FY26 combined, 91.0% of 122.6 lakh individuals lost money, leaving **9.0%** profitable. Over FY22–FY24 the figure was 92.7% (about 7.3% profitable). **FY22–FY26 cumulative: 160.3 of 167.7 lakh traders (95.6%) were net loss-makers**, with an average loss of ₹2.30 lakh (Annex Table 32). — [SEBI-P26](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [A] FY22 cohort, by years of continuous participation. Consistent profit-makers were 9.7% of 1-year traders, 2.2% of 2-year, 0.8% of 3-year, 0.4% of 4-year and **0.5% of 5-year continuous traders**. Consistent loss-makers among 5-year traders were 65.6%. The average cumulative profit of 5-year consistent winners was ₹66.5 lakh; the average loss of 5-year consistent losers was ₹13.8 lakh (Table 16). — [SEBI-B26, §5.15](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)
- [A] Profit is persistent on the losing side and only partly on the winning side. Traders by FY22–24 outcome went on to be profitable in FY25–26 at these rates: profit above ₹10 lakh, **48.3%**; profit ₹1–10 lakh, 35.3%; profit below ₹1 lakh, 16.7%; losses, 8.8% / 6.7% / **4.7%** (the last for losses above ₹10 lakh, of whom more than 95% lost again) (Chart 17). — [SEBI-B26, §5.24](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)
- [A] 90–92% of continuing traders who lost in each of the prior two years lost again: 91.6% in FY24, 92.0% in FY25, 90.0% in FY26 (Table 14). — [SEBI-B26, §5.14](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)
- [A] Experience does not help. The cumulative loss-maker share by consecutive years traded was 91.0% at 1 year, 94.4% at 2, 96.0% at 3, 96.5% at 4 and 95.3% at 5 (Table 15). New and regular traders had the same FY26 loss incidence (87.8% vs 87.7%), but regular traders lost 2.3× more on average (₹1.36 lakh vs ₹0.59 lakh) and turned over 45.7× their portfolio, against 19.2× for new traders. — [SEBI-B26, §5.15](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf); [SEBI-P26, §6.32](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [A] The earlier FY22–FY24 study found 93% lost (about ₹2 lakh average). The top 3.5% of loss-makers (about 4 lakh people) lost about ₹28 lakh each. **Only 7.2% made a profit, and only 1% made more than ₹1 lakh after costs.** More than 75% of loss-makers kept trading. — [SEBI press release, Sep 2024](https://www.sebi.gov.in/media-and-notifications/press-releases/sep-2024/updated-sebi-study-reveals-93-of-individual-traders-incurred-losses-in-equity-fando-between-fy22-and-fy24-aggregate-losses-exceed-1-8-lakh-crores-over-three-years_86906.html); [Taxmann](https://www.taxmann.com/post/blog/93-of-1-crore-fo-traders-saw-rs-2l-avg-loss-while-top-3-5-faced-rs-28l-avg-loss-incl-costs-sebi/); [Outlook Money](https://www.outlookmoney.com/invest/93-of-individual-traders-suffered-losses-in-fo-in-last-3-years-sebi-study)
- [A] Large wins are rare. Only about 1.1% earned more than ₹1 lakh over FY25–26. Losers outnumbered winners in every P&L slab: 21:1 in ₹1–10 lakh, 17:1 in ₹10 lakh–1 crore, 7:1 in ₹1–10 crore, 4:1 above ₹10 crore (Table 16). **Even the top 20 individual clients by turnover posted a combined net loss (−₹77 crore)** in FY26 (Table 14). — [SEBI-P26, §6.21, §6.27](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)

**Product: futures vs options, buyers vs sellers**
- [A] FY25–26 combined loss rates: options 91.0%, futures 68.4%. By product mix: **only-futures 67.3% (about one in three profitable, but just 0.75% of traders)**, both futures and options 84.8% (the largest average loss, ₹7.30 lakh), only-options 91.6% (Table 21). In FY26 by product: index options 87%, stock options 76%, stock futures 64%, index futures 62%. — [SEBI-P26, §6.24, §6.30](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [A] Buyer/seller profile, FY26, 5,050-trader sample. SEBI classifies a trader as "only options buyer" if every trading day starts with a buy, and as a "majorly options seller" if at least 50% of options days have short positions. The classes were 93% only buyers, 4.2% majorly buyers, 2.1% majorly sellers and 0.9% majorly futures. **Loss-maker shares: only buyers 89.9%, majorly buyers 75.2%, majorly futures 60.9%, majorly sellers 43.8%.** — [SEBI-B26, §5.1, Table 5](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)
- [A] Median return on peak margin in FY26: only buyers **−114%** (−187% in FY25), majorly buyers −15%, majorly futures −13%, **majorly sellers +1%** (the only positive median). A −114% median means at least half of pure buyers lost more than the largest margin they ever posted. — [SEBI-B26, §5.5, Table 8](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)
- [A] Sellers carry tail risk. The average loss per losing majorly-seller was **₹51.7 lakh** in FY26 (₹39.3 lakh in FY25), against ₹4.6 lakh for majorly buyers and ₹1.3 lakh for only buyers. The seller category as a whole still lost money (−₹5,430 lakh in the sample table; the text says "₹543 crore", which looks like a unit slip). SEBI says the sample has only 105 sellers, so read these as indicative. — [SEBI-B26, §5.1–5.2](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)

**Turnover, trading days, intensity**
- [A] By turnover in FY26: below ₹1 lakh, 86.4% loss-makers and ₹2,695 average loss; ₹1 lakh–1 crore, 87.8% and ₹40,019; above ₹1 crore, 89.7% and ₹4.87 lakh. Large-turnover traders were 20% of traders but **82% of losses**. They turned over 68× their portfolio, against 5.7× for medium-turnover traders. Over two-year windows, the loss share rises from about 86% (₹10k–1 lakh options turnover) to about 95% (above ₹10 crore) (Tables 22–23, Chart 37). Turnover here is premium turnover for options and notional for futures. — [SEBI-P26, §6.31, §6.33](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [A] Traders active on more than 100 days were 42% of traders but 94% of turnover and 87% of losses, with an average loss of ₹2.76 lakh against ₹0.22 lakh for 100 days or fewer. Loss-maker share by days traded (small sample cells): fewer than 10 days 83.3%, 10–25 days 85.8%, **25–50 days 84.7%, 50–100 days 90.8%**, more than 100 days 89.4%. Median loss: −₹654 under 10 days, −₹19,183 above 100 days (Table 17). — [SEBI-B26, §5.17](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)
- [A] Turnover relative to capital is the sharpest contrast. **More than one-fifth of traders ran ₹10 lakh–1 crore of annual turnover on a peak margin of only ₹10,000–1 lakh, and 94–98% of them were loss-makers.** At a given capital level, more turnover meant more losers; at a given turnover, more capital meant fewer. — [SEBI-B26, §5.9](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)

**Capital, portfolio, cash-market activity**
- [A] By peak margin (FY26 sample): below ₹10k, 90.5% loss-makers (average loss ₹5,561); ₹10k–1 lakh 90.0%; ₹1–5 lakh 86.4%; ₹5–10 lakh 76.3%; ₹10 lakh–1 crore 67.6%; above ₹1 crore **36.4% (only 22 traders)**. Average loss per loss-maker rises with capital, from ₹5,600 to ₹9.6 lakh. — [SEBI-B26, §5.3, Table 6](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)
- [A] By equity portfolio: none or below ₹50k, 93% loss-makers; ₹1–10 lakh 88%; ₹50 lakh–1 crore 72%; above ₹10 crore 58%. Small-portfolio traders (below ₹1 lakh) turned over **1,665×** their portfolio, against 44× (₹1–10 lakh) and 8× (above ₹1 crore). Small-portfolio, high-turnover traders were 13% of traders and **52% of losses**. Among high-turnover traders the loss rate was 93% with small portfolios and 64% with large ones. — [SEBI-P26, §6.45–6.48](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [A] By age and portfolio: traders under 30 with portfolios above ₹1 crore had a 50% loss rate, against 90% for under-30s with zero portfolio (Annex Table 44). — [SEBI-P26](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [A] Cash-market activity: traders with zero cash turnover had a 90% loss rate (FY26), against 84% for those whose cash turnover was more than 5× their derivatives turnover. Average loss fell from ₹2.07 lakh to about ₹38k–₹15k across those categories (Tables 19–20). — [SEBI-B26, §5.19](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)

**Demographics**
- [A] Age (FY26): under 30, 88.55% loss-makers with turnover 93× portfolio; 30–40, 88.05%; 40–50, 87.80%; 50–60, 85.29%; over 60, **80.95%** with turnover 19×. Average loss rises with age (₹58,749 under 30; ₹2.2 lakh at 50–60). Gender: women 84.73%, men 88.56%. Income: below ₹5 lakh 88% (and 53% of losses); ₹50 lakh–1 crore about 71%; above ₹1 crore about 81% (Tables 26–28). — [SEBI-P26, §6.38–6.40](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)

**Costs, asymmetry, algo use**
- [A] In FY26, transaction costs were **35% of gross losses for loss-makers but 21% of gross profits for profit-makers** (18–23% for winners in FY24–26). Costs alone turned 4.4 lakh gross winners into net losers in FY26 (5.3 lakh in FY25). The average cost per trader was ₹31,628 in FY26. — [SEBI-P26, §6.25, §6.35–6.36](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [A] Win/loss asymmetry: the average loss-maker lost ₹1.47 lakh and the average profit-maker made ₹1.22 lakh (FY26). Of 4.02 crore trader-quarters, only 15.4% were profitable. **The median losing quarter (₹10,525) was 2.4× the median winning quarter (₹4,366).** 78.7% of traders who had both kinds of quarter had a larger average loss than average gain. — [SEBI-P26, §6.25](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf); [SEBI-B26, §5.25](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)
- [A] Blow-ups precede exits. Among 16.2 lakh traders who stopped after a losing quarter, **the median final-quarter loss was 2.2× their average profit in earlier winning quarters (more than 30× for the top 10%)**, and the median maximum historical loss was about 5× (more than 73× for the top 10%). 86–89% of quarterly quitters had just had a losing quarter. — [SEBI-B26, §5.26–5.27](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)
- [A] Algo use among individuals: only 15% of 84.2 lakh individuals were "algo entities" in FY26. SEBI says this overstates real algo use, because broker auto square-offs after 3:20 pm count. **Individual algo entities still lost ₹51,728 crore gross over FY25–26, against ₹1,18,396 crore for non-algo individuals** (Chart 20). Meanwhile 99% of FPI and prop gross profit came from algo entities. — [SEBI-P26, §6.18](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [A] The cash-segment intraday study (FY23): 71% of individual intraday traders lost. **Very frequent traders (more than 500 trades a year) had an 80% loss rate.** Under-30s had 76%. Traders with 3 years of experience had 54%. Loss-makers' costs added 57% on top of trading losses; profit-makers spent 19% of profits on costs. — [SEBI study page, Jul 2024](https://www.sebi.gov.in/reports-and-statistics/research/jul-2024/study-analysis-of-intraday-trading-by-individuals-in-equity-cash-segment_84946.html); [summary](https://tradingqna.com/t/key-findings-from-sebis-analysis-of-intraday-trading-by-individuals-in-equity-cash-segment/170633) (summary only, PDF not parsed)
- [A] FY22 study (Jan 2023): 89% lost (average ₹1.1 lakh). 90% of "active traders" lost (average ₹1.25 lakh). Loss-makers paid a further 28% of net losses in costs; profit-makers paid 15–50% of profits. — [Business Standard](https://www.business-standard.com/amp/article/markets/sebi-study-suggests-89-retail-traders-in-equity-f-o-suffered-losses-123012501466_1.html); [Business Today](https://www.businesstoday.in/amp/markets/stocks/story/loss-makers-of-dalal-street-9-out-of-10-individual-fo-traders-lost-money-in-fy22-says-sebi-367628-2023-01-25)

### Inferences
- The best-supported profile of the profitable minority, built only from groups with lower loss rates, is: sells options or trades futures rather than buying options; has large capital relative to turnover (peak margin ≥ ₹5–10 lakh); holds a large equity portfolio; trades relatively few days; is older; and is also active in the cash market. None of these is shown to be causal. Much of the gradient is probably selection: wealthier, older and more diversified people both trade less intensively and are hedging or positioning rather than gambling.
- The horizon decay (12% → 9% → 7% → 4.4% → 0.5%) is the key number. A one-year profit is mostly noise, and multi-year profitability is a sub-1% event. This matches the global day-trader evidence in Section 2.
- A ₹10,000 account trading one lot of a ₹3,500–4,500 premium sits in SEBI's worst capital cells (peak margin below ₹10k–1 lakh, about 90% loss-makers). Gross premium turnover is about ₹8,000 per round trip (if SEBI counts buy plus sell premium; half that if one side). That gives about ₹12 lakh a year at 150 trades, about ₹8 lakh at 100 and about ₹4 lakh at 50. **Above roughly 125 trades a year, the system enters the "₹10 lakh–1 crore turnover on ₹10k–1 lakh margin" cell, where 94–98% lost.** This is an association-based warning, not proof that frequency causes losses for a rules-based trader.
- Buying is the structurally worst category: a 90% loss rate and a −114% median return on margin. That is the base rate our buy-only design starts from, so any live edge must be shown, not assumed.

### Gaps
- SEBI does not publish holding time, intraday versus overnight split, or expiry-day versus non-expiry outcomes for profitable individuals, nor whether profitable individuals used algos. AGPZ's intraday versus overnight evidence (Section 2) is the closest substitute.
- The buyer/seller and capital findings rest on a 5,050-trader sample (105 sellers, 22 traders with more than ₹1 crore margin). Their margins of error are large.
- SEBI-B26 Table 17 (days traded) has inconsistent sub-sample counts. Treat the 50-day step-up in loss rate as suggestive.
- I did not download the July 2024 intraday-cash PDF or the Sep 2024 FY22–24 PDF. Those figures come from the SEBI press release and secondary summaries.

---

## 2. Exchange-data studies of day traders: what fraction is persistently profitable, does skill persist, and what predicts it?

### Takeaway
Across Taiwan, Brazil, India and Korea, the persistently profitable share of day traders and speculators is **about 1% or less**. Skill does exist at the extreme top: in Taiwan, the prior year's top 500 earned 28 bps a day net the next year. It is identifiable mainly from **past performance**, plus experience, concentration and willingness to short. For the other 99%, experience does not improve results, losers keep trading, and in India continuation tracks past success without any skill persistence.

### Cited Findings
- [B] Taiwan, 1992–2006. About 360,000 individuals day-trade in an average year, and about 15% earn positive abnormal returns net of fees in a given year, which is largely luck. **Only about 1,000 (less than 1%) predictably outperform the next year.** The prior year's top 500 earn 49.5 bps a day gross and 28.1 bps net on day trades the following year. Prior-year losers earn −17.5 bps gross and −34.2 bps net. Including open positions, top traders net only about 2 bps a day. Predictors: past performance (by far the best), experience, past day-trading volume, willingness to short, and concentration in a few stocks. Top traders **demand** liquidity with aggressive orders; they are not paid market makers. — [BLLO working paper, 2011](https://faculty.haas.berkeley.edu/odean/papers/day%20traders/Day%20Trading%20Skill%20110523.pdf) (later published in J. Financial Markets, per my memory, not re-verified)
- [B] Taiwan, *Learning, Fast or Slow* (Review of Asset Pricing Studies 2020). **74% of day-trading volume comes from traders with a history of losses, and 97% of day traders are likely to lose money in future day trading.** Rational learning does not explain persistence. — [IDEAS abstract](https://ideas.repec.org/a/oup/rasset/v10y2020i1p61-93..html)
- [B] Brazil, mini-index futures, all 2013–2015 entrants who persisted more than 300 days. **97% lost money. Only 1.1% earned more than the minimum wage, and 0.4–0.5% more than a bank teller's starting pay.** The best trader averaged US$310 a day with a daily SD of US$2,560. No evidence of learning. — [FGV repository](https://repositorio.fgv.br/items/e87d04fc-4b4c-4a56-ab5a-1c84c1afde1b/full); [EconPapers](https://econpapers.repec.org/RePEc:fgv:eesptd:525)
- [A−] India, NSE retail options 2007–2021, with investor IDs. Day trading reached **90% of retail index-option volume**. The median holding interval was 0 days (mean 2.4). 82% of traders start a contract in its final week, and retail is 42% of expiry-day volume. **Day-trading P&L is "flat to weakly positive", while positions not closed the same day lose significantly**, a pattern the authors tie to the disposition effect. Exit is more likely after poor performance, but "**traders extrapolate their ability from their past successes without any evidence for skill persistence**". Cumulative retail losses were ₹506 billion. — [AGPZ](https://www.fma.org/assets/docs/Derivatives2025/Zhao.pdf)
- [A−] AGPZ: returns scaled by volume improve monotonically with volume decile. The lowest-volume decile averaged −21%, and the value-weighted figure is −1.4%. This is not in conflict with SEBI: heavy traders lose a smaller *percentage* of what they trade but more *rupees*, and more of them lose. — [AGPZ](https://www.fma.org/assets/docs/Derivatives2025/Zhao.pdf); [SEBI-P26](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [B] Korea (KOSPI 200 options and futures, Jan 2010–Jun 2014, 153,835 domestic retail accounts). About 66% of active retail investors mostly hold simple, one-sided positions in one option class, and they underperform. **Selling volatility is the most profitable style for both retail and institutional investors**, and style effects persist. — [Hu, Kirilova, Park & Ryu, Management Science 2024](https://pure.skku.edu/en/publications/who-profits-from-trading-options/); [CXO sample details](https://www.cxoadvisory.com/investing-expertise/what-kind-of-index-option-traders-and-trades-are-profitable/)
- [B] Korea: about 25% of retail KOSPI 200 futures day traders were profitable net of fees (Choe & Eom 2009). More frequent and intensive trading went with worse outcomes (Ryu 2012). Taiwan futures: 3,470 day traders lost NT$61,500 on average, and experience did not help (Kuo & Lin 2013). US day traders: about 67% lost and about 20% were more than marginally profitable (Jordan & Diltz 2003). All as summarised in SEBI's literature review. — [SEBI-P26, §3](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [B] A counterpoint: a 2024 JFM study of KOSPI 200 futures finds domestic individuals' performance does **not** depend on trading frequency in general, though they lose more in bearish, low-volatility markets. — [Frequent Trading and Investment Performance (JFM 2024)](https://scholar.xjtlu.edu.cn/en/publications/frequent-trading-and-investment-performance-evidence-from-the-kos/)
- [B] Korea's multiplier changes (raised 5× in 2012, halved in 2017) did not fix individual losses. Individuals "still persisted poor performance", and those with accumulated losses did worse after the cut. — [Park et al., Asian Review of Financial Research 2022](https://pure.uos.ac.kr/en/publications/the-impact-of-multiplier-reduction-on-the-trading-performance-in-/)
- [B] Professional floor traders (CME) also show the disposition effect, but **measures of trading discipline predict subsequent success** (Locke & Mann, JFE 2005). Only about 15% of new floor-trader entrants survive more than a year (Locke & Mann 2015). — [JFE 2005 abstract](https://academicnewsletter.sufe.edu.cn/info/357584); [2015 paper](https://ideas.repec.org/a/eee/beexfi/v8y2015icp54-63.html)

### Inferences
- The realistic prior for a new individual intraday options system is "below 1% chance of being a persistent winner". The only thing that moves that prior is **a live record**, and a losing early record is far more informative than a winning one (SEBI: 4.7% vs 48% repeat-profit rates).
- What predicts skill among the rare winners (concentration, willingness to short, experience combined with past profit) suggests a specialist, symmetric (long and short) approach with few instruments. That fits a two-index, call-and-put system, but it gives no support to the idea that more trading builds skill.
- Indian day trades being roughly flat while overnight holds lose is the single most design-relevant Indian finding. Losses come from *not exiting*, not from the intraday entry itself.

### Gaps
- No Indian study measures year-to-year *rank* persistence of skilled options day traders the way BLLO does for Taiwan stocks.
- The Wiley Scholar Gateway search quota was exhausted (it resets 1 Nov 2026), so Korean retail *options* lottery studies (e.g., Chung & Kim on OTM purchases) were found only by title and not read.

---

## 3. Behavioural traits linked to losses, and evidence that rules or automation reduce them

### Takeaway
The losing patterns are well documented. They are overtrading; the disposition effect (taking winners and holding losers, in India by letting losing options ride toward expiry); loss-chasing after a losing morning or quarter; a preference for cheap, short-dated, out-of-the-money "lottery" options; and attention or convenience-driven trading. The evidence that *pre-committed, automatic* constraints help is solid: automatic stop orders, leverage caps, algorithmic execution and robo-advice all reduce biases. **Reminders alone do not.** Automation removes execution biases but does not create an edge: Indian individual "algo" accounts lost heavily.

### Cited Findings
- [B] Overtrading: among 66,465 US households (1991–96), the heaviest traders earned 11.4% a year against 16.4% for the average household and 17.9% for the market. — [Barber & Odean, JF 2000](https://faculty.haas.berkeley.edu/odean/Papers%20current%20versions/Individual_Investor_Performance_Final.pdf)
- [A] Indian overtrading evidence: the loss rate and loss size rise with turnover, trading days and turnover-to-capital (Section 1). 80% of very frequent cash intraday traders (more than 500 trades a year) lost. — [SEBI-B26](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf); [SEBI intraday study](https://www.sebi.gov.in/reports-and-statistics/research/jul-2024/study-analysis-of-intraday-trading-by-individuals-in-equity-cash-segment_84946.html)
- [A−] Disposition effect in Indian options: day traders close profitable positions intraday and carry losers, which then "result in significant losses". In March 2020, about 5.9% of retail traders held short-volatility positions and reduced but did not close their short puts into the 26 Mar expiry while India VIX went from 13.6 to 70.4. — [AGPZ](https://www.fma.org/assets/docs/Derivatives2025/Zhao.pdf)
- [B] Loss-chasing: CBOT proprietary traders who lose in the morning take more afternoon risk (about 16% more likely than morning winners). Their trades move prices, which then reverse quickly. — [Coval & Shumway, JF 2005](https://ideas.repec.org/a/bla/jfinan/v60y2005i1p1-34.html); [BYU summary](https://scholarsarchive.byu.edu/facpub/9284)
- [A] Indian blow-up pattern: the final losing quarter before exit is 2.2× (median) to more than 30× (top decile) a trader's average winning quarter, and maximum losses run about 5× the average gain. Most traders' average loss exceeds their average gain (78.7%). — [SEBI-B26, §5.25–5.27](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)
- [B] Lottery preference: ex-ante option skewness is strongly negatively related to option returns. Low-minus-high skewness portfolios differ by 10–50% *per week* (equity options). — [Boyer & Vorkink, JF 2014](https://ideas.repec.org/a/bla/jfinan/v69y2014i4p1485-1527.html)
- [A−] Indian lottery evidence:
  - Skewness of weekly Nifty/Bank Nifty options is 1.1–3.9 at the money but 7.5–18.1 for OTM (moneyness below −2%).
  - Options entry is predicted by prior trading in volatile and lottery stocks and by poor stock-market performance ("gambling for resurrection"); poor stock performers are about 50% more likely to enter.
  - When SEBI tripled the Nifty lot (25 → 75, Aug 2015), affected small traders **moved 0.26% further OTM and 1.9 days shorter, and their returns fell 1.51%**.
  - After physical settlement of stock options, expiry-day OTM volume rose 55%, and short-maturity traders shifted to index options and lost ₹23,984 each.
  - Source: [AGPZ](https://www.fma.org/assets/docs/Derivatives2025/Zhao.pdf)
- [A−] Convenience: when the same trader moved from a traditional to a FinTech (discount app) broker, volume rose 55%. Traders using both lost ₹24,159 more via FinTech orders. — [AGPZ](https://www.fma.org/assets/docs/Derivatives2025/Zhao.pdf)
- [B] Attention: stocks that Robinhood users herd into earn −3% (−6% for extreme herding) average 5-day abnormal returns, and about −5% (−9% extreme) over the following month. — [Barber, Huang, Odean & Schwarz SSRN](https://www.smallake.kr/wp-content/uploads/2020/12/SSRN-id3715077.pdf); [UC Davis summary](https://gsm.ucdavis.edu/news/what-effect-brokerage-robinhood-having-stock-market)
- [B] **Automatic selling devices work; reminders don't.** In a controlled experiment, investors given automatic stop-loss and take-gain orders showed a significantly smaller disposition effect, driven by realising more losses. A reminder of one's own plan did not reduce it. — [Fischbacher, Hoffmann & Schudy, RFS 2017](https://kops.uni-konstanz.de/entities/publication/6576ae2f-bc9b-452c-9a2c-0379f8654c9d)
- [B] Constraints help: the 2010 US retail forex leverage cap (50:1) cut trading volume 23% and **high-leverage traders' losses 40%**, with no effect on spreads. — [Heimer & Simsek, JFE 2019](https://ideas.repec.org/a/eee/jfinec/v132y2019i3p1-21.html). In the same setting, leverage limits **reduced the disposition effect and improved market timing**, a result replicated in lab markets. — [Heimer & Imas, RFS 2022](https://ideas.repec.org/a/oup/rfinst/v35y2022i4p1643-1681..html)
- [B−] Algorithms vs humans, Copenhagen exchange, millisecond data: human day traders show a substantial disposition effect that grows on colder days. Algorithms show none, apart from a minority explained by profitable mean-reversion logic. — [Liaudinskas, Norges Bank WP 6/2022](https://www.norges-bank.no/en/news-events/news-publications/Papers/Working-Papers/2022/wp62022/)
- [A] India, robo-advice at a large brokerage (800,000+ accounts): adopters showed **declines in the disposition effect, trend chasing and rank effect**, plus diversification gains. This is equity portfolios, not derivatives. — [D'Acunto, Prabhala & Rossi, RFS 2019](https://academicnewsletter.sufe.edu.cn/info/352712)
- [A] Automation is not an edge: individual "algo entities" lost ₹51,728 crore gross in FY25–26. — [SEBI-P26, §6.18](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [A] Persistence despite losses: 88% of traders with losses above ₹10 lakh in FY22–24 kept trading. Among 1.10 crore FY22–24 loss-makers, 77% now hold equity portfolios worth less than 25% of their cumulative F&O losses. — [SEBI-B26, §5.23, §5.28](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)

### Inferences
- The behaviours to engineer out are, in order of evidence for Indian option buyers:
  1. holding losing options past the intended exit (AGPZ)
  2. trading frequency and turnover relative to capital (SEBI)
  3. moving to cheaper OTM or shorter-dated strikes when capital tightens (AGPZ lot-size experiment)
  4. loss-chasing and blow-ups after losses (SEBI quarter data; Coval–Shumway)
  5. app-driven, attention-driven extra trades (AGPZ FinTech result; Robinhood)
- Fischbacher et al. imply that an *alert* telling the user to exit is the weak form ("reminder"). The strong form is a resting broker-side stop-limit and target placed at entry. For an alerts-only system, the protocol must require placing the exit orders immediately after the fill.

### Gaps
- No Indian causal study tests whether self-imposed daily loss limits or trade caps improve retail F&O outcomes.
- Imas (2016) on "realisation effect" risk-taking after realised versus paper losses was not verified in this session.

---

## 4. Indian practitioner strategies and "proven" claims: what is verifiable?

### Takeaway
**I found no independently verifiable live P&L record for any popular Indian index-options retail strategy or algo-marketplace product.** That covers the 9:20 straddle, expiry-day straddles and strangles, ORB, OI/PCR systems, trainers' systems, and Tradetron, AlgoTest, Quantiply and Streak deployments. What is verifiable points the other way:
- SEBI orders show trainers claiming high accuracy while losing money themselves.
- SEBI data shows the retail option-seller category lost money in aggregate despite a 56% win rate.
- The best-documented expiry-day "edge" (Jane Street) is alleged manipulation by a firm with a huge options book.

Since May 2026, SEBI's PaRRVA is the only legitimate channel for performance claims, and no verified results are public yet.

### Cited Findings

**Verification infrastructure and claim rules**
- [A] PaRRVA (Past Risk and Return Verification Agency) verifies risk-return metrics of investment advisers, research analysts and algo providers. CARE Ratings ran it with NSE as the data centre: pilot from 8 Dec 2025, CARE recognised on 29 Apr 2026, live 4 May 2026, and an enrolment deadline of 3 Aug 2026 for entities that want to keep sharing past performance. — [Business Standard](https://www.business-standard.com/amp/markets/news/sebi-launches-return-verification-framework-parrva-to-curb-fake-performance-claims-125120800842_1.html); [NSE press release](https://nsearchives.nseindia.com//web/pressrelease/2025-12/PR_cc_08122025_20251208115202.pdf); [AIR News](https://www.newsonair.gov.in/sebi-operationalises-parrva-to-boost-transparency-and-investor-protection/); [Outlook Money](https://www.outlookmoney.com/news/sebi-operationalises-parrva-framework-sets-deadline-for-advisers-to-verify-data-on-past-performance)
- [A] SEBI's algo rules restrict risk-return claims. Brokers were barred (Sep 2022 directive) from associating with platforms that advertise past performance, and the restriction is lifted only for PaRRVA-verified claims. The Feb 2025 retail-algo framework makes brokers principals and providers their agents. "Black-box" algos need research-analyst registration and a research report for every logic change. — [Taxmann](https://www.taxmann.com/post/blog/sebi-launches-parrva-for-verified-performance-in-ads/); [QuantInsti summary](https://blog.quantinsti.com/sebi-algo-trading-guidelines-retail-investors); [MediaNama](https://www.medianama.com/2025/04/223-sebi-parrva-guidelines-updates-algo-trading-rules/)
- [D] Tradetron's own app listing claims about 11,000 algos deployed, and its marketplace sells fixed or profit-share subscriptions. No audited live returns were found. Reviews are mixed and unverified. — [App Store listing](https://apps.apple.com/us/app/tradetron/id1540269842); [Techjockey reviews](https://www.techjockey.com/reviews/tradetron)

**Trainer and finfluencer exposés (SEBI orders)**
- [A] "Baap of Chart" (Md Nasiruddin Ansari), Oct 2023: he claimed 20–30% returns and 95% accuracy, but **SEBI found a net trading loss of ₹2.89 crore (Jan 2021–Jul 2023), concealed from followers**. The order required ₹17.2 crore of fees to be disgorged, and recovery of ₹18.14 crore was started in Dec 2025. — [MediaNama](https://www.medianama.com/2023/10/223-finfluencer-baap-of-chart-fine-rs-17-2-crore-sebi/); [Business Standard](https://www.business-standard.com/amp/markets/news/sebi-bars-finfluencer-from-securities-market-asks-to-disgorge-rs-17-cr-123102501080_1.html); [Moneylife](https://www.moneylife.in/article/sebi-initiates-1814-crore-recovery-from-finfluencer-nasir-ansari-of-baap-of-charts-2-others/79146.html)
- [A] Avadhut Sathe Trading Academy, interim ex-parte order of 4 Dec 2025: ₹546.16 crore impounded and about ₹601 crore of disgorgement proposed. The academy ran mentorship batches costing up to ₹6.75 lakh, with WhatsApp calls giving option strategies, entries and exits, and index forecasts. It had already received an administrative warning in Mar 2024 for **showcasing selective profitable trades**. — [Moneylife](https://moneylife.in/article/54617-crore-impounded-as-sebi-bans-avadhut-sathe-wife-and-academy-for-running-unregistered-advisory-network/79036.html); [Angel One](https://www.angelone.in/news/market-updates/sebi-bars-avadhut-sathe-academy-for-unregistered-advisory-impounds-rs-546-crore)
- [A] Asmita Patel Global School of Trading ("Options Multiplier" course), Feb 2025 interim order: ₹53.67 crore impounded, with disgorgement possibly reaching about ₹105 crore. — [Business Standard](https://www.business-standard.com/markets/news/sebi-impounds-rs-53-crore-illegal-gains-from-asmita-patel-five-others-125020701263_1.html); [YourStory](https://yourstory.com/2025/02/sebi-bans-fininfluencer-asmita-patel-5-others-from-mkt-impound-illegal-gains-of-over-rs-53-cr)
- [A] PR Sundar / Mansun Consultancy, settled May 2023 without admission: ₹6.07 crore disgorged plus ₹46.8 lakh in settlement fees, and a one-year voluntary trading bar, for unregistered advice via Telegram and website. No verified trading record was disclosed. — [Moneylife](https://www.moneylife.in/article/mansun-consultancys-pr-sundar-his-wife-mangayarkarasi-agrees-to-disgorge-rs607-crore-pay-rs4680-lakh-to-settle-case-with-sebi/70918.html); [Goodreturns](https://www.goodreturns.in/news/finfluencer-pr-sundar-and-mansun-consulting-settle-sebi-case-pay-rs-6-crore-disgorgement-1284561.html)

**The 9:20 straddle and expiry-day selling**
- [C] AlgoTest's Apr 2026 page defines the 9:20 Nifty ATM short straddle (25% leg stops, exit 15:10) but gives **no** backtest statistics in text and calls such strategies "proven to be reliable" without support. — [AlgoTest](https://algotest.in/blog/the-920-straddle-strategy-defined.md)
- [C] Stop-hunt fragility (Aug 2021): on 20 Aug 2021 the Nifty 16450 PE went from 122.70 to 803.50 within one second and triggered about 6,287 lots of SL-M stops. The estimated slippage was ₹5,000–34,000 per lot. SL-M orders in index options were later withdrawn. — [Marketcalls 2021](https://www.marketcalls.in/futures-and-options/how-the-9-20-intraday-straddlers-are-being-gamed.html)
- [C] Edge decay: the Bank Nifty 9:20 straddle (35% stops, 0.5% costs) deteriorated in 2023, which the author attributes to crowding by sellers and low volatility. The figures are in images only. A Dec 2024 forum backtest of the Nifty version showed mixed daily P&L. — [Marketcalls 2023](https://www.marketcalls.in/futures-and-options/is-the-920-straddle-no-more-working.html); [TradingQnA](https://tradingqna.com/t/reports-of-the-death-of-920-short-straddle-are-greatly-exaggerated/179061)
- [D] Brokers publish daily expiry-day short-strangle calls (e.g., Kotak, Jul 2026) with no published track record. — [Business Today](https://www.businesstoday.in/markets/story/nifty-weekly-expiry-today-kotak-suggests-short-strangle-strategy-key-levels-to-watch-544084-2026-07-21)
- [A] The best verified Indian check on retail selling is SEBI-B26. Majorly-option-sellers had a 44% loss rate and a +1% median return on margin, but the category lost money overall, and losing sellers averaged ₹51.7 lakh (n = 105). Peer-reviewed Nifty evidence (Bhat et al. 2024) finds intraday short-option returns "largely negative and insignificant", with the volatility premium earned overnight (already in [note 02](<../02_strategy_evidence_part1.md>)). — [SEBI-B26](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf)

**Expiry-day dynamics**
- [A] Jane Street interim order (3 Jul 2025): alleged manipulation of Bank Nifty on 18 expiry days (Jan 2023–Mar 2025), with ₹43,289 crore of index-options profits in that period and ₹4,843.57 crore impounded. **Status, 6 Oct 2026:** SEBI told SAT the matter is still at the investigation stage and that the interim order could "probably be vacated" if Jane Street shows no manipulation. No final order yet. — [The Week/PTI](https://www.theweek.in/wire-updates/business/2025/07/04/dcm1-biz-sebi-jane-street.html); [Business Standard](https://www.business-standard.com/amp/markets/news/sebi-bars-jane-street-orders-rs-4844-cr-disgorgement-market-manipulation-125070400081_1.html); [Business Today, Oct 2026](https://www.businesstoday.in/markets/story/sebi-tells-sat-that-jane-street-has-enough-data-to-respond-to-market-manipulation-charges-559953-2026-10-06)
- [A] Liquidity provision is concentrated. The top 5 prop firms do 62% of prop index-option turnover and the top 10 do 85%. The top 10 prop firms earned 74.5% of prop gross profit (₹33,124 crore of ₹44,483 crore in FY26). — [SEBI-P26, §6.19–6.21](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [C] Zerodha's CEO (Apr 2026, citing NSE): 60–70% of F&O volume comes from 1–2% of traders. — [Business Today](https://www.businesstoday.in/amp/markets/stocks/story/zerodhas-nithin-kamath-says-60-70-of-fo-volumes-come-from-just-1-2-traders-526999-2026-04-23)

### Inferences
- Every "proven" retail strategy should be treated as **grade D until PaRRVA-verified or replicated on our own tick data with costs**. The only Indian cases where a seller's real P&L became public (SEBI enforcement) contradicted the marketing.
- The 9:20 straddle mostly matters to us as **counterparty structure**. Morning ATM premium is supplied by a crowd of rule-based sellers with percentage stops. Their stop cascades can produce sharp, short-lived premium spikes, a known mechanism (2021) that is now less extreme without SL-M. Our buyer system should not chase a premium spike in the first minutes after a leg stops out.
- Expiry-day price paths can be driven by large options books. The Jane Street allegation is morning buying followed by heavy selling after about 11:49 to push the index into the close. Retail is about 42% of expiry-day option volume, so it is the natural counterparty.

### Gaps
- No live, auditable P&L was found for any Tradetron, AlgoTest, Quantiply or Streak public deployment. These platforms publish backtests and forward tests, not broker-verified fills. No press investigation of subscriber outcomes was found.
- No PaRRVA-verified research-analyst or algo metrics are publicly visible yet. The pilot did not publish them, and I found no post-May-2026 disclosures.
- OI walls, PCR, max pain and ORB: no new verifiable Indian records beyond those already in note 02 and the multifactor report. Those were not re-researched, per the brief.
- The Jane Street "net ₹36,502 crore" figure seen in some coverage was not confirmed.

---

## 5. What do profitable groups (prop desks, FPIs, the profitable individual minority) do differently that a small retail system could copy?

### Takeaway
The profitable groups **sell options or provide liquidity, trade at scale with algorithms and low costs, and hold capital that is large relative to turnover**. FPIs add low turnover and high open interest, meaning positioning and hedging rather than churn. A ₹10,000 option-buying account cannot copy the selling or the scale. It can copy:
- low turnover relative to capital
- fixed, small size
- strict cost control
- symmetric, specialised trading
- pre-committed exits
- treating options as a small satellite to a cash-equity portfolio

### Cited Findings
- [A] Prop traders earned about ₹44,483 crore gross in FY26, **98% of it from options**, and FPIs about ₹13,896 crore (77% from options). 99% of FPI and prop profit came from algo entities. Prop desks supply about 60% of derivatives turnover. — [SEBI-P26, §6.16–6.19](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [A] FPIs are about 7% of turnover but hold 25–33% of daily open interest, which SEBI reads as "portfolio hedging and medium-term positioning, rather than high-frequency or intraday trading". — [SEBI-P26, §6.20](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [A−] Institutions are more likely to be net option sellers, use complex positions and avoid FinTech brokers. Retail losses equal institutional profits in aggregate. — [AGPZ](https://www.fma.org/assets/docs/Derivatives2025/Zhao.pdf)
- [B] Volatility selling was the most profitable style for both retail and institutions in Korea; simple one-sided retail strategies underperformed. — [Hu et al. 2024](https://pure.skku.edu/en/publications/who-profits-from-trading-options/)
- [A] Among individuals, lower loss rates go with option selling (44%), futures-only trading (67%), peak margin of ₹10 lakh–1 crore (68%) or more, portfolios above ₹10 crore (58%), age over 60 (81%), more cash-market activity (84%), and fewer trading days (83–85% below 50 days). — [SEBI-B26](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf); [SEBI-P26](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [A] Costs separate winners from losers: 21% of winners' gross profit against 35% of losers' gross loss. 4.4 lakh traders were flipped to net losses by costs in FY26. — [SEBI-P26](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)
- [B] Rare persistent day-trading winners in Taiwan trade both long and short, concentrate in few names and have experience together with a profit history. They earn their edge by forecasting short-term moves, not by providing liquidity. — [BLLO](https://faculty.haas.berkeley.edu/odean/papers/day%20traders/Day%20Trading%20Skill%20110523.pdf)
- [B] Discipline measures predict professional futures traders' later success. — [Locke & Mann 2005](https://academicnewsletter.sufe.edu.cn/info/357584)

### Inferences
- Not copyable at ₹10k: scale, liquidity provision, colocation and algo latency, naked or spread selling (about ₹29k exposure margin per short leg, per the multifactor report), and portfolio hedging.
- Copyable, with the closest evidence:
  1. **Turnover/capital discipline.** Keep annual premium turnover well under about ₹10 lakh at ₹10k capital, and scale capital before frequency (SEBI §5.9).
  2. **Few trading days** (SEBI §5.17).
  3. **Cost minimisation.** Limit orders, no chasing, a minimum expected edge as a multiple of cost (SEBI cost shares).
  4. **Fixed, small size with automatic exits** (Heimer–Simsek, Heimer–Imas, Fischbacher).
  5. **Symmetric, specialised** trading: calls and puts on two indices only (BLLO).
  6. **Buy only when volatility is cheap**, the buyer's version of being on the right side of the volatility premium (Hu et al.; Bhat et al.).
  7. **Run the options account as a satellite** to a cash-equity portfolio, since cash-active traders lose less (SEBI-B26 §5.19). This is association only.

### Gaps
- SEBI does not split individual *profitable* traders by algo use, holding period or index, so we cannot see what profitable individual option *buyers* (if any material group exists) do differently from losing buyers.

---

## 6. Concrete implications: rules our system should add or change

### Takeaway
The evidence argues for **fewer live trades than the current ≤3/week ceiling allows**, hard and automatic exits, no strike drift toward cheap OTM, a cost-edge hurdle, no top-ups, and a pre-committed quit rule. The most important new rule is a **turnover/trade-day budget**. At ₹10,000 capital, 3 trades a week (about 150 a year) puts the account in SEBI's 94–98%-loss cell for high turnover on low capital.

### Cited Findings
- [A] The supporting evidence for each rule is cited in Sections 1–5. The key numbers are:
  - **>100 trade-days:** 87% of losses ([SEBI-B26 §5.17](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf))
  - **₹10 lakh–1 crore turnover on ₹10k–1 lakh margin:** 94–98% loss-makers ([SEBI-B26 §5.9](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf))
  - **Two losing years:** 90–92% lose again ([SEBI-B26 §5.14](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233601328.pdf))
  - **Overnight carry:** day trades flat, overnight carry loses ([AGPZ](https://www.fma.org/assets/docs/Derivatives2025/Zhao.pdf))
  - **Strike drift:** −1.51% returns when constrained traders drifted OTM and shorter ([AGPZ](https://www.fma.org/assets/docs/Derivatives2025/Zhao.pdf))
  - **Automatic stops:** reduce the disposition effect; reminders don't ([Fischbacher et al.](https://kops.uni-konstanz.de/entities/publication/6576ae2f-bc9b-452c-9a2c-0379f8654c9d))

### Inferences

**Rules to enforce (with evidence grade)**

| # | Rule | Grade | Main evidence |
|---|---|---|---|
| R1 | **Trade-day and turnover budget.** Keep ≤3/week as a hard ceiling, but budget **≤100 live trade-days a year (about 2 a week on average, ideally 50–75)** and **annual gross premium turnover below ₹10 lakh (≈100× capital)** while capital is about ₹10k. Track both on the dashboard; block alerts once the monthly pro-rata budget is used. Scale capital before frequency. | A (association, not causal) | SEBI-B26 §5.9, §5.17; SEBI-P26 §6.31–6.33; SEBI intraday study |
| R2 | **Pre-registered quit and pause rule.** Keep the SPRT/CUSUM stop from the multifactor report. Add an **annual review**: if the live year is net negative after costs, stop live trading and return to shadow mode. Never "trade through" a second losing year. | A | SEBI-B26 §5.14–5.15, §5.24; BLLO; Learning Fast or Slow |
| R3 | **Automatic exits, not reminders.** Within 30 seconds of the fill, the alert protocol must have the user place a broker-side stop-limit backstop and a resting target. The alert is the trigger, not the stop. Log any trade where this was not done as a protocol breach. | B (lab plus field) | Fischbacher et al. 2017; Heimer & Imas 2022; Liaudinskas 2022 |
| R4 | **Intraday only; no conversion of losers.** Hard time exit (already 15:00 expiry, 15:10 otherwise). A losing position may never be rolled, carried or "given till expiry". No averaging down. | A− | AGPZ (day trades flat; overnight positions lose; disposition) |
| R5 | **No-revenge locks.** One trade a day already. Add: after 2 consecutive losing trades, or a weekly loss of 2R, **no new trade until next week**. After a −4R month, pause for the rest of the month. Size is always one lot and never increases after a loss. | B / A | Coval & Shumway 2005; SEBI-B26 §5.25–5.27 blow-up ratios |
| R6 | **No strike drift to lottery tickets.** Keep the delta floor at 0.25+. If capital or affordability rules leave only OTM, shorter-dated strikes, the answer is **no trade**, not a cheaper strike. | A− / B | AGPZ lot-size experiment (−1.51%); Boyer & Vorkink 2014; SEBI −114% median buyer RoCE |
| R7 | **Cost hurdle and cost ledger.** Require expected gross edge ≥ 3× the measured all-in round-trip cost. Keep the kill-switch when live costs exceed assumption by 30%. Report costs as a % of gross P&L monthly (winners spend about 21%, losers about 35%). | A | SEBI-P26 §6.25, §6.35–6.36 |
| R8 | **No top-ups; capital floor.** Starting capital is fixed risk capital. Never add money to recover a drawdown. Stop at the floor (about ₹7,000 at ₹10k, the equivalent of the earlier ₹3,500-on-₹5,000 logic; re-derive). | A (association) | SEBI-B26 §5.5 (median buyer lost more than 100% of peak margin), §5.23, §5.28 |
| R9 | **Keep the system a satellite.** The options account stays a small fraction of the user's cash-equity investing. Record the ratio. | A (association only) | SEBI-B26 §5.19; SEBI-P26 §6.45–6.48 |
| R10 | **Automation is not evidence.** The fact that alerts are rules-based is not an edge. The edge must come from the validation protocol. | A | SEBI-P26 §6.18 (individual algo entities lost ₹51,728 cr) |
| R11 | **Ignore unverified performance claims.** No external strategy, trainer system or marketplace algo enters the system unless PaRRVA-verified or replicated on our own data with costs. Treat all others as grade D. | A | SEBI orders (Baap of Chart, Sathe, Patel); PaRRVA framework |
| R12 | **No option-selling module at this capital.** A high win rate is not safety. Revisit only with defined-risk spreads at ≥₹50k (as in the multifactor report). | A | SEBI-B26 §5.1–5.2 (44% loss rate but ₹51.7 lakh average seller loss) |
| R13 | **Don't chase opening premium spikes or crowd events.** No entry within 5 minutes of an abrupt ATM premium spike, which may be a stop cascade from the 9:20 sellers. Keep the news-shock gate for attention events. | C / B | Marketcalls 2021; Barber et al. Robinhood |
| R14 | **Expiry-day humility.** Keep the existing expiry rules (no entries in the last hour, flat before the closing auction). Treat late-morning reversals on expiry days as a known risk pattern. | A / C | AGPZ (retail 42% of expiry volume); Jane Street interim order (alleged) |
| R15 | **Quarterly asymmetry check.** Each quarter, compute average loss on losing trades vs average gain on winners, and the largest single loss vs the average win. Flag if the largest loss exceeds 2× the average win; by construction it should be ≈ 1R vs ≥ 1.5R. | A-derived | SEBI-B26 §5.25–5.27 |

**Decision flag (CLAUDE.md "speak up first"): trade frequency vs validation time**
- *What matters.* The live phase has to show an edge after costs. The earlier report estimated about 95–115 live trades for an SPRT verdict, 7–9 months at 3 a week. The SEBI data says more trade-days and turnover per rupee of capital go with worse outcomes, so the frequency that speeds up validation is the frequency most associated with losses. This is association, not causation; a rules-gated system may not share the gamblers' selection effect.
- *Options:*
  - (a) **Keep 3/week live.** Fastest verdict (about 8 months). It sits in SEBI's 94–98% cell (about ₹12 lakh turnover on ₹10k), with the highest cost drag and the largest exposure to a streak.
  - (b) **Cap at about 100 trade-days a year (2/week on average).** The verdict takes about 12 months. Turnover stays below ₹10 lakh.
  - (c) **About 1/week live** plus full shadow-labelling of every gated setup, scored on calibration. Live P&L verdict takes about 2 years, but calibration and hit-rate evidence still accrue at about 20+ setups a month at no cost.
- *Recommendation:* **(b) with (c)'s shadow-labelling**, which the multifactor design already partly includes. Switch to (a) only if live costs come in at or below assumption and the first 40 trades show calibration within 5 points. Switch to (c) if the first 30 live trades trip the CUSUM.
- *What can't be known yet:* whether SEBI's frequency–loss link applies to a selective, rules-gated trader. That needs our own live data. The cheap pilot is to compare shadow-labelled outcomes on "would-have-been 3rd trade of the week" setups against the first two, to see whether marginal setups are worse.
- Record this decision and its reason in the decision log.

### Gaps
- There is no direct evidence that any of R1–R15 turns a losing Indian option buyer into a winning one. The rules remove documented loss channels; they do not create an edge.
- The turnover estimate assumes about ₹8,000 gross premium turnover per round trip and that SEBI counts buy plus sell premium. If SEBI counts one side, the thresholds roughly double the allowable trade count. The methodology section defines gross turnover as "premium turnover for options" without saying which sides are counted.
