# Decision log

## 2026-10-19: Analyst desk on Groq free tier, explanation-only, pilot first

**Owner's choice:** Groq free tier as the LLM provider. Paid models only after the system shows profit.

**What matters:**
- Free limits per model are 8K tokens/minute and 200K tokens/day. Stock TradingAgents prompts are about 7K tokens each, so a full run may be rejected.
- A model switch resets the forward-test record.

**Decisions:**
- **D7, explanation-only.** The desk writes briefs, bull/bear/risk cases and caution flags, but has no trade vote. Reason: LLM agents can't be honestly backtested (memorisation, non-determinism), and TradingAgents' published results come from one 3-month rally. After 150–300 scored days, one registry trial may test its caution flags as a veto.
- **Pilot first.** Week 1 after SP1: run trimmed TradingAgents v0.7.0 on Groq (quick tier `qwen/qwen3.8-27b`, deep tier `openai/gpt-oss-120b`) for 5–10 sessions.
  - **Path A (adapt TradingAgents)** if ≥90% of runs complete, no request exceeds the per-minute limit, and daily tokens stay ≤150K per model.
  - **Path B (compact desk with the same roles, prompts ≤5K tokens)** otherwise.
- **Pinning.** Keep the same models for the scoring year. Ollama fallback days are tagged and not scored.
- **Scoring.** Forward-only. The first verdict comes at about 250 sessions; at about 100 sessions the test reaches only about 1.6 SE.

**Can't be known yet:** real token use on Groq, and whether Groq accepts forced tool calls. The pilot measures both.

## 2026-10-19: OpenBB lean install as the global/macro data layer

**Decision:**
- Install only the free providers needed (`openbb-core`, `-fred`, `-federal-reserve`, `-oecd`, `-imf`, `-nasdaq`, `-ecb`, `-mcp-server`).
- Keep the plain `yfinance` library for prices.
- Do not use the AGPL `openbb-yfinance` add-on.

**Why:**
- OpenBB v5 removed yfinance, FMP and EconDB from the core.
- The full meta-package is heavy.
- It has no NSE/BSE options and no Indian news feeds, so Angel One and our own RSS collector remain the sources for those.

**Repository check:** `OpenBB-finance/OpenBB` redirects to `openbq-org/OpenBB` (same GitHub repo ID), so the owner's link is the official repo.

## 2026-10-19: Timing-report decisions D1–D6 accepted as defaults

Source: `reports/Nifty options strategy timing refinement.md`, section "Six decisions only the owner can make". The owner accepted the recommendations.

- **D1, exits.**
  - E-trail is the default: after +1b in favour, trail at 1.5b with stop = max(trail, VWAP); no breakeven move; laggard time stops at 30/60 minutes.
  - The 50% win-rate goal is retired, and the scoreboard is mean net R per trade.
  - **Why:** E-trail beat fixed targets in all 21 modelled cells, by about ₹10–85 a trade at ₹400 scale.
  - **Would change if:** the excursion pilot shows the system's setups peak within about 30 minutes and then revert.
- **D2, stop geometry.**
  - Keep ₹400 for the simulation.
  - If fewer than about 60 eligible setups a year, or the high-VIX pass rate is under half the low-VIX rate, choose between ₹15k/₹600 and alert-off before go-live.
- **D3, frequency.** ≤100 live trade-days a year spread pro-rata by month, ≤3 a week as a hard ceiling, and a premium-turnover ledger aiming for under ₹10 lakh a year.
  - **Why:** SEBI data ties high frequency and turnover relative to capital to 94–98% loss rates.
  - **Cost:** the live verdict takes about 12 months instead of about 8.
- **D4, holdout.**
  - 2026 is reported as "touched", because the timing research examined 2023–2026 descriptively.
  - Go live on the agreed timeline, but scale beyond 1 lot only after a clean forward holdout of about 150 labelled setups.
