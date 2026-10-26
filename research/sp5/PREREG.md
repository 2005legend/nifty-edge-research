# SP5 pre-registration: buy index options only when the market prices them below the forecast move

Written and committed on 26 Oct 2026, **before** any profit or loss of this rule was computed. The result is
judged against this file only. Nothing below may change after the first run; a change is a new hypothesis and
a new look.

## Question

Index options usually price a bigger move than the one that follows (the volatility risk premium), which is the
likely reason buying them loses on average. Is there an edge for a **buyer** on the days the market prices an
option **below** the system's own forecast move, measured on **real traded prices**?

## Data

- Option prices: the NSE F&O bhavcopy `close` (the day's last traded price) of every NIFTY option, 11 Feb 2019 to
  the last derived session. Only contracts that traded that day (`traded`).
- Index: the official daily close (`daily`). Time to expiry: the frozen business-time clock (`clock_v1.yaml`).
- Forecast: the system's HAR model, the version known at the previous close (`rv_hat_nogap`).

## The rule (decided at day d's close, held to day d+1's close)

1. **Contract:** the nearest NIFTY weekly whose expiry is strictly after d+1, so the position never holds through
   settlement. The strike is the one whose call and put closes are closest (|C − P| smallest), both traded on d
   and on d+1.
2. **Forward:** F = K + C − P at that strike (put-call parity).
3. **Implied variance for the night and day ahead:** IV² × T₁, where IV is the mean of the call's and put's
   Black-76 implied vols (time to expiry on the business clock), and T₁ = the clock's business time from d 15:30 to
   d+1 15:30.
4. **Forecast variance:** HAR `rv_hat_nogap` for d+1 × (1 + θ_night), the session plus the night (θ_night from the
   frozen clock).
5. **Ratio ρ = implied ÷ forecast. Buy the ATM straddle (1 lot call + 1 lot put) at d's close if ρ < 1.0.**
   The threshold 1.0 means "priced below the forecast". It is fixed by that meaning, not fitted.
6. **Exit:** both legs at d+1's close.
7. **Costs:** Angel One charges per leg at today's schedule (`costs.round_trip`, the as-of schedule reported
   beside). Each leg pays the system's half-spread at entry and again at exit (`half_spread`, at 15:29).

**Baseline:** the same straddle bought on **every** eligible day, with no filter.

## Gates (all must hold, NIFTY, 11 Feb 2019 to 31 Dec 2025)

1. Mean net return on premium per trade > 0, with t ≥ 2.
2. Positive mean in at least 4 of the 6 full years 2020-2025.
3. Filtered mean minus baseline mean > 0, with Welch t ≥ 2.

2026 is reported separately, because it is "touched" (spec D4) and not a gate. Passing means a **forward paper
trial** in shadow, never real money directly.

## Power and expected outcome (stated before the run)

- About 1,700 eligible days. If 20-40% have ρ < 1, that is 340-680 trades.
- A one-day ATM weekly straddle's return has a standard deviation of roughly 25-40%, so t ≥ 2 needs a mean of about
  +2.5 to +4% per trade.
- **Most likely outcome:** the baseline loses (the risk premium), and the filter loses less but does not reach a
  positive mean with t ≥ 2. The chance of passing is judged about 20-30%.
- **Capital note:** an ATM Nifty weekly straddle costs about ₹13,000-20,000 per lot pair, more than the owner's
  ₹10,000. A pass would need a cheaper structure, for example one leg or a strangle, and that would be its own
  pre-registered test.

## Bookkeeping

- This is **look 48** in `research/prior_looks.md`.
- Exploratory views after the primary result (deciles of ρ, Sensex from 2024, other holding periods) are
  labelled **exploratory**. They decide nothing.
