# Exit timing and trade management for intraday long Nifty/Sensex weekly options (Oct 2026)

Scope: stops, profit targets, trailing stops, time stops, breakeven moves and the behavioural/option-specific side of exits for the alerts-only system (one lot of Nifty, Tuesday expiry, lot 65, or Sensex, Thursday expiry, lot 20; ₹10,000 capital; ₹400 risk at the stop; manual execution in Angel One). It builds on [option_trade_construction.md](<../Nifty options multifactor quant strategy/option_trade_construction.md>) and the [main report](<../../reports/Nifty options multifactor quant strategy.md>), and does not repeat what they establish (SL-M ban, business-time pricing, theta table, cost model, barrier-probability formula).

Evidence grades: **A** = peer-reviewed and robust on real data; **B** = peer-reviewed but limited, non-intraday, lab or theory (B− = academic working paper); **C** = practitioner or independent backtest; **D** = anecdote or unverified. **[calc]** = my own Monte Carlo or arithmetic under stated assumptions (not evidence about markets). **[sib-C]** = descriptive Nifty/Sensex measurements by a sibling researcher in this folder ([entry_timing_measurements_output.txt](entry_timing_measurements_output.txt): Yahoo spot index, 60-min bars Nov 2023–Oct 2026, 5-/1-min bars for the last ~60/19 sessions).

**The Monte Carlo used throughout** ([exit_rules_mc.py](exit_rules_mc.py), output in [exit_rules_mc_output.txt](exit_rules_mc_output.txt)): 40,000 one-minute Brownian index paths per cell, common across exit policies so differences are paired. Pricing follows the earlier notes: Black-76, business-time clock, IV = India VIX 14.67, realised intraday σ 0.65%/day (0.45% in "low-vol" cells), ₹57 fixed costs, half-spread ₹0.10/₹0.20, with stop exits paying three half-spreads. Stop exits fill at the first 1-minute close beyond the stop, which models alert latency; targets fill exactly at the level, which models a resting limit. The instrument is a Nifty call: 0DTE strike 22600 (Δ 0.39 at 10:00, Δ 0.35 at 12:30) or 1DTE strike 22650 (Δ 0.36 at 10:00). Stop b = 0.10% and fixed target a = 2.5b. Hard exits are 15:00 on expiry and 15:10 otherwise. Seven post-entry "regimes":
- **nodrift:** martingale.
- **const:** +0.4%/day drift all session, about 60% hourly accuracy.
- **decay30:** the same total drift with a 30-minute half-life.
- **revert:** failed breakout, pulled back toward VWAP with a 60-minute half-life.
- **trendpm:** ±0.8%/day trend, right 60% of the time.
- **lowvol-nodrift** and **lowvol-const:** the first two cells at σ 0.45%.

The current rule set is policy **P0**: index stop, fixed 2.5× target, stall exit at 45 minutes, 90-minute deadline. The strike chosen loses about ₹750 at the stop, so 1R ≈ ₹750 in these tables. With the ₹400 cap the rupee numbers scale roughly with delta, but the per-trade fixed costs do not. Limitations: no jumps, no U-shaped intraday volatility, constant IV, an equal-weighted VWAP proxy, and no spot–vol beta.

---

## 1. Stop-loss rules: when do they add value, and should an option buyer stop on the underlying or on the premium?

### Takeaway
Stops cannot add expectancy to a driftless price. They help only when the post-entry drift runs *against* the position: momentum, or a failed breakout that keeps going. They cost return when the trade's drift is favourable or when price mean-reverts after stopping out. Every rigorous test finds they mainly cut risk, and tight stops lose value after costs. For this system the stop's job is to enforce the ₹400 cap, not to add edge. Keep it on the **index level**, with the premium SL-limit only as a catastrophe backstop. At equal rupee distance, a premium stop behaves like an index stop plus a hidden time stop, because theta drags the premium down to the trigger.

