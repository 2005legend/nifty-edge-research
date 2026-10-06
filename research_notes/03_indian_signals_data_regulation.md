# 03. India-specific signals, data sources, and algo rules

## A. Positioning and sentiment signals (from the options and futures market)

| Signal | What the evidence says | Grade | How we'd use it |
|---|---|---|---|
| **PCR (volume)** | No predictive power for Nifty returns. [MDPI 2019 rolling-causality study](https://www.mdpi.com/2227-7099/7/1/24) | B (negative) | Don't use |
| **PCR (open interest)** | OI-based PCR Granger-causes market returns in the same study. Extremes are only a "moderate" contrarian timing tool and work as crowd positioning. | B/C | Use *changes* and extremes in OI-PCR as a confluence feature, never alone |
| **Strike OI build-up** (max call OI = resistance, max put OI = support) | Practitioner heuristic, untested academically. Gamma and pinning near expiry are plausible. | C | Use as target/stop *levels*, not as a direction signal |
| **Growth in OTM call OI** | Seo, Byun & Kim (2020), JFM, [10.1002/fut.22095](https://doi.org/10.1002/fut.22095), Korea: growth in OTM call OI predicts market returns (hedger/informed-trader model) | B | Feature to test |
| **Option order imbalance in the first 10 minutes** | Kang, Kang & Lee (2021), JFM, [10.1002/fut.22301](https://doi.org/10.1002/fut.22301), Korea: predicts rest-of-day index return, **profitable after costs**, driven by institutions | B | Strong candidate. Needs tick or 1-min option-chain data from a broker websocket. |
| **Foreign investor open-buy trades in options** | Ryu & Yang (2018), JFM: foreign firms' open-buy put/call ratio predicts next-day spot returns (Korea) | B | NSE doesn't give trader-type flow intraday. The proxy is daily participant-wise OI. |
| **FII index-futures long/short ratio** | Sep 2016–Sep 2026: Nifty annualized about 6% after FII net-short days vs about 17% after net-long days. Long short streaks are *not* bearish: in 8 of 15 runs of 20+ sessions, the market ended higher. **Flip from a long short-campaign back to net long → Nifty up over the next 30 sessions more than 90% of the time** (small sample). About 2/3 of FII shorts are hedges. [Marketcalls](https://www.marketcalls.in/futures-and-options/what-do-we-actually-know-about-fii-index-futures-shorts.html) | C | Slow regime feature (days to weeks). Use the flip as an event. |
| **FII cash flows** | Patnaik, Shah & Singh (2013), Int'l Finance; Stigler et al. (2010): **FII flows follow Nifty returns, they do not lead them.** No post-event drift after extreme flows. | B (negative for prediction) | Context only |
| **India VIX** | Good predictor of realized volatility. Mean-reverting. Rises more on down moves (asymmetric). [NSE Working Paper 9/2013](https://nsearchives.nseindia.com/research/content/res_WorkingPaper9.pdf) | A/B | Decides trade *structure* and *size*, and sets expected-move-based targets and stops |
| **GIFT Nifty / US close** | US prior session → Nifty gap: corr **0.47**, sign match 68%. US → Nifty *intraday* move: corr **−0.03** (our own measurement, 2015–2026) | A (own data) | Explains the opening gap only. **No edge after the open.** |

Current positioning snapshot: FIIs were net short index futures for **333 straight sessions (May 2025 to Sep 2026)**, about 2.85 lakh contracts net short, long ratio about 11% (Marketcalls, Sep 2026). This is a record. A flip to net long would be a notable event.

## B. Expiry-day market structure (relevant to 0DTE/1DTE trading)

- **Jane Street case (SEBI interim order, 3 Jul 2025):** on 18 expiry days (Jan 2023–Mar 2025) the firm allegedly bought Bank Nifty constituents and futures in the morning, then sold aggressively after about 11:49 AM to push the index down into the close, profiting on large options positions. Example: 17 Jan 2024, ₹735 cr options profit vs a ₹61.6 cr cash/futures loss. ₹4,843.57 cr was impounded. [Oxford Business Law Blog](https://blogs.law.ox.ac.uk/oblb/blog-post/2025/07/jane-street-and-expiry-day-trap-unpacking-sebis-crackdown-algorithmic), [ECGI](https://www.ecgi.global/publications/blog/expiry-day-and-the-governance-of-algorithmic-trading-the-jane-street-episode)
  - **Lesson:** on expiry day, index moves can be driven by large options books rather than "fundamentals". Retail 0DTE traders are the counterparty.
- **Closing Auction Session since 3 Aug 2026** decides the expiry settlement (3:15–3:35 PM). There was a 2.5% indicative-price swing on the Sensex expiry of 3 Sep 2026. **Rule: no short-gamma positions held into the auction.**
- Agarwalla & Pandey (2013), JFM: volatility rises in the last half-hour of expiry day, when the settlement price is formed.

## C. Data sources: what we can actually get

| Need | Free option | Paid option | Notes |
|---|---|---|---|
| Live Nifty/futures/options ticks and full option chain | **Upstox API, Dhan API, Fyers API, Angel One SmartAPI** (free with an account) | Zerodha **Kite Connect ₹500/month** (live websocket + historical candles) | Zerodha's *free* "Personal" API has orders only, no market data. [Zerodha](https://zerodha.com/z-connect/updates/free-personal-apis-from-kite-connect), [AlgoTest broker comparison](https://algotest.in/blog/best-brokers-for-algo-trading-in-india/) |
| Historical 1-min index/futures | Broker historical APIs (Upstox, Fyers, Kite Connect) | TrueData, Global Datafeeds (GDFL) | Needed to test the opening-range, noise-area and first-half-hour signals |
| Historical 1-min **expired options** | Some free community datasets (quality varies) | GDFL, TrueData, AlgoTest/Stockmock (backtest platforms) | Critical for realistic option P&L backtests. Budget for one good source. |
| Daily F&O EOD (OI, settle) | **NSE F&O bhavcopy** (official, free) | — | Builds OI/PCR/max-pain history |
| Participant-wise OI (FII/DII/Pro/Client) | **NSE daily reports** (free, back to 2016) | — | FII long/short ratio |
| FII/DII cash flows | NSE/NSDL daily | — | Context only |
| India VIX history | NSE, Yahoo `^INDIAVIX` | — | Already downloaded to `data/` |
| Global cues | Yahoo: `^GSPC`, `BZ=F`, `INR=X`, US 10Y, GIFT Nifty (NSE IX) | — | Already downloaded to `data/` |
| News | ET / Moneycontrol / Business Standard RSS, GDELT | NewsAPI etc. | LLM headline classifier |
| Event calendar | RBI MPC schedule, US FOMC/CPI, NSE holiday list, results calendar | — | Hard-coded and refreshed monthly |

## D. Rules for running our own system (SEBI retail algo framework, fully in force since 1 Apr 2026)

- Orders through an API must come from a **static IP registered with the broker**.
- Authentication must be OAuth.
- Algo **registration** is needed only above **10 orders/second per exchange**. Below that, you count as a normal API user. A signal-and-alert system with manual or low-frequency execution is well under the limit.
- [Zerodha "In the Money" explainer](https://inthemoneybyzerodha.substack.com/p/sebi-algo-trading-changes-april-2026), [QuantInsti on algo trading in India](https://www.quantinsti.com/articles/algorithmic-trading-india/)
- **Design choice:** phase 1 should be **signal + alert only, with the human placing the order**. This avoids compliance overhead and keeps a human check. Automation can come later.

## E. MCP and connector status (checked 5 Oct 2026)

- No Indian market-data connector exists in the Claude connector registry. The "Financial Datasets" connector covers US fundamentals only.
- Zerodha publishes its own Kite MCP server (outside the registry). If you connect it later, use it **read-only for data**. Order placement stays with you.
- The Telegram plugin is configured in this environment but failed to connect today. It could be the alert channel later.