- **D5, trial budget.** A registry of 6 core trials (B0, X1, M1, RV-2, RV-1, RV-3) plus up to 5 conditional ones, hard cap 13 including reserves.
  - **Why:** the deflated Sharpe falls from 0.947 at 10 trials to 0.869 at 30.
- **D6, pauses.** No automatic loss-streak pauses: on Nifty, P&L-based filters skipped the better trades (t = −2.34). The owner may invoke a logged "shadow pause" (paper-only until the end of the week).

**Correction.** The 18 Oct entry below said "2–4 week paper check". The agreed paper phase is **1–2 months with rules frozen**, as the first 18 Oct entry records.

## 2026-10-18: Paper trade 1–2 months with frozen rules; tune only in simulation

**Owner's request:** paper trade 1–2 months and improve the system until the win rate crosses 50%.

**Concern raised:**
- 1–2 months gives about 8–20 alerts. With 16 trades, the observed win rate varies by about ±12 points from luck alone.
- A true 40% system shows 50% or more about 1 time in 4.
- Tuning until paper shows 50% would fit noise.
- At a 2:1 payoff, breakeven is 40%, so the scoreboard is net profit per trade, not win rate.

**Decision (confirmed in substance by the owner's acceptance of the full design on 19 Oct):**
- All rule changes are made and evaluated in the 2019–2026 simulation, within the trial budget.
- Paper trading runs 1–2 months with rules frozen.
- Go live only if the simulation passes its gates *and* paper results are not clearly worse than the simulated range.
- If the simulation result is borderline, extend paper trading towards about 100 alerts.

## 2026-10-18: Validation is simulation-first, with a short paper phase

**Decision.** The edge verdict comes from a historical simulation (2019–2026) run under pre-registered gates. After that comes only a 2–4 week paper check of mechanics and costs, then live trading with 1 lot.

**Why.** The owner did not want to wait months. The research shows that distinguishing a 46% win rate from 40% with live trades alone needs about 100 trades, which at about 8 trades a month is about a year.

**Trade-off we accept.** Live trading starts before live results can confirm the simulation.
- The kill-switches (SPRT, CUSUM, ₹7,000 capital floor) can catch a clearly broken system.
- They cannot prove a good one quickly.

**Mitigation.** Every alert is paper-tracked whether it is taken or not, and skipped setups are labelled too. This builds evidence faster at no cost.

**Expectations recorded at decision time.** These are guesses, not measurements:
- About 50–60% chance the simulation finds no cost-surviving edge. In that case the system stays alert-off.
- About 30–40% chance of a 42–46% win rate, i.e. roughly +₹200–600 a month on ₹10k with 8 trades a month.
- About 5–10% chance of 50% or better.
- Breakeven is 40% at ₹400 risk, ₹800 target and about ₹80 all-in cost per trade.

## 2026-10-07: Capital ₹10,000, risk ₹400 per trade, target ≥1.5× net

**Why.** At ₹5,000, a ₹400–500 risk per trade was 8–10% of capital, above Kelly at plausible edges. At ₹10,000, ₹400 is 4%.

## 2026-10-20: SP1 data foundation built; live smoke run waits for Angel One credentials

**Built:** 17 of 18 plan tasks, with 99 offline tests. A first live run without broker credentials worked:
- NSE holiday API
- all 9 news feeds (516 items)
- Federal Reserve, OECD and Nasdaq calendar via OpenBB
- yfinance
- Angel One's public instrument master (lot sizes, ticks and index tokens verified)

**Still open (needs the owner):**
- `.env` with Angel One SmartAPI credentials
- the live smoke tests (`pytest -m live`)
- one full recorded session on a trading day
- websocket token limit and expired-futures checks (spec §9 items 1–2)
- FBIL G-sec and NSE index P/E URLs (series show `failed` until configured)

**Notes:**
- 20 Oct 2026 was a market holiday (Dussehra).
- GDELT's newest GKG file returned 404 during the run; the collector reports it and continues.
