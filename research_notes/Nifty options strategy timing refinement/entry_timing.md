# Entry timing for intraday long-option trades on Nifty 50 and Sensex weeklies: when in the session, and how

Scope: when during the 09:15–15:30 session, and with what order technique, to enter a single long Nifty (lot 65, Tuesday expiry) or Sensex (lot 20, Thursday expiry) weekly option so that timing adds edge or cuts cost. This builds on, and does not repeat, [intraday_technical_regime.md](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md), [04_nifty_measured_facts.md](../04_nifty_measured_facts.md) and the spread/theta/IV work in [option_trade_construction.md](../Nifty%20options%20multifactor%20quant%20strategy/option_trade_construction.md).

**Evidence grades (this note):** **A** = peer-reviewed + India + robust; **B** = peer-reviewed but not India, or not robustness-tested; **C** = practitioner work or our own descriptive measurement; **D** = anecdote. "Pre-2024" marks results whose samples predate the Nov 2024 SEBI F&O changes, the 1 Sep 2025 Tuesday-expiry switch and the 3 Aug 2026 closing auction.

**Our measurements.** [fetch_intraday_yf.py](fetch_intraday_yf.py) caches Yahoo spot-index bars to `data/intraday_yf/` (git-ignored; Yahoo history rolls off, so re-run it weekly to build an archive). [entry_timing_measurements.py](entry_timing_measurements.py) produces [entry_timing_measurements_output.txt](entry_timing_measurements_output.txt). Section IDs such as "A5" below point into that output.
- 60-minute bars, 3 Nov 2023 – 16 Oct 2026, 722 sessions. Split into P1 (Thursday Nifty expiry, 447 sessions), P2 (Tuesday expiry, Sep 2025 – Jul 2026, 222) and P3 (after the closing auction started, Aug–Oct 2026, 53).
- 5-minute bars for the last ~60 sessions (23 Jul – 16 Oct 2026); 1-minute bars for the last 19 sessions; daily Nifty 2014–2026.
- Caveats: spot index, not futures; no index volume; no option quotes. Results are in-sample and descriptive (grade C). t-stats use i.i.d. errors across days.

**Units.** Moves are in basis points (bp) of the index. At Oct 2026 levels (Nifty ≈ 23,900, Sensex ≈ 76,400), **1 index bp ≈ ₹75–80 per lot for an ATM option (delta 0.5)** in both contracts. So the ₹400 risk budget is only about **5 bp of index** at delta 0.5 (about 12 Nifty or 39 Sensex points). That makes entry slippage and delay first-order issues.

