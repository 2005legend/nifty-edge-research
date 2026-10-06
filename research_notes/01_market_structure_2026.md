# 01. Indian index options market structure (as of 5 Oct 2026)

Collected 5 Oct 2026. Check these again before going live, because SEBI has changed the rules several times in two years.

## Contracts we can trade

| Index | Exchange | Weekly expiry? | Expiry day | Lot size (from Jan 2026) |
|---|---|---|---|---|
| Nifty 50 | NSE | Yes | Every Tuesday (since 1 Sep 2025) | 65 (was 75) |
| Sensex | BSE | Yes | Thursday | check BSE circular |
| Bank Nifty | NSE | No, monthly and quarterly only (last weekly expired 13 Nov 2024) | Last Tuesday of month | 30 (was 35) |
| FinNifty, Midcap Select, Next50 | NSE | Monthly only | Last Tuesday | n/a |

**What this means for the project:** "weekly options" now means **Nifty 50 (Tuesday)** and **Sensex (Thursday)**. Bank Nifty is monthly only. That makes Bank Nifty unsuitable for a weekly-expiry system, but it is still useful as an input signal, because banks are about 35% of Nifty.

Sources: [HDFC Sky lot sizes](https://hdfcsky.com/news/nse-revises-market-lot-sizes-for-major-index-derivatives-effective-january-2026), [AlgoTest lot sizes](https://algotest.in/blog/nifty-lot-size/), [NSE circular FAOP70616](https://nsearchives.nseindia.com/content/circulars/FAOP70616.pdf), [Zerodha on SEBI index-derivative rules](https://zerodha.com/z-connect/business-updates/sebis-new-rules-for-index-derivatives-heres-whats-changing)

## Costs (these decide whether an edge survives)

- **STT from 1 Apr 2026 (Budget 2026):** options **0.15% of premium on the sell side** (was 0.10%), 0.15% on exercise (was 0.125%), futures 0.05% (was 0.02%). [ICICI Direct](https://www.icicidirect.com/futures-and-options/articles/stt-changes-in-budget-2026-what-f-o-traders-need-to-know), [ClearTax](https://cleartax.in/s/securities-transaction-tax-stt)
- Brokerage is about ₹20 per order at discount brokers. On top of that come exchange transaction charges, SEBI fees, 18% GST on brokerage and charges, and stamp duty on buys.
- **Slippage and bid-ask spread** are usually bigger than all of the above for far out-of-the-money options and in fast markets.
- Calendar-spread margin benefit is removed on expiry day, and an extra 2% Extreme Loss Margin (ELM) is charged on short options on expiry day (since Nov 2024).
- The option premium is collected upfront from buyers (since Feb 2025).

## Expiry settlement mechanics (new in 2026)

- **Closing Auction Session (CAS) went live on 3 Aug 2026** for Nifty, Bank Nifty and Sensex.
- Index option settlement price = the equilibrium price from the **3:15–3:35 PM auction** on the index constituents. Options keep trading until **3:40 PM**.
- On 3 Sep 2026, the Sensex indicative level dropped about 2.5% during the auction and put premiums spiked 400–500%. Holding short options into the auction carries tail risk.
- SEBI consultation, expected around mid-Sep 2026: possible VWAP across the pre-auction and auction windows, expiry at 3:15 PM, tighter bands, and limits on late orders. **Recheck before going live.**
- Source: [MarketsEasy on CAS](https://marketseasy.in/blog/sebi-expiry-settlement-price-cas-review-2026)

## Who wins and who loses: SEBI study, Aug 2026 (FY25–FY26)

Source: SEBI DEPA, "Profitability of Individual Traders in the Equity Derivatives Segment (FY25–FY26)", released 20 Aug 2026. [PDF](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf). These numbers come from my own text extraction of the PDF.

- **87.7%** of individual traders had net losses in FY26 (90.9% in FY25). Aggregate net loss was ₹91,685 crore.
- Options loss incidence was 87.7%; futures was **66.0%**. Options made up 92% of individual losses.
- Average loss among loss-makers was ₹1.47 lakh. Average profit among profit-makers was ₹1.22 lakh. **Losers lose about 21% more than winners win.**
- About 97% of individuals mainly *bought* options. About 2% mainly sold.
- **Loss rate rises with turnover.** It goes from about 86% (₹10k–1L turnover) to **about 95% (more than ₹10 crore turnover)**. Overtrading is the main way people blow up.
- Transaction costs were about ₹25,000 crore a year. **82.1% were losers before costs, and costs pushed another 5.6 points into loss.**
- **99% of FPI and proprietary-desk profits came from "algo entities".** Prop desks made about ₹44,000 crore gross and FPIs about ₹14,000 crore. The top 10 prop firms earned about 75% of prop profits.
- **Options losses were "largely independent of market direction".** Even in Q1 FY26, when Nifty rose about 9%, individuals still lost ₹18,878 crore in options. In other words, **predicting direction correctly was not enough to make money buying options.** Theta, implied volatility, costs and timing ate the edge.
- Q4 FY26 (Jan–Mar 2026): **Nifty fell about 15%**, and individuals lost ₹8,081 crore in futures that quarter because they were mostly long.
- Expiry-day (0DTE) share of index-option turnover was 59% in FY26 (70% in FY25).

### Design implications

1. **Directional accuracy above 55% is necessary but nowhere near enough.** The metric that matters is *expectancy after costs*: (win% × avg win) − (loss% × avg loss) − costs. The system has to model theta, implied volatility (IV) and costs, not only direction.
2. **Trade frequency has to be low and selective.** Loss rate rises steadily with turnover. The system should be allowed to say "NO TRADE" on most days.
3. **Structure matters as much as direction.** Defined-risk spreads (debit or credit) usually beat naked option buying for a retail account.
4. **Systematic, rules-based (algo) trading** is where the profits sit. That supports building a rules-driven system, while staying honest that we are competing against those same firms.

## Live snapshot on the day research started (Mon 5 Oct 2026)

- Nifty 50 closed at **22,555.75** (+0.60%), ending a 4-day losing streak. Bank Nifty closed at 54,714.10 (+0.48%). **India VIX 14.67** (+1.47%).
- For context, Nifty fell about 15% in Jan–Mar 2026 and is well below its late-2025 levels (~26k).
- Source: [Business Standard live blog, 5 Oct 2026](https://www.business-standard.com/amp/markets/news/stock-market-live-october-5-nse-bse-sensex-today-nifty50-gift-nifty-crude-oil-prices-snapdeal-listing-today-rvnl-share-price-today-ipo-today-126100500057_1.html)
