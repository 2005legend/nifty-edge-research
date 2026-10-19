# Regime-level strategy timing for a Nifty/Sensex intraday breakout system: when it works, how to detect the regime in time, and whether timing works at all

Scope: regime dependence of intraday momentum/breakout and trend strategies; out-of-sample evidence on strategy/factor timing; regime-detection lag and false alarms; edge decay; Indian regime history; and a concrete regime-timing layer for the system (alerts-only, 1 lot of Nifty Tuesday-expiry or Sensex Thursday-expiry options, ₹10,000 capital, ₹400 risk, ≤1 trade/day and ≤3/week, H1 noise-band breakout with VWAP trail, daily jump-model regime, HAR forecast, gamma regime to validate, event gate, stress score that raises the hurdle, CUSUM kill-switch).

Not re-researched here (see `../Nifty options multifactor quant strategy/intraday_technical_regime.md` and `../Nifty options multifactor quant strategy/signal_fusion_validation.md`): Baltussen et al. gamma split and Rosa's post-publication decay of intraday momentum; the Shu-Yu-Mulvey jump model vs HMM results; Kurth et al. on the death of fast trend; Mesfin's falsification study; the Bernoulli CUSUM/SPRT design and its ARL table; retraining cadence via Pesaran-Timmermann window averaging; the DSR trial-budget arithmetic.

**Evidence grades used in this note:** **A** = peer-reviewed and robust out-of-sample; **B** = peer-reviewed but limited (in-sample, one market, abstract-level reading, or not cost-tested); **C** = practitioner work, working paper, or **own measurement**; **D** = anecdote.

**Own measurements** come from `regime_timing_measure.py` (this folder; output in `regime_timing_measure_output.txt`), using Yahoo daily data 2014 – 5 Oct 2026 for Nifty, India VIX, S&P 500, USD/INR and Brent. All regime variables are lagged so they are known before the open. The main tool is a **daily OHLC proxy of the noise-band breakout**:
- band = max/min(open, previous close) × (1 ± σ), σ = 14-day mean |close/open − 1|;
- enter exactly at the band, hold to the close; no VWAP trail, no 15-minute clock;
- outcomes are measured in "noise units" (σ) so that regimes with different volatility are comparable;
- "single-breach" days (only one band touched) are the trades; "both-band" days are counted separately, and in a conservative variant they are booked at −1σ.

**The proxy has a mechanical positive bias.** On simulated driftless Brownian days it shows +0.12σ (constant volatility) to +0.15σ (with volatility clustering) per trade. **The real edge is the observed value minus this null.** The proxy is a description of when breakouts pay, not a backtest.

---

## 1. Regime dependence of intraday momentum/breakout and trend strategies: what effect sizes are documented, and what Nifty shows

### Takeaway
**Literature (mostly US).**
- Intraday momentum and breakout strategies earn more in high-volatility, crisis and dealer-short-gamma states:
  - Zarattini et al.: SPY Sharpe about 1.5 unconditionally, rising to about 3.5 when VIX > 40 (C).
  - Baltussen et al.: R² 3.58% vs 0.05% by gamma sign (B).
- Their losing years are calm years (SPY strategy −12.8% in 2016, −6.9% in 2017).
- Slower trend (TSMOM) earns crisis alpha. Momentum crashes in "panic" states, after declines with high volatility, when the market rebounds (Daniel & Moskowitz, A).

**On Nifty (own daily proxy, C).**
- Per noise unit, the breakout edge does **not** vary significantly with any of 13 regime variables (0 of 13 top-vs-bottom spreads have |t| > 2).
- In **absolute** terms (bp per trade) the payoff scales with volatility: 6 bp at India VIX < 12 vs 26 bp at VIX ≥ 25. For a fixed-₹-cost option buyer this is the main regime channel.
- The proxy does worst:
  - after **VIX spikes** (5-day VIX up > 25%: −0.13σ, n = 38);
  - in **V-shaped rebounds** (April 2026: −0.55σ per trade);
  - in **2026 overall** (+0.05σ, below the +0.12–0.15σ random-walk null).

### Cited Findings
**Intraday momentum / noise-band breakout**

