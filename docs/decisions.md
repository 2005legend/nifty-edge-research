# Decision log

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