### Cited Findings
- **[B] Kaminski & Lo (J. Financial Markets 2014):** under a random walk, simple stop-loss rules always reduce expected return. They add value only when returns have momentum (serial correlation), and do not help under mean reversion. In US data for 1950–2004 the "stopping premium" was about 50–100 bp/month in stop-out periods (as extracted in the earlier note). Certain stop policies raised return and cut volatility at longer sampling frequencies — [MIT PDF](https://dspace.mit.edu/bitstream/handle/1721.1/114876/Lo_When%20Do%20Stop-Loss.pdf), [MIT record](https://dspace.mit.edu/entities/publication/bb69ca4b-0cdc-487f-831d-63b2e84fafee). The full text could not be re-read this session (HTTP 429).
- **[B] Lo & Remorov (MIT working paper, Nov 2015), US stocks 1964–2014, daily data, 0.2% trading cost:**
  - Tight stops (daily, 0 to −6%) significantly underperformed buy-and-hold after costs. Wide 10-day stops matched it on a risk-adjusted basis through lower downside volatility, higher skew and smaller drawdowns.
  - Tight-stop performance rises roughly linearly with volatility and autocorrelation.
  - Stock autocorrelations turned significantly negative in the second half of the sample, which was unfavourable for stops.
  - Delayed execution beat immediate execution because of one-day reversal.
  - Spreads widen in crashes and hurt stop fills.

  Sources: [MIT DSpace](https://dspace.mit.edu/handle/1721.1/107017), [CXO summary](https://www.cxoadvisory.com/equity-premium/stop-losses-on-stock-positions-in-depth).
- **[B−] Han, Zhou & Zhu, "Taming Momentum Crashes: A Simple Stop-Loss Strategy" (working paper; US momentum deciles 1926–2011):**
  - A 10% monthly stop cut the worst equal-weighted momentum month from −49.79% to −11.34%, and the value-weighted one from −65.34% to −23.69%.
  - Mean returns and Sharpe ratios were reported as "more than doubled".
  - Results are gross. Critics suggest deducting 300–600 bp a year for trading.

  Sources: [Alpha Architect](https://alphaarchitect.com/taming-the-momentum-roller-coaster-fact-or-fiction/), [CXO](https://www.cxoadvisory.com/?p=25071). Stops paid off here because the underlying strategy has crash-type adverse momentum.
- **[B] Clare, Seaton, Smith & Thomas (J. Asset Management 2013), S&P 500 1952–2011:** popular stop-loss rules did not add value to a 200-day moving-average rule, and month-end decisions beat more frequent trading — [City repository](https://openaccess.city.ac.uk/17842/), [RePEc](https://ideas.repec.org/a/pal/assmgt/v14y2013i3d10.1057_jam.2013.11.html).
- **[B] Lei & Li (Financial Services Review 2009), NYSE/AMEX stocks 1970–2005:** fixed and trailing stops gave returns statistically indistinguishable from buy-and-hold. Trailing stops reduced risk. In simulations neither type changed returns, with or without autocorrelation — [FSR](https://openjournals.libs.uga.edu/fsr/article/view/4933), [CXO summary](https://www.cxoadvisory.com/technical-trading/using-trailing-stop-losses-to-reduce-risk).
- **[B] Dai, Marshall, Nguyen & Visaltanachoti (Int. Review of Finance 2021), US stocks 1926–2016:** trailing stops have lower mean returns than a mean-variance benchmark but reduce total and downside risk. Costs erode tight thresholds, while wider ones stay useful after costs — [RePEc](https://ideas.repec.org/a/bla/irvfin/v21y2021i4p1334-1352.html).
- **[B−] Baule, Schlie & Zhou (2025 working paper, US stocks, high-frequency data):** average intraday return autocorrelations are mostly negative, and reversals are strongest at **15-minute horizons**. Continuation appears only at sub-minute horizons, in larger stocks, in market stress and in the first half-hour. The authors tie this to dealer inventory and option market-maker hedging — [OptionMetrics summary](https://optionmetrics.com/?p=2611) (SSRN 5227714). A tight stop with a 15–30-minute life is therefore exposed to the horizon where reversal is strongest.
- **[B] Dealer gamma (from earlier notes):** positive market-maker gamma strengthens intraday reversal, so stops get run. Negative gamma strengthens momentum, so stops help — [Dim, Eraker & Vilkov](https://dx.doi.org/10.2139/ssrn.4692190).
- **[sib-C] Nifty hourly noise-band breakouts, first signal of the day, held to 15:15, Nov 2023–Oct 2026:**
  - 368 signals averaged +5.4 bp (t = 1.88) with a 55% win rate.
  - The **median maximum adverse excursion was −21 bp**.
  - Breakouts that had failed by the next hourly check (23% of signals) averaged −18.3 bp (t = −3.47).

  Source: [entry_timing_measurements_output.txt](entry_timing_measurements_output.txt), section A5/A6.
- **[data, earlier note]** The Nifty moves at least 0.11% against its open on 85% of days (2024–2026) — [option_trade_construction.md §6](<../Nifty options multifactor quant strategy/option_trade_construction.md>).
- **[calc] Underlying vs premium stop.** The test (P8) set a premium stop at the same rupee loss as the index stop at the moment of entry. Against the index stop it changed EV per trade as follows:

| Scenario | 0DTE, 12:30 entry | 1DTE |
|---|---|---|
| Persistent drift | −₹15 | −₹9 |
| No drift | +₹12 | −₹1 |
| Failed breakout | +₹59 | +₹14 |
| Low vol, no drift | +₹41 | +₹5 |

  Theta drags the premium to the trigger without any index move, so the premium stop doubles as a time stop. It is costliest on afternoon 0DTE trades.
- **[calc] Value of the index stop itself.** P11 removed the index stop and kept only a ₹1,000 premium backstop plus the target and time stops (0DTE, 10:00 entry):

| Scenario | EV change vs P0 |
|---|---|
| Persistent drift | +₹36 |
| Drift with 30-min half-life | +₹43 |
| No drift | −₹17 |
| Failed breakout | −₹81 |
| Low vol, no drift | −₹39 |
| Trend of either sign | −₹1 |

  This is the Kaminski–Lo pattern: the stop pays only when drift is adverse.

### Inferences
- **Optional stopping:** for a martingale price, no bounded exit rule changes expected gross P&L ([optional stopping theorem](https://en.wikipedia.org/wiki/Optional_stopping_theorem)). Exit rules only reshape the distribution: win rate against payoff size. Any rupee gain from exits must come from four sources:
  1. Conditional drift after entry (momentum or reversal).
  2. The carry of the position: theta net of realised gamma for a long option.
  3. Cost asymmetries, since stop exits pay more spread.
  4. Execution conventions.

  On a near-martingale index like intraday Nifty (open-to-close drift −0.069%/day; 15-minute moves show no continuation at 5–30 minutes [sib-C, B3]), **exits cannot rescue a no-edge entry**. In the MC's no-drift column every policy loses ₹110–₹170 per trade.
- The 0.08–0.15% stop sits **inside** the typical adverse excursion of the very breakouts it protects (median MAE ≈ 21 bp [sib-C]). It works as a "timing is right in the next ~20 minutes" filter that will stop out many eventually-correct signals. That is acceptable only because the ₹400 cap forces it. It is the strongest reason to gate entries to momentum regimes (negative dealer gamma, high VIX, breakout days), which is exactly where Kaminski–Lo and Dim et al. say tight stops stop hurting.
- Keep the stop on the index (or near future), evaluated on 1-minute closes. The premium SL-limit stays as a catastrophe backstop only. Budget the realised stop loss at about 1.3× the nominal Δ·lot·S·b: in the MC the loss at the stop averaged ₹750 against a nominal ₹573, from overshoot, three half-spreads, costs and theta.

### Gaps
- No study found tests stops for **option buyers**, or index-trigger against premium-trigger stops on real option data. The comparison above is model-only.
- No Indian evidence was found on SL-limit non-fill rates in index options, or on intraday autocorrelation by horizon for Nifty/Sensex beyond the sibling measurements.
- Kaminski & Lo's numerical results were not re-verified from the full text this session.

---

## 2. Profit targets vs trailing stops vs letting winners run

### Takeaway
For momentum and breakout entries, the best evidence and the theory both point the same way: **do not cap winners with a fixed target**. Exit with a trailing stop (VWAP- or band-based in the Zarattini design) or at a time limit. This trades a lower win rate for a fatter right tail. The 2.3–2.5× fixed index target is the single rule that most limits expectancy in every MC scenario with a favourable drift. A trail that activates after +1× the stop distance and sits 1.5 stop-distances behind the running maximum, combined with a VWAP ratchet, beat the current rules in all 21 modelled cells. The exception: in failed-breakout or mean-reverting regimes a *tighter* target wins, so the regime gate decides which side of the trade-off you are on.

### Cited Findings
- **[C] Zarattini, Aziz & Barbon, "Beat the Market" (Swiss Finance Institute RP 24-97), SPY 1-minute data May 2007–2024, with commissions and slippage.** Two exit designs were compared:

| Exit design | Sharpe | Daily hit rate | Trade hit rate | Annual return | Volatility | Max drawdown | Skew | Worst day | Trades |
|---|---|---|---|---|---|---|---|---|---|
| Stop at the opposite noise-band edge | 0.61 | 54% | 53% | 6.2% | 10.9% | 21% | −1.24 | −10.3% | 5,494 |
| Trailing stop = max(current band, VWAP) for longs | 1.24 | 43% | 37% | 9.7% | 7.7% | 12% | +1.29 | −4.8% | 7,668 |

  - There is **no profit target**. Positions close at the market close, and signals and stops are checked only on the half-hour.
  - A **VWAP-only** trailing stop held trades longer with fewer trades (7,964 → 6,728). IRR fell 1.6 points, volatility rose 1.2 points, and Sharpe fell from 1.35 to 1.17.
  - Trend continuation pays from 10:00 to noon, pauses at lunch and resumes from 14:00 to the close.
  - The authors' update shows 2024 at +32.2%.

  Source: [paper PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download) (Tables 1, 2, 4; FAQ Q18, Q22, Q24), [SFI listing](https://www.sfi.ch/de/publications/n-24-97-beat-the-market-an-effective-intraday-momentum-strategy-for-s-p500-etf-spy).
- **[C] Opening-range breakout, QQQ (Zarattini & Aziz 2023):**
  - The exit is a 10R target or the close: 24% hit rate and +0.13R per trade, with commission but no spread or slippage — [CXO](https://www.cxoadvisory.com/technical-trading/day-trading-with-an-opening-range-breakout-strategy).
  - An independent replication of the related QQQ ORB fell from Sharpe 1.06 to 0.23 once slippage was added — [Brusco repo](https://github.com/giovannibrusco/zarattini-2023-orb-qqq).
  - [D/C] A blog replication on five index CFDs (2015–2026) reproduced the gross result, but the net result was indistinguishable from zero — [MQL5 blog](https://www.mql5.com/en/blogs/post/776235).
- **[B, theory] Glynn & Iglehart (Management Science 1995):** with a positive-drift random walk or GBM, it is optimal *never* to use a trailing stop. Hold instead — [INFORMS](https://pubsonline.informs.org/doi/10.1287/mnsc.41.6.1096), as summarised in [Leung & Zhang](https://arxiv.org/abs/1701.03960).
- **[B, theory] Shiryaev, Xu & Zhou (2008), "Thou shalt buy and hold":** under GBM the optimal sale time is bang-bang. Hold to the horizon if α = (μ − r)/σ² > ½; sell at once if α < 0. There is no interior target. Source: [Majumdar & Bouchaud comment](https://arxiv.org/abs/0809.2878), which extends the result to the gap 0 < α ≤ ½.
- **[B−, theory] Leung & Zhang, "Optimal trading with a trailing stop":** under mean-reverting (exponential O-U) prices it is optimal to place a **limit sell (take-profit) together with the trailing stop** at entry — [arXiv 1701.03960](https://arxiv.org/abs/1701.03960).
- **[B, theory] Imkeller & Rogers ("Trading to stops", SIAM J. Financial Mathematics 2014):** compares fixed and trailing stop rules under arithmetic Brownian motion, and argues that stops also reduce trading frequency and costs — [SIAM](https://epubs.siam.org/doi/10.1137/130911706).
- **[B] Osler (J. Finance 2003), FX order books:** take-profit orders cluster at round numbers and stop-losses just beyond them. Trends therefore tend to stall at round levels and accelerate once they break — [Wiley](https://onlinelibrary.wiley.com/doi/abs/10.1111/1540-6261.00588) (cited in the main report).
- **[C, cautionary] Li, Laryea & Ihlamur (arXiv 2604.27150, 2026), about 900 crypto agent trades:**
  - An in-sample grid of 8,960 exit configurations favoured *tighter* stops, earlier profit capture (75% partial take-profit) and closer trails. Sharpe rose from 0.419 to 0.653 (+56%).
  - The chronological hold-out reached Sharpe as low as −5 in a war-period regime shift, so the authors switched to a randomised split. No deflated-Sharpe correction was applied.

  Source: [arXiv](https://arxiv.org/abs/2604.27150). The optimal exit direction flips with the sample and regime.
- **[calc] Replacing the fixed 2.5× target with a trail (P5: activate at +1b, trail 1.5b, keep time stops).** EV change against P0 per trade, across the three entry cases:

| Scenario | EV change vs P0 |
|---|---|
| No drift | +₹17 to +₹39 (about ₹30 of this is the resting-target fill convention: a fixed target never captures the index overshoot) |
| Persistent drift | +₹71 to +₹101 |
| Drift with 30-min half-life | +₹74 to +₹109 |
| Trend of either sign, 60/40 | +₹105 to +₹157 |
| Failed breakout | −₹16 to 0 |
| Low vol, no drift | +₹3 to +₹15 |

  Win rate falls 2–6 points, average loss shrinks by ₹100–₹130 and average win rises by ₹100–₹390. Two trail widths:
  - Wider (2.0b): +₹118 to +₹141 under persistent drift but −₹77 to −₹97 on failed breakouts.
  - Tighter (1.0b): smaller gains under drift (+₹21 to +₹42) and +₹63 to +₹88 on failed breakouts.
- **[calc] Fixed-target width:**
  - **2.0×:** −₹31 to −₹32 under persistent drift; +₹50 to +₹62 on failed breakouts.
  - **3.5×:** +₹51 to +₹61 under persistent drift; −₹79 to −₹96 on failed breakouts.
- **[calc] Zarattini-style pure VWAP trailing with no target (P16):**
  - Under persistent drift or trend: +₹318 to +₹770 per trade.
  - On failed breakouts: −₹103 to −₹217.
  - Win rate falls to 3–16%, with average wins of ₹2,500–₹7,500 per lot, mostly held to 15:00.
- **[calc] Combined policy P15** (trail 1.5b after +1b, stop also ratcheted to VWAP, no target, time stops only for trades that never reached +1b) **beat P0 in all 21 cells**, by +₹20 to +₹170 (each about 4 or more standard errors). Two summary cells: persistent drift at 10:00 0DTE +₹65 (P0 +₹17 → +₹82), and failed breakout +₹41. Its win rate is 0.21–0.29, against P0's 0.28–0.36.
- **[calc] VWAP-cross exit on top of P0 with a fixed target (P9).** Since price sits above VWAP at entry, this is a VWAP ratchet:

| Scenario | EV change vs P0 (10:00, 0DTE) |
|---|---|
| Persistent drift | −₹30 |
| Drift with 30-min half-life | −₹33 |
| Failed breakout | +₹64 |
| Low vol, no drift | +₹62 |

  It double-tightens an already-tight stop. It works better combined with a trail and no target (P15).

### Inferences
- The fixed target throws away the fat right tail that carries the edge of every intraday momentum design found here: Zarattini's hit rate is only 37–43%, and the 10R ORB target hits 24%. A 2.3× target also locks the payoff ratio at a level the barrier formula ties to a no-edge hit probability of b/(a+b) ≈ 0.29–0.30.
- Whether trailing beats targeting depends on the drift *after* the target level. Under momentum, let it run. Under reversion, take the money. The two theory results agree: Glynn–Iglehart/Shiryaev for drift, and Leung–Zhang for mean reversion. The regime gate therefore decides the exit as well as the entry. If entries are restricted to trend or negative-gamma regimes, as recommended, the trailing exit is the consistent choice.
- For options the trail has an extra advantage. Once the option is in profit its delta has risen, so the index-level trail captures more rupees per point. Theta per rupee of position falls as the strike goes in-the-money.
- Practical form for manual execution: compute the trail on the index and alert on a 1-minute close through it. Treat the planning target (≥2.3× the stop, used by the strike picker for G/L ≥ 1.5) as separate from the actual exit rule.
- Round numbers ([Osler]): when a trail or planning target sits just beyond a Nifty 100-point or Sensex 500-point level, expect stalls there. Treat the level as a test, not a stop trigger, unless the trail is breached.

### Gaps
- No peer-reviewed intraday study compares fixed targets with trailing exits on index futures or options. The Zarattini comparison is in-sample on one ETF, and its exit design was chosen with the data. No Indian test exists.
- No rigorous test of chandelier (ATR-multiple) or parabolic SAR exits was found. Practitioner claims (Le Beau, Clenow-type) were not located with data this session, and Robot Wealth/Quantpedia tests on stops were not found.
- The MC's VWAP is an equal-weighted proxy with no volume profile. Real VWAP is front-weighted by the opening volume, so it moves more slowly early in the session.

---

## 3. Time stops, signal half-life and optimal holding horizon

### Takeaway
At the current barriers (0.10% stop, 0.25% target, σ ≈ 0.65%/day) a trade resolves in about 22–26 minutes on average, so the 45-minute stall and 90-minute deadline bind on only about 10% of trades in normal volatility and about 28% in low volatility. Time stops are cheap insurance:
- They cost at most ₹10–23 per trade when drift persists.
- They save ₹40–90 per trade when the edge is absent, the breakout fails or volatility is low.
- That asymmetry matters more for a long option, because theta charges rent every minute.

The improvement is to apply time stops **only to laggards**, meaning trades that never reached +1× the stop distance, and let trades in trailing mode run to the trail or the hard exit. The signal "half-life" that matters is unknown for this project's entries. The best Nifty proxy says breakout drift, if any, accrues slowly over hours, not minutes.

### Cited Findings
- **[C] Mesfin (arXiv 2605.04004, 2026), MNQ futures 5-minute bars 2021–2025, walk-forward:**
  - None of 14 retail intraday signal families passed.
  - The two positive controls hold **60–75 minutes**: exit at bar 13 (about 65 minutes), and a London-session signal exiting after 60 minutes. That holding time is credited with accumulating enough net return to clear friction.
  - A one-bar (15-minute) entry delay flipped one signal from t = +4.30 to t = −2.78, so its edge was front-loaded.
  - ORB long held 15 bars (75 minutes) earned +2.82 points net with t = 0.88.

  Source: [arXiv](https://arxiv.org/abs/2605.04004).
- **[C] Zarattini et al.:** the edge accrues over hours (10:00–noon and 14:00–close) and positions are held to the close — [paper](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download), FAQ Q18.
- **[B/B−] Intraday momentum literature (from the main report):** first half-hour or rest-of-day returns predict the **last half-hour** (Gao, Han, Li & Zhou 2018; Baltussen et al. 2021). The edge is concentrated at the close, not in the first hour after a signal — [Baltussen et al.](https://academicweb.nd.edu/~zda/intramom.pdf).
- **[B−] Baule, Schlie & Zhou:** reversal dominates at about 15-minute horizons in US stocks — [OptionMetrics](https://optionmetrics.com/?p=2611).
- **[sib-C] Nifty:**
  - After 15-minute moves at the 15-minute checks, continuation over the next 5, 10, 15 and 30 minutes is about zero (|t| ≤ 1.5).
  - The hourly band breakout pays +5.4 bp on average only when held to 15:15. First signals at 11:15 did best (+16.6 bp, t = 3.03, N = 74).
  - The median maximum excursion left after 10:15 is about 48 bp, and 21 bp after 14:15.

  Source: [entry_timing_measurements_output.txt](entry_timing_measurements_output.txt), sections A5, A11, B3.
- **[earlier note] Rent on long options:** realised open-to-close volatility has run at 0.69–0.80 of the VIX-implied intraday move, so a long option held flat loses on average. An ATM 0DTE loses about ₹375/lot per hour at 10:00 and about ₹597/lot per hour at 13:00 with the index flat — [option_trade_construction.md §2, §4](<../Nifty options multifactor quant strategy/option_trade_construction.md>).
- **[calc] Expected resolution time** of a driftless ±barrier pair is E[τ] = a·b/σ². For a = 0.25% and b = 0.10% that is about 22 minutes at σ = 0.65%/day and about 46 minutes at σ = 0.45%. MC mean holding times were 26 minutes (normal vol) and 40 minutes (low vol). Under P0 the stall/deadline exits fired on 9–10% of trades in normal vol and 25–28% in low vol.
- **[calc] Time-stop variants against P0** (per trade, three entry cases):

| Variant | No drift | Failed breakout | Low vol, no drift | Persistent drift | Low vol, persistent drift |
|---|---|---|---|---|---|
| Remove all time stops (P3) | −₹8 to −₹9 | −₹35 to −₹39 | −₹41 to −₹88 | +₹2 to +₹9 | −₹31 to +₹36 |
| Stall 30 min + deadline 60 min for all trades (P2/P14) | +₹5 to +₹13 | +₹38 to +₹43 | +₹22 to +₹52 | −₹4 to −₹10 | +₹7 to −₹23 |

  - With trailing exits, applying time stops to **all** trades (P5) gave up ₹100–₹120 a trade under low-vol persistent drift compared with no time stops (P5b), because it cut runners.
  - Applying them only to laggards (P13: stall 30 / deadline 60 if the trade never reached +1b) kept most of the upside: low-vol persistent drift +₹106 to +₹147 against P0, persistent drift +₹80 to +₹111.
  - The laggard-only version kept no-edge losses at or below P0: no drift +₹17 to +₹40, failed breakout −₹10 to +₹7, low vol no drift 0 to +₹6.

### Inferences
- Keep time stops, tighten them modestly, and condition them on progress. Exit at 30 minutes if the index is within ±0.05% of entry, and at 60 minutes if the trade has not reached +1× the stop distance. Trades already trailing are managed only by the trail and the hard exit.
- The vertical barrier should scale with expected resolution time: 2–3 × E[τ], where E[τ] = a·b/σ²_remaining and σ comes from the HAR remaining-session forecast. On low-vol days that lengthens the deadline. That is the same day type where theta per unit of realised movement is worst, so the laggard rule must stay.
- Do not plan to hold a non-trailing 0DTE long past about 13:30 on expiry day. With the index flat, an ATM option keeps only √(minutes left ratio) of its value, so it loses about 55% between 13:00 and 15:00 [calc].

### Gaps
- No Nifty or Sensex estimate exists of the signal's own drift profile (time to maximum favourable excursion, half-life) for this project's entries. It must be measured; see section 8 for the pilot.
- No peer-reviewed study of time stops for intraday option buyers was found.

---

## 4. Breakeven-stop rules

### Takeaway
Moving the stop to breakeven raises the share of "scratch" trades and lowers expectancy whenever the signal has drift. It helps only in failed-breakout regimes. For an option buyer, **index breakeven is not premium breakeven**: an exit at the entry index level is a net loss of theta, costs and three half-spreads, about ₹100–₹200. So the rule *lowers* the rupee win rate as well as the expectancy. Drop it. A trailing stop that reaches breakeven only after +1.5× the stop distance does the protective job better.

### Cited Findings
- **[theory]** Under a martingale no exit rule changes expected gross P&L ([optional stopping](https://en.wikipedia.org/wiki/Optional_stopping_theorem)). With positive drift, cutting exposure early forfeits drift, the same logic as Kaminski & Lo's random-walk result — [MIT PDF](https://dspace.mit.edu/bitstream/handle/1721.1/114876/Lo_When%20Do%20Stop-Loss.pdf).
- **[D]** A vendor blog's worked example and forum discussion argue that early moves to breakeven cut long-run profitability, especially in trend-following, because normal pullbacks hit a stop at entry. It cites Quantified Strategies backtests that I could not verify — [ATAS](https://atas.net/blog/break-even-in-trading/), [Babypips forum](https://forums.babypips.com/t/statistics-of-setting-break-even-vs-letting-run/126971). No rigorous study was found.
- **[calc] P4 = P0 plus a move of the stop to the entry index level once the index reaches +1b:**

| Scenario | EV change vs P0 |
|---|---|
| Persistent drift | −₹15 to −₹18 |
| Drift with 30-min half-life | −₹7 to −₹17 |
| No drift | +₹2 to +₹14 |
| Failed breakout | +₹44 to +₹60 |
| Low vol, persistent drift | −₹1 to −₹17 |

  The rupee win rate fell from 0.28–0.39 to 0.23–0.33 and the average loss shrank by about ₹120. More trades stopped out in total (64% → 74% at 10:00 0DTE with no drift), with the extra exits being breakeven scratches that still lose money net.

### Inferences
- Do not add a breakeven move. If the owner wants loss protection after a favourable move, use the trail (activate at +1b, trail 1.5b). It lifts the stop only to −0.5b at activation and to entry only after +1.5b, so normal pullbacks do not scratch the trade.
- Any scoreboard that counts index-breakeven exits as non-losses will overstate the win rate. Score every trade in net rupees, as the decision log already says.

### Gaps
- No peer-reviewed or credible practitioner backtest of breakeven stops on intraday index futures or options was found.

---

## 5. Triple-barrier calibration and the overfitting risk of optimising exits

### Takeaway
Exit parameters are among the easiest things to overfit: every stop, target, trail and time limit is a free parameter tuned on the same paths. The defensible practice:
- Set barriers **a priori** in units of the stop distance (R) and of remaining-session volatility.
- Set the vertical barrier from expected resolution time.
- Pre-register at most two or three exit variants.
- Compare them **paired on identical entries**.

Even so, power is low. In the MC the paired per-trade difference between exit variants has a standard deviation of about ₹900–₹1,500 (1.2–2R). Detecting a ₹60/trade (0.08R) improvement at 80% power needs about 2,600 setups. The project's roughly 2,000 historical setups can resolve only large differences, and live trading cannot resolve any. Choose exits from theory plus robustness across regimes, and use the backtest only as a guard against a clear reversal.

### Cited Findings
- **[B] López de Prado (2018), Advances in Financial Machine Learning:** triple-barrier labelling (profit-take, stop and a vertical time barrier, whichever comes first), with horizontal barriers set as multiples of a dynamic volatility estimate, plus meta-labelling — [Wiley](https://www.wiley.com/en-us/Advances+in+Financial+Machine+Learning-p-9781119482086).
- **[B−] Carr & López de Prado (arXiv 1408.1159, 2014):** "calibrating a trading rule using a historical simulation… contributes to backtest overfitting". They propose deriving optimal trading rules (profit-take and stop-loss) from a fitted discrete O-U process **without** backtesting alternatives. Solutions are numerical; closed form is conjectured — [arXiv](https://arxiv.org/abs/1408.1159).
- **[B] Bailey, Borwein, López de Prado & Zhu (Notices of the AMS 2014):** high simulated performance is easily reached after trying a relatively small number of configurations. With 5 years of daily data, no more than about 45 variations should be tried. Under memory effects an overfit strategy's expected out-of-sample return is *negative*, not zero — [CARMA PDF](https://carmamaths.org/jon/backtest.pdf).
- **[B]** The deflated Sharpe ratio corrects for the best-of-N selection — [Bailey & López de Prado](https://www.davidhbailey.com/dhbpapers/deflated-sharpe.pdf). The main report already sets the project budget at 10–15 effective configurations with PBO ≤ 0.2.
- **[C] Exit grids in practice overfit:**
  - Li et al. searched 8,960 exit configurations on about 900 trades and saw a −5 Sharpe chronological hold-out — [arXiv 2604.27150](https://arxiv.org/abs/2604.27150).
  - Mesfin tried 53+ parameter combinations before locking a signal, an exposure the author says "cannot be corrected post hoc" — [arXiv 2605.04004](https://arxiv.org/abs/2605.04004).
  - Lo & Remorov flag snooping from testing many stop settings on one dataset — [CXO](https://www.cxoadvisory.com/equity-premium/stop-losses-on-stock-positions-in-depth).
- **[calc] Power.** Paired standard errors of exit-variant differences were about ₹4–7 per 40,000 trades, so σ_diff ≈ ₹900–₹1,500 per trade. The setups needed for 80% power at two-sided α = 0.05 are n ≈ (2.8·σ_diff/Δ)². Using σ_diff ≈ ₹1,100 for the small differences:

| Detectable improvement per trade | Setups needed |
|---|---|
| ₹60 (≈0.08R) | ≈2,600 |
| ₹100 | ≈950 |
| ₹150 | ≈420 |

### Inferences
- **Barrier-setting recipe** (no outcome data used):
  1. b = the structural stop (band edge or VWAP), capped by the ₹ budget.
  2. Trail activation = +1.0b and trail distance = 1.5b. These are round R-multiples, chosen once and never tuned.
  3. Vertical barrier = min(60 minutes for laggards, hard exit). Optionally scale it by E[τ] = a·b/σ²_remaining.
  4. The labels used to train the probability model keep the fixed planning barriers (target ≥ 2.3b) so p stays comparable with b/(a+b). Exit-policy P&L is evaluated separately on the same setups.
- Treat exit variants as one correlated "cluster" in the registry, since they share entries, but count each as a trial against the 10–15 budget.

### Gaps
- Carr & López de Prado's heat-map conclusions (which rules are optimal at which half-life and forecast) were not re-read this session. Only the abstract-level claim is cited.
- No published guidance was found on triple-barrier widths for intraday index options specifically.

---

## 6. Behaviour: the disposition effect, pre-committed exits and resting orders

### Takeaway
Retail traders sell winners too early and hold losers too long, and intraday futures traders take extra risk in the afternoon after morning losses. The most credible remedy is **pre-commitment through automatic orders**. In a randomised experiment, automatic stop-loss and take-gain orders cut the disposition effect, mainly by forcing loss realisation, while mere reminders did not. Field data agree for stop-loss users. For a manual, alerts-only system, this means:
- Place broker-side orders immediately.
- Never widen the stop.
- Stop for the day after a stop-out.
- Log every override.

Note that a resting take-profit order is itself a pre-committed "sell the winner early" device.

### Cited Findings
- **[A] Odean (J. Finance 1998), 10,000 US discount-broker accounts:** the proportion of gains realised (PGR ≈ 0.148) exceeded the proportion of losses realised (PLR ≈ 0.098) outside December — [Berkeley page](https://faculty.haas.berkeley.edu/odean/papers/disposition/disposition.html), [Wikipedia summary](https://en.wikipedia.org/wiki/Disposition_effect).
- **[B, causal lab evidence] Fischbacher, Hoffmann & Schudy (Review of Financial Studies 2017):** automatic stop-loss and take-gain orders significantly reduced the disposition effect, driven by more realised losses; winners were realised at similar rates. A reminder-only treatment did **not** reduce it, so ex-ante commitment does the work — [working-paper PDF](https://www.twi-kreuzlingen.ch/wp-content/uploads/2017/12/twi-rps-089-fischbacher-hoffmann-schudy.pdf) (doi 10.1093/rfs/hhx016).
- **[B] Richards, Rutterford, Kodwani & Fenton-O'Creevy (European J. Finance 2017), UK individual investors 2006–2009:** stop-loss use is an effective tool against the disposition effect. The bias goes with poorer performance and is stronger in less experienced investors — [Open University](https://oro.open.ac.uk/44069), [RePEc](https://ideas.repec.org/a/taf/eurjfi/v23y2017i2p130-152.html).
- **[B] Nolte (European J. Finance 2012), FX traders:** an *inverted* disposition effect is largely driven by traders closing with take-profit and stop-loss limit orders — [RePEc](https://ideas.repec.org/a/taf/eurjfi/v18y2012i10p885-919.html).
- **[B] Linnainmaa (J. Finance 2010), all Finnish individual investors:** disposition-like patterns arise **mechanically** from limit orders, which are price-contingent and adversely selected — [RePEc](https://ideas.repec.org/a/bla/jfinan/v65y2010i4p1473-1506.html). A later working paper argues the link runs both ways — [De Winne, Luong & Palan](https://ideas.repec.org/p/ajf/louvlf/2022012.html).
- **[A] Coval & Shumway (J. Finance 2005), CBOT proprietary traders:**
  - Traders are highly loss-averse and regularly take above-average afternoon risk to recover morning losses.
  - Traders with morning losses are about 16% more likely to take above-average afternoon risk.
  - Prices they set reverse quickly.

  Sources: [RePEc](https://ideas.repec.org/a/bla/jfinan/v60y2005i1p1-34.html); the 16% figure is from the [BYU summary](https://scholarsarchive.byu.edu/facpub/9284).
- **[A] Locke & Mann (J. Financial Economics 2005), futures floor traders:** traders hold losses significantly longer than gains, without measurable cost. Relative trading discipline predicts subsequent success — [doi](https://doi.org/10.1016/j.jfineco.2004.01.004).
- **[B−, survey] Choubey & Joshi (2024), 250 NSE options traders:** the disposition effect is present. Time decay and open interest act as "enablers", alongside herding — [Finance: Theory and Practice](https://financetp.fa.ru/jour/article/view/2830).
- **[O, from the main report]** SEBI's August 2026 study found that 87.7% of individual F&O traders lost money in FY26 and that loss incidence rises with turnover — [SEBI PDF](https://www.sebi.gov.in/sebi_data/attachdocs/aug-2026/1787233506209.pdf).

### Inferences
- Pre-commit everything that can be pre-committed. Place the SL-limit backstop the moment the entry fills. Set the index alerts for stop, trail activation, trail level, stall and deadline before entry. Write the exit reason into the log.
- When the trail moves, also move the broker-side SL-limit up to the premium equivalent of the trailing index level (about Δ × move) at each 5–10-minute check. A hesitating trader then still has a resting order (not tested).
- Keep "stop for the day after one stop-out" (Coval–Shumway) and "never widen a stop" (the disposition effect). The ₹ cap is the experiment's risk unit, and widening it changes the tested strategy.
- A trailing exit puts more weight on discipline than a fixed target does. It needs repeated manual actions on alerts while in profit, which is exactly when the disposition effect tempts early selling. With win rates of 0.21–0.29 there will be long losing streaks (median longest streak of 7 at 42%, from the main report, and longer at 25%). Plan for this explicitly. Selling winners before the trail is hit is the disposition effect in action and must be logged as an override.

### Gaps
- No account-level study of the disposition effect or exit behaviour among Indian intraday option buyers was found; the only Indian evidence is a survey.
- Whether Angel One supports index-triggered, trailing or GTT orders on index options was not verified, so automation of the trail is uncertain.

---

## 7. Option-specific exit issues: closing auction, IV crush, late-day spreads, gap risk

### Takeaway
Options add four exit constraints the index does not have:
1. **Theta and realised-vs-implied variance** make time in the trade costly. Laggard time stops follow from this.
2. **Spreads widen sharply in the final hour**, and stop exits pay more, so exit before about 15:00 on expiry and use marketable limits.
3. **Since August 2026 the index barely prints after 15:15**, during the closing auction, so index-level stops are blind there. Expiry settlement runs through that auction, so hold nothing into it.
4. **Scheduled events crush IV** after the announcement.

Long intraday options carry no overnight gap risk. The intraday gap equivalent is an event or fast market in which an SL-limit fails to fill. The backstop limit therefore needs a wide buffer, and nothing should be held through scheduled announcements.

### Cited Findings
- **[O/C, earlier notes]** SL-M orders are banned for options on NSE (since 27 Sep 2021) and BSE (since 9 Oct 2023), so only SL-limit exists. An SL-limit with the limit placed well beyond the trigger behaves like SL-M — [Zerodha bulletin](https://zerodha.com/marketintel/bulletin/305785/stop-loss-market-sl-m-orders-blocked-for-index-options), [Zerodha support](https://support.zerodha.com/category/trading-and-markets/charts-and-orders/order/articles/how-to-use-sl-l-order-like-a-sl-m-order).
- **[B] US 0DTE retail:** effective spreads are 10.5% of mid with under one hour to expiry, against 4.5% at 3–24 hours. Buys pay more than sells — [Beckmeyer, Branger & Gayda](https://wp.lancs.ac.uk/fofi2024/files/2024/04/FoFI-2024-146-Leander-Gayda.pdf).
- **[C, main report]** Expiry settlement has come from the 15:15–15:35 closing auction since 3 August 2026. On 3 September 2026 the Sensex indicative level fell about 2.5% in the auction and put premiums jumped 400–500% — [MarketsEasy](https://marketseasy.in/blog/sebi-expiry-settlement-price-cas-review-2026).
- **[sib-C] Index readings in the last minutes:**
  - The spot index shows a median of **2** distinct 1-minute closes between 15:16 and 15:29 per day in the auction period.
  - Sensex 5-minute ranges in the 15:15 block averaged 53 bp on expiry days, against 8–10 bp earlier in the afternoon.

  Source: [entry_timing_measurements_output.txt](entry_timing_measurements_output.txt), C1/B1.
- **[own data, main report] Implied volatility around scheduled events:**
  - On RBI decision days India VIX fell 1.66% the day before and 1.95% on the day (t = −3.81).
  - On Budget days VIX fell 9.3% while the range ran 2.1× implied.
  - On the 2024 election result VIX rose 27.75%, then fell 29% the next day.

  Source: [macro checks output](<../Nifty options multifactor quant strategy/macro_crossasset_checks_output.txt>).
- **[earlier note, calc] Effect of IV level and theta:**
  - A 2-point IV drop cuts a 0.42%-OTM 0DTE call's gain at the target from ₹840 to ₹366.
  - An ATM 0DTE keeps about 85%, 63% and 40% of its value at 11:00, 13:00 and 14:30 with the index flat.

  Source: [option_trade_construction.md §2–3](<../Nifty options multifactor quant strategy/option_trade_construction.md>).
- **[B−, India] Agarwal, Ghosh, Prabhala & Zhao:** "positions not closed in day trading result in significant losses" — [FMA PDF](https://www.fma.org/assets/docs/Derivatives2025/Zhao.pdf).

### Inferences
- Keep the hard exits: **15:00 on expiry days** and **15:10 otherwise**, both before the 15:15 auction freeze. On expiry days, trades still trailing at 14:45 face roughly doubled spreads. Consider requiring the 15:00 exit to be a limit at mid minus 1 tick, placed at 14:55 (untested).
- **Event rule:** if a trade is open 5 minutes before a scheduled intraday announcement (RBI decision, Budget speech segments, election counting milestones), exit. The post-event IV fall works against a long option even when direction is right. This is consistent with the entry blackouts in the main report.
- **Backstop SL-limit:** keep the earlier design, a trigger at entry − (₹cap + slippage)/lot and a limit a further max(10% of premium, 5 ticks) below. After the trail activates, ratchet it up as described in section 6. A breached backstop that does not fill must trigger an immediate marketable limit from the alert.
- On 0DTE afternoons, theta per hour roughly doubles from morning levels. The laggard time stop protects against it; the trailing runner pays for it with delta.

### Gaps
- No measurement was found of Nifty/Sensex weekly option bid-ask spreads by time of day near expiry in 2026, or of SL-limit fill rates. Collect both with the snapshot logger.
- Intraday IV behaviour around the 15:15 auction, and whether option quotes keep updating while the spot index is frozen, was not verified.

---

## 8. Recommended exit rule set and pre-registered exit variants

### Takeaway
Change one thing materially, the fixed target to a trailing exit. Make one rule smarter: time stops for laggards only. Drop nothing that exists, but do not add a breakeven move. Keep the index stop, premium backstop, VWAP rule (as a ratchet), hard exits and daily stop. Spend only **two trial slots** on exits, a fixed-target baseline against a trailing variant, compared paired on identical setups. Add a third, Zarattini-style VWAP runner, only if the entry is the noise-band breakout. Pre-commit the decision rule. The data cannot pick a winner with confidence, so choose from theory and regime-robustness, and let the backtest only veto a clear reversal.

### Cited Findings
- Evidence base: sections 1–7 (Kaminski & Lo; Lo & Remorov; Zarattini, Aziz & Barbon; Glynn & Iglehart; Shiryaev, Xu & Zhou; Leung & Zhang; Fischbacher et al.; Coval & Shumway; Bailey et al.) and the project MC [calc] in [exit_rules_mc_output.txt](exit_rules_mc_output.txt).
- Project constraints: frozen-rule paper phase, simulation-first validation, and a 10–15-configuration budget — [docs/decisions.md](<../../docs/decisions.md>), [main report](<../../reports/Nifty options multifactor quant strategy.md>).

### Inferences

**A. Recommended default exit rule set ("E-trail")**

| # | Rule | Keep / change / drop | Default | Main support |
|---|---|---|---|---|
| E1 | Primary stop on the **index**: structural level (noise-band edge or VWAP), 0.08–0.15% from entry, evaluated on 1-min closes, executed by marketable limit (bid − 2 ticks) | **Keep** | b from structure, capped so the expected loss at the stop, including the ~1.3× overshoot/cost factor, is ≤ ₹400 | §1: risk cap; index avoids theta/IV noise; B + calc |
| E2 | Broker-side **SL-limit premium backstop** at entry | **Keep**, and ratchet it up once trailing | trigger = entry − (₹400 + slippage)/lot; limit = trigger − max(10% premium, 5 ticks) | SL-M ban (O); §6 pre-commitment (B) |
| E3 | Fixed index target ≥ 2.3× stop as the **exit** | **Change**: keep it only as the *planning* target for strike choice and the G/L ≥ 1.5 / EV gate | planning a ≥ 2.3b | §2 |
| E4 | **Trailing exit** (new) | **Add**, replacing E3 as the exit | activates when the index reaches +1.0b; stop = max(current stop, running max − 1.5b) | §2: theory, Zarattini (C), calc in all drift/trend cells |
| E5 | VWAP cross against the position | **Keep, as a ratchet**: stop = max(E1/E4 level, VWAP) once VWAP rises above the initial stop. Not a separate early exit when the stop already sits at VWAP | 1-min closes | Zarattini band+VWAP (C); calc P15 > P0 in 21/21 cells |
| E6 | Stall exit (45 min, ±0.05%) | **Change**: 30 min, ±0.05%, laggards only (never reached +1b) | 30 min | §3 calc |
| E7 | 90-minute deadline | **Change**: 60 min for laggards only; trailing trades run to E4/E5 or E8 | 60 min | §3 calc; Mesfin 60–75-min holds (C) |
| E8 | Hard exits | **Keep** | 15:00 on expiry days (before the 15:15 auction), 15:10 otherwise | §7 (C, sib-C) |
| E9 | Breakeven move | **Do not add** | — | §4 calc; index BE ≠ premium BE |
| E10 | Event exit (new) | **Add** | exit 5 min before any scheduled intraday announcement | §7 IV crush (own data) |
| E11 | Daily stop and no re-entry after a loss | **Keep** | 1 stop-out ends the day | Coval & Shumway (A) |
| E12 | Overrides | **New logging rule** | any discretionary early exit or skipped exit is logged with its reason and scored | §6 |

Modelled effect [calc]: E-trail (P15) beat the current rules by +₹20 to +₹170 per trade, about +0.03R to +0.23R, in every regime, entry time and expiry modelled. The two summary cells are no drift +₹41 and persistent drift +₹65 at 10:00 0DTE. It cuts the rupee win rate from 0.28–0.36 to 0.21–0.29, cuts the average loss by about ₹250 and raises the average win. **It does not make a no-edge entry profitable:** the no-drift EV stays at about −₹113 to −₹121 a trade.

**B. Pre-registered exit variants** (paired on the same simulated setups, 2019–2026, same entry, strike and cost model)

| ID | Variant | Why it is worth a trial | Trial cost |
|---|---|---|---|
| X0 | **Current rules** (E1, E2, fixed target 2.3–2.5b, VWAP cross, stall 45, deadline 90, hard exits) | Baseline; already specified | 1 |
| X1 | **E-trail** (table A) | Best-supported robust alternative | 1 |
| X2 *(only if the entry is the noise-band breakout)* | **Zarattini runner**: stop = max(structural stop, VWAP), no target, no trail, laggard time stops, hard exit | Highest upside under trend (+₹318 to +₹770 calc) but a 3–16% win rate and −₹103 to −₹217 on failed breakouts; tests whether Nifty breakout days carry the US-style fat tail | 1 (optional) |

Not recommended as trials (fix them a priori instead): trail width and activation multiples, the stall threshold, the deadline length, premium-based stops, and breakeven moves. Each would be a separately tuned parameter with too little power to detect its effect.

**C. Pre-committed decision rule (write it down before running)**
1. Compute the per-setup paired difference X1 − X0 in net rupees on the 2019–2023 development folds.
2. **Adopt X1 unless** its mean is below X0's with t ≤ −1.0 on development, **or** it is negative in the 2024–2025 walk-forward by more than one standard error. With low power, the a priori choice (X1) wins ties.
3. X2 is adopted only if it beats the winner of steps 1–2 with t ≥ 2 in both periods, **and** its maximum losing streak and drawdown stay inside the ₹7,000 capital floor in the walk-forward.
4. Freeze the winner for the paper phase. No exit changes during the paper phase.

**D. Design decision flagged under the trial budget (per the owner's standing instructions)**
- **What matters:** whether the exit rule lets the entry's edge show up net of theta, without spending scarce trials.
  - The power check says the 2,000-setup backtest can detect only exit improvements of about ₹75–₹100+ per trade at 80% power (≈2,600 setups needed for ₹60; ≈950 for ₹100). The modelled X1 − X0 is ₹20–₹65 a trade in the realistic weak-drift cells and ₹90–₹170 only in strong-trend cells.
  - The most likely outcome is therefore that the backtest **cannot distinguish** X1 from X0 at conventional significance, unless the entries really ride trend days.
  - Live trading (about 8 trades a month) cannot distinguish them at all.
- **Options:**
  1. **Two exit trials (X0, X1), a priori default X1.** Pros: uses 2 of 10–15 slots, theory-consistent, robust across modelled regimes. Cons: the choice rests mainly on theory and a model, not on Nifty data. Cost and time: none beyond the simulation already planned.
  2. **Three trials (add X2).** Pros: tests the fat-tail hypothesis that underlies the breakout literature. Cons: a third slot, and a 3–16% win rate makes paper and live verdicts nearly impossible within the planned horizon (the SPRT on win rate breaks down). Same cost as option 1.
  3. **Grid over trail, target and time-stop parameters.** Pros: looks thorough. Cons: classic exit overfitting (Bailey et al.; Li et al.'s −5 hold-out Sharpe), and it would consume most of the budget. **Not recommended.**
- **Recommendation:** option 1. Add X2 only if the final entry is the noise-band breakout *and* the owner accepts a low-win-rate, high-payoff profile. What would change this: the pilot below showing that the project's setups reach their maximum favourable excursion within about 30 minutes and then revert. Then a fixed target near 2× would be the a priori choice (it won the failed-breakout cells), and X1 would become the challenger.
- **What cannot be known yet:**
  - The drift profile (half-life) of the project's own entries.
  - How often Nifty breakout days trend on to the close.
  - Real slippage on manual trailing exits.
  - Whether realised/implied volatility stays at 0.69–0.80.

  **Cheap pilot, before freezing exits:** on the **training window only** (2019–2022 1-min Nifty futures), compute for every labelled setup:
  - the MFE and MAE paths;
  - time to MFE;
  - the share of setups whose MFE exceeds 2.5b;
  - the post-MFE retracement.

  This is descriptive, uses no exit P&L ranking, and sets the a priori default.
- **Consequences to record:**
  - With trailing exits the payoff is no longer binary, so the **SPRT and CUSUM kill-switches defined on win rate must be re-specified on net R per trade**, for example a sequential t-test or SPRT on mean R with variance estimated in simulation. The breakeven win rate of 40% in the decision log no longer applies, and the expected live win rate becomes about 25–33%.
  - Record the exit decision and this reason in `docs/decisions.md` once the owner chooses.

### Gaps
- Every number in A–D that is labelled [calc] comes from a stylised Brownian model. Real Nifty paths (jumps, U-shaped volatility, 15-minute reversal, auction effects, IV level drift, spot–vol asymmetry) could shrink the trailing advantage. That is why X0 against X1 must be re-run on 1-min futures paths with the calibrated option model before the paper phase.
- The strike in the MC (Δ ≈ 0.35–0.39, ≈₹750 at the stop) exceeds the ₹400 cap. At the cap, Nifty Δ must fall to about 0.20 at b = 0.10% (≈(400 − ~100)/(65 × 22.6)), where fixed costs weigh more. Relative exit rankings should hold, but rupee magnitudes will be about half and the cost share larger.
- Automation of the trail and backstop ratchet in Angel One is unverified. If only manual alerts are possible, model a 1–2-minute exit latency on trailing exits as well as on stops.
