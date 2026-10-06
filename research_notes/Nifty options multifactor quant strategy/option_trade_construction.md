# Option trade construction for a ₹5,000 intraday Nifty/Sensex option buyer (Oct 2026)

Evidence grades: **A** = peer-reviewed + India + survives costs; **B** = peer-reviewed non-India, or India but not cost-tested (academic working papers marked B−); **C** = practitioner; **D** = anecdote/unverified snippet; **O** = official rule/fee schedule/regulator data (factual, not a strategy test). **[calc]** = my own arithmetic/simulation under the stated assumptions (not evidence). **[data]** = my own descriptive statistics on Yahoo daily Nifty/India VIX data in `data/` (2015 to 5 Oct 2026; Yahoo opens can be noisy).

Common assumptions for [calc] items unless stated: Nifty 22,555.75 and Sensex 72,382.47 (5 Oct 2026 closes, [Business Standard](https://www.business-standard.com/markets/news/stock-market-live-october-5-nse-bse-sensex-today-nifty50-gift-nifty-crude-oil-prices-snapdeal-listing-today-rvnl-share-price-today-ipo-today-126100500057_1.html), [BBN Times](https://www.bbntimes.com/financial/bse-sensex-snaps-four-day-losing-streak-rises-472-77-points-to-72-382-47-as-fed-hike-fears-ease)); India VIX 14.67; Nifty lot 65 (50-pt strikes), Sensex lot 20 (100-pt strikes); one lot of either ≈ ₹14.5–14.7 lakh notional. Pricing = Black-76 with F ≈ spot, zero rates intraday, and a **business-time** variance clock: daily implied s.d. = VIX/√252 = 0.924%; each session = 1 variance unit of which an overnight share θ = 0.40 and intraday 0.60 spread uniformly over 9:15–15:30 (375 min). Remaining variance at time t with N full sessions left before expiry: w = 0.60·(minutes left today/375) + N.

---

## 1. What does the evidence say about 0DTE / very short-dated option returns and pricing, and which moneyness/time buckets are worst and least-bad for buyers?

### Takeaway
Across US and Indian evidence, **buying** short-dated options loses money on average mainly through (i) transaction costs/spreads and (ii) overnight holding; intraday-only long positions are roughly break-even gross (slightly positive in the US, insignificant in India), so a buyer's edge must come almost entirely from the directional forecast. The worst buckets are far-OTM (>1–2% OTM), last-hour, overnight-held, high-IV, single-leg debit trades; the least-bad are ATM/near-ATM, entered mid-morning with 3–24 h left, closed the same day, and (where affordable) defined-risk spreads.

### Cited Findings
- **[B] Beckmeyer, Branger & Gayda ("Retail Traders Love 0DTE Options… But Should They?", SPX, Feb 2021–Sep 2023):** >75% of retail SPX option trades are 0DTE; retail lost $241k/day on average, $350k/day after daily expiries began (16 May 2022); >$90m of ~$125m total losses were transaction costs ("roughly 60% of daily losses are the result of transaction costs"); losses are driven by single-leg, debit (upfront-payment) and high-IV trades; retail buys perform particularly poorly while retail sells are profitable after fees — [FoFI 2024 PDF](https://wp.lancs.ac.uk/fofi2024/files/2024/04/FoFI-2024-146-Leander-Gayda.pdf)
- **[B] Same paper, spreads by bucket (retail effective spread as % of mid):** calls 6.0%, puts 5.0% (non-retail 12.5%/9.6%); buys 8.4% vs sells 5.2%; time-to-maturity <1 h 10.5%, 1–3 h 5.9%, 3–24 h 4.5%; ATM calls 3.0%, calls 0.5–2% OTM 12.8%, calls >2% OTM 80.2% (quoted 98.2%); ATM puts 2.7%, puts 0.5–2% OTM 7.0%, puts >2% OTM 44.6% — [FoFI 2024 PDF](https://wp.lancs.ac.uk/fofi2024/files/2024/04/FoFI-2024-146-Leander-Gayda.pdf)
- **[B] Same paper, returns by structure:** single puts/calls have mean net profit −$16.3/−$20.7 per trade and median −$35; margin-adjusted mean return −5.6% (puts) / −9.4% (calls), median −0.7%/−0.8%; >25% of single-leg trades expire worthless; put/call spreads have median +3.0%/+3.3% (mean ≈0); regression: Debit dummy −0.293% per trade, Complex (multi-leg) +0.17%, IV coefficient negative ("retail investor trades are particularly poor in high-IV contracts and in high-IV times"); net profits negative in every trading hour of expiry day — [FoFI 2024 PDF](https://wp.lancs.ac.uk/fofi2024/files/2024/04/FoFI-2024-146-Leander-Gayda.pdf)
- **[B] Bandi, Fusari & Renò, "0DTE Option Pricing" (J. Finance forthcoming per SSRN):** a local-in-time Edgeworth-type expansion with closed-form skewness/kurtosis adjustments prices and hedges 0DTE options significantly better than state-of-the-art models; 0DTE-based return and variance risk premia give "suggestive evidence of nearly instantaneous predictability" — [SSRN 4503344](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4503344)
- **[B−, preprint] Bandi, Fusari, Gazzani & Renò (2026), "Ultra-short-term volatility surfaces":** the ATM implied-vol term structure across 0–7-day SPX tenors oscillates (slope breaks between 1–2 days and 4–6 days); classical (affine/rough) models cannot fit it; implied vols depend on calendar- vs business-time sampling, and CBOE's 1-day VIX uses business time — [arXiv 2603.29430](https://arxiv.org/abs/2603.29430)
- **[B] Vilkov, "0DTE Trading Rules" (SPX 09/2016–Feb 2026):** a positive 0DTE variance risk premium exists but is small and hard to monetise after frictions; P&L is dominated by tail/skewness realisations; the paper claimed 10:00 ET conditional rules worked out-of-sample — [SSRN 4641356](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4641356). **Contradicted by its own August 2026 correction:** a cost unit-scale bug charged the half-spread at 1/100 of its true size; after correction "no strategy or basket retains a positive net Sharpe ratio" — [GitHub replication repo](https://github.com/vilkovgr/0dte-strategies); [FirmTape/DEV write-up](https://dev.to/firmtape/we-replicated-a-published-0dte-options-paper-to-four-decimals-one-unit-scale-bug-reverses-its-3ddj)
- **[B] Almeida, Freire & Hizmeri, "0DTE Asset Pricing":** 0DTE variance risk premium is high and mostly compensation for *upside* risk, and negatively predicts intraday market returns; most 0DTEs violated risk-aversion price bounds and a strategy exploiting this was profitable up to 2022 but dissipated after daily expiries — [SSRN 4701401](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4701401). Second-hand summary: annualised 0DTE VRP 1.54–2.95% by entry time vs 0.55% at 1DTE [C] — [FirmTape](https://firmtape.com/research/what-the-0dte-literature-claims)
- **[B] Dim, Eraker & Vilkov, "0DTEs: Trading, Gamma Risk and Volatility Propagation":** market-maker net gamma is on average positive and negatively related to future intraday volatility; positive (negative) MM gamma strengthens intraday reversal (momentum); no evidence that 0DTE activity propagates volatility — [SSRN 4692190](https://dx.doi.org/10.2139/ssrn.4692190)
- **[B] Muravyev & Ni (JFE 2020):** delta-hedged S&P 500 option returns average −0.7%/day, made of −1.0% overnight and **+0.3% intraday**; explanation: option prices fail to reflect that volatility is much higher intraday than overnight; pattern holds across maturities and moneyness — [SSRN 2820264](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2820264), [JFE](https://www.sciencedirect.com/science/article/abs/pii/S0304405X19302193)
- **[B: peer-reviewed, India, not cost-tested] Bhat, Pandey & Nageswara Rao (J. Futures Markets 2024), Nifty options, 1-min data:** *short* option strategies earn positive, significant overnight returns and negative, insignificant intraday returns; the variance risk premium is "mainly a reward for overnight risk"; the asymmetry is strongest for short-dated OTM options (delta-hedged OTM calls ≤7 DTE: 30.87% overnight vs 19.4% of opposite sign intraday) and weakest for long-dated ITM — [Wiley](https://onlinelibrary.wiley.com/doi/10.1002/fut.22512). (Signs in my extracted tables were stripped; the paper's text states the direction.)
- **[B−, India working paper; P&L at execution prices so spreads included, ₹20/trade-day deducted, other levies not] Agarwal, Ghosh, Prabhala & Zhao, "Animal Spirits on Steroids" (NSE, 2007–2021):** retail dominates index options; day trading reaches ~90% of volume; mean holding 2.4 days, median 0; trading surges from ~5 days before expiry into 0DTE, concentrated in ATM/slightly OTM; "Day trading profits are flat to weakly positive on average… Positions not closed in day trading result in significant losses"; lowest-volume decile average trading return −21%; last-week return skewness 1.1–3.9 for ATM vs 7.5–18.1 for >2% OTM (lottery-like) — [FMA 2025 PDF](https://www.fma.org/assets/docs/Derivatives2025/Zhao.pdf), [SSRN 5430635](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5430635)
- **[B] Wang & Zhou (J. Futures Markets 2026), China 50ETF options:** calls positive overnight/negative intraday (opposite of US), driven by retail gambling/attention demand; asymmetries persist with retail as counterparties — [Wiley](https://onlinelibrary.wiley.com/doi/10.1002/fut.70095). Shows the sign of intraday option returns is market- and flow-specific.
- **[O] SEBI FY25–FY26 profitability study (Aug 2026):** 87.7% of individuals lost in FY26; options were ~92% of individual losses; 0DTE was ~59% of index-option turnover, ~75% within one day and ~97% within a week; option losses were largely independent of market direction — [SEBI PDF](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf), [TaxGuru summary](https://taxguru.in/sebi/sebi-studies-key-trends-retail-participation-trading-behaviour-profitability-equity-derivatives.html); expiry-day index-option turnover often ~350× cash-market turnover — [Upstox](https://upstox.com/news/market-news/financial-regulations/sebi-flags-unhealthy-imbalance-expiry-day-index-options-turnover-350x-cash-market-volumes/article-178256/)

### Inferences
- **Worst buckets for a buyer (ranked):** (1) holding overnight / into expiry (Bhat, Agarwal, Muravyev–Ni); (2) >1% OTM, especially in the last 1–2 h (effective spreads 45–80% of mid in the US; lottery skew in India); (3) market buys at the ask in fast markets and the last hour (spreads ~2× vs mid-morning); (4) high-IV days/contracts (Beckmeyer IV coefficient); (5) single-leg debit trades in general.
- **Least-bad:** ATM to ~0.5% OTM, entered ~9:45–13:00 with ≥2 h left, closed the same session with limit/marketable-limit orders. Gross expected return of an intraday long option without a forecast is ≈0 (±small VRP), so **net expectancy ≈ −(round-trip costs + spread)** unless the forecast adds drift.
- The one India result that survives costs at the aggregate level is the *seller* overnight premium — irrelevant to a ₹5k buyer, but it reinforces "never carry a long option overnight".
- The Vilkov correction is a warning for this project's own backtests: a cost-unit bug can flip the sign of a result. Unit-test the cost model (Section 10) against a broker contract note.

### Gaps
- No Indian study found that reports *net-of-all-costs* returns of long 0/1DTE Nifty or Sensex options by moneyness × time-of-day (SEBI does not split losses by DTE; no NSE/BSE paper found). Grade-A evidence for this exact question does not exist; it must be measured from the project's own option-chain snapshots.
- Bhat et al. (sample ~2017–2020, Thursday expiries) and Agarwal et al. (to 2021) pre-date Tuesday expiry, lot 65, the 2026 STT hike and the closing-auction settlement.

---

## 2. Intraday theta-decay shape on expiry day and the day before

### Takeaway
With variance spread in business time, an ATM option's value scales with √(remaining variance), so decay is non-linear and accelerates through the afternoon; OTM options lose a much larger *fraction* faster. With spot unchanged from 9:15, an ATM 0DTE keeps ~85% of its value at 11:00, ~63% at 13:00, ~40% at 14:30; a 0.3%-OTM keeps 76%/43%/14%; a 0.6%-OTM 64%/24%/2%. On the day before expiry, an unchanged ATM loses ~21% from open to close and another ~23% overnight (θ = 0.40), which is a cost an intraday-only system never pays.

### Cited Findings
- [B] Muravyev & Ni: realised volatility is much higher intraday than overnight in the US, and option prices under-reflect this — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2820264)
- [B−] Bandi et al. (2026): implied-vol term structures at 0–7 days depend on whether time is measured in calendar or business time; CBOE's 1-day VIX uses business time — [arXiv 2603.29430](https://arxiv.org/abs/2603.29430)
- [D, page attribution uncertain, from search snippets of Indian practitioner blogs such as [Niftywise](https://niftywise.org/blog/what-happens-on-nifty-weekly-expiry-day-a-complete-guide) and [MarketsEasy](https://marketseasy.in/blog/theta-decay-options-explained-nifty-premium-loss)]: "an ATM option can lose 70–80% of its remaining value between 1:00 and 3:00 PM"; "ATM ₹300 at 9:15 → ~₹120 by noon → ~₹50 by 2 PM"; weekly decay "Thu 10–15%, Fri 15–20%, Mon 25–35%, Tue 40–60%". The ₹300 ATM figure is inconsistent with VIX ≈ 15 (model ATM ≈ ₹60–70; see below) and should be ignored.

### Inferences
- **[data] Overnight share of daily variance** (var(prev close→open) / (var(overnight)+var(open→close))): 0.38 for 2015–2026, 0.43 for 2024–2026, **0.55 since Sep 2025** (overnight s.d. 0.66% vs intraday 0.59%). Unlike the US, recent Nifty variance is gap-heavy (2026 war/global-shock year); default θ = 0.40, recalibrate quarterly.
- **[calc] Premium vs time (spot flat, IV = VIX, θ = 0.40):**

| Contract / time | ATM per unit | ATM per lot |
|---|---|---|
| Nifty 2DTE 09:30 | ₹136 | ₹8,862 |
| Nifty 1DTE 09:30 / 13:00 | ₹107 / ₹96 | ₹6,973 / ₹6,207 |
| Nifty 0DTE 09:30 / 11:00 / 13:00 / 14:30 | ₹66 / ₹58 / ₹44 / ₹29 | ₹4,291 / ₹3,742 / ₹2,839 / ₹1,868 |
| Sensex 1DTE 09:30 | ₹326 | ₹6,527 |
| Sensex 0DTE 09:30 / 11:00 / 13:00 / 14:30 | ₹194 / ₹167 / ₹122 / ₹74 | ₹3,878 / ₹3,336 / ₹2,443 / ₹1,484 |

  So at VIX ≈ 14.7 the model says an ATM lot fits ₹5,000 **only on expiry day**; 1DTE fits only ~0.4–0.9% OTM (Δ 0.23–0.36). If real weekly IVs sit below VIX, 1DTE ATM may fit; check the live chain.
- **[calc] Theta in rupees:** Nifty ATM 0DTE loses ≈₹375/lot per hour at 10:00 and ≈₹597/lot per hour at 13:00 (spot flat); 1DTE ATM ≈₹213/lot per hour at 10:00. A 0.42%-OTM 0DTE call (₹24.7, ₹1,608/lot at 10:00) bleeds −₹304 by 11:00, −₹625 by 12:00, −₹965 by 13:00 if the index does not move. **A −₹500 premium stop on that contract is hit by time decay alone after ~1 h 40 min.**
- Closed form for planning: ATM value ≈ 0.399·F·σ_d·√w, so the fraction left between times t₀ and t₁ on expiry day = √(minutes left at t₁ / minutes left at t₀) with a uniform intraday clock. A U-shaped intraday variance profile (heavier at open/close) would front-load decay in the morning; calibrate u(t) from 1-min data.

### Gaps
- No data-driven Indian study of hour-by-hour premium decay for Tuesday-expiry Nifty or Thursday-expiry Sensex was found; the numbers above are model outputs. Measure: log ATM straddle mid every 5 min on expiry and pre-expiry days, normalise by 9:20 value, condition on |index move| < 0.1%.
- The intraday variance profile (U-shape weights) for Nifty in 2026 has not been measured here (no intraday data in `data/`).

---

## 3. Intraday implied-volatility dynamics, spot–vol relationship, sticky-strike vs sticky-delta, and how to model IV at the stop and target

### Takeaway
Nifty implied vol rises on down moves and falls on up moves, asymmetrically (≈+0.8–1.1 VIX points per 1% fall vs −0.5 per 1% rise), which slightly cushions put buyers and taxes call buyers; but over the 0.1–0.25% index moves this system targets, the spot–vol effect is only ~₹10–40 per lot. The bigger risk is a shift in the *level* of short-dated IV (vega of an ATM 0DTE ≈ ₹270/lot per vol point at 10:00): a 2-point IV drop cuts the 0.42%-OTM target gain from ₹840 to ₹366. Model IV as calibrated level path by DTE/time-of-day + asymmetric spot–vol beta + skew, not constant VIX.

### Cited Findings
- [B: peer-reviewed India, descriptive] Pati, Rajib & Barai (2017, Review of Financial Economics): India VIX moves opposite to Nifty returns in every volatility regime; negative returns move VIX more than positive ones; the asymmetry is stronger in low-vol regimes and weakest for India among the four markets studied — [doi](https://doi.org/10.1016/j.rfe.2017.07.004)
- [B] Badshah (2013, J. Futures Markets): the return–implied-vol relation is negative and asymmetric, and the asymmetry rises toward the upper quantiles, so OLS understates it in extreme moves — [doi](https://doi.org/10.1002/fut.21551)
- [B] Muravyev & Ni: on average, intraday option prices *rise* relative to delta (positive intraday delta-hedged returns, +0.3%/day in the US), i.e. there is no average "IV crush after the open" cost for intraday buyers in the US — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2820264); India: intraday short-option returns negative but insignificant — [Bhat et al.](https://onlinelibrary.wiley.com/doi/10.1002/fut.22512)
- [D] Practitioner claims that IV "collapses continuously" through Nifty expiry day appear in search snippets but give no data; they conflate IV quoted in calendar time with genuine re-pricing (see Section 4).

### Inferences
- **[data] Spot–vol beta, daily, 2018–2026:** ΔVIX = +0.79 pts per 1% Nifty fall, −0.46 per 1% rise (corr(ΔVIX, return) = −0.59); 2025–26: +1.12 / −0.57. In log terms: VIX +3.4% per 1% fall, −2.0% per 1% rise.
- **[calc] Effect at the stop/target** (Nifty 0DTE 22650 call, 0.42% OTM, entry 10:00, barrier hit after 45 min): constant IV −₹590 / +₹840; with spot–vol (+0.9 pts at stop, −0.5 at target) −₹430 / +₹721; with a parallel −2-point IV drop −₹920 / +₹366. For a put buyer the asymmetry is reversed and favourable (IV up on the favourable down move).
- **Recommended IV model for P&L at stop/target:** σ(K, t) = R(DTE, time-of-day) · VIX/√252 · [1 + γ_dn·min(r,0) + γ_up·max(r,0)] · [1 + β₁z + β₂z²], with r = index return since entry (in %), γ_dn ≈ −0.034, γ_up ≈ −0.020 (log-VIX betas above; signs give IV up when r < 0), z = ln(K/F)/σ_ATM,total. Use it with the business-time variance w. Default R = 1, β₁ = β₂ = 0 until calibrated.
- Sticky-strike vs sticky-delta: test on snapshots by regressing ΔIV at a fixed strike on Δln F over 5-min windows; sticky-strike predicts slope ≈ 0, sticky-moneyness predicts slope ≈ −(smile slope)·∂z/∂lnF. For 0.1–0.25% moves the choice changes P&L by tens of rupees at most; the level path R(t) matters far more.

### Gaps
- No published estimate of Nifty/Sensex weekly-option sticky-strike vs sticky-delta behaviour, or of intraday ATM-IV paths on expiry day, was found. Needs the snapshot calibration in Section 4.
- The daily VIX–return betas are a proxy; the intraday beta of 0–1DTE ATM IV may be larger.

---

## 4. How accurate is Black-76 with India VIX for weekly options, and how to calibrate a simple IV surface from live snapshots?

### Takeaway
India VIX is a 30-day, monthly-expiry-based, calendar-time measure, so plugging it into Black-76 for a 0–2-day weekly is a model approximation, not a price. The biggest error is the time clock: with VIX and *calendar* time to 15:30, an ATM 0DTE at 9:30 prices at ~₹35 vs ~₹66 in business time (≈1.9× gap; equivalently the market's calendar-time IV would be ~28%). Use business-time variance, scale by a calibrated ratio R(DTE, time-of-day), add skew, round to ₹0.05 ticks and charge bid-ask, and validate against a few weeks of live chain snapshots.

### Cited Findings
- [C, citing NSE] India VIX uses the best bid-ask quotes of **near- and next-month** Nifty options (CBOE methodology adapted) — [ICICI Direct FAQ](https://www.icicidirect.com/faqs/fno/how-is-india-vix-computed). [D] One search-result summary claimed weekly cycles are used; I could not verify it, and the NSE white paper ([PDF](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/white_paper_IndiaVIX.pdf)) timed out.
- [B] Agarwalla, Varma & Virmani (2021, JFM): India VIX follows CBOE methodology with amendments; in 2020 ATM implied vol and India VIX moved together and led EWMA volatility — [doi](https://doi.org/10.1002/fut.22240)
- [B−] Bandi et al. (2026): ultra-short ATM term structures oscillate and are hard for standard models; calendar vs business time changes implied vols — [arXiv 2603.29430](https://arxiv.org/abs/2603.29430); [B] Bandi, Fusari & Renò: skewness/kurtosis corrections materially improve 0DTE pricing over standard models — [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4503344)

### Inferences
- **[data] Implied vs realised:** realised open→close s.d. divided by VIX-implied daily s.d. = 0.80 (2015–26), 0.75 (2024–26), 0.69 (since Sep 2025). Realised close→close s.d. ≈ VIX-implied on average (1.03% vs 1.04%), so the "overpricing" shows up mainly in the intraday leg relative to a naïve VIX/√252 split.
- **[calc] Calendar-time pitfall:** ATM ≈ 0.399·F·σ·√T. Calendar T (6 h/8,760 h) gives ₹34.5 at 9:30 on expiry day vs ₹66 with business time. A backtest using VIX + calendar T would understate entry cost and overstate leverage on 0DTE by ~2×.
- **Calibration recipe (2–4 weeks of snapshots):**
  1. Every 5 min, 9:20–15:20, store per expiry (this and next weekly, Nifty and Sensex) and strike within ±3%: bid, ask, LTP, bid/ask qty, OI, volume, timestamp, spot, near future, VIX.
  2. Forward from put–call parity at the two strikes nearest spot: F = K + (C_mid − P_mid).
  3. Implied total s.d. per strike by inverting Black-76 on the mid; convert to business-time σ_d = σ_total/√w.
  4. Per snapshot fit σ_total(z) = a(1 + β₁z + β₂z²), z = ln(K/F)/a, OTM quotes only, weighted by 1/spread.
  5. Level ratio R = a / (VIX/√252·√w); tabulate the median R by (expiry, DTE 0/1/2/3+, 30-min time bucket) and its regression on VIX level; tabulate median β₁, β₂ by DTE.
  6. Quick check for the level: implied remaining s.d. ≈ ATM straddle mid / (0.798·F) (from ATM ≈ 0.399·F·σ√T per leg).
  7. Spreads: model half-spread in ticks as a function of (premium, |z|, DTE, time bucket, index).
  8. Validation: price the strikes the picker would have chosen with the fitted model and compare to the real mid. Target median absolute error < ₹0.5/unit Nifty (≈₹33/lot) and < ₹1.5/unit Sensex (≈₹30/lot); report bias by time bucket.
- Rounding: model prices should be rounded to the exchange tick before costs (I believe ₹0.05 for NSE index options; see Gaps).

### Gaps
- No published accuracy test of "Black-76 + India VIX" on Indian weekly options was found; the error size must be measured as above.
- Tick sizes for NSE and BSE index options, and the current India VIX expiry-selection rule, were not verified this session.

---

## 5. Bid-ask spreads, slippage and liquidity: Nifty vs Sensex weeklies (2025–2026), and impact cost for one lot

### Takeaway
BSE's Sensex options have taken a large share of premium turnover (NSE share fell to ~68% in Apr–Jun 2026). Practitioner reports say near-ATM Sensex weeklies are liquid, especially on expiry day, but liquidity thins faster away from ATM. One lot is tiny relative to displayed depth near ATM, so impact cost ≈ half the quoted spread. Per lot, one Nifty tick (₹0.05 × 65 = ₹3.25 a side) costs more than one Sensex tick (₹0.05 × 20 = ₹1), but Sensex quotes are usually several ticks wide. Measure both from your own snapshots before choosing a default.

### Cited Findings
- [C, citing NSE's IPO prospectus] NSE's share of equity-options premium turnover: 96.86% (FY24) → 87.43% (FY25) → 74.71% (FY26) → **68.48% (Apr–Jun 2026)** — [Multibagg](https://www.multibagg.ai/market-pulse/articles/nse-options-premium-share-falls-rhp-cmu8gzs5m0071y6pi1worz0aj)
- [C] Sensex near-ATM weekly strikes are "genuinely liquid", especially on expiry day, but spreads widen faster than Nifty's as you move OTM; Sensex strikes are 100 points apart vs Nifty's 50 (similar in % terms) — [Sahi blog](https://www.sahi.com/blogs/nse-vs-bse-expiry-shake-up-what-traders)
- [B] US analogue: effective spreads roughly double in the final hour (10.5% vs 4.5% of mid for 3–24 h) and explode beyond 2% OTM (45–80% of mid); buys pay more than sells (8.4% vs 5.2%) because market makers are short 0DTE gamma — [Beckmeyer et al.](https://wp.lancs.ac.uk/fofi2024/files/2024/04/FoFI-2024-146-Leander-Gayda.pdf)
- [O] Market orders are risky in thin option books: NSE removed SL-M orders for options after freak trades (Section 6).

### Inferences
- **[calc] Round-trip spread cost per lot** = 2 × half-spread × lot. Nifty: 1 tick ₹6.5, ₹0.25 ₹32.5, ₹0.50 ₹65, ₹1.00 ₹130. Sensex: 1 tick ₹2, ₹0.25 ₹10, ₹0.50 ₹20, ₹1.00 ₹40. One tick is 0.083% of a ₹60 Nifty premium vs 0.025% of a ₹200 Sensex premium, so at equal *tick* spreads Sensex is cheaper per lot; at equal *percentage* spreads they cost the same.
- Spread cost is the same size as the fixed charges (~₹57; Section 10). Spread data should therefore decide between Nifty and Sensex on any given day.
- Default backtest assumptions until measured (placeholders, deliberately conservative): Nifty half-spread ₹0.10 for premium < ₹50 and ₹0.20 above; Sensex ₹0.50; ×2 before 9:30 and after 14:45; ×3 on stop exits in fast markets.

### Gaps
- I found no 2025–26 quantitative study of quoted or effective spreads for Nifty vs Sensex weeklies by moneyness and time, and no exchange-published impact cost for index options. This is the most important unmeasured cost input; collect it with the snapshot logger.

---

## 6. Stop-loss mechanics: underlying vs premium stops, SL-limit behaviour on NSE/BSE, and whether stops help buyers

### Takeaway
SL-market orders are banned for options on NSE (since 27 Sep 2021) and BSE (since 9 Oct 2023), so only SL-limit orders exist, and they can fail to fill in a gap. Theory says stops lower expected return under a random walk and help only when returns trend after the stop. For an option buyer, a premium stop mixes direction with theta, IV and spread noise. Use the **index (or future) level as the primary stop**, a broker-side **SL-limit premium stop as a catastrophe backstop**, and a **time stop**. A 0.11% index stop sits inside normal noise: the index moves 0.11% against the open on ~85% of days.

### Cited Findings
- [O/C] NSE discontinued SL-M orders for index and stock options from 27 Sep 2021 (circular NSE/FAOP/49677) after freak trades; such orders are rejected — [Angel One](https://www.angelone.in/announcements/market/sl-m-orders-for-options-to-be-discontinued-by-nse), [Zerodha bulletin](https://zerodha.com/marketintel/bulletin/305785/stop-loss-market-sl-m-orders-blocked-for-index-options)
- [O/C] BSE discontinued SL-M orders from 9 Oct 2023 — [Business Standard](https://www.business-standard.com/markets/news/bse-to-discontinue-stop-loss-market-orders-from-oct-9-to-check-freak-trades-123092200889_1.html)
- [C] Workaround: an SL-limit order with the limit set well beyond the trigger behaves like SL-M while still protecting against freak prints — [Zerodha support](https://support.zerodha.com/category/trading-and-markets/charts-and-orders/order/articles/how-to-use-sl-l-order-like-a-sl-m-order)
- [B] Kaminski & Lo (2014, J. Financial Markets): under a random walk, simple stop-loss rules always reduce expected return; they add value only with momentum (50–100 bp/month in stop-out periods, 1950–2004) and do not help mean-reversion strategies — [MIT open access](https://dspace.mit.edu/bitstream/handle/1721.1/114876/Lo_When%20Do%20Stop-Loss.pdf)
- [B] Market-maker gamma regime matters: positive dealer gamma strengthens intraday reversal (stops get run, then price reverts); negative gamma strengthens momentum (stops help) — [Dim, Eraker & Vilkov](https://dx.doi.org/10.2139/ssrn.4692190)

### Inferences
- **[data] Noise vs stop size** (open-anchored, 2024–2026, 671 days): median day range 0.84%; median max up-excursion 0.34%, down-excursion 0.40%; P(down-excursion ≥ 0.11%) = 0.85, P(up-excursion ≥ 0.23%) = 0.63, both 0.48. A 0.11% stop is therefore an "is the timing right in the next ~20 minutes" stop, not a "the forecast is wrong" stop.
- **[calc] Expected time to resolution** of a ±barrier pair under driftless Brownian motion: E[τ] = a·b/σ² → with a = 0.23%, b = 0.11%, σ = 0.65%/day: 0.06 day ≈ **22 minutes**. Manual execution after an alert (30–90 s latency) is a meaningful fraction of the trade's life. Budget 2–3 extra ticks of slippage on stop exits.
- **Why not stop on premium:** a 0.42%-OTM 0DTE call loses ₹300/lot per hour from theta at a flat index, and a 1-vol-point IV change moves an ATM 0DTE ~₹270/lot. A premium stop fires on time or IV, not on the forecast being wrong. But an index stop leaves the rupee loss uncertain, so keep a hard premium backstop sized at the ₹500 cap plus slippage.
- **SL-limit placement:** for a long option, trigger = entry − (₹550/lot ÷ lot) (₹8.5/unit Nifty, ₹27.5/unit Sensex); limit = trigger − max(10% of premium, 5 ticks), so it still fills in a fast move. Re-check that the limit is inside the exchange's price-protection band.

### Gaps
- No study found on stop-loss efficacy for *option buyers* specifically, or on SL-limit non-fill rates in Indian index options.
- Not verified: whether Angel One supports index-level-triggered (GTT/conditional) orders on options. If not, the primary index stop must be executed manually from an alert.
- Exchange limit-price-protection band widths for options were not verified this session.

---

## 7. Expected-value strike selection: probability of target before stop, implied vs model probabilities, and the optimal delta

### Takeaway
With fixed index barriers (target +a, stop −b), P(target first) under driftless Brownian motion is b/(a+b), whatever the volatility or the implied distribution. Only the forecast's drift moves it. For a = 0.23%, b = 0.11% the no-edge probability is 0.324. The forecast must lift it to ≈0.40–0.42 before any 0DTE/1DTE strike shows positive EV after ₹57 charges plus spread. For a given edge, EV rises toward ATM (fixed per-lot costs, better gain/loss ratio), so the best strike is the **highest-delta (closest to ATM) strike that still meets the ₹500 loss cap**. Deep OTM (Δ < 0.2) is negative-EV at every edge level tested.

### Cited Findings
- [B] Short-horizon option P&L is driven by realised skewness/direction rather than variance alone, so the direction forecast is the source of edge — [Vilkov](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4641356)
- [B] Retail losses concentrate in single-leg debit positions and high-IV contracts; ATM spreads are smallest — [Beckmeyer et al.](https://wp.lancs.ac.uk/fofi2024/files/2024/04/FoFI-2024-146-Leander-Gayda.pdf)
- [B−] Indian retail favour ATM/slightly OTM near expiry; far-OTM returns are lottery-like (skewness 7.5–18) — [Agarwal et al.](https://www.fma.org/assets/docs/Derivatives2025/Zhao.pdf)

### Inferences
- **Barrier formula** for X_t = μt + σW_t, starting at 0, barriers +a and −b; k = 2μ/σ²:
  P(hit +a first) = (1 − e^{k·b}) / (e^{−k·a} − e^{k·b}); for μ = 0 this reduces to b/(a+b). E[τ | μ=0] = a·b/σ². With a deadline T, use Monte Carlo, or check that σ√T ≫ a+b (true for full-session holds: σ ≈ 0.65%/day vs a+b = 0.34%).
- **[calc] Forecast accuracy → barrier probability** (σ_intraday = 0.65%/day, 1-hour horizon accuracy converted to drift):

| 1-h direction accuracy | implied drift | P(+0.23% before −0.11%) | P(+0.20% before −0.20%) |
|---|---|---|---|
| 0.53 | 0.12%/day | 0.345 | 0.529 |
| 0.55 | 0.20%/day | 0.360 | 0.548 |
| 0.60 | 0.41%/day | 0.398 | 0.596 |
| 0.65 | 0.63%/day | 0.438 | 0.644 |
| 0.70 | 0.85%/day | 0.480 | 0.691 |

  The model should be trained and calibrated directly on the label "which barrier is hit first by the deadline", not on close-to-close direction.
- **[calc] Monte Carlo EV per trade** (20k paths, 1-min steps, realised intraday σ = 0.65%/day, Black-76 business-time pricing at IV = VIX, half-spread ₹0.05 each side, ₹57 charges; Nifty calls; entry 10:00; forced exit 15:00 for 0DTE or 15:10 for 1DTE; timeouts <1%):

| Nifty 0DTE strike (cost/lot) | net P&L at stop | net P&L at target | EV, no drift (p=.34) | EV, drift 0.2%/d (p=.38) | EV, drift 0.4%/d (p=.42) |
|---|---|---|---|---|---|
| 22550 ATM (₹4,117) | −1,119 | +1,881 | −92 | +34 | +153 |
| 22600 (₹2,660) | −861 | +1,383 | −92 | +3 | +92 |
| 22650, 0.42% OTM (₹1,608) | −620 | +930 | −89 | −23 | +39 |
| 22700 (₹905) | −420 | +563 | −83 | −41 | −2 |
| 22750 (₹473) | −273 | +297 | −77 | −53 | −30 |

  1DTE (entry 10:00) at drift 0.4%/day: 22650 (₹4,073) EV +105; 22700 +71; 22750 +41; 22800 +15; 22850 −6; deeper strikes negative.
- **The user's constraint set is nearly empty at 0.11%/0.23% barriers.** [calc] With entry at 10:00 and the barrier hit after 45 min, no 0DTE Nifty strike has both stop-loss ≤ ₹500 and target-gain ≥ ₹800 (22650: −590/+840; 22700: −388/+514). Sensex 0DTE: 72700 −563/+796; 72800 −436/+589. 1DTE: 22700 −570/+949; 22750 −456/+740. The reason: index ratio a/b = 2.09 translates to an option gain/loss ratio of only 1.4–1.7 after theta. **To get ₹800 vs ₹500 (ratio 1.6) after costs, the index target/stop ratio must be ≈ 2.3–2.6** (e.g. stop 0.10%, target 0.25%). That pushes the no-edge hit probability down to 0.29, so the forecast must supply more edge.
- **Optimal delta:** with fixed per-lot costs c and option gain/loss G_K, L_K, EV_K = p·G_K − (1−p)·L_K − c, and G_K/L_K rises toward ATM. So with any positive edge, EV is maximised at the highest delta the loss cap allows. In practice that is Δ ≈ 0.27–0.40 at 0DTE and Δ ≈ 0.25–0.36 at 1DTE for b ≈ 0.10–0.12%. Below Δ ≈ 0.2, fixed costs dominate and EV is negative at every edge tested.
- **Implied vs model probabilities:** under the risk-neutral measure the intraday drift is ≈0, so the market-implied P(target first) ≈ b/(a+b), the same as the no-edge case. The volatility risk premium changes the time to hit and theta, not this ratio. The edge test is therefore: calibrated p − b/(a+b) > cost hurdle. The hurdle is ≈ +0.07 to +0.09 for 0DTE near-ATM strikes in the MC above.

### Gaps
- The MC assumes Brownian index paths with constant σ, IV = VIX and uniform intraday variance. Real paths have jumps, intraday momentum/reversal (gamma regimes) and IV level drift. Re-run the EV table with the calibrated surface and with bootstrapped 1-min Nifty paths.
- No practitioner or academic framework specific to Indian weeklies for "optimal delta given forecast edge" was found; the above is derived.

---

## 8. Are defined-risk debit spreads feasible within ₹5,000 for one Nifty or Sensex lot, and do they improve expectancy?

### Takeaway
They are not feasible. The short leg of any spread attracts SPAN plus an exposure margin of about 2% of notional (≈₹29k for one Nifty or Sensex lot), plus another 2% extreme-loss margin on expiry day, even though the spread's maximum loss is just the debit. Reported spread margins are ₹14k–40k. US evidence says spreads have better median returns than naked buys, but that benefit is out of reach until capital is roughly ₹40–75k.

### Cited Findings
- [C] Exposure margin on short index options = 2% of contract value (spot × lot); NSE Clearing calls it Extreme Loss Margin; an additional 2% ELM applies to short index options on their expiry day — [INDmoney](https://www.indmoney.com/learn/fno/span-and-exposure-margin), [OneTradeJournal](https://onetradejournal.com/glossary/span-margin); [O] expiry-day +2% ELM since Nov 2024 — [SEBI rules summary in note 01 / Zerodha](https://zerodha.com/z-connect/business-updates/sebis-new-rules-for-index-derivatives-heres-whats-changing)
- [D] Zerodha user report (Oct 2024, lot 25 era): ~₹14,000 margin for a Nifty call spread whose maximum risk was ₹1,250, vs ~₹42,000 for the naked short; the reason given is that a trader could break the hedge by exiting the long leg — [TradingQnA](https://tradingqna.com/t/margin-required-on-call-spreads-looks-too-high/174263)
- [C] Search-result summaries cite ₹28,000–40,000 for a Nifty bull call spread vs ~₹1.25 lakh naked — [Angel One margin calculator page (search set)](https://www.angelone.in/calculators/margin-calculator). Some explainers instead claim the margin is "net premium plus a small buffer" — [Groww](https://groww.in/p/bull-call-spread). The conflict is noted; the exposure-margin rule makes the second claim implausible in 2026.
- [B] US 0DTE retail: put/call spreads have median margin-adjusted return +3.0%/+3.3% vs −0.7%/−0.8% for single legs; the Complex coefficient is +0.17% per trade — [Beckmeyer et al.](https://wp.lancs.ac.uk/fofi2024/files/2024/04/FoFI-2024-146-Leander-Gayda.pdf)

### Inferences
- [calc] Exposure margin alone on one short leg: Nifty 22,555.75 × 65 × 2% = ₹29,322; Sensex 72,382 × 20 × 2% = ₹28,953; on expiry day roughly double (my inference: the +2% ELM applies to the short leg even when hedged). Even with full SPAN offset, the requirement is ~6× the ₹5,000 capital.
- Spreads also pay two legs of costs (≈₹40 more brokerage + GST + a second spread) per round trip; at ₹5k the extra ~₹50–70 alone would eat most of the expectancy shown in Section 7.
- Revisit spreads when capital ≥ ~₹50k (after the margin is confirmed in Angel One's calculator). The long leg must always be entered first to get the hedge benefit.

### Gaps
- No 2026 Angel One margin-calculator output for a 1-lot Nifty/Sensex debit spread was retrieved (the calculator is interactive). Get a screenshot for a 100-point Nifty call spread on a non-expiry day and on expiry day.

---

## 9. Sizing with 1-lot granularity: when to skip, and Kelly when only 0 or 1 lot is possible

### Takeaway
With ₹5,000 and a ₹500 stop, every trade risks 10–12% of capital. That is above full Kelly unless the calibrated hit probability is ≳0.45 at a net gain/loss ratio of ~1.5. Below that, the strategy can have positive EV and still shrink capital geometrically. The only sizing lever is the 0/1 decision, so the skip rules carry all the risk control.

### Cited Findings
- [O] Indian option buyers pay the full premium upfront (since Feb 2025), so maximum loss per trade is the premium plus costs; nothing larger is possible — [note 01, Zerodha summary of SEBI rules](https://zerodha.com/z-connect/business-updates/sebis-new-rules-for-index-derivatives-heres-whats-changing)
- [O] SEBI: loss incidence rises with turnover, from ~86% to ~95% for the highest-turnover individuals, so frequency control matters — [SEBI FY26 study](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf)

### Inferences
- **Kelly for a binary trade:** f* = p − (1−p)/R, with R = G/L net of costs. Actual fraction risked f = L/C. Log-growth per trade g = p·ln(1 + G/C) + (1−p)·ln(1 − L/C).
- **[calc] Capital ₹5,000:**

| p | G/L (net) | EV/trade | Kelly f* (₹ risk) | actual f | log-growth/trade |
|---|---|---|---|---|---|
| 0.40 | 900/550 | +₹30 | 0.033 (₹167) | 0.110 | −0.0037 (shrinks) |
| 0.42 | 936/619 | +₹34 | 0.036 (₹182) | 0.124 | −0.0046 (shrinks) |
| 0.42 | 900/550 | +₹59 | 0.066 (₹328) | 0.110 | +0.0019 |
| 0.45 | 900/550 | +₹102 | 0.114 (₹569) | 0.110 | +0.0104 |
| 0.50 | 900/550 | +₹175 | 0.194 (₹972) | 0.110 | +0.0245 |
| 0.42 | 1200/500 | +₹214 | 0.178 (₹892) | 0.100 | +0.0292 |

- **[calc] Ruin simulation** (fixed +₹900/−₹550 net, ruin = capital < ₹2,500, i.e. can no longer buy a Δ≈0.3 lot; 100 trades): P(ruin) 0.57 at p = 0.40, 0.46 at 0.42, 0.31 at 0.45, 0.14 at 0.50.
- **Skip rules:**
  1. Δ_max that fits the cap: Δ_max ≈ (₹500 − theta to expected hit − slippage) / (lot × S × b). At b = 0.11%, Nifty: (500 − ~100)/(65 × 24.8) ≈ 0.25. If the forecast's natural stop b needs Δ < 0.25 (0DTE) or < 0.2 (1DTE+), skip. That is roughly b > 0.13% at 0DTE or b > 0.17% at 1DTE.
  2. Skip unless calibrated p satisfies f* ≥ L/C (no over-betting). At R ≈ 1.5 and L/C = 0.10, that needs p ≥ 0.46; at R ≈ 2.4 (e.g. stop 0.10%, target 0.25%), p ≥ 0.36.
  3. Skip if modelled EV < ₹75 (1.5% of capital) after costs and spread, so model error does not turn the trade negative.
  4. After a 30% drawdown (capital < ₹3,500), halt live trading and re-validate the calibration; the 1-lot constraint means the system cannot de-risk any other way.

### Gaps
- Kelly inputs (p, G, L) are model estimates. Shrink p toward b/(a+b) in proportion to calibration uncertainty, e.g. use the lower 80% bound from a reliability curve built on ≥200 out-of-sample signals.

---

## 10. Exact 2026 cost model for one round trip at Angel One, with worked examples

### Takeaway
One round trip of one lot costs about **₹56–58** in fixed and statutory charges for both Nifty and Sensex at ~₹4,000 premium. Brokerage plus its GST (₹47.2) is ~83% of that. STT at 0.15% of the sell premium adds ₹5–7. Add the bid-ask spread (₹6.5–₹65 per Nifty lot round trip; ₹2–₹40 for Sensex) and stop slippage. The ₹57 alone is 1.1% of capital and about 11% of the ₹500 risk per trade.

### Cited Findings
- [O/C] Angel One: brokerage ₹20 per executed order for F&O (₹0 up to ₹500 for the first 30 days); NSE options exchange transaction charge 0.0355299% of premium (buy and sell); BSE Sensex/Bankex options 0.0325% (Sensex 50 and stock options 0.0050%); SEBI fee ₹10/crore; stamp duty 0.003% of premium, buy side only; GST 18%; IPFT listed as 0.002%; no DP or clearing charges — [Angel One charges page](https://www.angelone.in/exchange-transaction-charges)
- [O/C] Zerodha schedule (same exchange levies): NSE 0.03553% of premium; BSE 0.0325%; STT 0.15% of premium on the sell side, and 0.15% of intrinsic value on options bought and exercised; SEBI ₹10/crore; stamp 0.003% (₹300/crore) on buy; GST 18% on brokerage + SEBI + transaction charges — [Zerodha charges](https://zerodha.com/charges/)
- [O/C] STT on options sale raised to 0.15% (from 0.10%) and on exercise to 0.15% from 1 Apr 2026 — [ICICI Direct](https://www.icicidirect.com/futures-and-options/articles/stt-changes-in-budget-2026-what-f-o-traders-need-to-know), [ClearTax](https://cleartax.in/s/securities-transaction-tax-stt)

### Inferences
- **Formula** (B = buy premium × qty, S = sell premium × qty):
  - Brokerage = ₹20 × 2
  - STT = round(0.0015 × S)
  - Exchange = r_ex × (B + S), with r_ex = 0.0003553 (NSE) or 0.000325 (BSE Sensex)
  - SEBI = 1e-6 × (B + S)
  - Stamp = 0.00003 × B
  - GST = 0.18 × (brokerage + exchange + SEBI)
  - Total = sum of the above, plus spread cost 2·h·qty and stop slippage.
- **[calc] Nifty, 65 × ₹60 (B = ₹3,900):**

| Exit | Brokerage | STT | Exchange | SEBI | Stamp | GST | **Total** |
|---|---|---|---|---|---|---|---|
| ₹60 (flat) | 40.00 | 6 | 2.77 | 0.01 | 0.12 | 7.70 | **₹56.60** |
| ₹74 (target, +₹910 gross) | 40.00 | 7 | 3.09 | 0.01 | 0.12 | 7.76 | **₹57.98** |
| ₹52 (stop, −₹520 gross) | 40.00 | 5 | 2.59 | 0.01 | 0.12 | 7.67 | **₹55.38** |

  Spread on top at 1 tick each side: ₹6.5, so all-in ≈ ₹63 (1.6% of premium). Break-even option move = 63/65 ≈ ₹0.97/unit ≈ 4.3 Nifty points at Δ 0.22, or 3.0 points at Δ 0.33.
- **[calc] Sensex, 20 × ₹200 (B = ₹4,000):**

| Exit | Brokerage | STT | Exchange | SEBI | Stamp | GST | **Total** |
|---|---|---|---|---|---|---|---|
| ₹200 (flat) | 40.00 | 6 | 2.60 | 0.01 | 0.12 | 7.67 | **₹56.40** |
| ₹245 (+₹900 gross) | 40.00 | 7 | 2.89 | 0.01 | 0.12 | 7.72 | **₹57.74** |

  Spread at ₹0.50 half-spread each side: +₹20, so all-in ≈ ₹76.
- Budget rule: premium × lot ≤ ₹5,000 − ₹60 (charges) − buffer for the exit spread, so premium ≤ ~₹75/unit (Nifty) or ≤ ~₹245/unit (Sensex).
- Never let a long ITM option go to settlement: exercise STT (0.15% of intrinsic) is small now, but closing-auction settlement risk (3:15–3:35 PM CAS since 3 Aug 2026) is not.

### Gaps
- IPFT treatment conflicts (Angel lists 0.002%; Zerodha appears to fold it into 0.03553%). The impact is under ₹0.20 per round trip.
- Whether Angel One counts a partially filled order as one executed order (₹20) was not verified. Check a contract note.
- Exchange charges change often; recheck NSE/BSE circulars quarterly.

---

## 11. Synthesis: recommended strike/expiry/exit algorithm with default parameters and cost model

### Takeaway
Only take near-ATM (Δ 0.25–0.55), same-day, intraday trades on the cheapest-to-carry expiry that fits the budget. Use index-level barriers with target/stop ratio ≥ 2.3, a calibrated barrier-hit probability that clears the Kelly and EV hurdles, a hard premium backstop and time stops, and exit by 15:00 on expiry day. Expect most days to be "no trade".

### Cited Findings
- Same-day exit and no overnight holding — [Bhat et al.](https://onlinelibrary.wiley.com/doi/10.1002/fut.22512), [Agarwal et al.](https://www.fma.org/assets/docs/Derivatives2025/Zhao.pdf), [Muravyev & Ni](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2820264)
- Avoid far OTM and the final hour; prefer ATM; costs dominate retail 0DTE losses — [Beckmeyer et al.](https://wp.lancs.ac.uk/fofi2024/files/2024/04/FoFI-2024-146-Leander-Gayda.pdf)
- Unconditional 0DTE strategies do not survive realistic costs — [Vilkov repo correction](https://github.com/vilkovgr/0dte-strategies)
- Closing auction 3:15–3:35 PM on expiry day; options trade to 3:40; auction-period premium spikes have occurred (3 Sep 2026) — [MarketsEasy, via note 01](https://marketseasy.in/blog/sebi-expiry-settlement-price-cas-review-2026)
- SL-M not available; use SL-limit — [Zerodha bulletin](https://zerodha.com/marketintel/bulletin/305785/stop-loss-market-sl-m-orders-blocked-for-index-options)

### Inferences

**A. Weekly calendar (which contract is affordable near ATM at VIX ≈ 15; [calc])**

| Day | Nifty (Tue expiry) | Sensex (Thu expiry) | Default candidate |
|---|---|---|---|
| Mon | 1DTE: 0.4–0.9% OTM (Δ 0.23–0.36) | 3DTE: far OTM only | Nifty 1DTE |
| Tue | 0DTE: ATM fits (₹3.7–4.3k before 11:00) | 2DTE: far OTM | Nifty 0DTE |
| Wed | next week (6DTE): far OTM | 1DTE: 0.3–0.7% OTM (Δ 0.27–0.40) | Sensex 1DTE |
| Thu | 5DTE: far OTM | 0DTE: ATM fits | Sensex 0DTE |
| Fri | 2 sessions + weekend: 0.6–1.1% OTM (Δ 0.23–0.33) | next week: far OTM | Nifty (Tue), or skip |

**B. Algorithm (run at every signal; defaults in brackets)**

1. **Session gates:** no entries before [09:45], after [13:30] on 0DTE, or after [14:30] otherwise. Skip the first 15 minutes after scheduled macro events. Skip if VIX has moved more than [±8%] intraday (IV-level risk).
2. **Forecast inputs:** direction d; index stop distance b and target a from the model/structure, with **a/b ≥ [2.3]** and b ∈ [0.08%, 0.15%]; calibrated **p = P(target before stop before deadline)**; deadline = min(entry + [90] min, 15:00 on expiry day / 15:10 otherwise).
3. **Candidates:** Nifty and Sensex; this and next weekly expiry; calls if d = up, puts if d = down; strikes from ATM to [1.5%] OTM, plus 1 strike ITM.
4. **Price each candidate** with the calibrated model: business-time variance w (θ = [0.40]), level ratio R(DTE, time bucket) [default 1.0], smile (β₁, β₂) [default 0], asymmetric spot–vol (γ_dn = [−0.034], γ_up = [−0.020] per 1% move), Black-76, rounded to ₹0.05. Live: entry = ask; backtest: entry = model mid + h.
5. **Rupee outcomes per lot,** evaluated at the expected hitting time (E[τ] = a·b/σ² with σ = realised intraday σ [0.65%/day], or by MC):
   - L_K = (V_K(stop) − entry) × lot − 3h × lot − C_fixed
   - G_K = (V_K(target) − entry) × lot − h × lot − C_fixed
   - M_K = mark-to-market at the deadline (MC)
   - C_fixed = ₹57
6. **Hard filters:**
   - entry × lot + ₹60 ≤ ₹5,000
   - **|L_K| ≤ ₹500**
   - G_K/|L_K| ≥ [1.5]
   - Δ ∈ [0.25, 0.55]
   - quoted spread ≤ max(2 ticks, 1.5% of mid) for Nifty, ≤ max(4 ticks, 2%) for Sensex
   - bid and ask qty each ≥ 5 lots; strike OI in the top 10 for that expiry
7. **Score:**
   - EV_K = p·G_K + (1 − p − p₀)·L_K + p₀·M_K
   - keep only EV_K ≥ [₹75] **and** Kelly f* = p − (1 − p)·|L_K|/G_K ≥ |L_K|/₹capital
   - choose the max EV_K
   - tie-break: tighter spread (in ₹ per lot), then Nifty
   - if nothing survives: **NO TRADE**
8. **Order entry (manual, Angel One):** limit at mid + 1 tick, or at the ask if the spread is ≤ 2 ticks; cancel if unfilled after [60] s and re-evaluate (do not chase more than 2 ticks).
9. **Immediately after the fill:** place an SL-limit catastrophe stop with trigger = entry − ₹550/lot ÷ lot and limit = trigger − max(10% of premium, 5 ticks). Place a resting sell limit at the target premium V_K(target) − 1 tick.
10. **Exits (whichever comes first):**
    - (a) index touches the stop level → sell at bid − 2 ticks (marketable limit)
    - (b) index touches the target level → sell, or let the resting limit fill
    - (c) time stop: deadline reached, or after [45] min the index is within ±0.05% of entry → exit (theta is ₹300–600/lot per hour near expiry)
    - (d) hard exit [15:00] on expiry day (before the 15:15 CAS), [15:10] otherwise
    - (e) never hold overnight
11. **Frequency cap:** ≤ [1] trade per day and ≤ [3] per week while capital < ₹10k. Stop for the day after one stop-out.
12. **Logging for recalibration:** log the signal, p, chosen K, quotes, fill, exit reason, and model-vs-real premium at entry, stop and target. Refit R, β, h and θ monthly, and the p-calibration (reliability curve) every 50 trades.

**C. Backtest cost/fill model (defaults)**
- Fixed charges: per Section 10 formula (≈₹56–58 per round trip).
- Half-spread h: Nifty ₹0.10 (<₹50 premium) / ₹0.20 (≥₹50); Sensex ₹0.50; ×2 before 09:30 and after 14:45. Stop exits pay 3h; target exits h. Replace with snapshot-measured values.
- Latency: alert → fill delay [60] s; evaluate the fill at the index price 60 s after the trigger.
- Option prices: model output rounded to ₹0.05, floored at ₹0.05.
- Validation gate before going live: on ≥ 2 weeks of real chain snapshots, the median model error at the chosen strikes must be < ₹35/lot and the backtest P&L must be re-run with the real quotes.

**D. What the numbers imply for the project**
- With 0.11%/0.23% barriers, a ₹500/₹800 rule finds almost no strike; switch to a ratio rule (G/L ≥ 1.5 net) and target/stop ≥ 2.3.
- The forecast must raise P(target first) by ≈ +0.07 to +0.12 over b/(a+b) (e.g. from 0.32 to ≥ 0.42–0.45) before trades are both positive-EV and not over-betting. A 55% hourly directional hit rate is far from enough; ≈ 65% is about the minimum at these barriers.

### Gaps
- All defaults marked [ ] are starting values from model arithmetic, not optimised or out-of-sample tested. The spread and IV-surface parameters are the least certain inputs and must come from the snapshot logger.
- No Grade-A study exists for this exact strategy (intraday long Nifty/Sensex weeklies with a directional model, net of 2026 costs); the project's own forward test is the only way to get one.