- **[C] Zarattini, Aziz & Barbon, "Beat the Market" (SPY, May 2007 – Apr 2024; working paper, version Feb 2025).**
  - VIX at the open was used to bucket days. Sharpe "tend[s] to improve with increasing levels of market volatility": about **1.50 when VIX > 6** (all days) and about **3.50 when VIX > 40**, then lower for even higher VIX (few observations).
  - The exact Sharpe at VIX > 20 is only shown in a figure (not extracted).
  - Performance by year (vol-targeted version): 2008 +63.4%, 2018 +61.1%, 2020 +26.8%, 2022 +24.4%; but **2016 −12.8% and 2017 −6.9%**, both very-low-VIX years.
  - Positive in all 10 worst S&P quarters, e.g. Q4 2008 +16%, Q1 2020 +7%, Q2 2022 +12%, Q4 2018 +31%.
  - **Short trades' P&L is unrelated to same-day VIX** (regression p = 0.91). Limiting shorts to high VIX does not help, and taking shorts only below the 100/150/200-day SMA "sacrific[es] a substantial portion" of profit.
  - **Gamma proxy:** strategy return on the prior day's 5-day RSI gives β = −3.25 bp per RSI point (p = 0.001). The strategy does better after short-term declines, which the authors read as dealers turning short gamma.
  - Daily patterns: NR4 days 22 bp/day (t = 5.14) vs 12 bp unconditional (t = 5.34); "trend" pattern days −2 bp.
  - Best volatility multiplier is about 1.5 (Sharpe 1.35 → 1.55). Best lookback is 90 days (1.35 → 1.50). The paper keeps 1.0 and 14 days.

  — [paper PDF](https://alexandria.unisg.ch/bitstreams/a99aba00-f967-49b3-aceb-f544dc386e0b/download)
- **[B] Gao, Han, Li & Zhou (2018, JFE).** Intraday momentum is stronger on high-volatility, recession and macro-news days. — summarised in [02_strategy_evidence_part1.md](../02_strategy_evidence_part1.md)
- **[B] Baltussen et al. (2021, JFE).** Last-half-hour momentum exists only when dealers are net short gamma (R² 3.58% vs 0.05%). **[B] Rosa (2022, JFM):** a Markov-switching model shows predictability is regime-dependent and vanished post-publication in SPY; thresholds beat always-on. — both in [intraday_technical_regime.md §2](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md)
- **[C] Barbon & Buraschi, "Gamma Fragility" (working paper).**
  - Intraday momentum is explained by **negative ex-ante dealer gamma imbalance interacting with illiquidity**; positive gamma goes with reversal. The effect is stronger in less liquid underlyings.
  - Follow-up on leveraged ETFs: a large negative (positive) gamma imbalance relative to dollar volume gives end-of-day momentum (reversal).

  Abstract-level only. — [author page](https://abarbon.com/papers/gamma-fragility); [Alpha Architect on the LETF paper](https://alphaarchitect.com/options-hedging-leveraged-etfs-in-market-swings/)
- **[B] Hossain et al. (2021), S&P 500 and CSI 300.** First-half-hour → last-half-hour momentum holds for the S&P 500, but **during the pandemic shock the last-half-hour predictability lost significance in both markets**. High volatility *and* volume coincide with the positive effect. — [ZCU repository](https://dspace5old.zcu.cz/handle/11025/46501?locale=en)
- **[B] Limkriangkrai et al. (2023, Pacific-Basin Finance Journal), APAC ETFs.** Intraday momentum is mainly present in China and Japan. It was **weaker during COVID-19**, and volatility matters more than volume. Summary-level; India not covered. — [Monash repository PDF](https://researchmgt.monash.edu/ws/files/519509174/494419119_oa.pdf)

**Trend following and momentum crashes**

- **[A] Moskowitz, Ooi & Pedersen (2012, JFE), 58 futures.** Time-series momentum persists for 1–12 months and "performs best during extreme markets", i.e. crisis alpha. — [PDF](https://fairmodel.econ.yale.edu/ec439/jpde.pdf); [SSRN](https://papers.ssrn.com/abstract=2089463)
- **[A] Daniel & Moskowitz (2016, JFE), "Momentum Crashes".**
  - Crashes happen in **panic states**: after market declines, when market volatility is high, and coinciding with market rebounds. They are partly forecastable.
  - A dynamic strategy built on forecasts of momentum's mean and variance **approximately doubles the alpha and Sharpe ratio** of static momentum. This is robust across periods, international equity markets and asset classes.
  - Mechanism: after big declines, the past-loser beta can exceed 3, so a sharp rebound crushes the short leg.

  — [NBER w20439](https://www.nber.org/papers/w20439); [PDF](https://business.columbia.edu/sites/default/files-efs/pubfiles/4607/mom11.pdf)
- **[A] Barroso & Santa-Clara (2015, JFE), "Momentum has its moments".** Volatility-targeting momentum virtually eliminated crashes and nearly doubled its Sharpe ratio (secondary summary). — [Swedroe, etf.com](https://www.etf.com/sections/index-investor-corner/swedroe-downside-momentum)
- **[B] Kurth et al. (2026).** LeBaron effect: daily trend P&L accrues disproportionately in *low*-volatility periods, and post-2008 trend losses come from high-volatility, large-return days. — in [intraday_technical_regime.md §3](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md)

**Volatility of volatility**

- **[B] Huang, Schlag, Shaliastovich & Thimme (2019, JFQA).** Volatility and volatility-of-volatility significantly *negatively* predict future delta-hedged option payoffs. Option buyers do worse after high VoV. US data. — [SAFE page](https://safe-frankfurt.de/publications/working-papers/details/publicationname/volatility-of-volatility-risk.html)
- **[C] Park (2013, FEDS).** VVIX forecasts tail-risk-hedge returns. **No study was found that tests VVIX (or India VIX-of-VIX) as a regime variable for intraday momentum or trend.** — [Federal Reserve](https://www.federalreserve.gov/pubs/feds/2013/201354/index.html)

**Own measurement: Nifty daily breakout proxy, 2015 – 5 Oct 2026, 2,894 days** [C] — [output](regime_timing_measure_output.txt)

Unconditional: 1,517 single-breach trades; mean +10.9 bp = **+0.224σ** (t = 7.35); hit rate 57.1%; both-band days 2.2%.

| Null comparison | Mean per trade | Hit rate | Trigger rate | Mean \|C−O\|/(H−L) |
|---|---|---|---|---|
| Nifty observed | +0.224σ | 57.1% | 52.4% | 0.482 |
| Brownian null, constant vol | +0.117σ | 53.6% | 59.9% | 0.479 |
| Brownian null, vol clustering | +0.154σ | 54.5% | 57.7% | 0.481 |

Excess over null is about **+0.07 to +0.11σ** per trade. Nifty days breach the band *less* often than a random walk, and day-level "trendiness" is indistinguishable from a random walk.

Regime splits (per single-breach trade):

| Regime bucket (known pre-open) | Trades | bp per trade | σ per trade | t | Noise unit σ (bp) |
|---|---|---|---|---|---|
| India VIX < 12 | 236 | 6.0 | 0.188 | 3.0 | 35 |
| VIX 12–15 | 481 | 10.5 | 0.263 | 5.6 | 47 |
| VIX 15–20 | 553 | 11.0 | 0.193 | 3.5 | 61 |
| VIX 20–25 | 178 | 12.0 | 0.245 | 2.2 | 71 |
| VIX ≥ 25 | 69 | 26.1 | 0.266 | 1.9 | 133 |
| 5-day VIX change ≤ −10% | 168 | 15.0 | **0.323** | 3.3 | 70 |
| 5-day VIX change +10 to +25% | 205 | 5.8 | 0.122 | 1.6 | 59 |
| 5-day VIX change > +25% | 38 | 9.0 | **−0.130** | −0.7 | 93 |
| VIX-of-VIX (20-day stdev of Δln VIX), bottom tercile | 493 | 12.5 | 0.283 | 6.4 | 49 |
| VIX-of-VIX top tercile | 434 | 12.7 | 0.225 | 3.9 | 72 |
| RV20 percentile > 0.9 | 142 | 18.8 | 0.305 | 2.6 | 96 |
| Recent trendiness (20-day mean \|C−O\|/(H−L)) top tercile | 437 | 6.5 | **0.113** | 2.9 | 70 |
| Online jump-model "bad" state, 2020–26 (model fit 2014–19, OOS) | 461 | 8.3 | **0.138** | 2.8 | 70 |
| Online jump-model "good" state, 2020–26 | 409 | 11.5 | **0.295** | 4.5 | 45 |
| Year 2026 (to 5 Oct) | 104 | −1.0 | **0.049** | 0.4 | 49 |

- **Top vs bottom spreads (per-trade σ, Welch t):**
  - VIX level +0.06 (t +0.6); VIX percentile 0.00; VoV −0.06 (t −0.8); RV percentile −0.01; VRP +0.10 (t +0.9).
  - 200-DMA +0.02; drawdown 0.01; 60-day autocorrelation +0.03.
  - |S&P prior day| +0.05; Brent 5-day −0.07; USD/INR 5-day +0.09.
  - **VIX 5-day change −0.24 (t −1.97); recent trendiness −0.15 (t −1.98)**.
  - So **0 of 13 reach |t| > 2**, where about 0.7 would be expected by chance.
  - The jump-model good-vs-bad split (out-of-sample for the model's parameters): +0.158σ, **t +1.93**. It held in both halves: 2020–22 good +0.30 / bad +0.21; 2023–26 good +0.29 / bad +0.08.
- **2026 monthly:**
  - March −11.3% Nifty, average VIX 21.4: proxy +0.18σ per trade.
  - **April +7.5% rebound: −0.55σ per trade** (the momentum-crash pattern).
  - September −6.1% with VIX ~11.9: −0.01σ.
- **Long vs short in 2026:** long trades −0.169σ, short trades +0.179σ.

### Inferences
- The literature's "breakouts love high volatility" result shows up on Nifty mainly as **bigger absolute moves per trade, not a better hit rate or more noise units per trade.**
  - With fixed rupee costs (₹80–135 per round trip), higher absolute moves still matter: the cost hurdle is a smaller fraction of the move.
  - For an option buyer, theta and the VRP scale with implied volatility. So the net regime benefit is smaller than for the SPY share strategy and must be measured with option P&L.
- **Panic and rebound states are the documented failure mode.** This is consistent with Daniel & Moskowitz (A), with Hossain et al. and Limkriangkrai et al. on COVID (B), and with our VIX-spike and April-2026 numbers (C, weak). A VIX *spike* (rate of change), not a VIX *level*, is the better-supported warning variable.
- **Recent trendiness predicted *worse* breakouts** (t −1.98). This suggests regime "momentum" in trendiness is not exploitable at daily-data resolution. Do not add a "trending regime" gate (e.g. ER/ADX/autocorrelation) without intraday evidence.
- **The jump-model "bad" (downtrend) state** is the only regime cut that held out-of-sample for its parameters and in both sub-periods. In that state the edge is roughly the random-walk null (about 0.14σ vs 0.12–0.15σ). It is borderline (t 1.93), so it is a candidate for a hurdle, not a switch.
- **The Zarattini short-side results argue against a "shorts only in bear markets / longs only in bull markets" filter.** A *long-side* hurdle is defensible on Nifty specifically: the intraday drift is negative (−6 bp/day in 2026, −9 bp/day 2015–19), and long trades were negative in 2026.
- **The system's own stop/strike rules are a hidden regime filter that points the "wrong" way** [C, calc].
  - The maximum option delta that fits a ₹400 stop is 400 / (65 × stop distance in points). With the strike picker's delta floor of 0.25, the structural stop must be ≤ about 25 Nifty points, about 0.11% at 22,500.
  - The end-of-day noise unit averaged 35 bp at VIX < 12 (≈ 79 points) but 133 bp at VIX ≥ 25 (≈ 300 points). A VWAP/band stop that is a fixed fraction of the band will fit the budget mostly in calm regimes, the regimes where the absolute payoff is smallest.
  - The backtest should report the H1 stop-fit pass rate by VIX tercile. This is descriptive and costs no trials.

### Gaps
- No peer-reviewed study tests intraday momentum or noise-band breakouts on Nifty or Sensex by regime. The only India evidence is our daily proxy, which cannot see intraday ordering, VWAP exits or the 15-minute clock.
- Zarattini's exact Sharpe at VIX 15–20 vs > 20 is only in a figure. The paper is a working paper, not refereed.
- No study links VVIX or India VIX-of-VIX to breakout or trend profitability.
- Our proxy has low power. Per-trade σ ≈ 1.19, so detecting a 0.10σ regime difference at 80% power needs about 2,200 trades per group, against about 1,500 trades in total.

---

## 2. Does timing a strategy (on/off by regime or by its own recent performance) work out of sample?

### Takeaway
**Mixed, and mostly weak after realistic implementation.**
- **Valuation-based contrarian factor timing failed robustness tests** (Asness et al., B).
- **Volatility-managed portfolios look good in-sample but lose out-of-sample for most strategies** (72 of 103 lower Sharpe; Cederburg et al., A) **and after costs** (Barroso & Detzel, A). The market portfolio is the exception.
- Evidence that *does* survive:
  - dimension-reduced factor timing (Haddad-Kozak-Santosh, A: out-of-sample Sharpe 0.87–0.96 vs 0.76 static, at monthly frequency with no costs);
  - momentum-crash avoidance via forecasts of momentum's mean and variance (Daniel-Moskowitz, A).
- **Timing by the strategy's own recent performance has no support at the horizon this system needs.**
  - Stop-loss rules reduce expected return unless returns are serially correlated (Kaminski & Lo, B).
  - In our Nifty proxy, monthly strategy returns show zero persistence (Spearman −0.005).
  - A trailing-60-day equity-curve filter would have kept the *worse* trades (+0.146σ kept vs +0.367σ skipped; Welch t −2.34).

### Cited Findings
- **[B] Asness, Chandra, Ilmanen & Israel (2017, JPM), "Contrarian factor timing is deceptively difficult".**
  - No robust evidence that value-spread timing of factors delivers meaningful outperformance.
  - The one exception (value timing of momentum) was judged not robust.
  - Turnover erodes the predictive power of factor valuations, especially for momentum.
  — [AQR supplement](https://www.Aqr.Com/Insights/Research/Journal-Article/Contrarian-Factor-Timing-is-Deceptively-Difficult-Supplement); [CXO summary](https://www.cxoadvisory.com/?p=29629); [Institutional Investor](https://www.institutionalinvestor.com/article/2bsvu85lwfurbhds0mh34/portfolio/cliff-asness-blasts-rob-arnott-on-factor-timing)
- **[A] Haddad, Kozak & Santosh (2020, RFS 33(5)), "Factor Timing".**
  - Each principal-component portfolio of anomalies is predicted by its own book-to-market ratio.
  - PC1 and PC4 have **out-of-sample monthly R² ≈ 4% and 3.5%**. Total out-of-sample R² is about 1%. All are significant against Kelly-Pruitt placebo critical values except PC5.
  - Split-sample out-of-sample Sharpe:

    | Strategy | Out-of-sample Sharpe |
    |---|---|
    | Static factor investing | 0.76 |
    | Market timing | 0.63 |
    | Full factor timing | 0.87 |
    | Anomaly timing | 0.96 |
    | Pure anomaly timing | 0.77 (0.71 in-sample) |

  - The authors note that a firm implementability verdict needs a transaction-cost model.
  — [NBER w26708 PDF](https://nber.org/system/files/working_papers/w26708/w26708.pdf); [RePEc](https://ideas.repec.org/p/nbr/nberwo/26708.html)
- **[C] Neuhierl, Randl, Reschenhofer & Zechner, "Timing the Factor Zoo" (AFA 2024 working paper).**
  - Over 300 factors and 39 signals. Timing improves almost all factor groups, and the median timed factor beats its untimed version by about 2% a year.
  - **Past factor returns and volatility are the strongest single predictors**. Partial-least-squares aggregation beats any single signal.
  - Out-of-sample tables not read.
  — [AEA abstract](https://aeaweb.org/conference/2024/program/paper/8GNzb57Z); [AFA](https://afajof.org/management/viewp.php?n=32508)
- **[A] Ehsani & Linnainmaa (2022, JF), factor momentum.** Most factors are positively autocorrelated. The average factor earns about **6 bp/month after a losing year vs 51 bp after a positive year**. This is monthly/annual factor-level persistence, not intraday strategy persistence. — [NBER w25551](https://www.nber.org/papers/w25551)
- **[B] Moreira & Muir (2017, JF).** Scaling exposure down when volatility is high produced large alphas and higher Sharpe ratios for market, value, momentum, profitability, ROE, investment, BAB and carry. A draft reports a market alpha of 4.9% and a 25% Sharpe increase. — [NBER 22208](https://www.nber.org/papers/22208)
- **[A] Cederburg, O'Doherty, Wang & Yan (2020, JFE).**
  - Volatility-managed versions had higher gross Sharpe ratios in only **53 of 103** strategies, and only **8** of those were significant.
  - Realistic out-of-sample mean-variance implementations had **lower Sharpe ratios and certainty-equivalent returns in 72 of 103**.
  - Cause: structural instability in the spanning regressions.
  — [paper PDF](https://www.lehigh.edu/~xuy219/research/COWY.pdf); [Alpha Architect](https://alphaarchitect.com/does-portfolio-timing-based-on-volatility-signals-outperform-buy-and-hold/)
- **[A] Barroso & Detzel (2021, JFE).** After transaction costs, volatility management of factors other than the market yields zero abnormal returns and lower Sharpe ratios. The volatility-managed market portfolio survives costs, but only when sentiment is high. — [working-paper PDF](https://sbfc.sydney.edu.au/2019/papers/P057_Named.pdf); [abstract](https://academicnewsletter.sufe.edu.cn/info/355328)
- **[B] Kaminski & Lo (2014, J. Financial Markets 18), "When do stop-loss rules stop losses?"**
  - Under a random walk, simple 0/1 stop-loss (switch-off) rules **always reduce expected return**. They add value only when returns have momentum (serial correlation).
  - US monthly equity data 1950–2004: some rules added 50–100 bp/month during stop-out periods.
  — [MIT DSpace](https://dspace.mit.edu/handle/1721.1/114876)
- **[A] Daniel & Moskowitz (2016).** The dynamic (mean- and variance-forecast) momentum strategy roughly doubles Sharpe, out of sample across markets. — see §1
- **[B] Rosa (2022).** Signal-strength thresholds beat always-on intraday momentum. — in [intraday_technical_regime.md §2](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md)

**[C] Own measurement: strategy momentum in the Nifty daily breakout proxy, 2015–2026** (conservative variant, noise units)

| Test | Result |
|---|---|
| Monthly proxy P&L vs previous month | Spearman −0.005 (p 0.95) |
| vs previous 3 months | +0.045 (p 0.61) |
| vs previous 6 months | +0.029 (p 0.73) |
| Next-month mean after a positive vs non-positive prior month | +2.00σ vs +1.69σ (n 105 / 31) |
| Equity-curve filter: trailing 60-day proxy P&L > 0 | kept trades +0.146σ (n 1,380) vs skipped +0.367σ (n 201); Welch t −2.34 |
| Trailing 20-day P&L > 0 | kept +0.144σ (n 1,144) vs skipped +0.254σ (n 437); t −1.58 |
| Sub-period check, trailing 60-day | 2015–19: kept +0.166 vs skipped +0.459. 2020–26: kept +0.130 vs skipped +0.326 |

- **[C] Own measurement: switch-off vs raised band hurdle** (band ×1.5 instead of ×1.0), by VIX-percentile tercile.
  - Per day, the ×1.5 band earns less than ×1.0 in every tercile: 0.058/0.063/0.028 vs 0.093/0.107/0.085σ per day.
  - Per trade it is better only in the low/mid-VIX terciles: 0.181/0.214 vs 0.163/0.198. It is worse in the high-VIX tercile: 0.085 vs 0.163.
  - Turning off any tercile would forgo positive per-day P&L (t 2.9–3.7 in each tercile).

### Inferences
- **Strategy timing can work when there is a mechanism and a slow-moving, well-measured state** (factor valuations; momentum's beta after crashes). It fails when the timing rule is fitted to a few episodes, uses unstable relations, or adds turnover.
  - A personal system with ≤150 trades a year sits squarely in the "unstable, few episodes" zone.
  - Default to **no switch-off** except for events with a known mechanism.
- **Do not switch the system on/off by its own recent P&L.**
  - Kaminski & Lo: stopping helps only with positive serial correlation.
  - Our proxy shows none at monthly horizons, and the opposite at 20–60 days (losing stretches were followed by *better* trades, consistent with mean reversion of whipsaw clusters).
  - The live CUSUM must therefore be framed as a **"broken system" detector** (structural loss of edge), not as a regime timer.
- **Raising the hurdle beats switching off** as the default response to an adverse-but-uncertain regime signal:
  1. It is monotone and loses less when the regime call is wrong. This is the same logic as shrinkage towards equal weights in forecast combination ([signal_fusion_validation.md §2](../Nifty%20options%20multifactor%20quant%20strategy/signal_fusion_validation.md)).
  2. With detection lags of 2–6 weeks (§3), a binary switch is wrong during the first weeks of each new regime and during the rebound.
  3. The volatility-timing literature shows the gains are fragile out of sample, so the action should be small.
- Volatility *scaling* (Moreira-Muir) does not apply directly: risk is already fixed at ₹400 per trade and size is fixed at 1 lot. The only levers are the probability hurdle and the strike/delta choice.

### Gaps
- No study found tests "trading the equity curve" (switching a single intraday strategy on or off by its own trailing P&L) out of sample in a peer-reviewed venue. The evidence is theoretical (Kaminski & Lo) plus our proxy.
- Neuhierl et al.'s out-of-sample and after-cost numbers were not read.
- Haddad-Kozak-Santosh is monthly and cost-free; its transfer to daily or intraday on/off decisions is an inference.

---

## 3. Regime detection methods: detection lag and false alarms

### Takeaway
Every detector trades lag for false alarms. On Nifty 2015–2026 (own measurement, C):
- **Online statistical jump model (λ = 20, Shu-Yu-Mulvey features):** flags a ≥10% drawdown **10–28 trading days after the peak**, when about **5%** of the fall has already happened. About 1.6 regime entries a year; 5% of spells last < 5 days. It clears 23–161 days after the trough.
- **VIX > 20:** lag 6 to 182 days. It **missed slow FII-driven drawdowns** (2019: 182 days; 2024–25: 131 days). 65% of its spells last < 5 days (whipsaw).
- **Variance CUSUM:** detects a 1.5× volatility jump in about 12–24 days on Gaussian data. **Fat tails cut its false-alarm interval from about 2,700 to about 200 days** at the same threshold.

Regimes last about 50–110 trading days (jump model), so a 2–6-week lag consumes 20–50% of a typical regime. Daily regime gates can only help if the edge difference between regimes is large.

### Cited Findings
- **[B] Shu, Yu & Mulvey (2024).** The 2-state jump model beats HMMs after costs with a 1-day delay. The jump model is robust to 5–10-day delays, whereas the HMM underperforms at a 5-day delay. Regime models aim to recognise a shift *after* it occurs and profit from persistence. — [arXiv 2402.05272](https://arxiv.org/abs/2402.05272); details in [intraday_technical_regime.md §3](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md)
- **[B] Nystrup, Lindström & Madsen ("Learning HMMs with persistent states by penalizing jumps").**
  - Misspecified or misestimated HMMs switch states unrealistically fast. The jump estimator gives direct control over the transition rate, is less sensitive to initialisation, is robust to misspecified distributions, and produced **much lower transaction costs** in a simple trading strategy.
  - A sparse variant with feature selection gives fewer, more persistent states.
  Abstract-level. — [NYU seminar abstract](https://cims.nyu.edu/dynamic/events/2422); [KTH seminar](https://www.kth.se/math/kalender/erik-lindstrom-what-drives-cryptocurrency-returns-learning-market-regimes-through-the-sparse-statistical-jump-model-1.1224113)
- **[B] Adams & MacKay (2007), Bayesian online change-point detection.** Exact online inference of the "run length" since the last change point. The hazard rate encodes the prior expected regime length. No finance detection-lag benchmarks were found. — [arXiv 0710.3742](https://www.alphaxiv.org/abs/0710.3742)
- **[B] Page (1954) CUSUM; Bernoulli CUSUM for live win rates.** h = 2.5 gives about 603 trades to a false alarm and about 102 trades to detect a fall from 42% to 33%. — in [signal_fusion_validation.md §8](../Nifty%20options%20multifactor%20quant%20strategy/signal_fusion_validation.md)
- **[C] India regime-switching.**
  - Ahmad & Kamaiah (2011, MPRA): a 2-state Markov-switching AR on Indian equities. The bull regime is far more persistent than the bear regime; bear phases match the 2008 and 2010 external crises, and the market is sensitive to external shocks. — [RePEc](https://ideas.repec.org/p/pra/mprapa/37174.html)
  - No study reporting Nifty regime durations or detection lags was found.

**[C] Own measurement: detectors vs the eight Nifty drawdowns ≥ 10%, 2015–2026**

The eight drawdowns (peak → trough, depth):
1. Mar 2015 → Feb 2016, −22.5%
2. Jan → Mar 2018, −10.2%
3. Aug → Oct 2018, −14.6%
4. Jun → Sep 2019, −11.4%
5. Jan → Mar 2020, −38.4%
6. Oct 2021 → Jun 2022, −17.2%
7. Sep 2024 → Mar 2025, −15.8%
8. 2 Jan 2026 → 30 Mar 2026, −15.2% (not yet recovered)

| Detector (risk-off flag) | % days flagged | Entries/yr | Mean spell (d) | Spells < 5 d | Lag peak → flag (trading days, 8 episodes) | Median drawdown at flag | Days after trough to clear | Agreement with ex-post jump-model label |
|---|---|---|---|---|---|---|---|---|
| Jump model online λ=5 (fit 2014–19) | 56% | 3.0 | 46 | 23% | 6,6,15,11,12,24,6,10 | −3.8% | 19–107 | 94% |
| **Jump model online λ=20 (fit 2014–19)** | 53% | **1.6** | 81 | **5%** | **13,10,18,27,15,28,13,13** | **−4.8%** | 23–161 | 92% |
| Jump model online λ=50 (fit 2014–19) | 51% | 1.2 | 105 | 0% | 19,17,23,34,25,32,21,19 | −6.4% | 30–166 | 87% |
| Jump model online λ=100 (fit 2014–19) | 51% | 1.1 | 113 | 0% | 33,28,26,40,32,41,31,39 | −7.8% | 45–175 | 79% |
| India VIX > 20 | 17% | 4.7 | 9 | **65%** | 44,6,26,**182**,32,27,**131**,40 | −8.6% | 0–101 | 57% |
| VIX 252-day percentile > 0.8 | 19% | 5.0 | 9 | 63% | 40,0,9,180,30,68,23,39 | −5.5% | 0–42 | 55% |
| RV20 percentile > 0.8 | 21% | 3.5 | 15 | 34% | 3,4,12,0,32,82,39,20 | −3.0% | 0–45 | 59% |
| Close < 200-DMA | 27% | 4.5 | 15 | 64% | 34,33,24,40,30,90,34,14 | −9.0% | 1–78 | 75% |
| Variance CUSUM h=3 (σ ×1.5, 20-day hold) | 17% | 1.6 | 26 | 0% | 43,4,17,0,32,82,131,20 | −7.0% | 0–29 | 57% |
| Variance CUSUM h=5 | 12% | 1.2 | 25 | 0% | 45,6,24,0,37,83,135,47 | −9.1% | 0–29 | 54% |

- **Jump-model setup.** Features as in Shu et al.: log EWM downside deviation (half-life 10) and EWM Sortino (half-lives 20 and 60). K = 2, centroids fit 2014–19. The online state is the last state of the optimal DP path using data up to t.
- **The jump model's "bad" state covers about half of all days.** On Nifty it separates "uptrend" from "not uptrend" rather than isolating crashes.
- **Persistence:** P(flag unchanged next day) is 0.962 for VIX > 20, 0.972 for RV percentile > 0.8, 0.964 for the 200-DMA, and 0.987–0.991 for the jump model at λ = 20 / 100.
- **Variance-CUSUM run lengths** (simulated; 1,000 paths; known baseline σ):

  | Threshold, return distribution | Days to false alarm, mean (median) | Days to detect σ ×1.5, mean (median) |
  |---|---|---|
  | h = 3, Gaussian | 314 (225) | 14.7 (12) |
  | h = 5, Gaussian | 2,709 (1,859) | 24.1 (21) |
  | h = 3, Student-t(4) | 96 (69) | 20.5 (15) |
  | h = 5, Student-t(4) | 207 (132) | 31.8 (24) |

- **Current state (5 Oct 2026):**
  - jump model "bad" at all λ;
  - Nifty below its 200-DMA;
  - India VIX 14.77 (252-day percentile 0.73);
  - 5-day VIX log change +0.195, just under a +0.20 spike threshold;
  - RV20 10.8 (percentile 0.52);
  - drawdown −14.3% from the 252-day high;
  - neither variance CUSUM in alarm.

### Inferences
- **The jump model is the only detector that is both timely and quiet.** It flags 10–28 days after the peak with about 1.6 entries a year. VIX and 200-DMA rules whipsaw (60–65% of spells < 5 days) and give erratic lags.
  - **λ ≈ 20 is a sensible fixed choice.** λ = 5 doubles the false entries; λ ≥ 50 adds 1–3 weeks of lag.
  - Fix λ rather than re-tuning it monthly on Sharpe as Shu et al. do. Re-tuning is a hidden trial multiplier.
- **The jump model clears late** (23–161 days after the trough). A jump-model gate is therefore least useful, even harmful, in V-shaped rebounds. That is exactly where the proxy lost most (April 2026). This argues for a *small* hurdle in the bad state, not a switch-off.
- **VIX level is a poor regime detector for India.**
  - 2019 and 2024–25 were slow, flow-driven drawdowns in which India VIX stayed below 20 for months.
  - 2026's shock spiked VIX only to 27.9 (30 Mar 2026, the trough day), *after* most of the fall.
  - Use VIX **rate of change** (5-day log change) to detect shocks, and the jump model for slow trends.
- **Variance-CUSUM thresholds calibrated on Gaussian assumptions are far too trigger-happy on fat-tailed returns** (false-alarm interval 207 vs 2,709 days at h = 5).
  - Calibrate thresholds by block-bootstrap of Nifty's own returns, not by Gaussian formulas.
  - The same warning applies to the live Bernoulli CUSUM if outcomes are serially correlated: regime clustering shortens ARL0.
- **Detection lag vs edge.** Suppose a regime lasts about 80 days and the detector lags about 15 days with about 15% false-entry spells.
  - The gate is "right" on roughly 65–75% of gated days.
  - With a true regime difference of about 0.15σ per trade (our jump-model split), the realised benefit of a gate shrinks to about 0.10σ. That is below what the backtest can confirm (§1 Gaps).
  - Use regime state as a **prior-motivated hurdle**, not a fitted switch.

### Gaps
- No finance benchmark of BOCPD detection delay or false-alarm rate was found. No India HMM, jump-model or change-point study with detection lags was found; the numbers above are our own.
- The jump-model centroids for the 2014–19 fit used data through 2019, so results for 2015–19 are in-sample. Only 2020–26 is out-of-sample for the model's parameters.
- Episode-level lags rest on 8 drawdowns, so their sampling error is large.
- A 2026 preprint frames *when to act* on a filtered regime as a Bayesian decision problem. It was not read. — [arXiv 2610.20366](https://www.alphaxiv.org/abs/2610.20366)

---

## 4. Edge decay and adaptive markets: how a small system should monitor and adapt without overfitting

### Takeaway
Expect the live edge to be about **half** of the backtest edge.
- Published anomalies lose 26% out of sample and 58% post-publication (McLean & Pontiff, A).
- Out-of-sample performance is about 50% of in-sample across 72 published strategies (Falck, Rej & Thesmar, B).
- Intraday momentum specifically vanished post-publication in SPY (Rosa, B).

Markets alternate between efficient and inefficient phases (Lo's adaptive markets hypothesis; Indian evidence of alternating efficiency, B). A small system cannot detect slow decay statistically at fewer than 150 trades a year. So adaptation should be **pre-scheduled, shrunk and slow**:
- refit on a calendar;
- self-normalising (percentile) thresholds;
- haircut priors;
- a CUSUM for collapse only.

### Cited Findings
- **[A] McLean & Pontiff (2016, JF), 97 predictors.**
  - Portfolio returns are **26% lower out-of-sample** and **58% lower post-publication**.
  - The 26% is an upper bound on data mining. The extra 32% is attributed to informed trading after publication.
  — [Ivey PDF](https://ivey.uwo.ca/media/3775549/pontiff.pdf); [published copy](https://Www.Gwern.net/doc/economics/2016-mclean.pdf)
- **[B] Falck, Rej & Thesmar (2022, Quantitative Finance 22(11)), 72 published strategies.**
  - Out-of-sample performance is about **50% of in-sample**, driven jointly by overfitting and arbitrage.
  - A secondary summary says publication year explains about 30% of the cross-strategy variance in Sharpe decay.
  — [MIT DSpace](https://dspace.mit.edu/handle/1721.1/163650); [Evidence Investor summary](https://evidenceinvestor.com/post/why-and-how-systematic-strategies-decay)
- **[B] Lo (2004, JPM 30), adaptive markets hypothesis.** Market efficiency is shaped by competition, adaptation and selection. Profit opportunities appear and disappear as the population of participants and the environment change. — [MIT page](https://web.mit.edu/Alo/www/Papers/JPM2004.html); [SSRN](https://papers.ssrn.com/abstract=602222)
- **[B] India AMH evidence.**
  - Hiremath & Kumari (2014, SpringerPlus): linear tests show **alternating efficient and inefficient periods** in Indian equities. Nonlinear dependence persists but tapers, so the market is moving towards efficiency. — [PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4155058/)
  - Sing & Singh (Ceylon J. Business), Sensex and Nifty 2014–2020: inefficiency appears **during crises and fear periods**. — [CBJ](https://mgmt.cmb.ac.lk/cbj/index.php/testing-the-adaptive-market-hypothesis-and-time-varying-efficiency-in-the-indian-equity-market/)
- **[B] Rosa (2022).** Intraday momentum in SPY disappeared post-publication. **[B] Kurth et al. (2026):** fast trend collapsed after 2009 on small-tick contracts. **[C] Mesfin (2026):** a 1-bar delay flips sign. — all in [intraday_technical_regime.md](../Nifty%20options%20multifactor%20quant%20strategy/intraday_technical_regime.md)
- **[A] Pesaran & Timmermann (2007); Zhang et al. (2020).** Averaging across estimation windows handles breaks. **Refit cadence:** every 6 months or after 250 new labelled setups. — in [signal_fusion_validation.md §8](../Nifty%20options%20multifactor%20quant%20strategy/signal_fusion_validation.md)
- **[A] Cederburg et al. (2020).** Volatility-timing failures come from **structural instability** in the estimated relations, which is the same risk any fitted regime gate carries. — see §2
- **[C] Own: drift of regime-variable levels.**
  - Mean India VIX by period: 15.7 in 2015–19; 14.3 in Jul 2022 – Nov 2024; 11.0 in Sep–Dec 2025. The 2026 maximum was only 27.9.
  - Share of days with India VIX > 20, by year:

    | Year | Days with VIX > 20 |
    |---|---|
    | 2017 | 0% |
    | 2020 | 70% |
    | 2021 | 36% |
    | 2022 | 37% |
    | 2023 | 0% |
    | 2024 | 6% |
    | 2025 | 2% |
    | 2026 | 10% |

  So a fixed-level gate is effectively a "2020–22 only" gate. — [output](regime_timing_measure_output.txt); same CSV

### Inferences
- **Haircut rule.** Set the live prior and the CUSUM in-control win rate at **validated win rate − 0.5 × (validated − breakeven)**. Example: a backtest at 46% with a 40% breakeven gives a live prior of 43%. This follows the roughly 50% decay found in two independent literatures.
- **Self-normalising thresholds.** Express regime thresholds as **trailing-252-day percentiles or rates of change** (5-day VIX change, HAR percentile), not as fixed levels. India VIX's level distribution shifted down after 2023. Percentiles keep a gate's activation rate stable without re-fitting.
- **Refit schedule** (no ad-hoc re-tuning after losses):

  | Component | Refit schedule | Fixed (never re-tuned) |
  |---|---|---|
  | HAR | Monthly, rolling 750 days | — |
  | Jump model | Yearly, expanding window | λ = 20 and the features |
  | Meta-model | Every 6 months or every 250 labelled setups, averaging expanding and 3-year rolling fits | — |
  | Regime-hurdle add-ons | — | Fixed numbers, changed only through the trial registry |

- **Monitoring hierarchy** (fastest-moving information has the least authority):
  1. **Calibration-in-the-large** on *all* labelled setups (taken or not), monthly. This is the only fast, statistically meaningful signal: about 23 setups a month.
  2. **Bernoulli CUSUM** on live trades, as a kill-switch for collapse (already specified).
  3. **Regime-conditional live hit rates** shown on the dashboard as descriptive only. Never act on them below 100 trades per regime.
- **Participant-ecology changes are the Indian analogue of "publication".** The SEBI reforms of Nov 2024 – 2025, the move to Tuesday expiry (Sep 2025) and the closing auction (Aug 2026) each changed who trades index options and how dealers hedge. Treat each date as a break: report backtest results before and after it, and weight post-break evidence more.

### Gaps
- No study measures edge-decay rates for intraday index strategies in India or for retail-scale option-buying systems.
- Falck et al.'s full results (decay by strategy type and holding period) were read only at abstract level.

---

## 5. Indian specifics: how Nifty intraday behaviour differed across regimes (2015–2026)

### Takeaway
- **Breakouts did well in fast crashes and badly in calm or whipsaw years** (own proxy, C):
  - COVID crash: +0.46σ per trade;
  - 2022 H1 rate hikes: +0.24σ;
  - 2015–19: +0.24σ;
  - Sep–Dec 2025 (low-vol Tuesday-expiry period): +0.12σ;
  - **2026: +0.05σ, below the random-walk null**, with the April rebound at −0.55σ.
- The post-SEBI-reform period had the **highest share of both-band whipsaw days** (4.1% vs 2.0% pre-COVID).
- Intraday drift was negative in every period except Sep–Dec 2025.
- 2026 is unusual in that **overnight returns were also negative** (−1.9 bp/day). Daily return autocorrelation was negative (−0.09).
- Index-option participation fell sharply after the reforms: premium turnover −9% YoY, notional −29%, unique individual traders −20% (SEBI study, C).

### Cited Findings
**[C] Own measurement: Nifty daily breakout proxy by period** — [output](regime_timing_measure_output.txt)

| Period | Days | Mean India VIX | Mean RV20 | VIX−RV | Noise unit (bp) | Both-band days | σ per trade (t) | Daily AC1 | Intraday drift bp/day | Overnight drift bp/day |
|---|---|---|---|---|---|---|---|---|---|---|
| 2015–2019 | 1,222 | 15.7 | 13.0 | +2.7 | 56 | 2.0% | +0.24 (5.2) | +0.06 | −9.3 | +12.5 |
| COVID crash, 20 Feb – 31 May 2020 | 64 | 42.5 | 49.4 | −6.9 | 180 | 1.6% | **+0.46 (2.0)** | −0.20 | −30.5 | −6.3 |
| Jun 2020 – Dec 2021 | 398 | 19.9 | 15.6 | +4.3 | 64 | 2.0% | +0.23 (2.5) | +0.06 | −7.8 | +22.7 |
| 2022 H1 rate hikes | 123 | 21.4 | 20.1 | +1.3 | 73 | 0.8% | +0.24 (1.7) | −0.02 | −4.5 | −3.2 |
| Jul 2022 – 19 Nov 2024 | 588 | 14.3 | 11.6 | +2.7 | 47 | 2.7% | +0.24 (3.3) | −0.05 | −4.2 | +11.0 |
| SEBI reforms, 20 Nov 2024 – Aug 2025 | 193 | 14.6 | 13.1 | +1.5 | 52 | **4.1%** | +0.22 (2.3) | 0.00 | −0.7 | +2.7 |
| Tuesday expiry, Sep – Dec 2025 | 84 | 11.0 | 8.0 | +3.1 | 38 | 1.2% | +0.12 (1.0) | +0.22 | +1.9 | +6.1 |
| **2026 YTD (war / oil / rates)** | 186 | 14.9 | 13.4 | +1.5 | 49 | 2.2% | **+0.05 (0.4)** | −0.09 | −6.1 | −1.9 |

**Own measurement: 2026 path.**
- Nifty peaked on 2 Jan 2026 (26,329). It fell 11.3% in March (average VIX 21.4; VIX peaked at 27.89 on 30 Mar 2026, the trough day), rebounded 7.5% in April, and fell another 6.1% in September with VIX only about 11.9.
- On 5 Oct 2026: 22,556 (−13.7% YTD); USD/INR 96.28; Brent $100.88.
- The September 2026 leg is a "slow" decline that VIX did not register.

**Reform and market-structure facts**
- **[C] SEBI study (July 2025) on the Nov 2024 F&O measures, Dec 2024 – May 2025 vs a year earlier:**
  - index-options premium turnover −9%; notional −29%;
  - individual traders' premium turnover −11%;
  - unique individual participants −20%;
  - premium turnover was still +14% vs two years earlier;
  - 91% of individual traders lost money in FY25.

  — [Business Standard](https://www.business-standard.com/amp/markets/capital-market-news/sebi-sees-dip-in-derivatives-turnover-91-of-retail-traders-lose-money-in-fy25-125070800660_1.html)
- **[C] ICRA (May 2025).** Premium average daily turnover fell 18% in Dec 2024 – Mar 2025 vs Apr – Nov 2024, and option contracts traded fell 60%. NSE's monthly average premium turnover went from ₹12.4 trn to ₹9.1 trn. — [ICRA](https://www.icra.in/Rating/DownloadResearchSummaryReport?id=6333); [Business Standard](https://www.business-standard.com/amp/markets/news/index-option-annual-premium-turnover-sees-first-dip-in-8-years-in-fy25-125042801097_1.html)
- **[C] Already in project notes** (not re-researched):
  - Nifty weekly expiry on Tuesday since 1 Sep 2025; Bank Nifty weeklies ended Nov 2024.
  - Closing auction session for expiry since 3 Aug 2026.
  - Expiry-day share of index-option turnover 59% in FY26 vs 70% in FY25.

  — [01_market_structure_2026.md](../01_market_structure_2026.md)
- **[B] Indian market efficiency alternates and is lowest during crises.** — [Hiremath & Kumari 2014](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4155058/); [Sing & Singh](https://mgmt.cmb.ac.lk/cbj/index.php/testing-the-adaptive-market-hypothesis-and-time-varying-efficiency-in-the-indian-equity-market/)

### Inferences
- **2026 is a bad regime for this trigger as measured so far.** The regime layer should therefore act *now*, with longs at a higher hurdle while the jump model is in its bad state.
  - The breakout proxy shows no edge above the random-walk null.
  - Long breakouts lost.
  - The biggest damage came in the post-crash rebound.
  - The 2026 holdout result for H1 should be expected to be weak. A weak 2026 result is consistent with the regime, not necessarily proof that H1 is broken. That ambiguity is why the 2026 holdout must be pre-registered with this expectation written down.
- **The post-reform rise in both-band days (4.1%)** is consistent with more two-way intraday flow after retail volume fell and expiry was restructured. With one sub-period this is a hypothesis, not a fact. The H1 backtest should report results separately for before and after 20 Nov 2024.
- **Indian drawdowns since 2015 come in two kinds.**
  - Fast ones with a VIX spike: Feb 2018 (VIX > 20 within 6 days of the peak), 2020, March 2026.
  - Slow, flow-driven grinds in which VIX stayed below 20 for months: 2019 (VIX > 20 only 182 trading days after the peak), 2024–25 (131 days), and the −6% September 2026 leg with VIX near 12.

  A regime layer therefore needs **two separate detectors**: a shock detector (VIX rate of change, variance CUSUM) and a slow-trend detector (jump model).

### Gaps
- No peer-reviewed study of Nifty *intraday* momentum, breakout or autocorrelation by regime (COVID, 2022, post-reform, 2026) was found. Everything here is our daily-data proxy.
- No public study quantifies how the Nov 2024 SEBI measures, the Tuesday expiry or the closing auction changed Nifty intraday volatility or autocorrelation. The project's own 1-minute data must answer this.
- Dealer-gamma regime history for Nifty is unavailable until the bhavcopy-based rebuild in the spec is done.

---

## 6. Recommended regime-timing layer and pre-registered regime variants

### Takeaway
Use a **small regime-hurdle layer**, not on/off regime switching:
- **Hard switch-offs** only for mechanism-certain cases: event gate, data or cost failures, the CUSUM kill-switch.
- **A shock hurdle:** VIX 5-day jump or variance-CUSUM alarm.
- **A slow-trend hurdle:** online jump model, heavier on longs.
- **A gamma hurdle** once gamma is validated.
- **A slow calibration-shortfall hurdle** from live and labelled-setup data.
- **Cap the macro stress score's effect.** Brent and rupee shocks showed no conditioning power.

Test at most **three or four** regime variants inside the system's 10–15-configuration budget, with fixed parameters. Expect them to be **statistically inconclusive**: they have about 30–40% power at realistic trade counts. Adopt them on a prior-plus-no-contradiction rule.

### Cited Findings
- **Panic/shock states hurt momentum and breakouts:** Daniel & Moskowitz (A); COVID-period weakening of intraday momentum (Hossain et al., Limkriangkrai et al., B); Nifty VIX-spike and April-2026 rebound numbers (C). — §1
- **High-volatility states give larger absolute breakout moves:** Zarattini et al. (C); Gao et al. (B); Nifty bp per trade 6 → 26 bp from VIX < 12 to ≥ 25 (C). — §1
- **Dealer gamma sign conditions intraday momentum:** Baltussen et al. (B); Barbon & Buraschi (C); Zarattini RSI proxy (C). — §1
- **Timing by own recent P&L fails:** Kaminski & Lo (B); Nifty proxy (C). **Volatility timing is fragile out of sample:** Cederburg et al.; Barroso & Detzel (A). — §2
- **Detection lag and false alarms:** the jump model at λ = 20 is the best trade-off; VIX levels whipsaw; Gaussian-calibrated CUSUMs over-alarm on fat tails (C). — §3
- **Expected decay of about 50%** (A/B). — §4
- **Power.** To detect an 8-point win-rate difference between two regimes (45% vs 37%) at 80% power, two-sided α = 0.05, needs **592 trades per regime**. A one-sided α = 0.10 screen needs 340. With 150–200 trades per regime, power is only **29–37%** [calc]. A 46% vs 40% difference needs 1,068 per regime. [calc, this note]
- **Trial budget.** 10–15 effective configurations for the whole system; DSR falls from 0.947 at N = 10 to 0.869 at N = 30 (600 trades). — [signal_fusion_validation.md §6](../Nifty%20options%20multifactor%20quant%20strategy/signal_fusion_validation.md)

### Inferences

#### A. The regime-timing layer (starting values, to be frozen before testing)

All inputs are computed after the close and used the next day, except the intraday shock check. The output is an **additive margin Δ on the EV gate**: p̂ ≥ p_breakeven + 0.04 (base) + Δ. **Cap Δ at +0.08**, so p̂ never needs to exceed breakeven + 0.12. Every component is logged on the day card.

| # | Component | Variable (exact definition) | Threshold (starting value) | Action | Evidence |
|---|---|---|---|---|---|
| 0 | **Hard off (unchanged)** | Event gate E3 (election results, Budget before the speech, first 30–45 min after RBI); data/feed fault; live costs > 30% over model; CUSUM alarm; capital ≤ ₹7,000 | as in spec | No alerts | Mechanism-certain (prior notes, spec) |
| 1 | **Shock hurdle** | S = 1 if ln(VIX_{t−1}/VIX_{t−6}) ≥ **+0.20**, OR the variance CUSUM (σ ×1.5 vs trailing-250-day σ, h set by block-bootstrap to about 1 false alarm a year; ≈ h = 5–6) alarmed in the last **20** sessions, OR \|overnight gap\| ≥ **1.5 × σ̂_HAR** | as stated | Δ += **+0.04** for 5 sessions after the trigger (both sides) | A (Daniel-Moskowitz, mechanism) + C (Nifty VIX-spike −0.13σ, n = 38; April 2026) |
| 2 | **Slow-trend hurdle** | Online 2-state jump model on log EWM downside deviation (half-life 10) and EWM Sortino (half-lives 20, 60); λ = **20** fixed; expanding refit yearly; state lagged 1 day | bad state | Δ += **+0.04 longs, +0.02 shorts** | C (Nifty out-of-sample split +0.16σ, t 1.93; 2026 long side −0.17σ) + B (negative Nifty intraday drift; Shu et al. persistence) |
| 3 | **Gamma hurdle** (only after gamma validation) | NGE from the chain/bhavcopy, sign convention fixed by the gamma engine's own pre-registered test | NGE ≥ 0 (dealers long gamma) | Δ += **+0.04**; no add-on when NGE < 0 | B (Baltussen R² 3.58% vs 0.05%), C (Barbon-Buraschi; Zarattini RSI proxy) |
| 4 | **Calibration-shortfall hurdle (live)** | Beta posterior on the gap between observed and predicted hit rate over *all* labelled setups since go-live, prior worth 100 setups centred on 0 | posterior mean shortfall > 0.03 | Δ += the shortfall, capped at +0.06; **never negative** (no loosening) | B (calibration logic, [signal_fusion_validation.md §4](../Nifty%20options%20multifactor%20quant%20strategy/signal_fusion_validation.md)); avoids equity-curve timing (§2) |
| 5 | **Macro stress score (spec)** | Oil, rupee, yields, FII, geopolitics (0–9) | as in spec | **Cap its hurdle effect at +0.02** unless variant RV-1 passes. Keep it for expected range and display | C: Brent 5-day and USD/INR 5-day splits show no effect (t −0.67, +0.85); no literature on macro-stress gating of intraday breakouts |
| — | **Volatility level** | HAR σ̂ percentile, India VIX level | — | **No hurdle.** Volatility enters through σ_rem sizing, the "implied move not rich vs HAR" gate and EV. Report stop-fit pass rate by VIX tercile | Literature points to high volatility being *good* (Zarattini, Gao); Nifty per-σ edge is flat; level gates whipsaw (§3) |

**Live usage on 5 Oct 2026.** Components 1 and 2: VIX 5-day change +0.195 (just under the shock threshold); jump model bad. So Δ = +0.04 for longs and +0.02 for shorts, plus whatever the stress cap allows. The system is currently tilted against long breakouts, which matches the 2026 evidence.

**Why hurdles, not switches.**
1. No regime cut in our data shows a negative per-trade edge with |t| ≥ 2. Switching off forgoes positive per-day expectancy in every volatility tercile (§2, own).
2. Detection lags of 10–28 days and exit lags of 23–161 days make binary switches wrong at turning points (§3).
3. Kaminski & Lo: switching off helps only with positive serial correlation, which our proxy does not show.
4. Hurdles fail gracefully and keep labelled setups accruing. All setups stay shadow-labelled either way.

**Rule for upgrading a hurdle to a switch-off.** Only if the H1 backtest shows *negative* net option expectancy in that regime with t ≤ −2 over at least 60 trades, and the sign agrees with the literature. Otherwise keep the hurdle.

**How to use live performance.**
- **Kill-switch:** Bernoulli CUSUM (already in the spec), with p0 set by the decay haircut (§4) and h re-checked by simulation that includes regime clustering. Expect about 100 trades (roughly a year at 8 trades a month) to detect a 9-point collapse. It is a collapse detector, not a regime timer.
- **Slow update:** component 4. It only tightens, and it learns from all labelled setups, about 23 a month vs 8 trades.
- **Never:** pause after N losses, trade only above the equity curve's moving average, or re-tune thresholds after drawdowns. All three are equity-curve timing, which is unsupported (§2).

**Detection-lag / false-alarm trade-offs to accept (own measurement):**

| Detector | Lag after peak | Clears after trough | False or short spells | Role |
|---|---|---|---|---|
| Jump model λ = 20 | ~2–6 weeks | ~1–8 months | ~1.6 entries/yr, 5% short spells | Slow trend |
| Shock rule (VIX 5-day ≥ +20% or CUSUM) | Fast (days) for fast crashes | — | Misses slow grinds by design | Shocks |
| VIX level > 20 | Lags up to 6–9 months | — | Whipsaws, 65% short spells | Not used |

#### B. What matters / options / recommendation / what can't be known yet (trial-budget decision)

**What matters**
- The regime layer must not starve H1 itself of its trial budget.
- Documented regime effects are of the order of 0.1–0.15σ per trade, or about 5–10 win-rate points. Detecting them needs about 340–590 trades *per regime* (or about 2,200 per group in the proxy's σ units).
- The H1 backtest will likely have 300–600 trades in total, so power is about 30–40%.
- **Most likely outcome:** every regime variant is inconclusive (point estimate in the expected direction, |t| < 2).

**Options**

| Option | What it is | Cost | Pros | Cons |
|---|---|---|---|---|
| **(a) Minimal** | Test only RV-1 (stress-score justification) and RV-2 (shock hurdle) | 2 trials | Smallest DSR penalty; keeps budget for H1 and the meta-model | Learns nothing about the slow-trend or gamma gates; they then ride on priors |
| **(b) Recommended** | RV-1, RV-2, RV-4 (gamma, only if the gamma engine passes) and RV-3 (slow trend) | 3–4 trials | Covers each mechanism once | DSR penalty of 3–4 trials; still underpowered |
| **(c) Prior-only** | Fix components 1–3 at the starting values with no testing; review after 12 months of labelled live setups | 0 trials | No backtest overfitting | Untested hurdles may cut good trades; the stress-score hurdle stays unjustified |

**Recommendation: (b).** Run each variant once, with parameters fixed in `hypotheses.yaml` before any outcome is seen.
- Use the **"prior + no contradiction"** acceptance rule below, because a significance rule would reject everything at this power.
- Change to (a) if H1's own test leaves fewer than 4 trials of budget, or if H1 fails (the regime layer is then moot).
- Change to (c) if the backtest has fewer than 200 H1 trades.

**What can't be known yet**
- Whether H1 has any cost-surviving edge on Nifty.
- The sign of Indian dealer gamma.
- Option-cost variation by regime (spreads widen in shocks).
- How the ₹400 stop-fit rule filters regimes.
- The between-regime variance of H1 outcomes.

**Cheap pilot (0 trials, no outcomes viewed).** On 2019–2026 1-minute data, tabulate H1 **trigger counts, stop-fit pass rates and strike-picker pass rates by regime** (jump-model state, shock flag, VIX tercile, pre/post 20 Nov 2024), **without P&L**. This gives the per-regime n needed for the power numbers above, and shows whether the stop-fit gate already removes high-volatility regimes.

**Record.** Write this decision and its reason in `docs/decisions.md` once the owner confirms.

#### C. Pre-registered regime variants (fixed parameters; each counts as one trial)

| ID | Variant | Fixed specification | Run condition |
|---|---|---|---|
| **RV-0** | Control: H1 with non-regime gates (event, stop-fit, room-to-run, vol-richness, confirmation), EV gate at a flat +0.04 | No stress, shock, trend or gamma add-ons | Shared with H1's primary test (no extra trial) |
| **RV-1** | Spec stress-score hurdle | Margin +0.04 / +0.06 / +0.08 by stress tier, as in the spec | Always (justifies or removes an existing design element) |
| **RV-2** | Shock hurdle | Component 1: VIX 5-day log change ≥ +0.20 OR variance CUSUM (bootstrap-calibrated h for ~1 false alarm/yr, σ ×1.5) in the last 20 sessions OR \|gap\| ≥ 1.5σ̂_HAR → +0.04 for 5 sessions | Always |
| **RV-3** | Slow-trend hurdle | Component 2: online jump model, λ = 20, features fixed, expanding yearly refit, 1-day lag; bad state → +0.04 longs, +0.02 shorts | If ≥ 4 trials of budget remain after H1 and the meta-model |
| **RV-4** | Gamma hurdle | Component 3: NGE ≥ 0 → +0.04, using the gamma engine's pre-registered sign convention | Only if the gamma engine passes its own validation |
| **RV-5** | Combined | RV-2 + RV-3 + RV-4 at the same fixed values, Δ capped at +0.08 | Only if ≥ 2 of RV-2/3/4 are accepted. Counts as an additional trial |

**Acceptance rule (pre-registered).** A regime add-on is kept only if **all** of the following hold vs RV-0, on CPCV 2019–2023 plus the walk-forward on 2024–2025:
1. Net option P&L **per available day** is not lower than RV-0, since gating cuts trades and per-trade comparisons flatter gates.
2. Per-trade net expectancy is higher, with the point estimate in the literature-predicted direction. A difference with **t ≥ 1** is enough, given the power.
3. It improves in at least 4 of 6 out-of-sample years, and is never worse by more than 1 σ in any year.
4. Each fold still has ≥ 30 trades.
5. Deflated Sharpe is computed with the **cumulative** trial count.

If a variant fails, the component reverts to "no add-on". RV-1 failing means the stress score's hurdle effect is capped at +0.02, or set to 0 if its point estimate is negative.

**Report regardless of outcome:** results split before and after 20 Nov 2024 and after 1 Sep 2025; the 2026 holdout broken out by jump-model state; stop-fit pass rates by VIX tercile.

**Excluded from testing (budget saved, with reasons):**
- India VIX level or percentile thresholds and VIX-of-VIX: flat per-σ edge, whipsaw, no literature.
- 200-DMA and drawdown gates: lag of 14–90 days; Zarattini found SMA filters on shorts cost profit.
- Autocorrelation, efficiency-ratio and ADX "trending regime" gates: Nifty proxy shows the opposite sign (t −1.98); no peer-reviewed support.
- Brent and USD/INR shock gates: null.
- Equity-curve and own-P&L switches: unsupported (§2).
- Re-tuning λ or the thresholds by cross-validation: hidden trial multiplier.

The intraday GMM regime stays as an exploratory item from the earlier note, outside this budget.

### Gaps
- All component thresholds (+0.20 VIX jump, 1.5σ gap, λ = 20, +0.02/+0.04 margins) are starting values chosen from the evidence above plus judgement [D]. None is optimised, and that is intentional.
- How the hurdle interacts with the meta-model is unknown. If the meta-model already contains a regime feature (the spec allows one), components 2–3 could double-count. **Recommendation:** the meta-model's regime feature should be the HAR volatility percentile only, leaving trend and gamma to the hurdle layer.
- Option-level regime effects (IV term structure and spreads during shocks, theta in calm regimes) cannot be measured until the recorder has data spanning at least one shock. The daily proxy is index-only.