**Expiry-day calendar used.**
- Nifty weekly expiry: Thursday until Aug 2025, Tuesday from 1 Sep 2025 ([01](../01_market_structure_2026.md)).
- Sensex weekly expiry: Friday until Dec 2024, Tuesday from 1 Jan 2025 ([Angel One](https://www.angelone.in/news/market-updates/bse-revised-expiry-days-for-sensex-bankex-and-sensex-index-derivatives)), Thursday from 4 Sep 2025 ([Sahi](https://blogs.sahi.com/p/nse-vs-bse-expiry-shake-up-what-traders); the exact cut-over date differs between secondary sources).
- Holidays move expiry to the previous trading day.

**Search limitation.** The Wiley Scholar Gateway quota was exhausted (it resets 1 Nov 2026), so peer-reviewed discovery relied on web search, RePEc/SSRN abstracts, alphaXiv and PDFs I could read in full.

---

## 1. Intraday seasonality in Indian index markets: U-shape, the opening, lunch, the last hour, expiry days, and the 2025–2026 rule changes

### Takeaway
- **Shape (robust, A).** Volatility and volume in India are U- or reverse-J-shaped. In 2023–2026:
  - the first five minutes are about 2× any later five-minute bar, and the first hour is about 1.75× mid-day per √minute;
  - 11:15–13:15 is the trough;
  - activity picks up again from about 14:15 (C).
- **The opening hour (C).** It has carried the session's only significant drift: about −3.7 bp (t ≈ −2.7) after a +6 bp average gap. About 40% of daily highs and lows are set inside it. Neither the opening-hour nor the opening-30-minute move gives a robust continuation or reversal signal.
- **The last hour (C).** "Rest-of-day predicts the last hour" momentum is absent in 2023–2026 and reversed in the 53 post-auction sessions.
- **Expiry days** differ mainly in the last 60–90 minutes.
- **The closing auction.** Since 3 Aug 2026 the spot index after 15:15 is an auction artefact: Nifty spot is frozen until the auction close, while Sensex prints indicative values that swung by more than 2.5% on one expiry day.

### Cited Findings
- **[A, pre-2013] NSE intraday volatility is reverse-J shaped.** Expiry-day stock volatility is elevated only in the last half-hour, which was then the settlement-averaging window. It is lower in the first two hours and at mid-day. — Agarwalla & Pandey (2013), JFM 33(11), cited in [intraday_technical_regime.md §2](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md); [Wiley](https://onlinelibrary.wiley.com/doi/10.1002/fut.21632)
- **[A, pre-2024] Nifty futures (Nov 2016 – Oct 2017).** Volatility, volume and trade counts are U-shaped at 10-, 30- and 60-minute frequency. — [Sampath & Garg (2018), IRF 19(3)](https://onlinelibrary.wiley.com/doi/10.1111/irfi.12175)
- **[B, India stocks, one year, pre-2024] Liquidity.** Most volume- and spread-based liquidity measures for 20 Nifty stocks are U-shaped intraday. — [Krishnan & Mishra (2013), J. Asian Economics 28:99–114](https://ideas.repec.org/a/eee/asieco/v28y2013icp99-114.html)
- **[C, India working paper, pre-2024] Nifty futures, 1-minute data, Jan 2011 – Aug 2018.**
  - "Hourly volatility" (the authors' per-minute volatility × 60) by window:

    | 9:15–10:00 | 10–11 | 11–12 | 12–13 | 13–14 | 14–15 | 15:00–15:30 |
    |---|---|---|---|---|---|---|
    | 0.350 | 0.238 | **0.225** (lowest) | 0.246 | 0.285 | 0.327 | 0.280 |

  - Friday was the most volatile day.
  - On Thursdays (then the expiry day), 15:00–15:30 was 0.308, the highest of any weekday for that window.
  - Hourly volatility declined over 2011–2018.

  — [Singh & Gangwar (2018), MPRA 89689](https://mpra.ub.uni-muenchen.de/89689/)
- **[C, own, A1] Hourly profile 2023–2026, Nifty non-expiry days (N = 568), per bar.**

  | Bar | 09:15 | 10:15 | 11:15 | 12:15 | 13:15 | 14:15 | 15:15 (15 min) |
  |---|---|---|---|---|---|---|---|
  | Mean \|open→close\|, bp | 26.3 | 17.8 | 14.4 | 14.1 | 14.6 | 17.2 | 7.1 |
  | High-low range per √minute, bp | 6.7 | 4.5 | 3.8 | 3.7 | 3.9 | 4.4 | — |

  Sensex has the same shape (28.1 / 17.3 / 14.1 / 13.8 / 14.8 / 17.3). — [output A1](entry_timing_measurements_output.txt)
- **[C, own, B1] 5-minute bars, last ~60 sessions (Nifty).**
  - Mean bar range: 09:15 bar 28.7 bp; 09:20 12.8; 09:25 11.7; 09:30 10.4; 09:40 9.5.
  - Average bar range by 30-minute block (non-expiry): 9:45–10:15 8.6 bp; 12:15–12:45 6.5 (trough); 14:45–15:15 7.7.
  - Sensex is nearly identical.

  — [output B1](entry_timing_measurements_output.txt)
- **[C, own, B5] Volume (Nifty ETF NIFTYBEES as a cash-market proxy; the index has no volume).** Median share of the day's volume:
  - 09:15–09:45: 12.8%
  - 09:45–10:15: 8.4%
  - trough at 12:15–12:45: 5.1%
  - 14:45–15:15: 10.5%

  — [output B5](entry_timing_measurements_output.txt)
- **[C, own, A2] Time-of-day returns, 722 sessions.**
  - Nifty: gap +5.9 bp (t = 2.9); first hour −3.7 bp (t = −2.8).
  - Sensex: gap +6.7 bp (t = 3.1); first hour −3.6 bp (t = −2.6).
  - Every later hourly bar has |t| < 1.4, except Nifty's 15:15 bar (+1.1 bp, t = 2.6; +6.8 bp, t = 2.5 in P3, which is the move into the auction close).
  - This is where the negative intraday drift documented for 2015–2026 in [04](../04_nifty_measured_facts.md) sits.

  — [output A2](entry_timing_measurements_output.txt)
- **[C, own, A10] Where the day's extremes are set.** The high is in the first hourly bar on 39% (Nifty) / 41% (Sensex) of days, and the low on 41% / 41%. The 14:15 bar holds 18–25%. Each mid-day bar holds 6–8%. — [output A10](entry_timing_measurements_output.txt)
- **[C, own, A4/B1] Opening continuation vs reversal.**
  - Following the first-hour direction from 10:15 to 15:15: Nifty +1.4 bp (t = 0.7), P(same sign) = 0.52; Sensex +1.6 bp (t = 0.8).
  - After gap-ups above 0.3%, following the first hour lost: Nifty −4.9 bp (t = −1.0), Sensex −2.5 bp.
  - After gap-downs below −0.3%, it gained: Nifty +8.5 bp (t = 1.2), Sensex +8.0 bp (t = 1.35).
  - In the 60-session 5-minute sample, following the open→09:30 move to 15:10 earned Nifty +10.1 bp (t = 1.7) and Sensex +7.0 bp (t = 1.2). Following the open→09:45 move earned +3.2 bp (t = 0.6) and +7.4 bp (t = 1.3).
  - None of these is significant.

  — [output A4, B1](entry_timing_measurements_output.txt)
- **[B] First half-hour → last half-hour.** Out-of-sample R² was −1.71% in pooled equity-index futures. Only the "rest-of-day" form was positive out of sample. — Baltussen et al. (2021), summarised in [intraday_technical_regime.md §2](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md)
- **[C, own, A3b] Last hour.** Following the rest-of-day move (previous close → 14:15) to 15:15:

  | Sample | Nifty | Sensex |
  |---|---|---|
  | All 722 sessions | +0.3 bp (t = 0.3) | +0.25 bp (t = 0.3) |
  | P3 (53 post-auction sessions) | −1.7 bp (t = −0.65), win 42% | −3.8 bp (t = −1.5), win 38% |

  In P3 the open-anchored move at 14:15 *reversed* by 15:15: −5.3 bp (t = −2.1) for Nifty. — [output A3, A3b](entry_timing_measurements_output.txt)
- **[B, negative] Post-publication decay.** SPY intraday momentum disappeared after publication. — Rosa (2022), in [intraday_technical_regime.md §2](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md)
- **[C, own, A1/B1] Expiry vs non-expiry.**
  - Nifty expiry days are more volatile in the first hour (29.5 vs 26.3 bp), in the 14:15 bar (19.0 vs 17.2) and in the 15:15 bar (10.6 vs 7.1).
  - In the recent 5-minute sample, Sensex expiry Thursdays are markedly more volatile all afternoon: average 5-minute bar range in 13:15–14:45 of 8.7–10.2 bp, vs 5.8–7.6 bp on non-expiry days (N = 13 expiry days). Nifty expiry Tuesdays are elevated only from 14:15 (8.1 vs 7.1).

  — [output A1, B1](entry_timing_measurements_output.txt)
- **[C, own, A1] Change after the Tuesday switch (P2).** The intraday shape is unchanged. The 14:15–15:15 bar is slightly more volatile (Nifty non-expiry 19.3 vs 16.8 bp in P1). P3 is quieter from 11:15 to 15:15 (12.2–14.2 bp per hour). — [output A1](entry_timing_measurements_output.txt)
- **[C, own, B1/C1] Closing auction (P3).**
  - Nifty spot: 68% of 15:15 and 87% of 15:20 five-minute bars have zero range. There are at most 2 distinct 1-minute prints between 15:16 and 15:29. So the spot index is frozen until the auction result.
  - Sensex spot keeps printing indicative values. On expiry days the 15:15–15:30 five-minute bars average 53 bp of range, and the hourly 15:15 bar averages 136 bp (N = 11).

  — [output B1, C1, A1](entry_timing_measurements_output.txt)
- **[C] Auction episodes and mechanics** (broker explainer; figures as reported):
  - Sensex, 3 Sep 2026: the indicative close fell from about 76,510 (15:18) to about 74,373 (15:20), then recovered to a 76,153 close. Some put premiums rose 400–500% within minutes.
  - Nifty, 8 Sep 2026: the indicative level swung between about 23,806 and 23,375; the close was 23,635.10.
  - NSE's auction runs 15:15–15:35. The reference price is the 15:00–15:15 VWAP, with a ±3% band.

  — [Riddhi Siddhi](https://www.riddhisiddhisharebrokers.com/nifty-closing-auction-session-cas-expiry-volatility)
- **[C] Other reports.**
  - Concern about thin BSE auction participation, and a Nifty Tuesday-expiry surge of more than 150 points inside the auction. — [NewKerala](https://www.newkerala.com/news/a/sensex-weekly-expiry-debut-under-closing-auction-system-784.htm)
  - Confusion over the new close mechanism fuelled a rally on 4 Aug 2026. — [Bloomberg newsletter](https://www.bloomberg.com/news/newsletters/2026-08-04/confusion-over-india-nse-closing-auction-turbocharges-nifty-rally)
- **[Excluded] A 2026 Zenodo "study" of Nifty expiry volatility** describes its own data as simulated, so it is not evidence. — [Zenodo](https://zenodo.org/records/19220278)

### Inferences
- **09:15–09:45 is the worst window to buy.** It has the highest noise, carries the session's only significant drift (down, so it works against calls), and is where (per §2) option spreads are widest and India VIX prints are least reliable. The current 09:45 start is supported. For long calls specifically, the drift argument extends to about 10:15 (test this; see §7).
- **The mid-day trough is a pace problem, not a signal problem.** At 11:15–13:15 the per-minute range is about 55–60% of the opening hour's, so the same index target takes longer, and a long option pays more theta per bp of movement. Handle this with a remaining-room requirement (§4), not a blanket block.
- **The 14:45 momentum check has no support in 2023–2026 Indian data.** Keep it research-only, as the spec already does.
- **After 3 Aug 2026, never use spot-index prints after 15:15** for signals, labels or "close" values. Use the 15:14 price or futures. Exits stay before 15:15. On expiry days the 15:00–15:15 VWAP sets the auction reference price, so settlement-related flow concentrates there. That is a further reason to keep the 15:00 expiry exit, and to test 15:00 on non-expiry days too.

### Gaps
- No peer-reviewed study of Indian intraday seasonality covers 2024–2026, and none studies the closing auction's effect on intraday behaviour. Our P3 sample is 53 sessions in a high-volatility year.
- Index volume is not available from Yahoo. The ETF volume proxy is cash-market only. Futures and option volume profiles need SmartAPI recording.

---

## 2. When are Nifty/Sensex weekly option spreads tightest and implied volatility least rich? Is there a cheapest time to buy?

### Takeaway
- **Spreads.** I found **no study of Nifty or Sensex weekly-option spreads by time of day.** International evidence (B) says option spreads are widest at the open, fall sharply over the first 30–60 minutes and then stay flat or narrow. 0DTE spreads roughly double in the final hour.
- **India VIX (own, C).** It is highest around 09:25–10:30 and drifts down about 1% of its level by 15:00–15:30, i.e. about 0.1–0.2 vol points. On Nifty expiry days it falls through the afternoon. That is worth only about ₹30–65 per lot, the same order as one round-trip spread: second-order next to theta and signal timing.
- **Options price the U-shape** (Todorov–Zhang), so no clock hour is "cheap" relative to the movement it buys.
- **The least-bad buying window is about 10:00–13:30**: past the opening spread and VIX noise, before late-day spread widening and the steepest 0DTE theta.

### Cited Findings
- **[B] Option spreads vs stock spreads (US, CBOE).** Option bid-ask spreads fall sharply after the open and then flatten. NYSE stock spreads are U-shaped. The difference is attributed to competition between market makers and to informed trading. — [Chan, Chung & Johnson (1995), JFQA 30(3):329–346](https://ideas.repec.org/a/cup/jfinqa/v30y1995i03p329-346_00.html)
- **[C] CBOE equity options** split into 13 half-hour intervals show L-shaped spreads (thesis). — [Chen (2018), U. Saskatchewan](https://harvest.usask.ca/handle/10388/8317)
- **[C, abstract-level only] FTSE 100 index options:** spreads are "wide near the market open and narrow near the close". I could not retrieve the title or authors. — [Southampton eprint 37372](https://eprints.soton.ac.uk/37372)
- **[B] US 0DTE.** Effective spreads roughly double in the final hour (10.5% vs 4.5% of mid). Beyond 2% OTM they reach 45–80% of mid. Buys pay more than sells. — Beckmeyer et al., summarised in [option_trade_construction.md §1, §5](../Nifty%20options%20multifactor%20quant%20strategy/option_trade_construction.md); [PDF](https://wp.lancs.ac.uk/fofi2024/files/2024/04/FoFI-2024-146-Leander-Gayda.pdf)
- **[B, working paper] US VIX, 1-minute data, 2003–2013.**
  - The VIX drifts down about 0.80% from open to close, most strongly in the first 30 minutes and the last few minutes.
  - The S&P 500 shows no intraday return pattern, but its volatility is U-shaped.
  - The VIX falls about 3% a week and surges over the weekend.

  — Fernandez-Perez, Frijns, Tourani-Rad & Webb (2016), "The Intraday Properties of the VIX and the VXO", via [CXO Advisory](https://cxoadvisory.com/?p=29380)
- **[B] Calendar-time artefact.** The 1-day VIX (VIX1D) rises during trading hours and falls overnight because of how it is calculated. Calendar-time short-dated IV therefore moves mechanically within the day. — [Finance Research Letters (2024), TU Dresden record](https://fis.tu-dresden.de/portal/de/publications/the-daily-rise-and-fall-of-the-vix1d-causes-and-solutions-of-its-overnight-bias(416336ff-f4f0-468f-a9cd-2877ae8ffdcd).html). See also the business-time discussion in [option_trade_construction.md §4](../Nifty%20options%20multifactor%20quant%20strategy/option_trade_construction.md).
- **[B] Options price the intraday pattern.** Option prices with 0 and 1 day to expiry, sampled through the day, recover the familiar U-shaped intraday volatility pattern (S&P 500). Market makers price the time-of-day pattern into short-dated premiums. — [Todorov & Zhang (2024), "Intraday Volatility Patterns from Short-Dated Options"](https://www.kellogg.northwestern.edu/faculty/todorov/htm/papers/odp.pdf)
- **[B] Intraday is not where option buyers lose (US).**
  - Delta-hedged S&P 500 option returns are −1.0% overnight but **+0.3% intraday**.
  - India [A, pre-2024]: Nifty short-option returns are positive overnight and negative but insignificant intraday, 2017–2020.

  — Muravyev & Ni (JFE 2020) and Bhat, Pandey & Nageswara Rao (JFM 2024), in [option_trade_construction.md §1](../Nifty%20options%20multifactor%20quant%20strategy/option_trade_construction.md)
- **[C] Vol-of-vol timing.** VVIX predictive power peaks at 10:00 ET and fades after 11:00 (US, 2006–2022; seminar abstract). — [Hizmeri, "Early Birds Get the Vol"](https://www.eur.nl/en/ese/events/early-birds-get-vol-morning-volatility-uncertainty-and-variance-risk-premium-2025-11-20)
- **[C, own, A9] India VIX hourly path, 722 sessions.** Median % change vs the previous day's last print:

  | Sample | First print | 10:15 | 11:15 | 12:15 | 14:15 | 15:15 | Close |
  |---|---|---|---|---|---|---|---|
  | All days | +0.09 | **+0.63** | +0.50 | +0.32 | +0.23 | −0.19 | −0.36 |
  | Non-expiry | +0.10 | +0.70 | +0.60 | +0.50 | +0.36 | +0.06 | −0.03 |
  | Nifty expiry | +0.07 | +0.03 | +0.08 | −0.32 | −0.07 | **−1.05** | −1.33 |

  - The VIX close is below its 10:15 value on 65% of days (median −0.98%).
  - The 10:15 value is above the 09:15 first print on 58% of days.

  — [output A9](entry_timing_measurements_output.txt)
- **[C, own, B4] India VIX, 5-minute data, last ~60 sessions** (VIX range 10.3–15.7, median 12.1). Median % change vs the 09:45 value:

  | 09:15 first print | 09:25–09:30 | 10:30–11:00 | 12:00 | 15:00 | 15:30 |
  |---|---|---|---|---|---|
  | −0.3 | +0.2 | −0.3 | −0.4 | −0.9 | −1.6 |

  The VIX is lower at 15:00 than at 10:00 on 58% of days. — [output B4](entry_timing_measurements_output.txt)
- **[C] India VIX is built from near- and next-month Nifty options, not weeklies.** It is a proxy for the level of weekly IV, not for its intraday path. — [option_trade_construction.md §3–4](../Nifty%20options%20multifactor%20quant%20strategy/option_trade_construction.md)
- **[C] Scheduled events.** On event days, buyers should enter only after the morning IV crush, since VIX falls on the day even when the range is large (RBI/Budget patterns). — [macro_crossasset_drivers.md §1](../Nifty%20options%20multifactor%20quant%20strategy/macro_crossasset_drivers.md)

### Inferences
- **Size of the IV-timing effect.** A 1% intraday VIX swing at VIX 12–15 is 0.12–0.15 vol points. With ATM 0DTE vega of about ₹270 per lot per vol point ([option_trade_construction.md §3](../Nifty%20options%20multifactor%20quant%20strategy/option_trade_construction.md)), and more for 1–2 DTE, that is roughly ₹30–65 per lot. That is comparable to one round-trip spread (₹6.5–65 per Nifty lot), but small against a ₹400 stop. **IV timing should not move the entry by more than a check or two.** It is a reason not to buy at 09:15–09:45, not a reason to wait for the afternoon.
- **Why the afternoon is not "cheap".** A lower afternoon IV coincides with lower realised movement (§1). For 0DTE, theta per clock-minute rises again into the last hour, because market makers price the U-shape (Todorov–Zhang). The only time the buyer clearly overpays on every dimension is 09:15–09:45: the widest spreads (international evidence), VIX first-print noise, and noise without a signal.
- **The expiry-day VIX decline** (−1.05% by 15:15) is consistent with demand for hedges falling away as weekly gamma expires. That is an interpretation, not a tested fact. For a buyer it reinforces the 13:30 entry cutoff on expiry days.
- **Default spread multipliers until measured.** Keep the placeholders from option_trade_construction (half-spread ×2 before 09:30 and after 14:45), and add ×1.5 for 09:30–10:00. Replace all of them with snapshot data.

### Gaps
- **Most important unmeasured input:** quoted and effective spreads of ATM ± 3 Nifty and Sensex weekly strikes by minute of day, by days to expiry, and on expiry vs non-expiry days. Log SmartAPI 5-level depth every minute for 4–8 weeks.
- The intraday path of *weekly* ATM IV in business time, which India VIX cannot show.
- Whether Indian option spreads follow the L-shape (CBOE) or a U-shape (Indian stocks) is unknown.

---

## 3. Entry technique: breakout vs pullback/retest vs waiting for confirmation; stop-entry vs limit-entry; false breakouts and filters

### Takeaway
- **Enter on the signal; don't wait for a pullback.** On a breakout trigger, entering at the signal with a marketable order beats waiting for a pullback or retest limit, *per signal*. Resting limits are adversely selected: they fill on the breakouts that fail and miss the ones that run (theory B; our data C). Retest-limit entries cut per-signal expectancy by 35–110% across Nifty and Sensex in both samples.
- **No extra confirmation bar.** Waiting one more 15-minute check was neutral. It screens out the 20–28% of breakouts that fail, but gives the gain back through worse entry prices. Waiting one hour hurt.
- **Volatility contraction.** NR7, inside days and Bollinger squeezes do not predict a larger next-day range for Nifty (12 years), because volatility clustering dominates.
- **Prior-day NR7** was associated with better breakout outcomes in Nifty, Sensex and SPY (Zarattini). It is a candidate tilt, not a proven filter. Prior inside days were worse in all three.

### Cited Findings
- **[B] The two risks of limit orders.** An adverse information event produces an unwanted fill; favourable news leaves the desired fill unobtained (non-execution). — [Handa & Schwartz (1996), JF 51(5):1835–61](https://ideas.repec.org/a/bla/jfinan/v51y1996i5p1835-61.html)
- **[B] Adverse selection is mechanical.** Limit orders' price-contingent execution and adverse selection mechanically produce the poor post-trade returns otherwise blamed on investor biases (all Finnish individual investors). — [Linnainmaa (2010), JF 65(4):1473–1506](https://ideas.repec.org/a/bla/jfinan/v65y2010i4p1473-1506.html)
- **[C] Pullback entries in futures (MNQ).**
  - An ORB pullback entry had an 80.7% stop-out rate.
  - Only a regime-gated, ATR-scaled pullback passed walk-forward.
  - A one-bar (15-minute) delay flipped a regime signal's out-of-sample T from +4.30 to −2.78.

  — Mesfin (2026), in [intraday_technical_regime.md §1, §7](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md); [arXiv 2605.04004](https://arxiv.org/abs/2605.04004)
- **[B] Zarattini, Aziz & Barbon (2024), "Beat the Market" (SPY 2007–2024, noise-area breakout):**
  - **Check timing.** "To mitigate the risk of overtrading caused by short-term market fluctuations", trades are taken only at HH:00 and HH:30. Positions are entered at 10:30 "even though the price had moved outside the Noise Area a few minutes earlier". The first possible entry is 10:00. Stops are also checked only on the half-hour.
  - **Band width.** Return falls as the volatility multiplier (VM) rises, but risk-adjusted return peaks at about VM = 1.5. The paper uses 1.
  - **Prior-day patterns** (average P&L per day):

    | Pattern | P&L | t | Hit rate |
    |---|---|---|---|
    | Unconditional | 12 bp | 5.34 | 43% |
    | NR4 | **22 bp** | 5.14 | 45% |
    | NR7 | 16 bp | 3.07 | 43% |
    | Triangle | 14 bp | 3.19 | 43% |
    | Inside day | 5 bp | 0.85 | 41% |
    | Outside day | 7 bp | 1.05 | 43% |
    | Prior trend day | −2 bp | −0.24 | 40% |

  - **RSI(5).** Regressing daily strategy return on the prior-day 5-day RSI gives β = −3.25 (p = 0.001): lower RSI, better momentum. The authors read this as a dealer-gamma proxy.
  - **Costs.** Measured slippage on algorithmic market orders at the minute open was about $0.001 per share.

  — [paper PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)
- **[C] Independent ORB replication, 5 index CFDs (NQ, SPX, Dow, DAX, FTSE), 2015–2026.**
  - Zarattini & Aziz's 5-minute ORB gross results reproduce (NQ +0.131R).
  - Net of spread and slippage, no market is significantly positive, and 4 of 5 are negative.
  - Every market lost in 2015–2017.
  - The first candle carries only about 0.1R of directional edge, roughly the round-trip cost.

  — [MQL5 blog](https://www.mql5.com/en/blogs/post/776235)
- **[C/D] Crabel (1990).** The narrow-range-N-day / opening-range "stretch" stop-entry method (buy-stop at open + stretch after NR days) is described by practitioners. I found no independent peer-reviewed test of it. — [Oxford Capital description](https://oxfordstrat.com/trading-strategies/narrow-range/); [QuantifiedStrategies NR7](https://quantifiedstrategies.substack.com/p/we-improved-the-nr7-trading-strategy)
- **[B] Bollinger Bands.**
  - Bollinger Band rules fail to beat buy-and-hold after costs. — [Lento, Gradojevic & Wright (2007), Applied Financial Economics Letters 3(4)](https://ideas.repec.org/a/taf/raflxx/v3y2007i4p263-267.html)
  - The "squeeze" refinement (band width at a six-month minimum, then a close outside the band) gives mixed results and is not recently profitable gross. — [Fang, Jacobsen & Qin, "Popularity versus Profitability"](https://www.tias.edu/en/item/popularity-versus-profitability)
- **[B/C] Volume filters (from earlier notes).** The ORB edge on US "stocks in play" came from the relative-volume filter. Volume-spike and dry-up signals failed on MNQ (T from −2.2 to −5.3). — [02_strategy_evidence_part1.md §3](../02_strategy_evidence_part1.md); [intraday_technical_regime.md §7](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md)
- **[C, own, A6] Entry technique on the hourly noise-band breakout** (first signal of the day, V = 1, held to 15:15, 2023–2026). Per-signal mean (unfilled limits count as zero):

  | Entry | Nifty: fill rate | Nifty: per signal | Sensex: fill rate | Sensex: per signal |
  |---|---|---|---|---|
  | **Market at signal** | 100% | **+5.36 bp** (N = 368, t = 1.88) | 100% | **+5.57 bp** (N = 365, t = 1.98) |
  | Limit 0.25σ back | 83% | +3.10 | 82% | +3.45 |
  | Limit 0.5σ back | 65% | +1.84 | 65% | +2.54 |
  | Limit at the band edge (retest) | 64% | **−0.60** | 65% | +1.27 |

  The limit orders that never filled were the trades that ran: +36 to +49 bp from market entry (t = 6.8–9.3). The filled limit trades averaged only −0.9 to +4.2 bp. — [output A6](entry_timing_measurements_output.txt)
- **[C, own, B2] The same test at 5-minute resolution** (45 sessions, 15-minute checks):
  - Nifty: market +15.2 bp per signal vs band-edge retest limit +5.7 bp (fill 65%; the 11 unfilled signals averaged +39.6 bp).
  - Sensex: market +14.1 bp vs limit +9.0 bp (fill 78%).

  — [output B2](entry_timing_measurements_output.txt)
- **[C, own, A6/B2] Waiting for confirmation (still outside the band at the next check).**

  | Test | Index | Confirmed entry | Immediate entry, same days | Failed breakouts | Mean of failed |
  |---|---|---|---|---|---|
  | Hourly, wait one check | Nifty | +3.16 bp (N = 257) | +5.97 bp (N = 333) | 23% | −18.3 bp (t = −3.5) |
  | Hourly, wait one check | Sensex | +3.56 bp | +5.26 bp | 22% | −23.1 bp (t = −4.3) |
  | 15-minute | Nifty | +14.6 bp | +15.2 bp | 6 of 31 | — |
  | 15-minute | Sensex | +17.8 bp | +14.1 bp | 9 of 32 | — |

  "Failed" means back inside the band one check later. — [output A6, B2](entry_timing_measurements_output.txt)
- **[C, own, D1] Contraction → expansion, Nifty daily 2014–2026 (3,114 days).**
  - **No absolute expansion.** Next-day range ÷ prior 20-day average range:

    | All days | NR7 (N = 492) | NR4 | Inside day | NR7 + inside | BB squeeze |
    |---|---|---|---|---|---|
    | 1.02 | **0.94** | 0.98 | 1.01 | 0.92 | 1.03 |

    The BB-squeeze 5-day range is 2.97 vs 2.80 for all days.
  - **The apparent expansion is mechanical.** An NR7 day's own range is 0.57 × average, so the next day is 1.50× it. That is mean reversion, not a signal.
  - **Next-day trendiness** (|open − close| / range) is 0.48–0.51 in every group.
  - **More whipsaw after NR7.** The next day breaks *both* prior-day extremes on 22% of days vs 11% unconditionally.
  - P(close beyond the broken extreme | only one side broken) is 0.78 vs 0.65, largely because the reference range is narrower.

  — [output D1](entry_timing_measurements_output.txt)
- **[C, own, A10] Prior-day pattern as a filter on the hourly band signal.**

  | Condition | Nifty | Sensex |
  |---|---|---|
  | All signals | +5.4 bp | +5.6 bp |
  | Prior NR7 | **+13.2 bp** (N = 52, t = 1.78) | **+19.4 bp** (N = 41, t = 2.83) |
  | Prior NR4 | +7.4 | +2.7 |
  | Prior inside day | **−0.8** (N = 40) | **−3.3** (N = 38) |
  | Prior RSI(5) ≥ 50 | +10.0 (t = 2.3) | +11.7 (t = 2.8) |
  | Prior RSI(5) < 50 | +1.8 | +0.6 |

  The RSI split has the **opposite sign to Zarattini's SPY result**. — [output A10](entry_timing_measurements_output.txt)
- **[C, own, A5] Longs vs shorts and band width.**
  - Short signals did better than long signals: Nifty +7.5 bp (t = 1.7) vs +2.9 bp (t = 0.8); Sensex +7.1 vs +3.8.
  - A wider band (V = 1.25 vs 1.0) raised the per-trade mean slightly (Nifty +6.35 vs +5.36 bp; Sensex +6.36 vs +5.57) on 18–19% fewer signals.

  — [output A5](entry_timing_measurements_output.txt)

### Inferences
- **A pullback or retest limit turns a momentum signal into a mean-reversion bet.** The fills are concentrated in the failures. For a trigger whose edge is "price has left the noise", the default should be **enter at the check that confirms the close outside the band**.
  - If the spec's H2 pullback variant is kept, it must be scored *per signal*, with missed trades as zero, never per filled trade.
- **The spec's order rule ("limit at mid + 1 tick, never chased more than 2 ticks") is a resting limit in a fast market.**
  - One Nifty point moves an ATM premium by about ₹0.5, which is 10 ticks. During a breakout the quote moves many ticks per minute, so this rule will often leave the order unfilled exactly on the winners.
  - Replace it with a **marketable limit at the ask (+ ≤ 2 ticks)**. Govern chasing with an **index-based cap** and a live stop-fit recheck (§6), not a premium-tick cap.
  - Log every non-fill.
- **No extra confirmation bar.** The trigger already requires a 15-minute close outside the band; that is the confirmation. A second bar has no measured benefit, and the hourly analogue hurt.
- **Band width.** Test V ∈ {1.0, 1.25, 1.5} (Zarattini's best risk-adjusted value was about 1.5). Consider an asymmetric bar, V_long = V_short + 0.25, because longs fight the negative intraday drift (§1; [04](../04_nifty_measured_facts.md)).
- **Contraction filters.** Prior-day NR7 → a candidate *tilt* (for example a lower meta-model hurdle or a feature), never a hard requirement. Prior inside day → a candidate *veto*. Both rest on 40–50 events per index, so they must be pre-registered and tested on 2019–2026 futures. RSI(5) → do not use: the sign conflicts between markets.
- **Stop-entry vs limit-entry.** For a manual, alerts-only system a true stop-entry (buy-stop at the band) is not available on options. It could only be built as an index-triggered conditional order, and whether Angel One supports that is unverified ([option_trade_construction.md §6](../Nifty%20options%20multifactor%20quant%20strategy/option_trade_construction.md)). The practical equivalent is "alert on the check, marketable limit immediately".

### Gaps
- No peer-reviewed or India-specific study compares breakout, pullback and confirmation entries on an index. Crabel's NR/ORB results have no independent rigorous test that I found.
- Our tests use the spot index, hold to 15:15 instead of the spec's VWAP/stall/90-minute exits, and ignore option costs. Conditioning subsets are small (N = 38–96).
- No India evidence on futures-volume filters for index breakouts.

---

## 4. Time-of-day dependence of momentum and breakout success: are first-hour breakouts more or less reliable, and should 11:30–13:30 be avoided?

### Takeaway
The evidence on *which* hour gives the best breakouts conflicts and is fragile:
- In 2023–2026 hourly data, first breakouts at 10:15 were the weakest and those at 11:15 the strongest.
- In the most recent 60 sessions, breakouts at 09:45–10:15 were the best.
- Per-bucket samples (N = 25–200) cannot separate effects smaller than about 20 bp.

**Nothing supports a blanket 11:30–13:30 block.** Midday signals were weaker but not negative. What declines steadily and robustly is the **room left**. The median maximum excursion to 15:15 falls from about 48 bp at 10:15 to about 35 bp at 12:15, 29 bp at 13:15 and 21 bp at 14:15. Late entries fail on geometry and theta, not on signal quality.

### Cited Findings
- **[C, own, A5] Hourly band breakout by the time of the day's first signal** (V = 1, follow to 15:15):

  | First signal at | Nifty | Sensex |
  |---|---|---|
  | 10:15 | N = 199, **+2.4 bp** (t = 0.6), win 51% | N = 196, +4.4 bp (t = 1.0) |
  | 11:15 | N = 74, **+16.6 bp** (t = 3.0), win 66% | N = 80, +8.6 bp (t = 1.5) |
  | 12:15 | N = 28, +5.7 bp | N = 25, +2.0 bp |
  | 13:15 | N = 32, +3.6 bp | N = 31, +4.8 bp |
  | 14:15 | N = 35, −0.5 bp | N = 33, +8.7 bp |

  At V = 1.25 the pattern is similar (11:15: +12.8 bp Nifty, +15.3 bp Sensex). — [output A5](entry_timing_measurements_output.txt)
- **[C, own, B2] The same split, recent 60 sessions, 15-minute checks:**

  | First signal in | Nifty | Sensex |
  |---|---|---|
  | 09:45–10:15 | N = 16, **+27.1 bp**, win 69% | N = 22, +16.9 bp |
  | 10:30–11:15 | N = 7, +8.5 bp | N = 6, +8.3 bp |
  | 11:30–13:15 | N = 6, −4.1 bp | N = 3, +3.2 bp |
  | 13:30–14:30 | N = 2 | N = 1 |

  This conflicts with the longer hourly sample. — [output B2](entry_timing_measurements_output.txt)
- **[C, own, A3] Does the move so far (open → τ) continue to 15:15?** Correlation is about 0 at every τ from 10:15 to 13:15, and +0.10 / +0.09 at 14:15 (Nifty / Sensex). Top-tercile moves only:

  | Decision time τ | Non-expiry days | Expiry days |
  |---|---|---|
  | 10:15 | +3.8 bp, win 49% | −5.9 bp |
  | 11:15 | +3.4 bp, win 56% | +0.9 bp |
  | 12:15 | +2.9 bp, win 58% | **+11.2 bp**, win 60% |
  | 13:15 | +3.6 bp, win 51% | **+9.4 bp**, win 68% |
  | 14:15 | +4.2 bp, win 55% (t = 2.1) | +1.6 bp |

  (Nifty shown. Expiry N = 154 days; top-tercile t ≤ 1.8.) — [output A3](entry_timing_measurements_output.txt)
- **[C, own, A11] Room left from each decision time to 15:15**, Nifty non-expiry, median bp:

  | τ | Median \|move\| to 15:15 | Median max excursion | P(max excursion ≥ 20 bp) |
  |---|---|---|---|
  | 10:15 | 27.6 | 47.8 | 0.94 |
  | 11:15 | 23.6 | 41.1 | 0.89 |
  | 12:15 | 19.7 | 34.9 | 0.83 |
  | 13:15 | 17.1 | 29.2 | 0.76 |
  | 14:15 | 12.3 | 21.3 | **0.55** |

  Sensex and expiry days are within ±3 bp of these figures. — [output A11](entry_timing_measurements_output.txt)
- **[B] Half-hour structure in US stocks.** Returns show short-run reversal within the hour (bid-ask bounce, weak resiliency) and continuation at exact multiples of one trading day, strongest in the first and last half-hours. — [Heston, Korajczyk & Sadka (2010), JF 65(4):1369–1407](https://ar5iv.arxiv.org/html/1005.3535)
- **[B] Momentum is strongest after active opening sessions.** In Chinese commodity futures, first sessions with high volume or volatility give the strongest intraday momentum. Market intraday momentum is concentrated in short-gamma states. — Jin et al. (2019) and Baltussen et al. (2021), in [intraday_technical_regime.md §2](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md)
- **[B] Bands widen through the day.** Zarattini's noise band needs half as much movement from the open by 10:30 as by 15:30 to signal an imbalance, so breakouts later in the day need larger absolute moves. — [Zarattini, Aziz & Barbon (2024)](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)
- **[C] The 11:00–12:00 volatility trough** in Nifty futures, 2011–2018. — [Singh & Gangwar (2018)](https://mpra.ub.uni-muenchen.de/89689/)
- **[C, model] 0DTE value decay with spot unchanged.** An ATM 0DTE keeps about 85% of its 09:15 value at 11:00, about 63% at 13:00 and about 40% at 14:30. A 0.3%-OTM keeps 76% / 43% / 14%. — [option_trade_construction.md §2](../Nifty%20options%20multifactor%20quant%20strategy/option_trade_construction.md)
- **[D] Lunch-hour false breakouts.** I found no rigorous source for the practitioner claim that lunch-hour breakouts are "false". Indian markets have no lunch break; the mid-day effect here is lower volatility and volume (§1).

### Inferences
- **Do not build sub-rules from the hourly buckets.** Per-signal standard deviation is about 55 bp (back-computed from A5: mean 5.36 bp, t = 1.88, N = 368), so the standard error of a 30-signal bucket is about 10 bp. The 11:15 "winner" and the recent 09:45 "winner" are both consistent with noise.
- **Replace "avoid 11:30–13:30" with a room-to-run-in-time condition.** Allow an entry only if the expected remaining maximum excursion in the trade direction is at least about 2× the index distance to the target *plus* the theta drag to the deadline. Use the σ_rem(τ) machinery from [intraday_technical_regime.md §4](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md).
  - With a ₹400 risk and a 1.5× net target at delta 0.5, the target is about 9 bp. At 14:15 only about 55% of days offer even a 20 bp excursion in either direction.
- **Later cut-offs.** On non-expiry days, test bringing the last entry forward from 14:30 to 14:00. The spec's 90-minute deadline and 15:10 exit leave a 14:30 entry only 40 minutes. On expiry days keep 13:30, because theta dominates. Expiry-day midday momentum is the one pocket where continuation looked decent (12:15–13:15 top tercile), so do not cut expiry entries earlier without a test.

### Gaps
- No Indian or rigorous international study measures breakout reliability by time of day for an index with realistic costs.
- Our two samples conflict, and both are in-sample. A 2019–2026 futures test is needed, with the bucket analysis kept *diagnostic only*.

---

## 5. Multi-timeframe alignment (daily trend + intraday trigger) as an entry filter

### Takeaway
I found **no peer-reviewed, out-of-sample evidence** that daily-trend alignment improves intraday entries. The literature consists of practitioner frameworks (Elder's Triple Screen) and vendor backtests.

In our data:
- The prior-day trend state (close vs SMA20/50) does not change Nifty's open→close drift.
- Noise-band breakouts aligned with SMA20 did modestly, not significantly, better.
- SMA50 alignment was mixed.
- First-hour moves *against* the daily trend continued slightly better.

Use the daily trend at most as a regime or size input, not a gate.

### Cited Findings
- **[C, own, D2] Nifty open→close by prior-day trend, 2014–2026.**

  | Prior-day state | Mean open→close | P(close > open) |
  |---|---|---|
  | Above SMA20 | −6.9 bp (t = −4.5) | 46.3% |
  | Below SMA20 | −6.4 bp (t = −2.2) | 47.7% |
  | Above SMA50 | −6.6 bp (t = −4.4) | 46.6% |
  | Below SMA50 | −7.7 bp (t = −2.4) | 47.0% |

  — [output D2](entry_timing_measurements_output.txt)
- **[C, own, A7] Hourly band signals by daily-trend alignment.**

  | Filter | Nifty: aligned | Nifty: counter | Sensex: aligned | Sensex: counter |
  |---|---|---|---|---|
  | SMA20 | +6.7 bp (t = 1.7), win 57% | +4.2 bp, win 53% | +7.8 bp (t = 1.9) | +3.5 bp |
  | SMA50 | +4.4 bp | **+6.4 bp** | +7.5 bp | +3.1 bp |

  The difference has t < 1 in every case. — [output A7](entry_timing_measurements_output.txt)
- **[C, own, A8] First-hour direction followed to 15:15.** Nifty: aligned with SMA20 −0.1 bp vs counter +3.8 bp; aligned with SMA50 −1.4 bp vs counter +5.1 bp. Sensex shows the same pattern, smaller. — [output A8](entry_timing_measurements_output.txt)
- **[C, from 04] The 50-DMA is mainly a volatility flag.** Next-5-day P(up) is 57.4% above the 50-DMA vs 54.8% below, but moves below it are 54% larger. — [04_nifty_measured_facts.md §6](../04_nifty_measured_facts.md)
- **[B] Fast daily trend has collapsed since 2009** on small-tick contracts, a group Nifty falls in. — Kurth et al. (2026), in [intraday_technical_regime.md §6](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md)
- **[D/C] Practitioner sources.**
  - Multi-timeframe filters "avoid low-probability situations" but cut trade counts, and higher-timeframe values must be computed on closed bars to avoid look-ahead. — [QuantifiedStrategies](https://quantifiedstrategies.substack.com/p/multi-timeframe-analysis-and-strategy)
  - A Bank Nifty 5-minute Supertrend with an hourly filter reports favourable, unverified equity curves. — [Marketcalls](https://www.marketcalls.in/amibroker/supertrend-multi-timeframe-based-trading-system-amibroker-afl-code.html)
- **[B vs C conflict] The RSI(5) "recent trend" proxy.** Zarattini found that *lower* prior RSI improves SPY momentum. Our Nifty and Sensex band signals did better after *higher* RSI (§3). — [Zarattini et al.](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download); [output A10](entry_timing_measurements_output.txt)

### Inferences
- **No hard multi-timeframe gate.** The spec's day card can *show* "daily up / 15-min up", but it should not veto counter-trend H1 signals. The only defensible use is as one shrunk meta-model feature (the spec already allows one regime feature), tested walk-forward.
- **Treat the daily trend as volatility context.** Below the 50-DMA, expect larger moves. That feeds stop and target sizing, not direction.

### Gaps
- No rigorous multi-timeframe study exists on any index that I could find, and none on India.
- Our hourly sample (Jan 2024 onward after SMA warm-up) is short and in-sample.

---

## 6. Execution timing for a manual trader: realistic alert-to-fill delay, the cost of a 1–5 minute delay, and alert designs that tolerate delay

### Takeaway
- **Latency.** I found no study of alert-to-fill latency for manual retail traders. Plan for about 1–3 minutes (alert → app → strike selection → order → fill) and measure it in the paper phase.
- **Unconditional delay is cheap.** At the minute horizon the index is close to a random walk: there is no significant continuation 1–10 minutes after a 15-minute move (|t| ≤ 1.4), and a slight reversal at about 5 minutes.
- **Delay on breakout signals is expensive.** On noise-band breakout signals the drift runs with the signal.
  - The 10-minute median lag of 15-minute checks cost Nifty 0.7 bp median / 3.6 bp mean. That is about ₹25–30 per lot per minute on average at delta 0.5.
  - In the last 19 sessions, a 1–5 minute delay cost Nifty 2.7–5.3 bp on average (₹200–400 per lot) but Sensex only 0.6–1.1 bp.
- **Delay breaks stop-fit more than direction.** The ₹400 stop is only about 5 bp of index, so delay mostly breaks *stop-fit*. Alerts therefore need an index-based chase cap, a short expiry, and a recheck of stop-fit at the actual fill price.

### Cited Findings
- **[B] Speed of convergence (NYSE).** After order imbalances, intraday efficiency is restored in "more than five minutes but less than sixty minutes". Follow-ups put it at 5–15 minutes for large NYSE stocks and about 10 minutes for FTSE-100 futures. — [Chordia, Roll & Subrahmanyam (2005), JFE 76(2):271–292, CFA digest](https://rpc.cfainstitute.org/en/research/cfa-digest/2005/11/evidence-on-the-speed-of-convergence-to-market-efficiency-digest-summary)
- **[B, India] Order-imbalance predictability** in NSE stocks is strong for 5 minutes and gone within 30. — Tripathi, Dixit & Vipul (2021), in [intraday_technical_regime.md §1](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md)
- **[C] Quarter-hour bursts (crypto futures).** In the first 10 seconds of quarter-hour minutes there are about 26% more trades and 26% larger absolute returns, attributed to scheduled algorithms on calendar bar grids. There is negative autocorrelation in the minute before each mark. The gross return predictability is about 0.5 bp. — [Kim & Hansen (2026), arXiv 2607.09426](https://arxiv.org/abs/2607.09426)
- **[C, own, C1] Same pattern in Indian indices.** Over the last 19 sessions (09:30–15:14), the mean |1-minute return| in minutes starting at :00/:15/:30/:45 was 2.40 bp vs 2.02 bp in other minutes (Nifty), and 2.38 vs 2.02 bp (Sensex). — [output C1](entry_timing_measurements_output.txt)
- **[B] Checking on a coarse grid is deliberate.** Zarattini et al. check only on the half-hour "to mitigate the risk of overtrading caused by short-term market fluctuations". — [paper](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)
- **[C] A one-bar delay can flip a signal.** On MNQ, a one-bar (15-minute) delay flipped a signal's OOS T from +4.30 to −2.78. — Mesfin (2026), in [intraday_technical_regime.md §1](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md)
- **[C, own, B3] Continuation after 15-minute moves, 5-minute data, 60 sessions** (about 1,200 checks per index).
  - After all moves, the mean signed continuation is −0.03 to +0.13 bp for Nifty at +5 to +30 minutes (|t| ≤ 0.5). Sensex is up to +0.60 bp at +30 minutes (t = 1.7).
  - After moves with |z| > 1: −0.37 / −0.45 bp at +5 minutes (t ≈ −1.0 / −1.2) and +1.1 / +1.3 bp at +30 minutes (t ≈ 1.3 / 1.5) for Nifty / Sensex.

  — [output B3](entry_timing_measurements_output.txt)
- **[C, own, C1] Same test at 1-minute resolution, 19 sessions** (379 checks): −0.07 to −0.29 bp at +1 to +10 minutes for Nifty, every |t| ≤ 1.0. — [output C1](entry_timing_measurements_output.txt)
- **[C, own, B2] Cost of the check grid** (vs the first 5-minute close outside the band, 45 sessions):

  | Check interval | Median lag | Nifty extra entry distance, mean / median | Sensex, mean / median | Nifty outcome to 15:10 |
  |---|---|---|---|---|
  | 15 minutes | 10 min | +3.6 / +0.7 bp | +3.0 / 0.0 bp | +15.2 bp |
  | 30 minutes | 25 min | +9.8 / +5.9 bp | +8.1 / +3.6 bp | +10.3 bp |
  | Continuous (5-min closes) | — | — | — | +15.4 bp |

  — [output B2](entry_timing_measurements_output.txt)
- **[C, own, C1] Alert-to-fill delay on actual first band signals** (1-minute data, 19 sessions; 15 Nifty and 17 Sensex signals). Entry worse than the signal price, mean (median):

  | Delay | Nifty, Nifty points | Nifty, bp (mean) | Sensex, Sensex points | Sensex, bp (mean) |
  |---|---|---|---|---|
  | 1 min | +6.1 (+5.0) | +2.7 | +4.4 (+0.1) | +0.6 |
  | 3 min | +9.7 (+6.2) | +4.3 | +7.8 (+5.8) | +1.1 |
  | 5 min | +12.0 (+6.5) | +5.3 | +4.2 (+7.6) | +0.6 |
  | 10 min | +17.8 (+7.8) | +7.9 | +9.6 (−1.4) | +1.3 |

  - The entry was worse in 67–80% of Nifty cases.
  - These signals worked unusually well (Nifty +28.5 bp to 15:10, win 87%). The sample is a trending month, so these are upper-end estimates.

  — [output C1](entry_timing_measurements_output.txt)
- **[C] Backtest-to-live parity.** Six defects found when an intraday system's live days were replayed in its backtest:
  - a data feed that carried 0.1–2% of the true opening-minute volume;
  - adjusted vs unadjusted prices;
  - UTC vs exchange-clock timestamps;
  - inputs downloaded live but not in the replay;
  - sizing past the binding limit;
  - settings that never reached the order path.

  None of them showed in summary statistics. — [Vidovich & Zerjal (2026), arXiv 2610.21846](https://arxiv.org/abs/2610.21846)
- **[C, abstract-level] Latency and adverse selection.** Delays between trader and exchange worsened market-order fills and caused aggressive limit orders to fail, in a large market-order experiment. — [Oxford working paper](https://ora.ox.ac.uk/objects/uuid:cdab1de2-7576-42e2-abae-ab12371eba76/files/rs4655j600)
- **[C, earlier inference] Assumed latency and trade horizon.** Earlier notes assumed 30–90 seconds of manual latency. With a +0.23% / −0.11% index barrier pair, the expected time to resolution is about 22 minutes. — [option_trade_construction.md §6](../Nifty%20options%20multifactor%20quant%20strategy/option_trade_construction.md)

### Inferences
- **What a delay really costs.**
  - Each minute between the signal and the fill costs on average about 0.3–0.4 bp on breakout days in the 45-session estimate (about ₹25–30 per lot at delta 0.5), with a fat right tail. The tail is the fast breakouts, which are also the winners.
  - A 3-minute delay (about ₹75–120 per lot on average, and much more in the tail) uses up 20–30% of the ₹400 budget.
  - The damage shows up as a wider index distance to the structural stop (band edge or VWAP). For a given strike that means a larger rupee loss at the stop.
- **Alert design for a manual trader** (inference; parameters to test):
  1. **Pre-alert ("setup forming").** Send it when, at a 5-minute check, price is within 0.25σ(τ) of the band on the VWAP-consistent side. You are then at the screen with the chain open when the 15-minute close confirms. This shrinks latency without trading early.
  2. **Signal alert payload:** side; signal index level S; structural stop level; target; recommended strike with its max premium; and an **index chase limit** S_max = S ± min(0.15σ(τ)·Open, 0.3·|S − stop|).
  3. **Validity.** The alert is valid while the index stays inside S_max **and** the dashboard's live stop-fit check (₹400 at the stop, including three half-spreads) still passes for some strike in the delta 0.25–0.55 window. A lower-delta strike can restore stop-fit after a small chase.
  4. **Expiry.** The alert expires after 5 minutes or at the next 15-minute check, whichever is first. After expiry, no chasing: re-evaluate at the next check like any other signal.
  5. **Order.** Use a marketable limit at the ask + ≤ 2 ticks. If unfilled after 30–60 seconds, re-price once within the chase limit, then abandon. Never send market orders; SL-M orders are disallowed for options, and freak-trade risk is real.
  6. **Timing within the minute.** Compute the signal on the completed 1-minute bar ending at the check time. The ~18% larger moves in quarter-hour minutes are too small to justify offsetting the check.
- **Backtest the policy, not only fixed delays.** Run the backtest with delay d ∈ {0, 1, 3, 5} minutes *and* the chase limit and expiry rules. Skipped signals count as zero. A signal family that only works at d = 0, or whose sign flips at d = 3, fails (as the spec already says).
- **Measure the real latency.** During the paper phase, timestamp the alert sent, the alert opened, the order placed and the fill, and record the index at each. Use the empirical distribution in the simulator.

### Gaps
- No published measurement of retail manual latency from alert to fill, in India or elsewhere. It must be logged.
- The 1-minute delay estimates rest on 15–17 signals in one month. The 45-session check-grid estimate is better, but still small.
- Not verified: whether Angel One supports index-level conditional (GTT-style) orders on options, which would remove most manual latency.

---

## 7. Recommended timing rules: entry windows, check frequency, technique, filters, defaults, and how to test them walk-forward

### Takeaway
Keep the core clock: 09:45 start, 15-minute checks, 13:30 expiry-day cut-off, 15:00 / 15:10 exits. The evidence supports:
1. bringing the non-expiry last entry forward to about **14:00**;
2. keeping the **14:45 momentum check off**;
3. **no** lunch block, replaced by a room-left-in-time condition;
4. entering **at the confirming 15-minute check with a marketable limit** and an index chase cap, instead of resting limits or extra confirmation bars;
5. treating NR7, inside days and daily-trend alignment as *tilts to test*, not gates.

Most of these are grade C. The paper phase runs with frozen rules ([docs/decisions.md](../../docs/decisions.md)), so they belong in the 2019–2026 simulation as pre-registered variants, not in live rules.

### Cited Findings
(Summary of the evidence above. Each line points to its section.)
- **Opening window.** 2× noise, the only significant drift (negative), 40% of daily extremes set, widest option spreads and noisy VIX at the open. — §1, §2 [A for the shape; C for the rest]
- **Check grid.** 15-minute checks cost about 0.7 bp median / 3–4 bp mean vs continuous; 30-minute checks cost about 4–6 bp median / 8–10 bp mean, with worse outcomes. — §6 [C]
- **Room left.** It shrinks from 48 to 21 bp median max excursion between 10:15 and 14:15. — §4 [C]
- **Last hour.** No last-hour momentum in 2023–2026; reversal after the auction. — §1 [C], with the post-publication decay elsewhere [B]
- **Entry technique.** Resting limits are adversely selected; a confirmation bar gives no benefit. — §3 [B theory, C own]
- **Contraction.** No next-day range expansion after NR7 or a squeeze; NR7 and inside-day conditioning are suggestive in three markets. — §3 [B/C]
- **Multi-timeframe.** No evidence for a hard filter. — §5 [C/D]

### Inferences

#### A. Recommended rules (defaults) with evidence grades

| # | Rule | Current | Recommended default | Variants to test | Grade | Main reason |
|---|---|---|---|---|---|---|
| 1 | Earliest entry | 09:45 | **Keep 09:45** | 10:00 and 10:15, for longs only and for both sides | B/C | Opening noise, spreads and VIX first print; first-hour drift is negative (works against calls) |
| 2 | Check frequency | Every 15 min | **Keep 15 min** on the completed 1-min bar at :00/:15/:30/:45. Add a 5-min "setup forming" pre-alert | 5-min checks; 30-min checks (Zarattini) | C | 15-min loses about 1 bp median vs continuous; 30-min loses about 4–6 bp median and had worse outcomes |
| 3 | Last entry, non-expiry | 14:30 | **14:00** | 13:30 / 14:00 / 14:30 | C | Remaining room and late-signal quality; a 14:30 entry has 40 min to the 15:10 exit; spreads widen into the close (US, B) |
| 4 | Last entry, expiry day | 13:30 | **Keep 13:30** | 13:00 / 13:30 | C (model) | 0DTE value decay after 13:00; auction reference VWAP 15:00–15:15; expiry-day midday continuation was decent |
| 5 | Lunch window 11:30–13:30 | Allowed | **Allowed**, with a room-in-time gate: expected remaining max excursion (σ_rem-based) ≥ 2 × (target distance + theta drag to the deadline) | Gate multiplier 1.5 / 2 / 2.5; hard block (as a control) | C | No evidence midday signals are worse; less room and pace |
| 6 | 14:45 momentum check | Research-only | **Keep off** for alerts; shadow-log it | Re-test on 2019–2026 futures, by gamma and expiry state | B (decay) / C (own) | No last-hour momentum 2023–2026; negative after the auction |
| 7 | Entry technique | 15-min close outside band + VWAP side | **Enter at that check**; no pullback limit, no extra confirmation bar | Band-edge retest limit (15-min validity); 15-min persistence confirmation | B/C | Adverse selection of limits; confirmation neutral |
| 8 | Order handling | Limit at mid + 1 tick, chase ≤ 2 ticks | **Marketable limit at ask + ≤ 2 ticks**; index chase limit S ± min(0.15σ(τ)·Open, 0.3·\|S − stop\|); live stop-fit recheck; alert expiry 5 min or next check | Chase limit 0.10 / 0.15 / 0.25σ; expiry 3 / 5 / 10 min | C/D | A premium-tick cap does not bound index drift; misses concentrate on winners |
| 9 | Band width V | k (spec) | **V = 1.0 baseline; V_long = V_short + 0.25** as the first variant | V ∈ {1.0, 1.25, 1.5} | B (Zarattini) / C | Wider band: better per-trade results in SPY and here; longs face negative drift |
| 10 | Contraction filters | None | **Feature-only:** prior-day NR7 (tilt +), prior inside day (tilt −) | As meta-model features vs a hard veto on inside days | B/C | Suggestive in SPY, Nifty and Sensex; N = 40–50 per index |
| 11 | Multi-timeframe alignment | Shown on day card | **Not a gate.** At most one shrunk feature (sign of close − SMA20) | Feature in/out | C/D | No rigorous evidence; mixed own results |
| 12 | Exit time, non-expiry | 15:10 | **Keep 15:10**; test 15:00 | 15:00 / 15:10 | D | Auction reference window 15:00–15:15; spot frozen after 15:15 |
| 13 | Event days | Spec gates | **Keep:** no entries until 30–45 min after RBI; enter after the morning IV crush on event days | — | C | [macro_crossasset_drivers.md](../Nifty%20options%20multifactor%20quant%20strategy/macro_crossasset_drivers.md) |

#### B. Walk-forward test protocol for these timing variants
1. **Data.**
   - Nifty and Sensex near-month futures, 1-minute, 2019–2026 (the spec's backfill). Spot alone cannot give VWAP or volume.
   - Keep running `fetch_intraday_yf.py` weekly to accumulate a free 1-minute spot archive.
   - Start the SmartAPI option-depth logger now (ATM ± 3, every minute). It gives the spread and IV time-of-day profiles that §2 lacks.
2. **Baseline** = the frozen rule set. Test **one dimension at a time**, in the pre-registered order of the table: cut-offs (3, 4, 6) → order handling and the delay/chase policy (8) → entry technique (7) → band width and long/short asymmetry (9) → check grid (2) → features (10, 11) → earliest entry (1). Add every variant to the trial count used for the deflated Sharpe ratio and PBO ([signal_fusion_validation.md](../Nifty%20options%20multifactor%20quant%20strategy/signal_fusion_validation.md)).
3. **Folds.** Expanding annual folds: train ≤ Y−1, test Y, for Y = 2021…2026. Run Nifty and Sensex separately. Report Thursday-expiry and Tuesday-expiry eras and the post-auction months separately.
4. **Execution model.**
   - Entry at the check + d ∈ {0, 1, 3, 5} minutes, with the chase-limit and expiry rules applied. Unfilled or expired signals score 0.
   - Option P&L from the spec's business-time pricer.
   - Half-spread multipliers by time of day until replaced by logged data: ×2 before 09:30 and after 14:45, ×1.5 for 09:30–10:00.
   - The spec's exits: index stop and target, VWAP cross, 45-minute stall, 90-minute deadline, hard exit.
5. **Metrics.** Net ₹ per *signal* and per *trade*; P(target before stop); and per-day **paired differences** vs the baseline. Variants trade the same days, so pairing removes most day-to-day noise. Time-of-day buckets are reported as diagnostics only.
6. **Adoption rule** (all required):
   - net ₹ per signal improves in ≥ 4 of 6 out-of-sample years;
   - it improves in both indices;
   - the paired mean improvement is > 2 SE;
   - the change has a stated mechanism.
   
   Otherwise keep the simpler rule.

#### C. Design decision under sample-size pressure (flagged per project rules)
- **What matters.**
  - The timing refinements above are worth roughly 2–10 bp per signal (₹150–800 per lot at delta 0.5) if real. That is economically large relative to the ₹400 risk.
  - Per-signal SD is about 55 bp, so detecting a 5 bp difference at t = 2 needs about (2 × 55 / 5)² ≈ 480 independent signals. That is about 4 years at about 125 signals per year per index. Paired testing on the same days should need far fewer, but the variance of the paired difference is unknown.
  - Our 60-session and 19-session samples can detect only differences of about 20 bp or more. The most likely outcome of testing time-of-day buckets on them is noise.
- **Options.**
  - **(a) Mechanism-backed changes only.** Adopt only rules 3, 6, 8 and the "no pullback limit" part of rule 7 into the *simulation baseline* now, since they rest on mechanism and on direction-consistent evidence. Cheap, and low overfitting risk. Con: still grade C.
  - **(b) Full grid.** Test the whole grid on 2019–2026 futures data. Most informative. Con: needs the backfill, and adds trials that raise the deflated-Sharpe hurdle.
  - **(c) Pilot first.** Run a 4–6 week pilot of the option-depth logger plus latency logging before any order-handling decision. About zero cost; it measures the two biggest unknowns.
- **Recommendation: (a) + (c) now, and (b) before adopting any filter (rules 9–11).** What would change it: if the paired-difference SD from the pilot or backfill is under about 20 bp, the full grid becomes affordable and (b) can come first.
- **What cannot be known yet.**
  - Nifty and Sensex weekly-option spreads by time of day.
  - Real manual latency.
  - Paired-difference variance.
  - Whether post-auction behaviour (last-hour reversal, early continuation) persists beyond 53 sessions.
- **Record the decision.** Record the decision and its reason in [docs/decisions.md](../../docs/decisions.md). This note does not modify that file.

### Gaps
- Everything in table A rests on 2023–2026 spot data and short recent samples. None of it is grade A, and the strongest pieces are grade B theory (adverse selection) plus consistent grade C measurements.
- Option-level validation (spreads, IV path, theta by time of day) waits on the option-depth logger.
- The interaction between timing rules and the spec's other gates (VWAP side, room to run vs levels, breadth, OFI veto, meta-model) is untested. A timing rule that helps the raw trigger may be redundant once those gates apply.
